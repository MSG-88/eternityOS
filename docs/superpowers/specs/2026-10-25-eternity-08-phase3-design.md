# Eternity 08 phase 3: the Eternity shell, agents without keys, hardware, USB persistence, customisation

Status: draft for the owner, written 2026-10-25 afternoon from the owner's testing feedback
(backlog section 5) and the Claude Design file (`docs/design/`, sources unpacked in
`docs/design/src/`). The owner's words that drive it:

> "the eternity claude or chatgpt or other agents are not integrated, what i am expecting is
> not only the api key based ingestion but claude code to be integrated within the OS which
> will work without api key. BIOS and most of the drivers were not working with the OS, the
> UI/UX is a mere copy of ubuntu distribution whereas we need to make eternity UI/UX
> completely unique with high tech visuals and navigation options. dive in deep to each
> section of the OS and ensure each one of them is completed with high precision. Very close
> integration of AI components to the OS and the hightened security is the key. ensure that
> this OS is in enterprise level with all the inbuilt components accurately working more than
> expected." … "Make this OS into a strong innovation friendly OS which will work both from an
> installed source and also usb based OS will also be available. high customization of the OS
> is one of the Key USP." … "Ensure that this layout is implemented with high precision and
> that the performance is the primary factor."

Decisions marked **(my call)** were made by the builder to keep moving; the owner can
overturn any of them. Questions only the owner can answer are collected at the end.

## 1. Intent

Eternity 08 is a personal operating system whose interface is one presence, not many apps:
the user talks to it, it acts on the machine with consent, and everything personal stays on
the device unless the user chooses otherwise. Phase 1 made the OS boot, install and run a
local model; phase 2 put a first version of the interface on XFCE and the assistant behind
it. Phase 3 makes the interface *the* interface (its own shell, not a themed desktop), makes
the strongest agents the user already pays for available inside the OS without API keys,
makes the hardware of the owner's laptop work, and turns "runs from USB" and "customise
everything" into first-class features. Performance is the primary quality: the design's
promise is "input under 50 ms end to end".

## 2. Goals, non-goals, anti-goals

Goals
- The layout of `eternity08.jsx` reproduced on the real screen at the design's geometry
  (1920×1080 reference, scaled by the shell to the actual output), with the same tokens,
  motion and copy, as a living shell (real clock, real cards, real metrics).
- Every surface is a GPU-rendered scene; animations hold 60 fps on the owner's laptop
  (Vega 10 iGPU) and degrade gracefully (30 fps on battery, no animation under software
  rendering); keyboard-to-pixel latency measured and shown, target < 50 ms.
- Claude through the user's own Claude account (Claude Code) is the headline agent; ChatGPT
  (Codex CLI) and Gemini (Gemini CLI) follow through the same bridge; the bundled local model
  remains the default and the offline fallback. Every agent action goes through Eternity's
  consent, audit and undo, regardless of which runtime answers.
- The owner's laptop (MSI Alpha 15 A3DDK) works out of the box: wifi, Bluetooth, both GPUs,
  audio, touchpad, webcam, brightness and function keys, suspend/resume, battery readout,
  firmware updates. A hardware report tells the truth about every other machine.
- The same image runs installed (Calamares, dual boot with Windows) and from USB with
  persistence (settings, files, sign-ins survive reboots on the stick).
- Customisation as a system: themes, layout, key maps, the presence's behaviour and the
  cards are declarative files the user, Settings and the assistant can all edit, with
  presets, live reload and undo.
- Enterprise grade: every section listed in §8 has an owner, a definition of done, a test and
  a screenshot before it is called finished; security hardening extended (lock screen,
  sandboxing, disk encryption option, audit viewer, signed updates).

Non-goals (this phase)
- Face and voice unlock (shown as "coming later" until an on-device model is chosen).
- A mail client, calendar backend or music player of our own: the home cards show what the
  system has (today, system, AI, recent files, notifications, now playing via MPRIS) and
  stay honest when a source is absent.
- Phone/tablet form factors, touch-first navigation, multi-user kiosk modes.
- Distribution to third parties (which would also need Anthropic's Commercial Terms for the
  preinstalled Claude Code; see §5.4).

Anti-goals (would make it a failure even if it "works")
- Fake numbers anywhere (an "NPU %" on a machine without an NPU, invented latencies).
- An agent that acts without a visible, logged, undoable decision by the user, or that can
  escalate privileges.
- A shell that looks like the design but stutters, or needs the Python interpreter in the
  frame loop.
