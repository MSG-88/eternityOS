# Overnight report, 2026-10-25 (00:55 to morning)

Owner's asks: (1) the USB stick still lands at `grub>`: analyse whether the OS can be
installed from Windows, otherwise find and fix the boot problem; (2) work the backlog and the
interface design screen by screen, end to end, towards an AI-integrated, secure, easy OS;
(3) clear large unwanted files. Live progress page: `tests/out/live/index.html`
(http://127.0.0.1:8787/live/index.html while the local server runs).

## 1. The stick and the `grub>` prompt: settled

- **Why it failed.** The stick was written by Rufus in *ISO Image mode*: an NTFS volume with
  the ISO files copied onto it. Reproduced in QEMU with the real UEFI:NTFS partition copied
  from the stick: Debian's signed GRUB starts, but under Secure Boot it refuses to read NTFS
  (`ls (hd0,gpt1)/` → "unknown filesystem"), so it cannot find its menu and stops at `grub>`.
  The identical stick boots to the Eternity menu with Secure Boot **off**. The laptop has
  Secure Boot on, so an extracted stick can never work; the raw image can.
- **What was done.** The stick was written raw from this session (UAC on this laptop
  elevates silently) with `tools\write-usb.ps1` and verified by hashing every byte back
  against the ISO (only the GPT header sector differs; Windows rewrites it on mount). First
  with build 8 (01:20), then with build 11 (05:31) which carries the new interface.
- **Installing "from Windows".** Not possible as such: the installer (Calamares) runs
  inside the Linux live system. What *is* possible from Windows is writing the stick raw
  (done) or booting the ISO from the Windows disk through a GRUB loopback entry; the stick
  is simpler and now works. Hyper-V works too with the *Microsoft UEFI Certificate
  Authority* Secure Boot template (your two hand-made VMs used the *Microsoft Windows*
  template, which refuses Debian's shim; both were turned off and their template corrected).
- **Second, latent defect fixed.** An *installed* system booted through
  `EFI/BOOT/BOOTX64.EFI` (no NVRAM entry) also stopped at `grub>` because Calamares copied
  a bare signed GRUB there without its `grub.cfg`. Fixed (bootloader.conf + post-install.sh:
  shim + GRUB + grub.cfg, never touching a Windows-owned `EFI/BOOT`) and covered by a new
  automated test (`tests/run-qemu-install.sh boot-fallback`).

## 2. The Eternity interface and assistant (phase 2) — in build 11, on the stick

- Branding: the Möbius mark, the three-bar-E Michroma wordmark, the Nocturne palette on
  GRUB, Plymouth, greeter, desktop, icons, installer, terminal.
- Boot: Plymouth draws the hairline, assembles the mark from 48 frames, settles the
  wordmark, and lists six real boot facts (the text font is missing in build 11's initramfs,
  shows as boxes; fixed for build 12).
- First run: name, unlock methods (passphrase, PIN; face/voice marked "coming later"),
  which assistant answers (on this device / Claude / ChatGPT with your own API key kept in
  the keyring, or "keep everything on this device").
- Home: the presence at the centre of the desktop with cards (today, system, Eternity,
  recent files, and "Install Eternity 08" in live sessions), status strip, command-bar hint.
- Ask (Super+Space): streamed answers with first-token / tok/s readout; the assistant can
  act (open apps, notes, volume, settings, shell commands, search files) and every action is
  confirmed first, logged in `~/.local/state/eternity/actions.log`, and undoable from its card.
- Launcher (Super+A), Files "search by meaning" (`eternity-find`, on-device embeddings),
  Monitor (Super+M), Settings > Eternity ("How she shows up").
- Security: firewall default-deny inbound, AppArmor, unattended security updates, kernel
  hardening, no listening services, AI servers on loopback only, the assistant never
  escalates privileges. Verified by the in-image self-test (`check_security` PASS).

Tests: 36 host unit tests, branding test, Xvfb renders of every window, the QEMU self-test
(all PASS on build 10/11), visual screenshots in `docs/screenshots/build11-*.png`.

## 3. Disk clean-up (asked at 01:50)

Deleted: stale WSL swap files (3.3 GB), old Remote Desktop diagnostics (1.3 GB), temp
files, pip/npm caches (0.8 GB); hibernation turned off (6 GB, also needed for dual boot).
Left for you to decide: `C:\HyperV\DevVM\MSG.VHDX` (115.5 GB, untouched since March),
the Hugging Face model cache (4.6 GB), the Ubuntu WSL distro (15 GB), `Downloads\claude`
(1.2 GB). C: went from 0.5 GB free to about 48 GB.

## What to do this morning

1. Boot the laptop from the stick (F11), Secure Boot on. Log in as `eternity` /
   `eternity`, walk the first-run wizard, press Super+Space and ask something.
2. To install: click "Install Eternity 08" on the home screen. Dual boot keeps Windows'
   own boot loader; GRUB lists Windows.
3. Decide on the 115 GB DevVM disk.

Details and every result: `docs/build-notes.md`; direction and statuses: `docs/backlog.md`.
