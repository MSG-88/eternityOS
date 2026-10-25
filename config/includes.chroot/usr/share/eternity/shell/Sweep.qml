import QtQuick

// View-change sweep (live design): a 96 px grid flash (peak 14 %, gone in sweepMs) and a scan
// line travelling top to bottom in sweepMs. Call play(); inert under reduced motion.
Item {
    id: root
    property real k: 1
    anchors.fill: parent
    visible: anim.running
    readonly property int cols: Math.ceil(width / (96 * k)) + 1
    readonly property int rows: Math.ceil(height / (96 * k)) + 1
    Item {
        id: grid
        anchors.fill: parent
        opacity: 0
        Repeater { model: root.cols; Rectangle { required property int index; x: (48 + index * 96) * root.k; width: Math.max(1, root.k); height: root.height; color: Theme.n700 } }
        Repeater { model: root.rows; Rectangle { required property int index; y: (48 + index * 96) * root.k; height: Math.max(1, root.k); width: root.width; color: Theme.n700 } }
    }
    Rectangle {
        id: line
        x: 0; width: root.width; height: Math.max(1, root.k); y: 0; opacity: 0
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: "transparent" }
            GradientStop { position: 0.04; color: Theme.accent300 }
            GradientStop { position: 0.96; color: Theme.accent300 }
            GradientStop { position: 1; color: "transparent" }
        }
    }
    ParallelAnimation {
        id: anim
        SequentialAnimation {
            NumberAnimation { target: grid; property: "opacity"; from: 0; to: 0.14; duration: Theme.sweepMs * 0.12 }
            NumberAnimation { target: grid; property: "opacity"; from: 0.14; to: 0; duration: Theme.sweepMs * 0.88 }
        }
        NumberAnimation { target: line; property: "y"; from: 0; to: root.height; duration: Theme.sweepMs; easing.type: Easing.InOutSine }
        SequentialAnimation {
            PropertyAction { target: line; property: "opacity"; value: 1 }
            PauseAnimation { duration: Theme.sweepMs * 0.75 }
            NumberAnimation { target: line; property: "opacity"; from: 1; to: 0; duration: Theme.sweepMs * 0.25 }
        }
    }
    function play() { if (!Theme.reduced) anim.restart(); }
}
