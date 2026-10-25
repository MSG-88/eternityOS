import QtQuick
import Quickshell

// Test harness (tests/host/test_shell_render.sh): loads the shell's content items into a plain
// window of the requested logical size (ETERNITY_HARNESS_W/H), with or without a daemon, and
// writes the geometry dump + screenshot through Dump. Lives next to the shell because Quickshell
// only imports files under its config root. Scenarios: strip, strip100, presence, presence-windows, bar, bar-focused, answer, answer-streaming, consent, consent-pin, lock, lock-backoff, lock-pin.
ShellRoot {
    id: root
    readonly property int w: parseInt(Quickshell.env("ETERNITY_HARNESS_W") || "1536")
    readonly property int h: parseInt(Quickshell.env("ETERNITY_HARNESS_H") || "864")
    readonly property string scenario: Quickshell.env("ETERNITY_HARNESS_SCENARIO") || "strip"
    readonly property real k: Geometry.k(w, h)
    readonly property bool presence: scenario.indexOf("presence") === 0
    readonly property bool lockScene: scenario.indexOf("lock") === 0
    readonly property bool barScene: scenario.indexOf("bar") === 0 || scenario.indexOf("answer") === 0 || scenario.indexOf("consent") === 0
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
            StripContent { id: strip; k: root.k; screenWidth: root.w; visible: !root.presence && !root.barScene && !root.lockScene }
            Loader {
                id: lockLoader
                anchors.fill: parent
                active: root.lockScene
                sourceComponent: LockContent {
                    k: root.k
                    info: ({ greeting: "Good evening", name: "Maya", since_count: 3, pin_available: true })
                    authFn: (pw, mode, cb) => cb(false)
                }
                onLoaded: {
                    const l = item;
                    if (root.scenario === "lock-backoff") { for (let i = 0; i < 5; i++) { l.authFn("x", "passphrase", ok => { l.busy = false; if (!ok) { l.failures += 1; l.shake = true; if (l.failures >= 5) l.backoffMs = 30000; } }); } }
                    if (root.scenario === "lock-pin") l.mode = "pin";
                }
            }
            Loader {
                id: barLoader
                anchors.fill: parent
                active: root.barScene
                sourceComponent: BarContent { id: bc; k: root.k; width: root.w; height: root.h }
                onLoaded: {
                    const b = item;
                    if (root.scenario === "bar-focused") b.show("");
                    if (root.scenario === "answer" || root.scenario === "answer-streaming") {
                        b.show(""); b.streaming = true;
                        b.applyEvent("ask.text", { delta: "Done. Design" }); b.applyEvent("ask.text", { delta: " review" });
                        if (root.scenario === "answer") {
                            b.applyEvent("ask.text", { delta: " is now tomorrow at 15:00." });
                            b.applyEvent("ask.action", { name: "write_note", ok: true, summary: "note saved", undoable: true });
                            b.applyEvent("ask.done", { readout: "on device  \u00b7  first token 41 ms  \u00b7  ~170 tok/s" });
                        }
                    }
                    if (root.scenario === "consent") b.applyEvent("consent.request", { consent_id: "c1", tool: "write_note", risk: "change", description: "Save a markdown note in ~/Documents/Notes\ntitle = Design review", need_pin: false });
                    if (root.scenario === "consent-pin") b.applyEvent("consent.request", { consent_id: "c2", tool: "run_command", risk: "dangerous", description: "Run a shell command as the user\ncommand = ls", need_pin: true });
                }
            }
        }
        Dump {
            dir: Quickshell.env("ETERNITY_SHELL_DUMP") || ""
            name: root.scenario
            target: stage
            collect: () => {
                const base = { screen: [root.w, root.h], k: root.k, scenario: root.scenario, connected: Daemon.connected };
                if (root.presence) { base.items = presenceLoader.item.geometry(); return base; }
                if (root.barScene) { base.items = barLoader.item.geometry(); return Object.assign(base, barLoader.item.flags()); }
                if (root.lockScene) { base.items = lockLoader.item.geometry(); return Object.assign(base, lockLoader.item.flags()); }
                base.items = strip.geometry(); return base;
            }
        }
    }
}
