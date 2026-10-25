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
        self.cfg = S.Settings(name="Maya", trust_level=0)   # these tests exercise the consent cards
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

    def test_memory_methods_and_asks_are_observed(self):
        r = self.c.call("memory.remember", text="I like tea")
        self.assertEqual(r["facts"], 1)
        sub = Subscriber(self.sock_path)
        self.c.call("ask.start", text="remember that I prefer short answers, then save a note")
        ev = sub.wait("consent.request")
        self.c.call("consent.reply", consent_id=ev["consent_id"], ok=True)
        sub.collect_until("ask.done")
        m = self.c.call("memory.list")
        self.assertEqual([f["text"] for f in m["facts"]], ["I like tea", "I prefer short answers, then save a note"])
        self.assertEqual(m["recent"][0]["tools"], ["write_note"])
        self.assertEqual(self.c.call("memory.forget", pattern="tea")["removed"], 1)
        self.assertEqual(len(self.c.call("memory.list")["facts"]), 1)

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
        r = self.c.call("consent.reply", consent_id=ev["consent_id"], ok=True, pin="9999")
        self.assertEqual((r["ok"], r.get("pin")), (False, "wrong"))          # wrong PIN: the consent stays open
        self.c.call("consent.reply", consent_id=ev["consent_id"], ok=False)   # the user gives up
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


class TestReviewFixes(Base):
    """Findings of the 2026-10-25 branch review: PIN cannot be skipped by the caller (C2),
    lock waits for the shell's ack (C3), bad lines never kill the daemon (I1), slow subscribers
    are dropped instead of corrupting the stream (I3), pending consents replay and close (I5),
    settings are reloaded from disk and coerced (I6), a reconnecting shell is re-locked (I2)."""

    def test_pin_cannot_be_skipped_by_the_caller(self):
        from eternity.ui.firstrun import store_pin
        store_pin("1234")
        self.cfg.unlock_methods = ["passphrase", "pin"]
        self.prov.turns = [[("tool_call", {"id": "c1", "name": "run_command", "arguments": {"command": "true"}})], [("text", "ok")]]
        sub = Subscriber(self.sock_path)
        self.c.call("ask.start", text="run true")
        ev = sub.wait("consent.request")
        r = self.c.call("consent.reply", consent_id=ev["consent_id"], ok=True, need_pin=False)   # caller says "no PIN needed"
        self.assertFalse(r["ok"])                                             # ignored: the daemon knows a PIN is required
        self.c.call("consent.reply", consent_id=ev["consent_id"], ok=False)
        events = sub.collect_until("ask.done")
        self.assertFalse(next(e["data"] for e in events if e["event"] == "ask.action")["ok"])

    def test_unlock_methods_and_trust_are_not_settable_over_the_socket(self):
        for key, value in (("unlock_methods", ["passphrase"]),):   # trust_level is the owner's choice in Settings since 2026-10-26
            with self.assertRaises(D.DaemonError):
                self.c.call("settings.set", key=key, value=value)

    def test_lock_requires_shell_ack(self):
        self.d.lock_ack_s = 0.5
        r = self.c.call("session.lock")                       # nobody acks
        self.assertFalse(r["locked"])
        sub = Subscriber(self.sock_path)
        acker = threading.Thread(target=lambda: (sub.wait("session.lock"), D.Client(self.sock_path).call("session.locked")), daemon=True)
        acker.start()
        r = self.c.call("session.lock")
        self.assertTrue(r["locked"])
        # a shell that (re)connects while locked is told to lock again
        late = Subscriber(self.sock_path)
        late.wait("session.lock", timeout=5)
        self.c.call("session.unlocked")
        self.assertFalse(self.c.call("session.lock_info")["locked"])

    def test_bad_lines_do_not_kill_the_daemon(self):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.connect(self.sock_path)
        s.sendall(b'[]\n1\n{"method":[1]}\n{"id":"x","method":"state.get","params":"nope"}\nnot json\n')
        time.sleep(0.5)
        self.assertIn("clock", self.c.call("state.get"))
        self.assertTrue(self.t.is_alive())

    def test_slow_subscriber_is_dropped_not_corrupting(self):
        slow = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); slow.connect(self.sock_path)
        slow.sendall(b'{"id":0,"method":"subscribe","params":{}}\n')
        time.sleep(0.2)
        for _ in range(3000):                                  # ~3 MB of events the slow client never reads
            self.d.emit("noise", {"pad": "x" * 1000})
        t0 = time.time()
        self.assertIn("clock", self.c.call("state.get"))         # others are not stalled
        self.assertLess(time.time() - t0, 5)
        time.sleep(0.5)
        with self.d.send_lock:
            self.assertNotIn(slow, self.d.subscribers)

    def test_pending_consent_replays_and_closes(self):
        self.cfg.trust_level = 0
        sub = Subscriber(self.sock_path)
        self.c.call("ask.start", text="save a note")
        ev = sub.wait("consent.request")
        late = Subscriber(self.sock_path)                       # a shell that connects while a consent is pending
        again = late.wait("consent.request", timeout=5)
        self.assertEqual(again["consent_id"], ev["consent_id"])
        self.c.call("consent.reply", consent_id=ev["consent_id"], ok=True)
        closed = sub.wait("consent.closed")
        self.assertEqual(closed["consent_id"], ev["consent_id"])
        sub.collect_until("ask.done")

    def test_settings_reloaded_and_coerced(self):
        cfg = S.load(); cfg.verbosity = "detailed"; S.save(cfg)   # another process (the Settings app) wrote the file
        self.assertEqual(self.c.call("settings.get")["verbosity"], "detailed")
        self.c.call("settings.set", key="verbosity", value="brief")
        self.assertEqual(S.load().verbosity, "brief")
        r = self.c.call("settings.set", key="verbosity", value=5)   # bad value: coerced back by validate, never crashes
        self.assertEqual(r["verbosity"], "normal")


