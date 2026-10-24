"""Files: search by meaning (design scene 07). A Files-like window with the usual places on
the left and "Search by meaning…" on top; results come grouped with the header "Grouped by
Eternity · N matches · M folders · <month> · <ms>", thumbnails for photos, and Eternity's
suggestion line. The index is built in the background on first use.
"""
import os
import subprocess
import sys
import threading
import time

from gi.repository import GdkPixbuf, GLib, Gtk  # noqa: E402

from .. import find as F
from . import button, label, load_css, shot

PLACES = (("Recents", "~"), ("Desktop", "~/Desktop"), ("Documents", "~/Documents"), ("Downloads", "~/Downloads"),
          ("Pictures", "~/Pictures"), ("Music", "~/Music"), ("Projects", "~/Projects"))


class FindWindow(Gtk.Window):
    def __init__(self, index: F.Index):
        super().__init__(title="Files · search by meaning")
        self.index = index
        self.get_style_context().add_class("eternity-window")
        self.set_default_size(1040, 680)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("destroy", Gtk.main_quit)
        root = Gtk.Box(spacing=0)
        self.add(root)
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        side.set_size_request(190, -1)
        side.set_margin_top(20); side.set_margin_start(16); side.set_margin_end(10)
        side.pack_start(label("PLACES", "kicker"), False, False, 6)
        for name, path in PLACES:
            b = button(name, "ghost", on_click=lambda p=path: subprocess.Popen(["xdg-open", os.path.expanduser(p)]))
            b.set_halign(Gtk.Align.START)
            side.pack_start(b, False, False, 0)
        root.pack_start(side, False, False, 0)
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        for s in ("top", "bottom", "start", "end"):
            getattr(main, f"set_margin_{s}")(20)
        root.pack_start(main, True, True, 0)
        self.entry = Gtk.Entry()
        self.entry.get_style_context().add_class("command")
        self.entry.set_placeholder_text("Search by meaning…  (photos from the Lisbon trip, the shell spec, invoices from March)")
        self.entry.connect("activate", self.on_search)
        main.pack_start(self.entry, False, False, 0)
        self.header = label("", "muted")
        main.pack_start(self.header, False, False, 0)
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.flow = Gtk.FlowBox()
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_max_children_per_line(6)
        self.flow.set_column_spacing(10); self.flow.set_row_spacing(10)
        self.scroll.add(self.flow)
        main.pack_start(self.scroll, True, True, 0)
        sugg = Gtk.Box(spacing=10)
        sugg.get_style_context().add_class("card")
        sugg.pack_start(label("ETERNITY", "kicker"), False, False, 0)
        self.suggest = label("Type what you remember about the file, not its name.", "muted", wrap=True)
        sugg.pack_start(self.suggest, True, True, 0)
        self.open_folder = button("Open folder", "ghost")
        self.open_folder.set_no_show_all(True)
        sugg.pack_end(self.open_folder, False, False, 0)
        main.pack_start(sugg, False, False, 0)
        self.last_group = None
        self.indexing = False
        GLib.idle_add(self.ensure_index)

    def ensure_index(self):
        if self.indexing:
            return False
        self.indexing = True
        self.header.set_text(f"{self.index.count()} files indexed  ·  updating in the background …")

        def work():
            try:
                st = self.index.build(progress=lambda d, n: GLib.idle_add(self.header.set_text, f"indexing {d} of {n} new or changed files …"))
                GLib.idle_add(self.header.set_text, f"{st['total']} files indexed  ·  {self.index.embedder_name.replace('Embedder', '').lower()} embeddings  ·  on device")
            except Exception as e:
                GLib.idle_add(self.header.set_text, f"index error: {e}")
            self.indexing = False
        threading.Thread(target=work, daemon=True).start()
        return False

    def tile(self, hit: F.Hit) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.get_style_context().add_class("orbit-card")
        box.set_size_request(150, -1)
        img = None
        if hit.kind == "photo":
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(hit.path, 140, 100, True)
                img = Gtk.Image.new_from_pixbuf(pb)
            except GLib.Error:
                img = None
        if img is None:
            icon = {"text": "text-x-generic", "document": "x-office-document", "music": "audio-x-generic", "video": "video-x-generic",
                    "photo": "image-x-generic"}.get(hit.kind, "text-x-generic")
            img = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.DIALOG)
            img.set_pixel_size(48)
        box.pack_start(img, False, False, 0)
        name = label(hit.name, "muted", xalign=0.0)
        name.set_ellipsize(3)
        name.set_max_width_chars(18)
        box.pack_start(name, False, False, 0)
        box.pack_start(label(hit.when, "faint"), False, False, 0)
        ev = Gtk.EventBox()
        ev.add(box)
        ev.connect("button-press-event", lambda *_: subprocess.Popen(["xdg-open", hit.path]) and True)
        return ev

    def on_search(self, *_):
        q = self.entry.get_text().strip()
        if not q:
            return
        for c in self.flow.get_children():
            self.flow.remove(c)
        self.header.set_text("searching …")

        def work():
            t0 = time.monotonic()
            try:
                hits = self.index.search(q)
            except Exception as e:
                GLib.idle_add(self.header.set_text, f"search failed: {e}")
                return
            ms = (time.monotonic() - t0) * 1000
            g = F.group(hits)
            GLib.idle_add(self.show_results, hits, g, ms)
        threading.Thread(target=work, daemon=True).start()

    def show_results(self, hits, g, ms):
        self.last_group = g
        self.header.set_text(F.header(g, ms) if hits else "No matches")
        for h in hits:
            self.flow.add(self.tile(h))
        self.suggest.set_text(F.suggestion(g))
        if g.get("top_folder"):
            self.open_folder.show()
            try:
                self.open_folder.disconnect_by_func(self._open_top)
            except TypeError:
                pass
            self.open_folder.connect("clicked", self._open_top)
        self.flow.show_all()
        return False

    def _open_top(self, *_):
        if self.last_group and self.last_group.get("top_folder"):
            subprocess.Popen(["xdg-open", str(self.last_group["top_folder"])])


def main(argv=None) -> int:
    from . import guarded
    return guarded("find", _main, argv)


def _main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    load_css()
    smoke = bool(os.environ.get("ETERNITY_UI_SMOKE"))
    idx = F.Index(embedder=F.HashEmbedder() if smoke else None)
    win = FindWindow(idx)
    win.show_all()
    if argv:
        win.entry.set_text(" ".join(argv))
        GLib.idle_add(win.on_search)
    if smoke:
        for _ in range(30):
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)
            time.sleep(0.05)
        win.entry.set_text("photos from the Lisbon trip")
        win.on_search()
        for _ in range(20):
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)
            time.sleep(0.05)
        shot(win, "find")
        return 0
    Gtk.main()
    return 0
