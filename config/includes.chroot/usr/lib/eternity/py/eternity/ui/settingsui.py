"""Settings > Eternity, "How she shows up" (design scene 09): assistant (provider, keys,
keep everything on this device), voice, verbosity, proactive suggestions, telemetry (there
is none, shown off and locked), unlock methods, trust level, and the action log. Changes
apply instantly to ~/.config/eternity/settings.json.
"""
import os
import subprocess
import sys

from gi.repository import GLib, Gtk  # noqa: E402

from .. import actions as A
from .. import providers as P
from .. import settings as S
from . import button, label, load_css, shot


class Row(Gtk.Box):
    def __init__(self, title: str, hint: str, widget: Gtk.Widget):
        super().__init__(spacing=16)
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        col.pack_start(label(title), False, False, 0)
        if hint:
            col.pack_start(label(hint, "faint", wrap=True), False, False, 0)
        self.pack_start(col, True, True, 0)
        widget.set_valign(Gtk.Align.CENTER)
        self.pack_end(widget, False, False, 0)


class SettingsWindow(Gtk.Window):
    def __init__(self, cfg: S.Settings, store: S.SecretStore):
        super().__init__(title="Settings · Eternity")
        self.cfg, self.store = cfg, store
        self.get_style_context().add_class("eternity-window")
        self.set_default_size(760, 720)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("destroy", Gtk.main_quit)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.add(scroll)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        for side in ("top", "bottom", "start", "end"):
            getattr(root, f"set_margin_{side}")(26)
        scroll.add(root)
        root.pack_start(label("SETTINGS · ETERNITY", "kicker"), False, False, 0)
        root.pack_start(label("How she shows up", "title"), False, False, 0)
        self.note = label("Changes apply instantly.", "muted")
        root.pack_start(self.note, False, False, 0)

        # --- assistant
        root.pack_start(self.section("ASSISTANT"), False, False, 6)
        self.prov = Gtk.ComboBoxText()
        self.cc = P.claude_code_status()
        for k in S.PROVIDERS:
            if k == "claude_code" and not self.cc["installed"]:
                continue
            self.prov.append(k, P.PROVIDER_LABELS[k])
        self.prov.set_active_id(cfg.provider)
        self.prov.connect("changed", self.on_provider)
        root.pack_start(Row("Who answers", "The on-device model works offline. Your Claude account runs Claude Code, signed in by you. API-key providers need your own key.", self.prov), False, False, 0)
        self.signin_status = label("", "faint", wrap=True)
        self.signin_btn = button("Sign in with your Claude account", "primary", on_click=self.on_signin)
        self.signin_row = Row("Claude account", "Eternity keeps no credentials: Claude Code holds the sign-in in your home folder. Every action still asks you first.", self.signin_btn)
        root.pack_start(self.signin_row, False, False, 0)
        root.pack_start(self.signin_status, False, False, 0)
        # Claude Code: model and what it may do without asking
        self.cc_model = Gtk.ComboBoxText()
        for m in S.CLAUDE_CODE_MODELS:
            self.cc_model.append(m, m)
        self.cc_model.set_active_id(cfg.claude_code_model)
        self.cc_model.connect("changed", lambda c: self.set_and_save("claude_code_model", c.get_active_id() or "sonnet"))
        self.cc_model_row = Row("Claude model", "sonnet is fast and capable; opus for the hardest tasks; haiku for quick answers.", self.cc_model)
        root.pack_start(self.cc_model_row, False, False, 0)
        self.cc_allow_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.cc_allow_box.pack_start(label("WHAT CLAUDE MAY DO WITHOUT ASKING", "kicker"), False, False, 0)
        self.cc_allow_box.pack_start(label("Everything else opens the consent dialog. sudo and pkexec are always refused.", "faint", wrap=True), False, False, 0)
        flow = Gtk.FlowBox(); flow.set_selection_mode(Gtk.SelectionMode.NONE); flow.set_max_children_per_line(4)
        self.cc_checks = {}
        for tool in S.CLAUDE_CODE_TOOLS + ("mcp__eternity__search_files_by_meaning", "mcp__eternity__hardware_report", "mcp__eternity__write_note"):
            cb = Gtk.CheckButton(label=tool.replace("mcp__eternity__", "Eternity: ").replace("_", " "))
            cb.set_active(tool in cfg.claude_code_allow)
            cb.connect("toggled", self.on_cc_allow)
            self.cc_checks[tool] = cb
            flow.add(cb)
        self.cc_allow_box.pack_start(flow, False, False, 0)
        root.pack_start(self.cc_allow_box, False, False, 0)
        self.ondevice = Gtk.Switch(active=cfg.on_device_only)
        self.ondevice.connect("notify::active", self.on_ondevice)
        root.pack_start(Row("Keep everything on this device", "Refuses cloud assistants even if one is selected; nothing leaves the machine.", self.ondevice), False, False, 0)
        self.key_entry = Gtk.Entry()
        self.key_entry.set_visibility(False)
        self.key_entry.set_width_chars(28)
        self.key_entry.connect("activate", self.on_key_saved)
        self.key_row = Row("API key", f"Stored in your {'keyring' if store.backend == 'keyring' else 'config folder (mode 600; keyring not running)'}. Press Enter to save; leave empty to keep.", self.key_entry)
        root.pack_start(self.key_row, False, False, 0)
        self.key_actions = Gtk.Box(spacing=8)
        self.key_actions.pack_end(button("Forget key", "danger", on_click=self.on_key_forget), False, False, 0)
        self.key_link = Gtk.LinkButton.new_with_label("https://console.anthropic.com/settings/keys", "Get a key")
        self.key_actions.pack_end(self.key_link, False, False, 0)
        root.pack_start(self.key_actions, False, False, 0)
        self.agent = Gtk.Switch(active=cfg.agent_mode)
        self.agent.connect("notify::active", lambda w, _p: self.set_and_save("agent_mode", w.get_active()))
        root.pack_start(Row("May propose actions", "Open apps, save notes, change volume, run commands: each one is confirmed by you first.", self.agent), False, False, 0)
        self.trust = Gtk.ComboBoxText()
        self.trust.append("0", "Confirm everything")
        self.trust.append("1", "Read-only lookups run without asking")
        self.trust.append("2", "Just do it (everything logged and undoable)")
        self.trust.set_active_id(str(cfg.trust_level))
        self.trust.connect("changed", lambda w: self.set_and_save("trust_level", int(w.get_active_id() or 0)))
        root.pack_start(Row("Trust level", "How much Eternity may do before asking.", self.trust), False, False, 0)

        # --- presence
        root.pack_start(self.section("PRESENCE"), False, False, 6)
        self.voice = Gtk.ComboBoxText()
        for k, lbl in (("off", "Off"), ("calm", "Calm (needs a voice engine, not bundled yet)"), ("bright", "Bright (needs a voice engine, not bundled yet)")):
            self.voice.append(k, lbl)
        self.voice.set_active_id(cfg.voice)
        self.voice.connect("changed", lambda w: self.set_and_save("voice", w.get_active_id()))
        root.pack_start(Row("Voice", "Spoken replies. No text-to-speech engine ships in this build, so only Off is active.", self.voice), False, False, 0)
        self.verb = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 2, 1)
        self.verb.set_draw_value(False)
        self.verb.set_size_request(220, -1)
        for i, m in enumerate(("brief", "normal", "detailed")):
            self.verb.add_mark(i, Gtk.PositionType.BOTTOM, m)
        self.verb.set_value(S.VERBOSITY.index(cfg.verbosity))
        self.verb.connect("value-changed", self.on_verbosity)
        root.pack_start(Row("Verbosity", "How much Eternity says.", self.verb), False, False, 0)
        self.proactive = Gtk.Switch(active=cfg.proactive)
        self.proactive.connect("notify::active", lambda w, _p: self.set_and_save("proactive", w.get_active()))
        root.pack_start(Row("Proactive suggestions", "Hints on the home screen based on what is happening on this device.", self.proactive), False, False, 0)
        self.name = Gtk.Entry(text=cfg.name)
        self.name.set_width_chars(18)
        self.name.connect("changed", lambda w: self.set_and_save("name", w.get_text().strip()[:40]))
        root.pack_start(Row("Your name", "Used in greetings.", self.name), False, False, 0)

        # --- privacy
        root.pack_start(self.section("PRIVACY"), False, False, 6)
        tele = Gtk.Switch(active=False)
        tele.set_sensitive(False)
        root.pack_start(Row("Share anonymous model telemetry", "Off, and there is nothing to share: Eternity 08 collects no telemetry at all.", tele), False, False, 0)
        logbtn = button("Open the action log", on_click=self.open_log)
        root.pack_start(Row("Action log", f"Everything the assistant did, with your decision: {A.Audit().path}", logbtn), False, False, 0)

        # --- unlock
        root.pack_start(self.section("UNLOCK"), False, False, 6)
        self.unlock = {}
        for key, title, hint, ok in (("passphrase", "Passphrase", "Your account password at the login screen.", False),
                                     ("pin", "PIN", "Confirms sensitive assistant actions. Set or change it with the first-run wizard (eternity-firstrun).", True),
                                     ("face", "Face", "Coming later: needs the on-device camera model.", False),
                                     ("voice", "Voice", "Coming later: needs the on-device voice model.", False)):
            sw = Gtk.Switch(active=key in cfg.unlock_methods or key == "passphrase")
            sw.set_sensitive(ok)
            sw.connect("notify::active", self.on_unlock)
            self.unlock[key] = sw
            root.pack_start(Row(title, hint, sw), False, False, 0)
        rerun = button("Run the first-run wizard again", "ghost", on_click=lambda: subprocess.Popen(["eternity-firstrun", "--reset"]))
        root.pack_start(rerun, False, False, 0)
        self.on_provider(self.prov)

    @staticmethod
    def section(text: str) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.pack_start(Gtk.Separator(), False, False, 0)
        box.pack_start(label(text, "kicker"), False, False, 0)
        return box

    def set_and_save(self, key, value):
        setattr(self.cfg, key, value)
        S.save(self.cfg)
        self.note.set_text(f"Changes apply instantly. {key.replace('_', ' ').capitalize()} updated.")

    def on_provider(self, combo):
        prov = combo.get_active_id() or "local"
        self.cfg.provider = prov
        if prov != "local":
            self.cfg.on_device_only = False
            self.ondevice.set_active(False)
        S.save(self.cfg)
        keyed = prov not in ("local",) + S.SIGNIN_PROVIDERS
        signin = prov in S.SIGNIN_PROVIDERS
        for w in (self.key_row, self.key_actions):
            w.set_visible(keyed); w.set_no_show_all(not keyed)
            if keyed:
                w.show_all()
        for w in (self.signin_row, self.signin_status, self.cc_model_row, self.cc_allow_box):
            w.set_visible(signin); w.set_no_show_all(not signin)
            if signin:
                w.show_all()
        if keyed:
            self.key_link.set_uri(P.PROVIDER_KEY_URLS[prov])
            self.key_entry.set_placeholder_text("A key is stored" if self.store.get(prov) else "No key yet")
        if signin:
            self.refresh_signin()
        self.note.set_text(f"Changes apply instantly. Assistant: {P.PROVIDER_LABELS[self.cfg.effective_provider()]}.")

    def on_cc_allow(self, *_):
        self.cfg.claude_code_allow = [t for t, cb in self.cc_checks.items() if cb.get_active()]
        S.save(self.cfg)
        self.note.set_text("Allow-list saved. Applies to the next question.")

    def refresh_signin(self, *_):
        self.cc = P.claude_code_status()
        ok = self.cc["signed_in"]
        self.signin_status.set_text(("Claude Code " + (self.cc["version"] or "") + ": " + self.cc["detail"]).strip())
        self.signin_btn.set_label("Signed in" if ok else "Sign in with your Claude account")
        self.signin_btn.set_sensitive(not ok)

    def on_signin(self):
        import subprocess
        subprocess.Popen(["eternity-signin"])
        GLib.timeout_add_seconds(5, self._poll_signin, 0)

    def _poll_signin(self, n):
        self.refresh_signin()
        if not self.cc["signed_in"] and n < 60:
            GLib.timeout_add_seconds(5, self._poll_signin, n + 1)
        return False

    def on_ondevice(self, sw, _p):
        self.cfg.on_device_only = sw.get_active()
        if sw.get_active() and self.cfg.provider != "local":
            self.prov.set_active_id("local")
        S.save(self.cfg)

    def on_key_saved(self, entry):
        key = entry.get_text().strip()
        prov = self.cfg.provider
        if key and prov != "local":
            self.store.set(prov, key)
            entry.set_text("")
            entry.set_placeholder_text("A key is stored")
            self.note.set_text(f"Key for {P.PROVIDER_LABELS[prov]} saved to the {self.store.backend}.")

    def on_key_forget(self):
        prov = self.cfg.provider
        if prov != "local":
            self.store.delete(prov)
            self.key_entry.set_placeholder_text("No key yet")
            self.note.set_text(f"Key for {P.PROVIDER_LABELS[prov]} forgotten.")

    def on_verbosity(self, scale):
        v = S.VERBOSITY[int(round(scale.get_value()))]
        if v != self.cfg.verbosity:
            self.set_and_save("verbosity", v)
            self.note.set_text(f"Verbosity {'lowered' if v == 'brief' else 'raised' if v == 'detailed' else 'set to normal'} — Eternity will answer {'in fewer words' if v == 'brief' else 'in more detail' if v == 'detailed' else 'normally'}.")

    def on_unlock(self, *_):
        methods = [k for k, sw in self.unlock.items() if sw.get_active()]
        self.set_and_save("unlock_methods", methods)

    def open_log(self):
        path = A.Audit().path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "a").close()
        subprocess.Popen(["xdg-open", path])


def main(argv=None) -> int:
    from . import guarded
    return guarded("settingsui", _main, argv)


def _main(argv=None) -> int:
    load_css()
    win = SettingsWindow(S.load(), S.SecretStore(lazy=True))
    win.show_all()
    if os.environ.get("ETERNITY_UI_SMOKE"):
        shot(win, "settings")
        win.verb.set_value(0)
        return 0
    Gtk.main()
    return 0
