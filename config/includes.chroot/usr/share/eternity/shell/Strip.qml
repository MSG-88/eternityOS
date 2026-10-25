import QtQuick
import Quickshell
import Quickshell.Wayland

// The status strip as a top layer-shell surface with an exclusive zone (the only one).
PanelWindow {
    id: win
    property real k: Geometry.forScreen(screen)
    anchors { top: true; left: true; right: true }
    implicitHeight: Math.round(Theme.stripHeight * k)
    exclusiveZone: implicitHeight
    color: "transparent"
    WlrLayershell.namespace: "eternity-strip"
    WlrLayershell.layer: WlrLayer.Top
    Rectangle { anchors.fill: parent; color: Theme.bg; opacity: 0.72 }
    StripContent { k: win.k; screenWidth: win.width }
}
