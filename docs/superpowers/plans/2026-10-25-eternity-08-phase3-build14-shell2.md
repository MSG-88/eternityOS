# Eternity shell, slice 2 (build 14): greeter, launcher ring, notifications, Settings pages, Monitor

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 14 replaces the stock greeter with the Eternity unlock scene, adds the launcher ring (Super released alone) and the window ring (Super+Tab), a notification daemon with cards and OSDs, the QML Settings pages (Eternity, Assistant, Devices, Network, Sound, Power, Appearance, Keys) and the Monitor page, all fed by the daemon and the Quickshell services, with the same offscreen render tests and the VM visual run as slice 1.

**Architecture:** Same split as slice 1: `eternity-daemon` (Python) holds state, settings and the assistant; the Quickshell shell owns the surfaces. New in this slice: Quickshell's own services are used directly from QML where they are the source of truth (Notifications server, UPower, Pipewire, Networking, Mpris, Greetd); the daemon gains a notification store (`notifications.jsonl`, held/seen counts for the Focus card and the lock screen) and the Settings schema the QML pages render. The greeter is `greetd` running `cage -s -- quickshell -c eternity-greeter` with a greeter-only config that reuses `LockContent`.

**Tech Stack:** as slice 1 (Hyprland 0.55, Quickshell 0.3, Qt Quick 6.8, Python 3.13), plus greetd 0.10, cage, Quickshell services (Notifications, UPower, Pipewire, Networking, Mpris, Greetd).

**Spec:** `docs/superpowers/specs/2026-10-25-eternity-08-phase3-design.md` (§4.2 launcher/monitor/settings/first run/unlock, §4.3 navigation, §4.5, §8 sections table, §9, §13.2, §15).

## Global Constraints

- Everything from the slice 1 plan's Global Constraints (tokens only, design px × k, no per-frame script, no fake numbers, consent/audit/undo for every agent action, stdlib Python, XFCE stays selectable, tests run with `tools/dev/t.sh`, `tools/dev/ui-smoke.sh`, `tools/dev/shell-render.sh`).
- The greeter never shows personal data before login (spec §13.2): no "n things since you left", no user name beyond the account list; PIN is not a login credential.
- Notifications: the daemon implements nothing of the D-Bus protocol itself; Quickshell's `NotificationServer` is the only org.freedesktop.Notifications owner in the Eternity session (XFCE keeps xfce4-notifyd through `OnlyShowIn`).
- Every Settings control writes through `settings.set` (daemon) or `eternity-theme`'s TOML files; no control stores state only in the shell.
- Honest sources: Monitor's "AI" panel shows tok/s from the last answer or "idle"; "NPU" appears only when `/sys/class/accel/accel*` exists; input latency is `Latency.p95`.

## Review Focus

1. **greetd fails to start the greeter** (cage or quickshell missing, config error): the system must fall back to lightdm or a TTY login, never a black screen. Test in Task 1 (`test_greeter_fallback`).
2. **A notification storm** (50 notifications in a second): at most three cards on screen, the rest held and counted, no per-notification window. Test in Task 4 (`notify-storm` scenario).
3. **Launcher filter with no match**: shows "No match" and Enter does nothing; Esc closes. Test in Task 2 (`launcher-nomatch`).
4. **Settings page with the daemon down**: controls disabled with a clear line, nothing pretends to save. Test in Task 6 (`settings-offline`).
5. **Monitor with no battery/GPU/AI model**: panels hide or show "—", never a zero that looks real. Test in Task 7 (`monitor-bare`).

---

### Task 1: Greeter (greetd + cage + a greeter-only shell config)

**Files:**
- Modify: `config/package-lists/desktop.list.chroot` (+ `greetd`, `cage`)
- Create: `config/includes.chroot/etc/greetd/config.toml`, `config/includes.chroot/usr/share/eternity/greeter/shell.qml` (+ qmldir importing `../shell` components by relative path is not allowed: copy `LockContent.qml`, `Mobius.qml`, `Theme.qml`, `Geometry.qml`, `Wordmark.qml` at build time via the hook, or make the greeter config a symlink farm), `config/includes.chroot/usr/local/bin/eternity-greeter`
- Modify: `config/hooks/normal/0460-session.hook.chroot` (enable greetd only when `eternity.greeter=eternity` is on the kernel line? No: greetd is enabled when the Eternity session is the default; build 14 keeps lightdm default and adds `eternity.greeter=greetd` as the kernel switch handled by the live-config component `0032`), `config/includes.chroot/usr/lib/live/config/0032-eternity-session`
- Test: `tests/host/test_session_files.py` (`test_greeter_files`, `test_greeter_fallback`), render scenario `greeter`