class TestLauncher(Base):
    """Slice 2 Task 2: the launcher index over the socket, the show event and launching."""

    def desktop(self, name, exec_cmd):
        d = os.path.join(self.tmp.name, ".local", "share", "applications")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, name.lower() + ".desktop"), "w") as f:
            f.write(f"[Desktop Entry]\nType=Application\nName={name}\nExec={exec_cmd}\nIcon=utilities-terminal\n")

    def test_index_filter_and_show(self):
        os.environ["XDG_DATA_HOME"] = os.path.join(self.tmp.name, ".local", "share")
        self.desktop("Terminal", "true")
        self.desktop("Files", "true")
        rows = self.c.call("launcher.index", query="term")["apps"]
        self.assertTrue(any(r["name"] == "Terminal" for r in rows))
        self.assertTrue(all({"name", "exec", "icon", "id"} <= set(r) for r in rows))
        self.assertFalse(any(r["name"] == "Files" for r in rows))
        sub = Subscriber(self.sock_path)
        self.c.call("launcher.show")
        sub.wait("launcher.show")

    def test_launch_by_id(self):
        os.environ["XDG_DATA_HOME"] = os.path.join(self.tmp.name, ".local", "share")
        marker = os.path.join(self.tmp.name, "launched")
        self.desktop("Marker", f"touch {marker}")
        row = next(r for r in self.c.call("launcher.index", query="marker")["apps"])
        self.assertTrue(self.c.call("launcher.launch", id=row["id"])["ok"])
        for _ in range(50):
            if os.path.exists(marker):
                break
            time.sleep(0.1)
        self.assertTrue(os.path.exists(marker))
        with self.assertRaises(D.DaemonError):
            self.c.call("launcher.launch", id="no-such-app")


class TestNotifications(Base):
    """Slice 2 Task 3: the notification store behind the Focus card and the lock screen's since-count."""

    def test_store_seen_and_since(self):
        for i in range(3):
            r = self.c.call("notifications.store", app="Mail", summary=f"msg {i}", body="hello", urgency="normal")
            self.assertIn("id", r)
        self.assertEqual(self.c.call("session.lock_info")["since_count"], 3)
        recent = self.c.call("notifications.recent", limit=10)["notifications"]
        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[0]["summary"], "msg 2")          # newest first
        self.assertFalse(recent[0]["seen"])
        self.c.call("notifications.seen")
        self.assertEqual(self.c.call("session.lock_info")["since_count"], 0)
        self.assertTrue(all(n["seen"] for n in self.c.call("notifications.recent", limit=10)["notifications"]))

    def test_dnd_setting_and_focus_card(self):
        self.c.call("settings.set", key="dnd", value=True)
        self.assertTrue(self.c.call("settings.get")["dnd"])
        self.c.call("notifications.store", app="Mail", summary="held", body="", urgency="normal")
        cards = {c["id"]: c for c in self.c.call("cards.get")["cards"]}
        self.assertIn("focus", cards)
        self.assertIn("held", cards["focus"]["body"].lower())
        self.assertIn("1", cards["focus"]["body"])
        self.c.call("settings.set", key="dnd", value=False)
        cards = {c["id"]: c for c in self.c.call("cards.get")["cards"]}
        self.assertNotIn("focus", cards)                           # no DND, nothing held: no Focus card

    def test_store_keeps_last_500_lines(self):
        for i in range(520):
            self.c.call("notifications.store", app="A", summary=str(i), body="", urgency="low")
        recent = self.c.call("notifications.recent", limit=1000)["notifications"]
        self.assertLessEqual(len(recent), 500)
        self.assertEqual(recent[0]["summary"], "519")


