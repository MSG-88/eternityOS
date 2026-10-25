import QtQuick
import Quickshell

// The lock scene (design scene 03 without the camera): mark 176 at (960, 420), "Good evening,
// <name>." 52/500 at y 640, "n things since you left", the passphrase (or PIN) field, chips
// "Passphrase" / "PIN" at bottom 88 and "Other ways to unlock" at bottom 56. Wrong answers shake
// the field; after 5 failures a 30 s backoff. authFn(password, mode, cb) is pluggable for tests.
Item {
    id: root
    property real k: 1
    property var info: ({ greeting: "Good evening", name: "", since_count: 0, pin_available: false })
    property string mode: "passphrase"          // passphrase | pin
    property int failures: 0
    property int backoffMs: 0
    property bool shake: false
    property bool locked: true
    property bool busy: false
    property var authFn: null                    // function(password, mode, cb)
    signal unlocked()
    readonly property string greetingText: (info.greeting || "Good evening") + (info.name ? ", " + info.name : "") + "."
    readonly property string sinceText: (info.since_count || 0) === 0 ? "Nothing new since you left" : (info.since_count === 1 ? "1 thing since you left" : info.since_count + " things since you left")

    Rectangle { anchors.fill: parent; color: Theme.bg }
    Mobius { id: mark; size: 176 * root.k; x: 960 * root.k - width / 2; y: 420 * root.k - height / 2; animated: !Theme.reduced }
    Text {
        id: greeting
        text: root.greetingText; color: Theme.text; font.family: Theme.body; font.pixelSize: 52 * root.k; font.weight: Font.Medium; font.letterSpacing: -0.015 * 52 * root.k
        anchors.horizontalCenter: parent.horizontalCenter; y: 640 * root.k
    }
    Text {
        id: since
        text: root.sinceText; color: Theme.n500; font.family: Theme.body; font.pixelSize: 16 * root.k
        anchors.horizontalCenter: parent.horizontalCenter; y: greeting.y + greeting.height + 14 * root.k
    }
    Rectangle {
        id: fieldBox
        width: 360 * root.k; height: 44 * root.k; radius: Theme.radiusMd * root.k
        anchors.horizontalCenter: parent.horizontalCenter; y: since.y + since.height + 28 * root.k
        color: Theme.surface; border.width: 1; border.color: root.backoffMs > 0 ? Theme.n700 : (field.activeFocus ? Theme.accent : Theme.n800)
        TextInput {
            id: field
            anchors.fill: parent; anchors.margins: 10 * root.k
            echoMode: TextInput.Password; color: Theme.text; font.family: Theme.body; font.pixelSize: 16 * root.k
            enabled: root.backoffMs === 0 && !root.busy
            inputMethodHints: root.mode === "pin" ? Qt.ImhDigitsOnly : Qt.ImhNone
            onAccepted: root.submit()
            focus: true
        }
        Text { id: fieldPlaceholder; visible: field.text === ""; text: root.backoffMs > 0 ? ("Try again in " + Math.ceil(root.backoffMs / 1000) + " s") : (root.mode === "pin" ? "PIN" : "Passphrase")
               color: Theme.n600; font.family: Theme.body; font.pixelSize: 16 * root.k; x: 10 * root.k; anchors.verticalCenter: parent.verticalCenter }
        SequentialAnimation {
            id: shakeAnim
            NumberAnimation { target: fieldBox; property: "anchors.horizontalCenterOffset"; to: -10 * root.k; duration: 50 }
            NumberAnimation { target: fieldBox; property: "anchors.horizontalCenterOffset"; to: 10 * root.k; duration: 90 }
            NumberAnimation { target: fieldBox; property: "anchors.horizontalCenterOffset"; to: -6 * root.k; duration: 70 }
            NumberAnimation { target: fieldBox; property: "anchors.horizontalCenterOffset"; to: 0; duration: 60 }
        }
    }
    Row {
        id: chips
        anchors.horizontalCenter: parent.horizontalCenter
        y: root.height - 88 * root.k - height
        spacing: 10 * root.k
        Repeater {
            model: root.info.pin_available ? ["Passphrase", "PIN"] : ["Passphrase"]
            Rectangle {
                required property string modelData
                readonly property bool on: (modelData === "PIN") === (root.mode === "pin")
                width: chipLabel.implicitWidth + 28 * root.k; height: chipLabel.implicitHeight + 12 * root.k; radius: 6 * root.k
                color: "transparent"; border.width: 1; border.color: on ? Theme.accent : Theme.n700
                Text { id: chipLabel; anchors.centerIn: parent; text: modelData; color: on ? Theme.accent : Theme.n500; font.family: Theme.body; font.pixelSize: 11 * root.k }
                MouseArea { anchors.fill: parent; onClicked: { root.mode = modelData === "PIN" ? "pin" : "passphrase"; field.text = ""; field.forceActiveFocus(); } }
            }
        }
    }
    Text { id: other; text: "Other ways to unlock"; color: Theme.n600; font.family: Theme.body; font.pixelSize: 12 * root.k; anchors.horizontalCenter: parent.horizontalCenter; y: root.height - 56 * root.k - height }

    Timer { id: backoff; interval: 1000; repeat: true; running: root.backoffMs > 0; onTriggered: { root.backoffMs = Math.max(0, root.backoffMs - 1000); if (root.backoffMs === 0) root.failures = 0; } }

    function submit() {
        const pw = field.text;
        if (pw === "" || root.busy || root.backoffMs > 0) return;
        root.busy = true;
        const done = ok => {
            root.busy = false; field.text = "";
            if (ok) { root.failures = 0; root.locked = false; root.unlocked(); return; }
            root.failures += 1; root.shake = true; shakeAnim.restart();
            if (root.failures >= 5) root.backoffMs = 30000;
            field.forceActiveFocus();
        };
        if (root.authFn) root.authFn(pw, root.mode, done);
        else if (root.mode === "pin") Daemon.call("pin.verify", { pin: pw }, (r, e) => done(!!(r && r.ok)));
        else pam.start(pw, done);
    }
    PamAuth { id: pam; user: Quickshell.env("USER") }

    function geometry() {
        return { mark: [mark.x, mark.y, mark.width, mark.height, ""], greeting: [greeting.x, greeting.y, greeting.width, greeting.height, greeting.text],
                 since: [since.x, since.y, since.width, since.height, since.text], field: [fieldBox.x, fieldBox.y, fieldBox.width, fieldBox.height, ""],
                 field_placeholder: [fieldPlaceholder.x, fieldPlaceholder.y, fieldPlaceholder.width, fieldPlaceholder.height, fieldPlaceholder.text],
                 chips: [chips.x, chips.y, chips.width, chips.height, ""], other: [other.x, other.y, other.width, other.height, other.text] };
    }
    function flags() { return { locked: root.locked, backoff_ms: root.backoffMs, failures: root.failures, shake: root.shake, mode: root.mode }; }
}
