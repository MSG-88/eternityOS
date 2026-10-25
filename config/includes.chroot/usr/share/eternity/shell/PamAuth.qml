import QtQuick
import Quickshell.Services.Pam

// Passphrase check through PAM (the "login" stack). start(password, cb) -> cb(ok).
Item {
    id: root
    property string user: ""
    property var callback: null
    property string pending: ""
    function start(password, cb) {
        root.callback = cb; root.pending = password;
        if (pam.active) pam.abort();
        pam.start();
    }
    PamContext {
        id: pam
        config: "login"
        user: root.user
        onResponseRequiredChanged: { if (responseRequired) respond(root.pending); }
        onCompleted: result => { const cb = root.callback; root.callback = null; root.pending = ""; if (cb) cb(result === PamResult.Success); }
        onError: error => { const cb = root.callback; root.callback = null; root.pending = ""; if (cb) cb(false); }
    }
}