class TestThemeOverSocket(Base):
    """Slice 2 Task 4: Settings pages write the user's theme/layout files through the daemon."""

    def test_theme_get_and_set(self):
        os.environ["ETERNITY_SHARE"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config", "includes.chroot", "usr", "share", "eternity")
        from eternity import theme
        theme.SHARE = os.environ["ETERNITY_SHARE"]
        t = self.c.call("theme.get")
        self.assertEqual(t["theme"]["color"]["accent"], "#9184d9")
        self.assertEqual(t["layout"]["scale"], 1.25)
        sub = Subscriber(self.sock_path)
        r = self.c.call("theme.set", file="layout", key="scale", value=1.5)
        self.assertEqual(r["layout"]["scale"], 1.5)
        with open(os.path.join(self.tmp.name, ".config", "eternity", "layout.toml"), encoding="utf-8") as f:
            self.assertIn("scale = 1.5", f.read())
        self.assertIn("monitor=eDP-1,preferred,auto,1.5", open(os.path.join(self.tmp.name, ".config", "eternity", "generated", "hyprland.conf")).read())
        sub.wait("theme.changed")
        r = self.c.call("theme.set", file="theme", section="motion", key="reduced", value=True)
        self.assertTrue(r["theme"]["motion"]["reduced"])
        with self.assertRaises(D.DaemonError):
            self.c.call("theme.set", file="layout", key="scale", value=9)        # invalid: refused, file untouched
        self.assertEqual(self.c.call("theme.get")["layout"]["scale"], 1.5)
        with self.assertRaises(D.DaemonError):
            self.c.call("theme.set", file="nope", key="x", value=1)

    def test_presets(self):
        os.environ["ETERNITY_SHARE"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config", "includes.chroot", "usr", "share", "eternity")
        from eternity import theme
        theme.SHARE = os.environ["ETERNITY_SHARE"]
        names = [p["id"] for p in self.c.call("theme.presets")["presets"]]
        for n in ("nocturne", "nocturne-light", "mono", "high-contrast", "quiet"):
            self.assertIn(n, names)
        r = self.c.call("theme.apply_preset", id="quiet")
        self.assertTrue(r["theme"]["motion"]["reduced"])
        r = self.c.call("theme.apply_preset", id="nocturne")
        self.assertFalse(r["theme"]["motion"]["reduced"])
        self.assertEqual(r["theme"]["color"]["accent"], "#9184d9")


class TestMonitor(Base):
    """Slice 2 Task 5: metrics history (60 samples) and the process list behind the Monitor page."""

    def test_history_and_processes(self):
        for _ in range(3):
            self.d.m_metrics({})
        h = self.c.call("metrics.history")
        self.assertTrue({"cpu", "mem_gb", "ai_tps", "latency_ms"} <= set(h["series"]))
        self.assertGreaterEqual(len(h["series"]["cpu"]), 3)
        self.assertLessEqual(len(h["series"]["cpu"]), 60)
        self.assertIn("accel", h)                                  # NPU present? (never faked)
        self.assertFalse(h["accel"])
        procs = self.c.call("metrics.processes", limit=5)["processes"]
        self.assertLessEqual(len(procs), 5)
        self.assertTrue(all({"pid", "comm", "rss_mb"} <= set(p) for p in procs))
        self.assertTrue(all(procs[i]["rss_mb"] >= procs[i + 1]["rss_mb"] for i in range(len(procs) - 1)))
        sub = Subscriber(self.sock_path)
        self.c.call("monitor.show")
        sub.wait("monitor.show")


class TestSlice2Review(Base):
    """Slice 2 review fixes: unlock marks notifications seen (I4), provider switch in one call (I7),
    theme.set allow-list (I8)."""

    def test_unlock_marks_seen(self):
        self.c.call("notifications.store", app="A", summary="x", body="", urgency="normal")
        self.assertEqual(self.c.call("session.lock_info")["since_count"], 1)
        self.c.call("session.unlocked")
        self.assertEqual(self.c.call("session.lock_info")["since_count"], 0)

    def test_provider_switch_in_one_call(self):
        self.c.call("settings.set", key="on_device_only", value=True)
        r = self.c.call("settings.set", key="provider", value="anthropic")
        self.assertEqual(r["provider"], "anthropic")
        self.assertFalse(self.c.call("settings.get")["on_device_only"])
        self.assertEqual(self.c.call("settings.get")["provider"], "anthropic")

    def test_theme_set_allow_list(self):
        os.environ["ETERNITY_SHARE"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config", "includes.chroot", "usr", "share", "eternity")
        from eternity import theme
        theme.SHARE = os.environ["ETERNITY_SHARE"]
        for kw in (dict(file="keys", section="action", key="lock", value="true"), dict(file="layout", key="exec_once", value=["x"]),
                   dict(file="layout", key="blur_namespaces", value=[]), dict(file="theme", section="font", key="body", value="x")):
            with self.assertRaises(D.DaemonError):
                self.c.call("theme.set", **kw)
        self.assertEqual(self.c.call("theme.set", file="layout", key="gaps", value=8)["layout"]["gaps"], 8)
        self.assertEqual(self.c.call("theme.set", file="theme", section="color", key="accent", value="#2ec4b6")["theme"]["color"]["accent"], "#2ec4b6")


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
