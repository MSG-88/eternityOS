import QtQuick

// "Eternity asks": the consent dialog (Nocturne .dialog, 440 wide, radius 14, surface,
// shadow-lg). Kicker "ALLOW <TOOL>?", the description, the risk line, a PIN field when the
// action is dangerous and a PIN is set, "Not now" / "Allow". Answered through reply(ok, pin).
Rectangle {
    id: root
    property real k: 1
    property var request: ({})          // {consent_id, tool, risk, description, need_pin}
    signal reply(bool ok, string pin)
    property string message: ""
    readonly property string toolName: (request.tool || "tool").replace(/_/g, " ").toUpperCase()
    readonly property bool needPin: request.need_pin === true
    readonly property string riskText: request.risk === "read" ? "reads information" : request.risk === "dangerous" ? "is a sensitive action" : "changes something on this device"
    width: 440 * k
    height: col.implicitHeight + 2 * pad
    radius: Theme.radiusLg * k
    color: Theme.surface
    border.width: Math.max(1, Math.round(k)); border.color: Theme.n500
    readonly property real pad: 20 * k
    Column {
        id: col
        x: root.pad; y: root.pad; width: root.width - 2 * root.pad
        spacing: 10 * root.k
        Text { id: kicker; text: "ALLOW " + root.toolName + "?"; color: Theme.accent; font.family: Theme.body; font.pixelSize: 11 * root.k; font.weight: Font.Medium; font.letterSpacing: 1.3 * root.k }
        Text { text: request.description || ""; color: Theme.text; font.family: Theme.body; font.pixelSize: 15 * root.k; width: parent.width; wrapMode: Text.WordWrap }
        Text { text: "This " + root.riskText + ". It will be logged and, where possible, can be undone."; color: Theme.n500; font.family: Theme.body; font.pixelSize: 12 * root.k; width: parent.width; wrapMode: Text.WordWrap }
        Text { visible: root.message !== ""; text: root.message; color: Theme.accent300; font.family: Theme.body; font.pixelSize: 12 * root.k; width: parent.width; wrapMode: Text.WordWrap }
        Rectangle {
            id: pinBox
            visible: root.needPin
            width: parent.width; height: 36 * root.k; radius: Theme.radiusMd * root.k
            color: Theme.bg; border.width: 1; border.color: pin.activeFocus ? Theme.accent : Theme.n800
            TextInput { id: pin; anchors.fill: parent; anchors.margins: 8 * root.k; echoMode: TextInput.Password; color: Theme.text; font.family: Theme.body; font.pixelSize: 14 * root.k
                        inputMethodHints: Qt.ImhDigitsOnly; onAccepted: root.reply(true, text) }
            Text { visible: pin.text === ""; text: "Your PIN"; color: Theme.n600; font.family: Theme.body; font.pixelSize: 14 * root.k; x: 8 * root.k; anchors.verticalCenter: parent.verticalCenter }
        }
        Row {
            anchors.right: parent.right
            spacing: 8 * root.k
            Rectangle { width: notNow.implicitWidth + 24 * root.k; height: 32 * root.k; radius: Theme.radiusMd * root.k; color: "transparent"; border.width: 1; border.color: Theme.n700
                        Text { id: notNow; anchors.centerIn: parent; text: "Not now"; color: Theme.n400; font.family: Theme.body; font.pixelSize: 14 * root.k; font.weight: Font.Medium }
                        MouseArea { anchors.fill: parent; onClicked: root.reply(false, "") } }
            Rectangle { width: allow.implicitWidth + 24 * root.k; height: 32 * root.k; radius: Theme.radiusMd * root.k; color: "transparent"; border.width: 1
                        border.color: request.risk === "dangerous" ? Theme.accent300 : Theme.accent
                        Text { id: allow; anchors.centerIn: parent; text: "Allow"; color: Theme.accent; font.family: Theme.body; font.pixelSize: 14 * root.k; font.weight: Font.Medium }
                        MouseArea { anchors.fill: parent; onClicked: root.reply(true, pin.text) } }
        }
    }
    Keys.onEscapePressed: root.reply(false, "")
    // keyboard: Enter allows a non-PIN action (the PIN field submits through onAccepted), Esc declines
    Keys.onReturnPressed: if (!root.needPin) root.reply(true, "")
    Keys.onEnterPressed: if (!root.needPin) root.reply(true, "")
    function geometry() { return { consent: [x, y, width, height, ""], consent_kicker: [kicker.x, kicker.y, kicker.width, kicker.height, kicker.text], pin_visible: pinBox.visible }; }
    function focusInput() { if (root.needPin) { pin.text = ""; pin.forceActiveFocus(); } else root.forceActiveFocus(); }
}
