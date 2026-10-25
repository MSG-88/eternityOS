# Eternity session on Hyprland (phase 3 slice 1, build 13) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 13 boots into a selectable "Eternity" Wayland session (Hyprland + the Quickshell shell) that renders the design's status strip, presence desktop, command bar with streamed answers and consent, lock screen and view-change effects at 125 % scale, fed by a Python daemon over a Unix socket, with XFCE still selectable; plus the first "deeper Claude Code" items.

**Architecture:** Hyprland is configured from generated files (`eternity-theme` turns `theme.toml` + `layout.toml` + `keys.toml` into `hyprland.conf`, `Theme.qml`, GTK CSS). `eternity-daemon` (Python, the existing `eternity` package) owns state, cards, metrics, the agent, consent and settings and speaks JSON lines on `$XDG_RUNTIME_DIR/eternity/daemon.sock`. `eternity-shell` (Quickshell, QML) owns every layer-shell surface and never computes anything per frame in script beyond property animations. All geometry is in design pixels times `k = min(W/1920, H/1080)` of the logical output.

**Tech Stack:** Debian 13 + trixie-backports (hyprland 0.55.2, quickshell 0.3.0, hypridle), Qt 6.8 Quick (Shapes, Effects), Python 3.13 stdlib (daemon), live-build, QEMU/TCG for VM evidence, `unittest` for host tests.

**Spec:** `docs/superpowers/specs/2026-10-25-eternity-08-phase3-design.md` (§4 shell, §4.4 budgets, §5.1 Claude Code, §13 calls, §15 owner answers).

## Global Constraints

- Every colour, radius, font, duration and size comes from the Nocturne tokens in `theme.toml` (bg `#161826`, surface `#232532`, text `#e9e9ed`, accent `#9184d9`, accent-300 `#d2cefd`, accent-400 `#b5abfc`, accent-600 `#796cbf`, accent-700 `#5d5294`, neutral-400 `#b2b6ca`, 500 `#9397ab`, 600 `#75798c`, 700 `#595d6c`, 800 `#3f424d`, 900 `#292b31`; radii 4/8/14; shadow-sm `0 0 0 1px #3f424d`; Inter 400/500, Michroma for wordmark and HUD labels, JetBrains Mono for logs). No literal hex in QML outside `Theme.qml`.
- Geometry in design pixels (1920×1080) × `k`; default output scale 1.25 (`layout.toml` `scale = 1.25`); must render at 1.0 and 1.5 too.
- No per-frame JavaScript or Python: animations are `NumberAnimation`/`RotationAnimation`/`SequentialAnimation` on properties; the Möbius mark is an `AnimatedSprite` from a baked atlas; sparklines and rings are `Shape` items updated at most once per second.
- No fake numbers: every readout is measured or hidden ("NPU" never shown unless `/sys/class/accel` has a device).
- Every agent action goes through `ActionBroker` consent + audit + undo, now rendered by the shell; sudo/pkexec/doas always refused.
- Python keeps the stdlib-only rule for `/usr/lib/eternity/py/eternity`.
- XFCE stays the default session in build 13; the Eternity session is selected by the kernel parameter `eternity.session=eternity` (tests) or the greeter's session menu (owner).
- Host tests run with `bash tools/dev/host-tests.sh`; UI smoke with `tools/dev/ui-smoke.sh`; new QML tests run offscreen (`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software`).

## Review Focus

1. **The daemon is not running** when the shell starts (crash, slow start): the shell must show the strip and the presence with "—" readouts and reconnect every 2 s, never a blank screen. Test in Task 5 (`test_shell_offline`).
2. **A workspace with windows**: the orbit cards hide, the core moves right or fades, nothing paints over windows. Test in Task 6 (`test_presence_window_state`).
3. **Consent arrives while another consent is open** (two tool calls in one Claude Code turn): queued, answered in order, never dropped as "declined". Test in Task 4 (`test_consent_queue`).
4. **Output scale change at runtime** (plugging HDMI at 1.0 while the panel is 1.25): `k` recomputes per screen, surfaces re-layout. Test in Task 5 (`test_k_per_screen`).
5. **The passphrase is wrong at the lock screen**: the field shakes, PAM is retried, the session stays locked; after 5 failures a 30 s delay. Test in Task 8 (`test_lock_backoff`).

---

### Task 1: Packages, session entry and the session launcher

