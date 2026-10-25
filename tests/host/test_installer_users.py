"""The installer's user page must accept the owner's own choice of password: this is a personal OS.
Found on the Hyper-V install attempt (2026-10-25): libpwquality's dictionary check refused a plain
word even though length and character classes were already relaxed.
Run: python3 -m unittest tests/host/test_installer_users.py"""
import os
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
USERS = "config/includes.chroot/etc/calamares/modules/users.conf"


def read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class TestInstallerUsers(unittest.TestCase):
    def test_weak_passwords_are_the_owners_choice(self):
        s = read(USERS)
        self.assertIn("allowWeakPasswords: true", s)
        self.assertIn("allowWeakPasswordsDefault: true", s)

    def test_dictionary_and_similarity_checks_off(self):
        s = read(USERS)
        for opt in ("dictcheck=0", "usercheck=0", "minlen=0", "minclass=0"):
            self.assertIn("- " + opt, s, opt)


if __name__ == "__main__":
    unittest.main()
