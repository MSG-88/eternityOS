import QtQuick

// A notification card (Nocturne card, 300 wide): kicker = app, title = summary, body, actions
// as ghost buttons; slides in from the right over enterMs; click dismisses.
Rectangle {
    id: root
    property real k: 1
    property var item: ({})
    signal dismissed(var id)
    signal action(var id, var actionId)
    width: 300 * k
    height: col.implicitHeight + 2 * pad
    radius: Theme.radiusMd * k
    color: Theme.surface
    border.width: Math.max(1, Math.round(k)); border.color: item.urgency === "critical" || item.urgency === 2 ? Theme.accent : Theme.n800
    readonly property real pad: 8.4 * k
    opacity: 0; x: 40 * k
    Component.onCompleted: { enter.start(); }
    ParallelAnimation { id: enter; NumberAnimation { target: root; property: "opacity"; to: 1; duration: Theme.reduced ? 0 : Theme.enterMs; easing.type: Easing.OutCubic }
                        NumberAnimation { target: root; property: "x"; to: 0; duration: Theme.reduced ? 0 : Theme.enterMs; easing.type: Easing.OutCubic } }
    Column {
        id: col
        x: root.pad; y: root.pad; width: root.width - 2 * root.pad
        spacing: 5.6 * root.k
        Text { id: kicker; text: String(root.item.app || "").toUpperCase(); color: Theme.accent; font.family: Theme.body; font.pixelSize: 10 * root.k; font.letterSpacing: 1 * root.k; visible: text !== "" }
        Text { text: root.item.summary || ""; color: Theme.text; font.family: Theme.body; font.pixelSize: 17 * root.k; font.weight: Font.Medium; width: parent.width; elide: Text.ElideRight; visible: text !== "" }
        Text { text: root.item.body || ""; color: Theme.text; opacity: 0.8; font.family: Theme.body; font.pixelSize: 13 * root.k; width: parent.width; wrapMode: Text.WordWrap; maximumLineCount: 4; elide: Text.ElideRight; visible: text !== "" }
        Row {
            spacing: 8 * root.k
            visible: (root.item.actions || []).length > 0
            Repeater {
                model: root.item.actions || []
                Rectangle {
                    required property var modelData
                    width: aLabel.implicitWidth + 20 * root.k; height: 28 * root.k; radius: Theme.radiusMd * root.k; color: "transparent"; border.width: 1; border.color: Theme.accent
                    Text { id: aLabel; anchors.centerIn: parent; text: modelData.text || modelData.id; color: Theme.accent; font.family: Theme.body; font.pixelSize: 12 * root.k; font.weight: Font.Medium }
                    MouseArea { anchors.fill: parent; onClicked: root.action(root.item.id, modelData.id) }
                }
            }
        }
    }
    MouseArea { anchors.fill: parent; z: -1; onClicked: root.dismissed(root.item.id) }
    function geometry() { return [root.x, root.y, root.width, root.height, kicker.text]; }
}