- A second "Ubuntu-looking" layer: no stock panels, no stock greeter, no stock notification
  bubbles in the default session.

## 3. Constraints

- Debian 13 (trixie) with `trixie-backports` already enabled in the image (kernel pinned
  from it). Packages verified available on 2026-10-25: hyprland 0.55.2 (bpo), quickshell 0.3.0
  (bpo), hyprlock/hypridle/hyprpaper/xdg-desktop-portal-hyprland (bpo), labwc 0.8.3, sway
  1.10, gtk4 4.18 + `gir1.2-gtk4layershell-1.0`, greetd 0.10, wlgreet, bluez 5.82, fwupd 2.0,
  power-profiles-daemon 0.30, nodejs 20.19, podman 5.4, flatpak 1.16; claude-code from
  Anthropic's apt repository (stable channel, pinned 2.1.308-1). Not in Debian 13: niri,
  river, eww, ags, swww, msi-perkeyrgb.
- Hardware we must satisfy first: Ryzen 7 3750H (Picasso) + Vega 10, Radeon RX 5500M (Navi
  14) as a second GPU, Realtek RTL8822CE wifi (rtw88, ASPM quirk), Realtek Bluetooth over USB
  13d3:3549, Killer E2600 (RTL8125, r8169), Realtek ALC235 + AMD HDMI audio, I2C HID touchpad,
  Chicony UVC webcam, WDC SN730 NVMe, TPM 2.0, UEFI with Secure Boot on, 14 GB RAM.
- Tests run under QEMU TCG (no KVM on the build host since KB5127648) at roughly 10× real
  time, plus Hyper-V at native speed when the owner's machine is free. The shell therefore
  needs a software-rendering path good enough to boot and screenshot, and the performance
  acceptance measurements are taken on the laptop (and in Hyper-V), not in TCG.
- Everything in `config/` is the image; everything must work identically on the live stick
  and on an installed system; the 5 GB ISO cap is history (6.0 GB today) but growth must
  stay deliberate (Qt is already there through Calamares; Hyprland + Quickshell add ~60 MB).
- Secure Boot stays on: only Debian-signed kernels and shim; no DKMS modules.
- Python 3.13 stays the language of the Eternity services and tests (`tests/host`, 61 unit
  tests + Xvfb UI smoke today); the shell's pixels move to a GPU scene-graph language.

## 4. The shell (owner: "completely unique, high tech visuals and navigation options";
## "high precision", "performance is the primary factor")

### 4.1 Platform **(my call)**

- **Wayland session on Hyprland** (trixie-backports). Reasons: GPU-composited by design,
  per-window animations, blur behind our surfaces, rounded corners and gaps without
  patching anything, a text configuration that is hot-reloadable (the customisation system
  writes it), a socket IPC the shell uses for workspaces/windows/keybinds, and first-class
  layer-shell support for our surfaces. Fallback if Hyprland misbehaves on the laptop's
  Picasso/Navi pair or in the VMs: **labwc** (same wlroots protocols, software rendering
  proven, fewer animations); the shell is written against the protocols, not the compositor.
- **The Eternity shell in Quickshell (QML / Qt Quick 6)**: one process that owns every
  persistent surface (status strip, presence desktop, command bar, launcher, notifications,
  OSD, lock screen) as layer-shell windows. Qt Quick renders on the GPU scene graph with
  batching, shaders and a 60 fps animation clock; QML maps one-to-one onto the design's
  React tree (absolute geometry, eased property animations), so the design file is ported
  element by element. Qt 6 is already in the image (Calamares). The alternative, GTK 4 +
  layer-shell driven from Python (our current language), was rejected for the frame loop:
  the presence (Möbius ribbon with 150 shaded quads, 72 ticks, four dashed rings, glow)
  must animate every frame without an interpreter in the path. Python keeps the brain.
- **Greeter**: greetd running a minimal compositor (`cage`, or Hyprland with a greeter
  config) that shows the Eternity unlock scene from the same QML (design scene 03 without
  the camera: passphrase and PIN; "n things since you left" from the notification store).
  Replaces lightdm-gtk-greeter in the default session.
- **Lock screen**: the same scene through `ext-session-lock` (Quickshell supports it), so
  lock and login look identical; hypridle drives timeouts, no screensaver.
- **XFCE "Classic" stays selectable** in the greeter for builds 13 and 14 (it is the only
  session the tests have passed on), and is removed once the Eternity session passes the
  same visual and install runs.

### 4.2 Geometry (from `docs/design/src/eternity08.jsx`, 1920×1080 reference)

