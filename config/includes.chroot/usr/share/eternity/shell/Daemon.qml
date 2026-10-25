pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

// Client of eternity-daemon ($XDG_RUNTIME_DIR/eternity/daemon.sock, JSON lines). While the daemon
// is away a fresh Socket is created every 2 s (a Socket that lost the daemon did not reconnect when
// `connected` was set again on it: seen on the installed system, 2026-10-26); subscribes on connect;
// keeps the last state and metrics; routes events.
Singleton {
    id: root
    property bool connected: sockLoader.item ? sockLoader.item.connected : false
    property var state: ({})
    property var metrics: ({})
    property var cards: []
    property int nextId: 1
    property var pending: ({})
    signal event(string name, var data)

    readonly property string sockPath: Quickshell.env("ETERNITY_SOCK")
        || ((Quickshell.env("XDG_RUNTIME_DIR") || ("/run/user/" + Quickshell.env("UID"))) + "/eternity/daemon.sock")

    function call(method, params, cb) {
        const sock = sockLoader.item;
        if (!sock || !sock.connected) { if (cb) cb(null, "not connected"); return; }
        const id = root.nextId++;
        if (cb) { const p = root.pending; p[id] = cb; root.pending = p; }
        sock.write(JSON.stringify({ id: id, method: method, params: params || {} }) + "\n");
        sock.flush();
    }
    function refresh() {
        call("state.get", {}, (r, e) => { if (r) root.state = r; });
        call("cards.get", {}, (r, e) => { if (r) root.cards = r.cards; });
    }
    function reconnect() {   // throw the old Socket away and try again with a new one
        sockLoader.active = false;
        root.pending = ({});
        sockLoader.active = true;
    }

    Loader { id: sockLoader; active: true; sourceComponent: socketComponent }

    Component {
        id: socketComponent
        Socket {
            id: sock
            path: root.sockPath
            connected: true
            parser: SplitParser {
                onRead: line => {
                    let obj;
                    try { obj = JSON.parse(line); } catch (e) { return; }
                    if (obj.event !== undefined) {
                        if (obj.event === "metrics.sample") root.metrics = obj.data;
                        if (obj.event === "settings.changed" || obj.event === "ask.done") root.refresh();
                        root.event(obj.event, obj.data);
                        return;
                    }
                    const cb = root.pending[obj.id];
                    if (cb) { const p = root.pending; delete p[obj.id]; root.pending = p; cb(obj.result, obj.error); }
                }
            }
            onConnectedChanged: {
                if (connected) {
                    root.call("subscribe", {});
                    root.refresh();
                    root.call("metrics.sample", {}, (r, e) => { if (r) root.metrics = r; });
                } else {
                    root.pending = ({});
                }
            }
        }
    }
    Timer {   // reconnect while the daemon is away; refresh the slow state every 30 s
        interval: root.connected ? 30000 : 2000
        running: true; repeat: true
        onTriggered: { if (!root.connected) root.reconnect(); else root.refresh(); }
    }
}
