import QtQuick

// Nocturne slider (design: 240 x 2 track in neutral-800, accent fill, 14 px accent-300 knob).
Item {
    id: root
    property real k: 1
    property real value: 0.5          // 0..1
    property int steps: 0             // 0 = continuous
    property bool enabled: true
    signal changed(real value)
    width: 240 * k; height: 16 * k
    opacity: enabled ? 1 : 0.45
    Rectangle { id: track; x: 0; y: 7 * root.k; width: 240 * root.k; height: Math.max(2, 2 * root.k); radius: height / 2; color: Theme.n800
        Rectangle { width: Math.max(0, Math.min(1, root.value)) * parent.width; height: parent.height; color: Theme.accent }
        Rectangle { x: Math.max(0, Math.min(1, root.value)) * parent.width - 7 * root.k; y: -6 * root.k; width: 14 * root.k; height: 14 * root.k; radius: 7 * root.k; color: Theme.accent300 } }
    MouseArea {
        anchors.fill: parent; enabled: root.enabled
        function set(mx) { let v = Math.max(0, Math.min(1, mx / track.width)); if (root.steps > 0) v = Math.round(v * root.steps) / root.steps; root.value = v; root.changed(v); }
        onPressed: mouse => set(mouse.x)
        onPositionChanged: mouse => { if (pressed) set(mouse.x); }
    }
}
