import AppKit
import CmuxNextHome

/// A file or picture dragged over Home's conversation list goes to the shown conversation, as a
/// drop on its transcript does: the whole Home pane is one drop target (Lawrence 2026-10-20:
/// "I want people to drag images into Chief properly"). The transcript view decides, takes the
/// drop and draws the highlight; the New Message page takes no attachments.
extension TopHomePageView {
    private var dropTarget: HomeNativeTranscriptView? {
        guard !isComposingNewMessage, let host, !host.isHidden, !host.transcript.isHidden else { return nil }
        return host.transcript
    }

    override func draggingEntered(_ sender: any NSDraggingInfo) -> NSDragOperation {
        dropTarget?.draggingEntered(sender) ?? []
    }

    override func draggingUpdated(_ sender: any NSDraggingInfo) -> NSDragOperation {
        dropTarget?.draggingUpdated(sender) ?? []
    }

    // NSView has no `draggingExited:`/`draggingEnded:` of its own: no super call.
    override func draggingExited(_ sender: (any NSDraggingInfo)?) {
        dropTarget?.draggingExited(sender)
    }

    override func draggingEnded(_ sender: any NSDraggingInfo) {
        dropTarget?.draggingEnded(sender)
    }

    override func performDragOperation(_ sender: any NSDraggingInfo) -> Bool {
        dropTarget?.performDragOperation(sender) ?? false
    }
}
