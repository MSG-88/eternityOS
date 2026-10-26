"""The assistant loop: a question goes to the chosen provider with the OS knowledge in the
system prompt and the tool schemas; tool calls go through the ActionBroker (consent, audit,
undo) and their results back to the model until it answers in text.

    agent = Agent(consent=lambda tool, args: True)
    for kind, payload in agent.ask("what changed in my files today?"):
        ...  # ("text", str) | ("status", str) | ("action", dict) | ("done", Metrics)
"""
import os
import platform
import re
import shutil
import socket
import subprocess
from typing import Callable, Iterator, List, Optional, Tuple

from . import actions as A
from . import memory as M
from . import providers as P
from . import settings as S

MAX_TOOL_ROUNDS = 6


def os_knowledge() -> str:
    """What the assistant knows about this machine and this OS, generated from the system."""
    bits: List[str] = []
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    bits.append(line.split("=", 1)[1].strip().strip('"'))
    except OSError:
        bits.append("Eternity 08")
    bits.append(f"kernel {platform.release()}, host {socket.gethostname()}, user {os.environ.get('USER', '')}")
    bits.append(f"{os.cpu_count()} CPU threads")
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    bits.append(f"{int(line.split()[1]) / 1048576:.1f} GB memory")
                    break
    except OSError:
        pass
    live = os.path.exists("/run/live/medium")
    bits.append(f"{session_description()}; {'live session from the USB stick (nothing persists)' if live else 'installed system'}")
    tools = [t for t in ("eternity-chat", "eternity-ai", "eternity-install", "eternity-find", "eternity-hw", "claude", "firefox", "thunar", "xfce4-terminal", "mousepad")
             if shutil.which(t)]
    bits.append("installed Eternity tools and apps: " + ", ".join(tools))
    bits.append("local AI: llama.cpp with Qwen3.5 GGUF models in /opt/eternity/models; Python ML venv /opt/eternity/venv")
    if shutil.which("claude"):
        bits.append("Claude Code is installed (the user may sign in with their own Claude account; Eternity's tools reach it through the eternity MCP server)")
    bits.append("hardware: the hardware_report tool (eternity-hw) lists devices, drivers, missing firmware and radio/power state; use it for any question about wifi, Bluetooth, sound, display, battery or 'X is not working'")
    bits.append("settings: ~/.config/eternity/settings.json; action log ~/.local/state/eternity/actions.log; "
                "installer: 'Install Eternity 08' (Calamares) in live sessions")
    return "\n".join("- " + b for b in bits)


_HYPR_VERSION: Optional[str] = None


def hyprland_version() -> str:
    """'0.55.2' from `Hyprland --version` (cached; '' when it cannot be read)."""
    global _HYPR_VERSION
    if _HYPR_VERSION is None:
        _HYPR_VERSION = ""
        exe = shutil.which("Hyprland")
        if exe:
            try:
                out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=3).stdout
                m = re.search(r"v?(\d+\.\d+(?:\.\d+)?)", out.splitlines()[0] if out else "")
                _HYPR_VERSION = m.group(1) if m else ""
            except (OSError, subprocess.SubprocessError, IndexError):
                _HYPR_VERSION = ""
    return _HYPR_VERSION


def session_description() -> str:
    """Which desktop session the user is in, so the assistant looks at the right compositor."""
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "XFCE")
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") or desktop.lower() == "eternity":
        v = hyprland_version()
        return (f"session: the Eternity shell (Quickshell) on the Hyprland Wayland compositor{' ' + v if v else ''}; "
                "there is no X11 window manager here; windows, workspaces and keybinds come from "
                "`hyprctl` (hyprctl version / clients / monitors); Super+Space asks Eternity, Super+Return opens a terminal")
    return f"session: the classic {desktop} desktop (X11) with the xfwm4 window manager"


def system_prompt(cfg: S.Settings, memory: Optional["M.Memory"] = None) -> str:
    style = {"brief": "Answer in one or two short sentences.",
             "normal": "Answer concisely, in a few sentences unless more is needed.",
             "detailed": "Answer thoroughly with the relevant details."}[cfg.verbosity]
    name = f" The user's name is {cfg.name}." if cfg.name else ""
    agent = ("You can act through tools. Prefer a tool over guessing when a question is about this computer. "
             "Every action is shown to the user for confirmation before it runs and can be undone; "
             "never pretend an action happened if the tool result says it was declined or failed."
             if cfg.agent_mode else "You cannot run actions in this session; explain what the user can do.")
    known = memory.prompt_section() if memory is not None else ""
    learned = f"\n\nWhat you know about this user (learned on this device, never sent anywhere else):\n{known}" if known else ""
    routines = ""
    try:
        from . import routines as RT
        rsec = RT.Routines().prompt_section()
        routines = f"\n\n{rsec}" if rsec else ""
    except Exception:  # noqa: BLE001  (routines are a convenience, never block an answer)
        routines = ""
    return (f"You are Eternity, the assistant built into Eternity 08, a personal operating system.{name} "
            f"{style} Be warm and direct, no filler. {agent}\n\nAbout this machine and OS:\n{os_knowledge()}{learned}{routines}")


