import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.Greetd

// The Eternity greeter (runs under cage through greetd): the unlock scene with the accounts and
// the session chooser; authentication and launch through greetd. The shared scene files
// (GreeterContent, LockContent, Theme, ...) are copied next to this file at build time.
ShellRoot {
    id: root
    property var users: []
    FileView {
        path: Quickshell.env("ETERNITY_GREETER_USERS") || "/run/eternity-greeter/users.json"
        blockLoading: true
        onLoaded: { try { root.users = JSON.parse(text()); } catch (e) { root.users = []; } }
    }
    PanelWindow {
        id: win
        anchors { top: true; bottom: true; left: true; right: true }
        color: "transparent"
        GreeterContent {
            id: scene
            anchors.fill: parent
            k: Geometry.forScreen(win.screen)
            users: root.users.map(u => u.name)
            authFn: (pw, mode, cb) => root.authenticate(pw, cb)
            onLaunch: cmd => Greetd.launch(cmd)
        }
    }
    property var pending: null
    function authenticate(pw, cb) {
        root.pending = { pw: pw, cb: cb };
        Greetd.createSession(scene.selectedUser);
    }
    Connections {
        target: Greetd
        function onAuthMessage(message, error, responseRequired, echoResponse) { if (responseRequired && root.pending) Greetd.respond(root.pending.pw); }
        function onAuthFailure(message) { const p = root.pending; root.pending = null; if (p) p.cb(false); }
        function onReadyToLaunch() { const p = root.pending; root.pending = null; if (p) p.cb(true); scene.startSession(); }
    }
}
