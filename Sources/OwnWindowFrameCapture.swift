import CoreGraphics
import Foundation
import CoreMedia
import CoreVideo
import QuartzCore
@preconcurrency import ScreenCaptureKit

/// One captured frame of one of cmux's own windows.
///
/// Unchecked because it carries a `CGImage`, which the capture does not keep
/// or mutate after handing it over.
struct OwnWindowFrame: @unchecked Sendable {
    let image: CGImage
    /// Pixels per point of the captured image, so a rectangle given in window
    /// points lands on the right pixels on a Retina display.
    let pointPixelScale: Double
}

/// Captures a single frame of a cmux window, with no Screen Recording permission.
///
/// Shared by the recorder, which samples it on a schedule, and
/// `window.screenshot`, which takes one frame and writes it. The current-process
/// query is what makes the permission unnecessary, and it is also what makes
/// this safe to ship in Release: it cannot reach another application's windows
/// even on a Mac where cmux was granted Screen Recording.
struct OwnWindowFrameCapture {
    enum Failure: Error, Equatable {
        case unsupportedSystem
        case windowGone
        case timedOut
        case captureFailed(String)
    }

    /// Shorter than the socket command's 20-second deadline so both the
    /// content lookup and the first frame have their own chance to fail and
    /// retire before the socket worker gives up.
    static let operationTimeoutNanoseconds: UInt64 = 8_000_000_000

    /// At most one ScreenCaptureKit operation may be physically in flight.
    /// A timed-out API call can ignore task cancellation; it keeps this lease
    /// until it really returns, and later requests fail instead of accumulating
    /// more stuck captures behind it.
    actor OperationGate {
        private var activeLease: UUID?

        func claim() -> UUID? {
            guard activeLease == nil else { return nil }
            let lease = UUID()
            activeLease = lease
            return lease
        }

        func release(_ lease: UUID) {
            guard activeLease == lease else { return }
            activeLease = nil
        }

        var isClaimed: Bool { activeLease != nil }
    }

    private static let operationGate = OperationGate()

    let windowID: CGWindowID

    /// Finds the window and returns a filter for it.
    ///
    /// A recording resolves this once and reuses it for every frame; a still
    /// resolves it and throws it away.
    func resolveFilter() async throws -> SCContentFilter {
        if #available(macOS 14.4, *) {
            // The current-process query captures cmux's own windows without
            // Screen Recording permission, and cannot reach another app's
            // windows even if that permission was granted.
            let content: SCShareableContent
            do {
                content = try await Self.withDeadline {
                    try await SCShareableContent.currentProcess
                }
            } catch let failure as Failure {
                throw failure
            } catch {
                throw Failure.captureFailed(error.localizedDescription)
            }
            guard let window = content.windows.first(where: { $0.windowID == windowID }) else {
                throw Failure.windowGone
            }
            return SCContentFilter(desktopIndependentWindow: window)
        }
        throw Failure.unsupportedSystem
    }

    /// Captures the window the filter names at its full pixel size.
    ///
    /// Cropping and scaling happen afterwards, from
    /// `WindowRecordingFrameGeometry`, so a still and a clip of the same region
    /// come out of the same pixels.
    static func sample(filter: SCContentFilter) async throws -> OwnWindowFrame {
        let info = SCShareableContent.info(for: filter)
        // A window that has closed reports an empty rectangle rather than an
        // error, and capturing that gives a one-pixel image.
        guard info.contentRect.width > 1, info.contentRect.height > 1 else {
            throw Failure.windowGone
        }
        let pixelScale = Double(info.pointPixelScale) > 0 ? Double(info.pointPixelScale) : 1
        let configuration = SCStreamConfiguration()
        configuration.width = max(1, Int((Double(info.contentRect.width) * pixelScale).rounded(.up)))
        configuration.height = max(1, Int((Double(info.contentRect.height) * pixelScale).rounded(.up)))
        configuration.showsCursor = false
        configuration.ignoreShadowsSingleWindow = true
        configuration.captureResolution = .best
        do {
            let image = try await withDeadline {
                try await SCScreenshotManager.captureImage(
                    contentFilter: filter,
                    configuration: configuration
                )
            }
            return OwnWindowFrame(image: image, pointPixelScale: pixelScale)
        } catch let failure as Failure {
            throw failure
        } catch {
            throw Failure.captureFailed(error.localizedDescription)
        }
    }

    /// Resolves the window and captures one frame, for a caller that captures
    /// once and does not keep a filter around.
    func captureOnce() async throws -> OwnWindowFrame {
        let filter = try await resolveFilter()
        return try await Self.sample(filter: filter)
    }

    /// Gives one ScreenCaptureKit operation its own hard deadline.
    ///
    /// The operation is intentionally unstructured: a task group waits for all
    /// children when its scope exits, so an API call that ignores cancellation
    /// would defeat the deadline. The one-shot waiter discards a late result,
    /// while `gate` remains claimed until that physical operation returns. This
    /// lets the caller return on time without allowing retries to pile up more
    /// ScreenCaptureKit work.
    static func withDeadline<T: Sendable>(
        timeoutNanoseconds: UInt64 = operationTimeoutNanoseconds,
        gate: OperationGate = operationGate,
        operation: @escaping @Sendable () async throws -> T
    ) async throws -> T {
        try Task.checkCancellation()
        guard let lease = await gate.claim() else {
            throw Failure.timedOut
        }
        do {
            try Task.checkCancellation()
        } catch {
            await gate.release(lease)
            throw error
        }

        let waiter = OwnWindowCaptureDeadlineWaiter<T>()
        let operationTask = Task {
            let result: Result<T, Error>
            do {
                try Task.checkCancellation()
                result = .success(try await operation())
            } catch {
                result = .failure(error)
            }
            await gate.release(lease)
            waiter.finish(result)
        }
        waiter.setOperationCancellation {
            operationTask.cancel()
        }

        let boundedNanoseconds = min(timeoutNanoseconds, UInt64(Int.max))
        let deadline = DispatchWorkItem {
            waiter.finish(.failure(Failure.timedOut), cancelOperation: true)
        }
        DispatchQueue.global(qos: .utility).asyncAfter(
            deadline: .now() + .nanoseconds(Int(boundedNanoseconds)),
            execute: deadline
        )
        defer { deadline.cancel() }

        return try await withTaskCancellationHandler {
            try Task.checkCancellation()
            return try await waiter.wait()
        } onCancel: {
            waiter.finish(.failure(CancellationError()), cancelOperation: true)
        }
    }
}

