"""The Claude Code provider against a fake `claude` binary that replays stream-json events
(shapes recorded from Claude Code 2.1.302 on 2026-10-25), plus the command line it builds and
the status probe. Run: python3 -m unittest tests/host/test_claude_code.py"""
import json
import os
import stat
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "config", "includes.chroot", "usr", "lib", "eternity", "py"))
os.environ["ETERNITY_NO_KEYRING"] = "1"

from eternity import agent as G  # noqa: E402
from eternity import providers as P  # noqa: E402
from eternity import settings as S  # noqa: E402

EVENTS = [
    {"type": "system", "subtype": "init", "session_id": "sess-1", "model": "claude-sonnet-5-5", "tools": ["Bash"], "mcp_servers": [{"name": "eternity", "status": "connected"}]},
    {"type": "stream_event", "event": {"type": "content_block_start"}},
    {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "tool_use", "id": "toolu_1", "name": "mcp__eternity__write_note", "input": {"title": "a", "text": "b"}}]}},
    {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_1", "content": [{"type": "text", "text": "note saved: ~/Documents/Notes/a.md"}]}]}},
    {"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Saved "}}},
    {"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "the note."}}},
    {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "Saved the note."}]}},
    {"type": "result", "subtype": "success", "is_error": False, "result": "Saved the note.", "session_id": "sess-1", "num_turns": 2,
     "duration_ms": 1234, "usage": {"input_tokens": 4, "output_tokens": 40}, "permission_denials": []},
]


def fake_claude(path: str, events, rc: int = 0, stderr: str = "") -> str:
    """A script that records its argv and replays the events."""
    log = path + ".args"
    with open(path, "w") as f:
        f.write("#!/bin/sh\n")
        f.write(f"printf '%s\\n' \"$@\" > {log}\n")
        f.write(f"env | grep -E '^(ANTHROPIC_API_KEY|DISABLE_UPDATES)=' >> {log}\n")
        f.write("if [ \"$1\" = auth ]; then echo '{\"loggedIn\": true, \"email\": \"u@x\", \"subscriptionType\": \"max\"}'; exit 0; fi\n")
        f.write("if [ \"$1\" = --version ]; then echo '2.1.308 (Claude Code)'; exit 0; fi\n")
        f.write("cat <<'EOF'\n")
        for e in events:
            f.write(json.dumps(e) + "\n")
        f.write("EOF\n")
        if stderr:
            f.write(f"echo '{stderr}' >&2\n")
        f.write(f"exit {rc}\n")
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
    return log


