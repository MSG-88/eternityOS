import QtQuick

// The greeter scene: LockContent in greeter mode (no personal data) plus the account chips above
// the field and the session chooser at the bottom right. authFn(password, mode, cb) is supplied by
// the greeter config (greetd) or the harness; launch(cmd) fires after a successful login.
Item {
    id: root
    property real k: 1
    property var users: []
    property string selectedUser: users.length ? users[0] : ""
    property string selectedSession: "eternity"
    readonly property var sessions: [{ id: "eternity", label: "Eternity", cmd: ["eternity-session"] },
                                     { id: "xfce", label: "Eternity Classic", cmd: ["startxfce4"] }]
    property var authFn: null
    signal launch(var cmd)
    onUsersChanged: if (!selectedUser && users.length) selectedUser = users[0]

    LockContent {
        id: lock
        anchors.fill: parent
        k: root.k
        greeter: true
        info: ({ greeting: "Good evening", name: "", since_count: 0, pin_available: false })
        authFn: root.authFn
        onUnlocked: root.startSession()
    }
    function startSession() { const s = root.sessions.find(x => x.id === root.selectedSession); if (s) root.launch(s.cmd); }

    Row {   // accounts
        id: accounts
        anchors.horizontalCenter: parent.horizontalCenter
        y: 560 * root.k
        spacing: 10 * root.k
        Repeater {
            model: root.users
            Rectangle {
                required property string modelData
                readonly property bool on: modelData === root.selectedUser
                width: userLabel.implicitWidth + 28 * root.k; height: userLabel.implicitHeight + 12 * root.k; radius: 6 * root.k
                color: on ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.12) : "transparent"; border.width: 1; border.color: on ? Theme.accent : Theme.n700
                Text { id: userLabel; anchors.centerIn: parent; text: modelData; color: on ? Theme.accent300 : Theme.n400; font.family: Theme.body; font.pixelSize: 13 * root.k }
                MouseArea { anchors.fill: parent; onClicked: root.selectedUser = modelData }
            }
        }
    }
    Row {   // session chooser
        id: sessionRow
        anchors.right: parent.right; anchors.rightMargin: 40 * root.k
        y: root.height - 56 * root.k - height
        spacing: 8 * root.k
        Repeater {
            model: root.sessions
            Rectangle {
                required property var modelData
                readonly property bool on: modelData.id === root.selectedSession
                width: sLabel.implicitWidth + 20 * root.k; height: sLabel.implicitHeight + 8 * root.k; radius: 6 * root.k
                color: "transparent"; border.width: 1; border.color: on ? Theme.accent : Theme.n800
                Text { id: sLabel; anchors.centerIn: parent; text: modelData.label; color: on ? Theme.accent : Theme.n600; font.family: Theme.body; font.pixelSize: 11 * root.k }
                MouseArea { anchors.fill: parent; onClicked: root.selectedSession = modelData.id }
            }
        }
    }
    function setPassword(pw) { lock.setPassword(pw); }
    function submit() { lock.submit(); }
    function geometry() { return lock.geometry(); }
    function flags() { return Object.assign(lock.flags(), { users: root.users, sessions: root.sessions.map(s => s.label), selected_user: root.selectedUser, selected_session: root.selectedSession, greeter: true }); }
}
