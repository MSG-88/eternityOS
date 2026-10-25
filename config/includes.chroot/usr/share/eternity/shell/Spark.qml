import QtQuick
import QtQuick.Shapes

// A sparkline (design: 400 x 70, 1.5 px line, a 3 px dot at the end): `values` normalised by
// `maxValue` (null values break the line). Rebuilt when the series changes (once per second), not per frame.
Item {
    id: root
    property real k: 1
    property var values: []
    property real maxValue: 100
    property color color: Theme.n400
    width: 400 * k; height: 70 * k
    readonly property var pts: {
        const n = Math.max(2, root.values.length);
        const out = [];
        for (let i = 0; i < root.values.length; i++) {
            const v = root.values[i];
            if (v === null || v === undefined) { out.push(null); continue; }
            out.push({ x: (i / (n - 1)) * root.width, y: root.height - 2 * root.k - Math.max(0, Math.min(1, v / Math.max(1e-6, root.maxValue))) * root.height * 0.9 });
        }
        return out;
    }
    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: root.color; strokeWidth: 1.5 * root.k; fillColor: "transparent"; capStyle: ShapePath.RoundCap
            startX: root.pts.length && root.pts[0] ? root.pts[0].x : 0
            startY: root.pts.length && root.pts[0] ? root.pts[0].y : root.height
            PathPolyline { path: root.pts.filter(p => p !== null).map(p => Qt.point(p.x, p.y)) }
        }
    }
    Rectangle { visible: root.pts.length > 0 && root.pts[root.pts.length - 1] !== null; width: 6 * root.k; height: 6 * root.k; radius: 3 * root.k; color: root.color
                x: (root.pts.length && root.pts[root.pts.length - 1]) ? root.pts[root.pts.length - 1].x - 3 * root.k : 0
                y: (root.pts.length && root.pts[root.pts.length - 1]) ? root.pts[root.pts.length - 1].y - 3 * root.k : 0 }
}
