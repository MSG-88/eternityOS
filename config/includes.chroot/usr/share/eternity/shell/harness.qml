import QtQuick
import Quickshell

// Test harness (tests/host/test_shell_render.sh): loads the shell's content items into a plain
// window of the requested logical size (ETERNITY_HARNESS_W/H), with or without a daemon, and
// writes the geometry dump + screenshot through Dump. Lives next to the shell because Quickshell
// only imports files under its config root. Scenarios: strip, strip100, presence, presence-windows.
ShellRoot {
    id: root
    readonly property int w: parseInt(Quickshell.env("ETERNITY_HARNESS_W") || "1536")
    readonly property int h: parseInt(Quickshell.env("ETERNITY_HARNESS_H") || "864")
    readonly property string scenario: Quickshell.env("ETERNITY_HARNESS_SCENARIO") || "strip"
    readonly property real k: Geometry.k(w, h)
    readonly property bool presence: scenario.indexOf("presence") === 0
    readonly property var designCards: [
        { id: "calendar", kicker: "Calendar", title: "Design review", body: "Today \u00b7 15:00 \u2014 16:00", meta: "with Priya, Ola" },
        { id: "mail", kicker: "Mail", title: "3 new, 1 needs you", body: "Ola: \u201cshell spec v3 is ready for a read\u201d", meta: "summarised" },
        { id: "nowplaying", kicker: "Now playing", title: "Nocturne in E\u266d", body: "Quiet focus \u00b7 42 min left", meta: "" },
        { id: "focus", kicker: "Focus", title: "Writing block until 14:30", body: "Notifications held \u00b7 6 queued", meta: "" }]

    FloatingWindow {
        id: win
        implicitWidth: root.w; implicitHeight: root.h
        color: Theme.bg
        Item {
            id: stage
            anchors.fill: parent
            Rectangle { anchors.fill: parent; color: Theme.bg }
            Loader {
                id: presenceLoader
                anchors.fill: parent
                active: root.presence
                sourceComponent: PresenceContent { k: root.k; cards: root.designCards; animated: false; windowState: root.scenario === "presence-windows" ? "windows" : "empty" }
            }
            StripContent { id: strip; k: root.k; screenWidth: root.w; visible: !root.presence }
        }
        Dump {
            dir: Quickshell.env("ETERNITY_SHELL_DUMP") || ""
            name: root.scenario
            target: stage
            collect: () => ({ screen: [root.w, root.h], k: root.k, scenario: root.scenario, connected: Daemon.connected,
                              items: root.presence ? presenceLoader.item.geometry() : strip.geometry() })
        }
    }
}
