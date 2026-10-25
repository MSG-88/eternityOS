import QtQuick
import Quickshell

// Test harness (tests/host/test_shell_render.sh): loads the shell's content items into a plain
// window of the requested logical size (ETERNITY_HARNESS_W/H), with or without a daemon, and
// writes the geometry dump + screenshot through Dump. Lives next to the shell because Quickshell
// only imports files under its config root. Scenarios: strip, strip100, presence, presence-windows, bar, bar-focused, answer, answer-streaming, consent, consent-pin, lock, lock-backoff, lock-pin.
ShellRoot {
    id: root
    property int w: parseInt(Quickshell.env("ETERNITY_HARNESS_W") || "1536")
    property int h: parseInt(Quickshell.env("ETERNITY_HARNESS_H") || "864")
    readonly property string scenario: Quickshell.env("ETERNITY_HARNESS_SCENARIO") || "strip"
    readonly property real k: Geometry.k(w, h)
    readonly property bool presence: scenario.indexOf("presence") === 0
    readonly property bool lockScene: scenario.indexOf("lock") === 0
    readonly property bool greeterScene: scenario.indexOf("greeter") === 0
    readonly property bool plainScene: scenario === "screens" || scenario === "latency"
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
            StripContent { id: strip; k: root.k; screenWidth: root.w; visible: !root.presence && !root.barScene && !root.lockScene && !root.greeterScene }
            Loader {
                id: greeterLoader
                anchors.fill: parent
                active: root.greeterScene
                sourceComponent: GreeterContent { k: root.k; users: ["maya", "eternity"]; authFn: (pw, mode, cb) => cb(false) }
                onLoaded: { if (root.scenario === "greeter-fail") { item.setPassword("wrong"); item.submit(); } }
            }
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
                    if (root.scenario === "lock-backoff" || root.scenario === "lock-backoff-submit") { for (let i = 0; i < 5; i++) { l.setPassword("wrong" + i); l.submit(); } }
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
                    if (root.scenario.indexOf("consent-queue") === 0 || root.scenario === "consent-closed" || root.scenario === "consent-dismiss" || root.scenario === "consent-wrong-pin") {
                        b.applyEvent("consent.request", { consent_id: "c1", tool: "write_note", risk: "change", description: "first", need_pin: false });
                        b.applyEvent("consent.request", { consent_id: "c2", tool: "run_command", risk: "dangerous", description: "second", need_pin: true });
                        b.applyEvent("consent.request", { consent_id: "c1", tool: "write_note", risk: "change", description: "first", need_pin: false, replay: true });   // replay is ignored
                    }
                    if (root.scenario === "consent-queue") b.answerConsent(false, "");
                    if (root.scenario === "consent-wrong-pin") { b.answerConsent(false, ""); b.handleConsentReply({ ok: false, pin: "wrong", consent_id: "c2" }, null); }
                    if (root.scenario === "consent-closed") { b.applyEvent("consent.closed", { consent_id: "c1" }); b.applyEvent("consent.closed", { consent_id: "c2" }); }
                    if (root.scenario === "consent-dismiss") { b.applyEvent("consent.closed", { consent_id: "c2" }); b.dismiss(); }
                }
            }
        }
        Timer { running: root.scenario === "rescale"; interval: 300; repeat: false; onTriggered: { root.w = 1536; root.h = 864; } }
        Component.onCompleted: {
            if (root.scenario === "latency") for (let i = 1; i <= 20; i++) Latency.record(i);
        }
        Dump {
            dir: Quickshell.env("ETERNITY_SHELL_DUMP") || ""
            name: root.scenario
            target: stage
            collect: () => {
                const base = { screen: [root.w, root.h], k: root.k, scenario: root.scenario, connected: Daemon.connected,
                               panel_edp: Geometry.isPanel("eDP-1", ["eDP-1", "HDMI-A-1"]), panel_hdmi: Geometry.isPanel("HDMI-A-1", ["eDP-1", "HDMI-A-1"]), panel_only_hdmi: Geometry.isPanel("HDMI-A-1", ["HDMI-A-1"]),
                               lat_count: Latency.count, lat_p95: Latency.p95, lat_file: Latency.filePath };
                if (root.presence) { base.items = presenceLoader.item.geometry(); return base; }
                if (root.barScene) { base.items = barLoader.item.geometry(); return Object.assign(base, barLoader.item.flags()); }
                if (root.lockScene) { base.items = lockLoader.item.geometry(); return Object.assign(base, lockLoader.item.flags()); }
                if (root.greeterScene) { base.items = greeterLoader.item.geometry(); return Object.assign(base, greeterLoader.item.flags()); }
                base.items = strip.geometry(); return base;
            }
        }
    }
}
