import QtQuick

// The launcher: the ring over the installed apps (daemon launcher.index); Enter launches through
// the daemon (launcher.launch) and closes; Esc closes.
RingContent {
    id: root
    property var apps: []          // [{name, exec, icon, id}] (harness injects; the shell loads from the daemon)
    items: apps.map(a => ({ id: a.id, label: a.name, sub: a.comment || "" }))
    function load() { Daemon.call("launcher.index", { limit: 200 }, (r, e) => { if (r) root.apps = r.apps; }); }
    onActivated: it => { if (Daemon.connected) Daemon.call("launcher.launch", { id: it.id }, null); root.closed(); }
}
