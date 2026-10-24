"""GTK 3 helpers shared by the Eternity windows: Nocturne CSS, the mark, fonts."""
import math
import os

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

ASSETS = os.environ.get("ETERNITY_ASSETS", "/usr/share/eternity")

CSS = b"""
@define-color bg #161826;
@define-color surface #232532;
@define-color text #e9e9ed;
@define-color muted #9397ab;
@define-color faint #595d6c;
@define-color accent #9184d9;
@define-color accent300 #d2cefd;
@define-color accent800 #423a6a;
@define-color accent900 #2b2741;
@define-color line alpha(#e9e9ed, 0.16);

.eternity-window, .eternity-window window, .eternity-window decoration { background-color: @bg; color: @text; }
.eternity-window * { font-family: Inter, sans-serif; }
.eternity-window label { color: @text; }
.eternity-window .muted { color: @muted; }
.eternity-window .faint { color: @faint; font-size: 12px; }
.eternity-window .kicker { color: @muted; font-size: 11px; letter-spacing: 0.14em; }
.eternity-window .title { font-size: 26px; font-weight: 500; }
.eternity-window .subtitle { font-size: 15px; color: @muted; }
.eternity-window .wordmark { font-family: Michroma, Inter, sans-serif; font-size: 11px; letter-spacing: 0.3em; color: @text; }
.eternity-window .card { background-color: @surface; border: 1px solid @line; border-radius: 14px; padding: 16px 18px; }
.eternity-window .pill { border-radius: 999px; padding: 2px 10px; font-size: 11px; background-color: @accent900; color: @accent300; }
.eternity-window entry, .eternity-window textview, .eternity-window textview text {
    background-color: @surface; color: @text; border: 1px solid @line; border-radius: 8px; padding: 10px 12px; caret-color: @accent; }
.eternity-window entry:focus { border-color: @accent; box-shadow: 0 0 0 1px alpha(@accent, 0.5); }
.eternity-window entry.command { font-size: 17px; padding: 14px 18px; border-radius: 14px; }
.eternity-window button { background-image: none; background-color: @surface; color: @text; border: 1px solid @line;
    border-radius: 8px; padding: 8px 18px; text-shadow: none; box-shadow: none; }
.eternity-window button:hover { border-color: @accent; }
.eternity-window button.primary { background-color: @accent; color: #161826; border-color: @accent; font-weight: 500; }
.eternity-window button.primary:hover { background-color: @accent300; }
.eternity-window button.ghost { background-color: transparent; border-color: transparent; color: @muted; }
.eternity-window button.ghost:hover { color: @text; }
.eternity-window button.danger { border-color: #e88a8a; color: #e88a8a; }
.eternity-window checkbutton, .eternity-window radiobutton { color: @text; }
.eternity-window check, .eternity-window radio { background-color: @surface; border: 1px solid @muted; color: @accent300; -gtk-icon-shadow: none; }
.eternity-window check:checked, .eternity-window radio:checked { background-color: @accent; border-color: @accent; color: #161826; }
.eternity-window switch { background-color: @surface; border: 1px solid @line; }
.eternity-window switch:checked { background-color: @accent; }
.eternity-window switch slider { background-color: @text; border: none; }
.eternity-window scale trough { background-color: @surface; border: 1px solid @line; }
.eternity-window scale highlight { background-color: @accent; }
.eternity-window scale slider { background-color: @text; border: none; }
.eternity-window separator { background-color: @line; min-height: 1px; }
.eternity-window .step-dot { color: @faint; font-size: 20px; }
.eternity-window .step-dot.active { color: @accent; }
.eternity-window .answer { font-size: 15px; }
.eternity-window .readout { font-family: "JetBrains Mono", monospace; font-size: 11px; color: @muted; }
.eternity-window scrolledwindow, .eternity-window viewport { background-color: transparent; }
.eternity-window .orbit-card { background-color: alpha(@surface, 0.86); border: 1px solid @line; border-radius: 14px; padding: 12px 14px; }
.eternity-window .orbit-card .value { font-size: 20px; font-weight: 500; }
.eternity-window .status-strip { background-color: alpha(@surface, 0.7); border: 1px solid @line; border-radius: 999px; padding: 4px 14px; }
.eternity-window .launcher-item { background-color: alpha(@surface, 0.9); border: 1px solid @line; border-radius: 999px; padding: 12px; }
.eternity-window .launcher-item:hover, .eternity-window .launcher-item.selected { border-color: @accent; background-color: @accent900; }
tooltip, tooltip * { background-color: @surface; color: @text; border: 1px solid @line; }
"""

