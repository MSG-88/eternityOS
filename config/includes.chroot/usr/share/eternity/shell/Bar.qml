import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Hyprland

// Ask Eternity as a layer-shell surface. Idle: a small window holding just the bar (shown on an
// empty workspace, hidden under windows). Active (Super+Space, a click, a consent request): the
// whole screen on the overlay layer with keyboard focus; Esc or a click outside dismisses.
PanelWindow {
    id: win
    property real k: Geometry.forScreen(screen)
    readonly property bool active: content.active
    readonly property bool hasWindows: { try { const ws = Hyprland.focusedWorkspace; return ws ? ws.toplevels.values.length > 0 : false; } catch (e) { return false; } }
    visible: active || !hasWindows
    anchors { left: true; right: true; bottom: true; top: active }
    implicitHeight: active ? screen.height : Math.round((1080 - Theme.bar[1]) * k)
    exclusionMode: ExclusionMode.Ignore
    color: "transparent"
    WlrLayershell.namespace: "eternity-bar"
    WlrLayershell.layer: active ? WlrLayer.Overlay : WlrLayer.Top
    WlrLayershell.keyboardFocus: active ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None
    MouseArea { anchors.fill: parent; enabled: content.active; onClicked: content.dismiss() }
    BarContent {
        id: content
        k: win.k
        width: screen.width; height: screen.height
        // when idle the window only covers the bottom band: shift the content up accordingly
        y: win.active ? 0 : -(screen.height - win.implicitHeight)
    }
}
