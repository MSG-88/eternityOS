import QtQuick

// A ring of tiles (design scene 06): up to 12 per page on the 1.35r x r ellipse around (960, 540),
// r 150 -> 350 easeOutBack with 70 ms stagger, 64 px tiles (radius 14, surface, shadow-sm; the
// selected one with the accent ring + glow), label under each, "Type to filter · <query>" at y 100.
// Generic: `items` = [{id, label, sub}]; the launcher and the window ring feed it.
Item {
    id: root
    property real k: 1
    property var items: []
    property string query: ""
    property int page: 0
    property int selected: 0
    property bool animated: !Theme.reduced
    property var launched: []
    signal activated(var item)
    signal closed()
    function filterItems(items, query) {
        const q = String(query || "").toLowerCase();
        return (items || []).filter(it => q === "" || String(it.label).toLowerCase().indexOf(q) >= 0 || String(it.sub || "").toLowerCase().indexOf(q) >= 0);
    }
    readonly property var filtered: filterItems(root.items, root.query)
    readonly property int pages: Math.max(1, Math.ceil((filtered || []).length / 12))
    readonly property var visibleItems: (filtered || []).slice(page * 12, page * 12 + 12)
    property real r: animated ? 150 : 350
    property real drift: 0
    onQueryChanged: { root.page = 0; root.selected = 0; }
    onFilteredChanged: { if (root.page >= root.pages) root.page = 0; if (root.selected >= (root.visibleItems || []).length) root.selected = 0; }

    Text {
        id: filterLine
        anchors.horizontalCenter: parent.horizontalCenter; y: 100 * root.k
        color: Theme.n500; font.family: Theme.body; font.pixelSize: 15 * root.k
        text: root.filtered.length === 0 && root.query !== "" ? ("No match for " + root.query)
              : ("Type to filter \u00b7 " + root.query + (root.pages > 1 ? ("   \u00b7   page " + (root.page + 1) + " of " + root.pages) : ""))
        Text { visible: root.query !== "" && root.filtered.length > 0; text: root.query; color: Theme.accent300; font: parent.font; x: parent.width - root.query.length * 0; opacity: 0 }
    }
    Repeater {
        id: rep
        model: root.visibleItems
        Item {
            id: tile
            required property var modelData
            required property int index
            readonly property real angle: (index / Math.max(1, root.visibleItems.length)) * Math.PI * 2 - Math.PI / 2 + root.drift
            readonly property bool sel: index === root.selected
            width: 88 * root.k; height: 100 * root.k
            x: 960 * root.k + Math.cos(angle) * root.r * 1.35 * root.k - 44 * root.k
            y: 540 * root.k + Math.sin(angle) * root.r * root.k - 44 * root.k
            scale: sel ? 1.12 : 1
            Rectangle {
                id: box
                x: 12 * root.k; y: 12 * root.k; width: 64 * root.k; height: 64 * root.k; radius: Theme.radiusLg * root.k   // box centred on the ellipse point
                color: Theme.surface; border.width: Math.max(1, Math.round(root.k)); border.color: tile.sel ? Theme.accent : Theme.n800
                Rectangle { visible: tile.sel; anchors.fill: parent; anchors.margins: -6 * root.k; radius: parent.radius + 6 * root.k; color: "transparent"; border.width: 6 * root.k; border.color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.2); z: -1 }
                Text { anchors.centerIn: parent; text: String(tile.modelData.label).slice(0, 2); color: tile.sel ? Theme.accent300 : Theme.n400; font.family: Theme.body; font.pixelSize: 18 * root.k; font.weight: Font.Medium; font.letterSpacing: 0.7 * root.k }
                MouseArea { anchors.fill: parent; onClicked: { root.selected = tile.index; root.submit(); } }
            }
            Text { anchors.horizontalCenter: parent.horizontalCenter; y: 84 * root.k; text: tile.modelData.label; color: tile.sel ? Theme.text : Theme.n500; font.family: Theme.body; font.pixelSize: 12 * root.k; elide: Text.ElideRight; width: 120 * root.k; horizontalAlignment: Text.AlignHCenter }
        }
    }
    NumberAnimation on r { running: root.animated; from: 150; to: 350; duration: Theme.popMs; easing.type: Easing.OutBack }
    NumberAnimation on drift { running: root.animated; loops: Animation.Infinite; from: 0; to: Math.PI * 2; duration: 209440 }   // 0.03 rad/s

    function submit() {
        const it = root.visibleItems[root.selected];
        if (!it) return false;
        const l = root.launched.slice(); l.push(it.id); root.launched = l;
        root.activated(it);
        return true;
    }
    function move(delta) { const n = root.visibleItems.length; if (n) root.selected = (root.selected + delta + n) % n; }
    function nextPage() { root.page = (root.page + 1) % root.pages; root.selected = 0; }
    function keyPressed(event) {
        if (event.key === Qt.Key_Escape) { root.closed(); return true; }
        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) { root.submit(); return true; }
        if (event.key === Qt.Key_Right || event.key === Qt.Key_Down || event.key === Qt.Key_Tab) { root.move(1); return true; }
        if (event.key === Qt.Key_Left || event.key === Qt.Key_Up) { root.move(-1); return true; }
        if (event.key === Qt.Key_PageDown) { root.nextPage(); return true; }
        if (event.key === Qt.Key_Backspace) { root.query = root.query.slice(0, -1); return true; }
        if (event.text && event.text >= " ") { root.query += event.text; return true; }
        return false;
    }
    function geometry() {
        const out = { filter: [filterLine.x, filterLine.y, filterLine.width, filterLine.height, filterLine.text] };
        for (let i = 0; i < rep.count; i++) { const t = rep.itemAt(i); if (t) out["tile" + i] = [t.x + 12 * root.k, t.y + 12 * root.k, 64 * root.k, 64 * root.k, t.modelData.label]; }
        return out;
    }
    function flags() {
        const sel = root.visibleItems[root.selected];
        return { tile_count: rep.count, selected: sel ? sel.label : "", query: root.query, launched: root.launched, page: root.page, pages: root.pages };
    }
}
