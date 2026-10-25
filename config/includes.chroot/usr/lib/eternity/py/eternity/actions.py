"""Actions the assistant can take on the user's behalf, with the human in control.

Every tool declares a risk class. The broker asks for consent through a callback before
running anything that changes state (read-only tools run without asking once the user has
raised the trust level), appends every decision and outcome to the audit log
(~/.local/state/eternity/actions.log, JSON lines) and keeps an undo stack for tools that
know their inverse. Nothing escalates privileges: a tool that would need root fails with a
message instead of prompting.
"""
import datetime as _dt
import json
import os
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from . import settings as S

RISK_READ, RISK_CHANGE, RISK_DANGEROUS = "read", "change", "dangerous"


@dataclass
class ActionResult:
    ok: bool
    summary: str
    data: dict = field(default_factory=dict)
    undo_token: Optional[dict] = None


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    run: Callable[[dict], ActionResult]
    risk: str = RISK_CHANGE
    undo: Optional[Callable[[dict, ActionResult], str]] = None

    def schema(self) -> dict:
        return {"name": self.name, "description": self.description, "parameters": self.parameters}


class Audit:
    def __init__(self, path: Optional[str] = None):
        self.path = path or os.path.join(S.state_dir(), "actions.log")

    def write(self, **entry) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        entry = {"ts": _dt.datetime.now().isoformat(timespec="seconds"), **entry}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def last_undoable(self) -> Optional[dict]:
        """The newest executed action that has an undo token and was not undone yet."""
        undone = set()
        for e in reversed(self.tail(200)):
            if e.get("decision") == "undo" and e.get("of"):
                undone.add(e["of"])
            elif e.get("undoable") and e.get("undo_token") is not None and e.get("id") not in undone:
                return e
        return None

    def tail(self, n: int = 20) -> List[dict]:
        try:
            with open(self.path, encoding="utf-8") as f:
                lines = f.readlines()[-n:]
        except OSError:
            return []
        out = []
        for line in lines:
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
        return out


def _run(cmd: List[str], timeout: float = 20.0, input_text: Optional[str] = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, input=input_text, check=False)


# ------------------------------------------------------------------------------ tools
def t_system_info(args: dict) -> ActionResult:
    info = {}
    try:
        with open("/proc/meminfo") as f:
            mem = dict(line.split(":", 1) for line in f if ":" in line)
        info["memory_total_gb"] = round(int(mem["MemTotal"].split()[0]) / 1048576, 1)
        info["memory_available_gb"] = round(int(mem["MemAvailable"].split()[0]) / 1048576, 1)
    except (OSError, KeyError, ValueError):
        pass
    try:
        with open("/proc/loadavg") as f:
            info["load_1m"] = float(f.read().split()[0])
    except (OSError, ValueError):
        pass
    info["cpu_threads"] = os.cpu_count()
    try:
        du = shutil.disk_usage(os.path.expanduser("~"))
        info["home_free_gb"] = round(du.free / 1e9, 1)
    except OSError:
        pass
    for bat in ("BAT0", "BAT1"):
        p = f"/sys/class/power_supply/{bat}/capacity"
        if os.path.exists(p):
            with open(p) as f:
                info["battery_percent"] = int(f.read().strip() or 0)
            break
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    info["os"] = line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    summary = ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in info.items())
    return ActionResult(True, summary, info)


