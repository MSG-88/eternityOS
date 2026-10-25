import QtQuick
import Quickshell

// Settings as a normal window (class eternity-settings): shown by the daemon's settings.show event.
Scope {
    id: root
    property bool shown: false
    FloatingWindow {
        id: win
        visible: root.shown
        title: "Settings \u00b7 Eternity"
        implicitWidth: Math.round(1100 * k); implicitHeight: Math.round(720 * k)
        color: Theme.bg
        readonly property real k: Geometry.k(1920, 1080) * 0.8
        SettingsContent { anchors.fill: parent; k: win.k * 1.25 }
        onVisibleChanged: if (!visible) root.shown = false
    }
    Connections { target: Daemon; function onEvent(name, data) { if (name === "settings.show") root.shown = true; } }
}