**Interfaces:**
- `GreeterContent.qml`: the lock scene without personal data: account list (from `getent passwd` filtered to uid ≥ 1000 by the greeter script into `/run/eternity-greeter/users.json`), passphrase field, session chooser (Eternity / Eternity Classic). Uses `Quickshell.Services.Greetd` (`Greetd.createSession(user)`, `respond(password)`, `launch(["eternity-session"])`); on failure shakes and retries like `LockContent`.
- `greetd/config.toml`: `[terminal] vt = 7`, `[default_session] command = "cage -s -- eternity-greeter" user = "_greetd"`.
- `eternity-greeter`: writes users.json, `exec quickshell -p /usr/share/eternity/greeter/shell.qml`; if quickshell exits non-zero within 5 s, `exec agreety --cmd eternity-session` (text fallback shipped with greetd).

- [ ] **Step 1: Write the failing tests**: files exist and parse; `config.toml` names cage and eternity-greeter; the live-config component writes `/etc/greetd` only on `eternity.greeter=greetd` and otherwise leaves lightdm enabled (`test_greeter_fallback`: the component text disables lightdm only inside the `greetd` branch); render scenario `greeter` with two fake users: account list present, no "since you left", field placeholder "Passphrase".
- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** (GreeterContent is LockContent with `greeter: true` hiding the since line and PIN chip and adding the account list and session chooser; the hook copies the shared QML files into `/usr/share/eternity/greeter/` at build time so Quickshell's config-root rule holds).
- [ ] **Step 4: Run** → PASS; `bash -n`
- [ ] **Step 5: Commit** `feat(greeter): greetd + cage running the Eternity unlock scene (kernel switch eternity.greeter=greetd)`

### Task 2: Launcher ring and window ring

**Files:**
- Create: `shell/LauncherContent.qml` (ring of 64k tiles on the 1.35r×r ellipse, r 150→350 easeOutBack with 70 ms stagger, "Type to filter · <query>" at y 100, pagination 12 per ring, Enter launches, Esc closes), `shell/Launcher.qml` (overlay PanelWindow like Bar: Overlay layer, exclusive keyboard while shown), `shell/WindowRing.qml` (same ring over `Hyprland.toplevels` of the focused monitor, title + app id; release of Super selects: `GlobalShortcut` from `Quickshell.Hyprland` with `name: "window-ring"`; Hyprland bind `bind = SUPER, Tab, global, quickshell:window-ring`)
- Modify: `keys.toml` (`[bindr] launcher = "SUPER, Super_L"` already; add `[global] window_ring = "SUPER, Tab"` → `bind = SUPER, Tab, global, quickshell:window-ring`), `theme.py` (emit global binds), `eternity-launcher` (`--show` → daemon `launcher.show` event like `ask.show`), `daemon.py` (`launcher.show`), `shell.qml`
- Test: render scenarios `launcher` (12 tiles at the ellipse positions, tile 64k), `launcher-filter` (query "fil" → Files first and selected), `launcher-nomatch` ("No match", Enter inert), `windowring` (fake toplevels), `tests/host/test_theme.py` (global bind line), `test_daemon.py` (`launcher.show` event, `launcher.index` filter)

- [ ] Steps 1-5 as in slice 1 (RED → implement → GREEN → commit `feat(shell): launcher ring and window ring`).

### Task 3: Notification daemon, cards, OSD

**Files:**
- Create: `shell/Notifications.qml` (singleton: `NotificationServer { keepOnReload: true; onNotification: … }`, queue, `held` count, Do-Not-Disturb flag from `settings.dnd`), `shell/NotifyCard.qml` (300k card under the strip at top-right: kicker app name, title, body, actions as ghost buttons; slides in over enterMs; three visible, the rest held), `shell/Osd.qml` (volume / brightness bar 240×2 with the accent fill, centred at y 900, shown 1.2 s on `wpctl`/`brightnessctl` changes via `Pipewire.defaultAudioSink.audio.volume` and `/sys/class/backlight` through a daemon event `osd.brightness`)
- Modify: `daemon.py` (`notifications.store {app, summary, body, ts}` appends to `notifications.jsonl` with `seen: false`; `notifications.seen` marks all; `since_count` uses it; `settings.dnd` in SETTABLE), `PresenceContent.qml`/daemon `_card("focus")` (held count, DND state), `Strip.qml` (held badge)
- Test: render scenarios `notify` (one card at 300k under the strip), `notify-storm` (50 → 3 visible, held 47), `osd`; `test_daemon.py` (`notifications.store/seen`, `since_count`)

- [ ] Steps 1-5; commit `feat(shell): notification server, cards, OSD, Focus card`.

### Task 4: Settings pages in QML (Eternity, Assistant, Devices, Network, Sound, Power, Appearance, Keys)

**Files:**
- Create: `shell/SettingsWindow.qml` (a normal Wayland window, class `eternity-settings`, 1100×720 design px, left nav of pages, right the 700k column at the design's row geometry: 18k padding rows with fade-rule dividers), one `SettingsPage*.qml` per page: Eternity (voice seg, verbosity slider 240k, proactive, keep-on-device, telemetry off disabled, unlock methods read-only + "Change in the setup assistant"), Assistant (provider combo, sign-in row + status, Claude model, allow-list check grid, trust level), Devices (the `eternity-hw` report as rows + radios toggles via `Networking.wifiEnabled`, Bluetooth via `Quickshell.Bluetooth`, "Copy report"), Network (wifi list from `Networking.devices` with `connectWithPsk`, wired state), Sound (sinks/sources from `Pipewire.nodes`, volume sliders, default toggles), Power (battery from `UPower.displayDevice`, `PowerProfiles.profile` seg, idle timeouts → `hypridle.conf` through the daemon), Appearance (presets Nocturne / Nocturne Light / Mono / High contrast / Quiet writing `theme.toml` + `layout.toml` via `eternity-theme render`; scale 1.0/1.25/1.5; reduced motion; glow slider), Keys (table from `keys.toml`, read-only in this slice with "edit ~/.config/eternity/keys.toml")
- Modify: `daemon.py` (`theme.get/set {section,key,value}` → writes the user TOML and re-renders; `hyprctl reload` through `Hyprland.dispatch("reload")` from the shell on `theme.changed`), `eternity-settings` (`--show` → `settings.show` event when the daemon is up; GTK otherwise), `keys.toml` (`settings = "SUPER, comma"` exists)
- Test: render scenarios per page at design geometry (`settings-eternity` rows at 18k padding, the verbosity slider 240k; `settings-offline` controls disabled); `test_daemon.py` (`theme.set` writes `~/.config/eternity/theme.toml` and the generated files change; invalid value refused); `test_theme.py` (presets exist and validate)

- [ ] Steps 1-5; commit `feat(shell): Settings pages (Eternity, Assistant, Devices, Network, Sound, Power, Appearance, Keys)`.

### Task 5: Monitor page

**Files:**
- Create: `shell/MonitorWindow.qml` (class `eternity-monitor`; four 400k panels at (180,220)/(1340,220)/(180,680)/(1340,680): CPU %, AI (tok/s or "idle"; "NPU" only with `/sys/class/accel`), Memory GB, Input latency ms (`Latency.p95`); 400×70 sparklines as `Shape` paths updated once per second from `Daemon.metrics` history (60 samples); the 300k ring at (960,560) with the accent arc = CPU load; the status line at y 880: `CPU LOAD · N% · <refresh Hz> · N DROPPED FRAMES`), a second page "Processes" (top 12 by RSS from a new daemon method `metrics.processes`)
- Modify: `daemon.py` (`metrics.processes`, `metrics.history` keeps 60 samples), `eternity-monitor` (`--show`)
- Test: render scenarios `monitor` (panel positions, sparkline width 400k), `monitor-bare` (no battery/AI: "—"), `test_daemon.py` (`metrics.processes` returns rss/comm rows)

- [ ] Steps 1-5; commit `feat(shell): Monitor page with honest panels and sparklines`.

### Task 6: Visual run, smoke, build 14 chain, notes

- `run-qemu-visual.sh --session eternity` gains: Super (release) → `e-launcher.png`; `notify-send "Eternity" "hello"` from the terminal → `e-notify.png`; Super+, → `e-settings.png`; Super+M → `e-monitor.png`; with `eternity.greeter=greetd` on a second boot → `e-greeter.png`.
- `check_session` adds greetd/cage presence and `quickshell -p /usr/share/eternity/greeter/shell.qml` offscreen load.
- `tools/dev/chain-build14.sh` (from chain-build13 + greeter boot); results into `docs/build-notes.md`; stick rewrite when green.

## Self-review notes

- Covers spec §4.2 launcher, monitor, settings, unlock(greeter); §4.3 Super release, Super+Tab, notifications; §8 rows Greeter, Launcher, Monitor, Settings, Notifications & OSD, Network, Power, Sound (Settings pages). Out of scope: Files QML, customisation files UI beyond presets, persistence, Codex/Gemini (slice 2b).
- Interfaces reused from slice 1: `Daemon.call/event`, `Theme`, `Geometry.k/isPanel`, `LockContent` (greeter), `Latency.p95`, `theme.render`, `settings.set` + SETTABLE (`dnd` added), the overlay-window pattern of `Bar.qml`.
