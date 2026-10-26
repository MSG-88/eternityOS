"""Action broker: consent, audit log, undo, privilege rule. Run: python3 -m unittest tests/host/test_actions.py"""
import json
import os
import sys
import tempfile
import unittest
import unittest.mock

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

    def test_trust_two_runs_everything_without_asking(self):
        # Owner's default (2026-10-26): actions run without a consent card; everything is logged and undoable.
        b = self.broker(answer=False, trust=2)
        res = b.execute("write_note", {"title": "Trusted", "text": "no card"})
        self.assertTrue(res.ok, res.summary)
        self.assertEqual(self.asked, [])
        self.assertEqual(b.undoable().tool.name, "write_note")

    def test_trust_defaults_to_two_and_clamps(self):
        self.assertEqual(S.Settings().trust_level, 2)
        cfg = S.Settings(trust_level=9); cfg.validate(); self.assertEqual(cfg.trust_level, 2)
        cfg = S.Settings(trust_level=-1); cfg.validate(); self.assertEqual(cfg.trust_level, 0)

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

    def test_run_routine_executes_each_step_with_consent(self):
        ran = []
        obj = {"type": "object", "properties": {}, "required": []}
        fakes = [
            A.Tool("step_a", "a", obj, lambda args: ran.append("a") or A.ActionResult(True, "a done"), A.RISK_CHANGE),
            A.Tool("step_b", "b", obj, lambda args: ran.append("b") or A.ActionResult(True, "b done"), A.RISK_CHANGE),
        ]
        def consent(tool, args):
            self.asked.append(tool.name); return True
        b = A.ActionBroker(consent, cfg=S.Settings(trust_level=0), audit=A.Audit(), tools=fakes)
        from eternity import routines as R
        R.Routines().define("demo", [{"tool": "step_a", "args": {}}, {"tool": "step_b", "args": {}}])
        res = b.execute("run_routine", {"name": "demo"})
        self.assertTrue(res.ok, res.summary)
        self.assertEqual(ran, ["a", "b"])
        self.assertIn("step_a", self.asked)
        self.assertIn("step_b", self.asked)

    def test_run_routine_unknown_name_is_a_clear_miss(self):
        b = self.broker(trust=2)
        res = b.execute("run_routine", {"name": "nope"})
        self.assertFalse(res.ok)
        self.assertIn("no routine", res.summary.lower())

    def test_define_and_list_routine_tools(self):
        b = self.broker(trust=2)
        r = b.execute("define_routine", {"name": "focus", "steps": [{"tool": "system_info", "args": {}}], "description": "check the box"})
        self.assertTrue(r.ok, r.summary)
        listed = b.execute("list_routines", {})
        self.assertTrue(listed.ok)
        self.assertIn("focus", json.dumps(listed.data).lower())

    def test_window_control_rejects_unknown_and_needs_hyprland(self):
        self.assertFalse(A.t_window_control({"action": "explode"}).ok)
        with unittest.mock.patch.object(A.shutil, "which", return_value=None):
            self.assertFalse(A.t_window_control({"action": "close"}).ok)
        with unittest.mock.patch.object(A.shutil, "which", return_value="/usr/bin/hyprctl"):
            with unittest.mock.patch.object(A.subprocess, "run") as run:
                r = A.t_window_control({"action": "next_workspace"})
                self.assertTrue(r.ok)
                self.assertEqual(run.call_args[0][0], ["hyprctl", "dispatch", "workspace", "e+1"])

    def test_set_brightness_clamps_and_undoes(self):
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)

            class R:
                stdout = "120" + chr(10) if cmd[:2] == ["brightnessctl", "get"] else "240" + chr(10)
            return R()

        with unittest.mock.patch.object(A.shutil, "which", return_value="/usr/bin/brightnessctl"):
            with unittest.mock.patch.object(A.subprocess, "run", side_effect=fake_run):
                r = A.t_set_brightness({"percent": 999})
                self.assertTrue(r.ok)
                self.assertIn(["brightnessctl", "set", "100%"], calls)
                self.assertEqual(r.undo_token, {"percent": 50})

    def test_clipboard_copy_validates_and_runs(self):
        self.assertFalse(A.t_clipboard_copy({"text": ""}).ok)
        with unittest.mock.patch.object(A.shutil, "which", return_value="/usr/bin/wl-copy"):
            with unittest.mock.patch.object(A.subprocess, "run") as run:
                r = A.t_clipboard_copy({"text": "hello"})
                self.assertTrue(r.ok)
                self.assertEqual(run.call_args[0][0], ["wl-copy"])

    def test_remind_validates_time_and_schedules(self):
        self.assertFalse(A.t_remind({"text": "x", "minutes": 0}).ok)
        self.assertFalse(A.t_remind({"text": "", "minutes": 5}).ok)
        self.assertFalse(A.t_remind({"text": "x", "minutes": 9999}).ok)
        with unittest.mock.patch.object(A.shutil, "which", return_value="/usr/bin/x"):
            with unittest.mock.patch.object(A.subprocess, "run") as run:
                r = A.t_remind({"text": "stretch", "minutes": 10})
                self.assertTrue(r.ok)
                self.assertEqual(run.call_args[0][0][0], "systemd-run")
                self.assertIn("--on-active=600", run.call_args[0][0])

    def test_describe_call(self):
        t = A.default_tools()[0]
        self.assertIn("Memory", A.describe_call(t, {}))


if __name__ == "__main__":
    unittest.main()
