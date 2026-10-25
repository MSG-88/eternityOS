pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Services.Notifications

// The session's notification server (org.freedesktop.Notifications) and its policy: at most
// three cards on screen, the rest queued; under Do Not Disturb everything is held and counted
// (the Focus card, the lock screen's "n things since you left"); every notification is also
// stored by the daemon. The server is created only in a live session (not in the harness).
Singleton {
    id: root
    property bool dnd: Daemon.state && Daemon.state.dnd !== undefined ? Daemon.state.dnd : false
    property var visible: []        // [{id, app, summary, body, urgency, actions, ref}]
    property var queued: []
    property int held: 0
    property var heldItems: []
    property int nextId: 1
    readonly property int maxVisible: 3
    readonly property bool live: (Quickshell.env("ETERNITY_SHELL_DUMP") || "") === ""

    function push(n) {
        const item = { id: n.id !== undefined ? n.id : root.nextId++, app: n.app || n.appName || "", summary: n.summary || "", body: n.body || "",
                       urgency: n.urgency || "normal", timeout: n.timeout, actions: n.actions || [], ref: n.ref || null };
        if (Daemon.connected) Daemon.call("notifications.store", { app: item.app, summary: item.summary, body: item.body, urgency: String(item.urgency) }, null);
        const existing = root.visible.find(v => v.id === item.id) || root.queued.find(v => v.id === item.id);
        if (existing) { Object.assign(existing, item); root.visible = root.visible.slice(); root.queued = root.queued.slice(); return item.id; }   // replacement: update in place
        if (root.dnd) { const h = root.heldItems.slice(); h.push(item); root.heldItems = h; root.held = h.length + root.queued.length; return item.id; }
        if (root.visible.length < root.maxVisible) { const v = root.visible.slice(); v.push(item); root.visible = v; }
        else { const q = root.queued.slice(); q.push(item); root.queued = q; root.held = root.queued.length; }
        return item.id;
    }
    function dismiss(id) {
        root.visible = root.visible.filter(v => v.id !== id);
        root.queued = root.queued.filter(v => v.id !== id);
        root.refill();
    }
    function refill() {
        while (root.visible.length < root.maxVisible && root.queued.length > 0) {
            const q = root.queued.slice(); const next = q.shift(); root.queued = q;
            const v = root.visible.slice(); v.push(next); root.visible = v;
        }
        root.held = root.queued.length + root.heldItems.length;
    }
    onDndChanged: { if (!dnd && root.heldItems.length) { const q = root.queued.concat(root.heldItems); root.heldItems = []; root.queued = q; root.refill(); } }
    function clearAll() { root.visible = []; root.queued = []; root.heldItems = []; root.held = 0; if (Daemon.connected) Daemon.call("notifications.seen", {}, null); }
    function expiryMs(item) { if (!item) return 0; if (item.urgency === "critical" || item.urgency === 2) return 0; const t = Number(item.timeout); return (t > 0) ? t : 8000; }

    Loader {
        active: root.live
        sourceComponent: NotificationServer {
            keepOnReload: true
            actionsSupported: true
            bodySupported: true
            persistenceSupported: false
            onNotification: n => {
                n.tracked = true;
                root.push({ id: n.id, app: n.appName, summary: n.summary, body: n.body, urgency: n.urgency, timeout: n.expireTimeout, actions: n.actions.map(a => ({ id: a.identifier, text: a.text })), ref: n });
                n.closed.connect(() => root.dismiss(n.id));
            }
        }
    }
}
