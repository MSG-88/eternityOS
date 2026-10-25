"""What Eternity remembers about its user, so the assistant grows with every question. Local
only: ~/.local/state/eternity/memory.json, never sent anywhere except as a short section of the
system prompt to the provider the user chose.

    m = Memory()
    m.observe(question, actions)   # after every ask: counts tools, keeps recent questions, picks up stated facts
    m.remember("I prefer short answers"); m.forget("short answers")
    m.prompt_section()             # the "What you know about this user" block for the system prompt

Facts come from explicit statements only ("remember that ...", "my name is ...", "I prefer ...",
"I am a ..."); nothing is inferred from file contents or screen content. Settings.learning turns
observation off; /memory lists, /forget removes.
"""
import json
import os
import re
import time
from collections import Counter
from typing import Dict, List, Optional

from . import settings as S

RECENT_MAX = 40
FACTS_MAX = 200
PROMPT_FACTS = 24
PROMPT_RECENT = 6

# A statement about the user, worth keeping as a fact (the whole sentence after the cue).
_CUES = [
    re.compile(r"^\s*(?:please\s+)?remember(?:\s+that)?[:,]?\s+(?P<fact>.+)$", re.I),
    re.compile(r"^\s*(?:note|keep in mind)(?:\s+that)?[:,]?\s+(?P<fact>.+)$", re.I),
    re.compile(r"(?P<fact>\bmy name is\b.+)$", re.I),
    re.compile(r"(?P<fact>\bcall me\b.+)$", re.I),
    re.compile(r"(?P<fact>\bi(?:'m| am)\s+(?:a|an|the)\s+.+)$", re.I),
    re.compile(r"(?P<fact>\bi (?:prefer|like|hate|dislike|usually|always|never|work on|work at|use)\b.+)$", re.I),
]


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M")


class Memory:
    def __init__(self, path: Optional[str] = None, enabled: bool = True):
        self.path = path or os.path.join(S.state_dir(), "memory.json")
        self.enabled = enabled
        self._facts: List[dict] = []
        self._recent: List[dict] = []
        self._tools: Counter = Counter()
        self._hours: Counter = Counter()
        self._load()

    # -- persistence ---------------------------------------------------------------
    def _load(self) -> None:
        try:
            with open(self.path, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            return
        self._facts = [x for x in d.get("facts", []) if isinstance(x, dict) and x.get("text")]
        self._recent = [x for x in d.get("recent", []) if isinstance(x, dict) and x.get("q")]
        self._tools = Counter({k: int(v) for k, v in (d.get("tools") or {}).items()})
        self._hours = Counter({k: int(v) for k, v in (d.get("hours") or {}).items()})

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"facts": self._facts[-FACTS_MAX:], "recent": self._recent[:RECENT_MAX],
                       "tools": dict(self._tools), "hours": dict(self._hours)}, f, indent=1)
        os.replace(tmp, self.path)

    # -- facts ---------------------------------------------------------------------
    def facts(self) -> List[dict]:
        return list(self._facts)

    def remember(self, text: str) -> dict:
        text = " ".join(text.split()).strip().rstrip(".")
        for f in self._facts:
            if f["text"].lower() == text.lower():
                f["ts"] = _now()
                self._save()
                return f
        fact = {"text": text, "ts": _now()}
        self._facts.append(fact)
        self._facts = self._facts[-FACTS_MAX:]
        self._save()
        return fact

    def forget(self, pattern: str) -> int:
        pat = pattern.lower().strip()
        before = len(self._facts)
        self._facts = [f for f in self._facts if pat not in f["text"].lower()] if pat != "*" else []
        self._save()
        return before - len(self._facts)

    @staticmethod
    def stated_fact(question: str) -> Optional[str]:
        """The fact a question states about the user, or None."""
        q = " ".join(question.split())
        for cue in _CUES:
            m = cue.search(q)
            if m:
                fact = m.group("fact").strip().rstrip(".?!")
                if 3 <= len(fact) <= 240:
                    return fact
        return None

    # -- observation ---------------------------------------------------------------
    def observe(self, question: str, actions: List[dict]) -> Optional[str]:
        """Record one ask. Returns the fact picked up from the question, if any."""
        if not self.enabled or not question.strip():
            return None
        fact = self.stated_fact(question)
        if fact:
            self.remember(fact)
        self._recent.insert(0, {"q": question.strip()[:200], "ts": _now(),
                                "tools": sorted({a.get("name", "") for a in actions if a.get("name")})})
        self._recent = self._recent[:RECENT_MAX]
        for a in actions:
            if a.get("name"):
                self._tools[a["name"]] += 1
        self._hours[time.strftime("%H")] += 1
        self._save()
        return fact

    def recent(self) -> List[dict]:
        return list(self._recent)

    def tool_counts(self) -> Dict[str, int]:
        return dict(self._tools)

    # -- for the system prompt -----------------------------------------------------
    def prompt_section(self) -> str:
        if not (self._facts or self._recent or self._tools):
            return ""
        lines: List[str] = []
        if self._facts:
            lines.append("What the user has told you about themselves (use it, do not repeat it back unasked):")
            lines += [f"- {f['text']}" for f in self._facts[-PROMPT_FACTS:]]
        if self._tools:
            top = ", ".join(f"{k} x{v}" for k, v in self._tools.most_common(6))
            lines.append(f"Tools this user relies on most: {top}.")
        if self._hours:
            busy = ", ".join(f"{h}:00" for h, _ in sorted(self._hours.most_common(3)))
            lines.append(f"Usually active around {busy}.")
        if self._recent:
            lines.append("Recent questions (for continuity):")
            lines += [f"- {r['ts']} {r['q']}" for r in self._recent[:PROMPT_RECENT]]
        return "\n".join(lines)

    def summary(self) -> dict:
        return {"facts": len(self._facts), "recent": len(self._recent), "tools": dict(self._tools.most_common(6)),
                "path": self.path, "enabled": self.enabled}
