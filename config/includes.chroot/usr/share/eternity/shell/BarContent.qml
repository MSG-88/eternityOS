import QtQuick

// Ask Eternity (design scenes 04/05): the command bar 800x54 at (560, 950), radius 14, surface,
// shadow-sm; focused: 1 px accent ring + accent glow; a breathing accent dot; placeholder "Ask
// Eternity, or type a command"; chip "Super Space". Above it while an answer runs: the thinking
// line at y 580, a fade rule at y 620, the streamed reply at (560, 650) w 800 (Inter 19/1.55)
// with a blinking 8x18 accent caret, action cards, and the readout top-right (right 40, top 60).
// Consent requests from the daemon open the dialog centred. Quick commands as in the GTK bar.
Item {
    id: root
    property real k: 1
    property bool active: false              // overlay shown, input focused
    property string providerLabel: (Daemon.state && Daemon.state.ai && Daemon.state.ai.label) ? Daemon.state.ai.label : "Eternity"
    property string answerText: ""
    property string statusText: ""
    property string readoutText: ""
    property bool streaming: false
    property string runId: ""
    property var actions: []
    property var consentQueue: []
    property var consent: null
    signal dismissed()
    signal submitted(string text)
    readonly property bool focused: active && input.activeFocus
    readonly property bool hasAnswer: answerText !== "" || streaming || statusText !== ""

    // --- the bar -------------------------------------------------------------------
    Rectangle {
        id: bar
        x: Theme.bar[0] * root.k; y: Theme.bar[1] * root.k; width: Theme.bar[2] * root.k; height: Theme.bar[3] * root.k
        radius: Theme.radiusLg * root.k
        color: Theme.surface
        border.width: Math.max(1, Math.round(root.k)); border.color: root.focused ? Theme.accent : Theme.n800
        Rectangle {   // focused glow (design: 0 0 32px accent at 25 %)
            id: ring
            visible: root.focused
            anchors.fill: parent; anchors.margins: -6 * root.k
            radius: parent.radius + 6 * root.k; color: "transparent"
            border.width: 6 * root.k; border.color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.18)
            z: -1
        }
        Rectangle {
            id: dot
            x: 20 * root.k; anchors.verticalCenter: parent.verticalCenter
            width: 10 * root.k; height: width; radius: width / 2; color: Theme.accent
            SequentialAnimation on opacity { running: !Theme.reduced; loops: Animation.Infinite
                NumberAnimation { from: 0.6; to: 1; duration: 1050; easing.type: Easing.InOutSine }
                NumberAnimation { from: 1; to: 0.6; duration: 1050; easing.type: Easing.InOutSine } }
        }
        TextInput {
            id: input
            x: 44 * root.k; width: chip.x - x - 14 * root.k; anchors.verticalCenter: parent.verticalCenter
            color: Theme.text; font.family: Theme.body; font.pixelSize: 17 * root.k
            selectionColor: Theme.accent800; selectedTextColor: Theme.text
            clip: true
            enabled: root.active
            onAccepted: root.submit()
            Keys.onEscapePressed: root.dismiss()
            cursorDelegate: Rectangle { width: 2 * root.k; height: input.font.pixelSize; color: Theme.accent; visible: input.activeFocus
                SequentialAnimation on opacity { running: visible; loops: Animation.Infinite; NumberAnimation { from: 1; to: 0; duration: 400 } NumberAnimation { from: 0; to: 1; duration: 400 } } }
        }
        Text {
            id: placeholder
            visible: input.text === ""
            x: input.x; anchors.verticalCenter: parent.verticalCenter
            text: "Ask Eternity, or type a command"; color: Theme.n600; font.family: Theme.body; font.pixelSize: 17 * root.k
        }
        Rectangle {
            id: chip
            anchors.right: parent.right; anchors.rightMargin: 20 * root.k; anchors.verticalCenter: parent.verticalCenter
            width: chipText.implicitWidth + 16 * root.k; height: chipText.implicitHeight + 6 * root.k
            radius: 6 * root.k; color: "transparent"; border.width: 1; border.color: Theme.n800
            Text { id: chipText; anchors.centerIn: parent; text: "Super Space"; color: Theme.n600; font.family: Theme.body; font.pixelSize: 12 * root.k }
        }
        MouseArea { anchors.fill: parent; enabled: !root.active; onClicked: root.show("") }
    }
    Text {   // provider line under the bar (design: faint)
        visible: root.active
        anchors.horizontalCenter: bar.horizontalCenter; y: bar.y + bar.height + 10 * root.k
        text: root.providerLabel + "  \u00b7  Esc closes  \u00b7  /help"; color: Theme.n600; font.family: Theme.body; font.pixelSize: 12 * root.k
    }

    // --- the answer surface ----------------------------------------------------------
    Text {
        id: thinking
        visible: root.active && root.streaming && root.answerText === ""
        anchors.horizontalCenter: parent.horizontalCenter; y: 580 * root.k
        text: root.statusText !== "" ? root.statusText : "Thinking\u2026"; color: Theme.n500; font.family: Theme.body; font.pixelSize: 14 * root.k
    }
    Rectangle {
        id: rule
        visible: root.active && root.hasAnswer
        x: 560 * root.k; y: 620 * root.k; width: 800 * root.k; height: Math.max(1, root.k)
        gradient: Gradient { orientation: Gradient.Horizontal
            GradientStop { position: 0; color: "transparent" } GradientStop { position: 0.06; color: Qt.rgba(Theme.text.r, Theme.text.g, Theme.text.b, 0.22) }
            GradientStop { position: 0.94; color: Qt.rgba(Theme.text.r, Theme.text.g, Theme.text.b, 0.22) } GradientStop { position: 1; color: "transparent" } }
    }
    Item {
        id: answerBox
        visible: root.active && root.hasAnswer
        x: 560 * root.k; y: 650 * root.k; width: 800 * root.k
        Text {
            id: answer
            width: parent.width
            text: root.answerText !== "" ? root.answerText : (root.streaming ? "" : root.statusText)
            color: Theme.text; font.family: Theme.body; font.pixelSize: 19 * root.k; lineHeight: 1.55
            wrapMode: Text.WordWrap; textFormat: Text.PlainText
        }
        Rectangle {   // caret while streaming
            id: caret
            visible: root.streaming
            x: Math.min(answer.width - width, answer.contentWidth + 4 * root.k); y: Math.max(0, answer.contentHeight - 22 * root.k)
            width: 8 * root.k; height: 18 * root.k; color: Theme.accent
            SequentialAnimation on opacity { running: caret.visible && !Theme.reduced; loops: Animation.Infinite; NumberAnimation { from: 1; to: 0.3; duration: 320 } NumberAnimation { from: 0.3; to: 1; duration: 320 } }
        }
        Row {   // action cards
            id: actionRow
            y: answer.contentHeight + 22 * root.k
            spacing: 10 * root.k
            Repeater {
                model: root.actions
                Rectangle {
                    required property var modelData
                    width: actLabel.implicitWidth + 24 * root.k; height: 32 * root.k; radius: Theme.radiusMd * root.k
                    color: "transparent"; border.width: 1; border.color: modelData.ok ? Theme.n700 : Theme.n800
                    Text { id: actLabel; anchors.centerIn: parent; text: (modelData.ok ? "Done \u00b7 " : "Not done \u00b7 ") + String(modelData.name).replace(/_/g, " "); color: modelData.ok ? Theme.n400 : Theme.n600; font.family: Theme.body; font.pixelSize: 13 * root.k }
                }
            }
            Rectangle {
                visible: root.actions.some(a => a.undoable && a.ok)
                width: undoLabel.implicitWidth + 24 * root.k; height: 32 * root.k; radius: Theme.radiusMd * root.k; color: "transparent"; border.width: 1; border.color: Theme.accent
                Text { id: undoLabel; anchors.centerIn: parent; text: "Undo"; color: Theme.accent; font.family: Theme.body; font.pixelSize: 13 * root.k; font.weight: Font.Medium }
                MouseArea { anchors.fill: parent; onClicked: Daemon.call("ask.undo", {}, (r, e) => { if (r) root.appendStatus(r.message); }) }
            }
        }
    }
    Column {
        id: readout
        visible: root.active && (root.streaming || root.readoutText !== "")
        anchors.right: parent.right; anchors.rightMargin: 40 * root.k; y: 60 * root.k
        spacing: 6 * root.k
        Text { anchors.right: parent.right; text: Daemon.state && Daemon.state.provider === "local" ? "realtime \u00b7 on device" : root.providerLabel; color: Theme.accent300; font.family: Theme.body; font.pixelSize: 12 * root.k }
        Text { id: readoutLine; anchors.right: parent.right; text: root.readoutText !== "" ? root.readoutText : (root.streaming ? "planning" : ""); color: Theme.n600; font.family: Theme.body; font.pixelSize: 12 * root.k; font.features: ({ "tnum": 1 }) }
    }

    // --- consent -----------------------------------------------------------------------
    Rectangle { visible: root.consent !== null; anchors.fill: parent; color: Qt.rgba(Theme.n900.r, Theme.n900.g, Theme.n900.b, 0.5) }
    Consent {
        id: consentDialog
        visible: root.consent !== null
        k: root.k
        request: root.consent || ({})
        anchors.centerIn: parent
        onReply: (ok, pin) => root.answerConsent(ok, pin)
    }

    // --- behaviour ----------------------------------------------------------------------
    function show(text) {
        root.active = true;
        if (text) input.text = text;
        input.forceActiveFocus();
    }
    function dismiss() { root.active = false; input.text = ""; root.dismissed(); }
    function submit() {
        const text = input.text.trim();
        if (text === "" || root.streaming) return;
        input.text = "";
        if (text[0] === "/") { root.quick(text); return; }
        root.answerText = ""; root.statusText = ""; root.readoutText = ""; root.actions = []; root.streaming = true;
        root.submitted(text);
        Daemon.call("ask.start", { text: text[0] === ">" ? "Run this shell command: " + text.slice(1).trim() : text }, (r, e) => {
            if (e) { root.streaming = false; root.statusText = e; }
            else root.runId = r.run_id;
        });
    }
    function quick(cmd) {
        const word = cmd.split(" ")[0].toLowerCase();
        if (word === "/help") root.statusText = "Type a question or an instruction. Eternity may propose actions; you confirm each one.\n> command runs a shell command after confirmation \u00b7 /undo \u00b7 /clear \u00b7 /settings \u00b7 /local";
        else if (word === "/undo") Daemon.call("ask.undo", {}, (r, e) => { root.statusText = r ? r.message : e; });
        else if (word === "/clear") { root.answerText = ""; root.statusText = ""; root.actions = []; root.readoutText = ""; }
        else if (word === "/settings") Daemon.call("ask.show", {}, null), Qt.callLater(() => Quickshell.execDetached(["eternity-settings"]));
        else if (word === "/local") Daemon.call("settings.set", { key: "on_device_only", value: true }, (r, e) => { root.statusText = r ? "On this device for now." : e; });
        else root.statusText = "Unknown command " + word + ". /help lists them.";
    }
    function appendStatus(text) { root.statusText = text; }
    function applyEvent(name, data) {
        if (name === "ask.show") { root.show(data && data.text ? data.text : ""); return; }
        if (name === "consent.request") { const q = root.consentQueue.slice(); q.push(data); root.consentQueue = q; if (!root.consent) root.nextConsent(); if (!root.active) root.active = true; return; }
        if (root.runId !== "" && data && data.run_id && data.run_id !== root.runId) return;
        if (name === "ask.text") root.answerText += data.delta;
        else if (name === "ask.status") root.statusText = data.text;
        else if (name === "ask.action") { const a = root.actions.slice(); a.push(data); root.actions = a; }
        else if (name === "ask.done") { root.streaming = false; root.readoutText = data.readout || ""; root.runId = ""; }
    }
    function nextConsent() {
        if (root.consentQueue.length === 0) { root.consent = null; input.forceActiveFocus(); return; }
        const q = root.consentQueue.slice(); root.consent = q.shift(); root.consentQueue = q;
        consentDialog.focusInput();
    }
    function answerConsent(ok, pin) {
        const c = root.consent; if (!c) return;
        Daemon.call("consent.reply", { consent_id: c.consent_id, ok: ok, pin: pin || "" }, null);
        root.nextConsent();
    }
    Connections { target: Daemon; function onEvent(name, data) { root.applyEvent(name, data); } }

    function geometry() {
        const out = { bar: [bar.x, bar.y, bar.width, bar.height, ""], placeholder: [placeholder.x, placeholder.y, placeholder.width, placeholder.height, placeholder.text],
                      chip: [chip.x, chip.y, chip.width, chip.height, chipText.text], answer: [answerBox.x, answerBox.y, answer.width, answer.contentHeight, answer.text],
                      rule: [rule.x, rule.y, rule.width, rule.height, ""], readout: [readout.x, readout.y, readout.width, readout.height, readoutLine.text] };
        const cg = consentDialog.geometry(); out.consent = [consentDialog.x, consentDialog.y, cg.consent[2], cg.consent[3], ""]; out.consent_kicker = cg.consent_kicker;
        return out;
    }
    function flags() { return { focused: root.focused, active: root.active, ring: ring.visible, caret: caret.visible, thinking: thinking.visible, pin_visible: consentDialog.visible && consentDialog.geometry().pin_visible }; }
}
