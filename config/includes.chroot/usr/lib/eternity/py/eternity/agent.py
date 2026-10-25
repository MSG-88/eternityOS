"""The assistant loop: a question goes to the chosen provider with the OS knowledge in the
system prompt and the tool schemas; tool calls go through the ActionBroker (consent, audit,
undo) and their results back to the model until it answers in text.

    agent = Agent(consent=lambda tool, args: True)
    for kind, payload in agent.ask("what changed in my files today?"):
        ...  # ("text", str) | ("status", str) | ("action", dict) | ("done", Metrics)
"""
import os
import platform
import shutil
import socket
from typing import Callable, Iterator, List, Optional, Tuple

from . import actions as A
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
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "XFCE")
    live = os.path.exists("/run/live/medium")
    bits.append(f"desktop {desktop}; {'live session from the USB stick (nothing persists)' if live else 'installed system'}")
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


def system_prompt(cfg: S.Settings) -> str:
    style = {"brief": "Answer in one or two short sentences.",
             "normal": "Answer concisely, in a few sentences unless more is needed.",
             "detailed": "Answer thoroughly with the relevant details."}[cfg.verbosity]
    name = f" The user's name is {cfg.name}." if cfg.name else ""
    agent = ("You can act through tools. Prefer a tool over guessing when a question is about this computer. "
             "Every action is shown to the user for confirmation before it runs and can be undone; "
             "never pretend an action happened if the tool result says it was declined or failed."
             if cfg.agent_mode else "You cannot run actions in this session; explain what the user can do.")
    return (f"You are Eternity, the assistant built into Eternity 08, a personal operating system.{name} "
            f"{style} Be warm and direct, no filler. {agent}\n\nAbout this machine and OS:\n{os_knowledge()}")


class Agent:
    def __init__(self, consent: Callable[[A.Tool, dict], bool], cfg: Optional[S.Settings] = None,
                 provider: Optional[P.Provider] = None, secrets: Optional[S.SecretStore] = None,
                 broker: Optional[A.ActionBroker] = None):
        self.cfg = cfg or S.load()
        self.secrets = secrets
        self._provider = provider
        self.broker = broker or A.ActionBroker(consent, cfg=self.cfg)
        self.history: List[dict] = []

    @property
    def provider(self) -> P.Provider:
        if self._provider is None:
            self._provider = P.get_provider(self.cfg, self.secrets)
        return self._provider

    def reset(self) -> None:
        self.history = []

    def ask(self, question: str) -> Iterator[Tuple[str, object]]:
        self.history.append({"role": "user", "content": question})
        tools = self.broker.schemas() if self.cfg.agent_mode else None
        system = system_prompt(self.cfg)
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