class Agent:
    def __init__(self, consent: Callable[[A.Tool, dict], bool], cfg: Optional[S.Settings] = None,
                 provider: Optional[P.Provider] = None, secrets: Optional[S.SecretStore] = None,
                 broker: Optional[A.ActionBroker] = None, memory: Optional[M.Memory] = None):
        self.cfg = cfg or S.load()
        self.secrets = secrets
        self._provider = provider
        self.broker = broker or A.ActionBroker(consent, cfg=self.cfg)
        self.history: List[dict] = []
        self.memory = memory if memory is not None else M.Memory(enabled=self.cfg.learning)
        self.memory.enabled = self.cfg.learning

    @property
    def provider(self) -> P.Provider:
        if self._provider is None:
            self._provider = P.get_provider(self.cfg, self.secrets)
        return self._provider

    def reset(self) -> None:
        self.history = []

    def ask(self, question: str) -> Iterator[Tuple[str, object]]:
        """Runs the question; records it (and the tools used) in memory when the answer is done."""
        actions: List[dict] = []
        try:
            for kind, payload in self._ask(question):
                if kind == "action" and isinstance(payload, dict):
                    actions.append(payload)
                yield (kind, payload)
        finally:
            try:
                self.memory.observe(question, actions)
            except Exception:  # noqa: BLE001  (memory must never break an answer)
                pass

    def _ask(self, question: str) -> Iterator[Tuple[str, object]]:
        self.history.append({"role": "user", "content": question})
        tools = self.broker.schemas() if self.cfg.agent_mode else None
        system = system_prompt(self.cfg, self.memory)
        last_metrics = None
        try:
            provider = self.provider
        except P.ProviderError as e:
            yield ("status", str(e))
            yield ("done", P.Metrics(provider=self.cfg.effective_provider()))
            return
        if getattr(provider, "agentic", False):
            # the runtime (Claude Code) runs its own tool loop; consent happens in eternity-mcp
            text = ""
            try:
                for kind, payload in provider.stream(self.history, system=system):
                    if kind == "text":
                        text += payload
                    elif kind == "done":
                        last_metrics = payload
                    yield (kind, payload)
            except P.ProviderError as e:
                yield ("status", str(e))
                yield ("done", last_metrics or P.Metrics(provider=self.cfg.effective_provider()))
                return
            self.history.append({"role": "assistant", "content": text})
            if last_metrics is None:
                yield ("done", P.Metrics(provider=self.cfg.effective_provider()))
            return
        for _round in range(MAX_TOOL_ROUNDS):
            text, calls = "", []
            try:
                for kind, payload in self.provider.stream(self.history, system=system, tools=tools):
                    if kind == "text":
                        text += payload
                        yield ("text", payload)
                    elif kind == "tool_call":
                        calls.append(payload)
                    elif kind == "done":
                        last_metrics = payload
            except P.ProviderError as e:
                yield ("status", str(e))
                yield ("done", last_metrics or P.Metrics(provider=self.cfg.effective_provider()))
                return
            if not calls:
                self.history.append({"role": "assistant", "content": text})
                break
            self.history.append({"role": "assistant", "content": text,
                                 "tool_calls": [{"id": c["id"], "type": "function",
                                                 "function": {"name": c["name"], "arguments": __import__("json").dumps(c["arguments"])}}
                                                for c in calls]})
            for c in calls:
                yield ("status", f"{c['name']} …")
                res = self.broker.execute(c["name"], c["arguments"] if isinstance(c["arguments"], dict) else {})
                yield ("action", {"name": c["name"], "args": c["arguments"], "ok": res.ok, "summary": res.summary,
                                  "undoable": self.broker.undoable() is not None})
                content = res.summary if not res.data else f"{res.summary}\n{__import__('json').dumps(res.data)[:3000]}"
                self.history.append({"role": "tool", "tool_call_id": c["id"], "content": content})
        yield ("done", last_metrics or P.Metrics(provider=self.cfg.effective_provider()))

    def undo_last(self) -> str:
        return self.broker.undo_last()
