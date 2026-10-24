"""First run: "Hello. I'm Eternity." Three steps plus the assistant choice (design scene 02,
backlog item 1): greeting, name, unlock methods, which assistant answers (on this device,
Claude or ChatGPT with the user's own key), done. Runs once per user from
/etc/xdg/autostart (eternity-firstrun --autostart exits at once when already completed).
"""
import hashlib
import json
import os
import secrets as _secrets
import sys

from gi.repository import Gdk, GLib, Gtk, Pango  # noqa: E402

from .. import providers as P
from .. import settings as S
from . import button, label, load_css, mark_image, shot

STEPS = ("hello", "name", "unlock", "assistant", "done")


def pin_path() -> str:
    return os.path.join(S.config_dir(), "pin.json")


def store_pin(pin: str) -> None:
    salt = _secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), 200_000).hex()
    S._atomic_write(pin_path(), json.dumps({"salt": salt, "hash": digest, "kdf": "pbkdf2-sha256-200000"}) + "\n", 0o600)


def verify_pin(pin: str) -> bool:
    try:
        with open(pin_path(), encoding="utf-8") as f:
            rec = json.load(f)
        digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(rec["salt"]), 200_000).hex()
        return _secrets.compare_digest(digest, rec["hash"])
    except (OSError, ValueError, KeyError):
        return False


