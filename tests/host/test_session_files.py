"""Build 13: the Eternity Wayland session is packaged (packages, backports pin, session entry,
launcher script, live-config switch). Run: python3 -m unittest tests/host/test_session_files.py"""
import os
import re
import subprocess
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")


def read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class TestSessionFiles(unittest.TestCase):
    def test_session_entry(self):
        d = read("config/includes.chroot/usr/share/wayland-sessions/eternity.desktop")
        self.assertIn("Exec=eternity-session", d)
        self.assertIn("Name=Eternity", d)
        self.assertIn("DesktopNames=Eternity", d)

    def test_packages(self):
        pk = read("config/package-lists/desktop.list.chroot")
        for p in ("hyprland", "quickshell", "hypridle", "xdg-desktop-portal-hyprland", "xdg-desktop-portal-gtk",
                  "qml6-module-qtquick-shapes", "qml6-module-qtquick-effects", "qml6-module-qt5compat-graphicaleffects",
                  "qt6-wayland", "wl-clipboard", "grim", "slurp", "fonts-jetbrains-mono"):
            self.assertTrue(re.search(rf"^{re.escape(p)}$", pk, re.M), p)

    def test_backports_pin(self):
        pref = read("config/archives/eternity-backports.pref.chroot")
        self.assertIn("Package: hyprland quickshell hypridle xdg-desktop-portal-hyprland hyprland-protocols hyprutils* hyprlang* hyprcursor* hyprgraphics* aquamarine*", pref)
        self.assertIn("Pin: release n=trixie-backports", pref)
        self.assertIn("Pin-Priority: 600", pref)

    def test_session_script_parses(self):
        path = os.path.join(ROOT, "config/includes.chroot/usr/local/bin/eternity-session")
        subprocess.run(["sh", "-n", path], check=True)
        s = read("config/includes.chroot/usr/local/bin/eternity-session")
        self.assertIn("XDG_CURRENT_DESKTOP=Eternity", s)
        self.assertIn("eternity-theme render", s)
        self.assertIn("exec Hyprland", s)
        self.assertIn("WLR_RENDERER_ALLOW_SOFTWARE=1", s)

    def test_live_config_component(self):
        s = read("config/includes.chroot/usr/lib/live/config/0032-eternity-session")
        self.assertIn("eternity.session=", s)
        self.assertIn("20-session.conf", s)
        subprocess.run(["sh", "-n", os.path.join(ROOT, "config/includes.chroot/usr/lib/live/config/0032-eternity-session")], check=True)

    def test_hook_parses(self):
        path = os.path.join(ROOT, "config/hooks/normal/0460-session.hook.chroot")
        subprocess.run(["sh", "-n", path], check=True)
        self.assertIn("eternity-session", read("config/hooks/normal/0460-session.hook.chroot"))

    def test_smoke_has_check_session(self):
        s = read("tests/smoke.sh")
        self.assertIn("check_session()", s)
        self.assertIn("eternity-theme render --check", s)


if __name__ == "__main__":
    unittest.main()
