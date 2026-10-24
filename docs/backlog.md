# Eternity 08 backlog (owner direction for the next phases)

Recorded 2026-10-24 while phase 1 (the OS itself) was being finished. **Status 2026-10-25
(overnight session):** items 1 to 3 and most of section 4 are implemented on branch `phase1`
and go into build 10 (`docs/superpowers/plans/2026-10-25-eternity-08-phase2-ui.md`,
`docs/build-notes.md`). Status marks below: ✔ landed, ◐ partial, ○ open.

## 1. AI agents ingested into the OS, chosen at first-boot setup

Status: ✔ `eternity-firstrun` (greeting, name, unlock methods, assistant choice: on-device /
Claude / ChatGPT with the user's own API key in the keyring), ✔ provider layer
`eternity.providers` (local llama-server on demand, Anthropic, OpenAI; streaming, tool calls,
first-token and tok/s), ✔ `eternity.agent` with the OS-knowledge system prompt and tools
(system info, files, apps, volume, notes, settings, shell, power, search by meaning),
✔ `eternity-ask` command bar (Super+Space). ○ Subscription sign-in: the providers offer no
OAuth for third-party apps, so keys are pasted (link to each console shown).

- Subscription-based agents (Claude, ChatGPT) are integrated into the OS next to the
  bundled local LLMs (Qwen3.5 via llama.cpp).
- The initial OS setup screen (first boot after install, and optionally the live session)
  offers the choice: local model (default, offline), Claude, or ChatGPT, and takes the
  user's own subscription sign-in. Credentials live in the user's keyring, never in the
  image.
- The chosen agent then takes over the setup and can understand each component of the
  OS in depth and perform actions for the user: an OS-knowledge layer (inventory of
  packages, services, configs, hardware, the Eternity tools) plus a documented tool set
  the agent drives (install/configure/diagnose). Provider layer under `eternity-chat` /
  `eternity-ai`; offline falls back to the local model.

## 2. Higher security standards

Status: ✔ nftables default-deny inbound, ✔ AppArmor enabled with profiles, ✔ unattended
security upgrades (no auto-reboot), ✔ sysctl hardening, ✔ no listening daemons and AI servers
on loopback only, ✔ the assistant never escalates privileges (sudo refused), ✔ smoke
`check_security`. ○ Integrity checks of the Eternity tools, ○ on-access scanning (ClamAV),
○ sandboxed execution (bubblewrap) for assistant-run commands.

- Harden against viruses and attacks: AppArmor enforced for exposed services, firewall
  default-deny inbound, unattended security updates, Secure Boot kept on, integrity
  checks of the Eternity tools, sandboxed execution for anything the agent runs, no
  silent privilege escalation, optional on-access scanning (ClamAV) for downloads.

## 3. The human stays in control

Status: ✔ every action is proposed and confirmed (consent dialog; PIN for sensitive ones when
chosen), ✔ trust level (read-only lookups may run unasked), ✔ audit log
`~/.local/state/eternity/actions.log`, ✔ undo on action cards (notes, volume, settings),
✔ provider switch / agent off in Settings > Eternity.

- The AI follows the human: every action the agent proposes is shown and confirmed
  before it runs (with a per-session "trust" level the user can raise), everything it did
  is logged and reversible where possible, and the user can switch provider or disable
  the agent at any time.

## 4. The Eternity interface design (captured from Claude Design)

Source: the owner's Claude Design project "Eternity OS AI Interface Design",
<https://claude.ai/design/p/f4409f71-86f6-4ef0-9cc6-babf6d42d16d?file=Eternity+08.dc.html&via=share>.
Durable copy and full notes: `docs/design/README.md` and `docs/design/Eternity-08.dc.html`
(**last captured 2026-10-25**; refresh the file and this section whenever the design changes,
the hosted version disappears on 2026-12-14).

Thesis of the design: one presence instead of many apps, input under 50 ms end to end,
everything personal kept on the device. Work items it implies, in rough order:

Status per screen: ✔ branding refresh, ✔ boot (Plymouth frames + real boot log), ✔ first run,
◐ unlock (greeter uses the new wallpaper; face/voice marked "coming later"; no "n things since
you left" in lightdm-gtk-greeter), ✔ home (presence + orbit cards, real data), ✔ ask (streamed,
readout, actions, undo), ✔ launcher, ✔ files (search by meaning, on device), ✔ monitor
(CPU, memory, disk, network, AI tok/s, shell frame time; no NPU), ✔ settings.
○ Platform: still XFCE/X11 with GTK windows; a compositor shell is phase 3.

- **Branding refresh (can land in phase 1 builds):** adopt the 3b mark (fading-ring 0 with an
  animated Möbius ∞) and the Michroma three-bar-E wordmark with "PERSONAL OS · 08" in
  `branding/` (logo, GRUB theme, Plymouth, greeter, wallpaper); keep Inter for everything
  else; re-check the Nocturne token values against `branding/colors.md`.
- **Boot:** Plymouth sequence that draws the hairline, assembles the ring and settles the
  wordmark, with the six-line boot log (secure boot verified, neural runtime, memory graph,
  sensors, scheduler, ready) as the status text.
- **First run (3 steps):** greeting, name, unlock methods (face, passphrase, voice, PIN),
  on-device voice sample; ties into backlog item 1 (agent choice at first boot).
- **Unlock:** greeter with camera-based face recognition and the alternative methods;
  "n things since you left" summary after login.
- **Home:** the presence at the centre of the desktop with orbiting cards (calendar, mail
  summarised, now playing, focus) and a bottom command bar (⌘ Space, "Ask Eternity, or type
  a command") wired to `eternity-chat`.
- **Ask:** streamed replies with first-token and tok/s readout, actions on calendar and
  mail (move meeting, notify attendees), undo for every action (backlog item 3).
- **Launcher:** radial app launcher with type-to-filter.
- **Files:** semantic "search by meaning" over local files with grouped results and an
  assistant suggestion (local embeddings, on device).
- **System monitor:** CPU / NPU / memory / input-latency sparklines, scheduler and dropped
  frame counters.
- **Settings "How she shows up":** voice (calm / bright / off), verbosity, proactive
  suggestions, keep-everything-on-device, telemetry off by default, unlock methods.
- **Platform implications:** a compositor/shell that can render the presence (likely a
  Wayland shell or a custom XFCE panel + overlay as a stepping stone), an NPU/GPU inference
  path for the latency targets, camera and microphone pipelines with on-device models.
