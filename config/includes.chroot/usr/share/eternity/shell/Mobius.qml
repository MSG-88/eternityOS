import QtQuick

// The Möbius mark: 48 baked frames (branding/render.py --atlas, 256 px each, 8 per row), one
// loop per 4 s like the design's travelling light (0.22 loops/s). The atlas is shown through a
// clipping box and stepped by a 12 fps timer: AnimatedSprite needs the shader sprite engine and
// draws nothing while running on the software scene graph the session uses without a GPU
// (build 13 on Hyper-V: faint core; the offscreen harness renders it stopped, so it passed).
Item {
    id: root
    property real size: 176
    property bool animated: true
    property real speed: 1.0
    property int frame: 0
    width: size; height: size
    clip: true
    Image {
        source: Qt.resolvedUrl("assets/mobius-atlas.png")
        width: 8 * root.size; height: 6 * root.size
        x: -(root.frame % 8) * root.size
        y: -Math.floor(root.frame / 8) * root.size
        smooth: true
        asynchronous: true
    }
    Timer {
        interval: Math.max(16, Math.round(1000 / (12 * Math.max(0.1, root.speed))))
        running: root.animated; repeat: true
        onTriggered: root.frame = (root.frame + 1) % 48
    }
}
