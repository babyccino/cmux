import CoreGraphics
import Foundation
// usage: kb <pid> <count> <gapSeconds>
let args = CommandLine.arguments
let pid = pid_t(args[1])!
let count = Int(args[2])!
let gap = Double(args[3])!
let src = CGEventSource(stateID: .privateState)
for i in 0..<count {
    let key: CGKeyCode = i % 2 == 0 ? 30 : 33
    for down in [true, false] {
        let e = CGEvent(keyboardEventSource: src, virtualKey: key, keyDown: down)!
        e.flags = [.maskCommand, .maskShift]
        e.postToPid(pid)
    }
    Thread.sleep(forTimeInterval: gap)
}
