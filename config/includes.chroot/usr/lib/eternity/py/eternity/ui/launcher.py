"""Radial launcher (design scene 06): applications fan out around the mark; typing filters
them ("fil" -> Files). Enter opens the highlighted one, Esc closes. Reads the .desktop
entries of the system and the user (eternity.launcher_index), so it always shows what is
really installed.
"""
import math
import os
import subprocess
import sys

from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from .. import launcher_index as LI
from . import label, load_css, mark_image, shot

RING = 12   # apps on the ring; the rest are reachable by typing


class Launcher(Gtk.Window):
    def __init__(self):
        super().__init__(title="Eternity launcher")
        self.get_style_context().add_class("eternity-window")
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_default_size(760, 620)
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self.on_key)
        self.apps = LI.load()
        self.filter_text = ""
        self.selected = 0

        self.fixed = Gtk.Fixed()
        self.add(self.fixed)
        self.cx, self.cy, self.r = 380, 290, 215
        self.fixed.put(mark_image(120), self.cx - 60, self.cy - 60)
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Type to filter")
        self.entry.set_size_request(320, -1)
        self.entry.connect("changed", self.on_changed)
        self.entry.connect("activate", lambda *_: self.launch_selected())
        self.fixed.put(self.entry, self.cx - 160, 560)
        self.caption = label("", "muted", xalign=0.5)
        self.caption.set_size_request(760, -1)
        self.fixed.put(self.caption, 0, 520)
        self.items = []
        self.rebuild()

    def visible_apps(self):
        q = self.filter_text.strip().lower()
        if not q:
            return self.apps[:RING]
        hits = [a for a in self.apps if q in a.name.lower() or any(q in k for k in a.keywords)]
        return hits[:RING]

    def rebuild(self):
        for it in self.items:
            self.fixed.remove(it)
        self.items = []
        apps = self.visible_apps()
        n = max(1, len(apps))
        self.selected = min(self.selected, max(0, n - 1))
        for i, app in enumerate(apps):
            ang = -math.pi / 2 + i * 2 * math.pi / n
            x, y = self.cx + math.cos(ang) * self.r, self.cy + math.sin(ang) * self.r
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            btn = Gtk.Button()
            btn.get_style_context().add_class("launcher-item")
            if i == self.selected:
                btn.get_style_context().add_class("selected")
            img = Gtk.Image.new_from_icon_name(app.icon or "application-x-executable", Gtk.IconSize.DIALOG)
            img.set_pixel_size(36)
            btn.add(img)
            btn.connect("clicked", lambda _b, a=app: self.launch(a))
            box.pack_start(btn, False, False, 0)
            box.pack_start(label(app.name, "faint", xalign=0.5), False, False, 0)
            box.set_size_request(90, -1)
            self.fixed.put(box, int(x - 45), int(y - 36))
            self.items.append(box)
        if apps:
            self.caption.set_text(f"{apps[self.selected].name}  ·  {apps[self.selected].comment}" if apps[self.selected].comment else apps[self.selected].name)
        else:
            self.caption.set_text("Nothing matches. Try Ask Eternity (Super + Space).")
        self.show_all()

    def on_changed(self, entry):
        self.filter_text = entry.get_text()
        self.selected = 0
        self.rebuild()

    def on_key(self, _w, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
            return True
        n = len(self.visible_apps())
        if event.keyval in (Gdk.KEY_Right, Gdk.KEY_Down, Gdk.KEY_Tab) and n:
            self.selected = (self.selected + 1) % n
            self.rebuild()
            return True
        if event.keyval in (Gdk.KEY_Left, Gdk.KEY_Up) and n:
            self.selected = (self.selected - 1) % n
            self.rebuild()
            return True
        return False

    def launch_selected(self):
        apps = self.visible_apps()
        if apps:
            self.launch(apps[self.selected])

    def launch(self, app):
        LI.launch(app)
        Gtk.main_quit()


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    load_css()
    win = Launcher()
    win.show_all()
    win.entry.grab_focus()
    if os.environ.get("ETERNITY_UI_SMOKE"):
        shot(win, "launcher-all")
        win.entry.set_text("fil")
        while Gtk.events_pending():
            Gtk.main_iteration()
        shot(win, "launcher-filtered")
        return 0
    Gtk.main()
    return 0
