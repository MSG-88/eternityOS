"""eternity-theme: one set of tokens for the whole system.

The Nocturne tokens (`theme.toml`), the layout (`layout.toml`) and the key map (`keys.toml`)
ship in /usr/share/eternity and are overlaid by the user's files in ~/.config/eternity. From
the merged configuration this module renders, into ~/.config/eternity/generated/:

    hyprland.conf   the compositor: monitors (scale), borders, gaps, rounding, blur rules,
                    animations, binds, exec-once (daemon, shell, idle)
    Theme.qml       a QML singleton (reference) and theme.json, which the shell's Theme singleton reads
    gtk.css         @define-color tokens for ordinary GTK apps

    cfg = load()                 # merged dict: {"theme": {...}, "layout": {...}, "keys": {...}, "_errors": [...]}
    validate(cfg) -> [errors]    # [] when fine
    render(out_dir) -> [paths]   # writes the three files, raises ValueError on invalid config

CLI: `eternity-theme render [--check]` (exit 1 on errors; --check validates only).
Standard library only (tomllib, string.Template).
"""
import os
import re
import string
import sys
import tomllib
from typing import Dict, List, Optional

SHARE = os.environ.get("ETERNITY_SHARE", "/usr/share/eternity")
FILES = {"theme": "theme.toml", "layout": "layout.toml", "keys": "keys.toml"}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
COLOR_KEYS = ("bg", "surface", "text", "accent", "accent_100", "accent_200", "accent_300", "accent_400", "accent_600",
              "accent_700", "accent_800", "accent_900", "n400", "n500", "n600", "n700", "n800", "n900")


def _user_dir() -> str:
    from . import settings as S
    return S.config_dir()


def _read_toml(path: str, errors: List[str]) -> dict:
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}
    except (tomllib.TOMLDecodeError, OSError) as e:
        errors.append(f"{path}: {e}")
        return {}


def _merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load(user_dir: Optional[str] = None) -> Dict[str, dict]:
    """Shipped defaults overlaid by the user's files; parse errors are collected, never fatal."""
    user_dir = user_dir or _user_dir()
    errors: List[str] = []
    cfg: Dict[str, object] = {}
    for key, name in FILES.items():
        base = _read_toml(os.path.join(SHARE, name), errors)
        over = _read_toml(os.path.join(user_dir, name), errors)
        cfg[key] = _merge(base, over)
    cfg["_errors"] = errors
    return cfg  # type: ignore[return-value]


def validate(cfg: dict) -> List[str]:
    errors: List[str] = []
    colors = (cfg.get("theme") or {}).get("color") or {}
    for k, v in colors.items():
        if not isinstance(v, str) or not HEX.match(v):
            errors.append(f"theme.color.{k}: not a #rrggbb colour: {v!r}")
    layout = cfg.get("layout") or {}
    for key in ("scale", "external_scale"):
        scale = layout.get(key)
        if scale is not None and not (isinstance(scale, (int, float)) and 1.0 <= float(scale) <= 3.0):
            errors.append(f"layout.{key}: must be between 1.0 and 3.0: {scale!r}")
    for k in ("gaps", "border", "rounding", "strip_height"):
        v = layout.get(k)
        if v is not None and not (isinstance(v, int) and 0 <= v <= 200):
            errors.append(f"layout.{k}: must be an integer 0..200: {v!r}")
    bar = layout.get("bar")
    if bar is not None and not (isinstance(bar, list) and len(bar) == 4 and all(isinstance(x, (int, float)) for x in bar)):
        errors.append(f"layout.bar: must be [x, y, w, h]: {bar!r}")
    motion = (cfg.get("theme") or {}).get("motion") or {}
    for k in ("enter_ms", "draw_ms", "pop_ms", "sweep_ms"):
        v = motion.get(k)
        if v is not None and not (isinstance(v, int) and 0 <= v <= 5000):
            errors.append(f"theme.motion.{k}: must be 0..5000 ms: {v!r}")
    return errors


def _fmt_scale(scale: float) -> str:
    return str(int(scale)) if float(scale).is_integer() else f"{scale:g}"


