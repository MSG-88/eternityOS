"""Eternity's MCP server (stdio, JSON-RPC): the bridge between an outside agent runtime, today
Claude Code signed in with the user's own Claude account, and this OS.

It offers two things:

* the Eternity actions (system_info, search_files_by_meaning, open_app, set_volume, write_note,
  set_setting, run_command, power, hardware_report, undo_last) as MCP tools, run through the
  same ActionBroker as the Ask bar: consent dialog, audit log, undo;
* an `approve` tool that Claude Code calls through `--permission-prompt-tool` for every one of
  its own tools (Bash, Edit, Write, ...) that is not pre-allowed. The same consent dialog and
  trust rules decide; commands that escalate privileges are always denied; the decision is
  logged. The human stays in control no matter which brain is answering.

Consent is shown with GTK when a display is available (ETERNITY_CONSENT=gtk, the default),
or decided by policy for tests and headless runs (ETERNITY_CONSENT=allow|deny).

Protocol: MCP 2025-06-18 subset (initialize, notifications/initialized, ping, tools/list,
tools/call); unknown requests get an empty result so a newer client never hangs.
Standard library only.
"""
import json
import os
import sys
import threading
from typing import Callable, Dict, List, Optional

from . import actions as A
from . import settings as S

PROTOCOL = "2025-06-18"
SERVER = {"name": "eternity", "version": "0.2"}


def _log(msg: str) -> None:
    try:
        path = os.path.join(S.state_dir(), "mcp.log")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(msg.rstrip() + "\n")
    except OSError:
        pass


# ----------------------------------------------------------------------------- consent
def policy_consent(policy: str) -> Callable[[A.Tool, dict], bool]:
    return lambda tool, args: policy == "allow"


def gtk_consent(cfg: S.Settings) -> Callable[[A.Tool, dict], bool]:
    """A consent callback that shows the Eternity dialog on the user's display. GTK runs in
    its own thread so the JSON-RPC loop stays responsive to pings while the user decides."""
    import gi  # type: ignore
    gi.require_version("Gtk", "3.0")
    from gi.repository import GLib, Gtk  # type: ignore

    from .ui import load_css
    from .ui.ask import ConsentDialog
    from .ui.firstrun import verify_pin

    load_css()
    loop = threading.Thread(target=Gtk.main, daemon=True)
    loop.start()

    def consent(tool: A.Tool, args: dict) -> bool:
        ev = threading.Event()
        result = {"ok": False}

        def ask():
            need_pin = tool.risk == A.RISK_DANGEROUS and "pin" in cfg.unlock_methods and os.path.exists(
                os.path.join(S.config_dir(), "pin.json"))
            dlg = ConsentDialog(None, tool, args, need_pin)
            dlg.set_keep_above(True)
            dlg.present()
            resp = dlg.run()
            ok = resp == Gtk.ResponseType.OK
            if ok and need_pin:
                ok = verify_pin(dlg.pin.get_text())
            dlg.destroy()
            result["ok"] = ok
            ev.set()
            return False
        GLib.idle_add(ask)
        ev.wait()
        return result["ok"]
    return consent


def make_consent(cfg: S.Settings) -> Callable[[A.Tool, dict], bool]:
    mode = os.environ.get("ETERNITY_CONSENT", "gtk")
    if mode in ("allow", "deny"):
        return policy_consent(mode)
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        _log("no display: consent policy deny")
        return policy_consent("deny")
    try:
        return gtk_consent(cfg)
    except Exception as e:  # noqa: BLE001
        _log(f"GTK consent unavailable ({e}); denying")
        return policy_consent("deny")


