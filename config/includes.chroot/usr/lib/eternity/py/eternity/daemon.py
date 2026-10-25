"""eternity-daemon: the state hub of the Eternity session.

One process per user session owns the state the shell renders (clock, battery, network, AI,
cards, metrics), runs the assistant (the existing Agent with its ActionBroker), and asks the
shell for consent instead of opening GTK dialogs. The shell, the CLIs (`eternity-ask --show`,
`eternity-lock`) and `eternity-mcp` talk to it over a Unix socket with one JSON object per
line:

    request   {"id": 1, "method": "state.get", "params": {}}
    response  {"id": 1, "result": {...}}  |  {"id": 1, "error": "..."}
    event     {"event": "ask.text", "data": {...}}      (to clients that sent "subscribe")

Socket: $XDG_RUNTIME_DIR/eternity/daemon.sock (override ETERNITY_SOCK), mode 0600, and every
connection's SO_PEERCRED uid must be ours. Methods: ping, subscribe, state.get, cards.get,
metrics.sample, settings.get, settings.set, ask.start, ask.cancel, ask.undo, ask.show,
consent.reply, consent.ask, session.lock, session.locked, session.unlocked, session.lock_info,
pin.verify, hw.summary, launcher.index, claude.sessions, claude.resume.

Robustness rules (branch review 2026-10-25): a bad line never ends the loop; writes go through
a per-connection queue drained by the selector (a client that stops reading is dropped, never
left with half a line); the PIN requirement of a consent is decided by the daemon only;
`session.lock` succeeds only when the shell acknowledges the lock; a shell that connects while
a lock or a consent is pending is told about it; settings are re-read from disk when another
process wrote them. Standard library only.
"""
import collections
import datetime as _dt
import json
import os
import selectors
import socket
import struct
import threading
import time
import uuid
from typing import Callable, Deque, Dict, List, Optional

from . import actions as A
from . import agent as G
from . import cards as C
from . import providers as P
from . import settings as S

CONSENT_TIMEOUT_S = 600
LOCK_ACK_S = 5.0
OUTQ_CAP_BYTES = 4 * 1024 * 1024
INBUF_CAP_BYTES = 1024 * 1024
# What a client may change over the socket. Credentials (unlock methods) and the trust level are
# changed only through the Settings app, which writes the file: a process that can reach the
# socket must not be able to lower the bar for its own actions.
SETTABLE = ("verbosity", "proactive", "voice", "name", "provider", "on_device_only", "claude_code_model", "claude_code_allow",
            "local_model", "hotkey", "agent_mode", "anthropic_model", "openai_model", "dnd")


class DaemonError(Exception):
    """An error the daemon reported for a request."""


def default_sock_path() -> str:
    if os.environ.get("ETERNITY_SOCK"):
        return os.environ["ETERNITY_SOCK"]
    run = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    return os.path.join(run, "eternity", "daemon.sock")


def greeting_for_hour(hour: int) -> str:
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


def _peer_uid(conn: socket.socket) -> Optional[int]:
    try:
        creds = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
        _pid, uid, _gid = struct.unpack("3i", creds)
        return uid
    except (OSError, AttributeError):
        return None


# ----------------------------------------------------------------------------- client
class Client:
    """Blocking request/response client (CLIs, tests, eternity-mcp)."""

    def __init__(self, sock_path: Optional[str] = None, timeout: float = 30.0):
        self.path = sock_path or default_sock_path()
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect(self.path)
        self.f = self.sock.makefile("rwb", buffering=0)
        self._id = 0
        self.lock = threading.Lock()

    def call(self, method: str, **params):
        with self.lock:
            self._id += 1
            rid = self._id
            self.f.write((json.dumps({"id": rid, "method": method, "params": params}) + "\n").encode("utf-8"))
            for line in self.f:
                obj = json.loads(line)
                if obj.get("id") != rid:
                    continue            # an event or a stale answer
                if "error" in obj:
                    raise DaemonError(obj["error"])
                return obj.get("result")
        raise DaemonError("connection closed")

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass


def available(sock_path: Optional[str] = None, probe: bool = True) -> bool:
    """True when a daemon answers on the socket (a stale socket file does not count)."""
    path = sock_path or default_sock_path()
    if not os.path.exists(path):
        return False
    if not probe:
        return True
    try:
        c = Client(path, timeout=2.0)
        c.call("ping")
        c.close()
        return True
    except (OSError, DaemonError, ValueError):
        return False


