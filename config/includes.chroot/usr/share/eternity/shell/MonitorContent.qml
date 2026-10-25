import QtQuick
import QtQuick.Shapes

// System monitor (design scene 08): four 400-wide panels at (180,220)/(1340,220)/(180,680)/(1340,680)
// with kicker, value and a 400x70 sparkline; a 300 ring at (960,560) whose accent arc is the CPU
// load; the status line at y 880. Honest sources: AI shows tok/s of the last answer or "idle", "NPU"
// only when an accel device exists, latency is the shell's own measurement or a dash.
Item {
    id: root
    property real k: 1
    property var metrics: Daemon.metrics
    property var history: ({})
    property bool accel: false
    readonly property var series: history && history.series ? history.series : ({})
    readonly property real cpu: (metrics && metrics.cpu !== null && metrics.cpu !== undefined) ? metrics.cpu : 0
    readonly property bool hasCpu: metrics && metrics.cpu !== null && metrics.cpu !== undefined
    readonly property var labels: ["CPU", accel ? "NPU" : "AI", "Memory", "Input latency"]
    readonly property var values: [hasCpu ? Math.round(cpu) + "%" : "\u2014",
                                   accel ? "\u2014" : ((metrics && metrics.ai_tps) ? Math.round(metrics.ai_tps) + " tok/s" : "idle"),
                                   (metrics && metrics.mem_gb !== null && metrics.mem_gb !== undefined) ? Number(metrics.mem_gb).toFixed(1) + " GB" : "\u2014",
                                   (metrics && metrics.latency_ms !== null && metrics.latency_ms !== undefined) ? Math.round(metrics.latency_ms) + " ms" : "\u2014"]
    readonly property var seriesKeys: ["cpu", "ai_tps", "mem_gb", "latency_ms"]
    readonly property var maxes: [100, 300, 16, 50]
    readonly property var positions: [[180, 220], [1340, 220], [180, 680], [1340, 680]]
    readonly property int dropped: (metrics && metrics.dropped_frames) ? metrics.dropped_frames : 0

    Rectangle { anchors.fill: parent; color: Theme.bg }
    Shape {   // the ring: track + accent arc (CPU load)
        id: ring
        x: 960 * root.k - 300 * root.k; y: 560 * root.k - 300 * root.k; width: 600 * root.k; height: 600 * root.k
        preferredRendererType: Shape.CurveRenderer
        ShapePath { strokeColor: Theme.n800; strokeWidth: Math.max(1, root.k); fillColor: "transparent"
            PathAngleArc { centerX: 300 * root.k; centerY: 300 * root.k; radiusX: 300 * root.k; radiusY: 300 * root.k; startAngle: 0; sweepAngle: 360 } }
        ShapePath { strokeColor: Theme.accent; strokeWidth: 3 * root.k; fillColor: "transparent"; capStyle: ShapePath.RoundCap
            PathAngleArc { centerX: 300 * root.k; centerY: 300 * root.k; radiusX: 300 * root.k; radiusY: 300 * root.k; startAngle: -90; sweepAngle: Math.max(1, Math.min(100, root.cpu)) * 3.6 } }
        opacity: 0.8
    }
    Repeater {
        id: panels
        model: 4
        Item {
            required property int index
            x: root.positions[index][0] * root.k; y: root.positions[index][1] * root.k
            width: 400 * root.k; height: 130 * root.k
            Text { id: kick; text: root.labels[index].toUpperCase(); color: Theme.n500; font.family: Theme.body; font.pixelSize: 11 * root.k; font.weight: Font.Medium; font.letterSpacing: 1.1 * root.k; y: 12 * root.k }
            Text { id: val; anchors.right: parent.right; y: 0; text: root.values[index]; color: Theme.text; font.family: Theme.body; font.pixelSize: 30 * root.k; font.weight: Font.Medium; font.features: ({ "tnum": 1 }) }
            Spark { id: spark; y: 48 * root.k; k: root.k; values: root.series[root.seriesKeys[index]] || []; maxValue: root.maxes[index]; color: index === 1 ? Theme.accent : Theme.n400 }
            Rectangle { y: 128 * root.k; width: parent.width; height: Math.max(1, root.k)
                gradient: Gradient { orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: "transparent" } GradientStop { position: 0.12; color: Qt.rgba(Theme.text.r, Theme.text.g, Theme.text.b, 0.14) }
                    GradientStop { position: 0.88; color: Qt.rgba(Theme.text.r, Theme.text.g, Theme.text.b, 0.14) } GradientStop { position: 1; color: "transparent" } } }
            function geometry() { return { panel: [x, y, width, height, root.labels[index]], spark: [x + spark.x, y + spark.y, spark.width, spark.height, ""], value: [x + val.x, y + val.y, val.width, val.height, val.text] }; }
        }
    }
    Text {
        id: status
        anchors.horizontalCenter: parent.horizontalCenter; y: 880 * root.k
        text: "CPU LOAD \u00b7 " + (root.hasCpu ? Math.round(root.cpu) + "%" : "\u2014") + " \u00b7 1 HZ SAMPLING \u00b7 " + root.dropped + " DROPPED FRAMES"
        color: Theme.n500; font.family: Theme.body; font.pixelSize: 13 * root.k; font.letterSpacing: 1.3 * root.k
    }
    function refresh() { Daemon.call("metrics.history", {}, (r, e) => { if (r) { root.history = r; root.accel = !!r.accel; } }); }
    Timer { interval: 1000; running: root.visible && Daemon.connected; repeat: true; onTriggered: root.refresh() }
    Component.onCompleted: if (Daemon.connected) refresh()
    function geometry() {
        const out = { ring: [ring.x, ring.y, ring.width, ring.height, ""], status: [status.x, status.y, status.width, status.height, status.text] };
        for (let i = 0; i < panels.count; i++) { const p = panels.itemAt(i); if (p) { const g = p.geometry(); out["panel" + i] = g.panel; out["spark" + i] = g.spark; out["value" + i] = g.value; } }
        return out;
    }
    function flags() { return { labels: root.labels, npu: root.accel }; }
}