def t_list_recent_files(args: dict) -> ActionResult:
    n = int(args.get("count", 8))
    roots = [os.path.expanduser(p) for p in ("~/Documents", "~/Desktop", "~/Downloads", "~/Pictures", "~/Projects")]
    found = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")][:50]
            for fn in filenames:
                if fn.startswith("."):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    found.append((os.stat(p).st_mtime, p))
                except OSError:
                    pass
            if len(found) > 5000:
                break
    found.sort(reverse=True)
    files = [{"path": p, "modified": _dt.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M")} for t, p in found[:n]]
    return ActionResult(True, f"{len(files)} recent files", {"files": files})


def t_find_files(args: dict) -> ActionResult:
    pattern = str(args.get("pattern", "")).strip()
    if not pattern:
        return ActionResult(False, "no pattern given")
    home = os.path.expanduser("~")
    r = _run(["find", home, "-xdev", "-not", "-path", "*/.*", "-iname", f"*{pattern}*", "-maxdepth", "6"], timeout=30)
    paths = [p for p in r.stdout.splitlines() if p][:50]
    return ActionResult(True, f"{len(paths)} matches for '{pattern}'", {"paths": paths})


def t_search_meaning(args: dict) -> ActionResult:
    """Search by meaning over the indexed home folders (eternity.find)."""
    query = str(args.get("query", "")).strip()
    if not query:
        return ActionResult(False, "no query given")
    from . import find as F
    idx = F.Index()
    if idx.count() == 0:
        idx.build()
    hits = idx.search(query, k=int(args.get("count", 10)))
    g = F.group(hits)
    return ActionResult(True, F.suggestion(g) if hits else "nothing close enough",
                        {"matches": [{"path": h.path, "kind": h.kind, "when": h.when} for h in hits], "summary": g})


def _desktop_entries() -> Dict[str, str]:
    out = {}
    for d in ("/usr/share/applications", os.path.expanduser("~/.local/share/applications")):
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if fn.endswith(".desktop"):
                out[fn[:-8].lower()] = os.path.join(d, fn)
    return out


def t_open_app(args: dict) -> ActionResult:
    name = str(args.get("name", "")).strip().lower()
    entries = _desktop_entries()
    match = next((v for k, v in entries.items() if k == name), None) or \
        next((v for k, v in entries.items() if name and name in k), None)
    if not match:
        return ActionResult(False, f"no application called '{name}'")
    if shutil.which("gtk-launch"):
        subprocess.Popen(["gtk-launch", os.path.basename(match)[:-8]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen(["xdg-open", match], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return ActionResult(True, f"opened {os.path.basename(match)[:-8]}", {"desktop": match})


def t_open_url(args: dict) -> ActionResult:
    url = str(args.get("url", "")).strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return ActionResult(False, "only http(s) links are opened")
    subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return ActionResult(True, f"opened {url}")


def _volume_get() -> Optional[int]:
    if shutil.which("wpctl"):
        r = _run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
        try:
            return int(round(float(r.stdout.split()[1]) * 100))
        except (IndexError, ValueError):
            return None
    if shutil.which("pactl"):
        r = _run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
        for tok in r.stdout.replace("/", " ").split():
            if tok.endswith("%"):
                try:
                    return int(tok[:-1])
                except ValueError:
                    pass
    return None


def _volume_set(pct: int) -> bool:
    pct = max(0, min(100, int(pct)))
    if shutil.which("wpctl"):
        return _run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{pct}%"]).returncode == 0
    if shutil.which("pactl"):
        return _run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{pct}%"]).returncode == 0
    return False


def t_set_volume(args: dict) -> ActionResult:
    before = _volume_get()
    pct = int(args.get("percent", 50))
    if not _volume_set(pct):
        return ActionResult(False, "no audio control available (wpctl/pactl)")
    return ActionResult(True, f"volume set to {pct}%", {"before": before}, undo_token={"percent": before} if before is not None else None)


def u_set_volume(args: dict, result: ActionResult) -> str:
    pct = (result.undo_token or {}).get("percent")
    if pct is None:
        return "previous volume unknown"
    _volume_set(pct)
    return f"volume back to {pct}%"


def t_write_note(args: dict) -> ActionResult:
    title = str(args.get("title", "note")).strip() or "note"
    body = str(args.get("text", ""))
    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in title).strip()[:60] or "note"
    notes = os.path.join(os.path.expanduser("~"), "Documents", "Notes")
    os.makedirs(notes, exist_ok=True)
    path = os.path.join(notes, f"{_dt.date.today().isoformat()} {safe}.md")
    if os.path.exists(path):
        path = os.path.join(notes, f"{_dt.date.today().isoformat()} {safe} {int(time.time())}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n{body}\n")
    return ActionResult(True, f"note saved: {path}", {"path": path}, undo_token={"path": path})


def u_write_note(args: dict, result: ActionResult) -> str:
    path = (result.undo_token or {}).get("path")
    if path and os.path.exists(path):
        os.remove(path)
        return f"removed {path}"
    return "nothing to remove"


def t_run_command(args: dict) -> ActionResult:
    cmd = str(args.get("command", "")).strip()
    if not cmd:
        return ActionResult(False, "empty command")
    if cmd.startswith("sudo") or " sudo " in f" {cmd} " or cmd.startswith("pkexec"):
        return ActionResult(False, "commands that escalate privileges are not run by the assistant")
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60, check=False)
    except subprocess.TimeoutExpired:
        return ActionResult(False, "command timed out after 60 s")
    out = (r.stdout + r.stderr).strip()
    return ActionResult(r.returncode == 0, f"exit {r.returncode}: {out[:400]}", {"stdout": r.stdout[-4000:], "returncode": r.returncode})


def t_power(args: dict) -> ActionResult:
    what = str(args.get("action", "")).strip()
    if what not in ("suspend", "reboot", "poweroff", "lock"):
        return ActionResult(False, "action must be suspend, reboot, poweroff or lock")
    if what == "lock":
        for cmd in (["xflock4"], ["loginctl", "lock-session"]):
            if shutil.which(cmd[0]):
                subprocess.Popen(cmd)
                return ActionResult(True, "screen locked")
        return ActionResult(False, "no screen locker found")
    subprocess.Popen(["systemctl", what])
    return ActionResult(True, f"{what} requested")


def t_set_setting(args: dict) -> ActionResult:
    key, value = str(args.get("key", "")), args.get("value")
    cfg = S.load()
    allowed = {"verbosity": str, "proactive": bool, "voice": str, "trust_level": int, "name": str}
    if key not in allowed:
        return ActionResult(False, f"setting '{key}' cannot be changed by the assistant")
    before = getattr(cfg, key)
    try:
        setattr(cfg, key, allowed[key](value))
    except (TypeError, ValueError):
        return ActionResult(False, f"bad value for {key}")
    S.save(cfg)
    return ActionResult(True, f"{key} is now {getattr(S.load(), key)}", undo_token={"key": key, "before": before})


def u_set_setting(args: dict, result: ActionResult) -> str:
    tok = result.undo_token or {}
    cfg = S.load()
    setattr(cfg, tok["key"], tok["before"])
    S.save(cfg)
    return f"{tok['key']} restored to {tok['before']}"


def t_hardware_report(args: dict) -> ActionResult:
    from . import hw
    inv = hw.inventory()
    probs = hw.problems(inv)
    summ = hw.summary(inv)
    head = "no hardware problems found" if summ["ok"] else f"{summ['bad']} problem(s), {summ['warn']} warning(s)"
    data = {"report": hw.report(inv), "problems": [f"{s}: {m}" for s, m in probs],
            "network": inv["network"], "bluetooth": inv["bluetooth"], "graphics": inv["graphics"], "sound": inv["sound"],
            "power": inv["power"], "firmware": inv["firmware"], "platform": inv["platform"]}
    return ActionResult(True, head, data)


def default_tools() -> List[Tool]:
    obj = lambda props, req=(): {"type": "object", "properties": props, "required": list(req)}  # noqa: E731
    return [
        Tool("system_info", "Memory, load, disk space, battery and OS version of this computer.", obj({}), t_system_info, RISK_READ),
        Tool("list_recent_files", "The most recently changed files in the user's folders.",
             obj({"count": {"type": "integer", "description": "how many, default 8"}}), t_list_recent_files, RISK_READ),
        Tool("find_files", "Find files under the home folder whose name contains a pattern.",
             obj({"pattern": {"type": "string"}}, ["pattern"]), t_find_files, RISK_READ),
        Tool("search_files_by_meaning", "Find the user's files by what they are about (photos from a trip, the spec about X, invoices from March); uses the on-device index.",
             obj({"query": {"type": "string"}, "count": {"type": "integer"}}, ["query"]), t_search_meaning, RISK_READ),
        Tool("hardware_report", "Devices of this computer with their drivers, missing firmware, wifi/Bluetooth/sound/display/battery state and detected problems. Use for 'X is not working'.",
             obj({}), t_hardware_report, RISK_READ),
        Tool("open_app", "Open an installed application by name (for example 'firefox', 'files', 'terminal').",
             obj({"name": {"type": "string"}}, ["name"]), t_open_app, RISK_CHANGE),
        Tool("open_url", "Open a web link in the browser.", obj({"url": {"type": "string"}}, ["url"]), t_open_url, RISK_CHANGE),
        Tool("set_volume", "Set the speaker volume in percent.", obj({"percent": {"type": "integer"}}, ["percent"]),
             t_set_volume, RISK_CHANGE, u_set_volume),
        Tool("write_note", "Save a markdown note in ~/Documents/Notes.",
             obj({"title": {"type": "string"}, "text": {"type": "string"}}, ["title", "text"]), t_write_note, RISK_CHANGE, u_write_note),
        Tool("set_setting", "Change how Eternity shows up: verbosity (brief/normal/detailed), proactive (true/false), voice, trust_level (0/1), name.",
             obj({"key": {"type": "string"}, "value": {}}, ["key", "value"]), t_set_setting, RISK_CHANGE, u_set_setting),
        Tool("run_command", "Run a shell command as the user (never with sudo). Use only when no other tool fits.",
             obj({"command": {"type": "string"}}, ["command"]), t_run_command, RISK_DANGEROUS),
        Tool("power", "Lock the screen, suspend, reboot or power off.",
             obj({"action": {"type": "string", "enum": ["lock", "suspend", "reboot", "poweroff"]}}, ["action"]), t_power, RISK_DANGEROUS),
    ]


# ----------------------------------------------------------------------------- broker
@dataclass
class Executed:
    tool: Tool
    args: dict
    result: ActionResult
    undone: bool = False
    id: str = ""


class ActionBroker:
    """Runs tool calls under the user's rules: consent, audit, undo."""

    def __init__(self, consent: Callable[[Tool, dict], bool], cfg: Optional[S.Settings] = None,
                 audit: Optional[Audit] = None, tools: Optional[List[Tool]] = None):
        self.consent = consent
        self.cfg = cfg or S.load()
        self.audit = audit or Audit()
        self.tools: Dict[str, Tool] = {t.name: t for t in (tools or default_tools())}
        self.history: List[Executed] = []

    def schemas(self) -> List[dict]:
        return [t.schema() for t in self.tools.values()]

    def needs_consent(self, tool: Tool) -> bool:
        if self.cfg.trust_level >= 2:
            return False  # the owner's default: act, log, keep it undoable; Settings can bring the cards back
        if tool.risk == RISK_READ:
            return self.cfg.trust_level < 1
        return True   # at levels 0 and 1 changes and dangerous actions ask

    def execute(self, name: str, args: dict) -> ActionResult:
        tool = self.tools.get(name)
        if not tool:
            res = ActionResult(False, f"unknown tool {name}")
            self.audit.write(tool=name, args=args, decision="rejected", ok=False, summary=res.summary)
            return res
        if self.needs_consent(tool):
            if not self.consent(tool, args):
                res = ActionResult(False, "declined by the user")
                self.audit.write(tool=name, args=args, decision="declined", ok=False, summary=res.summary)
                return res
            decision = "approved"
        else:
            decision = "auto (read-only, trusted)"
        try:
            res = tool.run(args)
        except Exception as e:  # a tool must never take the assistant down
            res = ActionResult(False, f"{type(e).__name__}: {e}")
        entry_id = f"{int(time.time() * 1000)}-{os.getpid()}-{len(self.history)}"
        self.history.append(Executed(tool, args, res, id=entry_id))
        undoable = bool(tool.undo and res.ok and res.undo_token is not None)
        self.audit.write(id=entry_id, tool=name, args=args, decision=decision,
                         ok=res.ok, summary=res.summary, undoable=undoable,
                         undo_token=res.undo_token if undoable else None)
        return res

    def undoable(self) -> Optional[Executed]:
        for ex in reversed(self.history):
            if not ex.undone and ex.tool.undo and ex.result.ok and ex.result.undo_token is not None:
                return ex
        return None

    def undo_last(self) -> str:
        ex = self.undoable()
        if not ex:
            return self.undo_from_log()
        msg = ex.tool.undo(ex.args, ex.result)
        ex.undone = True
        self.audit.write(tool=ex.tool.name, args=ex.args, decision="undo", of=ex.id, ok=True, summary=msg)
        return msg

    def undo_from_log(self) -> str:
        """Undo the newest undoable action recorded in the audit log, whichever process ran it
        (the MCP server used by Claude Code runs actions outside the Ask window)."""
        e = self.audit.last_undoable()
        if not e:
            return "nothing to undo"
        tool = self.tools.get(e.get("tool", ""))
        if not tool or not tool.undo:
            return f"{e.get('tool')} cannot be undone"
        res = ActionResult(True, e.get("summary", ""), undo_token=e.get("undo_token"))
        try:
            msg = tool.undo(e.get("args") or {}, res)
        except Exception as ex:  # noqa: BLE001
            msg = f"undo failed: {type(ex).__name__}: {ex}"
        self.audit.write(tool=tool.name, args=e.get("args") or {}, decision="undo", of=e.get("id"), ok=True, summary=msg)
        return msg


# Claude Code's own tools, classified like ours so the same consent rules apply to them.
BUILTIN_RISK = {"Read": RISK_READ, "Glob": RISK_READ, "Grep": RISK_READ, "LS": RISK_READ, "WebSearch": RISK_READ,
                "WebFetch": RISK_READ, "TodoWrite": RISK_READ, "Task": RISK_READ, "NotebookRead": RISK_READ,
                "Edit": RISK_CHANGE, "Write": RISK_CHANGE, "MultiEdit": RISK_CHANGE, "NotebookEdit": RISK_CHANGE,
                "Bash": RISK_DANGEROUS, "KillShell": RISK_DANGEROUS}
_ESCALATES = ("sudo", "pkexec", "su -", "su root", "doas")


def builtin_tool(name: str, args: dict) -> Tool:
    """A Tool record for one of Claude Code's built-in tools, so the consent dialog, the audit
    log and the trust rules treat it exactly like an Eternity action."""
    risk = BUILTIN_RISK.get(name, RISK_DANGEROUS)
    if name == "Bash":
        desc = f"Run a shell command: {args.get('command', '')}"
    elif name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        desc = f"{'Create or overwrite' if name == 'Write' else 'Edit'} the file {args.get('file_path', args.get('notebook_path', '?'))}"
    elif name == "Read":
        desc = f"Read the file {args.get('file_path', '?')}"
    elif name in ("Glob", "Grep"):
        desc = f"Search files for {args.get('pattern', '?')}"
    elif name in ("WebFetch", "WebSearch"):
        desc = f"Fetch from the web: {args.get('url') or args.get('query', '?')}"
    else:
        desc = f"Use the {name} tool"
    return Tool(name, desc, {"type": "object", "properties": {}}, lambda a: ActionResult(False, "not run here"), risk)


def escalates_privileges(name: str, args: dict) -> bool:
    if name != "Bash":
        return False
    cmd = f" {str(args.get('command', ''))} "
    return any(f" {w}" in cmd or cmd.strip().startswith(w) for w in _ESCALATES)


def describe_call(tool: Tool, args: dict) -> str:
    """Human sentence for the consent dialog."""
    if not args:
        return f"{tool.description}"
    rendered = ", ".join(f"{k} = {shlex.quote(str(v)) if isinstance(v, str) and ' ' in str(v) else v}" for k, v in args.items())
    return f"{tool.description}\n{rendered}"
