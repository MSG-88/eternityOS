import QtQuick

// The visible notification cards stacked top-right under the strip (12 px below it, 28 px from the
// right edge), newest at the bottom; a held badge when more are queued or DND holds them.
Item {
    id: root
    property real k: 1
    property real screenWidth: 1920
    width: screenWidth; height: 1080 * k
    Column {
        id: stack
        anchors.right: parent.right; anchors.rightMargin: 28 * root.k
        y: (Theme.stripHeight + 12) * root.k
        spacing: 10 * root.k
        Repeater {
            id: rep
            model: Notifications.visible
            NotifyCard {
                required property var modelData
                k: root.k; item: modelData
                onDismissed: id => { if (item.ref) { try { item.ref.dismiss(); } catch (e) {} } Notifications.dismiss(id); }
                onAction: (id, actionId) => { if (item.ref) { try { const a = item.ref.actions.find(x => x.identifier === actionId); if (a) a.invoke(); } catch (e) {} } Notifications.dismiss(id); }
            }
        }
        Text {
            visible: Notifications.held > 0
            anchors.right: parent.right
            text: Notifications.held + (Notifications.dnd ? " held \u00b7 do not disturb" : " more")
            color: Theme.n500; font.family: Theme.body; font.pixelSize: 12 * root.k
        }
    }
    function geometry() {
        const out = {};
        for (let i = 0; i < rep.count; i++) { const c = rep.itemAt(i); if (c) { const p = c.mapToItem(root, 0, 0); out["card" + i] = [p.x, p.y, c.width, c.height, c.item.app]; } }
        return out;
    }
    function flags() { return { cards_visible: rep.count, held: Notifications.held, queued: Notifications.queued.length, dnd: Notifications.dnd }; }
}
