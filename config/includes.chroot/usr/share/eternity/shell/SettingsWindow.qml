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
        implicitWidth: 1100; implicitHeight: 720
        color: Theme.bg
        readonly property real k: Geometry.k(win.width, win.height)        // the design's 1920x1080 geometry scaled to this window
        SettingsContent { anchors.fill: parent; k: win.k }
        onVisibleChanged: if (!visible) root.shown = false
    }
    Connections { target: Daemon; function onEvent(name, data) { if (name === "settings.show") root.shown = true; } }
}
