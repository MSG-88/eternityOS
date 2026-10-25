# Eternity 08

A lightweight Linux operating system (Debian 13 "trixie" base, newest backports
kernel, XFCE desktop) with Eternity 08 branding end to end and a local AI stack
built in: Python 3.13 with PyTorch, Transformers, scikit-learn, pandas and
Jupyter in `/opt/eternity/venv`, llama.cpp, and two bundled Apache-2.0 models
(Qwen3.5-4B and Qwen3.5-2B, GGUF) that run offline on the CPU.

Phase 1 = the OS itself. Phase 2 (on this branch, from build 10) = the Eternity
interface and the assistant: one presence at the centre of the desktop, a command bar
(Super+Space) that answers from the on-device model or, if you choose, from Claude or
ChatGPT with your own key, actions that are always confirmed and can be undone, search
by meaning over your files, and a security baseline (firewall default-deny, AppArmor,
unattended security updates). Phase 3 adds Windows application compatibility. Design
capture: `docs/design/README.md`; direction: `docs/backlog.md`.

## Live session

- Boot the ISO. GRUB offers **Eternity 08 Live**, a safe-graphics entry and a
  self-test entry.
- Login screen: user `eternity`, password `eternity`.
- First login: the **first-run wizard** (your name, unlock methods, which assistant
  answers). The desktop is the **presence**: the mark at the centre with cards for today,
  the system, Eternity and your recent files; in a live session a card offers
  **Install Eternity 08**.
- **Super+Space** opens Ask Eternity (type a question, `> cmd` for a shell command,
  `/help`), **Super+A** the radial launcher, **Super+M** the monitor; Settings > Eternity
  (`eternity-settings`) is "How she shows up". `eternity-find` searches files by meaning.
- Terminal: `eternity-chat` (interactive), `eternity-chat --ask "..."`,
  `eternity-ai status`, `eternity-ai models`, `eternity-ai serve`.
- Everything the assistant does is confirmed first and logged in
  `~/.local/state/eternity/actions.log`; API keys live in the keyring; nothing is sent
  anywhere unless you chose a cloud assistant.
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
login and desktop, a legacy BIOS boot, and a boot from the ISO attached as a USB
disk (the hybrid-image path a written stick takes, `tests/run-qemu-usb.sh`). The
runners use KVM when WSL has `/dev/kvm`; without it (nested virtualization missing,
see `docs/build-notes.md`) they fall back to QEMU software emulation, about ten times
slower.
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
device; ASUS ROG: Esc or F8 at power-on, pick the stick in the one-time boot menu and leave
the boot order alone). Secure Boot can stay enabled. Per-machine notes and the test plan for
the second test laptop, an ASUS ROG Strix SCAR 16 G635LW, are in `docs/hardware/asus-g635lw.md`.

**Write the image raw.** The ISO is a hybrid image: copied byte for byte it brings its
own partition table (an EFI System Partition with shim and GRUB, the ISO9660 filesystem
on the whole device). Tools that *extract* the ISO onto a filesystem produce a stick this
boot chain cannot use **with Secure Boot on**. Rufus reports "ISOHybrid image detected"
and defaults to **ISO Image mode**; because `live/filesystem.squashfs` is larger than
4 GB it then formats the stick NTFS. Debian's signed GRUB refuses to read NTFS while
Secure Boot lockdown is active ("unknown filesystem" for the partition it was started
from), so it cannot find its menu and stops at a bare `grub>` prompt; the identical stick
boots with Secure Boot disabled. Both facts were reproduced in QEMU on 2026-10-25
(`docs/build-notes.md`). Pick **DD Image mode** in Rufus, or use `tools\write-usb.ps1`
(run it from an elevated PowerShell; it verifies the write), or balenaEtcher (always raw).
The raw image boots to the menu as a USB disk under OVMF Secure Boot and under SeaBIOS
(`tests/run-qemu-usb.sh`).

If the firmware starts GRUB but shows only a `grub>` prompt: `ls` lists the devices;
`ls (hd0,gpt1)/` answering "unknown filesystem" means an NTFS (extracted) stick, rewrite
it raw. On a raw stick `search --file --set=root /.disk/info` followed by
`configfile ($root)/boot/grub/grub.cfg` brings the menu up.

Windows blocks unsigned scripts by default; run them as
`powershell -ExecutionPolicy Bypass -File .\tools\write-usb.ps1 -List` (same for
the Hyper-V driver) or set `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` once.

## Layout

```
auto/           live-build auto scripts        config/   live-build inputs (packages, hooks, files)
branding/       logo, palette, renderers       ai/       lock file, model manifest, fetchers
tests/          smoke + QEMU suites            tools/    Windows-side helpers (WSL, Hyper-V, USB)
docs/           design, plan, build notes, screenshots
```

## Try it in a VM on this laptop (Hyper-V, no scripts needed)

Hyper-V works even though WSL lost nested virtualization. In Hyper-V Manager:

1. New > Virtual Machine > Generation 2; 4096 MB or more (8192 MB to use the default
   4B model); 4 virtual processors; a 40 GB dynamic disk (only needed to install).
2. Settings > Security: Secure Boot enabled, template **Microsoft UEFI Certificate
   Authority** (the ISO boots through Debian's signed shim).
   With the default *Microsoft Windows* template the VM refuses Debian's shim ("The
   image's hash and certificate are not allowed (DB)", then "No operating system was
   loaded"): that is the template, not the ISO. A Generation 1 VM has no UEFI at all.
3. Settings > SCSI Controller > DVD Drive: attach `out\eternity-08-0.1.0-amd64.iso`;
   Firmware: put the DVD drive first in the boot order.
4. Connect and start. GRUB > Eternity 08 Live > greeter: user `eternity`, password
   `eternity`. The desktop has **Eternity Chat** and **Install Eternity 08**.

Or, from an elevated PowerShell, `.\tools\hyperv-test.ps1 -Iso .\out\eternity-08-0.1.0-amd64.iso -Scenario live`
does the same and takes screenshots.

## Installing next to Windows (dual boot)

The installer offers **Install alongside** when it finds a resizable partition, and GRUB
on the installed system lists Windows (os-prober is enabled). Before you start:

- If BitLocker is on for the Windows drive, shrink the Windows partition from Windows
  first (Disk Management > Shrink Volume, 40 GB or more) and suspend BitLocker for the
  reboot; Linux cannot resize an encrypted NTFS volume.
- Keep Secure Boot on; boot the stick with F11 and pick the USB device.
- Choose the free space (or **Install alongside**), create your user, and install. The
  live user and the installer are removed from the installed system; `eternity-chat`
  and the models are kept.
