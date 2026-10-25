"""eternity-daemon: the state hub on a Unix socket (JSON lines). State, cards, ask streaming
with shell-rendered consent (queued, declined), settings, peer-uid check, lock info and PIN.
Run: python3 -m unittest tests/host/test_daemon.py"""
import json
import os
import socket
import sys
import tempfile
import threading
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "config", "includes.chroot", "usr", "lib", "eternity", "py"))
os.environ["ETERNITY_NO_KEYRING"] = "1"

from eternity import daemon as D  # noqa: E402
from eternity import providers as P  # noqa: E402
from eternity import settings as S  # noqa: E402
from test_agent import ScriptedProvider  # noqa: E402


class Subscriber:
    """A raw client that subscribes and collects events."""

    def __init__(self, path):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(path)
        self.f = self.sock.makefile("rwb", buffering=0)
        self.events = []
        self.lock = threading.Condition()
        self.subscribed = threading.Event()
        self.send({"id": 0, "method": "subscribe", "params": {}})
        threading.Thread(target=self._reader, daemon=True).start()
        assert self.subscribed.wait(5), "subscribe not acknowledged"

    def send(self, obj):
        self.f.write((json.dumps(obj) + "\n").encode())

    def _reader(self):
        for line in self.f:
            obj = json.loads(line)
            if obj.get("id") == 0:
                self.subscribed.set()
            if "event" in obj:
                with self.lock:
                    self.events.append(obj)
                    self.lock.notify_all()

    def wait(self, name, timeout=10.0):
        deadline = time.time() + timeout
        with self.lock:
            while True:
                for e in self.events:
                    if e["event"] == name and not e.get("_seen"):
                        e["_seen"] = True
                        return e["data"]
                remaining = deadline - time.time()
                if remaining <= 0:
                    raise AssertionError(f"no {name} event; got {[e['event'] for e in self.events]}")
                self.lock.wait(remaining)

    def collect_until(self, name, timeout=10.0):
        self.wait(name, timeout)
        with self.lock:
            return list(self.events)


class Base(unittest.TestCase):
    turns = [[("text", "Saving. "), ("tool_call", {"id": "c1", "name": "write_note", "arguments": {"title": "t", "text": "x"}})],
             [("text", "Done.")]]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HOME"] = self.tmp.name
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.tmp.name, ".config")
        os.environ["XDG_STATE_HOME"] = os.path.join(self.tmp.name, ".local", "state")
        os.environ["XDG_RUNTIME_DIR"] = self.tmp.name
        self.sock_path = os.path.join(self.tmp.name, "d.sock")
        self.prov = ScriptedProvider(list(self.turns))
        self.cfg = S.Settings(name="Maya")
        self.d = D.Daemon(provider_factory=lambda cfg: self.prov, sock_path=self.sock_path, cfg=self.cfg, tick_s=0)
        self.t = threading.Thread(target=self.d.serve_forever, daemon=True)
        self.t.start()
        self.d.ready.wait(5)
        self.c = D.Client(self.sock_path)

    def tearDown(self):
        self.d.stop()
        self.tmp.cleanup()


class TestState(Base):
    def test_state_and_cards(self):
        r = self.c.call("state.get")
        self.assertTrue(set(r) >= {"clock", "battery", "network", "ai", "live", "user_name", "memory", "cpu"})
        self.assertEqual(r["user_name"], "Maya")
        cards = self.c.call("cards.get")["cards"]
        self.assertIsInstance(cards, list)
        self.assertTrue(all({"id", "kicker", "title", "body"} <= set(c) for c in cards))
        self.assertIn("today", [c["id"] for c in cards])

    def test_settings_roundtrip(self):
        self.c.call("settings.set", key="verbosity", value="brief")
        self.assertEqual(self.c.call("settings.get")["verbosity"], "brief")
        with self.assertRaises(D.DaemonError):
            self.c.call("settings.set", key="telemetry", value=True)

    def test_unknown_method(self):
        with self.assertRaises(D.DaemonError):
            self.c.call("nope.nothing")

    def test_metrics_sample(self):
        m = self.c.call("metrics.sample")
        self.assertTrue({"cpu", "mem_gb", "latency_ms"} <= set(m))

    def test_lock_info_and_pin(self):
        from eternity.ui.firstrun import store_pin
        store_pin("4321")
        info = self.c.call("session.lock_info")
        self.assertEqual(info["name"], "Maya")
        self.assertIn(info["greeting"], ("Good morning", "Good afternoon", "Good evening"))
        self.assertEqual(D.greeting_for_hour(21), "Good evening")
        self.assertEqual(D.greeting_for_hour(9), "Good morning")
        self.assertEqual(D.greeting_for_hour(15), "Good afternoon")
        self.assertTrue(self.c.call("pin.verify", pin="4321")["ok"])
        self.assertFalse(self.c.call("pin.verify", pin="0000")["ok"])

    def test_ask_show_and_lock_events(self):
        sub = Subscriber(self.sock_path)
        self.c.call("ask.show")
        sub.wait("ask.show")
        self.c.call("session.lock")
        sub.wait("session.lock")


