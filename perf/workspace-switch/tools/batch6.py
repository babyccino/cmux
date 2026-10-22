import os
os.chdir(os.path.expanduser('~/Code/cmux'))
p='Sources/ContentView.swift'
s=open(p).read()
rep=[
('''@MainActor enum TmpWorkspaceAppKitHostRegistry {
    static let containers = NSMapTable<NSUUID, NSView>.strongToWeakObjects()
}''','''@MainActor enum TmpWorkspaceAppKitHostRegistry {
    static let containers = NSMapTable<NSUUID, TmpPageContainer>.strongToWeakObjects()
}

/// Hosts one workspace page. With `CMUX_TMP_PAGE_ALPHA=1` a hidden page stays
/// in the AppKit tree at alpha 0, so showing it is a compositor change.
final class TmpPageContainer: NSView {
    var hostingView: NSHostingView<AnyView>?
    var tmpRenderedHidden: Bool?
    override var isFlipped: Bool { true }

    var pageHidden: Bool {
        get { TmpSwitchProbe.pageAlpha ? alphaValue < 0.5 : isHidden }
        set {
            if TmpSwitchProbe.pageAlpha {
                alphaValue = newValue ? 0 : 1
            } else {
                isHidden = newValue
            }
        }
    }

    override func hitTest(_ point: NSPoint) -> NSView? {
        if TmpSwitchProbe.pageAlpha, alphaValue < 0.5 { return nil }
        return super.hitTest(point)
    }
}'''),
('''    final class Container: NSView {
        var hostingView: NSHostingView<AnyView>?
        var tmpRenderedHidden: Bool?
        override var isFlipped: Bool { true }
    }
''','''    typealias Container = TmpPageContainer
'''),
('''        container.isHidden = isHidden
        TmpWorkspaceAppKitHostRegistry''','''        container.pageHidden = isHidden
        TmpWorkspaceAppKitHostRegistry'''),
('''        let hiddenChanged = container.isHidden != isHidden || container.tmpRenderedHidden != isHidden''','''        let hiddenChanged = container.pageHidden != isHidden || container.tmpRenderedHidden != isHidden'''),
('''        if hiddenChanged {
            container.isHidden = isHidden
        }''','''        if hiddenChanged {
            container.pageHidden = isHidden
        }'''),
]
for a,b in rep:
    assert a in s, a[:60]
    s=s.replace(a,b)
open(p,'w').write(s)
p='Sources/TabManager.swift'
s=open(p).read()
a='''            if container.isHidden != hidden {
                container.isHidden = hidden'''
assert a in s
s=s.replace(a,'''            if container.pageHidden != hidden {
                container.pageHidden = hidden''')
a='''    static let lazyAppKitHost = env["CMUX_TMP_APPKIT_HOST_LAZY"] == "1"
'''
assert a in s
s=s.replace(a,a+'''    static let pageAlpha = env["CMUX_TMP_PAGE_ALPHA"] == "1"
''')
open(p,'w').write(s)
print("batch6 applied")
p='Sources/TabManager.swift'
s=open(p).read()
a='''        if TmpSwitchProbe.sidebarPreview {
            NotificationCenter.default.post('''
assert a in s
s=s.replace(a,'''        if TmpSwitchProbe.batchPreviewCommit {
            CATransaction.begin()
            CATransaction.setDisableActions(true)
        }
        if TmpSwitchProbe.sidebarPreview {
            NotificationCenter.default.post(''')
a='''            TmpSwitchProbe.forceSwap(to: incoming, in: tabs)
            CATransaction.flush()
            TmpSwitchProbe.log("preflushed")
        }'''
assert a in s
s=s.replace(a,'''            TmpSwitchProbe.forceSwap(to: incoming, in: tabs)
            if TmpSwitchProbe.batchPreviewCommit {
                CATransaction.commit()
            }
            CATransaction.flush()
            TmpSwitchProbe.log("preflushed")
        } else if TmpSwitchProbe.batchPreviewCommit {
            CATransaction.commit()
        }''')
a='''    static let pageAlpha = env["CMUX_TMP_PAGE_ALPHA"] == "1"
'''
s=s.replace(a,a+'''    static let batchPreviewCommit = env["CMUX_TMP_BATCH_COMMIT"] == "1"
''')
open(p,'w').write(s)
print("batch6b applied")
