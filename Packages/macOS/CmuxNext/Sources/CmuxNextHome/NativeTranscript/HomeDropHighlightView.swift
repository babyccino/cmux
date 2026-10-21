import AppKit
import CmuxNextDesign

/// Home's drop highlight: while a drag that the composer takes is over the
/// pane (the transcript, the header, the field, or the conversation list
/// beside it), the whole pane shows the theme's focus ring as a rounded
/// outline over a faint tint of it, the border-only look of the panes' own
/// drop outline. Drawn only; it never takes a click or a drag.
final class HomeDropHighlightView: NSView {
    static let inset: CGFloat = 6
    static let cornerRadius: CGFloat = 12
    static let lineWidth: CGFloat = 2
    static let fillAlpha: CGFloat = 0.06

    private(set) var isShowing = false

    override init(frame: NSRect) {
        super.init(frame: frame)
        wantsLayer = true
        layer?.cornerRadius = Self.cornerRadius
        layer?.borderWidth = Self.lineWidth
        isHidden = true
        alphaValue = 0
        setAccessibilityElement(false)
        applyTheme()
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) { nil }

    nonisolated override var isFlipped: Bool { true }
    override func hitTest(_ point: NSPoint) -> NSView? { nil }

    override func viewDidChangeEffectiveAppearance() {
        super.viewDidChangeEffectiveAppearance()
        applyTheme()
    }

    func applyTheme() {
        performWithTheme {
            layer?.borderColor = Palette.focusRing.cgColor
            layer?.backgroundColor = Palette.focusRing.withAlphaComponent(Self.fillAlpha).cgColor
        }
    }

    /// Fades in or out (Motion.home: no animation at all when motion is off; the end state is set
    /// in this frame either way).
    func show(_ shown: Bool) {
        guard shown != isShowing else { return }
        isShowing = shown
        if shown {
            applyTheme()
            isHidden = false
        }
        Motion.home.animate(shown ? .fadeIn : .fadeOut, in: self, { self.animator().alphaValue = shown ? 1 : 0 }, completion: { [weak self] in
            guard let self, !self.isShowing else { return }
            self.isHidden = true
        })
    }
}
