"""The eternity MCP server: JSON-RPC over stdio, the tool list, consent and audit for both
Eternity tools and Claude Code's own tools through `approve`, and undo across processes.
Run: python3 -m unittest tests/host/test_mcp.py"""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PYROOT = os.path.join(HERE, "..", "..", "config", "includes.chroot", "usr", "lib", "eternity", "py")
sys.path.insert(0, PYROOT)
os.environ["ETERNITY_NO_KEYRING"] = "1"
os.environ.setdefault("ETERNITY_CONSENT", "deny")

from eternity import actions as A  # noqa: E402
from eternity import mcp  # noqa: E402
from eternity import settings as S  # noqa: E402


def rpc(server: mcp.Server, method: str, params=None, rid=1):
    return server.handle({"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})


class Base(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        os.environ["HOME"] = self.home
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.home, ".config")
        os.environ["XDG_STATE_HOME"] = os.path.join(self.home, ".local", "state")
        self.cfg = S.Settings(trust_level=0)
        self.decisions = []

    def server(self, allow=True, trust=0):
        self.cfg.trust_level = trust

        def consent(tool, args):
            self.decisions.append((tool.name, tool.risk))
            return allow
        broker = A.ActionBroker(consent, cfg=self.cfg)
        return mcp.Server(broker, self.cfg), broker


class TestProtocol(Base):
    def test_initialize_and_list(self):
        srv, _ = self.server()
        r = rpc(srv, "initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "t"}})
        self.assertEqual(r["result"]["protocolVersion"], "2025-11-25")
        self.assertEqual(r["result"]["serverInfo"]["name"], "eternity")
        names = {t["name"] for t in rpc(srv, "tools/list")["result"]["tools"]}
        for n in ("approve", "undo_last", "system_info", "hardware_report", "write_note", "run_command", "search_files_by_meaning"):
            self.assertIn(n, names)
        self.assertIsNone(srv.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        self.assertEqual(rpc(srv, "ping")["result"], {})
        self.assertEqual(rpc(srv, "something/new", rid=9)["id"], 9)

    def test_stdio_loop(self):
        srv, broker = self.server()
        inp = io.StringIO(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) + "\n"
                          + json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
                          + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "system_info", "arguments": {}}}) + "\n")
        out = io.StringIO()
        mcp.serve(inp, out, broker=broker, cfg=self.cfg)
        lines = [json.loads(x) for x in out.getvalue().splitlines()]
        self.assertEqual([x["id"] for x in lines], [1, 2])
        self.assertFalse(lines[1]["result"].get("isError"))


class TestConsent(Base):
    def test_eternity_tool_asks_and_logs(self):
        srv, broker = self.server(allow=True)
        r = rpc(srv, "tools/call", {"name": "write_note", "arguments": {"title": "t", "text": "hello"}})
        self.assertFalse(r["result"].get("isError"), r)
        self.assertEqual(self.decisions, [("write_note", "change")])
        entries = broker.audit.tail(5)
        self.assertEqual(entries[-1]["tool"], "write_note")
        self.assertEqual(entries[-1]["decision"], "approved")
        self.assertTrue(entries[-1]["undoable"])

    def test_declined(self):
        srv, broker = self.server(allow=False)
        r = rpc(srv, "tools/call", {"name": "write_note", "arguments": {"title": "t", "text": "hello"}})
        self.assertTrue(r["result"]["isError"])
        self.assertIn("declined", r["result"]["content"][0]["text"])

    def test_read_only_auto_when_trusted(self):
        srv, _ = self.server(allow=False, trust=1)
        r = rpc(srv, "tools/call", {"name": "system_info", "arguments": {}})
        self.assertFalse(r["result"].get("isError"))
        self.assertEqual(self.decisions, [])

    def approve(self, srv, name, inp):
        r = rpc(srv, "tools/call", {"name": "approve", "arguments": {"tool_name": name, "input": inp, "tool_use_id": "toolu_1"}})
        return json.loads(r["result"]["content"][0]["text"])

    def test_approve_claude_code_tools(self):
        srv, broker = self.server(allow=True)
        res = self.approve(srv, "Bash", {"command": "ls ~"})
        self.assertEqual(res["behavior"], "allow")
        self.assertEqual(res["updatedInput"], {"command": "ls ~"})
        self.assertEqual(self.decisions[-1], ("Bash", "dangerous"))
        res = self.approve(srv, "Write", {"file_path": "/tmp/x", "content": "hi"})
        self.assertEqual(res["behavior"], "allow")
        self.assertEqual(self.decisions[-1], ("Write", "change"))
        last = broker.audit.tail(1)[0]
        self.assertEqual((last["tool"], last["decision"], last["via"]), ("Write", "approved", "claude-code"))

    def test_approve_denies_privilege_escalation_even_when_user_allows(self):
        srv, _ = self.server(allow=True)
        for cmd in ("sudo apt install x", "echo hi | sudo tee /etc/x", "pkexec rm -rf /", "doas reboot"):
            res = self.approve(srv, "Bash", {"command": cmd})
            self.assertEqual(res["behavior"], "deny", cmd)
        self.assertEqual(self.decisions, [])  # never even asked

    def test_approve_declined(self):
        srv, _ = self.server(allow=False)
        res = self.approve(srv, "Edit", {"file_path": "/home/u/a.txt"})
        self.assertEqual(res["behavior"], "deny")
        self.assertIn("declined", res["message"])

    def test_approve_read_only_auto_when_trusted(self):
        srv, _ = self.server(allow=False, trust=1)
        self.assertEqual(self.approve(srv, "Read", {"file_path": "/etc/os-release"})["behavior"], "allow")
        self.assertEqual(self.approve(srv, "Grep", {"pattern": "x"})["behavior"], "allow")
        self.assertEqual(self.decisions, [])
        # but a change still asks (and is declined here)
        self.assertEqual(self.approve(srv, "Write", {"file_path": "/x"})["behavior"], "deny")

    def test_own_mcp_tools_are_not_double_prompted(self):
        srv, _ = self.server(allow=False)
        self.assertEqual(self.approve(srv, "mcp__eternity__write_note", {"title": "a"})["behavior"], "allow")
        self.assertEqual(self.decisions, [])


