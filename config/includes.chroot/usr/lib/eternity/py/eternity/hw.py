"""Hardware inventory and health for Eternity 08: which devices this machine has, which
driver (if any) the kernel bound to each, which firmware files failed to load, and whether
the stacks above them (NetworkManager, BlueZ, PipeWire, power-profiles-daemon) are running.

    inv = inventory()          # dict, JSON-serialisable
    text = report(inv)         # readable report, one line per device/subsystem
    problems(inv)              # [(severity, message)] with severity "bad" | "warn"

Used by `eternity-hw` (CLI), the assistant tool `hardware_report`, Settings > Eternity >
Devices and the in-image self-test (`check_hardware`). Standard library only; every probe
tolerates a missing tool or a locked-down kernel (dmesg_restrict) and says so instead of
failing. Nothing here needs root.
"""
import glob
import json
import os
import re
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple

SYS = os.environ.get("ETERNITY_SYSFS", "/sys")
PROC = os.environ.get("ETERNITY_PROCFS", "/proc")

# PCI classes (first two hex digits of the class code) whose devices must have a driver
NEEDS_DRIVER = {"02": "network", "03": "display", "04": "multimedia", "0c": "serial bus", "01": "storage"}


def _run(cmd: List[str], timeout: float = 10.0) -> Tuple[int, str]:
    if not shutil.which(cmd[0]):
        return 127, ""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return r.returncode, r.stdout + (r.stderr if r.returncode else "")
    except (subprocess.TimeoutExpired, OSError):
        return 1, ""


def _read(path: str, default: str = "") -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return default


def _link_base(path: str) -> str:
    try:
        return os.path.basename(os.readlink(path))
    except OSError:
        return ""


# ----------------------------------------------------------------------------- PCI
def parse_lspci_k(text: str) -> List[Dict[str, str]]:
    """Blocks of `lspci -k` -> [{slot, description, driver, modules}]."""
    devices: List[Dict[str, str]] = []
    cur: Optional[Dict[str, str]] = None
    for line in text.splitlines():
        if not line.strip():
            continue
        if not line[0].isspace():
            slot, _, desc = line.partition(" ")
            cur = {"slot": slot, "description": desc.strip(), "driver": "", "modules": ""}
            devices.append(cur)
        elif cur is not None:
            key, _, val = line.strip().partition(":")
            if key == "Kernel driver in use":
                cur["driver"] = val.strip()
            elif key == "Kernel modules":
                cur["modules"] = val.strip()
    return devices


def pci() -> List[Dict[str, str]]:
    """PCI devices from sysfs (always available) enriched with lspci names when present."""
    names: Dict[str, Dict[str, str]] = {}
    rc, out = _run(["lspci", "-k"])
    if rc == 0:
        for d in parse_lspci_k(out):
            names[d["slot"]] = d
    devices = []
    for dev in sorted(glob.glob(f"{SYS}/bus/pci/devices/*")):
        slot_full = os.path.basename(dev)                 # 0000:03:00.0
        slot = slot_full.split(":", 1)[1] if slot_full.count(":") == 2 else slot_full
        cls = _read(f"{dev}/class")[2:4] if _read(f"{dev}/class").startswith("0x") else ""
        info = names.get(slot, {})
        devices.append({
            "slot": slot,
            "class": cls,
            "kind": NEEDS_DRIVER.get(cls, ""),
            "vendor": _read(f"{dev}/vendor"), "device": _read(f"{dev}/device"),
            "description": info.get("description") or f"PCI device {_read(f'{dev}/vendor')}:{_read(f'{dev}/device')}",
            "driver": _link_base(f"{dev}/driver") or info.get("driver", ""),
            "modules": info.get("modules", ""),
        })
    return devices


# ----------------------------------------------------------------------------- USB
def usb() -> List[Dict[str, object]]:
    devices = []
    for dev in sorted(glob.glob(f"{SYS}/bus/usb/devices/*")):
        base = os.path.basename(dev)
        if ":" in base or base.startswith("usb"):     # interfaces and root hubs
            continue
        vid, pid = _read(f"{dev}/idVendor"), _read(f"{dev}/idProduct")
        if not vid:
            continue
        name = " ".join(x for x in (_read(f"{dev}/manufacturer"), _read(f"{dev}/product")) if x) or f"USB {vid}:{pid}"
        drivers = sorted({_link_base(f"{iface}/driver") for iface in glob.glob(f"{dev}/{base}:*")} - {""})
        if _read(f"{dev}/bDeviceClass") == "09":      # hubs are not interesting
            continue
        devices.append({"id": f"{vid}:{pid}", "name": name, "drivers": drivers})
    return devices