def request_consent(tool: A.Tool, args: dict, need_pin: bool, sock_path: Optional[str] = None) -> bool:
    """Used by eternity-mcp: ask the session's shell through the daemon; False when unanswered."""
    try:
        c = Client(sock_path, timeout=CONSENT_TIMEOUT_S + 5)
        r = c.call("consent.ask", tool=tool.name, risk=tool.risk, description=A.describe_call(tool, args), need_pin=need_pin)
        c.close()
        return bool(r.get("ok"))
    except (OSError, DaemonError, ValueError):
        return False


# ----------------------------------------------------------------------------- daemon
class Daemon:
    def __init__(self, provider_factory: Optional[Callable[[S.Settings], P.Provider]] = None, sock_path: Optional[str] = None,
                 cfg: Optional[S.Settings] = None, tick_s: float = 1.0, allowed_uid: Optional[int] = None, lock_ack_s: float = LOCK_ACK_S):
        self.provider_factory = provider_factory
        self.sock_path = sock_path or default_sock_path()
        self.cfg = cfg or S.load()
        self._cfg_mtime = self._settings_mtime()
        self.tick_s = tick_s
        self.lock_ack_s = lock_ack_s
        self.allowed_uid = os.getuid() if allowed_uid is None else allowed_uid
        self.ready = threading.Event()
        self._stop = threading.Event()
        self.subscribers: List[socket.socket] = []
        self.send_lock = threading.Lock()
        self._outq: Dict[socket.socket, Deque[bytes]] = {}
        self._outq_bytes: Dict[socket.socket, int] = {}
        self._wake_r, self._wake_w = socket.socketpair()
        self._wake_r.setblocking(False)
        self.consents: Dict[str, dict] = {}
        self.run: Optional[dict] = None
        self.agent: Optional[G.Agent] = None
        self.locked = False
        self._lock_event = threading.Event()
        self.methods: Dict[str, Callable[[dict], object]] = {
            "ping": lambda p: {}, "subscribe": self.m_subscribe, "state.get": self.m_state, "cards.get": self.m_cards, "metrics.sample": self.m_metrics,
            "settings.get": self.m_settings_get, "settings.set": self.m_settings_set, "ask.start": self.m_ask_start,
            "ask.cancel": self.m_ask_cancel, "ask.undo": self.m_ask_undo, "ask.show": self.m_ask_show, "consent.reply": self.m_consent_reply,
            "consent.ask": self.m_consent_ask, "session.lock": self.m_lock, "session.locked": self.m_locked, "session.unlocked": self.m_unlocked,
            "session.lock_info": self.m_lock_info, "pin.verify": self.m_pin,
            "hw.summary": self.m_hw, "launcher.index": self.m_launcher, "launcher.show": self.m_launcher_show, "launcher.launch": self.m_launcher_launch,
            "notifications.store": self.m_notif_store, "notifications.recent": self.m_notif_recent, "notifications.seen": self.m_notif_seen, "osd.show": self.m_osd, "claude.sessions": self.m_claude_sessions, "claude.resume": self.m_claude_resume,
        }
        # methods answered on a worker thread because they block on the user or on slow probes
        self.slow_methods = {"consent.ask", "session.lock", "state.get", "cards.get", "metrics.sample", "hw.summary", "pin.verify",
                             "consent.reply", "ask.undo", "launcher.index", "claude.resume"}

    # -- transport ------------------------------------------------------------------
    def serve_forever(self) -> None:
        os.makedirs(os.path.dirname(self.sock_path), exist_ok=True)
        try:
            os.unlink(self.sock_path)
        except FileNotFoundError:
            pass
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(self.sock_path)
        os.chmod(self.sock_path, 0o600)
        srv.listen(16)
        srv.setblocking(False)
        sel = selectors.DefaultSelector()
        sel.register(srv, selectors.EVENT_READ, data="server")
        sel.register(self._wake_r, selectors.EVENT_READ, data="wake")
        buffers: Dict[socket.socket, bytes] = {}
        if self.tick_s > 0:
            threading.Thread(target=self._ticker, daemon=True).start()
        self.ready.set()
        try:
            while not self._stop.is_set():
                try:
                    events = sel.select(timeout=0.2)
                except (OSError, ValueError):
                    continue
                for key, mask in events:
                    try:
                        self._serve_one(sel, srv, buffers, key, mask)
                    except Exception:  # noqa: BLE001  (never let one connection end the loop)
                        conn = key.fileobj
                        if conn is not srv and conn is not self._wake_r:
                            self._drop(sel, buffers, conn)
        finally:
            for conn in list(buffers):
                self._drop(sel, buffers, conn)
            sel.close()
            srv.close()
            try:
                os.unlink(self.sock_path)
            except OSError:
                pass

    def _serve_one(self, sel, srv, buffers, key, mask) -> None:
        if key.data == "server":
            conn, _ = srv.accept()
            if _peer_uid(conn) != self.allowed_uid:
                conn.close()
                return
            conn.setblocking(False)
            buffers[conn] = b""
            with self.send_lock:
                self._outq[conn] = collections.deque()
                self._outq_bytes[conn] = 0
            sel.register(conn, selectors.EVENT_READ, data="client")
            return
        if key.data == "wake":
            try:
                self._wake_r.recv(4096)
            except (BlockingIOError, OSError):
                pass
            self._rearm_writers(sel)
            return
        conn = key.fileobj
        if mask & selectors.EVENT_WRITE:
            if not self._flush(sel, conn):
                self._drop(sel, buffers, conn)
                return
        if mask & selectors.EVENT_READ:
            try:
                chunk = conn.recv(65536)
            except (BlockingIOError, InterruptedError):
                return
            except OSError:
                chunk = b""
            if not chunk:
                self._drop(sel, buffers, conn)
                return
            buffers[conn] += chunk
            if len(buffers[conn]) > INBUF_CAP_BYTES:
                self._drop(sel, buffers, conn)
                return
            while b"\n" in buffers[conn]:
                line, buffers[conn] = buffers[conn].split(b"\n", 1)
                try:
                    self._handle_line(conn, line)
                except Exception as e:  # noqa: BLE001
                    self._send(conn, {"id": None, "error": f"{type(e).__name__}: {e}"})

    def _drop(self, sel, buffers, conn) -> None:
        try:
            sel.unregister(conn)
        except (KeyError, ValueError):
            pass
        buffers.pop(conn, None)
        with self.send_lock:
            if conn in self.subscribers:
                self.subscribers.remove(conn)
            self._outq.pop(conn, None)
            self._outq_bytes.pop(conn, None)
        try:
            conn.close()
        except OSError:
            pass

    def _rearm_writers(self, sel) -> None:
        with self.send_lock:
            pending = [c for c, q in self._outq.items() if q]
        for conn in pending:
            try:
                sel.modify(conn, selectors.EVENT_READ | selectors.EVENT_WRITE, data="client")
            except (KeyError, ValueError):
                pass

    def _flush(self, sel, conn) -> bool:
        """Write what is queued for `conn`; False when the connection is dead."""
        with self.send_lock:
            q = self._outq.get(conn)
            if q is None:
                return False
            while q:
                data = q[0]
                try:
                    n = conn.send(data)
                except (BlockingIOError, InterruptedError):
                    break
                except OSError:
                    return False
                self._outq_bytes[conn] -= n
                if n < len(data):
                    q[0] = data[n:]
                    break
                q.popleft()
            empty = not q
        if empty:
            try:
                sel.modify(conn, selectors.EVENT_READ, data="client")
            except (KeyError, ValueError):
                pass
        return True

    def stop(self) -> None:
        self._stop.set()

    def _send(self, conn: socket.socket, obj: dict) -> None:
        """Queue one line for a connection; the selector thread writes it. A client that lets
        OUTQ_CAP_BYTES pile up is cut off (it reconnects and resubscribes)."""
        data = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
        with self.send_lock:
            q = self._outq.get(conn)
            if q is None:
                return
            if self._outq_bytes.get(conn, 0) + len(data) > OUTQ_CAP_BYTES:
                q.clear()
                self._outq_bytes[conn] = 0
                if conn in self.subscribers:
                    self.subscribers.remove(conn)
                try:
                    conn.shutdown(socket.SHUT_RDWR)     # the selector sees EOF and drops it
                except OSError:
                    pass
                return
            q.append(data)
            self._outq_bytes[conn] = self._outq_bytes.get(conn, 0) + len(data)
        try:
            self._wake_w.send(b"x")
        except OSError:
            pass

    def emit(self, event: str, data: dict, only: Optional[socket.socket] = None) -> None:
        with self.send_lock:
            subs = [only] if only is not None else list(self.subscribers)
        for conn in subs:
            self._send(conn, {"event": event, "data": data})

    def _handle_line(self, conn: socket.socket, line: bytes) -> None:
        try:
            req = json.loads(line.decode("utf-8"))
        except ValueError:
            return
        if not isinstance(req, dict):
            return
        rid, method, params = req.get("id"), req.get("method", ""), req.get("params")
        if not isinstance(method, str):
            self._send(conn, {"id": rid, "error": "method must be a string"})
            return
        if not isinstance(params, dict):
            params = {}
        fn = self.methods.get(method)
        if fn is None:
            self._send(conn, {"id": rid, "error": f"unknown method {method}"})
            return
        if method == "subscribe":
            with self.send_lock:
                if conn not in self.subscribers:
                    self.subscribers.append(conn)
            self._send(conn, {"id": rid, "result": {}})
            self._replay(conn)
            return
        if method == "consent.ask":
            threading.Thread(target=self._consent_ask_async, args=(conn, rid, params), daemon=True).start()
            return
        if method in self.slow_methods:
            threading.Thread(target=self._answer, args=(conn, rid, fn, params), daemon=True).start()
            return
        self._answer(conn, rid, fn, params)

    def _answer(self, conn, rid, fn, params) -> None:
        try:
            result = fn(params)
            self._send(conn, {"id": rid, "result": result})
        except DaemonError as e:
            self._send(conn, {"id": rid, "error": str(e)})
        except Exception as e:  # noqa: BLE001  (a method must never take the daemon down)
            self._send(conn, {"id": rid, "error": f"{type(e).__name__}: {e}"})

    def _replay(self, conn) -> None:
        """A shell that (re)connects learns what is pending: the lock and open consents."""
        if self.locked:
            self.emit("session.lock", {"replay": True}, only=conn)
        for entry in list(self.consents.values()):
            if not entry["event"].is_set():
                self.emit("consent.request", dict(entry["request"], replay=True), only=conn)

    def _ticker(self) -> None:
        while not self._stop.wait(self.tick_s):
            if self.subscribers:
                try:
                    self.emit("metrics.sample", self.m_metrics({}))
                except Exception:  # noqa: BLE001
                    pass

    # -- settings ------------------------------------------------------------------------
    def _settings_mtime(self) -> float:
        try:
            return os.stat(S.settings_path()).st_mtime
        except OSError:
            return 0.0

    def _fresh_cfg(self) -> S.Settings:
        """Re-read settings.json when another process (the Settings app) wrote it."""
        mtime = self._settings_mtime()
        if mtime and mtime != self._cfg_mtime:
            self.cfg = S.load()
            self.agent = None
            self._cfg_mtime = mtime
        return self.cfg

    def m_subscribe(self, params: dict) -> dict:
        return {}

    def m_settings_get(self, params: dict) -> dict:
        from dataclasses import asdict
        return asdict(self._fresh_cfg())

    def m_settings_set(self, params: dict) -> dict:
        key, value = params.get("key"), params.get("value")
        if key not in SETTABLE:
            raise DaemonError(f"setting '{key}' cannot be changed here")
        cfg = self._fresh_cfg()
        setattr(cfg, key, value)
        cfg.validate()                     # coerces bad values back to safe ones, never raises
        S.save(cfg)
        self._cfg_mtime = self._settings_mtime()
        self.agent = None   # provider may have changed
        self.emit("settings.changed", {"key": key, "value": getattr(cfg, key)})
        return {key: getattr(cfg, key)}

    # -- state -----------------------------------------------------------------------
    def m_state(self, params: dict) -> dict:
        cfg = self._fresh_cfg()
        now = _dt.datetime.now()
        mem = C.memory()
        lat = C.latency_sample()
        return {"clock": now.strftime("%H:%M"), "date": now.strftime("%A %d %B"), "battery": C.battery(), "network": C.network(),
                "ai": C.ai_status(cfg), "memory": mem, "cpu": C.cpu_percent(), "latency_ms": (lat or {}).get("latency_ms"),
                "live": C.live_session(), "user_name": cfg.name, "notifications_held": 0, "uptime": C.uptime_text(),
                "provider": cfg.effective_provider(), "locked": self.locked}

    def m_cards(self, params: dict) -> dict:
        from . import theme
        wanted = (theme.load().get("layout") or {}).get("cards") or ["today", "system", "eternity", "recent", "install", "focus", "nowplaying"]
        out = []
        for cid in wanted:
            card = self._card(cid)
            if card:
                out.append(card)
        return {"cards": out}

    def _card(self, cid: str) -> Optional[dict]:
        cfg = self._fresh_cfg()
        if cid == "today":
            t = C.today()
            return {"id": cid, "kicker": "Today", "title": t.get("weekday", ""), "body": t.get("date", ""), "meta": C.uptime_text(), "actions": []}
        if cid == "system":
            mem, bat, cpu = C.memory(), C.battery(), C.cpu_percent()
            body = f"memory {mem.get('used_gb', 0):.1f} of {mem.get('total_gb', 0):.1f} GB"
            if cpu is not None:
                body += f" · cpu {cpu:.0f}%"
            net = C.network()
            meta = (f"battery {bat['percent']}%" + (" · charging" if bat.get("charging") else "")) if bat else net
            return {"id": cid, "kicker": "System", "title": net or "this device", "body": body, "meta": meta, "actions": ["monitor"]}
        if cid == "eternity":
            ai = C.ai_status(cfg)
            n = C.actions_today()
            return {"id": cid, "kicker": "Eternity", "title": ai["label"], "body": (ai.get("readout") or ("warm" if ai.get("warm") else "ready")) + (f" · {ai['model']}" if ai.get("model") else ""),
                    "meta": f"{n} action{'s' if n != 1 else ''} today", "actions": ["ask"]}
        if cid == "recent":
            files = C.recent_files(4)
            if not files:
                return None
            return {"id": cid, "kicker": "Recent files", "title": files[0]["name"], "body": "\n".join(f["name"] for f in files[1:4]), "meta": files[0].get("when", ""), "actions": ["files"]}
        if cid == "install":
            if not C.live_session():
                return None
            return {"id": cid, "kicker": "Live session", "title": "Install Eternity 08", "body": "Keep everything: install next to Windows or on the whole disk.", "meta": "eternity-install", "actions": ["install"]}
        if cid == "focus":
            if not cfg.dnd:
                return None
            held = self._since_count()
            return {"id": cid, "kicker": "Focus", "title": "Do not disturb", "body": f"Notifications held \u00b7 {held} queued", "meta": "until you turn it off", "actions": ["dnd"]}
        return None   # nowplaying: MPRIS lives in the shell (slice 2b)

    def m_metrics(self, params: dict) -> dict:
        lat = C.latency_sample() or {}
        tps = None
        try:
            with open(C.metrics_path(), encoding="utf-8") as f:
                m = json.load(f)
            if time.time() - m.get("ts", 0) < 600:
                tps = m.get("tokens_per_s")
        except (OSError, ValueError):
            pass
        mem = C.memory()
        return {"cpu": C.cpu_percent(), "mem_gb": mem.get("used_gb"), "ai_tps": tps, "latency_ms": lat.get("latency_ms"),
                "dropped_frames": lat.get("dropped_frames")}

    # -- assistant ---------------------------------------------------------------------
    def _make_agent(self) -> G.Agent:
        cfg = self._fresh_cfg()
        if self.agent is None:
            provider = self.provider_factory(cfg) if self.provider_factory else None
            self.agent = G.Agent(self._consent, cfg=cfg, provider=provider)
        return self.agent

    def m_ask_start(self, params: dict) -> dict:
        text = str(params.get("text", "")).strip()
        if not text:
            raise DaemonError("nothing to ask")
        if self.run and not self.run.get("done"):
            raise DaemonError("an answer is still running")
        run_id = uuid.uuid4().hex[:12]
        self.run = {"id": run_id, "done": False, "cancelled": False}
        threading.Thread(target=self._ask_worker, args=(run_id, text), daemon=True).start()
        return {"run_id": run_id}

    def _ask_worker(self, run_id: str, text: str) -> None:
        metrics = None
        try:
            agent = self._make_agent()
            for kind, payload in agent.ask(text):
                if self.run and self.run.get("cancelled"):
                    break
                if kind == "text":
                    self.emit("ask.text", {"run_id": run_id, "delta": payload})
                elif kind == "status":
                    self.emit("ask.status", {"run_id": run_id, "text": str(payload)})
                elif kind == "action":
                    self.emit("ask.action", {"run_id": run_id, **payload})
                elif kind == "done":
                    metrics = payload
        except Exception as e:  # noqa: BLE001
            self.emit("ask.status", {"run_id": run_id, "text": f"{type(e).__name__}: {e}"})
        readout = metrics.readout() if isinstance(metrics, P.Metrics) else ""
        if isinstance(metrics, P.Metrics):
            C.remember_metrics(metrics)
        data = {"run_id": run_id, "readout": readout}
        if isinstance(metrics, P.Metrics) and getattr(metrics, "cost_usd", None):
            data["cost_usd"] = metrics.cost_usd
        if self.run and self.run["id"] == run_id:
            self.run["done"] = True
        self.emit("ask.done", data)

    def m_ask_cancel(self, params: dict) -> dict:
        if self.run and not self.run.get("done"):
            self.run["cancelled"] = True
        return {}

    def m_ask_undo(self, params: dict) -> dict:
        agent = self._make_agent()
        return {"message": agent.undo_last()}

    def m_ask_show(self, params: dict) -> dict:
        self.emit("ask.show", {"text": params.get("text", "")})
        return {}

    # -- consent ----------------------------------------------------------------------
    def _need_pin(self, tool: A.Tool) -> bool:
        cfg = self._fresh_cfg()
        return tool.risk == A.RISK_DANGEROUS and "pin" in cfg.unlock_methods and os.path.exists(os.path.join(S.config_dir(), "pin.json"))

    def _consent(self, tool: A.Tool, args: dict) -> bool:
        return self._consent_request(tool.name, tool.risk, A.describe_call(tool, args), self._need_pin(tool))

    def _consent_request(self, tool: str, risk: str, description: str, need_pin: bool) -> bool:
        cid = uuid.uuid4().hex[:12]
        request = {"consent_id": cid, "tool": tool, "risk": risk, "description": description, "need_pin": need_pin,
                   "run_id": self.run["id"] if self.run else None}
        entry = {"event": threading.Event(), "ok": False, "need_pin": need_pin, "request": request}
        self.consents[cid] = entry
        self.emit("consent.request", request)
        answered = entry["event"].wait(CONSENT_TIMEOUT_S)
        self.consents.pop(cid, None)
        self.emit("consent.closed", {"consent_id": cid, "ok": bool(entry["ok"]), "reason": "answered" if answered else "timeout"})
        return bool(entry["ok"])

    def m_consent_reply(self, params: dict) -> dict:
        cid = str(params.get("consent_id", ""))
        entry = self.consents.get(cid)
        if entry is None or entry["event"].is_set():
            raise DaemonError("unknown or expired consent")
        ok = bool(params.get("ok"))
        if ok and entry["need_pin"]:                 # the daemon decides whether a PIN is needed, never the caller
            from .ui.firstrun import verify_pin
            if not verify_pin(str(params.get("pin", ""))):
                return {"ok": False, "pin": "wrong", "consent_id": cid}   # stays open: the dialog asks again
        entry["ok"] = ok
        entry["event"].set()
        return {"ok": ok, "consent_id": cid}

    def m_consent_ask(self, params: dict) -> dict:
        raise DaemonError("internal")   # answered asynchronously by _consent_ask_async

    def _consent_ask_async(self, conn: socket.socket, rid, params: dict) -> None:
        tool, risk = str(params.get("tool", "tool")), str(params.get("risk", A.RISK_DANGEROUS))
        ok = self._consent_request(tool, risk, str(params.get("description", "")), bool(params.get("need_pin")))
        self._send(conn, {"id": rid, "result": {"ok": ok}})

    # -- session ----------------------------------------------------------------------
    def m_lock(self, params: dict) -> dict:
        """Ask the shell to lock and wait for its acknowledgement; {"locked": bool}."""
        if self.locked:
            return {"locked": True}
        self._lock_event.clear()
        self.emit("session.lock", {})
        self._lock_event.wait(self.lock_ack_s)
        return {"locked": self.locked}

    def m_locked(self, params: dict) -> dict:
        self.locked = True
        self._lock_event.set()
        return {"locked": True}

    def m_unlocked(self, params: dict) -> dict:
        self.locked = False
        return {"locked": False}

    def m_lock_info(self, params: dict) -> dict:
        cfg = self._fresh_cfg()
        return {"greeting": greeting_for_hour(_dt.datetime.now().hour), "name": cfg.name, "since_count": self._since_count(),
                "pin_available": "pin" in cfg.unlock_methods and os.path.exists(os.path.join(S.config_dir(), "pin.json")), "locked": self.locked}

    # -- notifications (store behind the Focus card and the lock screen's since-count) ------
    NOTIF_KEEP = 500

    def _notif_path(self) -> str:
        return os.path.join(S.state_dir(), "notifications.jsonl")

    def _notif_read(self) -> List[dict]:
        try:
            with open(self._notif_path(), encoding="utf-8") as f:
                rows = []
                for line in f:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        pass
                return rows
        except OSError:
            return []

    def _notif_write(self, rows: List[dict]) -> None:
        S._atomic_write(self._notif_path(), "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows[-self.NOTIF_KEEP:]), 0o600)

    def _since_count(self) -> int:
        return sum(1 for r in self._notif_read() if not r.get("seen"))

    def m_notif_store(self, params: dict) -> dict:
        row = {"id": uuid.uuid4().hex[:12], "ts": _dt.datetime.now().isoformat(timespec="seconds"), "app": str(params.get("app", ""))[:80],
               "summary": str(params.get("summary", ""))[:200], "body": str(params.get("body", ""))[:1000], "urgency": str(params.get("urgency", "normal")),
               "seen": False, "held": bool(self._fresh_cfg().dnd)}
        rows = self._notif_read()
        rows.append(row)
        if len(rows) > self.NOTIF_KEEP + 20:
            self._notif_write(rows)
        else:
            os.makedirs(S.state_dir(), exist_ok=True)
            with open(self._notif_path(), "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return {"id": row["id"], "held": row["held"]}

    def m_notif_recent(self, params: dict) -> dict:
        rows = self._notif_read()[-self.NOTIF_KEEP:]
        return {"notifications": list(reversed(rows))[: int(params.get("limit", 20))]}

    def m_notif_seen(self, params: dict) -> dict:
        rows = self._notif_read()
        for r in rows:
            r["seen"] = True
        self._notif_write(rows)
        return {"seen": len(rows)}

    def m_osd(self, params: dict) -> dict:
        self.emit("osd", {"kind": str(params.get("kind", "volume")), "level": float(params.get("level", 0)), "label": str(params.get("label", ""))})
        return {}

    def m_pin(self, params: dict) -> dict:
        from .ui.firstrun import verify_pin
        return {"ok": verify_pin(str(params.get("pin", "")))}

    def m_hw(self, params: dict) -> dict:
        from . import hw
        inv = hw.inventory()
        return {"summary": hw.summary(inv), "problems": [f"{s}: {m}" for s, m in hw.problems(inv)], "platform": inv["platform"]}

    def m_launcher(self, params: dict) -> dict:
        from . import launcher_index as L
        q = str(params.get("query", "")).lower().strip()
        apps = L.load()
        rows = [{"name": a.name, "exec": a.exec_cmd, "icon": a.icon, "id": a.desktop_id or a.name, "comment": a.comment}
                for a in apps if not q or q in a.name.lower() or any(q in k.lower() for k in a.keywords)]
        return {"apps": rows[: int(params.get("limit", 60))]}

    def m_launcher_show(self, params: dict) -> dict:
        self.emit("launcher.show", {})
        return {}

    def m_launcher_launch(self, params: dict) -> dict:
        from . import launcher_index as L
        wanted = str(params.get("id", ""))
        for a in L.load():
            if wanted and wanted in (a.desktop_id, a.name):
                L.launch(a)
                return {"ok": True, "name": a.name}
        raise DaemonError(f"no app {wanted!r}")

    def m_claude_sessions(self, params: dict) -> dict:
        return {"sessions": P.claude_code_sessions(int(params.get("limit", 20)))}

    def m_claude_resume(self, params: dict) -> dict:
        agent = self._make_agent()
        prov = agent.provider
        if not hasattr(prov, "resume"):
            raise DaemonError("the current assistant has no sessions to resume")
        prov.resume(str(params.get("session_id", "")) or None)
        agent.reset()
        return {"session_id": prov.session_id}


def main(argv: Optional[List[str]] = None) -> int:
    import sys
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--once"] and len(argv) >= 2:
        c = Client()
        params = json.loads(argv[2]) if len(argv) > 2 else {}
        print(json.dumps(c.call(argv[1], **params), indent=1))
        return 0
    d = Daemon()
    try:
        d.serve_forever()
    except KeyboardInterrupt:
        pass
    except Exception as e:  # noqa: BLE001
        print(f"eternity-daemon: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
