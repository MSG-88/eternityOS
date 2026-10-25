import QtQuick
import Quickshell

// The Eternity shell: per screen the presence (background layer) and the status strip.
ShellRoot {
    Variants {
        model: Quickshell.screens
        delegate: Component {
            Scope {
                required property var modelData
                Presence { screen: modelData }
                Strip { screen: modelData }
            }
        }
    }
}