class TestUndoAcrossProcesses(Base):
    def test_undo_from_log(self):
        srv, broker = self.server(allow=True)
        rpc(srv, "tools/call", {"name": "write_note", "arguments": {"title": "undo me", "text": "x"}})
        notes = os.path.join(self.home, "Documents", "Notes")
        self.assertTrue(any("undo me" in f for f in os.listdir(notes)))
        # a fresh broker (another process, e.g. the Ask window) undoes it from the audit log
        other = A.ActionBroker(lambda t, a: True, cfg=self.cfg)
        msg = other.undo_last()
        self.assertIn("removed", msg)
        self.assertFalse(any("undo me" in f for f in os.listdir(notes)))
        self.assertEqual(other.undo_last(), "nothing to undo")

    def test_undo_tool(self):
        srv, _ = self.server(allow=True)
        rpc(srv, "tools/call", {"name": "write_note", "arguments": {"title": "n2", "text": "x"}})
        r = rpc(srv, "tools/call", {"name": "undo_last", "arguments": {}})
        self.assertIn("removed", r["result"]["content"][0]["text"])


class TestConsentViaDaemon(Base):
    """In the Eternity session the MCP server asks the shell through the daemon, not GTK."""

    def test_consent_via_daemon(self):
        import threading
        from eternity import daemon as D
        from test_daemon import Subscriber
        sock = os.path.join(self.home, "d.sock")
        d = D.Daemon(provider_factory=None, sock_path=sock, cfg=self.cfg, tick_s=0)
        threading.Thread(target=d.serve_forever, daemon=True).start()
        d.ready.wait(5)
        seen = []

        def auto_approve():
            sub = Subscriber(sock)
            started.set()
            ev = sub.wait("consent.request", timeout=20)
            seen.append(ev)
            D.Client(sock).call("consent.reply", consent_id=ev["consent_id"], ok=True)
        started = threading.Event()
        threading.Thread(target=auto_approve, daemon=True).start()
        started.wait(5)
        os.environ["ETERNITY_SOCK"] = sock
        os.environ.pop("ETERNITY_CONSENT", None)
        try:
            consent = mcp.make_consent(self.cfg)
            ok = consent(A.builtin_tool("Bash", {"command": "ls"}), {"command": "ls"})
        finally:
            os.environ.pop("ETERNITY_SOCK", None)
            os.environ["ETERNITY_CONSENT"] = "deny"
            d.stop()
        self.assertTrue(ok)
        self.assertEqual(seen[0]["tool"], "Bash")
        self.assertEqual(seen[0]["risk"], "dangerous")
        self.assertIn("ls", seen[0]["description"])

    def test_no_daemon_falls_back(self):
        os.environ["ETERNITY_SOCK"] = os.path.join(self.home, "missing.sock")
        os.environ.pop("ETERNITY_CONSENT", None)
        os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
        try:
            consent = mcp.make_consent(self.cfg)
            self.assertFalse(consent(A.builtin_tool("Bash", {"command": "ls"}), {"command": "ls"}))
        finally:
            os.environ.pop("ETERNITY_SOCK", None)
            os.environ["ETERNITY_CONSENT"] = "deny"


class TestCommandLine(unittest.TestCase):
    def test_tools_listing_and_policy_mode(self):
        env = dict(os.environ, ETERNITY_CONSENT="deny", PYTHONPATH=PYROOT)
        r = subprocess.run([sys.executable, "-c", "from eternity import mcp; import sys; sys.exit(mcp.main(['--tools']))"],
                           capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("approve:", r.stdout)
        req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                          "params": {"name": "approve", "arguments": {"tool_name": "Bash", "input": {"command": "rm x"}}}}) + "\n"
        r = subprocess.run([sys.executable, "-c", "from eternity import mcp; import sys; sys.exit(mcp.main([]))"],
                           input=req, capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(json.loads(out["result"]["content"][0]["text"])["behavior"], "deny")


if __name__ == "__main__":
    unittest.main()
