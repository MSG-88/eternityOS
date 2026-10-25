import QtQuick

// One Settings row (design: 18 px vertical padding, a fade rule under it, label left, control right).
Item {
    id: root
    property real k: 1
    property string label: ""
    property string hint: ""
    default property alias control: slot.data
    width: parent ? parent.width : 700 * k
    height: Math.max(Math.max(labelCol.implicitHeight, slot.childrenRect.height) + 36 * k, 66 * k)   // uniform rows: the design's tallest control (seg) + 18 px padding
    Column {
        id: labelCol
        anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
        width: parent.width - slot.childrenRect.width - 16 * root.k
        Text { text: root.label; color: Theme.text; font.family: Theme.body; font.pixelSize: 15 * root.k }
        Text { visible: root.hint !== ""; text: root.hint; color: Theme.n500; font.family: Theme.body; font.pixelSize: 12 * root.k; width: parent.width; wrapMode: Text.WordWrap }
    }
    Item { id: slot; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; width: childrenRect.width; height: childrenRect.height }
    Rectangle {   // fade rule
        anchors.bottom: parent.bottom; width: parent.width; height: Math.max(1, root.k)
        gradient: Gradient { orientation: Gradient.Horizontal
            GradientStop { position: 0; color: "transparent" } GradientStop { position: 0.07; color: Qt.rgba(Theme.text.r, Theme.text.g, Theme.text.b, 0.1) }
            GradientStop { position: 0.93; color: Qt.rgba(Theme.text.r, Theme.text.g, Theme.text.b, 0.1) } GradientStop { position: 1; color: "transparent" } }
    }
}