/// Bridges an unstructured capture into one awaiting caller. Exactly one of
/// operation completion, deadline, or caller cancellation wins; all later
/// results are discarded. The lock also handles cancellation racing ahead of
/// continuation installation.
private final class OwnWindowCaptureDeadlineWaiter<Value: Sendable>: @unchecked Sendable {
    private let lock = NSLock()
    private var continuation: CheckedContinuation<Value, Error>?
    private var storedResult: Result<Value, Error>?
    private var operationCancellation: (@Sendable () -> Void)?
    private var finished = false

    func setOperationCancellation(_ cancellation: @escaping @Sendable () -> Void) {
        lock.lock()
        if !finished {
            operationCancellation = cancellation
        }
        lock.unlock()
    }

    func wait() async throws -> Value {
        try await withCheckedThrowingContinuation { continuation in
            lock.lock()
            if let result = storedResult {
                storedResult = nil
                lock.unlock()
                continuation.resume(with: result)
            } else {
                self.continuation = continuation
                lock.unlock()
            }
        }
    }

    func finish(_ result: Result<Value, Error>, cancelOperation: Bool = false) {
        let continuation: CheckedContinuation<Value, Error>?
        let cancellation: (@Sendable () -> Void)?
        lock.lock()
        guard !finished else {
            lock.unlock()
            return
        }
        finished = true
        continuation = self.continuation
        self.continuation = nil
        if continuation == nil {
            storedResult = result
        }
        cancellation = cancelOperation ? operationCancellation : nil
        operationCancellation = nil
        lock.unlock()

        cancellation?()
        continuation?.resume(with: result)
    }
}

/// Streams the app's own main window and logs when its pixels change after a
/// workspace switch, so switch latency can be read as time-to-pixels.
final class TmpPhotonProbe: NSObject, SCStreamOutput, SCStreamDelegate, @unchecked Sendable {
    static let shared = TmpPhotonProbe()
    private var stream: SCStream?
    private let queue = DispatchQueue(label: "cmux.tmp.photon", qos: .userInteractive)
    private var previous: [UInt32] = []
    private let gridX = 96
    private let gridY = 60
    private var timebase: Double = {
        var info = mach_timebase_info_data_t()
        mach_timebase_info(&info)
        return Double(info.numer) / Double(info.denom) / 1_000_000_000
    }()
    private let handle: FileHandle? = {
        let path = "/tmp/cmux-tmp-photon.log"
        FileManager.default.createFile(atPath: path, contents: nil)
        return FileHandle(forWritingAtPath: path)
    }()