# ----------------------------------------------------------------------------- firmware
FW_PATTERNS = (re.compile(r"Direct firmware load for (\S+) failed"),
               re.compile(r"firmware: failed to load (\S+)"),
               re.compile(r"failed to load firmware (\S+)", re.I))


def firmware_failures() -> Dict[str, object]:
    """Firmware files the kernel asked for and could not find (from the kernel log)."""
    rc, out = _run(["journalctl", "-k", "-b", "--no-pager", "-o", "cat"], timeout=20)
    source = "journal"
    if rc != 0 or not out:
        rc, out = _run(["dmesg"])
        source = "dmesg"
    if rc != 0:
        return {"readable": False, "missing": [], "source": ""}
    missing = []
    for line in out.splitlines():
        for pat in FW_PATTERNS:
            m = pat.search(line)
            if m and m.group(1) not in missing:
                missing.append(m.group(1))
    return {"readable": True, "missing": missing, "source": source}


# ----------------------------------------------------------------------------- subsystems
def _unit_active(unit: str, user: bool = False) -> Optional[bool]:
    cmd = ["systemctl"] + (["--user"] if user else []) + ["is-active", unit]
    rc, out = _run(cmd, timeout=5)
    if rc == 127:
        return None
    return out.strip() == "active"


def network() -> Dict[str, object]:
    devs = []
    rc, out = _run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "dev"])
    if rc == 0:
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[1] not in ("loopback",):
                devs.append({"device": parts[0], "type": parts[1], "state": parts[2], "connection": ":".join(parts[3:])})
    else:
        for d in sorted(glob.glob(f"{SYS}/class/net/*")):
            n = os.path.basename(d)
            if n == "lo":
                continue
            devs.append({"device": n, "type": "wifi" if os.path.isdir(f"{d}/wireless") else "ethernet",
                         "state": _read(f"{d}/operstate"), "connection": ""})
    blocked = []
    rc, out = _run(["rfkill", "-J"])
    if rc == 0:
        try:
            for r in (json.loads(out).get("rfkilldevices") or json.loads(out).get("") or []):
                if r.get("soft") == "blocked" or r.get("hard") == "blocked":
                    blocked.append(f"{r.get('type')} ({'hard' if r.get('hard') == 'blocked' else 'soft'})")
        except ValueError:
            pass
    return {"devices": devs, "manager_active": _unit_active("NetworkManager"), "rfkill_blocked": blocked}


def bluetooth() -> Dict[str, object]:
    adapters = [os.path.basename(p) for p in glob.glob(f"{SYS}/class/bluetooth/hci*")]
    return {"adapters": adapters, "service_active": _unit_active("bluetooth"),
            "stack_installed": shutil.which("bluetoothctl") is not None}


def graphics() -> Dict[str, object]:
    cards = []
    for c in sorted(glob.glob(f"{SYS}/class/drm/card[0-9]*")):
        if "-" in os.path.basename(c):
            continue
        cards.append({"card": os.path.basename(c), "driver": _link_base(f"{c}/device/driver"),
                      "vendor": _read(f"{c}/device/vendor"), "device": _read(f"{c}/device/device")})
    outputs = [os.path.basename(c) for c in glob.glob(f"{SYS}/class/drm/card*-*") if _read(f"{c}/status") == "connected"]
    return {"cards": cards, "connected_outputs": outputs, "session": os.environ.get("XDG_SESSION_TYPE", "")}


def sound() -> Dict[str, object]:
    cards = []
    for line in _read(f"{PROC}/asound/cards").splitlines():
        m = re.match(r"\s*(\d+)\s+\[(\S+)\s*\]:\s*(.*)", line)
        if m:
            cards.append({"index": int(m.group(1)), "id": m.group(2), "name": m.group(3).strip()})
    return {"cards": cards, "pipewire_active": _unit_active("pipewire", user=True),
            "wireplumber_active": _unit_active("wireplumber", user=True)}


def inputs() -> List[Dict[str, str]]:
    devices, cur = [], {}
    for line in _read(f"{PROC}/bus/input/devices").splitlines() + [""]:
        if line.startswith("N: Name="):
            cur["name"] = line.split("=", 1)[1].strip().strip('"')
        elif line.startswith("H: Handlers="):
            cur["handlers"] = line.split("=", 1)[1].strip()
        elif not line.strip() and cur:
            devices.append(cur)
            cur = {}
    return devices


def cameras() -> List[Dict[str, str]]:
    cams = []
    for v in sorted(glob.glob(f"{SYS}/class/video4linux/video*")):
        name = _read(f"{v}/name")
        if os.path.exists(f"{v}/index") and _read(f"{v}/index") not in ("0", ""):
            continue  # metadata nodes of the same camera
        cams.append({"device": "/dev/" + os.path.basename(v), "name": name})
    return cams


