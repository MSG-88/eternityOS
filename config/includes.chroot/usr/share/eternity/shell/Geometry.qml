pragma Singleton
import QtQuick
import Quickshell

// (Named Geometry: "Scale" is a QtQuick transform type.) Design pixels (1920x1080 reference) -> logical pixels of an output: k = min(W/1920, H/1080).
Singleton {
    function k(w, h) { return Math.min(w / 1920, h / 1080); }
    function forScreen(screen) { return screen ? k(screen.width, screen.height) : 1; }
    // The presence and the idle bar live on the laptop panel (eDP-*); when no panel exists, on the first screen.
    function isPanel(name, allNames) {
        if (!name) return false;
        if (name.indexOf("eDP") === 0) return true;
        const anyPanel = (allNames || []).some(n => n && n.indexOf("eDP") === 0);
        return !anyPanel && (allNames || []).length > 0 && allNames[0] === name;
    }
}