**Files:**
- Modify: `config/package-lists/desktop.list.chroot` (append)
- Create: `config/archives/eternity-backports.pref.chroot`
- Create: `config/includes.chroot/usr/share/wayland-sessions/eternity.desktop`
- Create: `config/includes.chroot/usr/local/bin/eternity-session`
- Create: `config/includes.chroot/usr/lib/live/config/0032-eternity-session`
- Create: `config/hooks/normal/0460-session.hook.chroot`
- Modify: `tests/smoke.sh` (add `check_session`)
- Test: `tests/host/test_session_files.py`

**Interfaces:**
- Produces: `eternity-session` (sh) that exports `XDG_CURRENT_DESKTOP=Eternity XDG_SESSION_TYPE=wayland QT_QPA_PLATFORM=wayland QT_WAYLAND_DISABLE_WINDOWDECORATION=1 MOZ_ENABLE_WAYLAND=1 ETERNITY_SESSION=1`, runs `eternity-theme render` (Task 2), then `exec Hyprland --config "$XDG_CONFIG_HOME/eternity/generated/hyprland.conf"`; when `/sys/class/drm/card*/device/driver` resolves to no hardware driver (QEMU `bochs`/`virtio_gpu` without GL) it also exports `WLR_RENDERER_ALLOW_SOFTWARE=1 AQ_NO_MODIFIERS=1 LIBGL_ALWAYS_SOFTWARE=1`.
- Produces: kernel parameter `eternity.session=<name>` honoured by the live-config component (writes `user-session=<name>` into `/etc/lightdm/lightdm.conf.d/20-session.conf`).

- [ ] **Step 1: Write the failing test** `tests/host/test_session_files.py`

```python
def test_session_entry():
    d = read("config/includes.chroot/usr/share/wayland-sessions/eternity.desktop")
    assert "Exec=eternity-session" in d and "Name=Eternity" in d and "DesktopNames=Eternity" in d
def test_packages():
    pk = read("config/package-lists/desktop.list.chroot")
    for p in ("hyprland", "quickshell", "hypridle", "xdg-desktop-portal-hyprland", "xdg-desktop-portal-gtk",
              "qml6-module-qtquick-shapes", "qml6-module-qtquick-effects", "qml6-module-qt5compat-graphicaleffects",
              "qt6-wayland", "wl-clipboard", "grim", "slurp", "fonts-jetbrains-mono"):
        assert re.search(rf"^{re.escape(p)}$", pk, re.M), p
def test_backports_pin():
    pref = read("config/archives/eternity-backports.pref.chroot")
    assert "Package: hyprland quickshell hypridle xdg-desktop-portal-hyprland hyprland-protocols hyprutils* hyprlang* hyprcursor* hyprgraphics* aquamarine*" in pref
    assert "Pin: release n=trixie-backports" in pref and "Pin-Priority: 600" in pref
def test_session_script_parses():
    subprocess.run(["sh", "-n", "config/includes.chroot/usr/local/bin/eternity-session"], check=True)
    s = read("config/includes.chroot/usr/local/bin/eternity-session")
    assert "XDG_CURRENT_DESKTOP=Eternity" in s and "eternity-theme render" in s and "exec Hyprland" in s
def test_live_config_component():
    s = read("config/includes.chroot/usr/lib/live/config/0032-eternity-session")
    assert "eternity.session=" in s and "20-session.conf" in s
```

- [ ] **Step 2: Run** `bash tools/dev/host-tests.sh test_session_files.py` → FAIL (files missing)
- [ ] **Step 3: Create the files.** `eternity.desktop`: `[Desktop Entry] Name=Eternity Comment=The presence is the desktop Exec=eternity-session Type=Application DesktopNames=Eternity`. The hook enables nothing new (Hyprland runs per user) but creates `/etc/xdg/eternity/` and `chmod 755` the launcher, and prints `Hyprland --version | head -1` and `quickshell --version` into the build log. `check_session` in smoke: session file present, `command -v Hyprland quickshell hypridle`, `eternity-theme render --check` exits 0 (Task 2), `/usr/share/eternity/shell/shell.qml` present (Task 5). The live-config component mirrors `0031-eternity-user` (Cmdline/Init/Config; state file `eternity-session`).
- [ ] **Step 4: Run** the test → PASS; run `bash -n` on the hook.
- [ ] **Step 5: Commit** `feat(session): Hyprland + Quickshell packages, Eternity wayland session, eternity.session= switch`

### Task 2: `eternity-theme`: tokens and layout → Hyprland config, Theme.qml, GTK CSS

