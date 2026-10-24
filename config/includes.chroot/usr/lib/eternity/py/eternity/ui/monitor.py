"""System monitor (design scene 08): sparklines for CPU, memory, disk, network and AI tokens/s
around a load ring, plus the real counters this machine has (threads, load average, frame
time of the shell animation when it runs). No NPU exists on this hardware, so the ring shows
CPU load and says so.
"""
import math
import os
import sys
import time
from collections import deque

import cairo
from gi.repository import GLib, Gtk  # noqa: E402

from .. import cards as C
from . import label, load_css, shot

ACCENT = (0x91 / 255, 0x84 / 255, 0xd9 / 255)
A300 = (0xd2 / 255, 0xce / 255, 0xfd / 255)
N400 = (0xb2 / 255, 0xb6 / 255, 0xca / 255)
N800 = (0x3f / 255, 0x42 / 255, 0x4d / 255)
SURFACE = (0x23 / 255, 0x25 / 255, 0x32 / 255)


def _net_bytes():
    rx = tx = 0
    try:
        with open("/proc/net/dev") as f:
            for line in f.readlines()[2:]:
                name, data = line.split(":", 1)
                if name.strip() == "lo":
                    continue
                parts = data.split()
                rx += int(parts[0]); tx += int(parts[8])
    except (OSError, ValueError, IndexError):
        pass
    return rx, tx


def _disk_bytes():
    rd = wr = 0
    try:
        with open("/proc/diskstats") as f:
            for line in f:
                p = line.split()
                if len(p) < 14 or not (p[2].startswith(("sd", "nvme", "vd", "mmcblk")) and not p[2][-1].isdigit()):
                    continue
                rd += int(p[5]) * 512; wr += int(p[9]) * 512
    except (OSError, ValueError):
        pass
    return rd, wr


class Spark(Gtk.DrawingArea):
    def __init__(self, title: str, unit: str, maximum=None, n=90):
        super().__init__()
        self.title, self.unit, self.maximum = title, unit, maximum
        self.values = deque(maxlen=n)
        self.set_size_request(300, 92)
        self.connect("draw", self.on_draw)

    def push(self, v):
        if v is not None:
            self.values.append(float(v))
        self.queue_draw()

    def on_draw(self, _w, cr: cairo.Context):
        a = self.get_allocation()
        w, h = a.width, a.height
        cr.set_source_rgba(*SURFACE, 0.9)
        self._round(cr, 0, 0, w, h, 12)
        cr.fill()
        cr.set_source_rgba(*N400, 0.9)
        cr.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(11)
        cr.move_to(14, 20)
        cr.show_text(self.title.upper())
        last = self.values[-1] if self.values else None
        cr.set_source_rgb(*A300)
        cr.set_font_size(20)
        txt = ("%.0f" % last if last is not None and last >= 10 else "%.1f" % last if last is not None else "…") + f" {self.unit}"
        ext = cr.text_extents(txt)
        cr.move_to(w - 14 - ext.x_advance, 26)
        cr.show_text(txt)
        if len(self.values) < 2:
            return False
        vmax = self.maximum or max(max(self.values), 1e-9) * 1.15
        x0, y0, x1, y1 = 14, 36, w - 14, h - 12
        cr.set_source_rgba(*N800, 0.8)
        cr.set_line_width(1)
        cr.move_to(x0, y1); cr.line_to(x1, y1); cr.stroke()
        pts = list(self.values)
        n = self.values.maxlen
        cr.set_source_rgb(*ACCENT)
        cr.set_line_width(1.6)
        for i, v in enumerate(pts):
            x = x0 + (x1 - x0) * (n - len(pts) + i) / (n - 1)
            y = y1 - (y1 - y0) * min(1.0, v / vmax)
            (cr.move_to if i == 0 else cr.line_to)(x, y)
        cr.stroke_preserve()
        cr.line_to(x1, y1)
        cr.line_to(x0 + (x1 - x0) * (n - len(pts)) / (n - 1), y1)
        cr.close_path()
        cr.set_source_rgba(*ACCENT, 0.16)
        cr.fill()
        return False

    @staticmethod
    def _round(cr, x, y, w, h, r):
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()


