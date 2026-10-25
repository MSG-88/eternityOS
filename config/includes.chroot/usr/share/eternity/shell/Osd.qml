import QtQuick

// On-screen display for volume and brightness (design: the Settings slider, 240 x 2, accent fill,
// accent-300 knob) centred at y 900 with the label above; shown for 1.2 s after a change.
Item {
    id: root
    property real k: 1
    property real level: 0
    property string label: ""
    property bool shown: false
    width: 240 * k; height: 40 * k
    opacity: shown ? 1 : 0
    Behavior on opacity { NumberAnimation { duration: Theme.reduced ? 0 : 200 } }
    Text { id: lab; anchors.horizontalCenter: parent.horizontalCenter; y: 0; text: root.label; color: Theme.n500; font.family: Theme.body; font.pixelSize: 12 * root.k; font.features: ({ "tnum": 1 }) }
    Rectangle { id: track; x: 0; y: 28 * root.k; width: 240 * root.k; height: Math.max(2, 2 * root.k); radius: height / 2; color: Theme.n800
        Rectangle { id: fill; x: 0; y: 0; height: parent.height; width: Math.max(0, Math.min(1, root.level)) * parent.width; color: Theme.accent }
        Rectangle { x: fill.width - 7 * root.k; y: -6 * root.k; width: 14 * root.k; height: 14 * root.k; radius: 7 * root.k; color: Theme.accent300 } }
    Timer { id: hide; interval: 1200; onTriggered: root.shown = false }
    function show(kind, level, label) { root.level = level; root.label = label || (kind + " " + Math.round(level * 100) + "%"); root.shown = true; hide.restart(); }
    function geometry() { return { osd: [root.x, root.y + track.y, track.width, track.height, ""], osd_fill: [root.x, root.y + track.y, fill.width, fill.height, ""], osd_label: [root.x + lab.x, root.y + lab.y, lab.width, lab.height, lab.text] }; }
}
