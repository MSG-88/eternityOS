import QtQuick
import Quickshell
import Quickshell.Hyprland

// The Eternity shell: per screen the presence (background layer), the status strip and the Ask bar; one session lock.
ShellRoot {
    Lock {}
    // one registration per client: a second GlobalShortcut with the same name is a protocol error
    GlobalShortcut { name: "window-ring"; appid: "quickshell"; onPressed: { if (Rings.panelLauncher) Rings.panelLauncher.windowRingPressed(); } }
    SettingsWindow {}
    MonitorWindow {}
    Variants {
        model: Quickshell.screens
        delegate: Component {
            Scope {
                required property var modelData
                Presence { screen: modelData }
                Strip { screen: modelData }
                Bar { screen: modelData }
                Launcher { screen: modelData }
                Overlay { screen: modelData }
            }
        }
    }
}
