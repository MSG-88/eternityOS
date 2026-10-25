import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Hyprland

// The launcher and the window ring as one overlay surface on the panel screen: shown by the
// daemon's launcher.show event (eternity-launcher, Super released alone) or the Quickshell
// global shortcut quickshell:window-ring (Super+Tab); Esc or Enter closes.
PanelWindow {
    id: win
    property real k: Geometry.forScreen(screen)
    readonly property bool panel: Geometry.isPanel(screen ? screen.name : "", Quickshell.screens.map(s => s.name))
    property string mode: ""         // "" | "launcher" | "windows"
    visible: mode !== "" && panel
    anchors { top: true; bottom: true; left: true; right: true }
    exclusionMode: ExclusionMode.Ignore
    color: "transparent"
    WlrLayershell.namespace: "eternity-launcher"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: visible ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None
    Rectangle { anchors.fill: parent; color: Qt.rgba(Theme.bg.r, Theme.bg.g, Theme.bg.b, 0.55); MouseArea { anchors.fill: parent; onClicked: win.mode = "" } }
    Sweep { id: sweep; k: win.k }
    LauncherContent {
        id: launcher
        anchors.fill: parent; k: win.k; visible: win.mode === "launcher"
        onClosed: win.mode = ""
        focus: visible
        Keys.onPressed: event => { if (keyPressed(event)) event.accepted = true; }
    }
    WindowRingContent {
        id: ring
        anchors.fill: parent; k: win.k; visible: win.mode === "windows"
        onClosed: win.mode = ""
        onFocusRequested: id => { try { const a = String(id); Hyprland.dispatch("focuswindow address:" + (a.indexOf("0x") === 0 ? a : "0x" + a)); } catch (e) {} }
        focus: visible
        Keys.onPressed: event => { if (keyPressed(event)) event.accepted = true; }
    }
    function open(which) {
        if (!win.panel) return;
        if (which === "launcher") { launcher.query = ""; launcher.load(); }
        else {
            try { const mon = Hyprland.monitorFor(screen); ring.windows = Hyprland.toplevels.values.filter(t => !mon || !t.monitor || t.monitor === mon).map(t => ({ id: t.address, title: t.title, app: t.wayland ? t.wayland.appId : "" })); } catch (e) { ring.windows = []; }
            ring.query = "";
        }
        win.mode = which;
        sweep.play();
    }
    // Super released alone: the launcher; while the window ring is open it selects (spec: release selects)
    Connections { target: Daemon; function onEvent(name, data) { if (name !== "launcher.show" || !win.panel) return; if (win.mode === "windows") ring.submit(); else win.open(win.mode === "launcher" ? "" : "launcher"); } }
    // Super+Tab (one global shortcut for the whole shell, see shell.qml): first press opens, further presses cycle
    function windowRingPressed() { if (!win.panel) return; if (win.mode === "windows") ring.move(1); else win.open("windows"); }
    Component.onCompleted: if (panel) Rings.panelLauncher = win
}
