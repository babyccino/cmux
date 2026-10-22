import os
os.chdir(os.path.expanduser('~/Code/cmux'))
p='Sources/Sidebar/AppKitList/SidebarWorkspaceTableController.swift'
s=open(p).read()
old='''        resizeDidEndObserver = NotificationCenter.default.addObserver(
            forName: .cmuxInteractiveGeometryResizeDidEnd,'''
new='''        tmpKeyboardPreviewObserver = NotificationCenter.default.addObserver(
            forName: TmpSwitchProbe.keyboardSelectionPreview,
            object: nil,
            queue: nil
        ) { [weak self] notification in
            MainActor.assumeIsolated {
                guard let self,
                      let workspaceId = notification.userInfo?["workspaceId"] as? UUID,
                      let window = notification.object as? NSWindow,
                      self.containerView?.window === window,
                      let row = self.rows.firstIndex(where: { $0.workspaceId == workspaceId && !$0.isGroupHeader }) else { return }
                self.previewSelection(row: row, modifiers: [], hitView: nil)
                TmpSwitchProbe.log("sidebar.preview")
            }
        }

        resizeDidEndObserver = NotificationCenter.default.addObserver(
            forName: .cmuxInteractiveGeometryResizeDidEnd,'''
assert old in s
s=s.replace(old,new,1)
old='''    private var optimisticallyPaintedRowIds: Set<SidebarWorkspaceRenderItemID> = []
'''
assert old in s
s=s.replace(old,old+'''    private var tmpKeyboardPreviewObserver: NSObjectProtocol?
''',1)
open(p,'w').write(s)

p='Sources/TabManager.swift'
s=open(p).read()
old='''    static let lazyAppKitHost = env["CMUX_TMP_APPKIT_HOST_LAZY"] == "1"
'''
assert old in s
s=s.replace(old,old+'''    static let sidebarPreview = env["CMUX_TMP_SIDEBAR_PREVIEW"] == "1"
    static let keyboardSelectionPreview = Notification.Name("cmux.tmp.keyboardSelectionPreview")
''')
old='''        selectWorkspaceId(
            destinationId,
            notificationDismissalContext: .explicitWorkspaceResume
        )
        if TmpSwitchProbe.forceReveal'''
assert old in s
s=s.replace(old,'''        if TmpSwitchProbe.sidebarPreview {
            NotificationCenter.default.post(
                name: TmpSwitchProbe.keyboardSelectionPreview,
                object: window,
                userInfo: ["workspaceId": destinationId]
            )
        }
        if TmpSwitchProbe.forceReveal, TmpSwitchProbe.forceBeforeSelect, let incoming = tabs.first(where: { $0.id == destinationId }) {
            TmpSwitchProbe.forceSwap(to: incoming, in: tabs)
            CATransaction.flush()
            TmpSwitchProbe.log("preflushed")
        }
        selectWorkspaceId(
            destinationId,
            notificationDismissalContext: .explicitWorkspaceResume
        )
        if TmpSwitchProbe.forceReveal''')
s=s.replace('''    static let sidebarPreview = env["CMUX_TMP_SIDEBAR_PREVIEW"] == "1"
''','''    static let sidebarPreview = env["CMUX_TMP_SIDEBAR_PREVIEW"] == "1"
    static let forceBeforeSelect = env["CMUX_TMP_FORCE_BEFORE_SELECT"] == "1"
''')
open(p,'w').write(s)
print("batch3 applied")
p='Sources/ContentView.swift'
s=open(p).read()
old='''            .opacity(sidebarSelectionState.selection == .tabs ? 1 : 0)
            .allowsHitTesting(sidebarSelectionState.selection == .tabs)'''
assert old in s
s=s.replace(old,'''            .opacity(sidebarSelectionState.selection == .tabs ? 1 : TmpSwitchProbe.hiddenOpacity)
            .allowsHitTesting(sidebarSelectionState.selection == .tabs)''')
open(p,'w').write(s)
print("batch3b applied")