def power() -> Dict[str, object]:
    supplies = []
    for p in sorted(glob.glob(f"{SYS}/class/power_supply/*")):
        supplies.append({"name": os.path.basename(p), "type": _read(f"{p}/type"),
                         "capacity": _read(f"{p}/capacity"), "status": _read(f"{p}/status"), "online": _read(f"{p}/online")})
    backlights = []
    for b in sorted(glob.glob(f"{SYS}/class/backlight/*")):
        backlights.append({"name": os.path.basename(b), "brightness": _read(f"{b}/brightness"), "max": _read(f"{b}/max_brightness")})
    return {"supplies": supplies, "backlights": backlights, "profiles_daemon_active": _unit_active("power-profiles-daemon"),
            "suspend_supported": "mem" in _read(f"{SYS}/power/state").split()}


def platform() -> Dict[str, object]:
    cpu = ""
    microcode = ""
    for line in _read(f"{PROC}/cpuinfo").splitlines():
        if line.startswith("model name") and not cpu:
            cpu = line.split(":", 1)[1].strip()
        elif line.startswith("microcode") and not microcode:
            microcode = line.split(":", 1)[1].strip()
    dmi = f"{SYS}/class/dmi/id"
    sb = ""
    for f in glob.glob(f"{SYS}/firmware/efi/efivars/SecureBoot-*"):
        try:
            with open(f, "rb") as fh:
                sb = "on" if fh.read()[-1:] == b"\x01" else "off"
        except OSError:
            pass
    return {"vendor": _read(f"{dmi}/sys_vendor"), "product": _read(f"{dmi}/product_name"),
            "bios": f"{_read(f'{dmi}/bios_version')} {_read(f'{dmi}/bios_date')}".strip(),
            "cpu": cpu, "microcode": microcode, "kernel": _read(f"{PROC}/sys/kernel/osrelease"),
            "efi": os.path.isdir(f"{SYS}/firmware/efi"), "secure_boot": sb,
            "tpm": bool(glob.glob(f"{SYS}/class/tpm/tpm*")),
            "memory_gb": round(int((re.search(r"MemTotal:\s+(\d+)", _read(f"{PROC}/meminfo")) or [0, "0"])[1]) / 1048576, 1),
            "virtual": bool(re.search(r"QEMU|VirtualBox|VMware|Virtual Machine|KVM", _read(f"{dmi}/product_name") + _read(f"{dmi}/sys_vendor"))),
            "fwupd_installed": shutil.which("fwupdmgr") is not None}


def inventory() -> Dict[str, object]:
    return {"platform": platform(), "pci": pci(), "usb": usb(), "firmware": firmware_failures(),
            "network": network(), "bluetooth": bluetooth(), "graphics": graphics(), "sound": sound(),
            "inputs": inputs(), "cameras": cameras(), "power": power()}


# ----------------------------------------------------------------------------- judgement
def problems(inv: Dict[str, object]) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for d in inv.get("pci", []):
        if d.get("kind") and not d.get("driver"):
            hint = f" (candidate modules: {d['modules']})" if d.get("modules") else " (no kernel module claims it)"
            out.append(("bad", f"{d['kind']} device without a driver: {d['description']}{hint}"))
    fw = inv.get("firmware", {})
    for f in fw.get("missing", []):
        out.append(("bad", f"firmware file missing: {f}"))
    if not fw.get("readable", True):
        out.append(("warn", "kernel log not readable by this user, firmware failures unknown (run eternity-hw as root for them)"))
    net = inv.get("network", {})
    if net.get("manager_active") is False:
        out.append(("bad", "NetworkManager is not running"))
    for b in net.get("rfkill_blocked", []):
        out.append(("warn", f"radio blocked by rfkill: {b}"))
    if not any(d.get("type") == "wifi" for d in net.get("devices", [])) and any(d.get("kind") == "network" and "etwork" in d.get("description", "") and ("ireless" in d["description"] or "WiFi" in d["description"] or "802.11" in d["description"]) for d in inv.get("pci", [])):
        out.append(("bad", "a wireless card is present but no wifi interface exists"))
    bt = inv.get("bluetooth", {})
    if bt.get("adapters") and bt.get("service_active") is False:
        out.append(("bad", "a Bluetooth adapter is present but bluetooth.service is not running"))
    if not bt.get("stack_installed"):
        out.append(("warn", "BlueZ (bluetoothctl) is not installed"))
    for c in inv.get("graphics", {}).get("cards", []):
        if not c.get("driver"):
            out.append(("bad", f"display {c['card']} has no kernel driver"))
    snd = inv.get("sound", {})
    if snd.get("cards") and snd.get("pipewire_active") is False:
        out.append(("warn", "sound cards present but PipeWire is not running in this session"))
    pw = inv.get("power", {})
    if any(s.get("type") == "Battery" for s in pw.get("supplies", [])) and not pw.get("backlights"):
        out.append(("warn", "laptop without a backlight device: brightness keys will not work"))
    return out