_loaded = False


def load_css() -> None:
    global _loaded
    if _loaded:
        return
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    settings = Gtk.Settings.get_default()
    if settings:
        settings.set_property("gtk-application-prefer-dark-theme", True)
    _loaded = True


def mark_image(size: int) -> Gtk.Image:
    """The Möbius mark as a Gtk.Image (from the pre-rendered PNGs)."""
    for cand in (f"mark-{size}.png", "mark-176.png", "mark-512.png", "logo-256.png"):
        path = os.path.join(ASSETS, cand)
        if os.path.exists(path):
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, size, True)
            return Gtk.Image.new_from_pixbuf(pb)
    return Gtk.Image.new_from_icon_name("eternity", Gtk.IconSize.DIALOG)


def wordmark_label(size_class: str = "wordmark") -> Gtk.Box:
    """ETERNITY in Michroma with the three-bar E drawn as text (the font has an E; the bars are the design's flourish)."""
    box = Gtk.Box(spacing=0)
    lbl = Gtk.Label(label="ETERNITY")
    lbl.get_style_context().add_class(size_class)
    box.pack_start(lbl, False, False, 0)
    return box


def label(text: str, *classes: str, xalign: float = 0.0, wrap: bool = False, selectable: bool = False) -> Gtk.Label:
    lbl = Gtk.Label(label=text)
    lbl.set_xalign(xalign)
    lbl.set_line_wrap(wrap)
    lbl.set_selectable(selectable)
    for c in classes:
        lbl.get_style_context().add_class(c)
    return lbl


def button(text: str, *classes: str, on_click=None) -> Gtk.Button:
    b = Gtk.Button(label=text)
    for c in classes:
        b.get_style_context().add_class(c)
    if on_click:
        b.connect("clicked", lambda *_: on_click())
    return b


def ease_out_cubic(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def pulse(t: float) -> float:
    return 0.5 + 0.5 * math.sin(t)


def idle(fn, *args):
    GLib.idle_add(lambda: (fn(*args), False)[1])


def guarded(name: str, fn, *args) -> int:
    """Run a window's main() and write any crash to ~/.local/state/eternity/ui.log, so an
    autostarted window that never appears leaves a trace."""
    import traceback
    try:
        return int(fn(*args) or 0)
    except SystemExit as e:
        return int(e.code or 0)
    except Exception:
        try:
            from .. import settings as _S
            os.makedirs(_S.state_dir(), exist_ok=True)
            with open(os.path.join(_S.state_dir(), "ui.log"), "a", encoding="utf-8") as f:
                f.write("--- " + name + " crashed\n" + traceback.format_exc() + "\n")
        except Exception:
            pass
        traceback.print_exc()
        return 1


def shot(win: Gtk.Window, name: str) -> None:
    """Save a PNG of a window when ETERNITY_UI_SHOT_DIR is set (headless checks under Xvfb).
    Lets the frame clock run a few frames so sizes are allocated, then draws the widget tree
    offscreen through cairo (independent of a compositor or window manager)."""
    d = os.environ.get("ETERNITY_UI_SHOT_DIR")
    if not d:
        return
    import time
    import cairo
    for _ in range(25):
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        time.sleep(0.02)
    nat = win.get_preferred_size()[1]
    alloc = win.get_allocation()
    w, h = max(1, alloc.width, nat.width), max(1, alloc.height, nat.height)
    if (alloc.width, alloc.height) != (w, h):
        win.resize(w, h)
        for _ in range(15):
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)
            time.sleep(0.02)
        alloc = win.get_allocation()
        w, h = max(1, alloc.width), max(1, alloc.height)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    cr = cairo.Context(surface)
    cr.set_source_rgb(0x16 / 255, 0x18 / 255, 0x26 / 255)
    cr.paint()
    win.draw(cr)
    os.makedirs(d, exist_ok=True)
    surface.write_to_png(os.path.join(d, f"{name}.png"))
