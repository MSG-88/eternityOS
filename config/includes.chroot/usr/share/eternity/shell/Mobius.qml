import QtQuick

// The Möbius mark: 48 baked frames (branding/render.py --atlas, 256 px each, 8 per row),
// played on the GPU; one loop per 4 s like the design's travelling light (0.22 loops/s).
Item {
    id: root
    property real size: 176
    property bool animated: true
    property real speed: 1.0
    width: size; height: size
    AnimatedSprite {
        anchors.fill: parent
        source: Qt.resolvedUrl("assets/mobius-atlas.png")
        frameWidth: 256; frameHeight: 256
        frameCount: 48; frameRate: 12 * root.speed
        running: root.animated
        interpolate: false
        smooth: true
    }
}
