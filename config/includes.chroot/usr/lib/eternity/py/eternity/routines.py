"""Routines: named task sequences the user teaches Eternity in plain words and runs on command or
by voice ("set up my morning routine: open firefox and the terminal" -> define_routine; "run my
morning routine" -> run_routine). Stored on this device in ~/.local/state/eternity/routines.json.

A routine is {"name", "description", "steps"} where each step is {"tool": <action name>, "args": {}}.
The ActionBroker runs the steps, so every step is still consented at the user's trust level and
audited — a routine is a shortcut, never a way around the human-in-control rules.
"""
import json
import os
import re
from typing import Dict, List, Optional

from . import settings as S

NAME_MAX = 60
STEPS_MAX = 25


class RoutineError(Exception):
    pass


def normalize(name: str) -> str:
    """'My Morning Routine' / 'morning-routine' / '  MORNING  routine ' -> 'morning routine'."""
    n = re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()
    return re.sub(r"\s+", " ", n)


class Routines:
    def __init__(self, path: Optional[str] = None):
        self.path = path or os.path.join(S.state_dir(), "routines.json")
        self._items: Dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        for item in data.get("routines", []):
            if isinstance(item, dict) and item.get("name") and item.get("steps"):
                self._items[normalize(item["name"])] = item

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"routines": list(self._items.values())}, f, indent=1)
        os.replace(tmp, self.path)

    @staticmethod
    def _clean_steps(steps) -> List[dict]:
        if not isinstance(steps, list) or not steps:
            raise RoutineError("a routine needs at least one step")
        out = []
        for s in steps[:STEPS_MAX]:
            if not isinstance(s, dict) or not s.get("tool"):
                raise RoutineError("each step must name a tool")
            out.append({"tool": str(s["tool"]), "args": s.get("args") or {}})
        return out

    def define(self, name: str, steps, description: str = "") -> dict:
        key = normalize(name)
        if not key:
            raise RoutineError("a routine needs a name")
        item = {"name": " ".join(name.split()).strip()[:NAME_MAX], "description": (description or "").strip(),
                "steps": self._clean_steps(steps)}
        self._items[key] = item
        self._save()
        return item

    def get(self, name: str) -> Optional[dict]:
        return self._items.get(normalize(name))

    def list(self) -> List[dict]:
        return sorted(self._items.values(), key=lambda x: normalize(x["name"]))

    def forget(self, name: str) -> int:
        key = normalize(name)
        if key in self._items:
            del self._items[key]
            self._save()
            return 1
        return 0

    def prompt_section(self) -> str:
        """What the assistant should know about the user's routines, for the system prompt."""
        if not self._items:
            return ""
        lines = ["The user has saved routines (run one with the run_routine tool, by name):"]
        for it in self.list():
            desc = f" — {it['description']}" if it.get("description") else ""
            lines.append(f"- {it['name']}{desc} ({len(it['steps'])} steps)")
        return "\n".join(lines)
