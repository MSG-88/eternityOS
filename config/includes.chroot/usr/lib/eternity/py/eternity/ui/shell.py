"""The presence is the desktop (design scene 04). eternity-shell is a full-screen,
undecorated, kept-below window painted with the Nocturne vignette: the Möbius mark breathes
at the centre inside the concentric rings, four cards orbit it (today, system, Eternity,
recent files; plus "Install Eternity 08" in live sessions), a status strip sits at the top
and the command-bar hint at the bottom. Clicking the mark opens the launcher; the hint opens
Ask Eternity. Everything shown comes from eternity.cards (real data).
"""
import math
import os
import subprocess
import sys
import time

import cairo
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from .. import cards as C
from .. import settings as S
from . import button, label, load_css, shot

# Nocturne colours as floats
BG_TOP, BG_EDGE = (0x1b / 255, 0x1e / 255, 0x31 / 255), (0x12 / 255, 0x14 / 255, 0x21 / 255)
A100, A600 = (0xf5 / 255, 0xf4 / 255, 0xff / 255), (0x79 / 255, 0x6c / 255, 0xbf / 255)
ACCENT, N400 = (0x91 / 255, 0x84 / 255, 0xd9 / 255), (0xb2 / 255, 0xb6 / 255, 0xca / 255)
MOB_N = 150


def _mob(t):
    d = 1 + math.sin(t) ** 2
    return 62 * math.sin(t) * math.cos(t) / d, 46 * math.cos(t) / d


MOB = [(i / MOB_N * 2 * math.pi,) + _mob(i / MOB_N * 2 * math.pi) for i in range(MOB_N + 1)]


def draw_mark(cr: cairo.Context, cx: float, cy: float, size: float, phase: float, light_t: float, glow: float = 1.0):
    """The 3b mark drawn live with cairo (same geometry as branding/render.py)."""
    s = size / 140.0
    cr.save()
    cr.translate(cx, cy)
    cr.scale(s, s)
    # glow halo
    if glow > 0:
        rg = cairo.RadialGradient(0, 0, 10, 0, 0, 80)
        rg.add_color_stop_rgba(0, *ACCENT, 0.28 * glow)
        rg.add_color_stop_rgba(1, *ACCENT, 0.0)
        cr.set_source(rg)
        cr.arc(0, 0, 80, 0, 2 * math.pi)
        cr.fill()
    # fading ring
    lg = cairo.LinearGradient(0, -64, 0, 64)
    lg.add_color_stop_rgba(0.0, *N400, 0.0)
    lg.add_color_stop_rgba(0.3, *N400, 1.0)
    lg.add_color_stop_rgba(0.7, *N400, 1.0)
    lg.add_color_stop_rgba(1.0, *N400, 0.0)
    cr.set_source(lg)
    cr.set_line_width(2.2)
    cr.arc(0, 0, 64, 0, 2 * math.pi)
    cr.stroke()
    # Möbius ribbon
    for i in range(MOB_N):
        t0, x0, y0 = MOB[i]
        t1, x1, y1 = MOB[i + 1]
        nx, ny = -(y1 - y0), x1 - x0
        nl = math.hypot(nx, ny) or 1
        w0 = 7.5 * abs(math.cos(t0)) ** 0.75
        w1 = 7.5 * abs(math.cos(t1)) ** 0.75
        sh = 0.5 + 0.5 * math.sin(t0 * 2 + phase)
        lit = 0.5 + 0.5 * math.cos(t0 + phase * 0.7)
        p = (45 + 55 * (0.55 * sh + 0.45 * lit)) / 100
        r, g, b = (A100[k] * p + A600[k] * (1 - p) for k in range(3))
        cr.set_source_rgb(r, g, b)
        cr.move_to(x0 + nx / nl * w0, y0 + ny / nl * w0)
        cr.line_to(x1 + nx / nl * w1, y1 + ny / nl * w1)
        cr.line_to(x1 - nx / nl * w1, y1 - ny / nl * w1)
        cr.line_to(x0 - nx / nl * w0, y0 - ny / nl * w0)
        cr.close_path()
        cr.fill_preserve()
        cr.set_line_width(0.6)
        cr.stroke()
    # light point
    k = MOB[int(light_t % 1 * MOB_N)]
    cr.set_source_rgba(*A100, 0.95)
    cr.arc(k[1], k[2], 2.2, 0, 2 * math.pi)
    cr.fill()
    cr.restore()


