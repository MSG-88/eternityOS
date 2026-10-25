import QtQuick

// HUD frame (live design): corner brackets (22 px legs, 1.5 px) that draw in, faint guide lines
// at 22 %, one scan beam, and a decoding Michroma label 20 px above. All in design px x k.
Item {
    id: root
    property real k: 1
    property string label: ""
    property color lineColor: Theme.n500
    property bool animated: !Theme.reduced
    property real progress: animated ? 0 : 1      // 0..1 draw-in
    property real scan: animated ? 0 : 1
    readonly property real legLen: 22 * k
    readonly property real thick: 1.5 * k
    property string shown: label

    function corner(cx, cy, sx, sy) { return { x: cx, y: cy, sx: sx, sy: sy }; }
    readonly property var corners: [corner(0, 0, 1, 1), corner(width, 0, -1, 1), corner(0, height, 1, -1), corner(width, height, -1, -1)]

    Repeater {
        model: root.corners
        Item {
            required property var modelData
            // vertical leg
            Rectangle { x: modelData.sx > 0 ? modelData.x : modelData.x - root.thick; y: modelData.sy > 0 ? modelData.y : modelData.y - root.legLen * root.progress
                        width: root.thick; height: root.legLen * root.progress; color: root.lineColor }
            // horizontal leg
            Rectangle { x: modelData.sx > 0 ? modelData.x : modelData.x - root.legLen * root.progress; y: modelData.sy > 0 ? modelData.y : modelData.y - root.thick
                        width: root.legLen * root.progress; height: root.thick; color: root.lineColor }
        }
    }
    Rectangle { id: leg; visible: false; width: root.legLen; height: root.thick }   // measured by the harness
    Rectangle { x: root.legLen + 10 * root.k; y: 0; width: (root.width - 2 * root.legLen - 20 * root.k) * root.progress; height: Math.max(1, root.k); color: root.lineColor; opacity: 0.22 }
    Rectangle { x: root.width - root.legLen - 10 * root.k - width; y: root.height - height; width: (root.width - 2 * root.legLen - 20 * root.k) * root.progress; height: Math.max(1, root.k); color: root.lineColor; opacity: 0.22 }
    // scan beam: a fade rule in accent-300 sweeping top to bottom once
    Rectangle {
        x: 0; width: root.width; height: Math.max(1, root.k)
        y: root.scan * root.height
        visible: root.scan > 0 && root.scan < 1
        opacity: 0.9 * (1 - root.scan * 0.6)
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: "transparent" }
            GradientStop { position: Math.min(0.49, 48 * root.k / Math.max(1, root.width)); color: Theme.accent300 }
            GradientStop { position: Math.max(0.51, 1 - 48 * root.k / Math.max(1, root.width)); color: Theme.accent300 }
            GradientStop { position: 1; color: "transparent" }
        }
    }
    Text {
        id: labelText
        visible: root.label !== ""
        x: root.legLen + 10 * root.k; y: -20 * root.k
        text: root.shown
        color: root.lineColor
        font.family: Theme.tech; font.pixelSize: 10 * root.k; font.letterSpacing: 0.24 * 10 * root.k
    }
    // decode: resolves left to right from a glyph pool at decodeCps; only runs for ~0.35 s per label
    property real decode: animated ? 0 : 1
    readonly property string pool: "0123456789ABCDEF<>/|"
    onDecodeChanged: {
        if (label === "") return;
        let out = "";
        for (let i = 0; i < label.length; i++) {
            const ch = label[i];
            const p = Math.max(0, Math.min(1, (decode * (label.length * 0.035 + 0.35) - i * 0.035) / 0.35));
            out += (p >= 1 || ch === " " || ch === "\u00b7") ? ch : (p > 0 ? pool[(Math.floor(decode * 100) + i * 7) % pool.length] : " ");
        }
        shown = out;
    }
    ParallelAnimation {
        running: root.animated
        NumberAnimation { target: root; property: "progress"; from: 0; to: 1; duration: Theme.drawMs; easing.type: Easing.InOutSine }
        NumberAnimation { target: root; property: "scan"; from: 0; to: 1; duration: Theme.drawMs + 150; easing.type: Easing.InOutSine }
        NumberAnimation { target: root; property: "decode"; from: 0; to: 1; duration: Math.round((root.label.length * 35 + 350)) }
    }
    function geometry() { return { hud: [x, y, width, height, label], hudleg: [0, 0, leg.width, leg.height, ""] }; }
}
