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
        onFocusRequested: id => { try { Hyprland.dispatch("focuswindow address:" + id); } catch (e) {} }
        focus: visible
        Keys.onPressed: event => { if (keyPressed(event)) event.accepted = true; }
    }
    function open(which) {
        if (!win.panel) return;
        if (which === "launcher") { launcher.query = ""; launcher.load(); }
        else {
            try { ring.windows = Hyprland.toplevels.values.map(t => ({ id: t.address, title: t.title, app: t.wayland ? t.wayland.appId : "" })); } catch (e) { ring.windows = []; }
            ring.query = "";
        }
        win.mode = which;
        sweep.play();
    }
    Connections { target: Daemon; function onEvent(name, data) { if (name === "launcher.show") win.open(win.mode === "launcher" ? "" : "launcher"); } }
    GlobalShortcut { name: "window-ring"; appid: "quickshell"; onPressed: win.open("windows"); onReleased: { if (win.mode === "windows") ring.submit(); } }
}