Scale factor `k = min(W/1920, H/1080)`; every px below is multiplied by k; layouts anchor
to the centre `(W/2, H/2)` and to edges as the design does.

- **Background**: radial vignette `ellipse 70% 60% at (50+d/20)% (45+d/40)%`, `#1b1e31 → #161826
  (60%) → #121421`, with `d = 60·sin(0.21·t)`; plus the presence glow
  `radial(circle at core, rgba(145,132,217,0.12·glow) → transparent at 300·s+200 px)`.
- **Status strip** (top, 44 px): left the 20 px mark (ring colour neutral-500, no glow) and
  the wordmark at 11 px with 0.2 em tracking; centre clock `HH:MM` (tabular numerals, text
  colour); right, 22 px gaps: `● live · <latency> ms` (accent dot), the AI readout (local
  model state or `~tok/s`, never "NPU" unless a real NPU exists), network, battery %.
  Font Inter 500 13 px, colour neutral-400, padding 0 28 px.
- **Presence (core)**: a 600×600 box at the scene position scaled by `s`: four rings r = 92,
  134, 176, 214 (stroke 1.25, ring 2 at 2.5 and accent; ring 4 neutral-600; others
  accent-700), dashed by the design's fractions, each rotating at `±(10+7i)°/s`; 72 ticks on
  r 228/234→240 (every 6th accent-400) rotating 1.5°/s; a soft glow (energy = 0.55 + 0.2
  sin(0.9πt) [+ fast·sin(4.4πt)] scaled 1+0.08·energy); the 176 px Möbius mark in the
  centre (ring stroke 2.2 fading top and bottom; 150 quads whose width is
  7.5·|cos t|^0.75 and whose shade mixes accent-100 into accent-600 by 45 + 55·(0.55 sh +
  0.45 lit); a 2.2 px light travelling the path at 0.22 loops/s). Per-section placement
  table: Boot (960,500,1.0), Setup (520,540,0.72), Login (960,420,0.78), Home
  (960,540,0.5), Ask (960,420,0.62, fast 0.3), Launcher (960,540,0.42), Files
  (1600,540,0.38), Monitor (960,560,0.46, fast 0.12), Settings (520,540,0.5); glides take 1 s
  with easeInOutCubic.
- **Home**: an orbit ellipse 440×270 around the centre carrying the cards at angles −90, 0,
  90, 180 (+2.5°/s drift), each card 300 px wide (`card elev-sm`: kicker, title, body,
  meta), a faint dotted guide circle r 400 (neutral-700, dash 0.002/0.01) and an accent arc
  (18 % of the circumference, 1.5 px, rotating 1.4× the drift). Caption line at y 900 in
  neutral-500 15 px. Cards are real: Today (clock, date, next event if a calendar exists),
  System (CPU, memory, battery, network), Eternity (model, tok/s, actions today), Recent
  files, Install (live only), Now playing (MPRIS, hidden when nothing plays), Focus (Do Not
  Disturb state and held notification count).
- **Command bar**: 800×54 at (560, 950), radius 14, surface colour, shadow-sm; focused:
  1 px accent ring + 32 px accent glow at 25 %; a 10 px accent dot breathing at 3 rad/s;
  placeholder "Ask Eternity, or type a command" in neutral-600 17 px; the shortcut chip
  "⌘ Space" (we print "Super Space") 12 px, 1 px neutral-800 border, radius 6.
- **Ask**: the reply at (560, 650) width 800 in Inter 400 19 px/1.55, streamed word by word
  (we stream tokens), a blinking 8×18 accent caret while streaming; a fade rule at y 620;
  the "thinking" line at y 580 centred (neutral-500 14 px); the readout top-right at (right
  40, top 60): `realtime · on device` (accent-300) or the provider, `first token N ms`,
  `~N tok/s`; action buttons 22 px below the reply (primary / secondary / ghost); the other
  cards dim to 10 % while the answer is live and the affected card updates in place.
- **Launcher**: twelve 64 px tiles (radius 14, surface, shadow-sm; selected: accent ring +
  28 px glow, label text colour) fanned on an ellipse 1.35·r × r with r from 150 to 350
  (easeOutBack, 70 ms stagger), angle `i/n·2π − π/2 + 0.03 t`; "Type to filter · <query>" at
  y 100. Beyond twelve, the ring paginates (Page Down / scroll) and the filter wins.
