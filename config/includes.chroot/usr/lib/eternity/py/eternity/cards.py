"""Data behind the home-screen cards and the status strip. Pure functions over /proc, /sys and
the user's folders, so the shell stays honest: nothing shown here is invented.
"""
import datetime as _dt
import json
import os
import subprocess
import time
from typing import Dict, List, Optional

from . import settings as S

_last_cpu = {"idle": 0, "total": 0}


def cpu_percent() -> Optional[float]:
    """CPU use since the previous call (None on the first call)."""
    try:
        with open("/proc/stat") as f:
            parts = f.readline().split()[1:]
    except OSError:
        return None
    nums = [int(x) for x in parts[:8]]
    idle = nums[3] + nums[4]
    total = sum(nums)
    d_idle, d_total = idle - _last_cpu["idle"], total - _last_cpu["total"]
    first = _last_cpu["total"] == 0
    _last_cpu.update(idle=idle, total=total)
    if first or d_total <= 0:
        return None
    return round(100.0 * (1 - d_idle / d_total), 1)


def memory() -> Dict[str, float]:
    info = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                k, v = line.split(":", 1)
                info[k] = int(v.split()[0])
    except (OSError, ValueError):
        return {"total_gb": 0, "used_gb": 0, "percent": 0}
    total, avail = info.get("MemTotal", 0), info.get("MemAvailable", 0)
    used = total - avail
    return {"total_gb": round(total / 1048576, 1), "used_gb": round(used / 1048576, 1),
            "percent": round(100 * used / total, 0) if total else 0}


def battery() -> Optional[Dict[str, object]]:
    for bat in ("BAT0", "BAT1"):
        base = f"/sys/class/power_supply/{bat}"
        if os.path.exists(os.path.join(base, "capacity")):
            try:
                with open(os.path.join(base, "capacity")) as f:
                    cap = int(f.read().strip())
                status = "unknown"
                if os.path.exists(os.path.join(base, "status")):
                    with open(os.path.join(base, "status")) as f:
                        status = f.read().strip().lower()
                return {"percent": cap, "status": status}
            except (OSError, ValueError):
                return None
    return None


def network() -> str:
    """Connected / wifi name when known, from NetworkManager; 'offline' otherwise."""
    try:
        r = subprocess.run(["nmcli", "-t", "-f", "TYPE,STATE,CONNECTION", "device"], capture_output=True, text=True, timeout=2)
        for line in r.stdout.splitlines():
            typ, state, conn = (line.split(":") + ["", "", ""])[:3]
            if state == "connected":
                return f"{'Wi-Fi' if typ == 'wifi' else typ} · {conn}" if conn else typ
        return "offline"
    except (OSError, subprocess.TimeoutExpired):
        return ""


def uptime_text() -> str:
    try:
        with open("/proc/uptime") as f:
            s = float(f.read().split()[0])
    except (OSError, ValueError):
        return ""
    h, m = int(s // 3600), int(s % 3600 // 60)
    return f"{h} h {m} min" if h else f"{m} min"


def today() -> Dict[str, str]:
    now = _dt.datetime.now()
    hour = now.hour
    part = "morning" if 5 <= hour < 12 else "afternoon" if 12 <= hour < 18 else "evening" if 18 <= hour < 23 else "night"
    return {"time": now.strftime("%H:%M"), "date": now.strftime("%A, %d %B"), "part": part, "uptime": uptime_text()}


def recent_files(n: int = 4, roots: Optional[List[str]] = None) -> List[Dict[str, str]]:
    roots = roots or [os.path.expanduser(p) for p in ("~/Documents", "~/Desktop", "~/Downloads", "~/Pictures")]
    found = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")][:30]
            for fn in filenames:
                if fn.startswith("."):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    found.append((os.stat(p).st_mtime, p))
                except OSError:
                    pass
            if len(found) > 2000:
                break
    found.sort(reverse=True)
    out = []
    for t, p in found[:n]:
        age = time.time() - t
        when = "just now" if age < 120 else f"{int(age // 60)} min ago" if age < 7200 else f"{int(age // 3600)} h ago" if age < 172800 else _dt.datetime.fromtimestamp(t).strftime("%d %b")
        out.append({"name": os.path.basename(p), "path": p, "when": when})
    return out


def metrics_path() -> str:
    return os.path.join(S.state_dir(), "last-metrics.json")


def remember_metrics(m) -> None:
    """Called by the command bar after each answer so the home card can show the readout."""
    try:
        os.makedirs(S.state_dir(), exist_ok=True)
        with open(metrics_path(), "w", encoding="utf-8") as f:
            json.dump({"first_token_ms": m.first_token_ms, "tokens_per_s": m.tokens_per_s, "provider": m.provider,
                       "on_device": m.on_device, "ts": time.time()}, f)
    except (OSError, AttributeError):
        pass


def ai_status(cfg: Optional[S.Settings] = None) -> Dict[str, object]:
    from . import providers as P
    cfg = cfg or S.load()
    prov = cfg.effective_provider()
    out = {"provider": prov, "label": P.PROVIDER_LABELS[prov], "warm": False, "model": "", "readout": ""}
    if prov == "local":
        lp = P.LocalProvider(cfg.local_model)
        out["warm"] = lp.healthy(timeout=0.3)
        mp = lp.model_path()
        out["model"] = os.path.basename(os.path.realpath(mp)).replace(".gguf", "") if os.path.exists(mp) else "no model"
    else:
        out["model"] = cfg.anthropic_model if prov == "anthropic" else cfg.openai_model
    try:
        with open(metrics_path(), encoding="utf-8") as f:
            m = json.load(f)
        if time.time() - m.get("ts", 0) < 86400:
            bits = []
            if m.get("first_token_ms") is not None:
                bits.append(f"first token {m['first_token_ms']} ms")
            if m.get("tokens_per_s"):
                bits.append(f"~{m['tokens_per_s']:.0f} tok/s")
            out["readout"] = "  ·  ".join(bits)
    except (OSError, ValueError):
        pass
    return out


def actions_today() -> int:
    from . import actions as A
    n = 0
    today_s = _dt.date.today().isoformat()
    for e in A.Audit().tail(500):
        if str(e.get("ts", "")).startswith(today_s) and e.get("decision") in ("approved", "auto (read-only, trusted)"):
            n += 1
    return n


def live_session() -> bool:
    return os.path.exists("/run/live/medium")