class TestAsk(Base):
    def test_ask_streams_and_consent(self):
        sub = Subscriber(self.sock_path)
        run = self.c.call("ask.start", text="save a note")["run_id"]
        ev = sub.wait("consent.request")
        self.assertEqual(ev["tool"], "write_note")
        self.assertEqual(ev["risk"], "change")
        self.assertFalse(ev["need_pin"])
        self.c.call("consent.reply", consent_id=ev["consent_id"], ok=True)
        events = sub.collect_until("ask.done")
        kinds = [e["event"] for e in events]
        self.assertIn("ask.text", kinds)
        self.assertIn("ask.action", kinds)
        action = next(e["data"] for e in events if e["event"] == "ask.action")
        self.assertTrue(action["ok"]); self.assertTrue(action["undoable"]); self.assertEqual(action["name"], "write_note")
        done = next(e["data"] for e in events if e["event"] == "ask.done")
        self.assertEqual(done["run_id"], run)
        self.assertIn("tok/s", done["readout"])
        self.assertEqual("".join(e["data"]["delta"] for e in events if e["event"] == "ask.text"), "Saving. Done.")
        self.assertIn("removed", self.c.call("ask.undo")["message"])

    def test_declined_consent(self):
        sub = Subscriber(self.sock_path)
        self.c.call("ask.start", text="save a note")
        ev = sub.wait("consent.request")
        self.c.call("consent.reply", consent_id=ev["consent_id"], ok=False)
        events = sub.collect_until("ask.done")
        action = next(e["data"] for e in events if e["event"] == "ask.action")
        self.assertFalse(action["ok"])
        self.assertIn("declined", action["summary"])

    def test_consent_queue(self):
        self.prov.turns = [[("tool_call", {"id": "c1", "name": "write_note", "arguments": {"title": "a", "text": "1"}}),
                            ("tool_call", {"id": "c2", "name": "set_volume", "arguments": {"percent": 30}})],
                           [("text", "Both done.")]]
        sub = Subscriber(self.sock_path)
        self.c.call("ask.start", text="two things")
        first = sub.wait("consent.request")
        second = sub.wait("consent.request", timeout=3.0) if False else None
        # the second request only arrives after the first is answered (sequential tool execution)
        self.c.call("consent.reply", consent_id=first["consent_id"], ok=True)
        second = sub.wait("consent.request")
        self.assertNotEqual(first["consent_id"], second["consent_id"])
        self.assertEqual((first["tool"], second["tool"]), ("write_note", "set_volume"))
        self.c.call("consent.reply", consent_id=second["consent_id"], ok=True)
        events = sub.collect_until("ask.done")
        self.assertEqual([e["data"]["name"] for e in events if e["event"] == "ask.action"], ["write_note", "set_volume"])

    def test_consent_pin_required(self):
        from eternity.ui.firstrun import store_pin
        store_pin("1234")
        self.cfg.unlock_methods = ["passphrase", "pin"]
        self.prov.turns = [[("tool_call", {"id": "c1", "name": "run_command", "arguments": {"command": "true"}})], [("text", "ok")]]
        sub = Subscriber(self.sock_path)
        self.c.call("ask.start", text="run true")
        ev = sub.wait("consent.request")
        self.assertTrue(ev["need_pin"])
        self.c.call("consent.reply", consent_id=ev["consent_id"], ok=True, pin="9999")
        events = sub.collect_until("ask.done")
        action = next(e["data"] for e in events if e["event"] == "ask.action")
        self.assertFalse(action["ok"])

    def test_provider_error_reports_status(self):
        self.prov.turns = ["ERROR"]
        sub = Subscriber(self.sock_path)
        self.c.call("ask.start", text="hi")
        events = sub.collect_until("ask.done")
        self.assertTrue(any(e["event"] == "ask.status" and "model" in e["data"]["text"] for e in events))

    def test_busy_rejects_second_ask(self):
        sub = Subscriber(self.sock_path)
        self.c.call("ask.start", text="save a note")
        sub.wait("consent.request")
        with self.assertRaises(D.DaemonError):
            self.c.call("ask.start", text="again")
        self.d.stop()


class TestSecurity(unittest.TestCase):
    def test_rejects_other_uid(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "d.sock")
        d = D.Daemon(provider_factory=None, sock_path=path, cfg=S.Settings(), tick_s=0, allowed_uid=os.getuid() + 1)
        threading.Thread(target=d.serve_forever, daemon=True).start()
        d.ready.wait(5)
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(path)
        s.sendall(b'{"id":1,"method":"state.get","params":{}}\n')
        s.settimeout(3)
        try:
            data = s.recv(100)
        except ConnectionResetError:
            data = b""
        self.assertEqual(data, b"")   # closed without an answer
        d.stop()

    def test_socket_mode(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "d.sock")
        d = D.Daemon(provider_factory=None, sock_path=path, cfg=S.Settings(), tick_s=0)
        threading.Thread(target=d.serve_forever, daemon=True).start()
        d.ready.wait(5)
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
        d.stop()


if __name__ == "__main__":
    unittest.main()
