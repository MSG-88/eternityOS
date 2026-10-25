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
        self.assertIn("Package: hyprland quickshell hypridle", pref)
        for p in ("libhypr*", "libaquamarine*", "libxkbcommon*", "wayland-protocols"):
            self.assertIn(p, pref)   # hyprland 0.55 needs these from backports too (build 13 attempt 2)
        self.assertIn("Pin: release n=trixie-backports", pref)
        self.assertIn("Pin-Priority: 600", pref)

    def test_session_script_parses(self):
        path = os.path.join(ROOT, "config/includes.chroot/usr/local/bin/eternity-session")
        subprocess.run(["sh", "-n", path], check=True)
        s = read("config/includes.chroot/usr/local/bin/eternity-session")
        self.assertIn("XDG_CURRENT_DESKTOP=Eternity", s)
        self.assertIn("eternity-theme render", s)
        self.assertIn("exec start-hyprland", s)        # Hyprland 0.55 warns on screen when started bare
        # build 14: start-hyprland does not forward --config and Hyprland came up with its default config;
        # HYPRLAND_CONFIG is honoured through the wrapper and bare
        self.assertRegex(s, r'export HYPRLAND_CONFIG="\$CFG/hyprland.conf"')
        self.assertNotIn("start-hyprland --config", s)
        self.assertIn("exec Hyprland", s)              # fallback when the wrapper is missing
        self.assertIn("WLR_RENDERER_ALLOW_SOFTWARE=1", s)

    def test_session_never_forces_software_gl_on_hyprland(self):
        # Build 13 diagnosis: with LIBGL_ALWAYS_SOFTWARE=1 Mesa refuses Hyprland's explicit EGL device
        # ("Not allowed to force software rendering when API explicitly selects a hardware device")
        # and Hyprland crashes before the shell starts. Mesa falls back to kms_swrast by itself.
        s = read("config/includes.chroot/usr/local/bin/eternity-session")
        self.assertFalse(re.search(r"^\s*export LIBGL_ALWAYS_SOFTWARE", s, re.M), "LIBGL_ALWAYS_SOFTWARE exported")
        self.assertIn("AQ_NO_MODIFIERS=1", s)
        self.assertIn("QT_QUICK_BACKEND=software", s)
        self.assertRegex(s, r"mkdir -p .*\.cache\}?/hyprland")   # Hyprland's crash-report directory must exist

    def test_live_config_component(self):
        s = read("config/includes.chroot/usr/lib/live/config/0032-eternity-session")
        self.assertIn("eternity.session=", s)
        self.assertIn("20-session.conf", s)
        subprocess.run(["sh", "-n", os.path.join(ROOT, "config/includes.chroot/usr/lib/live/config/0032-eternity-session")], check=True)

    def test_hook_parses(self):
        path = os.path.join(ROOT, "config/hooks/normal/0460-session.hook.chroot")
        subprocess.run(["sh", "-n", path], check=True)
        self.assertIn("eternity-session", read("config/hooks/normal/0460-session.hook.chroot"))

    def test_grub_entry_for_the_session(self):
        g = read("config/bootloaders/grub-pc/grub.cfg")
        # build 15: the Eternity shell is the first entry; XFCE is "Classic desktop"
        self.assertIn('menuentry "Eternity 08 Live" --hotkey=l {' + chr(10) + '    linux @KERNEL_LIVE@ @APPEND_LIVE@ eternity.session=eternity', g)
        self.assertIn('menuentry "Eternity 08 Live (Classic desktop)"', g)
        self.assertNotIn('(Eternity shell)"', g)

    def test_eternity_is_the_default_session_everywhere(self):
        self.assertIn("user-session=eternity", read("config/includes.chroot/etc/lightdm/lightdm.conf.d/10-eternity.conf"))
        dm = read("config/includes.chroot/etc/calamares/modules/displaymanager.conf")
        self.assertIn('executable: "eternity-session"', dm)
        self.assertIn('desktopFile: "eternity"', dm)

    def test_visual_runner_has_session_mode(self):
        r = read("tests/run-qemu-visual.sh")
        for needle in ("--session", "e-desktop.png", "e-ask.png", "e-answer.png", "e-lock.png", "e-unlocked.png", "e-terminal.png", "hyprctl layers"):
            self.assertIn(needle, r)
        subprocess.run(["bash", "-n", os.path.join(ROOT, "tests/run-qemu-visual.sh")], check=True)

    def test_chain13(self):
        c = read("tools/dev/chain-build13.sh")
        for needle in ("build13-run.log", "BUILD13 DONE", "run-qemu-visual.sh\" \"$ISO\" --session eternity", "run-qemu-smoke.sh", "boot-fallback", "run-qemu-bios.sh", "run-qemu-usb.sh"):
            self.assertIn(needle, c)
        subprocess.run(["bash", "-n", os.path.join(ROOT, "tools/dev/chain-build13.sh")], check=True)
        subprocess.run(["bash", "-n", os.path.join(ROOT, "tools/dev/start-chain13.sh")], check=True)

    def test_review_fixes_in_config(self):
        """Branch review 2026-10-25: C1 hook executable, C3 lock never falls open, I2 supervision."""
        out = subprocess.run(["git", "ls-files", "-s", "config/includes.chroot/usr/lib/eternity/claude-hook"], cwd=ROOT,
                             capture_output=True, text=True).stdout.split()
        if out:
            self.assertEqual(out[0], "100755")
        else:   # a git worktree under WSL cannot resolve its Windows gitdir: check the file mode instead
            self.assertTrue(os.access(os.path.join(ROOT, "config/includes.chroot/usr/lib/eternity/claude-hook"), os.X_OK))
        self.assertIn("claude-hook", read("config/hooks/normal/0460-session.hook.chroot"))
        lock = read("config/includes.chroot/usr/local/bin/eternity-lock")
        self.assertNotIn("loginctl", lock)
        self.assertIn("locked", lock)
        sup = read("config/includes.chroot/usr/local/bin/eternity-supervise")
        self.assertIn("while", sup)
        subprocess.run(["sh", "-n", os.path.join(ROOT, "config/includes.chroot/usr/local/bin/eternity-supervise")], check=True)
        subprocess.run(["sh", "-n", os.path.join(ROOT, "config/includes.chroot/usr/local/bin/eternity-lock")], check=True)

    def test_greeter_files(self):
        """Slice 2 Task 1: greetd + cage run the Eternity unlock scene as the greeter."""
        pk = read("config/package-lists/desktop.list.chroot")
        for p in ("greetd", "cage"):
            self.assertTrue(re.search(rf"^{p}$", pk, re.M), p)
        cfg = read("config/includes.chroot/etc/greetd/config.toml")
        self.assertIn('command = "eternity-greeter"', cfg)          # the wrapper decides cage vs text fallback
        self.assertNotIn("cage -s", cfg)
        self.assertIn('user = "_greetd"', cfg)
        g = read("config/includes.chroot/usr/local/bin/eternity-greeter")
        subprocess.run(["sh", "-n", os.path.join(ROOT, "config/includes.chroot/usr/local/bin/eternity-greeter")], check=True)
        self.assertIn("users.json", g)
        self.assertIn("cage -s -- eternity-greeter-scene", g)       # the scene runs under cage ...
        self.assertLess(g.index("cage -s"), g.index("exec agreety"))   # ... and agreety runs after cage has exited, on the VT
        self.assertNotIn("$5", g)                                     # no GECOS in the JSON
        scene = read("config/includes.chroot/usr/local/bin/eternity-greeter-scene")
        subprocess.run(["sh", "-n", os.path.join(ROOT, "config/includes.chroot/usr/local/bin/eternity-greeter-scene")], check=True)
        self.assertIn("quickshell", scene)
        tmpfiles = read("config/includes.chroot/usr/lib/tmpfiles.d/eternity-greeter.conf")
        self.assertIn("d /run/eternity-greeter 0755 _greetd _greetd", tmpfiles)
        dropin = read("config/includes.chroot/etc/systemd/system/greetd.service.d/eternity.conf")
        self.assertIn("OnFailure=lightdm.service", dropin)
        self.assertTrue(os.path.exists(os.path.join(ROOT, "config/includes.chroot/usr/share/eternity/greeter/shell.qml")))
        hook = read("config/hooks/normal/0460-session.hook.chroot")
        for f in ("LockContent.qml", "GreeterContent.qml", "Theme.qml", "Geometry.qml", "Mobius.qml", "Wordmark.qml", "SystemClockFallback.qml"):
            self.assertIn(f, hook)                       # shared scene files copied into the greeter's config root

    def test_greeter_fallback(self):
        """eternity.greeter=greetd switches the display manager; without it lightdm stays enabled."""
        s = read("config/includes.chroot/usr/lib/live/config/0032-eternity-session")
        self.assertIn("eternity.greeter=", s)
        branch = s[s.index("greetd)"):]
        self.assertIn("systemctl mask --runtime lightdm", branch)      # the queued lightdm job must not run on this boot
        self.assertIn("--no-block start greetd", branch)
        self.assertNotIn("systemctl mask", s[:s.index("greetd)")])
        hook = read("config/hooks/normal/0460-session.hook.chroot")
        self.assertIn("org.xfce.xfce4-notifyd.Notifications.service", hook)   # no D-Bus activation of xfce4-notifyd in the Eternity session
        self.assertIn("xfce4-notifyd.service", hook)
        smoke = read("tests/smoke.sh")
        self.assertIn("greeter/shell.qml", smoke)

    def test_build14_visual_and_chain(self):
        """Slice 2 Task 6: the Eternity visual run exercises launcher, notifications, Settings, Monitor and the greeter."""
        r = read("tests/run-qemu-visual.sh")
        for needle in ("e-launcher.png", "e-notify.png", "e-settings.png", "e-monitor.png", "e-greeter.png", "notify-send", "--session eternity-greetd"):
            self.assertIn(needle, r)
        g = read("config/bootloaders/grub-pc/grub.cfg")
        self.assertIn("eternity.session=eternity eternity.greeter=greetd", g)
        self.assertLess(g.index('"Eternity 08 Live" --hotkey=l'), g.index("eternity.greeter=greetd"))
        c = read("tools/dev/chain-build14.sh")
        for needle in ("build14-run.log", "BUILD14 DONE", "--session eternity-greetd", "run-qemu-smoke.sh"):
            self.assertIn(needle, c)
        subprocess.run(["bash", "-n", os.path.join(ROOT, "tools/dev/chain-build14.sh")], check=True)
        subprocess.run(["bash", "-n", os.path.join(ROOT, "tools/dev/start-chain14.sh")], check=True)
        q = read("tests/qmp.py")
        for needle in ('"Super"', '"Super-M"', '"Super-Comma"'):
            self.assertIn(needle, q)

    def test_smoke_has_check_session(self):
        s = read("tests/smoke.sh")
        self.assertIn("check_session()", s)
        self.assertIn("eternity-theme render --check", s)


if __name__ == "__main__":
    unittest.main()
