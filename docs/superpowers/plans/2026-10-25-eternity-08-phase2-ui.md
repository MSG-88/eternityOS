# Eternity 08 phase 2: the Eternity interface, AI agents, security (overnight 2026-10-25)

Owner direction (2026-10-25 00:55): work the backlog overnight, "take each screen and
section as a phase and ensure it is completed end to end"; the key is an OS that is "AI
integrated at the max with enhanced security and ease of use". Spec: `docs/backlog.md`
(sections 1 to 4) and the design capture `docs/design/README.md`. No check-ins: decisions
below are recorded here and in `docs/build-notes.md`.

"End to end" for a phase means: implemented in `config/`, covered by a host-side test
(`tests/host/`) or a chroot/smoke check, included in the next build, and seen in a QEMU
screenshot or self-test line. Everything runs on the live ISO and on installed systems.

## Constraints that shape the design

- XFCE on X11 stays the session for this phase (a Wayland shell is phase 3). The presence,
  command bar, launcher and monitor are GTK 3 + cairo windows driven by Python 3 (PyGObject
  is already in the image through the XFCE stack); they sit on the XFCE desktop rather than
  replacing it.
- Inference is CPU llama.cpp (Qwen3.5 GGUF) via `llama-server` on 127.0.0.1:8080, started on
  demand; cloud providers are Anthropic and OpenAI HTTP APIs with keys in the user's keyring
  (libsecret). No subscription OAuth exists for third-party apps, so "sign in with your
  subscription" is implemented as "paste your API key" with the provider's console linked.
- Honest UI: no fake sensors. Cards and readouts show what the machine really has (clock,
  system load, AI status, recent files, battery, network). Face/voice unlock are shown as
  "coming later" in the first-run flow; passphrase and PIN work.
- The human stays in control: every agent action is proposed, confirmed and logged
  (`~/.local/state/eternity/actions.log`), with undo where the action has an inverse.

## Phases (each lands as one commit, in this order)

| # | Phase | Deliverable | Test |
|---|---|---|---|
| D1 | Branding refresh | Nocturne tokens, Möbius mark, Michroma wordmark in `branding/render.py`; GRUB theme, greeter, wallpaper, icons, Calamares, terminal palette | `tests/host/test_branding.sh` (renders, checks files and colours) |
| D2 | Boot | Plymouth script: hairline, ring draw-in (frames), wordmark settle, six real boot-log lines | script syntax via `plymouth --help`-free lint + visual (`run-qemu-visual.sh` plymouth shot) |
| D3 | First run | `eternity-firstrun` (GTK): greeting, name, unlock methods, AI provider choice (local / Claude / ChatGPT) with keyring storage; autostart once | `tests/host/test_firstrun.py` (settings + provider model, no display) |
| D4 | Unlock | greeter theme: Nocturne GTK CSS for lightdm-gtk-greeter, mark avatar, wallpaper | chroot check (files), visual run login shot |
| D5 | Home | `eternity-shell`: presence at the desktop centre (animated mark + rings), orbit cards (clock/day, system, AI, recent files), status strip; command bar on Super+Space | `tests/host/test_shell_cards.py` (card data sources) + visual desktop shot |
| D6 | Ask | `eternity_ai` provider layer (local server autostart, Anthropic, OpenAI), streaming with first-token and tok/s readout, tools with consent and audit log and undo, `eternity-chat` rewired | `tests/host/test_ai_provider.py` (fake HTTP server), `test_actions.py` |
| D7 | Launcher | radial launcher over .desktop files with type-to-filter (Super) | `tests/host/test_launcher_index.py` |
| D8 | Files | `eternity-find`: semantic search over the home folder with a small on-device embedding model (bundled through `ai/`), grouped results, assistant suggestion | `tests/host/test_find_index.py` (toy corpus) |
| D9 | Monitor | sparklines for CPU, memory, disk, network, AI tokens/s; scheduler and frame counters where real | `tests/host/test_monitor_sources.py` |
| D10 | Settings | "How she shows up": verbosity, proactive suggestions, keep everything on device (disables cloud providers), telemetry (none, shown as off), unlock methods, provider and keys | `tests/host/test_settings.py` |
| E | Security | nftables default-deny inbound, AppArmor enforced, unattended security upgrades, agent sandbox rules, no silent privilege escalation | smoke `check_security` |
| F | Build 10 | all of the above in one ISO; smoke, Secure Boot, visual, USB runs; stick rewritten if green | `tests/run-all.sh` |

Build 9 (installer fixes only) runs first so a known-good ISO exists for the stick in the
morning; build 10 carries the interface.
