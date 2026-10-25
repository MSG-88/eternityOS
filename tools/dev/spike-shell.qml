import QtQuick
import Quickshell
ShellRoot {
    FloatingWindow {
        id: w
        implicitWidth: 400; implicitHeight: 200
        color: "#161826"
        Item { id: root; anchors.fill: parent
        Rectangle { anchors.centerIn: parent; width: 120; height: 120; radius: 60; color: "transparent"; border.color: "#9184d9"; border.width: 2
            Text { anchors.centerIn: parent; text: "8"; color: "#e9e9ed"; font.pixelSize: 48 } } }
        Timer { interval: 800; running: true; onTriggered: { root.grabToImage(function(r){ r.saveToFile("/tmp/e8qs/shot.png"); Qt.quit(); }); } }
    }
}