def _hypr(cfg: dict) -> str:
    th, lay, keys = cfg["theme"], cfg["layout"], cfg["keys"]
    c, motion = th["color"], th.get("motion", {})
    binds = []
    for name, combo in (keys.get("bind") or {}).items():
        action = (keys.get("action") or {}).get(name)
        if action:
            binds.append(f"bind = {combo}, exec, {action}")
    for name, combo in (keys.get("bindr") or {}).items():
        action = (keys.get("action") or {}).get(name)
        if action:
            binds.append(f"bindr = {combo}, exec, {action}")
    for name, combo in (keys.get("dispatch") or {}).items():
        binds.append(f"bind = {combo}, {name.replace('__', ' ').replace('_', ' ', 0)}")
    for i in range(1, 10):
        binds.append(f"bind = SUPER, {i}, workspace, {i}")
        binds.append(f"bind = SUPER SHIFT, {i}, movetoworkspace, {i}")
    for d, key in (("l", "right"), ("h", "left"), ("k", "up"), ("j", "down")):
        binds.append(f"bind = SUPER, {key}, movefocus, {d}")
        binds.append(f"bind = SUPER SHIFT, {key}, movewindow, {d}")
    layer_rules = "\n".join(f"layerrule = blur, {ns}\nlayerrule = ignorezero, {ns}" for ns in lay.get("blur_namespaces", []))
    execs = "\n".join(f"exec-once = {x}" for x in lay.get("exec_once", ["eternity-supervise eternity-daemon", "eternity-supervise quickshell -c eternity", "hypridle -c /usr/share/eternity/hypridle.conf", "/usr/libexec/polkit-mate-authentication-agent-1", "eternity-firstrun --autostart"]))
    tpl = string.Template(open(os.path.join(SHARE, "hyprland.base.conf"), encoding="utf-8").read())
    return tpl.substitute(
        scale=_fmt_scale(float(lay.get("scale", 1.25))), panel=str(lay.get("panel", "eDP-1")), external_scale=_fmt_scale(float(lay.get("external_scale", 1.0))),
        accent=c["accent"][1:], n800=c["n800"][1:], bg=c["bg"][1:],
        gaps_in=int(lay.get("gaps", 12)) // 2, gaps_out=int(lay.get("gaps", 12)),
        border=int(lay.get("border", 1)), rounding=int(lay.get("rounding", 8)),
        animations="false" if motion.get("reduced") else "true",
        enter_s=f"{int(motion.get('enter_ms', 700)) / 100:.1f}", sweep_s=f"{int(motion.get('sweep_ms', 800)) / 100:.1f}",
        layer_rules=layer_rules, execs=execs, binds="\n".join(binds),
    )


def _qml(cfg: dict) -> str:
    th, lay = cfg["theme"], cfg["layout"]
    c, f, r, m = th["color"], th.get("font", {}), th.get("radius", {}), th.get("motion", {})
    lines = ["pragma Singleton", "import QtQuick", "", "QtObject {",
             "    // generated by eternity-theme from theme.toml / layout.toml; do not edit"]
    for k in COLOR_KEYS:
        if k in c:
            lines.append(f'    readonly property color {k}: "{c[k]}"')
    lines += [f'    readonly property string body: "{f.get("body", "Inter")}"',
              f'    readonly property string tech: "{f.get("tech", "Michroma")}"',
              f'    readonly property string mono: "{f.get("mono", "JetBrains Mono")}"',
              f"    readonly property int radiusSm: {int(r.get('sm', 4))}",
              f"    readonly property int radiusMd: {int(r.get('md', 8))}",
              f"    readonly property int radiusLg: {int(r.get('lg', 14))}",
              f"    readonly property int enterMs: {int(m.get('enter_ms', 700))}",
              f"    readonly property int drawMs: {int(m.get('draw_ms', 800))}",
              f"    readonly property int popMs: {int(m.get('pop_ms', 600))}",
              f"    readonly property int sweepMs: {int(m.get('sweep_ms', 800))}",
              f"    readonly property int decodeCps: {int(m.get('decode_cps', 28))}",
              f"    readonly property bool reduced: {'true' if m.get('reduced') else 'false'}",
              f"    readonly property real glow: {float(m.get('glow', 1.0)):.1f}",
              f"    readonly property real scale: {float(lay.get('scale', 1.25)):g}",
              f"    readonly property int stripHeight: {int(lay.get('strip_height', 44))}",
              f"    readonly property var bar: [{', '.join(str(x) for x in lay.get('bar', [560, 950, 800, 54]))}]",
              f"    readonly property var orbit: [{', '.join(str(x) for x in lay.get('orbit', [440, 270]))}]",
              f"    readonly property var cards: [{', '.join(chr(34) + str(x) + chr(34) for x in lay.get('cards', []))}]",
              "}", ""]
    return "\n".join(lines)


def _css(cfg: dict) -> str:
    c = cfg["theme"]["color"]
    out = ["/* generated by eternity-theme */"]
    out += [f"@define-color {k} {v};" for k, v in c.items()]
    out += ["@define-color theme_bg_color @bg;", "@define-color theme_fg_color @text;",
            "@define-color theme_selected_bg_color @accent;", "@define-color theme_selected_fg_color @bg;", ""]
    return "\n".join(out)


def render(out_dir: Optional[str] = None, cfg: Optional[dict] = None) -> List[str]:
    cfg = cfg or load()
    errors = validate(cfg)
    if errors:
        raise ValueError("; ".join(errors))
    out_dir = out_dir or os.path.join(_user_dir(), "generated")
    os.makedirs(out_dir, exist_ok=True)
    written = []
    import json
    theme_json = json.dumps({**cfg["theme"], "layout": cfg["layout"]}, indent=1)
    for name, text in (("hyprland.conf", _hypr(cfg)), ("Theme.qml", _qml(cfg)), ("gtk.css", _css(cfg)), ("theme.json", theme_json)):
        path = os.path.join(out_dir, name)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
        written.append(path)
    return written


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] != "render":
        print("usage: eternity-theme render [--check] [--out DIR]", file=sys.stderr)
        return 2
    cfg = load()
    for e in cfg["_errors"]:
        print(f"eternity-theme: ignoring {e}", file=sys.stderr)
    errors = validate(cfg)
    if errors:
        for e in errors:
            print(f"eternity-theme: {e}", file=sys.stderr)
        return 1
    if "--check" in argv:
        return 0
    out = argv[argv.index("--out") + 1] if "--out" in argv else None
    for p in render(out, cfg):
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
