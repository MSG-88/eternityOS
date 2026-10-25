import QtQuick
import Quickshell

// Test harness (tests/host/test_shell_render.sh): loads the shell's content items into a plain
// window of the requested logical size (ETERNITY_HARNESS_W/H), with or without a daemon, and
// writes the geometry dump + screenshot through Dump. Lives next to the shell because Quickshell
// only imports files under its config root.
ShellRoot {
    id: root
    readonly property int w: parseInt(Quickshell.env("ETERNITY_HARNESS_W") || "1536")
    readonly property int h: parseInt(Quickshell.env("ETERNITY_HARNESS_H") || "864")
    readonly property string scenario: Quickshell.env("ETERNITY_HARNESS_SCENARIO") || "strip"
    readonly property real k: Geometry.k(w, h)

    FloatingWindow {
        id: win
        implicitWidth: root.w; implicitHeight: root.h
        color: Theme.bg
        Item {
            id: stage
            anchors.fill: parent
            Rectangle { anchors.fill: parent; color: Theme.bg }
            StripContent { id: strip; k: root.k; screenWidth: root.w }
        }
        Dump {
            dir: Quickshell.env("ETERNITY_SHELL_DUMP") || ""
            name: root.scenario
            target: stage
            collect: () => ({ screen: [root.w, root.h], k: root.k, scenario: root.scenario, connected: Daemon.connected, items: strip.geometry() })
        }
    }
}
