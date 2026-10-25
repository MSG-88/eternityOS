import QtQuick

// Settings (design scene 09, "How she shows up"): a left nav of pages and the 700-wide column
// at (1000, 200) in the 1920 reference. Every control writes through the daemon
// (settings.set / theme.set); when the daemon is away the controls are disabled and say so.
Item {
    id: root
    property real k: 1
    property var settings: Daemon.state && Daemon.state.settings ? Daemon.state.settings : ({})
    property var themeCfg: ({})
    property var presets: []
    property string page: "Eternity"
    property bool online: Daemon.connected
    property var hw: ({})
    readonly property var pages: ["Eternity", "Assistant", "Devices", "Network", "Sound", "Power", "Appearance", "Keys"]
    readonly property var presetList: presets.length ? presets : [{ id: "nocturne", name: "Nocturne" }, { id: "nocturne-light", name: "Nocturne Light" }, { id: "mono", name: "Mono" }, { id: "high-contrast", name: "High contrast" }, { id: "quiet", name: "Quiet" }]
    readonly property var scales: [1, 1.25, 1.5]
    readonly property var providerIds: ["local", "claude_code", "anthropic", "openai"]
    readonly property var allowTools: ["Read", "Glob", "Grep", "WebSearch", "WebFetch", "Edit", "Write", "Bash"]

    function load() {
        Daemon.call("settings.get", {}, (r, e) => { if (r) root.settings = r; });
        Daemon.call("theme.get", {}, (r, e) => { if (r) root.themeCfg = r; });
        Daemon.call("theme.presets", {}, (r, e) => { if (r) root.presets = r.presets; });
    }
    function setSetting(key, value) { Daemon.call("settings.set", { key: key, value: value }, (r, e) => { root.load(); }); }
    function setTheme(file, key, value, section) { Daemon.call("theme.set", { file: file, key: key, value: value, section: section || "" }, (r, e) => { root.load(); }); }
    function applyPreset(id) { Daemon.call("theme.apply_preset", { id: id }, (r, e) => { root.load(); }); }
    Component.onCompleted: if (Daemon.connected) load()
    Connections { target: Daemon; function onConnectedChanged() { if (Daemon.connected) root.load(); } }

    Rectangle { anchors.fill: parent; color: Theme.bg }
    Column {   // nav (left)
        id: nav
        x: 260 * root.k; y: 200 * root.k
        spacing: 4 * root.k
        Repeater {
            model: root.pages
            Rectangle {
                required property string modelData
                readonly property bool on: modelData === root.page
                width: 180 * root.k; height: 34 * root.k; radius: Theme.radiusSm * root.k
                color: on ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.12) : "transparent"
                Text { x: 10 * root.k; anchors.verticalCenter: parent.verticalCenter; text: modelData; color: on ? Theme.accent300 : Theme.n400; font.family: Theme.body; font.pixelSize: 14 * root.k }
                MouseArea { anchors.fill: parent; onClicked: root.page = modelData }
            }
        }
    }
    Column {   // the column
        id: column
        x: 1000 * root.k; y: 200 * root.k; width: 700 * root.k
        spacing: 0
        Text { id: kicker; text: "SETTINGS \u00b7 " + root.page.toUpperCase(); color: Theme.accent; font.family: Theme.tech; font.pixelSize: 11 * root.k; font.letterSpacing: 0.24 * 11 * root.k }
        Item { width: 1; height: 12 * root.k }
        Text { id: title; text: root.page === "Eternity" ? "How she shows up" : root.page; color: Theme.text; font.family: Theme.body; font.pixelSize: 36 * root.k; font.weight: Font.Medium; font.letterSpacing: -0.015 * 36 * root.k }
        Item { width: 1; height: 30 * root.k }
        Text { id: offline; visible: !root.online; text: "Eternity's daemon is not running: settings cannot be changed right now."; color: Theme.accent300; font.family: Theme.body; font.pixelSize: 13 * root.k; width: parent.width; wrapMode: Text.WordWrap }
        Loader { id: pageLoader; width: parent.width; sourceComponent: root.page === "Eternity" ? eternityPage : root.page === "Appearance" ? appearancePage : root.page === "Assistant" ? assistantPage : root.page === "Keys" ? keysPage : root.page === "Devices" ? devicesPage : genericPage }
        Item { width: 1; height: 20 * root.k }
        Text { id: note; text: "Changes apply instantly."; color: Theme.n500; font.family: Theme.body; font.pixelSize: 13 * root.k }
    }

    Component {
        id: eternityPage
        Column {
            SettingsRow { k: root.k; label: "Voice"; Seg { k: root.k; options: [{ id: "calm", label: "Calm" }, { id: "bright", label: "Bright" }, { id: "off", label: "Off" }]; value: root.settings.voice || "off"; enabled: root.online; onChosen: id => root.setSetting("voice", id) } }
            SettingsRow { k: root.k; label: "Verbosity"; Slider { id: verb; objectName: "slider"; k: root.k; steps: 2; value: ({ brief: 0, normal: 0.5, detailed: 1 })[root.settings.verbosity || "normal"]; enabled: root.online; onChanged: v => root.setSetting("verbosity", v < 0.25 ? "brief" : v > 0.75 ? "detailed" : "normal") } }
            SettingsRow { k: root.k; label: "Proactive suggestions"; Toggle { k: root.k; on: root.settings.proactive !== false; enabled: root.online; onToggled: v => root.setSetting("proactive", v) } }
            SettingsRow { k: root.k; label: "Keep everything on device"; Toggle { k: root.k; on: root.settings.on_device_only !== false; enabled: root.online; onToggled: v => root.setSetting("on_device_only", v) } }
            SettingsRow { k: root.k; label: "Share anonymous model telemetry"; hint: "There is none. This stays off."; Toggle { id: telemetry; objectName: "telemetry"; k: root.k; on: false; enabled: false } }
            SettingsRow { k: root.k; label: "Do not disturb"; hint: "Notifications are held and counted on the Focus card."; Toggle { k: root.k; on: root.settings.dnd === true; enabled: root.online; onToggled: v => root.setSetting("dnd", v) } }
            SettingsRow { k: root.k; label: "Unlock"; hint: "Change the methods in the setup assistant (eternity-firstrun --reset)."; Text { text: (root.settings.unlock_methods || ["passphrase"]).map(m => m.charAt(0).toUpperCase() + m.slice(1)).join(" \u00b7 "); color: Theme.n400; font.family: Theme.body; font.pixelSize: 13 * root.k } }
        }
    }
    Component {
        id: appearancePage
        Column {
            SettingsRow { k: root.k; label: "Preset"; hint: "Writes your theme.toml and layout.toml; the shell reloads live."
                Seg { objectName: "presets"; k: root.k; options: root.presetList.map(p => ({ id: p.id, label: p.name })); value: ""; enabled: root.online; onChosen: id => root.applyPreset(id) } }
            SettingsRow { k: root.k; label: "Scale"; hint: "Of the laptop panel (external outputs stay at 100 %)."
                Seg { objectName: "scales"; k: root.k; options: root.scales.map(s => ({ id: String(s), label: Math.round(s * 100) + " %" })); value: String((root.themeCfg.layout || {}).scale || 1.25); enabled: root.online; onChosen: id => root.setTheme("layout", "scale", parseFloat(id)) } }
            SettingsRow { k: root.k; label: "Reduced motion"; hint: "No sweeps, no decoding text, no glow breathing."; Toggle { k: root.k; on: !!((root.themeCfg.theme || {}).motion || {}).reduced; enabled: root.online; onToggled: v => root.setTheme("theme", "reduced", v, "motion") } }
            SettingsRow { k: root.k; label: "Presence glow"; Slider { k: root.k; value: ((((root.themeCfg.theme || {}).motion || {}).glow || 1) - 0.3) / 1.5; enabled: root.online; onChanged: v => root.setTheme("theme", "glow", Math.round((0.3 + v * 1.5) * 10) / 10, "motion") } }
        }
    }
    Component {
        id: assistantPage
        Column {
            SettingsRow { k: root.k; label: "Who answers"; Seg { objectName: "providers"; k: root.k; options: [{ id: "local", label: "On this device" }, { id: "claude_code", label: "Claude account" }, { id: "anthropic", label: "Claude key" }, { id: "openai", label: "ChatGPT key" }]; value: root.settings.provider || "local"; enabled: root.online; onChosen: id => root.setSetting("provider", id) } }
            SettingsRow { k: root.k; label: "Claude model"; Seg { k: root.k; options: ["sonnet", "opus", "haiku"]; value: root.settings.claude_code_model || "sonnet"; enabled: root.online; onChosen: id => root.setSetting("claude_code_model", id) } }
            SettingsRow { k: root.k; label: "Sign in"; hint: "Claude Code holds your sign-in in your home folder; Eternity keeps no credentials."
                Rectangle { width: signLabel.implicitWidth + 24 * root.k; height: 32 * root.k; radius: Theme.radiusMd * root.k; color: "transparent"; border.width: 1; border.color: Theme.accent
                    Text { id: signLabel; anchors.centerIn: parent; text: "Sign in with your Claude account"; color: Theme.accent; font.family: Theme.body; font.pixelSize: 14 * root.k; font.weight: Font.Medium }
                    MouseArea { anchors.fill: parent; onClicked: Quickshell.execDetached(["eternity-signin"]) } } }
            SettingsRow { k: root.k; label: "What Claude may do without asking"; hint: "Everything else opens the consent dialog. sudo and pkexec are always refused."
                Flow { id: allowFlow; objectName: "allow"; width: 360 * root.k; spacing: 6 * root.k
                    Repeater { model: root.allowTools
                        Rectangle { required property string modelData; readonly property bool on: (root.settings.claude_code_allow || []).indexOf(modelData) >= 0
                            width: aLbl.implicitWidth + 20 * root.k; height: 26 * root.k; radius: 6 * root.k; color: on ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.12) : "transparent"; border.width: 1; border.color: on ? Theme.accent : Theme.n700
                            Text { id: aLbl; anchors.centerIn: parent; text: modelData; color: on ? Theme.accent300 : Theme.n400; font.family: Theme.body; font.pixelSize: 12 * root.k }
                            MouseArea { anchors.fill: parent; enabled: root.online; onClicked: { const cur = (root.settings.claude_code_allow || []).slice(); const i = cur.indexOf(modelData); if (i >= 0) cur.splice(i, 1); else cur.push(modelData); root.setSetting("claude_code_allow", cur); } } } } } }
            SettingsRow { k: root.k; label: "Trust"; hint: "Set in the setup assistant; read-only lookups run unasked at level 1."; Text { text: "level " + (root.settings.trust_level || 0); color: Theme.n400; font.family: Theme.body; font.pixelSize: 13 * root.k } }
        }
    }
    Component {
        id: keysPage
        Column {
            Repeater {
                model: Object.keys((root.themeCfg.keys || {}).bind || {}).map(n => ({ name: n, combo: root.themeCfg.keys.bind[n] }))
                SettingsRow { required property var modelData; k: root.k; label: modelData.name; Text { text: modelData.combo; color: Theme.n400; font.family: Theme.mono; font.pixelSize: 13 * root.k } }
            }
            SettingsRow { k: root.k; label: "Edit"; hint: "~/.config/eternity/keys.toml, then eternity-theme render"; Text { text: ""; } }
        }
    }
    Component {
        id: devicesPage
        Column {
            SettingsRow { k: root.k; label: "Hardware report"; hint: "Devices, drivers, firmware, radios, sound, power (eternity-hw)."
                Rectangle { width: hwLabel.implicitWidth + 24 * root.k; height: 32 * root.k; radius: Theme.radiusMd * root.k; color: "transparent"; border.width: 1; border.color: Theme.accent
                    Text { id: hwLabel; anchors.centerIn: parent; text: "Refresh"; color: Theme.accent; font.family: Theme.body; font.pixelSize: 14 * root.k }
                    MouseArea { anchors.fill: parent; onClicked: Daemon.call("hw.summary", {}, (r, e) => { if (r) root.hw = r; }) } } }
            Repeater { model: (root.hw.problems || [])
                SettingsRow { required property string modelData; k: root.k; label: modelData; Text { text: "" } } }
            SettingsRow { k: root.k; label: root.hw.summary ? ((root.hw.summary.bad || 0) + " problems \u00b7 " + (root.hw.summary.warn || 0) + " warnings") : "Press Refresh"; Text { text: "" } }
        }
    }
    Component {
        id: genericPage
        Column { SettingsRow { k: root.k; label: root.page + " controls arrive in the next build"; hint: "The strip's popovers cover the basics meanwhile."; Text { text: "" } } }
    }

    function geometry() {
        const out = { kicker: [column.x + kicker.x, column.y + kicker.y, kicker.width, kicker.height, kicker.text], title: [column.x + title.x, column.y + title.y, title.width, title.height, title.text],
                      column: [column.x, column.y, column.width, column.height, ""], offline: [column.x, column.y + offline.y, offline.width, offline.height, offline.visible ? offline.text : ""] };
        const col = pageLoader.item;
        if (col) for (let i = 0; i < col.children.length; i++) { const r = col.children[i]; if (r && r.height !== undefined) out["row" + i] = [column.x, column.y + pageLoader.y + r.y, r.width, r.height, r.label || ""]; }
        const s = findChild(pageLoader.item, "slider"); if (s) out.slider = [0, 0, s.width, s.height, ""];
        return out;
    }
    function findChild(item, name) { if (!item) return null; if (item.objectName === name) return item; for (let i = 0; i < item.children.length; i++) { const f = findChild(item.children[i], name); if (f) return f; } return null; }
    function flags() {
        const col = pageLoader.item;
        const tele = findChild(col, "telemetry");
        const pres = findChild(col, "presets"); const sc = findChild(col, "scales"); const prov = findChild(col, "providers"); const allow = findChild(col, "allow");
        return { pages: root.pages, page: root.page, rows: col ? col.children.length : 0, controls_enabled: root.online,
                 telemetry_enabled: tele ? tele.enabled : null, telemetry_on: tele ? tele.on : null,
                 presets: pres ? pres.opts.map(o => o.label) : [], scales: sc ? sc.opts.map(o => parseFloat(o.id)) : [],
                 providers: prov ? prov.opts.length : 0, allow_tools: allow ? allow.children.length - 1 : 0 };
    }
}