    func write(_ line: String) {
        queue.async { [handle] in
            handle?.write(Data((line + "\n").utf8))
        }
    }

    @MainActor func start(windowID: CGWindowID, sidebarFraction: Double) {
        guard #available(macOS 14.4, *) else { return }
        Task { @MainActor in
            do {
                let content = try await SCShareableContent.currentProcess
                guard let window = content.windows.first(where: { $0.windowID == windowID }) else {
                    write("photon fail window-missing")
                    return
                }
                let filter = SCContentFilter(desktopIndependentWindow: window)
                let configuration = SCStreamConfiguration()
                configuration.width = max(64, Int(window.frame.width / 2))
                configuration.height = max(64, Int(window.frame.height / 2))
                configuration.minimumFrameInterval = CMTime(value: 1, timescale: 240)
                configuration.queueDepth = 8
                configuration.pixelFormat = kCVPixelFormatType_32BGRA
                configuration.showsCursor = false
                let stream = SCStream(filter: filter, configuration: configuration, delegate: self)
                try stream.addStreamOutput(self, type: .screen, sampleHandlerQueue: queue)
                try await stream.startCapture()
                self.stream = stream
                self.sidebarFraction = sidebarFraction
                write("photon started w=\(configuration.width) h=\(configuration.height) sidebar=\(sidebarFraction)")
            } catch {
                write("photon fail \(error)")
            }
        }
    }

    private var sidebarFraction: Double = 0.15

    func stream(_ stream: SCStream, didStopWithError error: Error) {
        write("photon stopped \(error)")
    }

    func stream(_ stream: SCStream, didOutputSampleBuffer sampleBuffer: CMSampleBuffer, of type: SCStreamOutputType) {
        guard type == .screen,
              let attachments = CMSampleBufferGetSampleAttachmentsArray(sampleBuffer, createIfNecessary: false) as? [[SCStreamFrameInfo: Any]],
              let info = attachments.first,
              let statusRaw = info[.status] as? Int,
              SCFrameStatus(rawValue: statusRaw) == .complete,
              let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        let displayTime = (info[.displayTime] as? UInt64).map { Double($0) * timebase } ?? CACurrentMediaTime()
        CVPixelBufferLockBaseAddress(pixelBuffer, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(pixelBuffer, .readOnly) }
        guard let base = CVPixelBufferGetBaseAddress(pixelBuffer) else { return }
        let width = CVPixelBufferGetWidth(pixelBuffer)
        let height = CVPixelBufferGetHeight(pixelBuffer)
        let rowBytes = CVPixelBufferGetBytesPerRow(pixelBuffer)
        var samples = [UInt32](repeating: 0, count: gridX * gridY)
        for gy in 0..<gridY {
            let y = min(height - 1, (gy * height + height / 2) / gridY)
            let row = base.advanced(by: y * rowBytes).assumingMemoryBound(to: UInt32.self)
            for gx in 0..<gridX {
                let x = min(width - 1, (gx * width + width / 2) / gridX)
                samples[gy * gridX + gx] = row[x]
            }
        }
        defer { previous = samples }
        guard previous.count == samples.count else { return }
        let sidebarColumns = Int(Double(gridX) * sidebarFraction)
        var sideChanged = 0
        var mainChanged = 0
        for index in 0..<samples.count where samples[index] != previous[index] {
            if index % gridX < sidebarColumns { sideChanged += 1 } else { mainChanged += 1 }
        }
        let sideTotal = max(1, sidebarColumns * gridY)
        let mainTotal = max(1, (gridX - sidebarColumns) * gridY)
        let start = TmpSwitchProbe.start
        let seq = TmpSwitchProbe.seq
        write(String(
            format: "photon seq=%d dt=%.1f side=%.3f main=%.3f",
            seq,
            (displayTime - start) * 1000,
            Double(sideChanged) / Double(sideTotal),
            Double(mainChanged) / Double(mainTotal)
        ))
    }
}
