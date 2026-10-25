import QtQuick
import Quickshell
import Quickshell.Wayland

// Notification cards and the OSD on the panel screen: a top-right surface for the stack and a
// bottom-centred one for the OSD (no exclusive zones, no keyboard focus).
Scope {
    id: root
    required property var screen
    readonly property real k: Geometry.forScreen(screen)
    readonly property bool panel: Geometry.isPanel(screen ? screen.name : "", Quickshell.screens.map(s => s.name))
    PanelWindow {
        screen: root.screen
        visible: root.panel && Notifications.visible.length > 0
        anchors { top: true; right: true }
        implicitWidth: Math.round((300 + 56) * root.k)
        implicitHeight: Math.round(Math.min(screen.height * 0.8, stack.childrenRect.height + 80 * root.k))
        exclusionMode: ExclusionMode.Ignore
        color: "transparent"
        WlrLayershell.namespace: "eternity-notify"
        WlrLayershell.layer: WlrLayer.Overlay
        NotifyStack { id: stack; k: root.k; screenWidth: parent.width; height: parent.height }
    }
    PanelWindow {
        screen: root.screen
        visible: root.panel && osd.shown
        anchors { bottom: true }
        margins { bottom: Math.round((1080 - 900 - 40) * root.k) }
        implicitWidth: Math.round(300 * root.k); implicitHeight: Math.round(48 * root.k)
        exclusionMode: ExclusionMode.Ignore
        color: "transparent"
        WlrLayershell.namespace: "eternity-osd"
        WlrLayershell.layer: WlrLayer.Overlay
        Osd { id: osd; k: root.k; anchors.centerIn: parent }
    }
    Connections { target: Daemon; function onEvent(name, data) { if (name === "osd" && root.panel) osd.show(data.kind, data.level, data.label); } }
}