class FirstRun(Gtk.Window):
    def __init__(self, cfg: S.Settings, store: S.SecretStore):
        super().__init__(title="Eternity 08")
        self.cfg, self.store = cfg, store
        self.set_default_size(920, 620)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)
        self.get_style_context().add_class("eternity-window")
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", lambda _w, e: (Gtk.main_quit(), True)[1] if e.keyval == Gdk.KEY_Escape else False)
        self.step = 0
        self.pin_value = ""

        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(outer)
        # left: the presence
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        left.set_size_request(360, -1)
        left.set_valign(Gtk.Align.CENTER)
        left.set_margin_start(40)
        left.set_margin_end(10)
        left.pack_start(mark_image(176), False, False, 0)
        wm = label("ETERNITY", "wordmark", xalign=0.5)
        left.pack_start(wm, False, False, 0)
        sub = label("PERSONAL OS · 08", "kicker", xalign=0.5)
        left.pack_start(sub, False, False, 0)
        outer.pack_start(left, False, False, 0)
        # right: the steps
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        right.set_margin_top(54)
        right.set_margin_bottom(40)
        right.set_margin_start(30)
        right.set_margin_end(44)
        outer.pack_start(right, True, True, 0)
        self.kicker = label("", "kicker")
        right.pack_start(self.kicker, False, False, 0)
        self.title_lbl = label("", "title", wrap=True)
        right.pack_start(self.title_lbl, False, False, 0)
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        right.pack_start(self.body, True, True, 0)
        nav = Gtk.Box(spacing=10)
        self.dots = Gtk.Box(spacing=6)
        nav.pack_start(self.dots, False, False, 0)
        self.skip = button("Skip for now", "ghost", on_click=self.on_skip)
        nav.pack_end(self.skip, False, False, 0)
        self.cont = button("Continue", "primary", on_click=self.on_continue)
        nav.pack_end(self.cont, False, False, 0)
        right.pack_end(nav, False, False, 0)
        self.render()

    # ------------------------------------------------------------------ step bodies
    def clear_body(self):
        for c in self.body.get_children():
            self.body.remove(c)

    def render(self):
        self.clear_body()
        for c in self.dots.get_children():
            self.dots.remove(c)
        for i in range(len(STEPS) - 1):
            d = label("●", "step-dot")
            if i == self.step:
                d.get_style_context().add_class("active")
            self.dots.pack_start(d, False, False, 0)
        step = STEPS[self.step]
        self.skip.set_visible(step in ("name", "unlock", "assistant"))
        self.cont.set_label("Continue" if step != "done" else "Start")
        getattr(self, f"step_{step}")()
        self.show_all()
        self.skip.set_visible(step in ("name", "unlock", "assistant"))

    def step_hello(self):
        self.kicker.set_text("FIRST RUN")
        self.title_lbl.set_text("Hello. I'm Eternity.")
        self.body.pack_start(label("I run on this device, in real time. Everything personal stays here unless you decide otherwise.\n\nLet's set a few things.", "subtitle", wrap=True), False, False, 0)

    def step_name(self):
        self.kicker.set_text("STEP 1 OF 3")
        self.title_lbl.set_text("What should I call you?")
        self.name_entry = Gtk.Entry()
        self.name_entry.set_placeholder_text("Your name")
        real = GLib.get_real_name() or ""
        self.name_entry.set_text(self.cfg.name or (real.split(" ")[0] if real and real != "Unknown" else ""))
        self.name_entry.connect("activate", lambda *_: self.on_continue())
        self.body.pack_start(self.name_entry, False, False, 0)
        self.body.pack_start(label("Used only on this device, in greetings and in the assistant's replies.", "faint", wrap=True), False, False, 0)

    def step_unlock(self):
        self.kicker.set_text("STEP 2 OF 3")
        self.title_lbl.set_text("How do you want to unlock?")
        self.body.pack_start(label("Your account passphrase always works at the login screen. A PIN additionally confirms sensitive actions the assistant proposes (power, shell commands).", "subtitle", wrap=True), False, False, 0)
        grid = Gtk.Grid(column_spacing=18, row_spacing=10)
        self.unlock_checks = {}
        rows = (("passphrase", "Passphrase", "your account password, used by the login screen", True),
                ("pin", "PIN", "4 to 8 digits, asked before dangerous actions", True),
                ("face", "Face", "coming later: needs the on-device camera model", False),
                ("voice", "Voice", "coming later: needs the on-device voice model", False))
        for r, (key, title, hint, available) in enumerate(rows):
            cb = Gtk.CheckButton(label=title)
            cb.set_active(key in self.cfg.unlock_methods or key == "passphrase")
            cb.set_sensitive(available and key != "passphrase")
            cb.connect("toggled", self.on_unlock_toggled)
            grid.attach(cb, 0, r, 1, 1)
            grid.attach(label(hint, "faint", wrap=True), 1, r, 1, 1)
            self.unlock_checks[key] = cb
        self.body.pack_start(grid, False, False, 0)
        self.pin_entry = Gtk.Entry()
        self.pin_entry.set_visibility(False)
        self.pin_entry.set_input_purpose(Gtk.InputPurpose.PIN)
        self.pin_entry.set_max_length(8)
        self.pin_entry.set_placeholder_text("Choose a PIN (digits only)")
        self.pin_entry.set_text(self.pin_value)
        self.body.pack_start(self.pin_entry, False, False, 0)
        self.pin_hint = label("", "faint")
        self.body.pack_start(self.pin_hint, False, False, 0)
        self.on_unlock_toggled(None)

    def on_unlock_toggled(self, *_):
        want_pin = self.unlock_checks["pin"].get_active()
        self.pin_entry.set_sensitive(want_pin)
        self.pin_hint.set_text("Stored on this device as a salted hash (PBKDF2)." if want_pin else "")

    def step_assistant(self):
        self.kicker.set_text("STEP 3 OF 3")
        self.title_lbl.set_text("Who answers when you ask?")
        self.body.pack_start(label("The assistant can understand this computer and act for you; every action is confirmed by you first and can be undone.", "subtitle", wrap=True), False, False, 0)
        self.provider_radios = {}
        first = None
        for key in ("local", "anthropic", "openai"):
            rb = Gtk.RadioButton.new_with_label_from_widget(first, P.PROVIDER_LABELS[key])
            first = first or rb
            rb.set_active(self.cfg.provider == key)
            rb.connect("toggled", self.on_provider_toggled)
            self.provider_radios[key] = rb
            self.body.pack_start(rb, False, False, 0)
        self.body.pack_start(label("On this device: the bundled Qwen model via llama.cpp, works offline, nothing leaves the machine.", "faint", wrap=True), False, False, 0)
        self.key_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.key_entry = Gtk.Entry()
        self.key_entry.set_visibility(False)
        self.key_entry.set_placeholder_text("Paste your API key")
        self.key_box.pack_start(self.key_entry, False, False, 0)
        self.key_link = Gtk.LinkButton.new_with_label("", "Get a key from the provider's console")
        self.key_link.set_halign(Gtk.Align.START)
        self.key_box.pack_start(self.key_link, False, False, 0)
        self.key_box.pack_start(label(f"Stored in your {'keyring' if self.store.backend == 'keyring' else 'config folder (keyring not running; file mode 600)'}; sent only to that provider.", "faint", wrap=True), False, False, 0)
        self.body.pack_start(self.key_box, False, False, 0)
        self.ondevice = Gtk.CheckButton(label="Keep everything on this device (disables cloud assistants)")
        self.ondevice.set_active(self.cfg.on_device_only and self.cfg.provider == "local")
        self.ondevice.connect("toggled", self.on_provider_toggled)
        self.body.pack_start(self.ondevice, False, False, 0)
        self.on_provider_toggled(None)

    def selected_provider(self) -> str:
        return next(k for k, rb in self.provider_radios.items() if rb.get_active())

    def on_provider_toggled(self, *_):
        prov = self.selected_provider()
        cloud = prov != "local"
        self.key_box.set_visible(cloud)
        self.key_box.set_no_show_all(not cloud)
        if cloud:
            self.key_box.show_all()
            self.key_link.set_uri(P.PROVIDER_KEY_URLS[prov])
            existing = self.store.get(prov)
            self.key_entry.set_placeholder_text("A key is already stored; paste a new one to replace it" if existing else "Paste your API key")
            self.ondevice.set_active(False)
        self.ondevice.set_sensitive(not cloud)

    def step_done(self):
        self.kicker.set_text("READY")
        self.title_lbl.set_text(f"Good to meet you{', ' + self.cfg.name if self.cfg.name else ''}.")
        who = P.PROVIDER_LABELS[self.cfg.effective_provider()]
        lines = [f"Assistant: {who}.",
                 "Unlock: " + ", ".join(m for m in self.cfg.unlock_methods) + ".",
                 "Open the command bar any time with Super + Space and ask, or type a command.",
                 "Change any of this later in Settings > Eternity (\"How she shows up\")."]
        for ln in lines:
            self.body.pack_start(label(ln, "subtitle", wrap=True), False, False, 0)

    # ------------------------------------------------------------------ navigation
    def on_skip(self):
        self.advance(save=False)

    def on_continue(self):
        self.advance(save=True)

    def advance(self, save: bool):
        step = STEPS[self.step]
        if save and step == "name":
            self.cfg.name = self.name_entry.get_text().strip()[:40]
        if save and step == "unlock":
            methods = [k for k, cb in self.unlock_checks.items() if cb.get_active()]
            if "pin" in methods:
                pin = self.pin_entry.get_text().strip()
                if not (pin.isdigit() and 4 <= len(pin) <= 8):
                    self.pin_hint.set_text("The PIN must be 4 to 8 digits.")
                    return
                store_pin(pin)
                self.pin_value = pin
            self.cfg.unlock_methods = methods
        if save and step == "assistant":
            prov = self.selected_provider()
            if prov != "local":
                key = self.key_entry.get_text().strip()
                if key:
                    self.store.set(prov, key)
                elif not self.store.get(prov):
                    self.key_entry.set_placeholder_text("An API key is needed for this assistant")
                    self.key_entry.grab_focus()
                    return
                self.cfg.on_device_only = False
            else:
                self.cfg.on_device_only = self.ondevice.get_active()
            self.cfg.provider = prov
        S.save(self.cfg)
        if step == "done":
            self.cfg.first_run_done = True
            S.save(self.cfg)
            Gtk.main_quit()
            return
        self.step += 1
        self.render()


def main(argv=None) -> int:
    from . import guarded
    return guarded("firstrun", _main, argv)


def _main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cfg = S.load()
    if "--autostart" in argv and cfg.first_run_done:
        return 0
    if "--reset" in argv:
        cfg.first_run_done = False
    load_css()
    win = FirstRun(cfg, S.SecretStore(lazy=True))
    win.show_all()
    if os.environ.get("ETERNITY_UI_SMOKE"):
        # headless smoke: walk every step without saving secrets, then quit
        for i in range(len(STEPS)):
            shot(win, f"firstrun-{i}-{STEPS[win.step]}")
            win.advance(save=False)
            while Gtk.events_pending():
                Gtk.main_iteration()
        return 0
    Gtk.main()
    return 0
