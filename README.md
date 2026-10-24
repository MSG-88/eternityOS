# Eternity 08

A lightweight Linux operating system (Debian 13 "trixie" base, newest backports
kernel, XFCE desktop) with Eternity 08 branding end to end and a local AI stack
built in: Python 3.13 with PyTorch, Transformers, scikit-learn, pandas and
Jupyter in `/opt/eternity/venv`, llama.cpp, and two bundled Apache-2.0 models
(Qwen3.5-4B and Qwen3.5-2B, GGUF) that run offline on the CPU.

Phase 1 = the OS itself. Phase 2 adds the Jarvis-style assistant; phase 3 adds
Windows application compatibility. See `docs/superpowers/specs/` for the design.

## Live session

- Boot the ISO. GRUB offers **Eternity 08 Live**, a safe-graphics entry and a
  self-test entry.
- Login screen: user `eternity`, password `eternity`.
- Desktop launchers: **Eternity Chat** and **Install Eternity 08**.
- Terminal: `eternity-chat` (interactive), `eternity-chat --ask "..."`,
  `eternity-ai status`, `eternity-ai models`, `eternity-ai serve`.
- Python: `python` is the ML environment (`import torch` just works);
  `jupyter lab` is available.

Minimum 4 GB RAM (the small model is picked automatically), 8 GB recommended.

## Build (Windows 11 host, WSL2)

```powershell
# once, elevated: creates the Debian 13 WSL instance with the toolchain
.\tools\wsl-setup.ps1

# build the ISO and run the QEMU verification suite (about an hour the first time)
wsl -d Debian -u root -- bash /mnt/c/<path-to-repo>/build.sh --test
```

`build.sh` mirrors the repo to `/srv/eternity-build`, renders the branding,
downloads the models (checksums in `ai/models.manifest`), stages the pinned
Python wheels (`ai/requirements.lock`), runs `lb build`, and copies
`out/eternity-08-0.1.0-amd64.iso` back. Builds must be reproducible: all
versions come from the lock file, the manifest and `ai/llama-cpp.version`.

Tests (`tests/run-all.sh`): direct-kernel smoke boot with the in-image
self-test, UEFI Secure Boot boot through GRUB, screenshots of GRUB, splash,
login and desktop, and a legacy BIOS boot. The runners use KVM when WSL has
`/dev/kvm`; without it (nested virtualization missing, see `docs/build-notes.md`)
they fall back to QEMU software emulation, about ten times slower.
`tests/run-chroot-checks.sh` runs the file-level and model checks natively in
the build chroot without a VM.

## Try it on this machine

```powershell
# Hyper-V (elevated): Gen 2 VM with Secure Boot, boots the ISO, logs in, runs the chat
.\tools\hyperv-test.ps1 -Iso .\out\eternity-08-0.1.0-amd64.iso -Scenario live

# USB stick (elevated): list USB disks, then write (everything on the stick is erased)
.\tools\write-usb.ps1 -List
.\tools\write-usb.ps1 -DiskNumber <N> -Iso .\out\eternity-08-0.1.0-amd64.iso -Confirm:$true
```

Boot the laptop from the stick (MSI: press F11 at power-on and pick the USB
device). Secure Boot can stay enabled.

## Layout

```
auto/           live-build auto scripts        config/   live-build inputs (packages, hooks, files)
branding/       logo, palette, renderers       ai/       lock file, model manifest, fetchers
tests/          smoke + QEMU suites            tools/    Windows-side helpers (WSL, Hyper-V, USB)
docs/           design, plan, build notes, screenshots
```