def draw_rings(cr: cairo.Context, cx: float, cy: float, unit: float, t: float):
    for i, r in enumerate((92, 134, 176, 214)):
        rr = r * unit
        a = 0.30 - 0.06 * i
        cr.set_source_rgba(*N400, a * (0.85 + 0.15 * math.sin(t * 0.6 + i)))
        cr.set_line_width(max(1.0, 1.2 * unit))
        cr.arc(cx, cy, rr, 0, 2 * math.pi)
        cr.stroke()
    rr = 214 * unit
    cr.set_line_width(max(1.0, unit))
    for k in range(60):
        ang = k / 60 * 2 * math.pi + t * 0.02
        ln = unit * (6 if k % 5 == 0 else 3)
        cr.set_source_rgba(*N400, 0.22)
        cr.move_to(cx + math.cos(ang) * rr, cy + math.sin(ang) * rr)
        cr.line_to(cx + math.cos(ang) * (rr + ln), cy + math.sin(ang) * (rr + ln))
        cr.stroke()


class Card(Gtk.Box):
    def __init__(self, kicker: str, on_click=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.get_style_context().add_class("orbit-card")
        self.set_size_request(240, -1)
        self.kicker = label(kicker, "kicker")
        self.pack_start(self.kicker, False, False, 0)
        self.value = label("", "value", wrap=True)
        self.pack_start(self.value, False, False, 0)
        self.meta = label("", "muted", wrap=True)
        self.pack_start(self.meta, False, False, 0)
        self.extra = label("", "faint", wrap=True)
        self.pack_start(self.extra, False, False, 0)

    def set(self, value: str, meta: str = "", extra: str = ""):
        self.value.set_text(value)
        self.meta.set_text(meta)
        self.extra.set_text(extra)
        self.meta.set_visible(bool(meta))
        self.extra.set_visible(bool(extra))


class Shell(Gtk.Window):
    def __init__(self, cfg: S.Settings):
        super().__init__(title="Eternity")
        self.cfg = cfg
        self.get_style_context().add_class("eternity-window")
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_below(True)
        self.stick()
        self.set_accept_focus(False)
        self.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        self.set_app_paintable(True)
        self.connect("destroy", Gtk.main_quit)
        self.connect("draw", self.on_draw)
        self.t0 = time.monotonic()
        self.frame_ms = []

        screen = Gdk.Screen.get_default()
        self.w, self.h = screen.get_width(), screen.get_height()
        self.set_default_size(self.w, self.h)
        self.move(0, 0)

        self.fixed = Gtk.Fixed()
        self.add(self.fixed)
        self.unit = self.h / 1080
        self.cx, self.cy = self.w / 2, self.h * 0.46

        # status strip
        self.strip = Gtk.Box(spacing=18)
        self.strip.get_style_context().add_class("status-strip")
        self.s_word = label("ETERNITY", "wordmark")
        self.strip.pack_start(self.s_word, False, False, 0)
        self.s_clock = label("", "muted")
        self.strip.pack_start(self.s_clock, False, False, 0)
        self.s_live = label("● live", "muted")
        self.strip.pack_start(self.s_live, False, False, 0)
        self.s_cpu = label("", "muted")
        self.strip.pack_start(self.s_cpu, False, False, 0)
        self.s_net = label("", "muted")
        self.strip.pack_start(self.s_net, False, False, 0)
        self.s_bat = label("", "muted")
        self.strip.pack_start(self.s_bat, False, False, 0)
        self.fixed.put(self.strip, int(self.w / 2 - 330), int(14 * self.unit))

        # orbit cards
        self.c_today = Card("TODAY")
        self.c_system = Card("SYSTEM")
        self.c_ai = Card("ETERNITY")
        self.c_recent = Card("RECENT")
        r = 300 * self.unit
        places = {self.c_today: (-r - 150, -140), self.c_system: (r - 90, -140),
                  self.c_recent: (-r - 150, 110), self.c_ai: (r - 90, 110)}
        for card, (dx, dy) in places.items():
            self.fixed.put(card, int(self.cx + dx), int(self.cy + dy))
        if C.live_session():
            self.c_install = Card("LIVE SESSION")
            self.c_install.set("Try, then install", "Everything you do now stays in memory.", "")
            inst = button("Install Eternity 08", "primary", on_click=lambda: subprocess.Popen(["eternity-install"]))
            self.c_install.pack_start(inst, False, False, 4)
            self.fixed.put(self.c_install, int(self.cx - 120), int(self.cy + 300 * self.unit))

        # command hint
        self.hint = button("Ask Eternity, or type a command        Super + Space", "ghost",
                           on_click=lambda: subprocess.Popen(["eternity-ask"]))
        self.hint.get_style_context().add_class("status-strip")
        self.fixed.put(self.hint, int(self.w / 2 - 260), int(self.h - 70 * self.unit))

        # the mark is clickable: an invisible event box over it opens the launcher
        ev = Gtk.EventBox()
        ev.set_visible_window(False)
        ev.set_size_request(int(176 * self.unit), int(176 * self.unit))
        ev.connect("button-press-event", lambda *_: subprocess.Popen(["eternity-launcher"]) and True)
        self.fixed.put(ev, int(self.cx - 88 * self.unit), int(self.cy - 88 * self.unit))

        self.refresh_cards()
        GLib.timeout_add(2000, self.refresh_cards)
        GLib.timeout_add(1000 // 30, self.tick)

    # ------------------------------------------------------------------- drawing
    def tick(self):
        t = time.monotonic()
        self.queue_draw()
        self.frame_ms.append((time.monotonic() - t) * 1000)
        if len(self.frame_ms) > 60:
            self.frame_ms.pop(0)
        return True

    def on_draw(self, _w, cr: cairo.Context):
        t = time.monotonic() - self.t0
        # vignette
        rg = cairo.RadialGradient(self.w / 2, -self.h * 0.1, 10, self.w / 2, -self.h * 0.1, max(self.w, self.h) * 1.1)
        rg.add_color_stop_rgb(0, *BG_TOP)
        rg.add_color_stop_rgb(1, *BG_EDGE)
        cr.set_source(rg)
        cr.paint()
        draw_rings(cr, self.cx, self.cy, self.unit, t)
        breathe = 1 + 0.015 * math.sin(t * 1.1)
        draw_mark(cr, self.cx, self.cy, 176 * self.unit * breathe, t * 1.4, (t * 0.22) % 1, glow=1.0 + 0.3 * math.sin(t * 0.9))
        return False

    # ------------------------------------------------------------------- data
    def refresh_cards(self):
        td = C.today()
        greet = f"Good {td['part']}" + (f", {self.cfg.name}" if self.cfg.name else "")
        self.c_today.set(td["time"], td["date"], f"{greet}.  Up {td['uptime']}." if td["uptime"] else greet + ".")
        cpu = C.cpu_percent()
        mem = C.memory()
        bat = C.battery()
        sys_line = f"{mem['used_gb']} of {mem['total_gb']} GB memory"
        self.c_system.set(f"CPU {cpu:.0f}%" if cpu is not None else "CPU …", sys_line,
                          (f"Battery {bat['percent']}% · {bat['status']}" if bat else "Mains power"))
        ai = C.ai_status(self.cfg)
        self.c_ai.set(ai["label"], ai["model"] + ("  ·  warm" if ai["warm"] else ""),
                      (ai["readout"] + "  ·  " if ai["readout"] else "") + f"{C.actions_today()} actions confirmed today")
        rec = C.recent_files(3)
        self.c_recent.set(rec[0]["name"] if rec else "Nothing yet", (rec[0]["when"] if rec else "Files you change show up here"),
                          "\n".join(f"{f['name']}  ·  {f['when']}" for f in rec[1:]))
        self.s_clock.set_text(td["time"])
        lat = sum(self.frame_ms) / len(self.frame_ms) if self.frame_ms else 0
        self.s_live.set_text(f"● live · {lat:.1f} ms" if lat else "● live")
        try:
            os.makedirs(S.state_dir(), exist_ok=True)
            with open(os.path.join(S.state_dir(), "frame-ms"), "w") as f:
                f.write(f"{lat:.2f} {time.time():.0f}
")
        except OSError:
            pass
        self.s_cpu.set_text(f"CPU {cpu:.0f}%" if cpu is not None else "")
        net = C.network()
        self.s_net.set_text(net)
        self.s_bat.set_text(f"⚡ {bat['percent']}%" if bat else "")
        self.show_all()
        return True


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    load_css()
    cfg = S.load()
    win = Shell(cfg)
    win.show_all()
    if os.environ.get("ETERNITY_UI_SMOKE"):
        for _ in range(5):
            win.tick()
            win.refresh_cards()
            while Gtk.events_pending():
                Gtk.main_iteration()
        shot(win, "shell-home")
        return 0
    Gtk.main()
    return 0
