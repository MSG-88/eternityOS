import QtQuick
import QtQuick.Shapes

// The presence desktop (design scene 04): vignette ground, the core at the centre, the orbit
// (guide circle r 400, accent arc), four cards on a 440x270 ellipse at -90/0/90/180 (+2.5 deg/s),
// the caption at y 900 and the HUD frame. With windows on the workspace the cards hide and
// the core moves to the Files-scene placement (1600, 540, s 0.38).
Item {
    id: root
    property real k: 1
    property var cards: Daemon.cards
    property string windowState: "empty"      // "empty" | "windows"
    property bool answering: false            // an answer is on screen: everything slides left, the right column is the answer's
    property real cx: answering ? 640 : 960    // orbit centre x (design px)
    Behavior on cx { NumberAnimation { duration: Theme.enterMs + 300; easing.type: Easing.InOutCubic } }
    property bool animated: !Theme.reduced
    property bool dimmed: false               // while an answer streams
    property real rot: 0
    readonly property bool cardsVisible: windowState === "empty"
    readonly property real coreX: answering ? 640 : (windowState === "empty" ? 960 : 1600)
    readonly property real coreY: 540
    readonly property real coreS: answering ? 0.42 : (windowState === "empty" ? 0.5 : 0.38)

    // ground: the design's vignette and the glow that follows the core
    Rectangle { anchors.fill: parent; color: Theme.bg }
    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeWidth: 0
            fillGradient: RadialGradient {
                centerX: root.width * 0.5; centerY: root.height * 0.45; focalX: centerX; focalY: centerY
                centerRadius: Math.max(root.width, root.height) * 0.7
                GradientStop { position: 0; color: "#1b1e31" }
                GradientStop { position: 0.6; color: Theme.bg }
                GradientStop { position: 1; color: "#121421" }
            }
            PathLine { x: root.width; y: 0 } PathLine { x: root.width; y: root.height } PathLine { x: 0; y: root.height } PathLine { x: 0; y: 0 }
        }
    }

    Hud { id: hud; k: root.k; x: 56 * k; y: 112 * k; width: 1808 * k; height: 812 * k; label: "HOME \u00b7 ORBIT \u00b7 " + (root.cards ? root.cards.length : 0) + " ACTIVE"; lineColor: Theme.n700; visible: root.cardsVisible; animated: root.animated; opacity: root.dimmed ? 0.1 : 1 }

    // orbit guides
    Shape {
        id: guide
        visible: root.cardsVisible
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: Theme.n700; strokeWidth: Math.max(1, root.k); fillColor: "transparent"
            strokeStyle: ShapePath.DashLine; dashPattern: [0.5, 2.5]
            PathAngleArc { centerX: root.cx * root.k; centerY: 540 * root.k; radiusX: 400 * root.k; radiusY: 400 * root.k; startAngle: 0; sweepAngle: 360 }
        }
        ShapePath {
            strokeColor: Theme.accent; strokeWidth: 1.5 * root.k; fillColor: "transparent"; capStyle: ShapePath.RoundCap
            PathAngleArc { centerX: root.cx * root.k; centerY: 540 * root.k; radiusX: 400 * root.k; radiusY: 400 * root.k; startAngle: -90 + root.rot * 1.4; sweepAngle: 0.18 * 360 }
        }
        opacity: 0.6
    }

    Core { id: core; k: root.k; s: root.coreS; animated: root.animated
           x: root.coreX * root.k - width / 2; y: root.coreY * root.k - height / 2
           Behavior on x { NumberAnimation { duration: Theme.enterMs + 300; easing.type: Easing.InOutCubic } }
           Behavior on s { NumberAnimation { duration: Theme.enterMs + 300; easing.type: Easing.InOutCubic } } }

    Repeater {
        id: orbit
        model: root.cards
        Card {
            required property var modelData
            required property int index
            k: root.k
            kicker: modelData.kicker || ""; title: modelData.title || ""; body: modelData.body || ""; meta: modelData.meta || ""
            readonly property real angle: ([-90, 0, 90, 180][index % 4] + Math.floor(index / 4) * 45 + root.rot) * Math.PI / 180
            x: root.cx * root.k + Math.cos(angle) * Theme.orbit[0] * root.k - 150 * root.k
            y: 540 * root.k + Math.sin(angle) * Theme.orbit[1] * root.k - 60 * root.k
            visible: root.cardsVisible
            opacity: (root.dimmed && index !== 0) ? 0.1 : 1
            Behavior on opacity { NumberAnimation { duration: Theme.enterMs } }
        }
    }
    NumberAnimation on rot { running: root.animated && root.cardsVisible; loops: Animation.Infinite; from: 0; to: 360; duration: 144000 }

    Text {
        id: caption
        visible: root.cardsVisible
        text: "Everything stays in orbit \u2014 Eternity keeps what matters closest."
        color: Theme.n500; font.family: Theme.body; font.pixelSize: 15 * root.k
        anchors.horizontalCenter: parent.horizontalCenter; y: 900 * root.k
        opacity: root.dimmed ? 0 : 1
    }
    Sweep { id: sweep; k: root.k }
    function playSweep() { sweep.play(); }

    function geometry() {
        const out = { core: [root.coreX * root.k - 300 * root.k * root.coreS, root.coreY * root.k - 300 * root.k * root.coreS, 600 * root.k * root.coreS, 600 * root.k * root.coreS, ""],
                      caption: [caption.x, caption.y, caption.width, caption.height, caption.text], cards_visible: root.cardsVisible };
        const h = hud.geometry(); out.hud = h.hud; out.hud[0] = hud.x; out.hud[1] = hud.y; out.hudleg = h.hudleg;
        out["cx"] = [root.cx * root.k, 540 * root.k, 0, 0, root.answering ? "answering" : ""];
        for (let i = 0; i < orbit.count; i++) { const c = orbit.itemAt(i); if (c) out["card" + i] = [c.x, c.y, c.width, c.height, c.kicker]; }
        return out;
    }
}
