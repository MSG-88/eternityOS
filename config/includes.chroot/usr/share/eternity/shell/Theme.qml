pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

// Nocturne tokens. Defaults are the design system's; eternity-theme writes
// ~/.config/eternity/generated/theme.json from theme.toml/layout.toml and this singleton
// reads it at start (no hex literals anywhere else in the shell).
Singleton {
    id: root
    property var cfg: ({})
    function pick(section, key, dflt) {
        const s = root.cfg[section];
        return (s && s[key] !== undefined) ? s[key] : dflt;
    }
    readonly property color bg: pick("color", "bg", "#161826")
    readonly property color surface: pick("color", "surface", "#232532")
    readonly property color text: pick("color", "text", "#e9e9ed")
    readonly property color accent: pick("color", "accent", "#9184d9")
    readonly property color accent100: pick("color", "accent_100", "#f5f4ff")
    readonly property color accent200: pick("color", "accent_200", "#e7e5fe")
    readonly property color accent300: pick("color", "accent_300", "#d2cefd")
    readonly property color accent400: pick("color", "accent_400", "#b5abfc")
    readonly property color accent600: pick("color", "accent_600", "#796cbf")
    readonly property color accent700: pick("color", "accent_700", "#5d5294")
    readonly property color accent800: pick("color", "accent_800", "#423a6a")
    readonly property color accent900: pick("color", "accent_900", "#2b2741")
    readonly property color n400: pick("color", "n400", "#b2b6ca")
    readonly property color n500: pick("color", "n500", "#9397ab")
    readonly property color n600: pick("color", "n600", "#75798c")
    readonly property color n700: pick("color", "n700", "#595d6c")
    readonly property color n800: pick("color", "n800", "#3f424d")
    readonly property color n900: pick("color", "n900", "#292b31")
    readonly property string body: pick("font", "body", "Inter")
    readonly property string tech: pick("font", "tech", "Michroma")
    readonly property string mono: pick("font", "mono", "JetBrains Mono")
    readonly property int radiusSm: pick("radius", "sm", 4)
    readonly property int radiusMd: pick("radius", "md", 8)
    readonly property int radiusLg: pick("radius", "lg", 14)
    readonly property int enterMs: pick("motion", "enter_ms", 700)
    readonly property int drawMs: pick("motion", "draw_ms", 800)
    readonly property int popMs: pick("motion", "pop_ms", 600)
    readonly property int sweepMs: pick("motion", "sweep_ms", 800)
    readonly property int decodeCps: pick("motion", "decode_cps", 28)
    readonly property bool reduced: pick("motion", "reduced", false)
    readonly property real glow: pick("motion", "glow", 1.0)
    readonly property int stripHeight: pick("layout", "strip_height", 44)
    readonly property var bar: pick("layout", "bar", [560, 950, 800, 54])
    readonly property var orbit: pick("layout", "orbit", [440, 270])
    readonly property var cards: pick("layout", "cards", ["today", "system", "eternity", "recent", "install"])
    // easing curves of the design (cubic-bezier control points)
    readonly property var enter: [0.33, 1, 0.68, 1, 1, 1]          // easeOutCubic
    readonly property var draw: [0.37, 0, 0.63, 1, 1, 1]           // easeInOutSine
    readonly property var pop: [0.34, 1.56, 0.64, 1, 1, 1]         // easeOutBack

    FileView {
        id: file
        path: (Quickshell.env("XDG_CONFIG_HOME") || (Quickshell.env("HOME") + "/.config")) + "/eternity/generated/theme.json"
        blockLoading: true
        onLoaded: { try { root.cfg = JSON.parse(file.text()); } catch (e) { console.log("Theme: bad theme.json, using defaults"); } }
        onLoadFailed: console.log("Theme: no generated theme.json, using defaults")
    }
}
