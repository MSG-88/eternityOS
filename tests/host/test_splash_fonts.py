"""The Plymouth splash text must use a font that exists at the same path in the initramfs and in the
real root. Build 13 drew boxes: inside the initramfs "Sans" resolved to /usr/share/fonts/Plymouth.ttf,
a symlink Debian's plymouth hook creates only there; after `plymouth --newroot` the daemon kept that
path, cairo could not open it, and Pango stroked a box per glyph.
Run: python3 -m unittest tests/host/test_splash_fonts.py"""
import os
import re
import subprocess
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
HOOK = "config/includes.chroot/etc/initramfs-tools/hooks/eternity-fonts"
SCRIPT = "config/includes.chroot/usr/share/plymouth/themes/eternity/eternity.script"
THEME_HOOK = "config/hooks/normal/0200-theme.hook.chroot"
INTER = "/usr/share/fonts/opentype/inter/Inter-Regular.otf"
MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Regular.ttf"


def read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class TestSplashFonts(unittest.TestCase):
    def test_theme_script_names_a_shipped_family_not_sans(self):
        s = read(SCRIPT)
        fonts = re.findall(r'Image\.Text\([^;]*?"([A-Za-z ]+ \d+)"\)', s)
        self.assertTrue(fonts, "no Image.Text font names found")
        for f in fonts:
            self.assertTrue(f.startswith("Inter ") or f.startswith("JetBrains Mono "), f)
        self.assertNotIn('"Sans', s)

    def test_initramfs_hook_ships_the_fonts_at_their_real_paths(self):
        s = read(HOOK)
        self.assertIn("prereqs", s)
        self.assertIn("copy_file font " + INTER, s)
        self.assertIn("copy_file font " + MONO, s)
        self.assertIn("/usr/share/fonts/Plymouth.ttf", s)       # the Debian symlink must resolve in both roots
        subprocess.run(["sh", "-n", os.path.join(ROOT, HOOK)], check=True)

    def test_initramfs_hook_is_executable_in_git(self):
        mode = subprocess.run(["git", "ls-files", "-s", HOOK], cwd=ROOT, capture_output=True, text=True).stdout
        self.assertTrue(mode.startswith("100755"), mode or "not in git")

    def test_real_root_gets_the_same_plymouth_symlinks(self):
        s = read(THEME_HOOK)
        self.assertIn("ln -sfn", s)
        self.assertIn("/usr/share/fonts/Plymouth.ttf", s)
        self.assertIn("/usr/share/fonts/Plymouth-monospace.ttf", s)
        self.assertIn("fc-match -f %{file}", s)                  # same choice as Debian's initramfs hook


if __name__ == "__main__":
    unittest.main()
