"""eternity-theme: Nocturne tokens + layout + keys -> hyprland.conf, Theme.qml, gtk.css.
Run: python3 -m unittest tests/host/test_theme.py"""
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
PYROOT = os.path.join(ROOT, "config", "includes.chroot", "usr", "lib", "eternity", "py")
SHARE = os.path.join(ROOT, "config", "includes.chroot", "usr", "share", "eternity")
sys.path.insert(0, PYROOT)
os.environ["ETERNITY_SHARE"] = SHARE

from eternity import theme  # noqa: E402


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


class Base(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        os.environ["HOME"] = self.home
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.home, ".config")
        self.out = tempfile.mkdtemp()


class TestRender(Base):
    def test_defaults_render(self):
        files = theme.render(self.out)
        self.assertEqual(sorted(os.path.basename(f) for f in files), ["Theme.qml", "gtk.css", "hyprland.conf", "theme.json"])
        import json
        self.assertEqual(json.load(open(os.path.join(self.out, "theme.json")))["color"]["accent"], "#9184d9")
        hypr = read(os.path.join(self.out, "hyprland.conf"))
        qml = read(os.path.join(self.out, "Theme.qml"))
        css = read(os.path.join(self.out, "gtk.css"))
        self.assertIn("monitor=eDP-1,preferred,auto,1.25", hypr)      # the laptop panel
        self.assertIn("monitor=,preferred,auto,1\n", hypr)             # external outputs: external_scale (1.0)
        self.assertIn("col.active_border = rgb(9184d9)", hypr)
        self.assertIn("col.inactive_border = rgb(3f424d)", hypr)
        self.assertIn("gaps_in = 6", hypr)
        self.assertIn("gaps_out = 12", hypr)
        self.assertIn("rounding = 8", hypr)
        self.assertIn("bind = SUPER, space, exec, eternity-ask --show", hypr)
        self.assertIn("bindr = SUPER, Super_L, exec, eternity-launcher", hypr)   # release of Super alone, not every Super press
        self.assertIn("bind = SUPER, Tab, global, quickshell:window-ring", hypr)    # the window ring is a Quickshell global shortcut
        self.assertNotIn("code:133", hypr)
        self.assertIn("allow_session_lock_restore = true", hypr)
        self.assertIn("exec-once = eternity-supervise eternity-daemon", hypr)
        self.assertIn("exec-once = eternity-supervise quickshell -c eternity", hypr)
        self.assertIn("exec-once = /usr/libexec/polkit-mate-authentication-agent-1", hypr)
        self.assertIn("exec-once = eternity-firstrun --autostart", hypr)
        self.assertIn("bind = SUPER, L, exec, eternity-lock", hypr)
        # Hyprland 0.53+ rule syntax (0.55 shows the old forms as config errors on screen)
        self.assertIn("layerrule = blur on, match:namespace eternity-bar", hypr)
        self.assertIn("layerrule = ignore_alpha 0, match:namespace eternity-bar", hypr)
        self.assertNotIn("windowrulev2", hypr)
        self.assertIn("windowrule = match:class ^(eternity-firstrun)$, float on", hypr)
        self.assertIn("gesture = 3, horizontal, workspace", hypr)
        for gone in ("workspace_swipe =", "vfr =", "pseudotile ="):
            self.assertNotIn(gone, hypr, gone)
        self.assertIn("exec-once = hypridle -c /usr/share/eternity/hypridle.conf", hypr)
        self.assertIn("enabled = true", hypr.split("animations {")[1].split("}")[0])
        self.assertIn("pragma Singleton", qml)
        self.assertIn('readonly property color accent: "#9184d9"', qml)
        self.assertIn('readonly property color n800: "#3f424d"', qml)
        self.assertIn("readonly property int enterMs: 700", qml)
        self.assertIn("readonly property real glow: 1.0", qml)
        self.assertIn('readonly property string tech: "Michroma"', qml)
        self.assertIn("readonly property int radiusLg: 14", qml)
        self.assertIn("readonly property real scale: 1.25", qml)
        self.assertIn("@define-color accent #9184d9;", css)
        self.assertIn("@define-color bg #161826;", css)

    def test_user_override(self):
        os.makedirs(os.path.join(self.home, ".config", "eternity"))
        with open(os.path.join(self.home, ".config", "eternity", "theme.toml"), "w") as f:
            f.write('[color]\naccent = "#2ec4b6"\n')
        with open(os.path.join(self.home, ".config", "eternity", "layout.toml"), "w") as f:
            f.write("scale = 1.0\n")
        theme.render(self.out)
        self.assertIn("monitor=eDP-1,preferred,auto,1\n", read(os.path.join(self.out, "hyprland.conf")))
        self.assertIn('accent: "#2ec4b6"', read(os.path.join(self.out, "Theme.qml")))
        self.assertIn("col.active_border = rgb(2ec4b6)", read(os.path.join(self.out, "hyprland.conf")))

    def test_reduced_motion_disables_animations(self):
        os.makedirs(os.path.join(self.home, ".config", "eternity"))
        with open(os.path.join(self.home, ".config", "eternity", "theme.toml"), "w") as f:
            f.write("[motion]\nreduced = true\n")
        theme.render(self.out)
        hypr = read(os.path.join(self.out, "hyprland.conf"))
        self.assertIn("enabled = false", hypr.split("animations {")[1].split("}")[0])
        self.assertIn("readonly property bool reduced: true", read(os.path.join(self.out, "Theme.qml")))

    def test_validate_rejects_bad_values(self):
        self.assertTrue(theme.validate({"theme": {"color": {"accent": "teal"}}}))
        self.assertTrue(theme.validate({"layout": {"scale": 9}}))
        self.assertEqual(theme.validate(theme.load()), [])

    def test_bad_user_file_is_reported_not_fatal(self):
        os.makedirs(os.path.join(self.home, ".config", "eternity"))
        with open(os.path.join(self.home, ".config", "eternity", "layout.toml"), "w") as f:
            f.write("scale = [\n")
        cfg = theme.load()
        self.assertEqual(cfg["layout"]["scale"], 1.25)
        self.assertTrue(cfg["_errors"])

    def test_cli_check_and_render(self):
        env = dict(os.environ, PYTHONPATH=PYROOT)
        r = subprocess.run([sys.executable, "-c", "from eternity import theme; raise SystemExit(theme.main(['render', '--check']))"],
                           env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = subprocess.run([sys.executable, "-c", "from eternity import theme; raise SystemExit(theme.main(['render']))"],
                           env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.exists(os.path.join(self.home, ".config", "eternity", "generated", "hyprland.conf")))


class TestPresets(unittest.TestCase):
    def test_shipped_presets_validate(self):
        presets = theme.presets()
        ids = [p["id"] for p in presets]
        for n in ("nocturne", "nocturne-light", "mono", "high-contrast", "quiet"):
            self.assertIn(n, ids)
        for p in presets:
            cfg = theme.load()
            cfg["theme"] = theme._merge(cfg["theme"], p.get("theme", {}))
            cfg["layout"] = theme._merge(cfg["layout"], p.get("layout", {}))
            self.assertEqual(theme.validate(cfg), [], p["id"])
        light = next(p for p in presets if p["id"] == "nocturne-light")
        self.assertNotEqual(light["theme"]["color"]["bg"], "#161826")
        quiet = next(p for p in presets if p["id"] == "quiet")
        self.assertTrue(quiet["theme"]["motion"]["reduced"])


class TestDefaultsFiles(unittest.TestCase):
    def test_shipped_defaults_exist(self):
        for n in ("theme.toml", "layout.toml", "keys.toml", "hyprland.base.conf", "hypridle.conf"):
            self.assertTrue(os.path.exists(os.path.join(SHARE, n)), n)


if __name__ == "__main__":
    unittest.main()
