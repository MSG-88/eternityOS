import QtQuick
import Quickshell

// Monitor as a normal window (class eternity-monitor): shown by the daemon's monitor.show event.
Scope {
    id: root
    property bool shown: false
    FloatingWindow {
        id: win
        visible: root.shown
        title: "Monitor \u00b7 Eternity"
        implicitWidth: Math.round(1536 * 0.75); implicitHeight: Math.round(864 * 0.75)
        color: Theme.bg
        MonitorContent { anchors.fill: parent; k: Geometry.k(win.width, win.height); visible: root.shown }
        onVisibleChanged: if (!visible) root.shown = false
    }
    Connections { target: Daemon; function onEvent(name, data) { if (name === "monitor.show") root.shown = true; } }
}