- **Files**: a 1190×620 window at (150, 230), radius 14, surface, shadow-md; sidebar 220 px
  (FILES kicker, Recents, Desktop, Projects, Photos, starred places, Shared); "Search by
  meaning…" input 46 px on background colour with an 8 px accent dot; the result header
  (`tag-accent` "Grouped by Eternity", counts, latency in accent-300); a 4-column grid of
  4:3 thumbnails (radius 8) popping in with 90 ms stagger; the assistant's one-line
  suggestion below in neutral-500 14 px. Backed by `eternity-find` (bge-small embeddings on
  device).
- **Monitor**: four 400 px panels at (180,220), (1340,220), (180,680), (1340,680): kicker
  (11 px, 0.1 em, uppercase, neutral-500), value 30 px 500 with the unit at 14 px, a 400×70
  sparkline (1.5 px; the AI panel in accent, others neutral-400) ending in a 3 px dot, a
  fade rule under each; a 300 px ring at (960,560) with a 3 px accent arc showing the
  headline load and a 1 px neutral-800 track; the line at y 880: `<AI or CPU> LOAD · N% ·
  <scheduler Hz if known> · N DROPPED FRAMES` (dropped frames measured from the scene
  graph). Panels: CPU %, AI (tok/s or idle), Memory GB, Input latency ms (measured:
  keypress timestamp to presented frame, via the compositor's presentation feedback).
- **Settings · Eternity**: 700 px column at (1000, 200): kicker "Settings · Eternity"
  (accent, 11 px, 0.12 em), title "How she shows up" (36 px 500, −0.015 em), rows of 18 px
  padding with fade-rule dividers: Voice (segmented Calm / Bright / Off), Verbosity (240 px
  slider, 2 px track neutral-800, accent fill, 14 px accent-300 knob), Proactive
  suggestions, Keep everything on device, Share anonymous model telemetry (off, disabled:
  there is none), Unlock (methods); below, the "Changes apply instantly…" note (13 px
  neutral-500). Further pages (Assistant, Devices, Network, Power, Appearance, Keys, Stick,
  Security, About) share the column, each a QML page fed by the daemon.
- **First run / Unlock**: scenes 02 and 03 as specified in phase 2, re-rendered in QML with
  the design's positions (text column at x 1000, width 640, from y 250; step bar at y 190;
  46 px title with typed-in greeting at 18 cps; the unlock chips 220 px circle at
  (960, 420) replaced by the mark while no camera model exists; "Good evening, <name>." at
  52 px; alternative methods as outline tags at bottom 88).
- **Boot**: Plymouth keeps scene 01 (already built); the hairline at y 500 (1400 px, draws
  over 1.1 s), the log at (64, bottom 64) 13 px neutral-600 with accent-700 numbering, the
  wordmark 24 px at y 790 and "PERSONAL OS · 08" 11 px Michroma 0.3 em at y 830.
- **Motion**: entrances easeOutCubic 0.6-0.8 s with 14-20 px rise; strokes easeInOutSine;
  pops easeOutBack; typed text 24 cps; fade rules 48 px at both ends; nothing bounces more
  than the design does. All durations are tokens (`motion.toml`) so "reduced motion" is one
  switch.
- **Tokens**: the Nocturne set from `nocturne.css` (colours, accent and neutral ramps,
  section colours, divider at 16 %, radii 4/8/14, shadows sm/md/lg, spacing 2.8 px scale,
  Inter 400/500, Michroma for the wordmark) is the single source: a generator emits the QML
  `Theme` singleton, the GTK 3/4 theme for ordinary apps, the Qt palette, the terminal
  palette, the GRUB/Plymouth colours and the Calamares stylesheet from one `theme.toml`.

### 4.3 Navigation model **(my call, within the design's hints)**

- Keyboard first: Super = launcher ring; Super+Space = Ask; Super+Tab = window ring (open
  windows fan out like the launcher, release selects); Super+1…9 = workspaces shown as
  rings around the presence while held; Super+F = Files search by meaning; Super+M =
  Monitor; Super+, = Settings; Super+L = lock; Super+Q = close window; Super+Enter =
  terminal; arrows/HJKL = focus; Super+Shift+arrows = move; Super+drag = move/resize.
- Pointer: the presence is the desktop (click = Ask, right-click = launcher ring); hot
  corner top-left = window ring; the status strip's items open their panel (network,
  sound, battery/power profile, notifications) as layer-shell popovers in the card style.
- Touchpad: three-finger swipe between workspaces (Hyprland gestures), pinch = launcher.
- Windows: no title bars (Hyprland server decorations off); 1 px neutral-800 border, 2 px
  accent when focused, 8 px rounding, 12 px gaps, blur behind our surfaces only; tiling
  by default with a one-key float, because the design keeps the presence visible.
