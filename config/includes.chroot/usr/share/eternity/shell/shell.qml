import QtQuick
import Quickshell

// The Eternity shell: one strip per screen (slice 1). Presence, bar, lock follow in later tasks.
ShellRoot {
    Variants {
        model: Quickshell.screens
        delegate: Component { Strip { required property var modelData; screen: modelData } }
    }
}
