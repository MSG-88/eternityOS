import QtQuick

// ETERNITY in Michroma with the three-bar E (bars at Michroma's stem weight) and wide tracking.
Item {
    id: root
    property real size: 24            // design px, already multiplied by k by the caller
    property color color: Theme.text
    property real tracking: 0.34      // em
    readonly property real cap: size * 0.72
    readonly property real stem: size * 0.1
    readonly property real ew: size * 0.74
    implicitWidth: ew + size * tracking + word.implicitWidth
    implicitHeight: Math.max(cap, word.implicitHeight)
    Column {
        id: e
        anchors.verticalCenter: parent.verticalCenter
        spacing: (root.cap - 3 * root.stem) / 2
        Repeater { model: 3; Rectangle { width: root.ew; height: root.stem; color: root.color } }
    }
    Text {
        id: word
        anchors.verticalCenter: parent.verticalCenter
        x: root.ew + root.size * root.tracking
        text: "TERNITY"
        color: root.color
        font.family: Theme.tech
        font.pixelSize: root.size
        font.letterSpacing: root.size * root.tracking
    }
}