**Files:**
- Create: `config/includes.chroot/usr/share/eternity/theme.toml`, `layout.toml`, `keys.toml`, `hyprland.base.conf`
- Create: `config/includes.chroot/usr/lib/eternity/py/eternity/theme.py`
- Create: `config/includes.chroot/usr/local/bin/eternity-theme`
- Test: `tests/host/test_theme.py`

**Interfaces:**
- Produces: `theme.load(user_dir=None) -> dict` (defaults from `/usr/share/eternity/*.toml` merged with `~/.config/eternity/{theme,layout,keys}.toml`, `tomllib`); `theme.render(out_dir) -> list[str]` writing `hyprland.conf`, `Theme.qml`, `gtk.css`; `theme.validate(cfg) -> list[str]` (errors; empty = ok). CLI: `eternity-theme render [--check]` (writes to `$XDG_CONFIG_HOME/eternity/generated/`, `--check` only validates; exit 1 on errors).
- `theme.toml` keys: `[color] bg surface text accent accent_300 accent_400 accent_600 accent_700 n400 n500 n600 n700 n800 n900`, `[radius] sm=4 md=8 lg=14`, `[font] body="Inter" tech="Michroma" mono="JetBrains Mono"`, `[motion] enter_ms=700 draw_ms=800 pop_ms=600 sweep_ms=800 decode_cps=28 reduced=false glow=1.0`.
- `layout.toml` keys: `scale=1.25`, `strip_height=44`, `bar=[560,950,800,54]`, `gaps=12`, `border=1`, `rounding=8`, `orbit=[440,270]`, `cards=["today","system","eternity","recent","install","focus","nowplaying"]`, `blur_namespaces=["eternity-bar","eternity-lock"]`.
- `keys.toml`: `[bind] launcher="SUPER, code:133" ask="SUPER, space" files="SUPER, F" monitor="SUPER, M" settings="SUPER, comma" lock="SUPER, L" close="SUPER, Q" terminal="SUPER, Return" home="SUPER, Home"` plus workspaces 1-9 and focus/move arrows.
- `Theme.qml` is a `pragma Singleton` `QtObject` exposing `color.*`, `radius.*`, `font.*`, `motion.*` and `readonly property real scale`.

- [ ] **Step 1: Write the failing tests** `tests/host/test_theme.py`

```python
def test_defaults_render(tmp):
    files = theme.render(tmp)
    hypr = read(tmp/"hyprland.conf"); qml = read(tmp/"Theme.qml"); css = read(tmp/"gtk.css")
    assert "monitor=,preferred,auto,1.25" in hypr
    assert "col.active_border = rgb(9184d9)" in hypr and "col.inactive_border = rgb(3f424d)" in hypr
    assert "gaps_in = 6" in hypr and "gaps_out = 12" in hypr and "rounding = 8" in hypr
    assert "bind = SUPER, space, exec, eternity-ask --show" in hypr
    assert 'layerrule = blur, eternity-bar' in hypr and "exec-once = eternity-daemon" in hypr and "exec-once = quickshell -c eternity" in hypr
    assert 'readonly property color accent: "#9184d9"' in qml and "pragma Singleton" in qml and "readonly property int enterMs: 700" in qml
    assert "@define-color accent #9184d9;" in css
def test_user_override(tmp, home):
    write(home/".config/eternity/theme.toml", '[color]\naccent = "#2ec4b6"\n'); write(home/".config/eternity/layout.toml", "scale = 1.0\n")
    theme.render(tmp)
    assert "monitor=,preferred,auto,1" in read(tmp/"hyprland.conf") and 'accent: "#2ec4b6"' in read(tmp/"Theme.qml")
def test_validate_rejects_bad_values():
    assert theme.validate({"color": {"accent": "teal"}}) and theme.validate({"layout": {"scale": 9}})
def test_cli_check(home):
    assert subprocess.run([sys.executable, "-c", "from eternity import theme; raise SystemExit(theme.main(['render', '--check']))"], env=env).returncode == 0
```

- [ ] **Step 2: Run** `bash tools/dev/host-tests.sh test_theme.py` → FAIL
- [ ] **Step 3: Implement** `theme.py` (`load`, `validate`, `render`, `main`) and the four default files. `hyprland.base.conf` is a template with `${...}` placeholders filled by `string.Template`: general (gaps/border/colours), decoration (rounding 8, blur size 6 passes 2 only for `layerrule`), animations (`bezier = enter, 0.33, 1, 0.68, 1` → windows 0.7 s, workspaces 0.8 s slide, layers fade 0.3 s; `animations:enabled = !reduced`), `misc { disable_hyprland_logo = true; vfr = true; vrr = 0 }`, `input { kb_options = "" touchpad { natural_scroll = true } }`, `gestures { workspace_swipe = true }`, `windowrulev2 = noborder, class:^(eternity-)`, `exec-once` lines, binds from `keys.toml`.
- [ ] **Step 4: Run** tests → PASS
- [ ] **Step 5: Commit** `feat(theme): eternity-theme renders Hyprland config, Theme.qml and GTK css from the Nocturne tokens`

