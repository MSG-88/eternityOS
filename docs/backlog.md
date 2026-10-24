# Eternity 08 backlog (owner direction for the next phases)

Recorded 2026-10-24 while phase 1 (the OS itself) was being finished. These shape the
phase 2 spec; they are not implemented in phase 1.

## 1. AI agents ingested into the OS, chosen at first-boot setup

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

- Harden against viruses and attacks: AppArmor enforced for exposed services, firewall
  default-deny inbound, unattended security updates, Secure Boot kept on, integrity
  checks of the Eternity tools, sandboxed execution for anything the agent runs, no
  silent privilege escalation, optional on-access scanning (ClamAV) for downloads.

## 3. The human stays in control

- The AI follows the human: every action the agent proposes is shown and confirmed
  before it runs (with a per-session "trust" level the user can raise), everything it did
  is logged and reversible where possible, and the user can switch provider or disable
  the agent at any time.
