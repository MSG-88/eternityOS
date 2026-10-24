"""Settings and secret store (file backend). Run: python3 -m unittest tests/host/test_settings.py"""
import json
import os
import stat
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "config", "includes.chroot", "usr", "lib", "eternity", "py"))
os.environ["ETERNITY_NO_KEYRING"] = "1"

from eternity import settings as S  # noqa: E402


class SettingsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["XDG_CONFIG_HOME"] = self.tmp.name
        os.environ["XDG_STATE_HOME"] = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_defaults_are_private_and_local(self):
        s = S.load()
        self.assertEqual(s.provider, "local")
        self.assertTrue(s.on_device_only)
        self.assertFalse(s.telemetry)
        self.assertFalse(s.first_run_done)
        self.assertEqual(s.unlock_methods, ["passphrase"])

    def test_round_trip_and_mode(self):
        s = S.Settings(name="Maya", verbosity="brief", proactive=False, unlock_methods=["passphrase", "pin"])
        S.save(s)
        self.assertEqual(stat.S_IMODE(os.stat(S.settings_path()).st_mode), 0o600)
        t = S.load()
        self.assertEqual((t.name, t.verbosity, t.proactive, t.unlock_methods), ("Maya", "brief", False, ["passphrase", "pin"]))

    def test_validation_fixes_bad_values(self):
        s = S.Settings(provider="skynet", verbosity="loud", voice="shout", unlock_methods=["retina"], trust_level=9, telemetry=True)
        s.validate()
        self.assertEqual(s.provider, "local")
        self.assertEqual(s.verbosity, "normal")
        self.assertEqual(s.voice, "off")
        self.assertEqual(s.unlock_methods, ["passphrase"])
        self.assertEqual(s.trust_level, 1)
        self.assertFalse(s.telemetry, "telemetry can never be switched on")

    def test_on_device_only_overrides_cloud_provider(self):
        s = S.Settings(provider="anthropic", on_device_only=True).validate()
        self.assertEqual(s.effective_provider(), "local")
        s = S.Settings(provider="anthropic", on_device_only=False).validate()
        self.assertEqual(s.effective_provider(), "anthropic")

    def test_unknown_keys_in_file_are_ignored(self):
        os.makedirs(S.config_dir(), exist_ok=True)
        with open(S.settings_path(), "w") as f:
            json.dump({"name": "Ola", "mystery": 1}, f)
        self.assertEqual(S.load().name, "Ola")

    def test_secret_store_file_backend(self):
        st = S.SecretStore(allow_keyring=False)
        self.assertEqual(st.backend, "file")
        self.assertIsNone(st.get("anthropic"))
        st.set("anthropic", " sk-ant-test ")
        self.assertEqual(st.get("anthropic"), "sk-ant-test")
        self.assertTrue(st.file_mode_ok())
        with open(S.settings_path(), "a"):
            pass
        with open(S.settings_path()) as f:
            self.assertNotIn("sk-ant", f.read(), "keys never land in settings.json")
        st.delete("anthropic")
        self.assertIsNone(st.get("anthropic"))


if __name__ == "__main__":
    unittest.main()
