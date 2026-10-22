import os
os.chdir(os.path.expanduser('~/Code/cmux'))
p='Sources/TabManager.swift'
s=open(p).read()
old='''    @MainActor static func startAutodriveIfRequested() {
        guard let spec = env["CMUX_TMP_AUTODRIVE"] else { return }'''
assert old in s
s=s.replace(old,'''    @MainActor static func installAddSubviewProbeIfRequested() {
        guard env["CMUX_TMP_ADDSUB_PROBE"] == "1" else { return }
        let selector = #selector(NSView.addSubview(_:positioned:relativeTo:))
        guard let method = class_getInstanceMethod(NSView.self, selector) else { return }
        typealias Original = @convention(c) (NSView, Selector, NSView, NSWindow.OrderingMode, NSView?) -> Void
        let original = unsafeBitCast(method_getImplementation(method), to: Original.self)
        let block: @convention(block) (NSView, NSView, NSWindow.OrderingMode, NSView?) -> Void = { receiver, view, mode, relative in
            if CACurrentMediaTime() - start < 0.3, view.superview !== receiver {
                let hosted = view.subviews.first.map { String(describing: type(of: $0)) } ?? "-"
                let inner = view.subviews.first?.subviews.first.map { String(describing: type(of: $0)) } ?? "-"
                GhosttyApp.shared.logBackground("TMPSW seq=\\(seq) addsub parent=\\(type(of: receiver)) view=\\(type(of: view)) hosted=\\(hosted) inner=\\(inner) dt=\\(String(format: "%.1f", (CACurrentMediaTime() - start) * 1000))ms")
            }
            original(receiver, selector, view, mode, relative)
        }
        method_setImplementation(method, imp_implementationWithBlock(block))
    }

    @MainActor static func startAutodriveIfRequested() {
        installAddSubviewProbeIfRequested()
        guard let spec = env["CMUX_TMP_AUTODRIVE"] else { return }''')
open(p,'w').write(s)
print("batch4 applied")
p='Sources/ContentView.swift'
s=open(p).read()
old='''TmpWorkspaceAppKitHost(isHidden: !isSelectedWorkspace, content: content)'''
assert old in s
s=s.replace(old,'''TmpWorkspaceAppKitHost(workspaceId: tab.id, isHidden: !isSelectedWorkspace, content: content)''')
old='''struct TmpWorkspaceAppKitHost<Content: View>: NSViewRepresentable {
    let isHidden: Bool'''
assert old in s
s=s.replace(old,'''@MainActor enum TmpWorkspaceAppKitHostRegistry {
    static let containers = NSMapTable<NSUUID, NSView>.strongToWeakObjects()
}

struct TmpWorkspaceAppKitHost<Content: View>: NSViewRepresentable {
    let workspaceId: UUID
    let isHidden: Bool''')
old='''        container.isHidden = isHidden
        return container'''
assert old in s
s=s.replace(old,'''        container.isHidden = isHidden
        TmpWorkspaceAppKitHostRegistry.containers.setObject(container, forKey: workspaceId as NSUUID)
        return container''')
old='''        let hiddenChanged = container.isHidden != isHidden'''
assert old in s
s=s.replace(old,'''        TmpWorkspaceAppKitHostRegistry.containers.setObject(container, forKey: workspaceId as NSUUID)
        let hiddenChanged = container.isHidden != isHidden || container.tmpRenderedHidden != isHidden
        container.tmpRenderedHidden = isHidden''')
old='''        var hostingView: NSHostingView<AnyView>?'''
assert old in s
s=s.replace(old,'''        var hostingView: NSHostingView<AnyView>?
        var tmpRenderedHidden: Bool?''')
open(p,'w').write(s)

p='Sources/TabManager.swift'
s=open(p).read()
old='''        incoming.tmpForceTerminalPresentation(visible: true)
        CATransaction.commit()'''
assert old in s
s=s.replace(old,'''        incoming.tmpForceTerminalPresentation(visible: true)
        for workspace in workspaces {
            guard let container = TmpWorkspaceAppKitHostRegistry.containers.object(forKey: workspace.id as NSUUID) else { continue }
            let hidden = workspace.id != incoming.id
            if container.isHidden != hidden {
                container.isHidden = hidden
                log("force.page.\\(hidden ? "hide" : "show")")
            }
        }
        CATransaction.commit()''')
open(p,'w').write(s)
print("batch4b applied")