- Notifications: a card slides from the top-right under the strip (300 px, kicker = app,
  title, body), stacks to three, the rest "held" in the Focus card; Do Not Disturb from the
  strip and from Ask ("hold notifications until 3").

### 4.4 Performance budgets and how they are measured

| Budget | Target | Measured by |
|---|---|---|
| Key press to presented frame (Ask bar typing) | < 50 ms p95 on the laptop | `wp-presentation` feedback from Quickshell, logged by the daemon, shown in Monitor |
| Shell frame time while animating | 16.7 ms (60 fps) on Vega 10; 33 ms on battery | QSG render timing (`QSG_RENDER_TIMING`), dropped-frame counter in Monitor |
| Shell idle CPU | < 2 % of one core | `eternity-monitor` sampling over 60 s in the smoke run |
| Shell resident memory | < 150 MB (Quickshell + QML) | smoke `check_shell` |
| Login to usable desktop | < 3 s after the greeter accepts | journal timestamps, smoke |
| Launcher open | first frame < 80 ms | timestamp in the shell log |
| Ask first token (local) | unchanged from phase 2 (reported, not budgeted) | readout |
| Software rendering (TCG) | boots, renders, screenshots; animations off | visual run |

Rules that make the budgets reachable: no per-frame work in Python; the presence's
Möbius ribbon is a GLSL `ShaderEffect` (or a pre-baked 48-frame texture atlas under
software rendering); sparklines are `Shape` paths updated once per second; the daemon
pushes state over a Unix socket as JSON lines, the shell never polls; blur only behind
our layer surfaces; animations use the property animation system, not timers.

### 4.5 Architecture

```
greetd ─► cage/Hyprland (greeter) ─► eternity-greeter.qml        # unlock scene
          Hyprland (user session)
            ├─ eternity-shell (quickshell)   layer-shell: strip, presence, bar, launcher, OSD, lock
            ├─ eternity-daemon (python)      state hub over $XDG_RUNTIME_DIR/eternity.sock:
            │     settings, cards, metrics, notifications (org.freedesktop.Notifications),
            │     MPRIS, NetworkManager/BlueZ/UPower/PipeWire via D-Bus, hardware (hw.py),
            │     agents (agent.py, providers.py incl. claude_code), actions (consent → shell)
            ├─ eternity-mcp (per agent run)  consent dialog now asks the shell, not GTK
            ├─ xdg-desktop-portal-hyprland + -gtk, pipewire, wireplumber, gnome-keyring
            └─ ordinary apps (GTK/Qt themed Nocturne, no decorations)
```

The daemon is the existing Python package plus a socket API; the GTK windows of phase 2
become QML scenes; `eternity-ask`, `eternity-launcher` etc. remain as CLI entry points that
tell the shell to show the surface. Consent dialogs come from the shell (one process owns
the screen), the MCP server asks the daemon which asks the shell. The daemon is also what
future agents (Codex, Gemini) talk to.

## 5. Agents without keys (owner: "claude code integrated within the OS which will work
## without api key")

5.1 **Claude (your Claude account)**: delivered in build 12 as specified in
`docs/build-notes.md` (Claude Code from Anthropic's signed apt repository, pinned; sign-in
by the user through `claude auth login`; the Ask bar drives `claude -p` with stream-json;
Eternity's tools over the `eternity` MCP server; `--permission-prompt-tool` routes every
tool call of Claude Code through Eternity's consent, audit and undo; sudo/pkexec/doas always
denied; nothing stored by Eternity). Phase 3 adds: the consent dialog rendered by the shell;
a session list ("continue yesterday's thread"); a "what Claude may do without asking" page
(the allow-list by trust level, per tool, shown and editable); cost/usage readout from the
result events; the model picker (sonnet/opus/haiku aliases); a terminal tile "Claude Code"
in the launcher for the full interactive tool.

5.2 **ChatGPT (your ChatGPT account)** via OpenAI's Codex CLI (Apache-2.0, npm or release
binary; ChatGPT sign-in built in; `codex exec --json` for headless runs; MCP servers in its
config) through the same `eternity-mcp` bridge and the same consent rules; **Gemini (your
Google account)** via Gemini CLI likewise. Order: Codex first (the owner named ChatGPT).
Each is offered only when installed and shows its own sign-in status; none ever receives an
API key from our keyring unless the user chose the API-key variant.

