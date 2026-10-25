pragma Singleton
import QtQuick
import Quickshell

// (Named Geometry: "Scale" is a QtQuick transform type.) Design pixels (1920x1080 reference) -> logical pixels of an output: k = min(W/1920, H/1080).
Singleton {
    function k(w, h) { return Math.min(w / 1920, h / 1080); }
    function forScreen(screen) { return screen ? k(screen.width, screen.height) : 1; }
}
