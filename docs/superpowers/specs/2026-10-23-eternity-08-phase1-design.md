# Eternity 08 — Phase 1 Design

Date: 2026-10-23
Status: draft, awaiting approval
Owner: Muthu

## 1. Intent

Eternity 08 is a lightweight, Linux-based operating system that is visibly
its own thing (branded from boot splash to desktop) and ships with a working
local AI stack: Python, the core machine-learning libraries, and one or two
small open-weight language models that run offline on ordinary CPUs.

Phase 1 delivers the OS itself. A later phase layers a Jarvis-style assistant
on top; another adds Windows application compatibility. Phase 1 must not
block either of those, but builds neither.

The reason for building on Linux rather than from scratch: a from-scratch
kernel with Windows and Linux application compatibility is a decade-scale
effort. A Linux base gives hardware support, a package ecosystem, and a
path to Wine for Windows apps, while still leaving every user-visible layer
ours to design.

The reason for "latest": the owner wants the newest stable base available
at build time, not a cached or aging image. This is a hard requirement.

## 2. Goals

1. A bootable, installable 64-bit x86 ISO called Eternity 08 that runs on
   ordinary PCs and in virtual machines.
2. Branding everywhere a user looks: GRUB menu, boot splash, login screen,
   desktop theme, wallpaper, icons, system name, terminal, installer.
3. Python and the core ML/AI stack preinstalled and importable on first boot
   with no network access.
4. At least one small open-weight LLM baked into the image, runnable from a
   terminal command on first boot with no download.
5. Built on the newest stable Debian release and its newest available kernel
   at build time, with a one-command, repeatable build.
6. Boots on the owner's MSI Alpha 15 laptop (UEFI, Secure Boot on) from a
   USB stick, and in a Hyper-V virtual machine on the same laptop.

## 3. Non-goals (phase 1)

- The Jarvis-style assistant (voice, agents, system control). Phase 2.
- Windows application compatibility (Wine/Proton). Phase 3.
- GPU acceleration (CUDA, ROCm). CPU inference only.
- ARM, 32-bit, or non-PC hardware.
- A custom kernel or custom init system. Debian's kernel and systemd are used
  as-is.
- A bundle of desktop applications (office suite, GIMP, etc.). Users install
  those from the package manager.
- An app store, Flatpak, or Snap integration.

## 4. Anti-goals (what would make it a failure even if it boots)

- It looks like stock Debian with a wallpaper swapped. Every surface in
  Goal 2 must carry Eternity 08 identity.
- The AI stack needs the internet on first boot. Models and libraries are in
  the image.
- It fails to boot on the owner's laptop because of Secure Boot or missing
  firmware.
- The image grows past 6 GB, or the desktop is sluggish on 4 GB of RAM.
- The build is a pile of manual steps. One script, from clean checkout to ISO.
- The base is stale: an older Debian release or kernel than what was
  available on build day.

## 5. Constraints

- Owner's hardware: MSI Alpha 15 (AMD Ryzen 7 3750H, 4C/8T, 14 GB RAM,
  Radeon RX 5500M + Vega 10, UEFI with Secure Boot, 83 GB free on disk).
  No NVIDIA GPU. Build host is WSL2 on this machine (Ubuntu 24.04 present;
  see 6.2 for the chosen build host).
- Owner has granted full permission and admin rights for implementation on
  this machine. The Windows install is not to be touched; testing is via
  Hyper-V VM and live USB, not dual boot.
- Target class: 64-bit x86 PC. Minimum 4 GB RAM for the OS; 8 GB recommended
  for the default model.
- Everything shipped is open source or openly licensed (models included).

## 6. Decisions made (how it gets made)

Items marked **[owner]** were stated by the owner. Items marked **[call]**
are the designer's choices; the owner can override any of them.

### 6.1 Base

- **[owner]** Linux-based, customized, not from scratch. Newest stable release.
- **[call]** Debian 13 "trixie", at its current point release on build day
  (13.7 as of 2026-10-23), amd64. Chosen for stability, the largest package
  archive, straightforward Wine availability for phase 3, and mature
  live-ISO tooling.
