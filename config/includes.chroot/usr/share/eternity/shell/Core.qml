import QtQuick
import QtQuick.Shapes

// The presence: four dashed rings, 72 ticks, a breathing glow and the Möbius mark, in a
// 600x600 design box scaled by `s` around its centre. Everything animates through property
// animations on the GPU scene graph; nothing runs per frame in script.
Item {
    id: root
    property real k: 1
    property real s: 0.5
    property real fast: 0
    property real glow: Theme.glow
    property bool animated: !Theme.reduced
    width: 600 * k; height: 600 * k
    scale: s
    transformOrigin: Item.Center

    readonly property var ringR: [92, 134, 176, 214]
    readonly property var ringDash: [0.62, 0.16, 0.3, 0.08]
    readonly property var ringWidth: [1.25, 2.5, 1.25, 1.25]
    readonly property var ringColor: [Theme.accent700, Theme.accent, Theme.accent700, Theme.n600]

    // glow: radial, breathing (energy 0.55 + 0.2 sin(0.9 pi t) in the design)
    Shape {
        id: glowShape
        anchors.fill: parent
        opacity: 0.9
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeWidth: 0
            fillGradient: RadialGradient {
                centerX: 300 * root.k; centerY: 300 * root.k; focalX: centerX; focalY: centerY
                centerRadius: 180 * root.k
                GradientStop { position: 0; color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.28 * 0.65 * root.glow) }
                GradientStop { position: 0.45; color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.08 * root.glow) }
                GradientStop { position: 0.7; color: "transparent" }
            }
            PathAngleArc { centerX: 300 * root.k; centerY: 300 * root.k; radiusX: 180 * root.k; radiusY: 180 * root.k; startAngle: 0; sweepAngle: 360 }
        }
        SequentialAnimation on scale {
            running: root.animated; loops: Animation.Infinite
            NumberAnimation { from: 1.0; to: 1.08; duration: 1100; easing.type: Easing.InOutSine }
            NumberAnimation { from: 1.08; to: 1.0; duration: 1100; easing.type: Easing.InOutSine }
        }
    }

    // ticks: 72 around r 228/234 -> 240, every 6th accent-400, rotating 1.5 deg/s
    Item {
        id: ticks
        anchors.fill: parent
        Repeater {
            model: 72
            Rectangle {
                required property int index
                readonly property bool major: index % 6 === 0
                width: 1.5 * root.k
                height: (major ? 12 : 6) * root.k
                color: major ? Theme.accent400 : Theme.n700
                opacity: major ? 0.9 : 0.55
                x: 300 * root.k - width / 2
                y: 300 * root.k - 240 * root.k
                transform: Rotation { origin.x: 0.75 * root.k; origin.y: 240 * root.k; angle: index * 5 }
            }
        }
        RotationAnimation on rotation { running: root.animated; loops: Animation.Infinite; from: 0; to: 360; duration: 240000 }
    }

    // rings: arcs of dash fraction x 360 deg, round caps, counter-rotating at (10 + 7 i) deg/s
    Repeater {
        model: 4
        Shape {
            id: ring
            required property int index
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            opacity: 1.0
            ShapePath {
                strokeWidth: root.ringWidth[ring.index] * root.k
                strokeColor: root.ringColor[ring.index]
                fillColor: "transparent"
                capStyle: ShapePath.RoundCap
                PathAngleArc {
                    centerX: 300 * root.k; centerY: 300 * root.k
                    radiusX: root.ringR[ring.index] * root.k; radiusY: root.ringR[ring.index] * root.k
                    startAngle: -90; sweepAngle: 360 * root.ringDash[ring.index]
                }
            }
            RotationAnimation on rotation {
                running: root.animated; loops: Animation.Infinite
                from: 0; to: (ring.index % 2 ? -360 : 360); duration: 360000 / (10 + 7 * ring.index)
            }
        }
    }

    Mobius { size: 176 * root.k; anchors.centerIn: parent; animated: root.animated; speed: 1 + root.fast }
}