def summary(inv: Dict[str, object]) -> Dict[str, object]:
    probs = problems(inv)
    return {"devices": len(inv.get("pci", [])) + len(inv.get("usb", [])),
            "bad": sum(1 for s, _ in probs if s == "bad"), "warn": sum(1 for s, _ in probs if s == "warn"),
            "ok": not any(s == "bad" for s, _ in probs)}


def report(inv: Dict[str, object]) -> str:
    p = inv["platform"]
    lines = [f"{p.get('vendor', '')} {p.get('product', '')}".strip() or "Unknown machine",
             f"  firmware {p.get('bios') or '?'} · {'UEFI' if p.get('efi') else 'legacy BIOS boot'}"
             + (f" · Secure Boot {p['secure_boot']}" if p.get("secure_boot") else "") + (" · TPM" if p.get("tpm") else ""),
             f"  {p.get('cpu') or 'CPU ?'} · {p.get('memory_gb')} GB · kernel {p.get('kernel')}"
             + (f" · microcode {p['microcode']}" if p.get("microcode") else ""),
             "", "PCI devices"]
    for d in inv.get("pci", []):
        if not d.get("kind"):
            continue
        mark = "✓" if d.get("driver") else "✗"
        lines.append(f"  {mark} {d['description']}  [{d.get('driver') or 'no driver'}]")
    lines.append("")
    lines.append("USB devices")
    for d in inv.get("usb", []):
        mark = "✓" if d.get("drivers") else "·"
        lines.append(f"  {mark} {d['name']} ({d['id']})  [{', '.join(d['drivers']) or 'no driver'}]")
    net = inv.get("network", {})
    lines += ["", "Network: " + (", ".join(f"{d['device']} {d['type']} {d['state']}" for d in net.get("devices", [])) or "no interfaces")
              + ("" if net.get("manager_active") else " · NetworkManager not running")]
    bt = inv.get("bluetooth", {})
    lines.append("Bluetooth: " + (", ".join(bt.get("adapters", [])) or "no adapter") + (" · service running" if bt.get("service_active") else " · service not running"))
    g = inv.get("graphics", {})
    lines.append("Graphics: " + (", ".join(f"{c['card']} [{c.get('driver') or 'no driver'}]" for c in g.get("cards", [])) or "no DRM device")
                 + (f" · outputs {', '.join(g['connected_outputs'])}" if g.get("connected_outputs") else ""))
    s = inv.get("sound", {})
    lines.append("Sound: " + (", ".join(c["name"] for c in s.get("cards", [])) or "no card") + (" · PipeWire running" if s.get("pipewire_active") else ""))
    lines.append("Cameras: " + (", ".join(c["name"] for c in inv.get("cameras", [])) or "none"))
    lines.append("Input: " + (", ".join(i.get("name", "?") for i in inv.get("inputs", [])[:8]) or "none"))
    pw = inv.get("power", {})
    bat = [f"{x['name']} {x.get('capacity') or '?'}% {x.get('status') or ''}".strip() for x in pw.get("supplies", []) if x.get("type") == "Battery"]
    lines.append("Power: " + (", ".join(bat) or "no battery") + (f" · backlight {', '.join(b['name'] for b in pw['backlights'])}" if pw.get("backlights") else "")
                 + (" · power profiles" if pw.get("profiles_daemon_active") else "") + (" · suspend ok" if pw.get("suspend_supported") else ""))
    fw = inv.get("firmware", {})
    lines.append("Firmware: " + ("missing " + ", ".join(fw["missing"]) if fw.get("missing") else ("all loaded" if fw.get("readable") else "log not readable")))
    probs = problems(inv)
    lines.append("")
    if probs:
        lines.append("Problems")
        for sev, msg in probs:
            lines.append(f"  {'✗' if sev == 'bad' else '!'} {msg}")
    else:
        lines.append("No problems found.")
    return "\n".join(lines)


def save(inv: Dict[str, object], path: Optional[str] = None) -> str:
    from . import settings as S
    path = path or os.path.join(S.state_dir(), "hardware.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(inv, f, indent=1)
    return path


def main(argv: Optional[List[str]] = None) -> int:
    import sys
    argv = sys.argv[1:] if argv is None else argv
    inv = inventory()
    if "--save" in argv:
        print(save(inv))
        return 0
    if "--json" in argv:
        print(json.dumps(inv, indent=1))
    else:
        print(report(inv))
    return 0 if summary(inv)["ok"] else 1
