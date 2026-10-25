"""Ask Eternity: the command bar (design scenes 04 and 05). Super+Space opens a bar at the
bottom of the screen: "Ask Eternity, or type a command". The reply streams in above it with
the first-token and tokens/s readout; actions the assistant proposes appear as cards and are
confirmed in a dialog (PIN for dangerous ones when the user chose a PIN); every executed
action can be undone from its card. Lines starting with ">" run as a shell command (after
confirmation), "/" lines are quick commands (/undo, /clear, /settings, /local, /help).
"""
import os
import sys
import threading

from gi.repository import Gdk, GLib, Gtk, Pango  # noqa: E402

from .. import actions as A
from .. import agent as G
from .. import providers as P
from .. import settings as S
from . import button, label, load_css, mark_image, shot

HELP = ("Type a question or an instruction. Eternity may propose actions; you confirm each one.\n"
        "> command   runs a shell command after confirmation\n"
        "/undo       undoes the last undoable action      /clear   new conversation\n"
        "/settings   opens Settings > Eternity             /local   switch to the on-device model for this session")


class ConsentDialog(Gtk.Dialog):
    def __init__(self, parent, tool: A.Tool, args: dict, need_pin: bool):
        super().__init__(title="Eternity asks", transient_for=parent, modal=True)
        self.get_style_context().add_class("eternity-window")
        self.set_default_size(520, -1)
        box = self.get_content_area()
        box.set_spacing(10)
        box.set_margin_top(18); box.set_margin_bottom(6); box.set_margin_start(20); box.set_margin_end(20)
        risk = {"read": "reads information", "change": "changes something on this device", "dangerous": "is a sensitive action"}[tool.risk]
        box.pack_start(label(f"ALLOW {tool.name.replace('_', ' ').upper()}?", "kicker"), False, False, 0)
        box.pack_start(label(A.describe_call(tool, args), "subtitle", wrap=True, selectable=True), False, False, 0)
        box.pack_start(label(f"This {risk}. It will be logged and, where possible, can be undone.", "faint", wrap=True), False, False, 0)
        self.pin = None
        if need_pin:
            self.pin = Gtk.Entry()
            self.pin.set_visibility(False)
            self.pin.set_placeholder_text("Your PIN")
            self.pin.set_input_purpose(Gtk.InputPurpose.PIN)
            box.pack_start(self.pin, False, False, 0)
            self.pin.connect("activate", lambda *_: self.response(Gtk.ResponseType.OK))
        self.add_button("Not now", Gtk.ResponseType.CANCEL)
        ok = self.add_button("Allow", Gtk.ResponseType.OK)
        ok.get_style_context().add_class("primary" if tool.risk != "dangerous" else "danger")
        self.show_all()


