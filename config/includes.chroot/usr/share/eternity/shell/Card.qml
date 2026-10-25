import QtQuick

// Nocturne card (design: 300 px wide, radius 8, surface, shadow-sm = 1 px neutral-800 ring):
// kicker 10/0.1em accent uppercase, title 17/500, body 13 at 80 %, meta 11 at 50 %.
Rectangle {
    id: root
    property real k: 1
    property string kicker
    property string title
    property string body
    property string meta
    width: 300 * k
    height: col.implicitHeight + 2 * pad
    radius: Theme.radiusMd * k
    color: Theme.surface
    border.width: Math.max(1, Math.round(k)); border.color: Theme.n800
    readonly property real pad: 8.4 * k
    Column {
        id: col
        x: root.pad; y: root.pad
        width: root.width - 2 * root.pad
        spacing: 5.6 * root.k
        Text { text: root.kicker.toUpperCase(); color: Theme.accent; font.family: Theme.body; font.pixelSize: 10 * root.k; font.letterSpacing: 1 * root.k; visible: text !== "" }
        Text { text: root.title; color: Theme.text; font.family: Theme.body; font.pixelSize: 17 * root.k; font.weight: Font.Medium; width: parent.width; elide: Text.ElideRight; visible: text !== "" }
        Text { text: root.body; color: Theme.text; opacity: 0.8; font.family: Theme.body; font.pixelSize: 13 * root.k; width: parent.width; wrapMode: Text.WordWrap; maximumLineCount: 3; elide: Text.ElideRight; visible: text !== "" }
        Text { text: root.meta; color: Theme.text; opacity: 0.5; font.family: Theme.body; font.pixelSize: 11 * root.k; visible: text !== "" }
    }
}