@unittest.skipUnless(sys.platform.startswith("linux"), "needs /bin/sh")
class TestProvider(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["HOME"] = self.tmp
        os.environ["ANTHROPIC_API_KEY"] = "sk-must-not-leak"
        self.bin = os.path.join(self.tmp, "claude")

    def tearDown(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)

    def test_stream_and_command(self):
        log = fake_claude(self.bin, EVENTS)
        cfg = S.Settings(trust_level=1, claude_code_model="sonnet")
        prov = P.ClaudeCodeProvider("sonnet", cfg=cfg, binary=self.bin, mcp_command="/usr/local/bin/eternity-mcp")
        events = list(prov.stream([{"role": "user", "content": "save a note"}], system="SYS"))
        kinds = [k for k, _ in events]
        self.assertEqual(kinds, ["status", "action", "text", "text", "done"])
        action = dict(events)["action"] if False else events[1][1]
        self.assertEqual(action["name"], "write_note")
        self.assertTrue(action["ok"]); self.assertTrue(action["undoable"])
        self.assertIn("note saved", action["summary"])
        m = events[-1][1]
        self.assertEqual((m.provider, m.tokens, m.total_ms, m.on_device), ("claude_code", 40, 1234, False))
        self.assertEqual(prov.session_id, "sess-1")
        args = open(log).read().splitlines()
        self.assertEqual(args[:2], ["-p", "save a note"])
        for flag in ("--output-format", "stream-json", "--include-partial-messages", "--strict-mcp-config", "--permission-prompt-tool", "mcp__eternity__approve", "--append-system-prompt", "SYS"):
            self.assertIn(flag, args)
        self.assertNotIn("--resume", args)
        self.assertIn("DISABLE_UPDATES=1", args)
        self.assertFalse(any(a.startswith("ANTHROPIC_API_KEY=") for a in args), "the API key must never reach Claude Code")
        allowed = args[args.index("--allowedTools") + 1].split(",")
        self.assertIn("Read", allowed); self.assertIn("mcp__eternity__system_info", allowed); self.assertNotIn("Bash", allowed)
        mcp = json.loads(args[args.index("--mcp-config") + 1])
        self.assertEqual(mcp["mcpServers"]["eternity"]["command"], "/usr/local/bin/eternity-mcp")
        # second turn resumes the session; trust 0 pre-allows nothing
        cfg.trust_level = 0
        list(prov.stream([{"role": "user", "content": "and again"}]))
        args = open(log).read().splitlines()
        self.assertIn("--resume", args); self.assertEqual(args[args.index("--resume") + 1], "sess-1")
        self.assertNotIn("--allowedTools", args)

    def test_not_signed_in(self):
        fake_claude(self.bin, [], rc=1, stderr="Not logged in. Please run /login")
        prov = P.ClaudeCodeProvider("sonnet", cfg=S.Settings(), binary=self.bin)
        with self.assertRaises(P.ProviderError) as cm:
            list(prov.stream([{"role": "user", "content": "hi"}]))
        self.assertIn("not signed in", str(cm.exception))

    def test_error_result(self):
        ev = EVENTS[:1] + [{"type": "result", "subtype": "error_max_turns", "is_error": True, "errors": ["max turns"], "session_id": "s"}]
        fake_claude(self.bin, ev)
        prov = P.ClaudeCodeProvider("sonnet", cfg=S.Settings(), binary=self.bin)
        with self.assertRaises(P.ProviderError):
            list(prov.stream([{"role": "user", "content": "hi"}]))

    def test_status(self):
        fake_claude(self.bin, EVENTS)
        st = P.claude_code_status(self.bin)
        self.assertTrue(st["installed"]); self.assertTrue(st["signed_in"])
        self.assertIn("u@x", st["detail"]); self.assertEqual(st["version"], "2.1.308")
        self.assertFalse(P.claude_code_status(os.path.join(self.tmp, "missing"))["installed"])

    def test_agent_passthrough(self):
        fake_claude(self.bin, EVENTS)
        cfg = S.Settings(provider="claude_code", on_device_only=False)
        prov = P.ClaudeCodeProvider("sonnet", cfg=cfg, binary=self.bin)
        agent = G.Agent(lambda t, a: True, cfg=cfg, provider=prov)
        out = list(agent.ask("save a note"))
        self.assertEqual([k for k, _ in out], ["status", "action", "text", "text", "done"])
        self.assertEqual(agent.history[-1], {"role": "assistant", "content": "Saved the note."})


@unittest.skipUnless(sys.platform.startswith("linux"), "needs /bin/sh")
class TestDeeper(unittest.TestCase):
    """Allow-list, model, cost readout and sessions."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["HOME"] = self.tmp
        os.environ["XDG_STATE_HOME"] = os.path.join(self.tmp, ".local", "state")
        self.bin = os.path.join(self.tmp, "claude")

    def test_allow_list_and_model(self):
        log = fake_claude(self.bin, EVENTS)
        cfg = S.Settings(trust_level=0, claude_code_model="opus", claude_code_allow=["Edit", "mcp__eternity__write_note"])
        prov = P.ClaudeCodeProvider(cfg.claude_code_model, cfg=cfg, binary=self.bin)
        list(prov.stream([{"role": "user", "content": "hi"}]))
        args = open(log).read().splitlines()
        self.assertEqual(args[args.index("--model") + 1], "opus")
        allowed = args[args.index("--allowedTools") + 1].split(",")
        self.assertEqual(allowed, ["Edit", "mcp__eternity__write_note"])

    def test_cost_readout_and_sessions(self):
        ev = list(EVENTS)
        ev[-1] = dict(ev[-1], total_cost_usd=0.0123)
        fake_claude(self.bin, ev)
        prov = P.ClaudeCodeProvider("sonnet", cfg=S.Settings(), binary=self.bin)
        events = list(prov.stream([{"role": "user", "content": "save a note about the review"}]))
        m = events[-1][1]
        self.assertAlmostEqual(m.cost_usd, 0.0123)
        self.assertIn("$0.01", m.readout())
        sessions = P.claude_code_sessions()
        self.assertEqual(sessions[0]["session_id"], "sess-1")
        self.assertEqual(sessions[0]["first_question"], "save a note about the review")
        self.assertIn("started", sessions[0])

    def test_resume_chosen_session(self):
        log = fake_claude(self.bin, EVENTS)
        prov = P.ClaudeCodeProvider("sonnet", cfg=S.Settings(), binary=self.bin)
        prov.resume("sess-old")
        list(prov.stream([{"role": "user", "content": "continue"}]))
        args = open(log).read().splitlines()
        self.assertEqual(args[args.index("--resume") + 1], "sess-old")


class TestSettings(unittest.TestCase):
    def test_model_and_allow_validation(self):
        self.assertEqual(S.Settings(claude_code_model="gpt").validate().claude_code_model, "sonnet")
        self.assertEqual(S.Settings(claude_code_model="haiku").validate().claude_code_model, "haiku")
        self.assertEqual(S.Settings().claude_code_allow, [])
        self.assertEqual(S.Settings(claude_code_allow=["Edit", 7, "Bash"]).validate().claude_code_allow, ["Edit", "Bash"])

    def test_provider_accepted(self):
        s = S.Settings(provider="claude_code", on_device_only=False).validate()
        self.assertEqual(s.effective_provider(), "claude_code")
        self.assertIn("claude_code", S.PROVIDERS)
        self.assertEqual(P.PROVIDER_LABELS["claude_code"], "Claude (your Claude account)")
        self.assertNotIn("claude_code", P.PROVIDER_KEY_URLS)  # no key is ever asked for


if __name__ == "__main__":
    unittest.main()