class LoadRing(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.value = 0.0
        self.caption = "CPU LOAD"
        self.set_size_request(220, 220)
        self.connect("draw", self.on_draw)

    def on_draw(self, _w, cr):
        a = self.get_allocation()
        cx, cy, r = a.width / 2, a.height / 2, min(a.width, a.height) / 2 - 14
        cr.set_line_width(8)
        cr.set_source_rgba(*N800, 0.9)
        cr.arc(cx, cy, r, 0, 2 * math.pi); cr.stroke()
        cr.set_source_rgb(*ACCENT)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.arc(cx, cy, r, -math.pi / 2, -math.pi / 2 + 2 * math.pi * max(0.0, min(1.0, self.value / 100)))
        cr.stroke()
        cr.set_source_rgb(*A300)
        cr.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(34)
        txt = f"{self.value:.0f}%"
        e = cr.text_extents(txt)
        cr.move_to(cx - e.x_advance / 2, cy + 10); cr.show_text(txt)
        cr.set_font_size(10)
        cr.set_source_rgba(*N400, 0.9)
        e = cr.text_extents(self.caption)
        cr.move_to(cx - e.x_advance / 2, cy + 34); cr.show_text(self.caption)
        return False


class Monitor(Gtk.Window):
    def __init__(self):
        super().__init__(title="Eternity monitor")
        self.get_style_context().add_class("eternity-window")
        self.set_default_size(1000, 640)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("destroy", Gtk.main_quit)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        for side in ("top", "bottom", "start", "end"):
            getattr(root, f"set_margin_{side}")(22)
        self.add(root)
        head = Gtk.Box(spacing=12)
        head.pack_start(label("SYSTEM", "kicker"), False, False, 0)
        self.head_line = label("", "muted")
        head.pack_end(self.head_line, False, False, 0)
        root.pack_start(head, False, False, 0)
        body = Gtk.Box(spacing=18)
        root.pack_start(body, True, True, 0)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        body.pack_start(left, True, True, 0)
        mid = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        mid.set_valign(Gtk.Align.CENTER)
        self.ring = LoadRing()
        mid.pack_start(self.ring, False, False, 0)
        self.mid_line = label("", "faint", xalign=0.5, wrap=True)
        mid.pack_start(self.mid_line, False, False, 0)
        body.pack_start(mid, False, False, 0)
        body.pack_start(right, True, True, 0)
        self.s_cpu = Spark("CPU", "%", 100)
        self.s_mem = Spark("Memory", "GB")
        self.s_disk = Spark("Disk", "MB/s")
        self.s_net = Spark("Network", "KB/s")
        self.s_ai = Spark("AI tokens", "tok/s")
        self.s_lat = Spark("Shell frame time", "ms")
        for s in (self.s_cpu, self.s_mem, self.s_disk):
            left.pack_start(s, False, False, 0)
        for s in (self.s_net, self.s_ai, self.s_lat):
            right.pack_start(s, False, False, 0)
        self.prev_net, self.prev_disk, self.prev_t = _net_bytes(), _disk_bytes(), time.monotonic()
        self.s_mem.maximum = C.memory()["total_gb"] or None
        C.cpu_percent()
        GLib.timeout_add(1000, self.sample)
        self.sample()

    def sample(self):
        now = time.monotonic()
        dt = max(1e-3, now - self.prev_t)
        cpu = C.cpu_percent()
        mem = C.memory()
        net = _net_bytes(); disk = _disk_bytes()
        kbs = ((net[0] - self.prev_net[0]) + (net[1] - self.prev_net[1])) / dt / 1024
        mbs = ((disk[0] - self.prev_disk[0]) + (disk[1] - self.prev_disk[1])) / dt / 1048576
        self.prev_net, self.prev_disk, self.prev_t = net, disk, now
        self.s_cpu.push(cpu); self.s_mem.push(mem["used_gb"]); self.s_net.push(max(0, kbs)); self.s_disk.push(max(0, mbs))
        ai = C.ai_status()
        toks = None
        try:
            import json
            with open(C.metrics_path()) as f:
                m = json.load(f)
            if time.time() - m.get("ts", 0) < 3600:
                toks = m.get("tokens_per_s")
        except (OSError, ValueError):
            pass
        self.s_ai.push(toks if toks else 0)
        self.s_lat.push(None)
        if cpu is not None:
            self.ring.value = cpu
        self.ring.queue_draw()
        try:
            with open("/proc/loadavg") as f:
                la = f.read().split()[:3]
        except OSError:
            la = ["?", "?", "?"]
        self.head_line.set_text(f"{os.cpu_count()} threads  ·  load {la[0]} / {la[1]} / {la[2]}  ·  up {C.uptime_text()}")
        self.mid_line.set_text(f"{ai['label']}  ·  {ai['model']}{'  ·  warm' if ai['warm'] else ''}\nNo NPU on this machine: the ring is CPU load.")
        return True


def main(argv=None) -> int:
    load_css()
    win = Monitor()
    win.show_all()
    if os.environ.get("ETERNITY_UI_SMOKE"):
        for v in (12, 30, 25, 48, 40, 35):
            win.s_cpu.push(v); win.s_mem.push(3.2 + v / 50); win.s_net.push(v * 3); win.s_disk.push(v / 10); win.s_ai.push(170 - v)
        win.ring.value = 35
        shot(win, "monitor")
        return 0
    Gtk.main()
    return 0