5.3 **Agent-OS integration depth**: the OS-knowledge prompt grows a live inventory (hardware
report, installed apps, services, settings schema, customisation files, the user's places);
new tools: `customize` (edit the declarative files with undo), `devices` (toggle radios,
pair Bluetooth, choose outputs), `network` (connect to a wifi, show status), `power`
(profiles, brightness), `notifications` (hold/release), `install_app` (Flatpak/apt via
pkexec with a visible policy prompt, never silent), `update_system` (unattended-upgrades
status, start an update, reboot required), `screenshot` (grim, for "what is on my screen").
The assistant answers "why is wifi not working" from `hardware_report` + journal lines.

5.4 **Terms** (to settle before distribution): Anthropic allows an end user to sign in to
the unmodified Claude Code with their own subscription on a platform that hosts it, but
preinstalling it in a product needs their Commercial Terms; products must not collect or
intermediate claude.ai credentials (we do not). We never use "Claude Code" or Anthropic
marks in feature names. Codex CLI and Gemini CLI are Apache-2.0; their sign-in terms are
the respective providers'.

## 6. Hardware (owner: "BIOS and most of the drivers were not working")

Build 12 (done): BlueZ + PipeWire Bluetooth + Blueman, `firmware-misc-nonfree`,
`firmware-sof-signed`, fwupd, power-profiles-daemon, acpid, rfkill/pciutils/usbutils,
rtw88 ASPM quirk, btusb autosuspend off; `eternity-hw` report, `hardware_report` tool,
`check_hardware` self-test.

Phase 3 adds, each with a check:
- **Function keys and brightness** on the MSI: `amdgpu` backlight (`amdgpu_bl*`) via
  brightnessctl bound in Hyprland; keyboard backlight through `msi-ec` if the kernel
  exposes it; volume/mute/mic keys; airplane mode key → rfkill; "BIOS" check: legacy BIOS
  boot of the stick is already tested in QEMU (`run-qemu-bios.sh`); on the laptop only UEFI
  applies. Owner to confirm what "BIOS not working" meant (boot menu entry missing?
  firmware settings? brightness/Fn keys?).
- **Dual GPU**: render on Vega (default), `DRI_PRIME=1` offload available from the launcher
  ("Run on the RX 5500M"); Navi 14 power-gated when idle; both reported by `eternity-hw`.
- **Suspend/resume** (s2idle on this platform): hypridle → `systemctl suspend`; the rtw88
  and btusb quirks are there because resume used to lose them; `check_hardware` reports
  `mem` in `/sys/power/state`.
- **Audio**: PipeWire with the ALC235 profile; output picker in the strip; HDMI audio when
  connected.
- **Camera**: UVC, listed; used only by apps the user opens (no face unlock yet).
- **Firmware updates**: fwupd via Settings > Devices ("2 updates available"), never silent.
- **Devices page**: the `eternity-hw` report as a live page with actions (toggle radios,
  pair, forget, set default output, brightness, power profile) and a "Copy report" button.
- **Owner's loop**: the first thing to do on the laptop with build 12 is `eternity-hw`
  (Super+Space → "hardware report"); its output decides the remaining quirks.

## 7. USB persistence and the two ways to run (owner: "work both from an installed
## source and also usb based")

- The stick stays a raw image of the ISO (the only layout that boots with Secure Boot on).
  `tools/write-usb.ps1 -Persistence <GB>` adds a fourth GPT partition labelled
  `persistence` (ext4, `persistence.conf` = `/ union`) after the image; live-boot picks it
  up with the `persistence` kernel parameter, which the GRUB menu offers as the default
  entry ("Eternity 08 (keep my data on this stick)") next to the stateless one and the
  installer entry. Everything (settings, sign-ins, files, installed Flatpaks) persists.
- In the OS: `eternity-stick` (Settings > Stick and the assistant's `make_persistent` tool)
  creates the partition on the running stick when none exists (polkit-gated, one visible
  prompt, verified unmounted free space), shows its usage, can encrypt it (LUKS, passphrase
  at boot) and can wipe it.
- First run on a live stick asks "Keep my data on this stick?" when no persistence exists
  and explains the alternative (install).
- Installed systems are unchanged; the installer offers full-disk encryption with the TPM
  option (§9).
- Tests: `run-qemu-usb.sh` grows a persistence partition on the virtual stick, boots twice,
  checks a file survives; `check_persistence` in the self-test reports the mode.

## 8. Every section, done with precision (owner: "dive in deep to each section")

Definition of done for a section: implemented in `config/`; a host test or self-test check;
present in the next build; a screenshot or measurement from a QEMU/Hyper-V run in
`docs/build-notes.md`; its Settings page (if any) complete; its agent tools (if any) listed
in the OS knowledge; its failure modes shown honestly in the UI.

| Section | Phase 3 deliverable | Test |
|---|---|---|
| Boot | splash text font (build 12), persistence menu entry, boot log from real facts incl. Secure Boot state | visual splash shot, `check_boot_theme` |
| Greeter / unlock | greetd + Eternity unlock scene (QML), passphrase + PIN, "n things since you left" | greeter screenshot in VM, `check_login` |
| Home | QML presence, real cards, orbit, Focus and Now playing, honest readouts | desktop shot, `check_shell` (memory, idle CPU), card data tests |
| Ask | QML bar and reply surface, shell-owned consent, action cards with undo, provider readout, sessions | fake-provider test, Ask shot, latency measurement |
| Launcher | ring with filter, pagination, GPU offload option, window ring (Super+Tab) | launcher shot, index tests |
| Files | QML window over `eternity-find`, places, thumbnails, suggestion; Thunar stays for management | find tests, Files shot |
| Monitor | real CPU/AI/memory/latency, dropped frames, process list page, per-GPU | shot, `check_monitor` |
| Settings | pages: Eternity, Assistant (providers, sign-ins, allow-list), Devices, Network, Sound, Power, Appearance (presets), Keys, Stick, Security (audit log viewer), Updates, About | shots per page, settings tests |
| Notifications & OSD | daemon implements org.freedesktop.Notifications; cards; volume/brightness OSD | notify-send in smoke, shot |
| Windows & workspaces | Hyprland config generated from `layout.toml`; borders, gaps, blur rules, animations; tiling + float | `hyprctl` checks in smoke |
| Network | NetworkManager via D-Bus in the strip popover and Settings; captive portal detection; VPN import (wg) | nmcli in smoke |
| Power | profiles, battery readout, lid/idle policy, suspend/hibernate (hibernate off by default) | upower in smoke |
| Sound | PipeWire outputs/inputs, Bluetooth audio, volume keys | wpctl in smoke |
| Installer | Calamares themed Nocturne (slides done), FDE option, persistence-aware ("you are running from a stick with data: copy it?") | install chain |
| Updates | unattended security updates (done), Updates page, our own signed repo for Eternity packages (later) | `check_security` |
| Accounts & keyring | gnome-keyring unlock at login via PAM (done), multiple users, PIN per user | `check_login` |
| Printing | cups + cups-browsed + system-config-printer, firewall rule only on demand | `check_printing` |
| Backup | Settings > Backup: Borg-based snapshot of home to an external disk or the stick, schedule | restore test in VM |
| Dev toolchain | Claude Code, Codex CLI, Gemini CLI, Python, Node, git, podman, VS Code (deb) or Codium | `check_dev` |

Execution order (each lands as one commit and one build): shell platform (session, strip,
presence, bar) → greeter/lock → launcher/windows → notifications/OSD → Settings pages
(Devices, Network, Sound, Power first) → Files/Monitor → customisation → persistence →
Codex/Gemini → printing/backup/dev → remove XFCE.

## 9. Security (owner: "heightened security is the key")

Already there: nftables default-deny inbound, AppArmor, unattended security updates, sysctl
hardening, loopback-only AI servers, no listeners, no privilege escalation by the assistant,
consent + audit + undo for every action (now also for Claude Code's tools).

Phase 3 adds: `ext-session-lock` lock screen with idle lock (5 min on battery, 15 on
mains) and lock on lid close; polkit rules that require the user's password for the few
root actions the OS exposes (install app, make stick persistent, firmware update, change
time); bubblewrap sandboxes for `run_command` and Claude Code's Bash (home read-write, no
network unless asked, no /etc writes); Flatpak with the Flathub remote verified, portals
on; full-disk encryption in the installer with TPM2 unlock (systemd-cryptenroll) and a
recovery key shown once; Secure Boot state and dbx status in Settings > Security; the audit
log viewer with export; ClamAV on-access for `~/Downloads` as an opt-in; USB guard (USBGuard)
opt-in with a one-click "allow this device" from the strip; fwupd for firmware; a monthly
"security posture" card (updates, firewall, encryption, lock) on the home screen; `sshd`
stays absent by default, enabled only from Settings with keys.

## 10. Customisation (owner: "high customization of the OS is one of the Key USP")

- Declarative files in `~/.config/eternity/`: `theme.toml` (tokens: colours, ramps, radii,
  fonts, shadows, glow), `layout.toml` (strip items and order, card set and orbit, bar
  position/size, gaps/borders/blur, launcher ring size, scale factor), `keys.toml` (every
  binding), `presence.toml` (motion intensity, reduced motion, idle behaviour, voice,
  verbosity, proactivity), `cards/*.toml` (user cards: a command, a URL poll or a file
  tail rendered as a card). The daemon validates, generates Hyprland config, the QML theme,
  GTK/Qt themes and terminal colours, and hot-reloads; errors are shown as a card, never a
  broken desktop.
- Presets shipped: Nocturne (default), Nocturne Light (same tokens inverted), Mono (no
  accent), High contrast, Quiet (reduced motion, no glow); "Save as preset" from Settings >
  Appearance; presets are plain files the user can share.
- Three ways to change anything: Settings pages (every control writes the file), the
  assistant (`customize` tool: "make the accent teal and the bar on top" → a diff shown and
  confirmed, undoable), or an editor (the files are documented and commented).
- Extension points: cards (above), launcher entries (`.desktop`), Ask quick commands
  (`/name` → script), MCP servers the user adds for the agents (through Settings >
  Assistant, with the same consent rules), Hyprland plugins are not supported (ABI churn).
- Innovation friendly: the dev toolchain in the image (§8), `eternity-dev` scaffolding a
  card or a quick command, the daemon's socket API documented (`docs/api.md`), everything
  under `/usr/lib/eternity` readable, the repo and build reproducible from the README.

## 11. Testing and builds

- Host: QML lint (`qmllint`) and the daemon's unit tests; `tests/host/test_shell_api.py`
  (socket protocol with a fake shell); screenshot tests of the QML scenes under a headless
  Qt (`QT_QPA_PLATFORM=offscreen`) compared to the design's geometry (positions of key
  elements within ±2 px at 1920×1080).
- Image: `run-qemu-visual.sh` boots the Eternity session (virtio-gpu, software GL) and
  captures greeter, home, Ask, launcher, Files, Monitor, Settings; `check_shell` (process
  present, memory, idle CPU, layer surfaces listed by `hyprctl layers`), `check_session`
  (portals, pipewire, keyring, notifications daemon), the existing smoke checks.
- Performance: measured on the laptop and in Hyper-V (native GPU for Hyper-V is absent, so
  Hyper-V covers latency logic, the laptop covers frame rate); results go in
  `docs/build-notes.md` per build with the budget table of §4.4.
- Builds: 12 (queued) = hardware + Claude Code + font; 13 = Eternity session next to XFCE
  (strip, presence, bar, greeter) ; 14 = launcher, windows, notifications, Settings core
  pages; 15 = Files, Monitor, customisation, persistence; 16 = Codex/Gemini, printing,
  backup, dev toolchain, XFCE removed. Each build: full chain (visual, smoke, install,
  fallback, Secure Boot, BIOS, USB), stick rewritten when green.

## 12. What is left to the builder

Exact QML component structure; the socket protocol's message names; how the Möbius shader
is written (GLSL vs. baked atlas) as long as the budget holds; the Hyprland config
template; GTK/Qt theme generation details; the polkit action names; the card schema; the
order inside each build as long as §8's order of sections holds.

## 13. Questions only the owner can answer

1. **Platform**: Hyprland + Quickshell/QML for the shell (my call, for performance and the
   design's animations) versus staying in Python/GTK 4. Any objection, or any compositor
   you specifically want?
2. **"BIOS not working"**: what exactly failed on the laptop: the stick not listed in the
   boot menu, firmware settings, brightness/Fn keys, suspend, or something else? And please
   run `eternity-hw` on build 12 and share the output (the Ask bar: "hardware report").
3. **Agents after Claude**: ChatGPT via Codex CLI next (sign-in, no key), then Gemini CLI?
   Or deeper Claude first (sessions, allow-lists, cost readout)?
4. **Distribution**: is Eternity for your machines only for now? Preinstalled Claude Code
   needs Anthropic's Commercial Terms the day it is distributed.
5. **Design access**: run `/design-login` in this session so the Claude Design project can
   be read live (the MCP needs your claude.ai authorisation); until then the unpacked bundle
   in `docs/design/src/` is the source of truth and matches the file you linked.
6. **Scale**: the design is 1920×1080; the laptop is 1920×1080 at 100 %. Should the shell
   also support 125/150 % scaling now (it costs little if decided up front)?