### Task 3: `eternity-daemon`: state hub on a Unix socket

**Files:**
- Create: `config/includes.chroot/usr/lib/eternity/py/eternity/daemon.py`
- Create: `config/includes.chroot/usr/local/bin/eternity-daemon`
- Modify: `config/includes.chroot/usr/lib/eternity/py/eternity/cards.py` (add `latency_sample()` reader of `$XDG_RUNTIME_DIR/eternity/latency.json` written by the shell)
- Test: `tests/host/test_daemon.py`

**Interfaces:**
- Protocol: one JSON object per line. Request `{"id": int, "method": str, "params": {}}`; response `{"id": int, "result": {...}}` or `{"id": int, "error": str}`; event `{"event": str, "data": {...}}`. Socket path `os.environ["XDG_RUNTIME_DIR"]/eternity/daemon.sock` (override `ETERNITY_SOCK`), mode 0600, `SO_PEERCRED` must match our uid.
- Methods: `state.get` → `{clock, date, battery, network, ai, memory, cpu, latency_ms, live, user_name, notifications_held}`; `cards.get` → `{cards: [{id, kicker, title, body, meta, actions}]}` (ids from `layout.cards`, absent sources omitted); `ask.start {text}` → `{run_id}` then events `ask.text {run_id, delta}`, `ask.status`, `ask.action {name,args,ok,summary,undoable}`, `ask.done {run_id, readout, cost_usd?}`; `ask.cancel {run_id}`; `ask.undo` → `{message}`; `consent.reply {consent_id, ok, pin?}`; event `consent.request {consent_id, tool, risk, description, need_pin}`; `settings.get` / `settings.set {key, value}`; `hw.summary`; `metrics.sample` → `{cpu, mem_gb, ai_tps, latency_ms, dropped_frames}`; `session.lock_info` → `{greeting, name, since_count}`; `launcher.index {query}` (wraps `launcher_index`).
- `daemon.Daemon(provider_factory=None, sock_path=None).serve_forever()`; `daemon.Client(sock_path).call(method, **params)` (used by tests and CLIs); events are pushed to every connected client that sent `subscribe`.

- [ ] **Step 1: Write the failing tests** `tests/host/test_daemon.py` (start the daemon in a thread on a temp socket with a scripted provider as in `test_agent.py`)

```python
def test_state_and_cards(self): r = c.call("state.get"); assert set(r) >= {"clock", "battery", "network", "ai", "live"}; assert isinstance(c.call("cards.get")["cards"], list)
def test_ask_streams_and_consent(self):
    sub = subscriber(); run = c.call("ask.start", text="save a note")["run_id"]
    ev = sub.wait("consent.request"); assert ev["tool"] == "write_note" and ev["risk"] == "change"
    c.call("consent.reply", consent_id=ev["consent_id"], ok=True)
    kinds = [e["event"] for e in sub.collect_until("ask.done")]; assert "ask.text" in kinds and "ask.action" in kinds
def test_consent_queue(self): two tool calls in one turn → two consent.request events with distinct ids, both answerable in order, both actions executed
def test_declined_consent(self): reply ok=False → ask.action with ok False and summary "declined by the user"
def test_rejects_other_uid(self): monkeypatch peer uid → connection closed
def test_settings_roundtrip(self): c.call("settings.set", key="verbosity", value="brief"); assert c.call("settings.get")["verbosity"] == "brief"
```

- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** `daemon.py`: `selectors`-based single thread for sockets, one worker thread per `ask.start` (the existing `Agent` with a consent callback that emits `consent.request` and blocks on a `threading.Event` keyed by `consent_id`; PIN verified with `firstrun.verify_pin`), `cards.py`/`hw.py`/`settings.py` reused; a 1 s metrics ticker emitting `metrics.sample` to subscribers. `eternity-daemon` wrapper like the other bins; `--once METHOD` for debugging.
- [ ] **Step 4: Run** tests → PASS; also `python3 -m unittest tests/host/test_agent.py` still PASS
- [ ] **Step 5: Commit** `feat(daemon): eternity-daemon state hub (JSON lines over a Unix socket) with ask streaming and shell-rendered consent`

