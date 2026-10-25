import QtQuick

// The window ring (Super+Tab): the ring over the open windows; Enter/release focuses the selection.
RingContent {
    id: root
    property var windows: []       // [{id, title, app}] (harness injects; the shell reads Hyprland.toplevels)
    items: windows.map(w => ({ id: w.id, label: w.title || w.app || "window", sub: w.app || "" }))
    signal focusRequested(var id)
    onActivated: it => { root.focusRequested(it.id); root.closed(); }
}
