import QtQuick

// The status strip's content (design: 44 px high, padding 0 28, Inter 500 13, neutral-400):
// mark 20 + wordmark 11/0.2em | clock (text colour, tabular) | "● live · N ms", AI, network, battery.
Item {
    id: root
    property real k: 1
    property real screenWidth: 1920
    property var state: Daemon.state
    property var metrics: Daemon.metrics
    property bool connected: Daemon.connected
    width: screenWidth
    height: Theme.stripHeight * k

    readonly property string clockText: (state && state.clock) ? state.clock : clock.timeText
    readonly property string latencyText: (metrics && metrics.latency_ms !== undefined && metrics.latency_ms !== null) ? Math.round(metrics.latency_ms) + " ms" : "\u2014"
    readonly property string aiText: (state && state.ai && state.ai.label) ? ((metrics && metrics.ai_tps) ? ("~" + Math.round(metrics.ai_tps) + " tok/s") : state.ai.label) : "\u2014"
    readonly property string netText: (state && state.network) ? state.network : "\u2014"
    readonly property string batteryText: (state && state.battery && state.battery.percent !== undefined) ? (state.battery.percent + "%") : "\u2014"

    SystemClockFallback { id: clock }

    Row {
        id: left
        anchors.left: parent.left; anchors.leftMargin: 28 * root.k
        height: parent.height
        spacing: 10 * root.k
        Mobius { id: mark; size: 20 * root.k; animated: !Theme.reduced; speed: 0.5; y: (parent.height - height) / 2 }
        Wordmark { size: 11 * root.k; tracking: 0.2; color: Theme.text; height: implicitHeight; y: (parent.height - height) / 2 }
    }
    Text {
        id: clockLabel
        anchors.centerIn: parent
        text: root.clockText
        color: Theme.text
        font.family: Theme.body; font.pixelSize: 13 * root.k; font.weight: Font.Medium
        font.features: ({ "tnum": 1 })
    }
    Row {
        id: right
        anchors.right: parent.right; anchors.rightMargin: 28 * root.k
        height: parent.height
        spacing: 22 * root.k
        Row {
            id: latency
            spacing: 6 * root.k
            height: parent.height
            Text { text: "\u25cf"; color: Theme.accent; font.pixelSize: 13 * root.k; font.family: Theme.body; y: (parent.height - height) / 2 }
            Text { id: latencyLabel; text: "live \u00b7 " + root.latencyText; color: Theme.n400; font.family: Theme.body; font.pixelSize: 13 * root.k; font.weight: Font.Medium; font.features: ({ "tnum": 1 }); y: (parent.height - height) / 2 }
        }
        Text { id: ai; text: root.aiText; color: Theme.n400; font.family: Theme.body; font.pixelSize: 13 * root.k; font.weight: Font.Medium; y: (parent.height - height) / 2 }
        Text { id: net; text: root.netText; color: Theme.n400; font.family: Theme.body; font.pixelSize: 13 * root.k; font.weight: Font.Medium; y: (parent.height - height) / 2 }
        Text { id: battery; text: root.batteryText; color: Theme.n400; font.family: Theme.body; font.pixelSize: 13 * root.k; font.weight: Font.Medium; font.features: ({ "tnum": 1 }); y: (parent.height - height) / 2 }
    }

    function geometry() {
        function g(item, label) { const p = item.mapToItem(root, 0, 0); return [p.x, p.y, item.width, item.height, label === undefined ? "" : label]; }
        return { strip: [0, 0, root.width, root.height, ""], mark: g(mark), clock: g(clockLabel, root.clockText),
                 latency: g(latency, root.latencyText), ai: g(ai, root.aiText), net: g(net, root.netText), battery: g(battery, root.batteryText) };
    }
}