### Task 4: `eternity-mcp` and the CLIs talk to the daemon

**Files:**
- Modify: `config/includes.chroot/usr/lib/eternity/py/eternity/mcp.py` (`make_consent`: when `ETERNITY_SESSION=1` or the socket exists, consent goes through `daemon.Client` → `consent.request`; GTK fallback stays for XFCE)
- Modify: `config/includes.chroot/usr/local/bin/eternity-ask` (`--show` sends `ask.show` to the daemon when the socket exists; otherwise the GTK bar as today)
- Test: extend `tests/host/test_mcp.py` (`test_consent_via_daemon`) and `tests/host/test_daemon.py` (`test_consent_queue` already covers ordering)

- [ ] **Step 1: Write the failing test**: start a daemon with a subscriber that auto-replies `ok=True` to every `consent.request`; `ETERNITY_SOCK` set; `mcp.make_consent(cfg)(builtin_tool("Bash", {"command": "ls"}), {...})` returns True and the daemon received the request with `tool == "Bash"`.
- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** `daemon_consent(cfg)` in `mcp.py` (new helper `daemon.request_consent(tool, args, need_pin) -> bool` on the client side, blocking with a 10 min timeout → False) and choose it first in `make_consent`.
- [ ] **Step 4: Run** `test_mcp.py` and `test_daemon.py` → PASS
- [ ] **Step 5: Commit** `feat(mcp): consent through the daemon in the Eternity session`

### Task 5: The shell skeleton and the status strip

