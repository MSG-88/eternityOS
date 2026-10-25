pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

// Key-to-frame latency: keyPressed() stamps the input, frameSwapped() closes the sample on the
// next presented frame. Keeps the last 60 samples, exposes p95, and writes
// $XDG_RUNTIME_DIR/eternity/latency.json (read by the daemon for the strip and Monitor) at
// most every 2 s. No per-frame work beyond one comparison when a key is pending.
Singleton {
    id: root
    property var samples: []
    property real pendingAt: 0
    property int count: 0
    property real p95: 0
    property real last: 0
    property int dropped: 0
    property bool dirty: false
    readonly property string filePath: (Quickshell.env("XDG_RUNTIME_DIR") || ("/run/user/" + Quickshell.env("UID"))) + "/eternity/latency.json"

    function keyPressed() { if (root.pendingAt === 0) root.pendingAt = Date.now(); }
    function frameSwapped() {
        if (root.pendingAt === 0) return;
        const ms = Date.now() - root.pendingAt;
        root.pendingAt = 0;
        root.record(ms);
    }
    function record(ms) {
        const s = root.samples.slice();
        s.push(ms);
        while (s.length > 60) s.shift();
        root.samples = s;
        root.count = s.length;
        root.last = ms;
        const sorted = s.slice().sort((a, b) => a - b);
        root.p95 = sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * 0.95))];
        root.dirty = true;
    }
    function flush() {
        if (!root.dirty) return;
        root.dirty = false;
        const json = JSON.stringify({ latency_ms: root.p95, last_ms: root.last, samples: root.count, dropped_frames: root.dropped, ts: Date.now() / 1000 });
        writer.command = ["sh", "-c", "mkdir -p \"$(dirname \"$2\")\" && printf '%s' \"$1\" > \"$2\"", "latency", json, root.filePath];
        writer.running = true;
    }
    Process { id: writer }
    Timer { interval: 2000; running: true; repeat: true; onTriggered: root.flush() }
}
