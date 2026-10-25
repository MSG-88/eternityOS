"""The PreToolUse hook for the interactive Claude Code tile: every tool call is appended to
Eternity's audit log (via "claude-code-terminal"); privilege escalation is denied (exit 2).
Also: the managed settings wire the hook, and the launcher entry labels the tile as expert mode.
Run: python3 -m unittest tests/host/test_claude_hook.py"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
HOOK = os.path.join(ROOT, "config", "includes.chroot", "usr", "lib", "eternity", "claude-hook")
PYROOT = os.path.join(ROOT, "config", "includes.chroot", "usr", "lib", "eternity", "py")


@unittest.skipUnless(sys.platform.startswith("linux"), "needs /bin/sh")
class TestHook(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.env = dict(os.environ, HOME=self.home, XDG_STATE_HOME=os.path.join(self.home, ".local", "state"), PYTHONPATH=PYROOT, ETERNITY_PYROOT=PYROOT)
        self.log = os.path.join(self.home, ".local", "state", "eternity", "actions.log")

    def run_hook(self, payload):
        return subprocess.run([HOOK], input=json.dumps(payload), capture_output=True, text=True, env=self.env, timeout=30)   # executed as Claude Code does

    def entries(self):
        try:
            with open(self.log, encoding="utf-8") as f:
                return [json.loads(line) for line in f if line.strip()]
        except OSError:
            return []

    def test_edit_is_logged_and_allowed(self):
        r = self.run_hook({"tool_name": "Edit", "tool_input": {"file_path": "/home/u/a.txt", "old_string": "a", "new_string": "b"}, "session_id": "s1"})
        self.assertEqual(r.returncode, 0, r.stderr)
        e = self.entries()
        self.assertEqual(len(e), 1)
        self.assertEqual(e[0]["tool"], "Edit")
        self.assertEqual(e[0]["via"], "claude-code-terminal")
        self.assertEqual(e[0]["decision"], "interactive")
        self.assertEqual(e[0]["args"]["file_path"], "/home/u/a.txt")

    def test_sudo_is_denied_and_not_logged_as_run(self):
        r = self.run_hook({"tool_name": "Bash", "tool_input": {"command": "sudo apt install x"}})
        self.assertEqual(r.returncode, 2)
        self.assertIn("never escalates", r.stderr)
        e = self.entries()
        self.assertEqual(len(e), 1)
        self.assertEqual(e[0]["decision"], "denied (privilege escalation)")

    def test_garbage_input_does_not_block(self):
        r = subprocess.run([HOOK], input="not json", capture_output=True, text=True, env=self.env, timeout=30)
        self.assertEqual(r.returncode, 0)


class TestWiring(unittest.TestCase):
    def test_managed_settings_hook(self):
        with open(os.path.join(ROOT, "config", "includes.chroot", "etc", "claude-code", "managed-settings.json"), encoding="utf-8") as f:
            ms = json.load(f)
        hooks = ms["hooks"]["PreToolUse"]
        cmds = [h["command"] for entry in hooks for h in entry["hooks"]]
        self.assertIn("/usr/lib/eternity/claude-hook", cmds)
        self.assertEqual(ms["env"]["DISABLE_UPDATES"], "1")

    def test_terminal_tile(self):
        with open(os.path.join(ROOT, "config", "includes.chroot", "usr", "share", "applications", "eternity-claude-terminal.desktop"), encoding="utf-8") as f:
            d = f.read()
        self.assertIn("Name=Claude Code (terminal)", d)
        self.assertIn("expert mode", d)
        self.assertIn("outside Eternity", d)
        self.assertIn("Exec=", d)


if __name__ == "__main__":
    unittest.main()