- **[call]** Kernel from `trixie-backports` (7.2.x as of 2026-10-23) rather
  than the stock 6.12, to satisfy "latest" and for newer hardware support.
  The build script must install whichever backports kernel is newest on
  build day, not a pinned version.
- **[call]** `main contrib non-free non-free-firmware` enabled, with the
  `firmware-linux` metapackages (including AMD GPU and common Wi-Fi
  firmware) in the image, so laptops get working graphics and wireless.

### 6.2 Build system

- **[call]** Debian `live-build` is the image builder. It produces a hybrid
  ISO (boots from DVD or USB, UEFI and legacy BIOS) and supports Secure Boot
  through Debian's signed shim and GRUB.
- **[call]** Build host: a Debian 13 instance under WSL2 on the owner's
  laptop (installed via `wsl --install -d Debian`), so that live-build and
  the target release match. The existing Ubuntu 24.04 WSL instance is left
  alone.
- **[call]** Repository layout:

  ```
  eternity-08/
    build.sh                 one command: clean checkout -> ISO
    config/                  live-build configuration (auto/, package lists,
                             hooks, includes.chroot/ for files copied into the OS)
    branding/                sources: logo SVG, wallpapers, Plymouth theme,
                             GRUB theme, LightDM greeter config, GTK/icon
                             theme overrides, fastfetch logo
    ai/                      model manifest, venv requirements, eternity-chat
    docs/                    this design, build/test notes
    tests/                   smoke tests run inside the built image
  ```
- **[call]** The build is repeatable: `build.sh` on a clean checkout produces
  the ISO with no manual steps. Downloaded artifacts (models, PyTorch wheels)
  are fetched by the script with checksums recorded in a manifest.
- **[call]** Versioning: Eternity 08 phase 1 is version `0.1.0`. The ISO is
  named `eternity-08-0.1.0-amd64.iso`.

### 6.3 Desktop and branding

- **[owner]** Custom login screen, own desktop theme, Eternity 08 branding
  everywhere.
- **[call]** Desktop: XFCE 4.20 (trixie's version). Light on RAM (about 500
  MB idle), fully themeable, well supported.
- **[call]** Login: LightDM with `lightdm-gtk-greeter`, configured with the
  Eternity 08 background, logo, and a greeter message. The live session
  shows the login screen (no autologin) so the custom login is the first
  thing seen; live credentials (`eternity` / `eternity`) are shown in the
  greeter message and the GRUB menu.
- **[call]** Boot: GRUB with an Eternity 08 theme (background, menu
  colours, title "Eternity 08"). Plymouth boot splash with a custom Eternity
  08 theme (logo plus progress animation).
- **[call]** Visual identity: dark base (near-black navy), one electric
  accent (cyan), a simple wordmark logo "ETERNITY 08" with the "08" as the
  motif. Logo and wallpapers are original SVG/PNG created in the repo. GTK
  theme: a dark theme (Arc-Dark or similar from the Debian archive) with the
  accent colour overridden; icon theme Papirus-Dark. The builder picks the
  exact theme packages and fonts.
- **[call]** System identity: `/etc/os-release` sets `NAME="Eternity 08"`,
  `ID=eternity`, `ID_LIKE=debian`, `VERSION_ID=0.1.0`, `PRETTY_NAME="Eternity
  08 0.1.0"`. `/etc/issue`, `/etc/motd`, default hostname `eternity`,
  and the terminal prompt carry the name. `fastfetch` is installed with an
  Eternity 08 ASCII logo and runs on first terminal open. The XFCE "About"
  dialog and the panel show the name and logo.
- **[call]** Installer: Calamares, branded (logo, slideshow, product name),
  so a user can install Eternity 08 to disk from the live session. Installed
  systems carry the same branding as the live session.
- **[call]** Preinstalled desktop apps are limited to essentials: Firefox
  ESR, a terminal, a file manager, a text editor, an image viewer, a
  PDF viewer, and the XFCE settings tools. Nothing else.

### 6.4 AI stack

- **[owner]** Python and all relevant ML/AI packages inbuilt, plus
  open-source lightweight LLMs.