# ----------------------------------------------------------------------------- server
class Server:
    def __init__(self, broker: A.ActionBroker, cfg: S.Settings):
        self.broker, self.cfg = broker, cfg

    # tools offered to the agent runtime
    def tool_list(self) -> List[dict]:
        tools = []
        for t in self.broker.tools.values():
            tools.append({"name": t.name, "description": t.description + f" (risk: {t.risk}; the user confirms before it runs)",
                          "inputSchema": t.parameters})
        tools.append({"name": "undo_last", "description": "Undo the newest undoable Eternity action (notes, volume, settings).",
                      "inputSchema": {"type": "object", "properties": {}}})
        tools.append({"name": "approve",
                      "description": "Permission prompt for the host's own tools: asks the user of this computer whether a tool may run.",
                      "inputSchema": {"type": "object", "properties": {"tool_name": {"type": "string"}, "input": {"type": "object"},
                                                                       "tool_use_id": {"type": "string"}}, "required": ["tool_name", "input"]}})
        return tools

    def approve(self, args: dict) -> dict:
        name = str(args.get("tool_name", ""))
        inp = args.get("input") if isinstance(args.get("input"), dict) else {}
        if name.startswith("mcp__eternity__"):
            # our own tools ask through the broker when they run; no second dialog
            return {"behavior": "allow", "updatedInput": inp}
        if A.escalates_privileges(name, inp):
            self.broker.audit.write(tool=name, args=inp, decision="denied (privilege escalation)", ok=False, summary="sudo/pkexec refused", via="claude-code")
            return {"behavior": "deny", "message": "Eternity never escalates privileges; ask the user to run this themselves."}
        tool = A.builtin_tool(name, inp)
        if not self.broker.needs_consent(tool):
            self.broker.audit.write(tool=name, args=inp, decision="auto (read-only, trusted)", ok=True, summary=tool.description, via="claude-code")
            return {"behavior": "allow", "updatedInput": inp}
        ok = self.broker.consent(tool, inp)
        self.broker.audit.write(tool=name, args=inp, decision="approved" if ok else "declined", ok=ok, summary=tool.description, via="claude-code")
        if ok:
            return {"behavior": "allow", "updatedInput": inp}
        return {"behavior": "deny", "message": "The user declined this action."}

    def call(self, name: str, args: dict) -> dict:
        if name == "approve":
            return {"content": [{"type": "text", "text": json.dumps(self.approve(args))}]}
        if name == "undo_last":
            return {"content": [{"type": "text", "text": self.broker.undo_last()}]}
        if name not in self.broker.tools:
            return {"content": [{"type": "text", "text": f"unknown tool {name}"}], "isError": True}
        res = self.broker.execute(name, args or {})
        text = res.summary if not res.data else f"{res.summary}\n{json.dumps(res.data)[:6000]}"
        return {"content": [{"type": "text", "text": text}], "isError": not res.ok}

    def handle(self, req: dict) -> Optional[dict]:
        method, rid = req.get("method"), req.get("id")
        params = req.get("params") or {}
        if method == "initialize":
            result = {"protocolVersion": params.get("protocolVersion") or PROTOCOL, "capabilities": {"tools": {}}, "serverInfo": SERVER}
        elif method == "tools/list":
            result = {"tools": self.tool_list()}
        elif method == "tools/call":
            try:
                result = self.call(str(params.get("name", "")), params.get("arguments") or {})
            except Exception as e:  # noqa: BLE001
                result = {"content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}], "isError": True}
        elif method == "ping":
            result = {}
        elif rid is None:
            return None            # notification
        else:
            result = {}
        return {"jsonrpc": "2.0", "id": rid, "result": result}


def serve(inp=None, out=None, broker: Optional[A.ActionBroker] = None, cfg: Optional[S.Settings] = None) -> int:
    inp = inp or sys.stdin
    out = out or sys.stdout
    cfg = cfg or S.load()
    broker = broker or A.ActionBroker(make_consent(cfg), cfg=cfg)
    srv = Server(broker, cfg)
    for line in inp:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except ValueError:
            continue
        if isinstance(req, list):
            responses = [r for r in (srv.handle(x) for x in req if isinstance(x, dict)) if r]
            if responses:
                out.write(json.dumps(responses) + "\n")
                out.flush()
            continue
        if not isinstance(req, dict):
            continue
        resp = srv.handle(req)
        if resp is not None:
            out.write(json.dumps(resp) + "\n")
            out.flush()
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--tools" in argv:
        cfg = S.load()
        for t in Server(A.ActionBroker(policy_consent("deny"), cfg=cfg), cfg).tool_list():
            print(f"{t['name']}: {t['description']}")
        return 0
    return serve()


if __name__ == "__main__":
    sys.exit(main())
