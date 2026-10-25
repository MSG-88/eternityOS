import QtQuick
import Quickshell

// The Eternity shell: per screen the presence (background layer), the status strip and the Ask bar; one session lock.
ShellRoot {
    Lock {}
    Variants {
        model: Quickshell.screens
        delegate: Component {
            Scope {
                required property var modelData
                Presence { screen: modelData }
                Strip { screen: modelData }
                Bar { screen: modelData }
            }
        }
    }
}
