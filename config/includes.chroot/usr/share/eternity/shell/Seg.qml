import QtQuick

// Nocturne segmented control (.seg / .seg-opt): options side by side, the chosen one in accent.
Item {
    id: root
    property real k: 1
    property var options: []       // [{id, label}] or strings
    property string value: ""
    property bool enabled: true
    signal chosen(string id)
    readonly property var opts: options.map(o => typeof o === "string" ? ({ id: o, label: o }) : o)
    width: row.width; height: row.height
    opacity: enabled ? 1 : 0.45
    Rectangle { anchors.fill: parent; radius: Theme.radiusMd * root.k; color: "transparent"; border.width: 1; border.color: Theme.n800 }
    Row {
        id: row
        Repeater {
            model: root.opts
            Rectangle {
                required property var modelData
                required property int index
                readonly property bool on: modelData.id === root.value
                width: segLabel.implicitWidth + 24 * root.k; height: segLabel.implicitHeight + 14 * root.k
                color: "transparent"
                border.width: on ? 1 : 0; border.color: Theme.accent; radius: Theme.radiusMd * root.k
                Rectangle { visible: index > 0; width: 1; height: parent.height; color: Theme.n800 }
                Text { id: segLabel; anchors.centerIn: parent; text: modelData.label; color: on ? Theme.accent : Theme.n400; font.family: Theme.body; font.pixelSize: 13 * root.k }
                MouseArea { anchors.fill: parent; enabled: root.enabled; onClicked: root.chosen(modelData.id) }
            }
        }
    }
}
