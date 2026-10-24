"""Launcher index over .desktop files. Run: python3 -m unittest tests/host/test_launcher_index.py"""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "config", "includes.chroot", "usr", "lib", "eternity", "py"))

from eternity import launcher_index as LI  # noqa: E402

ENTRY = """[Desktop Entry]
Type=Application
Name={name}
Exec={exe}
Icon={icon}
Comment={comment}
Categories={cats}
Keywords={kw}
{extra}
"""


class LauncherIndexTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HOME"] = self.tmp.name
        os.environ["XDG_DATA_DIRS"] = os.path.join(self.tmp.name, "share")
        self.d = os.path.join(self.tmp.name, "share", "applications")
        os.makedirs(self.d)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, did, **kw):
        base = dict(name=did, exe=did + " %U", icon=did, comment="", cats="Utility;", kw="", extra="")
        base.update(kw)
        with open(os.path.join(self.d, did + ".desktop"), "w") as f:
            f.write(ENTRY.format(**base))

    def test_ordering_filtering_and_exec_cleanup(self):
        self.write("zzz-tool", name="Zed")
        self.write("thunar", name="Files", comment="Browse the file system", kw="folder;browse;")
        self.write("eternity-ask", name="Ask Eternity")
        self.write("hidden-one", extra="NoDisplay=true")
        self.write("gnome-only", extra="OnlyShowIn=GNOME;")
        self.write("screensaver-prefs", cats="Settings;Screensaver;")
        apps = LI.load()
        names = [a.name for a in apps]
        self.assertEqual(names[:2], ["Ask Eternity", "Files"], names)
        self.assertNotIn("hidden-one", names)
        self.assertNotIn("gnome-only", names)
        self.assertNotIn("screensaver-prefs", names)
        files = next(a for a in apps if a.name == "Files")
        self.assertEqual(files.exec_cmd, "thunar")
        self.assertIn("folder", files.keywords)
        self.assertEqual(files.desktop_id, "thunar")

    def test_broken_file_is_skipped(self):
        with open(os.path.join(self.d, "broken.desktop"), "w") as f:
            f.write("not an ini\n[[[")
        self.write("ok", name="Ok")
        self.assertEqual([a.name for a in LI.load()], ["Ok"])


if __name__ == "__main__":
    unittest.main()
