import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Hyprland

// The presence as the background layer of each screen; follows the focused workspace's windows.
PanelWindow {
    id: win
    property real k: Geometry.forScreen(screen)
    anchors { top: true; bottom: true; left: true; right: true }
    exclusionMode: ExclusionMode.Ignore
    color: "transparent"
    WlrLayershell.namespace: "eternity-presence"
    WlrLayershell.layer: WlrLayer.Background
    readonly property bool panel: Geometry.isPanel(screen ? screen.name : "", Quickshell.screens.map(s => s.name))
    visible: panel      // external outputs get the strip and windows only (spec 13.1)
    readonly property bool hasWindows: {
        try { const m = Hyprland.monitorFor(screen); const ws = m ? m.activeWorkspace : null; return ws ? ws.toplevels.values.length > 0 : false; } catch (e) { return false; }
    }
    PresenceContent { id: content; anchors.fill: parent; k: win.k; windowState: win.hasWindows ? "windows" : "empty"; answering: Ask.answering }
    Connections {
        target: Hyprland
        function onFocusedWorkspaceChanged() { Hyprland.refreshToplevels(); content.playSweep(); }
    }
}
