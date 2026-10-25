pragma Singleton
import QtQuick
import Quickshell

// Registry of the panel screen's launcher window (one global shortcut must drive one surface).
Singleton {
    property var panelLauncher: null
}
