"""Action broker: consent, audit log, undo, privilege rule. Run: python3 -m unittest tests/host/test_actions.py"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "config", "includes.chroot", "usr", "lib", "eternity", "py"))
os.environ["ETERNITY_NO_KEYRING"] = "1"

from eternity import actions as A  # noqa: E402
from eternity import settings as S  # noqa: E402


class ActionsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HOME"] = self.tmp.name
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.tmp.name, ".config")
        os.environ["XDG_STATE_HOME"] = os.path.join(self.tmp.name, ".local", "state")
        self.asked = []

    def tearDown(self):
        self.tmp.cleanup()

    def broker(self, answer=True, trust=0):
        def consent(tool, args):
            self.asked.append(tool.name)
            return answer
        return A.ActionBroker(consent, cfg=S.Settings(trust_level=trust), audit=A.Audit())

    def test_change_requires_consent_and_is_logged_and_undoable(self):
        b = self.broker(answer=True)
        res = b.execute("write_note", {"title": "Design review", "text": "moved to tomorrow"})
        self.assertTrue(res.ok, res.summary)
        self.assertEqual(self.asked, ["write_note"])
        path = res.data["path"]
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            self.assertIn("# Design review", f.read())
        self.assertEqual(b.undoable().tool.name, "write_note")
        msg = b.undo_last()
        self.assertIn("removed", msg)
        self.assertFalse(os.path.exists(path))
        self.assertEqual(b.undo_last(), "nothing to undo")
        log = b.audit.tail()
        self.assertEqual([e["decision"] for e in log], ["approved", "undo"])
        self.assertTrue(log[0]["undoable"])

    def test_declined_action_does_nothing(self):
        b = self.broker(answer=False)
        res = b.execute("write_note", {"title": "x", "text": "y"})
        self.assertFalse(res.ok)
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "Documents", "Notes")))
        self.assertEqual(b.audit.tail()[-1]["decision"], "declined")

    def test_read_only_asks_at_trust_0_and_runs_free_at_trust_1(self):
        b = self.broker(answer=True, trust=0)
        res = b.execute("system_info", {})
        self.assertTrue(res.ok)
        self.assertEqual(self.asked, ["system_info"])
        self.asked.clear()
        b = self.broker(answer=True, trust=1)
        res = b.execute("system_info", {})
        self.assertTrue(res.ok)
        self.assertEqual(self.asked, [])
        self.assertIn("auto", b.audit.tail()[-1]["decision"])
        self.assertIn("cpu_threads", res.data)

    def test_dangerous_always_asks_and_sudo_is_refused(self):
        b = self.broker(answer=True, trust=1)
        res = b.execute("run_command", {"command": "sudo reboot"})
        self.assertEqual(self.asked, ["run_command"])
        self.assertFalse(res.ok)
        self.assertIn("escalate", res.summary)
        res = b.execute("run_command", {"command": "echo hello"})
        self.assertTrue(res.ok)
        self.assertIn("hello", res.data["stdout"])

    def test_unknown_tool_and_bad_url(self):
        b = self.broker()
        self.assertFalse(b.execute("format_disk", {}).ok)
        res = b.execute("open_url", {"url": "file:///etc/passwd"})
        self.assertFalse(res.ok)

    def test_schemas_are_well_formed(self):
        b = self.broker()
        for s in b.schemas():
            self.assertEqual(set(s), {"name", "description", "parameters"})
            self.assertEqual(s["parameters"]["type"], "object")

    def test_set_setting_changes_and_undoes(self):
        b = self.broker()
        res = b.execute("set_setting", {"key": "verbosity", "value": "brief"})
        self.assertTrue(res.ok, res.summary)
        self.assertEqual(S.load().verbosity, "brief")
        b.undo_last()
        self.assertEqual(S.load().verbosity, "normal")
        self.assertFalse(b.execute("set_setting", {"key": "telemetry", "value": True}).ok)

    def test_describe_call(self):
        t = A.default_tools()[0]
        self.assertIn("Memory", A.describe_call(t, {}))


if __name__ == "__main__":
    unittest.main()
