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
connection's SO_PEERCRED uid must be ours. Methods: subscribe, state.get, cards.get,
metrics.sample, settings.get, settings.set, ask.start, ask.cancel, ask.undo, ask.show,
consent.reply, session.lock, session.lock_info, pin.verify, hw.summary, launcher.index.
Standard library only.
"""
import datetime as _dt
import json
import os
import selectors
import socket
import struct
import threading
import time
import uuid
from typing import Callable, Dict, List, Optional

from . import actions as A
from . import agent as G
from . import cards as C
from . import providers as P
from . import settings as S

CONSENT_TIMEOUT_S = 600
SETTABLE = ("verbosity", "proactive", "voice", "trust_level", "name", "provider", "on_device_only", "claude_code_model",
            "local_model", "hotkey", "agent_mode", "unlock_methods", "anthropic_model", "openai_model")


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


def available(sock_path: Optional[str] = None) -> bool:
    return os.path.exists(sock_path or default_sock_path())


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
                 cfg: Optional[S.Settings] = None, tick_s: float = 1.0, allowed_uid: Optional[int] = None):
        self.provider_factory = provider_factory
        self.sock_path = sock_path or default_sock_path()
        self.cfg = cfg or S.load()
        self.tick_s = tick_s
        self.allowed_uid = os.getuid() if allowed_uid is None else allowed_uid
        self.ready = threading.Event()
        self._stop = threading.Event()
        self.subscribers: List[socket.socket] = []
        self.send_lock = threading.Lock()
        self.consents: Dict[str, dict] = {}
        self.run: Optional[dict] = None
        self.agent: Optional[G.Agent] = None
        self.methods: Dict[str, Callable[[dict], object]] = {
            "subscribe": self.m_subscribe, "state.get": self.m_state, "cards.get": self.m_cards, "metrics.sample": self.m_metrics,
            "settings.get": self.m_settings_get, "settings.set": self.m_settings_set, "ask.start": self.m_ask_start,
            "ask.cancel": self.m_ask_cancel, "ask.undo": self.m_ask_undo, "ask.show": self.m_ask_show, "consent.reply": self.m_consent_reply,
            "consent.ask": self.m_consent_ask, "session.lock": self.m_lock, "session.lock_info": self.m_lock_info, "pin.verify": self.m_pin,
            "hw.summary": self.m_hw, "launcher.index": self.m_launcher,
        }

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
        sel.register(srv, selectors.EVENT_READ, data=None)
        buffers: Dict[socket.socket, bytes] = {}
        if self.tick_s > 0:
            threading.Thread(target=self._ticker, daemon=True).start()
        self.ready.set()
        while not self._stop.is_set():
            for key, _mask in sel.select(timeout=0.2):
                if key.data is None:
                    conn, _ = srv.accept()
                    if _peer_uid(conn) not in (None, self.allowed_uid) or (_peer_uid(conn) is None and os.name == "posix"):
                        conn.close()
                        continue
                    conn.setblocking(False)
                    buffers[conn] = b""
                    sel.register(conn, selectors.EVENT_READ, data="client")
                    continue
                conn = key.fileobj
                try:
                    chunk = conn.recv(65536)
                except (BlockingIOError, InterruptedError):
                    continue
                except OSError:
                    chunk = b""
                if not chunk:
                    sel.unregister(conn)
                    buffers.pop(conn, None)
                    with self.send_lock:
                        if conn in self.subscribers:
                            self.subscribers.remove(conn)
                    conn.close()
                    continue
                buffers[conn] += chunk
                while b"\n" in buffers[conn]:
                    line, buffers[conn] = buffers[conn].split(b"\n", 1)
                    self._handle_line(conn, line)
        sel.close()
        srv.close()
        try:
            os.unlink(self.sock_path)
        except OSError:
            pass

    def stop(self) -> None:
        self._stop.set()

    def _send(self, conn: socket.socket, obj: dict) -> None:
        data = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
        with self.send_lock:
            try:
                conn.sendall(data)
            except OSError:
                if conn in self.subscribers:
                    self.subscribers.remove(conn)

    def emit(self, event: str, data: dict) -> None:
        with self.send_lock:
            subs = list(self.subscribers)
        for conn in subs:
            self._send(conn, {"event": event, "data": data})

    def _handle_line(self, conn: socket.socket, line: bytes) -> None:
        try:
            req = json.loads(line.decode("utf-8"))
        except ValueError:
            return
        rid, method, params = req.get("id"), req.get("method", ""), req.get("params") or {}
        fn = self.methods.get(method)
        if fn is None:
            self._send(conn, {"id": rid, "error": f"unknown method {method}"})
            return
        if method == "subscribe":
            with self.send_lock:
                self.subscribers.append(conn)
            self._send(conn, {"id": rid, "result": {}})
            return
        if method == "consent.ask":
            threading.Thread(target=self._consent_ask_async, args=(conn, rid, params), daemon=True).start()
            return
        try:
            result = fn(params)
            self._send(conn, {"id": rid, "result": result})
        except DaemonError as e:
            self._send(conn, {"id": rid, "error": str(e)})
        except Exception as e:  # noqa: BLE001  (a method must never take the daemon down)
            self._send(conn, {"id": rid, "error": f"{type(e).__name__}: {e}"})

    def _ticker(self) -> None:
        while not self._stop.wait(self.tick_s):
            if self.subscribers:
                self.emit("metrics.sample", self.m_metrics({}))

    # -- state -----------------------------------------------------------------------
    def m_subscribe(self, params: dict) -> dict:
        return {}

    def m_state(self, params: dict) -> dict:
        now = _dt.datetime.now()
        mem = C.memory()
        lat = C.latency_sample()
        return {"clock": now.strftime("%H:%M"), "date": now.strftime("%A %d %B"), "battery": C.battery(), "network": C.network(),
                "ai": C.ai_status(self.cfg), "memory": mem, "cpu": C.cpu_percent(), "latency_ms": (lat or {}).get("latency_ms"),
                "live": C.live_session(), "user_name": self.cfg.name, "notifications_held": 0, "uptime": C.uptime_text(),
                "provider": self.cfg.effective_provider()}

    def m_cards(self, params: dict) -> dict:
        from . import theme
        wanted = (theme.load().get("layout") or {}).get("cards") or ["today", "system", "eternity", "recent", "install"]
        out = []
        for cid in wanted:
            card = self._card(cid)
            if card:
                out.append(card)
        return {"cards": out}

    def _card(self, cid: str) -> Optional[dict]:
        if cid == "today":
            t = C.today()
            return {"id": cid, "kicker": "Today", "title": t.get("weekday", ""), "body": t.get("date", ""), "meta": C.uptime_text(), "actions": []}
        if cid == "system":
            mem, bat, cpu = C.memory(), C.battery(), C.cpu_percent()
            body = f"memory {mem.get('used_gb', 0):.1f} of {mem.get('total_gb', 0):.1f} GB"
            if cpu is not None:
                body += f" · cpu {cpu:.0f}%"
            meta = (f"battery {bat['percent']}%" + (" · charging" if bat.get("charging") else "")) if bat else C.network()
            return {"id": cid, "kicker": "System", "title": C.network() or "this device", "body": body, "meta": meta, "actions": ["monitor"]}
        if cid == "eternity":
            ai = C.ai_status(self.cfg)
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
            return None   # notifications are held by the daemon in slice 2
        if cid == "nowplaying":
            return None   # MPRIS in slice 2
        return None

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

    def m_settings_get(self, params: dict) -> dict:
        from dataclasses import asdict
        return asdict(self.cfg)

    def m_settings_set(self, params: dict) -> dict:
        key, value = params.get("key"), params.get("value")
        if key not in SETTABLE:
            raise DaemonError(f"setting '{key}' cannot be changed here")
        setattr(self.cfg, key, value)
        S.save(self.cfg)
        self.agent = None   # provider may have changed
        self.emit("settings.changed", {"key": key, "value": getattr(self.cfg, key)})
        return {key: getattr(self.cfg, key)}

    # -- assistant ---------------------------------------------------------------------
    def _make_agent(self) -> G.Agent:
        if self.agent is None:
            provider = self.provider_factory(self.cfg) if self.provider_factory else None
            self.agent = G.Agent(self._consent, cfg=self.cfg, provider=provider)
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
        return tool.risk == A.RISK_DANGEROUS and "pin" in self.cfg.unlock_methods and os.path.exists(os.path.join(S.config_dir(), "pin.json"))

    def _consent(self, tool: A.Tool, args: dict) -> bool:
        return self._consent_request(tool.name, tool.risk, A.describe_call(tool, args), self._need_pin(tool))

    def _consent_request(self, tool: str, risk: str, description: str, need_pin: bool) -> bool:
        cid = uuid.uuid4().hex[:12]
        entry = {"event": threading.Event(), "ok": False, "need_pin": need_pin}
        self.consents[cid] = entry
        self.emit("consent.request", {"consent_id": cid, "tool": tool, "risk": risk, "description": description, "need_pin": need_pin,
                                      "run_id": self.run["id"] if self.run else None})
        entry["event"].wait(CONSENT_TIMEOUT_S)
        self.consents.pop(cid, None)
        return bool(entry["ok"])

    def m_consent_reply(self, params: dict) -> dict:
        cid = str(params.get("consent_id", ""))
        entry = self.consents.get(cid)
        if entry is None:
            raise DaemonError("unknown or expired consent")
        ok = bool(params.get("ok"))
        if ok and params.get("need_pin", True) and self._pin_required_for(cid):
            from .ui.firstrun import verify_pin
            ok = verify_pin(str(params.get("pin", "")))
        entry["ok"] = ok
        entry["event"].set()
        return {"ok": ok}

    def _pin_required_for(self, cid: str) -> bool:
        return bool(self.consents.get(cid, {}).get("need_pin"))

    def m_consent_ask(self, params: dict) -> dict:
        # handled asynchronously in _consent_ask_async (blocks until the user answers)
        raise DaemonError("internal")

    def _consent_ask_async(self, conn: socket.socket, rid, params: dict) -> None:
        tool, risk = str(params.get("tool", "tool")), str(params.get("risk", A.RISK_DANGEROUS))
        need_pin = bool(params.get("need_pin"))
        cid = uuid.uuid4().hex[:12]
        entry = {"event": threading.Event(), "ok": False, "need_pin": need_pin}
        self.consents[cid] = entry
        self.emit("consent.request", {"consent_id": cid, "tool": tool, "risk": risk, "description": str(params.get("description", "")),
                                      "need_pin": need_pin, "run_id": None})
        entry["event"].wait(CONSENT_TIMEOUT_S)
        self.consents.pop(cid, None)
        self._send(conn, {"id": rid, "result": {"ok": bool(entry["ok"])}})

    # -- session ----------------------------------------------------------------------
    def m_lock(self, params: dict) -> dict:
        self.emit("session.lock", {})
        return {}

    def m_lock_info(self, params: dict) -> dict:
        return {"greeting": greeting_for_hour(_dt.datetime.now().hour), "name": self.cfg.name, "since_count": self._since_count(),
                "pin_available": "pin" in self.cfg.unlock_methods and os.path.exists(os.path.join(S.config_dir(), "pin.json"))}

    def _since_count(self) -> int:
        path = os.path.join(S.state_dir(), "notifications.jsonl")
        try:
            with open(path, encoding="utf-8") as f:
                return sum(1 for line in f if '"seen": false' in line)
        except OSError:
            return 0

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
        rows = [{"name": a.name, "exec": a.exec, "icon": getattr(a, "icon", ""), "id": getattr(a, "id", a.name)} for a in apps
                if not q or q in a.name.lower()]
        return {"apps": rows[: int(params.get("limit", 60))]}


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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
