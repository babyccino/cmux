import os
os.chdir(os.path.expanduser('~/Code/cmux'))
p='Sources/ContentView.swift'
s=open(p).read()
old='''                    if Self.tmpAppKitWorkspaceHost {
                        TmpWorkspaceAppKitHost(isHidden: !isSelectedWorkspace, content: content)
                    } else {'''
new='''                    if Self.tmpAppKitWorkspaceHost {
                        TmpWorkspaceAppKitHost(isHidden: !isSelectedWorkspace, content: content)
                    } else if TmpSwitchProbe.equatablePages {
                        TmpMountedWorkspacePage(
                            content: content,
                            workspaceIdentity: ObjectIdentifier(tab),
                            isSelected: isSelectedWorkspace,
                            isPresented: isPresentedWorkspace,
                            rightSidebarOwnsInputFocus: fileExplorerState.rightSidebarOwnsInputFocus,
                            isFullScreen: isFullScreen
                        )
                        .equatable()
                        .zIndex(isSelectedWorkspace ? 2 : 0)
                    } else {'''
assert old in s
s=s.replace(old,new)
old='''                        content
                            .opacity(isSelectedWorkspace ? 1 : 0)'''
assert old in s
s=s.replace(old,'''                        content
                            .opacity(isSelectedWorkspace ? 1 : TmpSwitchProbe.hiddenOpacity)''')
s+='''

/// Skips re-evaluating mounted workspaces whose inputs did not change, so a
/// switch only updates the outgoing and incoming pages.
struct TmpMountedWorkspacePage: View, Equatable {
    let content: WorkspaceContentView
    let workspaceIdentity: ObjectIdentifier
    let isSelected: Bool
    let isPresented: Bool
    let rightSidebarOwnsInputFocus: Bool
    let isFullScreen: Bool

    static func == (lhs: Self, rhs: Self) -> Bool {
        lhs.workspaceIdentity == rhs.workspaceIdentity
            && lhs.isSelected == rhs.isSelected
            && lhs.isPresented == rhs.isPresented
            && lhs.rightSidebarOwnsInputFocus == rhs.rightSidebarOwnsInputFocus
            && lhs.isFullScreen == rhs.isFullScreen
    }

    var body: some View {
        content
            .opacity(isSelected ? 1 : TmpSwitchProbe.hiddenOpacity)
            .allowsHitTesting(isSelected)
            .accessibilityHidden(!isSelected)
    }
}
'''
open(p,'w').write(s)
p='Sources/TabManager.swift'
s=open(p).read()
old='''    static let noInteractiveSync = env["CMUX_TMP_NO_INTERACTIVE_SYNC"] == "1"
'''
assert old in s
s=s.replace(old,old+'''    static let equatablePages = env["CMUX_TMP_EQUATABLE"] == "1"
    static let hiddenOpacity: Double = env["CMUX_TMP_NEAR_ZERO_OPACITY"] == "1" ? 0.001 : 0
''')
open(p,'w').write(s)
print("batch2 applied")
p='Sources/ContentView.swift'
s=open(p).read()
old='''        if container.isHidden != isHidden {
            TmpSwitchProbe.log("appkitHost.isHidden=\\(isHidden ? 1 : 0)")
            container.isHidden = isHidden
        }
        container.hostingView?.rootView = rootView(context)'''
assert old in s, 'host'
s=s.replace(old,'''        let hiddenChanged = container.isHidden != isHidden
        if hiddenChanged {
            TmpSwitchProbe.log("appkitHost.isHidden=\\(isHidden ? 1 : 0)")
        }
        if hiddenChanged || !TmpSwitchProbe.lazyAppKitHost {
            container.hostingView?.rootView = rootView(context)
        }
        if hiddenChanged {
            container.isHidden = isHidden
        }''')
open(p,'w').write(s)
p='Sources/TabManager.swift'
s=open(p).read()
old='''    static let equatablePages = env["CMUX_TMP_EQUATABLE"] == "1"
'''
s=s.replace(old,old+'''    static let lazyAppKitHost = env["CMUX_TMP_APPKIT_HOST_LAZY"] == "1"
''')
open(p,'w').write(s)
print("batch2b applied")