class AskWindow(Gtk.Window):
    def __init__(self, cfg: S.Settings, bar_only: bool = True):
        super().__init__(title="Ask Eternity")
        self.cfg = cfg
        self.get_style_context().add_class("eternity-window")
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_default_size(820, -1)
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self.on_key)
        self.busy = False
        self.agent = None
        self.pending_consent = None

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        root.set_margin_top(14); root.set_margin_bottom(14); root.set_margin_start(16); root.set_margin_end(16)
        self.add(root)

        # conversation area (hidden until the first answer)
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.set_min_content_height(0)
        self.scroll.set_max_content_height(420)
        self.scroll.set_propagate_natural_height(True)
        self.feed = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.scroll.add(self.feed)
        root.pack_start(self.scroll, True, True, 0)
        self.scroll.set_no_show_all(True)

        # the bar
        bar = Gtk.Box(spacing=12)
        bar.pack_start(mark_image(28), False, False, 0)
        self.entry = Gtk.Entry()
        self.entry.get_style_context().add_class("command")
        self.entry.set_placeholder_text("Ask Eternity, or type a command")
        self.entry.connect("activate", self.on_submit)
        bar.pack_start(self.entry, True, True, 0)
        self.readout = label("", "readout")
        bar.pack_end(self.readout, False, False, 0)
        root.pack_start(bar, False, False, 0)
        who = P.PROVIDER_LABELS[cfg.effective_provider()]
        if cfg.effective_provider() == "claude_code":
            who += " via Claude Code"
        self.status = label(who + "  ·  Esc closes  ·  /help", "faint")
        root.pack_start(self.status, False, False, 0)
        self.position_bottom()

    def position_bottom(self):
        screen = Gdk.Screen.get_default()
        display = Gdk.Display.get_default()
        mon = display.get_primary_monitor() or display.get_monitor(0)
        geo = mon.get_workarea() if mon else None
        if geo:
            w = min(820, geo.width - 40)
            self.set_default_size(w, -1)
            self.move(geo.x + (geo.width - w) // 2, geo.y + geo.height - 96)

    # --------------------------------------------------------------- feed widgets
    def add_bubble(self, text: str, who: str) -> Gtk.Label:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card.get_style_context().add_class("card")
        card.pack_start(label("YOU" if who == "user" else "ETERNITY", "kicker"), False, False, 0)
        lbl = label(text, "answer", wrap=True, selectable=True)
        lbl.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        card.pack_start(lbl, False, False, 0)
        self.feed.pack_start(card, False, False, 0)
        self.scroll.set_no_show_all(False)
        self.scroll.show_all()
        card.show_all()
        GLib.idle_add(self.scroll_to_end)
        return lbl

    def add_action_card(self, info: dict):
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        card.get_style_context().add_class("card")
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        col.pack_start(label(("DONE" if info["ok"] else "NOT DONE") + "  ·  " + info["name"].replace("_", " "), "kicker"), False, False, 0)
        col.pack_start(label(info["summary"], "muted", wrap=True, selectable=True), False, False, 0)
        card.pack_start(col, True, True, 0)
        if info.get("undoable") and info["ok"]:
            undo = button("Undo", "ghost")
            undo.connect("clicked", lambda *_: self.do_undo(undo))
            card.pack_end(undo, False, False, 0)
        self.feed.pack_start(card, False, False, 0)
        card.show_all()
        GLib.idle_add(self.scroll_to_end)

    def scroll_to_end(self):
        adj = self.scroll.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())
        return False

    def do_undo(self, btn=None):
        if self.agent:
            msg = self.agent.undo_last()
            self.add_bubble(msg, "eternity")
            if btn:
                btn.set_sensitive(False)

    # --------------------------------------------------------------- consent (UI thread)
    def consent(self, tool: A.Tool, args: dict) -> bool:
        """Called from the worker thread: ask on the UI thread and wait."""
        ev = threading.Event()
        result = {"ok": False}

        def ask():
            need_pin = tool.risk == A.RISK_DANGEROUS and "pin" in self.cfg.unlock_methods and os.path.exists(
                os.path.join(S.config_dir(), "pin.json"))
            dlg = ConsentDialog(self, tool, args, need_pin)
            resp = dlg.run()
            ok = resp == Gtk.ResponseType.OK
            if ok and need_pin:
                from .firstrun import verify_pin
                ok = verify_pin(dlg.pin.get_text())
                if not ok:
                    self.add_bubble("The PIN did not match; the action was not run.", "eternity")
            dlg.destroy()
            result["ok"] = ok
            ev.set()
            return False
        GLib.idle_add(ask)
        ev.wait()
        return result["ok"]

    # --------------------------------------------------------------- input
    def on_key(self, _w, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
            return True
        return False

    def on_submit(self, *_):
        text = self.entry.get_text().strip()
        if not text or self.busy:
            return
        self.entry.set_text("")
        if text.startswith("/"):
            return self.quick(text)
        if text.startswith(">"):
            return self.shell(text[1:].strip())
        self.add_bubble(text, "user")
        self.start(text)

    def quick(self, text: str):
        cmd = text.split()[0].lower()
        if cmd == "/help":
            self.add_bubble(HELP, "eternity")
        elif cmd == "/undo":
            self.do_undo()
        elif cmd == "/clear":
            for c in self.feed.get_children():
                self.feed.remove(c)
            if self.agent:
                self.agent.reset()
            self.scroll.hide(); self.scroll.set_no_show_all(True)
        elif cmd == "/settings":
            import subprocess
            subprocess.Popen(["eternity-settings"])
        elif cmd == "/local":
            self.cfg.on_device_only = True
            self.agent = None
            self.status.set_text(P.PROVIDER_LABELS["local"] + "  ·  this session")
        else:
            self.add_bubble(f"Unknown command {cmd}. {HELP}", "eternity")

    def shell(self, command: str):
        if not command:
            return
        self.add_bubble("> " + command, "user")
        broker = self.ensure_agent().broker

        def work():
            res = broker.execute("run_command", {"command": command})
            GLib.idle_add(self.add_action_card, {"name": "run_command", "ok": res.ok, "summary": res.summary, "undoable": False})
        threading.Thread(target=work, daemon=True).start()

    def ensure_agent(self) -> G.Agent:
        if self.agent is None:
            self.agent = G.Agent(self.consent, cfg=self.cfg)
        return self.agent

    def start(self, question: str):
        self.busy = True
        self.entry.set_sensitive(False)
        self.readout.set_text("thinking …")
        answer = self.add_bubble("", "eternity")
        state = {"text": ""}

        def on_event(kind, payload):
            if kind == "text":
                state["text"] += payload
                answer.set_text(state["text"])
                self.scroll_to_end()
            elif kind == "status":
                self.readout.set_text(payload if len(payload) < 40 else payload[:40] + "…")
                if "model" in payload or "key" in payload or "reach" in payload or "Claude Code" in payload or "signed in" in payload:
                    answer.set_text((state["text"] + "\n" if state["text"] else "") + payload)
            elif kind == "action":
                self.add_action_card(payload)
            elif kind == "done":
                m = payload
                self.readout.set_text(m.readout() if isinstance(m, P.Metrics) else "")
                if not state["text"] and not isinstance(m, str):
                    if answer.get_text() == "":
                        answer.set_text("(no answer)")
                self.busy = False
                self.entry.set_sensitive(True)
                self.entry.grab_focus()
            return False

        def work():
            try:
                for kind, payload in self.ensure_agent().ask(question):
                    GLib.idle_add(on_event, kind, payload)
            except Exception as e:  # never leave the bar disabled
                GLib.idle_add(on_event, "status", f"{type(e).__name__}: {e}")
                GLib.idle_add(on_event, "done", P.Metrics())
        threading.Thread(target=work, daemon=True).start()


def main(argv=None) -> int:
    from . import guarded
    return guarded("ask", _main, argv)


def _main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    load_css()
    cfg = S.load()
    win = AskWindow(cfg)
    win.show_all()
    win.entry.grab_focus()
    if os.environ.get("ETERNITY_UI_SMOKE"):
        shot(win, "ask-empty")
        win.add_bubble("Move my 3pm to tomorrow and summarise the design doc", "user")
        win.add_bubble("Done. Design review is now tomorrow at 15:00.", "eternity")
        win.add_action_card({"name": "write_note", "ok": True, "summary": "note saved: ~/Documents/Notes/2026-10-25 Design review.md", "undoable": True})
        win.readout.set_text("on device  ·  first token 41 ms  ·  ~170 tok/s")
        while Gtk.events_pending():
            Gtk.main_iteration()
        shot(win, "ask-conversation")
        return 0
    if argv and argv[0] not in ("--bar",):
        win.entry.set_text(" ".join(argv))
        GLib.idle_add(win.on_submit)
    Gtk.main()
    return 0