**Files:**
- Create: `config/includes.chroot/usr/share/eternity/shell/shell.qml` (ShellRoot: per-screen `Variants`), `Daemon.qml` (singleton: `Socket` client, `state`, `metrics`, `connected`, `call()`), `Theme.qml` (fallback copy; the generated one wins via `QML_IMPORT_PATH`), `Strip.qml`, `Mobius.qml` (AnimatedSprite), `Wordmark.qml`, `Dump.qml` (geometry dump + screenshot when `ETERNITY_SHELL_DUMP` is set)
- Create: `config/includes.chroot/usr/share/eternity/shell/assets/mobius-atlas.png` (generated by `branding/render.py --atlas`, 48 frames × 352 px, 8 columns) and `wordmark-e.svg`
- Modify: `branding/render.py` (add `--atlas`)
- Create: `tests/host/test_shell_render.sh` + `tests/host/shell_harness.qml` (loads the shell's components in a plain `Window` of 1536×864 with `k` forced, writes the dump)
- Test: `tests/host/test_shell_render.sh` (asserts via `python3 -c` on the dump JSON)

**Interfaces:**
- `Daemon.qml`: `property bool connected`, `property var state` (last `state.get`), `property var metrics`, `function call(method, params, cb)`, `signal event(string name, var data)`; reconnects every 2000 ms; subscribes on connect.
- `Scale.qml` singleton: `function k(screen) { return Math.min(screen.width / 1920, screen.height / 1080) }`.
- Dump format: `{"screen": [w,h], "k": k, "items": {"strip": [x,y,w,h], "clock": [...], "mark": [...], ...}}` plus `strip.png`.
- `Strip.qml`: `PanelWindow` anchored top, `exclusiveZone: 44*k`, namespace `eternity-strip`; left mark 20k + wordmark 11k/0.2 em; centre clock; right items with 22k gaps: `● live · N ms` (from `metrics.latency_ms`, "—" when null), AI readout (`state.ai.label`), network, battery %.

- [ ] **Step 1: Write the failing test** `tests/host/test_shell_render.sh`: runs `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software ETERNITY_SHELL_DUMP=$out quickshell -p tests/host/shell_harness.qml` with no daemon, then asserts: `k == 0.8`, strip height `round(44*0.8)=35`, clock centred within 2 px of `screen.w/2`, mark at x `28*0.8`, readouts show "—", and `test_shell_offline`: `connected == false` and no error lines in stderr; `test_k_per_screen`: harness run twice with 1920×1080 and 1536×864 gives k 1.0 and 0.8.
- [ ] **Step 2: Run** `bash tests/host/test_shell_render.sh` → FAIL (no shell)
- [ ] **Step 3: Implement** the QML files and the atlas generator. Rules: all sizes `* Scale.k(screen)`; fonts from `Theme`; `Socket { path: ...; parser: SplitParser { onRead: ... } }` from `Quickshell.Io`; the strip is `PanelWindow { anchors { top: true; left: true; right: true } }` from `Quickshell.Wayland` with `WlrLayershell.namespace: "eternity-strip"`. Verify type names against the installed Quickshell with `qmlls`-free check: `quickshell -p` loads without "is not a type" errors (the harness run).
- [ ] **Step 4: Run** the test → PASS; attach `strip.png` to `docs/screenshots/build13-strip-offscreen.png`
- [ ] **Step 5: Commit** `feat(shell): Quickshell skeleton, daemon client, status strip at design geometry`

### Task 6: The presence desktop (background layer)

**Files:**
- Create: `shell/Presence.qml` (PanelWindow `layer: WlrLayer.Background`, full screen, no exclusive zone), `Core.qml` (rings, ticks, glow, Mobius), `OrbitCards.qml`, `Card.qml`, `Hud.qml` (corner brackets + scan + decoding label), `Sweep.qml` (grid flash + scan line)
- Modify: `shell_harness.qml` (adds Presence), `tests/host/test_shell_render.sh`

**Interfaces:**
- `Core { x, y, s, fast, glow }` draws at design (960,540) scaled `s`; rings r 92/134/176/214 as `Shape` with `strokeDashArray` fractions `[0.62,0.16,0.3,0.08]` of circumference, widths 1.25/2.5/1.25/1.25, colours a700/accent/a700/n600, `RotationAnimation` `±(10+7i)` deg/s; 72 ticks as one `Shape` rotating 1.5 deg/s; glow `RadialGradient` breathing with `energy`; Mobius `AnimatedSprite` 176k, 48 frames at 12 fps (one loop per 4 s, matching the design's 0.22 loops/s light travel).
- `OrbitCards`: cards from `Daemon.state.cards` on the ellipse 440×270 at angles −90/0/90/180 + `rot` (2.5 deg/s), width 300k, `Card` = kicker 10/0.1 em accent, title 17/500, body 13 at 80 %, meta 11 at 50 %, radius 8, surface, shadow-sm; `dim` to 0.1 while an ask runs; hidden when `Hyprland.focusedMonitor.activeWorkspace` has toplevels (Quickshell.Hyprland) and `windowState` moves the core to (1600,540,0.38) when free width ≥ 420k else fades.
- `Hud { x,y,w,h,label,color }` and `Sweep { }` with durations from `Theme.motion`; `Sweep.play()` on `Hyprland` workspace change and on surface open.

- [ ] **Step 1: Extend the render test**: with a fake daemon state (harness sets `Daemon.state` to the four design cards), assert core centre at `(960k, 540k)` ±1, four cards of width `300k` at the four angles (`rot` frozen at 0 in the harness), caption at y `900k`; `test_presence_window_state`: harness sets `windowState = "windows"` → cards `visible == false`, core at `(1600k, 540k)`; `Hud` brackets 22k long; a `presence.png`.
- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** the files (no `Timer` per frame; `Sweep` is a `SequentialAnimation` of two overlays; `Hud` label decode is a `NumberAnimation` on a progress property with the decoded string computed in one `onProgressChanged` handler at 28 steps/s, which is the only script that runs during an animation and only for 0.35 s per label).
- [ ] **Step 4: Run** → PASS; save `presence.png` under `docs/screenshots/`
- [ ] **Step 5: Commit** `feat(shell): presence desktop (core, orbit cards, HUD frame, sweeps) at design geometry`

### Task 7: Command bar, answer surface and consent dialog

**Files:**
- Create: `shell/Bar.qml` (PanelWindow top layer, keyboard focus `OnDemand`, namespace `eternity-bar`, geometry 800×54 at (560,950)), `Answer.qml` (reply at (560,650) w 800, rule at 620, thinking line 580, readout top-right (right 40, top 60), action cards, caret), `Consent.qml` (Nocturne dialog: kicker "ALLOW <TOOL>?", description, risk line, PIN field when needed, "Not now"/"Allow")
- Modify: `Daemon.qml` (ask helpers), `shell.qml` (Super+Space → daemon `ask.show` event toggles the bar; Esc hides)
- Test: `tests/host/test_shell_render.sh` additions + `tests/host/test_daemon.py::test_ask_show_event`

- [ ] **Step 1: Write the failing tests**: render test with a fake `ask` run: bar at `(560k,950k,800k,54k)`, placeholder text and chip "Super Space" present, focused state shows the accent ring; after fake events `ask.text` ×3 the answer text equals the concatenation and the caret is visible until `ask.done`; a fake `consent.request` shows `Consent` with the kicker `ALLOW WRITE NOTE?` and the PIN field only when `need_pin`; `test_ask_show_event`: `c.call("ask.show")` emits event `ask.show` to subscribers.
- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement.** Typing sends `ask.start`; `/` and `>` prefixes behave as in `ui/ask.py` (`/undo`, `/clear`, `/settings`, `/local`, `/help`; `>` runs `run_command` through consent). Readout shows `Daemon` metrics; provider label from `state.ai.label` ("via Claude Code" when `claude_code`).
- [ ] **Step 4: Run** → PASS; screenshots `bar.png`, `answer.png`, `consent.png`
- [ ] **Step 5: Commit** `feat(shell): command bar, streamed answers, action cards and consent in QML`

### Task 8: Lock screen and idle

**Files:**
- Create: `shell/Lock.qml` (`WlSessionLock` from `Quickshell.Wayland`; scene: mark 176k at (960,420), "Good <part of day>, <name>." 52/500 at y 640, passphrase field, "Other ways to unlock" chips Passphrase/PIN at bottom 88/56, "n things since you left"), `PamAuth.qml` (`Quickshell.Services.Pam` `PamContext { config: "login" }`), PIN path via daemon `pin.verify`
- Create: `config/includes.chroot/usr/share/eternity/hypridle.conf` (lock at 300 s on battery / 900 s on mains via `eternity-lock`, dpms off +60 s, `before_sleep_cmd = eternity-lock`)
- Create: `config/includes.chroot/usr/local/bin/eternity-lock` (sends `session.lock` to the daemon → event → shell locks)
- Modify: `daemon.py` (`pin.verify {pin}`, `session.lock`, `session.lock_info` with `since_count` from the notification store, greeting by hour)
- Test: `tests/host/test_daemon.py::test_lock_info_and_pin`, render test `lock.png` with geometry; `test_lock_backoff` (QML state machine test in the harness: 5 wrong answers → `backoffMs == 30000`)

- [ ] **Step 1: Write the failing tests** (as listed; greeting "Good evening" for hour 21, "Good morning" < 12, "Good afternoon" < 18).
- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement.** Hyprland `bind = SUPER, L, exec, eternity-lock`; `exec-once = hypridle -c /usr/share/eternity/hypridle.conf` in the base config (Task 2 template gains the line).
- [ ] **Step 4: Run** → PASS
- [ ] **Step 5: Commit** `feat(shell): session lock scene with PAM passphrase, PIN and idle lock`

### Task 9: Visual and smoke integration for the Eternity session

**Files:**
- Modify: `tests/run-qemu-visual.sh` (`--session eternity` adds `eternity.session=eternity` to the kernel line via the GRUB edit the runner already uses for `eternity.test`; after login waits 25 s (×SCALE) and shoots `e-desktop.png`, opens the bar with Super+Space → `e-ask.png`, types a question to the scripted local model → `e-answer.png`, `Super+L` → `e-lock.png`, types the passphrase → `e-unlocked.png`; then `Ctrl-Alt-T` → `hyprctl layers; hyprctl monitors | grep scale; ps -o rss,comm -C quickshell,eternity-daemon` → `e-terminal.png`)
- Modify: `tests/smoke.sh` (`check_session`: files from Task 1, `eternity-theme render --check`, `quickshell -p /usr/share/eternity/shell/shell.qml --version`-free load test via `QT_QPA_PLATFORM=offscreen timeout 20 quickshell -p ... ` with `ETERNITY_SHELL_DUMP` producing a dump; `Hyprland --version`)
- Modify: `tools/dev/chain-build13.sh` (new: build, visual XFCE, visual `--session eternity`, smoke, install, fallback, Secure Boot, BIOS, USB)
- Test: the runs themselves; `CHECK session: PASS` line

- [ ] **Step 1: Add** `check_session` and run it in the chroot checker (`tests/run-chroot-checks.sh`) once the packages are in a built image; until then run `bash -n tests/smoke.sh`.
- [ ] **Step 2: Extend** the visual runner; `bash -n`.
- [ ] **Step 3: Write** `tools/dev/chain-build13.sh` from `chain-build12.sh` with the extra visual run; commit; create `out/build13.go` only after Tasks 1-8 are merged.
- [ ] **Step 4: Commit** `test: Eternity session visual run, check_session, build 13 chain`

### Task 10: Deeper Claude Code

**Files:**
- Modify: `settings.py` (`claude_code_allow: list[str]` default `[]`; `claude_code_model` validated against `("sonnet","opus","haiku")`), `providers.py` (`ClaudeCodeProvider.allowed_tools()` adds `cfg.claude_code_allow`; `Metrics.cost_usd` from `result.total_cost_usd`; `readout()` appends `$0.00` when set; `sessions.json` in `state_dir()` records `{session_id, started, first_question}` per run, `ClaudeCodeProvider.sessions()` lists them, `resume(session_id)`), `agent.py` (`/resume` quick command plumbing via `Agent.resume(session_id)`), `ui/ask.py` + `Bar.qml` (`/sessions`, `/resume N`, `/model sonnet|opus|haiku`), `ui/settingsui.py` + daemon `settings.set` (allow-list editor: checkboxes for Read/Glob/Grep/WebSearch/WebFetch/Edit/Write/Bash and the Eternity read-only tools; model picker)
- Create: `config/includes.chroot/usr/lib/eternity/claude-hook` (PreToolUse hook: reads the JSON on stdin, appends `{ts, tool, args, decision: "interactive", via: "claude-code-terminal"}` to `~/.local/state/eternity/actions.log`; exits 2 with a message when `escalates_privileges`), `config/includes.chroot/usr/share/applications/eternity-claude-terminal.desktop` ("Claude Code (terminal, expert mode: outside Eternity's consent and undo)")
- Modify: `config/includes.chroot/etc/claude-code/managed-settings.json` (`"hooks": {"PreToolUse": [{"matcher": "", "hooks": [{"type": "command", "command": "/usr/lib/eternity/claude-hook"}]}]}`)
- Test: `tests/host/test_claude_code.py` (cost parsed from a `result` with `total_cost_usd: 0.0123` → `readout()` contains `$0.01`; `claude_code_allow=["Edit"]` appears in `--allowedTools`; `sessions()` lists the recorded run; `--resume` uses the chosen id), `tests/host/test_claude_hook.py` (stdin `{"tool_name":"Bash","tool_input":{"command":"sudo id"}}` → exit 2 and no log entry; `{"tool_name":"Edit",...}` → exit 0 and one log line with `via == "claude-code-terminal"`), `tests/host/test_settings.py` (model validation)

- [ ] **Step 1: Write the failing tests** as listed.
- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** (hook in POSIX sh + python3 one-liner, stdlib only).
- [ ] **Step 4: Run** `bash tools/dev/host-tests.sh` → all PASS; `tools/dev/ui-smoke.sh` → PASS
- [ ] **Step 5: Commit** `feat(claude-code): allow-list, model picker, cost readout, sessions, audit hook for the terminal tile`

### Task 11: Build 13, results, notes

- [ ] **Step 1:** `touch /srv/eternity-build/out/build13.go` path is not used; instead start `tools/dev/chain-build13.sh` detached (`tools/dev/start-chain13.sh`, same shape as `start-resume11.sh`) once build 12's chain has printed `BUILD12 DONE`.
- [ ] **Step 2:** Read `build13-run.log`; copy `tests/out/build13/e-*.png` to `docs/screenshots/`; append the results and the dump geometry to `docs/build-notes.md`; update `docs/backlog.md` section 5 marks.
- [ ] **Step 3:** If the Eternity session fails to start under TCG (no `e-desktop.png` with the strip), switch the VM run to labwc (`eternity-session --compositor labwc`, config generated from the same tokens) as §13.3 allows, and record it.
- [ ] **Step 4:** Commit `docs: build 13 results`; rewrite the stick when the chain is green; ask the owner for laptop time (spec §14 Q7).

---

## Self-review notes

- Spec coverage for this slice: §4.1 platform (T1, T2), §4.2 strip/core/home/bar/ask/HUD/sweeps/boot-log-not-in-scope (Plymouth unchanged), §4.3 keys (T2), §4.4 budgets measured only in T9 terminal shot and the latency file (full measurement on the laptop; the Monitor page is slice 2), §4.5 architecture (T3-T5), §5.1 deeper Claude Code (T10), §13.1 windows state (T6), §13.2 PIN scope (T8), §13.5 expert tile hook (T10), §15.6 scale (T2, T5). Out of this slice: greeter replacement, launcher ring, Files/Monitor QML, Settings pages, persistence, customisation UI, Codex.
- Names used across tasks: `Daemon.call/state/metrics/event`, `Scale.k`, `Theme.*`, `theme.render/validate/load`, daemon methods as listed in T3; T4 and T7 use them unchanged.