- **[call]** Python 3.13 (trixie's system Python). The ML stack lives in a
  system-wide virtual environment at `/opt/eternity/venv`, on every user's
  PATH, because Debian's system Python refuses pip installs. Contents:
  NumPy, pandas, SciPy, scikit-learn, Matplotlib, Jupyter (notebook and
  lab), PyTorch (CPU-only wheel), Transformers, Tokenizers, safetensors,
  sentence-transformers, llama-cpp-python, and the Hugging Face hub client.
  Exact versions are the newest compatible releases on build day, recorded
  in a lock file in the repo.
- **[call]** Inference runtime: llama.cpp, built from a tagged release for
  CPU (AVX2) and installed system-wide (`llama-cli`, `llama-server`). Ollama
  is not shipped; it can be added later.
- **[call]** Models shipped in the image, under `/opt/eternity/models`, in
  GGUF format:
  - Default: a 4B-class instruct model at Q4_K_M quantization (about 2.5 GB).
    Candidate: Qwen3-4B. Runs on 8 GB RAM at a few tokens per second on the
    owner's CPU.
  - Small: a 1B-class instruct model at Q4_K_M (under 1 GB). Candidate:
    Qwen3-1.7B or Llama 3.2 1B. For 4 GB machines.
  The builder confirms the exact models and licences on build day (openly
  licensed, redistributable) and records them in `ai/models.manifest` with
  source URLs and SHA-256 checksums.
- **[call]** User-facing entry point: `eternity-chat`, a small command that
  starts an interactive chat with the default model (or `--small`) using
  llama.cpp, and `eternity-ai status`, which reports installed models,
  Python stack versions, and free RAM. A desktop launcher opens
  `eternity-chat` in a terminal. This is the phase-1 proof that the AI is
  there; it is not the Jarvis assistant.
- **[call]** A systemd service file for `llama-server` is shipped but
  disabled by default, so phase 2 can turn on an always-on local model
  endpoint without redesign.

### 6.5 Size and performance budget

- ISO: at most 6 GB. Rough budget: base plus desktop 1.5 GB, ML venv 2 GB,
  models 3.5 GB, compressed by squashfs to roughly 5 GB.
- Idle RAM after login: under 700 MB.
- Boot to login screen in a VM: under 30 seconds.

### 6.6 Testing and running it on the owner's machine

- **[call]** Automated: `tests/smoke.sh` runs inside the built image (via
  the build's chroot hook or a boot of the ISO under QEMU in WSL) and
  checks: os-release name, branding files present, venv imports (torch,
  transformers, sklearn), llama-cli loads the small model and answers a
  prompt, LightDM and Plymouth configured.
- **[call]** Manual, in order:
  1. Hyper-V Generation 2 VM on the laptop, Secure Boot enabled with the
     "Microsoft UEFI Certificate Authority" template, 4 CPUs, 8 GB RAM. Boot
     the ISO, log in, run `eternity-chat`, install to the VM disk with
     Calamares, reboot into the installed system.
  2. Write the ISO to a USB stick (Rufus, DD mode) and boot the MSI Alpha 15
     from it with Secure Boot left on. Confirm graphics, Wi-Fi, and
     `eternity-chat` work on real hardware.
  The Windows installation is not modified at any point.

## 7. Left to the builder

- Exact theme packages, fonts, icon set, and the look of the logo,
  wallpapers, GRUB and Plymouth themes, within the visual identity above.
- Exact package versions, pip lock file contents, and llama.cpp release tag.
- Final model choice between the candidates named in 6.4, subject to
  licence and size.
- live-build configuration details (hooks, package lists, squashfs
  compression settings).
- How the smoke test boots the image (QEMU vs chroot) as long as it runs
  from `build.sh --test`.

## 8. Future phases (recorded so phase 1 leaves room)

- Phase 2, Jarvis layer: an always-on local model endpoint (the shipped,
  disabled `llama-server` unit), a voice and text assistant, and system
  control tools. Nothing in phase 1 should assume the assistant is absent.
- Phase 3, Windows apps: Wine/Proton from the Debian archive; the multiarch
  (i386) foundation is not enabled in phase 1 but nothing prevents it.
