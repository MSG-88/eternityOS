"""Index of launchable applications from .desktop files (XDG), used by the radial launcher
and by the assistant's open_app tool. Eternity's own tools come first, then the everyday
apps named in the design (Files, Mail, Calendar, Notes, Music, Photos, Terminal, Browser,
Messages, Code, Monitor, Settings) when something installed provides them, then the rest.
"""
import configparser
import os
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

PREFERRED = ["eternity-ask", "eternity-chat", "eternity-install", "eternity-monitor", "eternity-settings", "eternity-find",
             "thunar", "firefox-esr", "firefox", "xfce4-terminal", "mousepad", "ristretto", "atril", "xfce4-settings-manager",
             "xfce4-taskmanager", "pavucontrol", "xarchiver"]
HIDE_CATEGORIES = {"Screensaver", "Settings"}   # settings dialogs clutter the ring; the settings manager stays via PREFERRED


@dataclass(order=True)
class App:
    rank: int
    name: str
    exec_cmd: str = field(compare=False)
    icon: str = field(default="", compare=False)
    comment: str = field(default="", compare=False)
    desktop_id: str = field(default="", compare=False)
    keywords: List[str] = field(default_factory=list, compare=False)
    terminal: bool = field(default=False, compare=False)


def desktop_dirs() -> List[str]:
    dirs = [os.path.join(os.path.expanduser("~"), ".local", "share", "applications")]
    for base in (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":"):
        dirs.append(os.path.join(base, "applications"))
    return [d for d in dirs if os.path.isdir(d)]


def _clean_exec(cmd: str) -> str:
    return " ".join(tok for tok in cmd.split() if not (tok.startswith("%") and len(tok) == 2))


def load(extra_dirs: Optional[List[str]] = None) -> List[App]:
    seen = set()
    apps: List[App] = []
    for d in (extra_dirs or []) + desktop_dirs():
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".desktop") or fn in seen:
                continue
            cp = configparser.RawConfigParser(strict=False, interpolation=None)
            try:
                cp.read(os.path.join(d, fn), encoding="utf-8")
                e = cp["Desktop Entry"]
            except (configparser.Error, KeyError, UnicodeDecodeError):
                continue
            if e.get("Type", "Application") != "Application" or e.get("NoDisplay", "false").lower() == "true" \
                    or e.get("Hidden", "false").lower() == "true" or not e.get("Exec"):
                continue
            only = e.get("OnlyShowIn", "")
            if only and "XFCE" not in only:
                continue
            cats = set(e.get("Categories", "").strip(";").split(";")) if e.get("Categories") else set()
            did = fn[:-8]
            if cats & HIDE_CATEGORIES and did not in PREFERRED:
                continue
            seen.add(fn)
            rank = PREFERRED.index(did) if did in PREFERRED else 100
            kws = [k.lower() for k in e.get("Keywords", "").strip(";").split(";") if k] + [e.get("GenericName", "").lower()]
            apps.append(App(rank, e.get("Name", did), _clean_exec(e["Exec"]), e.get("Icon", ""), e.get("Comment", ""), did,
                            [k for k in kws if k], e.get("Terminal", "false").lower() == "true"))
    apps.sort()
    return apps


def launch(app: App) -> None:
    if app.desktop_id and subprocess.run(["which", "gtk-launch"], capture_output=True).returncode == 0:
        subprocess.Popen(["gtk-launch", app.desktop_id], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    cmd = shlex.split(app.exec_cmd)
    if app.terminal:
        cmd = ["xfce4-terminal", "-e", app.exec_cmd]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
