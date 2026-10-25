import QtQuick

// Nocturne toggle (38 x 22, accent when on).
Item {
    id: root
    property real k: 1
    property bool on: false
    property bool enabled: true
    signal toggled(bool on)
    width: 38 * k; height: 22 * k
    opacity: enabled ? 1 : 0.45
    Rectangle { anchors.fill: parent; radius: height / 2; color: root.on ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.15) : "transparent"; border.width: 1; border.color: root.on ? Theme.accent : Theme.n700
        Rectangle { x: root.on ? 19 * root.k : 3 * root.k; y: 3 * root.k; width: 14 * root.k; height: 14 * root.k; radius: 7 * root.k; color: root.on ? Theme.accent : Theme.n600
                    Behavior on x { NumberAnimation { duration: Theme.reduced ? 0 : 160; easing.type: Easing.OutCubic } } } }
    MouseArea { anchors.fill: parent; enabled: root.enabled; onClicked: root.toggled(!root.on) }
}
