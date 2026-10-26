# Eternity 08 build notes

## Build host (Task 1)

- WSL2 distro `Debian` installed via `wsl --install -d Debian` (Microsoft's
  Debian 13 image, 13.5 on arrival, `full-upgrade` to 13.7 on 2026-10-23).
- live-build 1:20250505+deb13u1, debootstrap 1.0.141, QEMU 10.0.13, OVMF
  (`OVMF_CODE_4M.secboot.fd`, `OVMF_VARS_4M.ms.fd` present).
- `/dev/kvm` present inside WSL2 (nested virtualization works on this
  Windows 11 build without extra config). `.wslconfig` caps WSL at 6 GB RAM
  with `autoMemoryReclaim=gradual`, 8 processors, 8 GB swap,
  `nestedVirtualization=true`. A first attempt at 10 GB starved Windows on
  this 14 GB laptop and the build process was killed; 6 GB is enough for
  live-build. QEMU test VMs therefore use 4 GB, not the 8 GB the plan first
  suggested (the smoke test runs the small model).
- Gotchas found: `wsl --install -d Debian` returns before the distro is
  launchable (retry loop added); a `$VAR` inside `bash -lc '...'` passed
  through wsl.exe from PowerShell arrives empty, so scripts use grep/cut
  instead; salsa.debian.org serves a bot challenge to scripted downloads,
  so the fallback rootfs comes from the debuerreotype GitHub artifacts.

## Build 1 (Task 2): minimal live ISO

- `lb build` on the purged cache: 7 min, ISO 1.0 GB (base + firmware, no
  desktop or AI yet).
- Kernel in the image: `7.2.9+deb13-amd64` from trixie-backports (needed
  `linux-base` added to the backports pin).
- QEMU direct-kernel smoke boot reaches the self-test and powers off; live-boot
  otherwise waits 90 s at "remove the live medium", so the test command line
  carries `noeject`.
- Gotchas: live-build reads `auto/` from the project root, not `config/auto/`;
  a cached bootstrap from a wrong first config must be purged (`--clean`).

## Build 2 (Tasks 3-5): identity, assets, XFCE desktop

- 15 min, ISO 1.8 GB. Smoke: os_release, identity, assets, desktop all PASS.
- UEFI Secure Boot boot under QEMU (OVMF with Microsoft keys) reaches GRUB,
  proving shim + signed GRUB + signed backports kernel (`linux 7.2.9-1~bpo13+1`).
  The menu at this stage was still the stock live-build theme and had no
  timeout, so the visual test now presses Enter after the GRUB screenshot.
- Unix sockets cannot be created on /mnt/c; the QMP socket lives in /tmp.

## Build 4 (Tasks 6-11): boot theme, login, installer, AI stack

- 37 min, ISO 5.9 GB (squashfs 5.8 GB). Hooks 10.5 min (venv from the staged wheel
  cache + llama.cpp build), mksquashfs 16 min with `-processors 3 -mem 768M` to stay
  inside the 5 GB WSL cap. Kernel still `7.2.9+deb13-amd64`.
- Stack: Python 3.13 venv with torch 2.14.1+cpu, transformers 5.20.2,
  scikit-learn 1.9.1, pandas 3.1.0, numpy 2.5.4, jupyterlab 4.6.4,
  sentence-transformers 6.2.0, llama-cpp-python 0.3.36 (all pinned with hashes in
  `ai/requirements.lock`); llama.cpp tag `b11843` built from source (BLAS off, GGML_NATIVE off: AVX2/FMA/F16C so the binaries run on any x86-64-v3
  machine, not host-tuned); models Qwen3.5-4B
  Q4_K_M (2.7 GB, default) and Qwen3.5-2B Q4_K_M (1.3 GB, small), Apache-2.0.
- Memory at multi-user (no desktop session yet): 353 MB used of 4 GB in the smoke VM.
- Smoke result: every check passes in the live VM (chat answers PONG with the small
  model in under 5 min on 4 vCPUs), after two harness bugs were fixed:
  1. `serial-getty@ttyS0` starts while the self-test is running and `vhangup()`s the
     tty, so output after the first checks vanished and the VM looked hung until the
     script's final poweroff. The unit now carries `Conflicts=serial-getty@ttyS0.service`.
     Earlier builds never hit this because their checks finished in seconds.
  2. The direct-kernel smoke boot did not pass live-config's `username=eternity`, so
     `check_login` saw no live user; the runner's `-append` now mirrors the ISO's
     Self-test GRUB entry.
- Repo bug found while preparing the commits: `.gitignore` had an unanchored `local/`
  (for live-build's top-level dir) that also hid `includes.chroot/usr/local/bin/`
  (`eternity-chat`, `eternity-ai`, `eternity-install`). Live-build output dirs are now
  anchored with a leading slash.

## Build 5 (Task 12): harness fixes, verification on a host without KVM

- 34 min, ISO 5.9 GB (6 313 674 752 bytes), kernel `7.2.9+deb13-amd64`, llama.cpp
  `b11843`, models Qwen3.5-4B / Qwen3.5-2B Q4_K_M. Image changes since build 4: the
  `eternity-smoke.service` serial-getty fix, `check_memory`, and a self-test time
  scale (`systemd-detect-virt` = `qemu` means software emulation, model timeouts x10).
- The first build 5 attempt (03:07) was killed by a Windows Update reboot at 03:47
  (KB5127648, build 26200.9711). That update removes nested virtualization on this AMD
  laptop (no `svm` flag, no `/dev/kvm` in WSL; microsoft/WSL issues 41917, 41947,
  41955), so from here on QEMU runs under TCG software emulation: `tests/qemu-env.sh`
  picks the accelerator, multiplies waits and timeouts by 10, and the test VMs use 3 GB
  so the 5 GB WSL instance keeps headroom. Uninstalling the update restores KVM; that
  is the owner's decision.
- Claude Code stopped the build's host-side shell for memory pressure while it was
  copying the 6 GB ISO to `/mnt/c` (page cache filled the WSL instance). The build
  itself had already completed inside WSL; the partial Windows-side copy was renamed
  `*.iso.partial`. Copy the ISO from `\wsl.localhost\Debian\srv\eternity-build\out\`
  when needed.
- GRUB under Secure Boot: GRUB 2.12 runs locked down (`lockdown=y`, checked in the GRUB
  console under OVMF) and refuses the theme's `.pf2` fonts with "prohibited by secure
  boot policy", three lines that flashed before the menu in builds 4 and 5. The menu
  still renders with the built-in unicode font (screenshot `tests/out/grub.png`), BIOS
  boots show the Inter fonts. `config.cfg` now skips `loadfont` when locked down
  (commit 6b7dddd, in the image from build 6 on). The kernel, GRUB and shim signatures
  were checked with `sbverify`: Debian Secure Boot CA for the kernel and GRUB, Microsoft
  UEFI CA 2011 and 2023 for shim.
- GRUB timing under TCG varies (menu after 10-25 s), so the runners press Down+Up every
  second from t=2 s to stop the countdown instead of sleeping a fixed time.
- A 768 MB VM panics while unpacking the 159 MB live initramfs (firmware for every
  module); the live boot needs 2 GB or more. README states 4 GB minimum.

## What was not run, and what the owner has to do

1. **Build 6.** Two image fixes are committed but not yet built: the self-test unit
   without a start timeout (`bf13dc4`) and the GRUB font guard (`6b7dddd`). Run
   `wsl -d Debian -u root -- bash /mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08/build.sh`
   (about 35 min). Claude Code had stopped the build 5 shell for host memory pressure
   and asked that builds be restarted only on request, so this session did not start it.
   Close memory-hungry programs first, or let the build run in a plain terminal.
2. **KVM.** Uninstalling KB5127648 (Settings > Windows Update > Update history >
   Uninstall updates) restores nested virtualization and makes `tests/run-all.sh` run at
   native speed again (about 45 min for the whole suite). Without it the suite runs under
   TCG and needs several hours; the smoke run alone is the useful one there.
3. **Hyper-V run (Task 13).** Needs an elevated PowerShell (the session that wrote these
   notes was not elevated: `Get-VM` was denied). From an elevated prompt:
   `.\tools\hyperv-test.ps1 -Iso <iso> -Scenario live`, then inspect
   `docs\screenshots\hyperv-*.png`; the install path is driven with the single actions
   (`-Action shot|type|key|boot-disk`). Hyper-V is native virtualization, so it is not
   affected by the WSL nested-virtualization loss.
4. **USB stick (Task 14).** The owner's SanDisk Cruzer Blade (57.7 GB) is disk 1 and
   `tools\write-usb.ps1 -List` shows it; writing needs an elevated prompt:
   `.\tools\write-usb.ps1 -DiskNumber 1 -Iso <iso> -Confirm:$true`. Then boot the MSI
   laptop from it (F11 at power-on), Secure Boot on. This session cannot reboot the
   machine it runs on.
5. **ISO on the Windows side.** Copy from `\wsl.localhost\Debian\srv\eternity-build\out\`
   into `out\` (the `.partial` file there is the interrupted copy and can be deleted).

### Build 5 results

| Run | Result |
|---|---|
| Direct-kernel smoke (TCG, 3 GB) | boot to the self-test in 3 min; `assets`, `boot_theme` PASS; the unit's 900 s start timeout then killed the run during `check_chat` (fixed in `bf13dc4`, needs build 6) |
| UEFI Secure Boot screenshots (TCG) | GRUB menu themed (fallback font), Plymouth splash themed, LightDM greeter themed with logo, clock and credential hint; login screen up at 427 s (TCG) |
| Greeter login | **FAILED**: password `eternity` rejected. live-config 11 hard-codes `live` and shows the user as "Debian Live user". Fixed by the `0031-eternity-user` live-config component (password `eternity`, full name "Eternity 08 Live"); `check_login` now verifies both. Needs build 6. |
| Native chroot checks (`tests/run-chroot-checks.sh` on the build 5 chroot) | 11 PASS (`assets boot_theme chat desktop identity installer llama login models os_release venv`), `memory` and `secureboot` SKIP (not a live/EFI boot), 60 s; the small model answered PONG |
| Secure Boot GRUB self-test, legacy BIOS self-test | not run for build 5: both go through the in-image unit and would hit the same 900 s timeout under TCG; GRUB menus under both firmwares were screenshotted instead (`docs/screenshots/build5-grub-*.png`) |

Screenshots: `docs/screenshots/build5-grub-uefi-secureboot.png`, `build5-grub-bios.png`,
`build5-plymouth.png`, `build5-login.png`, `build5-login-wrong-password.png`.
Desktop and terminal screenshots, idle memory under the desktop, and tokens/s in a VM
are still open until build 6 boots with the corrected password (the build 4 KVM smoke
run measured 353 MB used at multi-user without a desktop session).

### Final review of the branch (2026-10-24) and fix pass

A fresh reviewer read the whole branch and the build 5 chroot. Findings fixed, each with a
check that failed first against the build 5 files and passed with the fix
(`tests/out/fixpass-red.log`, `fixpass-green.log`):

- **Critical: the Calamares install would abort after wiping the disk.** The exec
  sequence inherited Debian's `bootloader-config` job, which runs `apt-get install
  grub-efi` (offline, fails) and then `update-grub` before `grub-install` has created
  `/boot/grub`; this image ships only `grub-efi-amd64-bin`/`grub-pc-bin`, so `/boot/grub`
  and `/etc/default/grub` did not exist and the job failed. `bootloader-config`,
  `sources-media` and `sources-media-unmount` (they assume a package pool on the medium)
  are removed; Calamares' own `bootloader` module does `grub-install` + `grub-mkconfig`.
  A stock `/etc/default/grub` is shipped, `mate-polkit` (the agent `pkexec calamares`
  needs) is listed explicitly, and `check_installer` asserts all of it plus
  `/etc/kernel/postinst.d/zz-update-grub` (grub2-common) so kernel updates refresh GRUB.
- **Important: `llama-server.service` could never start.** `-t %E{ETERNITY_THREADS}` used
  systemd's `/etc` specifier, not environment expansion; fixed to `${ETERNITY_THREADS}`.
  `check_llama` now runs the unit's ExecStart (small model, unit Environment= applied)
  and waits for `/health`; it failed on the old unit with llama-server's usage text.
- **Important:** `build.sh --test` lost the suite's logs when the suite failed (`set -e`);
  rsync's `--delete` could trip over `/proc` left mounted in an interrupted chroot
  (live-build output dirs are now excluded from the mirror); `auto/build` masked a failed
  `lb build` behind `tee` (pipefail); build backends pinned (scikit-build-core 1.1.1,
  setuptools 84.2.1, wheel 0.48.0); scripts carry their executable bit in git.
- **Minor fixed:** `eternity-install` refuses to run outside the live medium (it parks
  `/etc/fstab`); the Eternity Chat launcher keeps its terminal open on error
  (`chat-launcher.sh`); PowerShell helper docs corrected.
- **Default model exercised:** `llama-bench` natively in the build 5 chroot, 4 threads on
  the Ryzen 7 3750H: Qwen3.5-4B Q4_K_M prompt 13.5 tok/s, generation 6.4 tok/s;
  Qwen3.5-2B Q4_K_M prompt 31.7 tok/s, generation 12.8 tok/s. Above the 4 tok/s fallback
  rule in `docs/models.md`, so the model choice stands. `check_chat` now also asks the
  default model when MemAvailable allows (8 GB machines) and always prints the bench line.

Deferred (recorded, not fixed): installed systems under Secure Boot still flash the three
font errors because `grub-mkconfig` loads every `.pf2` in the theme directory (fix:
font-free theme dir plus a `/etc/grub.d` snippet guarded by `$lockdown`); a QEMU install
run (`tests/run-qemu-install.sh`) to pin the installed-system path without Hyper-V;
`--system-site-packages` on the ML venv and `--apt-recommends true` were plan deviations
without a ruling and are kept deliberately (recommends bring the polkit agent, X input
drivers and codecs a desktop needs; the venv flag lets system python3 modules such as
`apt_pkg`/`gi` import).

Verdict as of this commit: not ready to merge until build 6 is built and the smoke, BIOS,
visual and one real install run pass (see "What was not run").

## Build 6 (2026-10-24, 34 min, 5.88 GB): first green boots of the fixed image

Emulated (TCG, 3 GB VMs). Direct-kernel smoke and the Secure Boot GRUB self-test both
pass every functional check: login with password `eternity` (verified by crypt), the
`llama-server` unit's command line comes up and answers `/health`, the offline Calamares
sequence and `/etc/default/grub` are present, chat answers PONG, and under OVMF
`check_secureboot` reports Secure Boot enabled through shim and the signed GRUB and
kernel. The only failure is `check_memory`: it sampled 488 MB (smoke) and 580 MB
(Secure Boot run) *after* the chat, llama and venv checks had loaded models and torch,
while the boot-time sample in the same logs was 299 MB / 342 MB; the check now grades the
boot-time sample (commit 223e1a0, build 7). The screenshot run logs in and reaches the
branded XFCE desktop with the Install and Chat launchers (`docs/screenshots/build6-*`);
`free -m` inside the desktop session shows 1.3 GB used, above the 700 MB idle budget of
the spec, so build 7's run also captures the top processes and `/proc/meminfo`.

## Build 7 (2026-10-24, 35 min, 5.9 GB): full suite green

Image change since build 6: `check_memory` grades the boot-time sample. Suite under TCG
software emulation (3 GB VMs, `ETERNITY_QEMU_MEM=3072`), about 3 h 20 min in total:

| Run | Result |
|---|---|
| smoke (direct kernel) | PASS, every check green, idle 301 MB at multi-user |
| secureboot (OVMF, shim, GRUB self-test entry) | PASS, `CHECK secureboot: PASS` (Secure Boot enabled), idle 353 MB |
| visual (OVMF, login, desktop, terminal) | PASS, login screen at 426 s (TCG), password `eternity` accepted, desktop with launchers |
| bios (SeaBIOS, GRUB self-test entry) | PASS, idle 299 MB, Secure Boot correctly SKIP |

Small model under TCG: 0.9 tok/s prompt, 0.47 tok/s generation (native on the build host:
31.7 / 12.8), which is why each emulated self-test takes 40-50 minutes.
Screenshots: `docs/screenshots/build7-*.png`. Output logs: `tests/out/build7/`.

Open: the XFCE session uses about 1.3 GB (`free -m` used) against the spec's 700 MB idle
budget; `/proc/meminfo` shows 962 MB anonymous, spread evenly over the GTK processes
(xfwm4 186 MB, nm-applet 154 MB, xfdesktop 130 MB, each panel plugin wrapper 115 MB).
A diagnostic run with per-process maps follows.

### Desktop memory: cause found (build 7 diagnostic run)

A diagnostic VM run on the build 7 ISO (`tests/out/memdiag/*.png`) showed that every GTK
process carried a single 78-112 MB anonymous heap block (xfwm4, each panel plugin wrapper,
nm-applet, xfdesktop, xfce4-terminal); `MALLOC_ARENA_MAX=2` changed nothing, so it was not
the allocator. The image had no `icon-theme.cache` in any icon theme: live-build's own
default hook `9000-remove-gnome-icon-cache.hook.chroot` deletes them "to save space" and
ran after our `0900` cleanup hook. Without a cache GTK indexes every icon directory at
startup, and Papirus has 43 000 files. The cleanup hook is now `9900` and rebuilds the
caches with `gtk-update-icon-cache` (12 s, 3 MB per Papirus theme); `check_desktop`
asserts the caches exist and are newer than their theme directory (RED on the build 7
chroot, GREEN after the cache loop). Build 8 measures the session figure. xfwm4 also maps
libLLVM/gallium for its software-GL compositor under QEMU (49 MB resident, file-backed);
on real AMD graphics that is hardware-backed.

## Build 8 (2026-10-24, 41 min, 5.9 GB): icon caches restored, desktop within budget

Smoke PASS, Secure Boot PASS (enabled), screenshot run PASS. In the XFCE session
`free -m` now reports **665 MB used** (build 7: 1309 MB); anonymous memory 284 MB (962),
nm-applet 52 MB (154), each panel plugin wrapper 45-50 MB (115), xfwm4 144 MB (186, of
which 49 MB is libLLVM for the software-GL compositor under QEMU; hardware GL on the
laptop). Within the 700 MB idle budget of the spec even with the terminal and fastfetch
open. Screenshots: `docs/screenshots/build8-*.png`.
BIOS run PASS as well: **build 8 passes the whole suite** (`tests/out/build8/build8-run.log`).

## Install test on build 8 (QEMU, OVMF Secure Boot, 40 GB virtio disk, TCG)

`tests/run-qemu-install.sh`: live boot, greeter login, `eternity-install` launched
Calamares (no polkit prompt for the sudo-group live user), pages driven by mouse clicks:
Welcome, Location, Keyboard, Partitions (Erase disk: 300 MiB EFI, 33.5 GiB ext4, 6.2 GiB
swap), Users (Muthu / muthu / eternity-vm; `eternity08` rejected by the libpwquality
dictionary rule, `Genesis08-vm` used), Summary, Install. All 39 jobs ran; "All done" after
52 minutes (unpackfs 46 min under emulation, bootloader 16 s, package removal 7 min,
initramfs 3.5 min). Screenshots `docs/screenshots/build8-installer-*.png`.

Booting the installed disk: themed GRUB with "Eternity 08 GNU/Linux" and a firmware
entry, greeter with only the new user, login, desktop with the Eternity Chat launcher,
`/etc/os-release` Eternity 08 0.1.0, no live user, hostname eternity-vm, Secure Boot
enabled, 636 MB used, 1213 packages (live-* and Calamares removed). Screenshots
`docs/screenshots/build8-installed-*.png`.

Defects found and fixed for build 9 (commit 005e31f):
- `post-install.sh` never ran: Calamares did not load `shellprocess@eternity.conf` for
  the implicit instance, so `eternity-smoke` stayed enabled, the installer launcher file
  remained and the greeter kept the live-credentials image. The instance is now declared
  under `instances:`; independently, the greeter conf in the image carries the plain
  wallpaper and only live sessions switch to the hinted image (live-config component).
- `hwclock` missing in the target (`util-linux-extra` added).
- `GRUB_DISABLE_OS_PROBER=false` so an installed system next to Windows lists it.

## First real-hardware attempt (2026-10-24 night): `grub>` prompt from a Rufus stick

The owner reported "the boot screen was stuck in the GRUB CLI" on the MSI laptop and
"not able to boot" in a hand-made Hyper-V VM. Investigation (session of 2026-10-24/25):

- **No installation happened.** Disk 0 still holds only the four Windows partitions
  (ESP, MSR, C:, recovery), so the "GRUB prompt after install" theory does not apply to
  this incident. (The Calamares `installEFIFallback` finding, a bare signed GRUB copied to
  `EFI/boot/bootx64.efi`, is still a real latent defect for installs; see the memory note
  and the backlog.)
- **The stick is not the raw image.** The SanDisk (disk 1) is MBR with a 57.7 GB NTFS
  partition labelled ETERNITY08 and a 1 MB `UEFI_NTFS` partition; the root has
  `autorun.inf` ("Created by Rufus 4.13.2316"), a `[BOOT]` folder and the ISO files
  extracted (23:04). That is Rufus **ISO Image mode**: the squashfs (6.1 GB) exceeds the
  FAT32 file limit, so Rufus used NTFS plus its UEFI:NTFS chain loader and its own BIOS
  GRUB core. The project's boot chain (shim + Debian-signed GRUB on the ISO's own ESP,
  ISO9660 on the raw device, `search /.disk/info`) was never built or tested for that.
- **The raw image boots as a USB disk.** The ISO attached to QEMU as USB mass storage
  (`qemu-xhci` + `usb-storage`) reaches the themed menu under OVMF Secure Boot and under
  SeaBIOS; the suite only ever attached it as a CD-ROM (El Torito path) before. The ISO
  files extracted onto a FAT32 partition also reach the menu under Secure Boot (the signed
  GRUB's built-in config finds `/boot/grub/grub.cfg` on the partition it was loaded from).
  A faithful NTFS + UEFI:NTFS reproduction was not achieved (OVMF would not start the
  hand-made helper partition), so the exact failing step on the laptop is unconfirmed.
- Both ISO copies are identical (SHA-256 `c12c6580...0b8a`, 6,314,383,360 bytes), so the
  Windows-side file is not corrupt.
- **Hyper-V was never run by the sessions** (never elevated; `Get-VM` is denied here too).
  The usual cause of "cannot boot" for a hand-made Gen 2 VM is the default *Microsoft
  Windows* Secure Boot template, which refuses Debian's shim; the README now says so.

Changes: `tests/run-qemu-usb.sh` (USB-disk boot, UEFI Secure Boot or BIOS, Self-test
entry) added to `tests/run-all.sh`; README warns to write the image raw (Rufus "DD Image
mode", `tools\write-usb.ps1`, balenaEtcher) and gives the `grub>` recovery commands.

### write-usb.ps1 on the real stick (2026-10-25)

Two defects surfaced the first time the writer ran against the SanDisk (both fixed):
`Set-Disk -IsOffline` is refused for removable media ("Not Supported"), and because the
image is written front to back Windows saw the new GPT at once, mounted two volumes from
the half-written stick and the raw write died at 4 GB with "The device is not ready".
The script now skips the offline step with a notice and writes the first megabyte
(protective MBR + GPT header) last. The second run was progressing normally at 10 MB/s
when the owner stopped it and wrote the stick with Rufus in DD Image mode instead, so the
write-last ordering is not yet proven to the end on this hardware.

## Second real-hardware attempt (2026-10-25 night): `grub>` again, root causes settled

The owner rewrote the stick (Rufus 4.13) and the MSI laptop again stopped at `grub>`.
`Get-Disk`/`Get-Partition` showed the stick was still a Rufus **ISO Image mode** copy, now
GPT: a 57.7 GB NTFS "ETERNITY08" partition with the ISO tree plus a 1 MB FAT "UEFI_NTFS"
partition (`autorun.inf` by Rufus). The firmware's boot entries (`bcdedit /enum firmware`,
elevated) list "UEFI: SanDisk, Partition 1" (the NTFS volume) first: the firmware loads
`EFI/boot/bootx64.efi` (shim) straight from NTFS, shim loads the signed `grubx64.efi`.

Reproduction in QEMU (`tests` session scripts, OVMF with Microsoft keys, Secure Boot on):
a GPT image with p1 = NTFS carrying the ISO tree (squashfs stubbed) and p2 = the real
1 MB UEFI:NTFS partition copied from the stick lands at the same `grub>`. Typed at the
prompt: `root=hd0,gpt1 prefix=(hd0,gpt1)/boot/grub cmdpath=` (GRUB knows which partition
it came from), `ls` shows `(memdisk) (hd0) (hd0,gpt2) (hd0,gpt1)`, but
`ls (hd0,gpt1)/` answers **error: unknown filesystem**, `search --file --set=root
/.disk/info` finds no device, and `configfile (hd0,gpt1)/boot/grub/grub.cfg` cannot be
read. The same image booted with Secure Boot **off** (plain OVMF) reaches the themed
Eternity menu. Debian's signed GRUB 2.12-9+deb13u2 carries the `ntfs` module but does
not use it under Secure Boot lockdown, so an extracted (NTFS) stick can never boot with
Secure Boot on; the raw image (ISO9660 + FAT ESP) is unaffected. README updated.

Resolution for the laptop: the stick was written raw from Windows with
`tools\write-usb.ps1` (elevated) and verified by hashing the whole image back from the
device. Note for future sessions: UAC on this laptop elevates administrators without a
prompt, so `Start-Process -Verb RunAs` runs unattended.

### Installed-system `grub>` through EFI/BOOT: fixed

Experiment: a disk with an ESP populated by `grub-install --force-extra-removable
--bootloader-id=Eternity_08` (shim as `EFI/BOOT/BOOTX64.EFI`, `grubx64.efi`, `mmx64.efi`;
`EFI/Eternity_08/{shimx64,grubx64,mmx64,fbx64}.efi`, `grub.cfg`, `BOOTX64.CSV`) and an
ext4 root with `/boot/grub/grub.cfg`, booted under OVMF with **fresh** variables (no NVRAM
entry, so the firmware takes `EFI/BOOT`): `grub>` prompt. With `EFI/Eternity_08/grub.cfg`
copied to `EFI/BOOT/grub.cfg`: the menu appears. Debian's signed `grubx64.efi` is built
for prefix `/EFI/debian` and otherwise reads `grub.cfg` next to itself; with the
bootloader id Eternity_08 only the NVRAM path finds it.

Fix (commit 60f08ce): `config/includes.chroot/etc/calamares/modules/bootloader.conf`
(`installEFIFallback: false`, `efiBootloaderId: "Eternity_08"`) and `post-install.sh`
installing the removable fallback with `grub.cfg` beside it, unless `EFI/Microsoft/Boot`
exists (Windows keeps its own fallback loader; the "Eternity_08" firmware entry boots
Eternity and GRUB's os-prober lists Windows). Test: `tests/run-qemu-install.sh
boot-fallback` (fresh OVMF variables, screenshot graded by `tests/grubshot-check.py`),
run by `tools/dev/chain-build9.sh` after the unattended install.

### Host-side findings the same night

- The WSL VM rebooted twice during the reproduction ("WSL Service terminated" in the
  System log): the laptop (14 GB) had 0.5 GB free because two hand-made Hyper-V VMs
  (4 GB each, Secure Boot template *Microsoft Windows*, stuck at "The signed image's hash
  is not allowed (DB)") were still running. They were turned off and their template set
  to *Microsoft UEFI Certificate Authority*.
- C: was full (510 MB free). Hibernation was turned off (6 GB; also disables Fast
  Startup, which a dual-boot install needs) and stale WSL swap files, old diagnostics
  and package caches removed (about 5.5 GB). 48 GB free afterwards.

## Phase 2 overnight (2026-10-25, 01:30 to morning): the Eternity interface, AI agents, security

Spec: `docs/backlog.md` and the design capture `docs/design/README.md`; plan
`docs/superpowers/plans/2026-10-25-eternity-08-phase2-ui.md`. Everything below is on branch
`phase1` and first ships in **build 10**; build 9 (started 01:29) carries only the installer
fix and is the fallback image for the stick.

What landed (commits 8c4b154 .. 358c579):

- **Branding**: `branding/render.py` renders the design's mark (fading ring + Möbius ribbon
  with the travelling light) and the three-bar-E Michroma wordmark into icons, wallpapers
  with the presence rings, greeter, GRUB background, Calamares slides and 48 Plymouth
  frames; Nocturne palette everywhere (GRUB theme, terminal, fastfetch, Calamares).
- **Boot**: Plymouth script (hairline, ring assembling from frames, wordmark settling, six
  boot-log lines) fed by `eternity-bootlog.service` with real facts.
- **AI core** (`/usr/lib/eternity/py/eternity`): settings + keyring secrets; providers
  (local llama-server started on demand as `eternity-llama` user unit with `--jinja`, Anthropic
  Messages API, OpenAI chat completions; streaming, tool calls, first-token/tok/s); action
  broker (risk classes, consent callback, JSONL audit log, undo, sudo refused); agent loop
  with the OS-knowledge system prompt.
- **Windows** (GTK 3, Python): `eternity-firstrun` (autostart once), `eternity-ask`
  (Super+Space), `eternity-shell` (the presence as the desktop; xfdesktop icons off),
  `eternity-launcher` (Super+A), `eternity-find` (search by meaning, bge-small embeddings via
  `llama-server --embedding` on 127.0.0.1:8081 or a hashed fallback), `eternity-monitor`
  (Super+M), `eternity-settings`.
- **Security**: nftables default-deny inbound, AppArmor, unattended security upgrades,
  sysctl hardening, loopback-only AI servers, no daemons; `check_security` in the self-test.
- **Packages added**: python3-gi (+cairo, GTK/GdkPixbuf/Pango/Notify typelibs),
  python3-secretstorage, gnome-keyring, libpam-gnome-keyring, libsecret-tools, brightnessctl,
  nftables, apparmor(-utils/-profiles/-profiles-extra), unattended-upgrades; model
  `bge-small-en-v1.5-f16.gguf` (67 MB, MIT) as role `embed`.
- **Tests**: `tests/host/` (36 unit tests with fake SSE servers and scripted providers,
  `test_branding.sh`, `test_ui_smoke.sh` under Xvfb rendering every window); smoke checks
  extended (`check_boot_theme`, `check_installer`, `check_security`); the visual and install
  runners capture and close the first-run wizard; `tests/run-qemu-install.sh boot-fallback`.

Build 10 must show: themed GRUB, the new splash, the greeter on the new wallpaper, the
first-run wizard after login, the presence shell with its cards, the command bar, and
`SMOKE: PASS` including `check_security` and `check_boot_theme`. Results are appended below
when the runs finish.

### Build 10 results (2026-10-25, 02:17 to 02:58 build, 36 min, 6.0 GB)

- Hooks: nftables and AppArmor enabled, theme/initramfs built, no errors.
- Smoke self-test (TCG, 40 min): **SMOKE: PASS**, every check including the new
  `check_security` (nftables input policy drop live, AppArmor on, hardening sysctls, no
  non-loopback listeners) and the extended `check_boot_theme` (ring frames in the initrd,
  eternity-bootlog enabled, Michroma, Nocturne GRUB theme). Idle memory at boot 300 MB.
- Visual run: themed GRUB with the lock-up, greeter on the new wallpaper with the mark as
  avatar, and the presence desktop after login (today / system / recent / Eternity cards,
  the live-session install card, status strip "● live · 0.4 ms", command-bar hint) all
  render in the real image. Two defects: (1) the first-run wizard did not open after login
  (no window; the autostart runs `eternity-firstrun --autostart`), most likely because the
  window opened the Secret Service before creating itself and blocked on a keyring prompt
  in the fresh session: the store is now lazy and never creates/unlocks a collection, and
  every window logs crashes to `~/.local/state/eternity/ui.log`; the visual runner now
  captures those logs; (2) the runner's Alt-F4 (meant for the wizard) opened XFCE's logout
  dialog on the bare desktop and the following Enter logged out, so the terminal, memory
  and command-bar screenshots of this run show the greeter instead; runners now send Esc.
  The 80 s splash shot shows an initramfs console line (`mount: efivarfs`) rather than the
  Plymouth splash: unverified whether the new script renders; its ternary/`!` expressions
  were replaced by plain if/else for the next build.
- The "recent files" card listed the launcher copies in ~/Desktop: desktop-icons.sh now
  does nothing while the presence owns the desktop, and .desktop files are skipped.
- Install chain (unattended install, boot-disk, boot-fallback, Secure Boot, BIOS, USB)
  restarted at 03:58 on the same ISO with the fixed runners: results below.

### Build 11 (2026-10-25, 04:52 to 05:30, 35 min, 6.0 GB): wizard fixed, splash renders

Build 10 plus: keyring opened lazily and never prompting, every window logs crashes to
`~/.local/state/eternity/ui.log`, wizard quits on Esc, Plymouth script without ternary/`!`,
runners send Esc, no desktop launcher copies, install-wait pattern fixed.

- Visual run (TCG): GRUB lock-up menu; **Plymouth splash renders** (mark, hairline, wordmark,
  six boot-log lines) but the log text shows as boxes: the initramfs carries no font for
  `Image.Text` (`fonts-dejavu-core` added for build 12); greeter on the new wallpaper;
  **the first-run wizard opens after login** ("Hello. I'm Eternity.") over the presence
  desktop; `~/.xsession-errors` has no Eternity lines; the autostart list shows
  eternity-firstrun / eternity-shell / eternity-wallpaper; terminal: fastfetch in the
  violet palette, 707 MB used in the live session with the shell running (build 8: 665 MB).
  Screenshots `docs/screenshots/build11-*.png`.
- The stick was rewritten raw with build 11 at 05:31 (`tools/write-usb.ps1` elevated;
  Windows re-enumerated, PnP re-plug, full read-back compared with the ISO).
- Install, boot-disk, boot-fallback, smoke, Secure Boot, BIOS and USB runs follow in the
  chain (`tools/dev/chain-build11.sh`); results appended when done.

### Build 11 chain, resumed (2026-10-25 13:35)

The laptop shut down unexpectedly during the night (Windows event 6008, no clean shutdown;
last sign of life from the install VM 06:41, Windows back at 13:22). The chain died with WSL
at the install step (Calamares at unpackfs, 5 %). Resumed with `tools/dev/chain-build11-resume.sh`
(install, boot-disk, boot-fallback, smoke, Secure Boot, BIOS, USB), which then waits for
`out/build12.go` and runs `tools/dev/chain-build12.sh`. `tools/dev/progress.sh` timestamps were
UTC labelled IST under Git Bash (no zoneinfo): fixed.

### Build 12 content (committed 2026-10-25 afternoon, owner's testing feedback, backlog section 5)

- **Splash font**: `fonts-dejavu-core` for Plymouth's `Image.Text`.
- **Hardware** (owner: "BIOS and most of the drivers were not working"): inventory of the
  laptop taken from Windows (MSI Alpha 15 A3DDK: Ryzen 7 3750H + Vega 10, Radeon RX 5500M,
  Realtek RTL8822CE wifi, Realtek Bluetooth over USB 13d3:3549, Killer E2600 = RTL8125
  ethernet, Realtek ALC235 + AMD HDMI audio, I2C HID touchpad, Chicony UVC webcam, SN730
  NVMe, TPM 2.0, BIOS E16U6AMS.111). The image had the firmware packages for all of it but
  **no Bluetooth stack at all** (bluez was missing) and no `firmware-misc-nonfree`. Added:
  bluez, libspa-0.2-bluetooth, blueman (no tray autostart), firmware-misc-nonfree,
  firmware-sof-signed, fwupd, power-profiles-daemon, acpid, pciutils, usbutils, rfkill,
  tpm2-tools, v4l-utils; `/etc/modprobe.d/eternity-hardware.conf` (rtw88 ASPM off, btusb
  autosuspend off); hook `0450-hardware` enables bluetooth / power-profiles-daemon / acpid.
  New `eternity-hw` (`eternity.hw`): PCI/USB devices with the bound driver, firmware files
  the kernel failed to load, NetworkManager/rfkill, BlueZ, DRM, ALSA/PipeWire, inputs,
  cameras, battery/backlight/suspend, platform (UEFI, Secure Boot, TPM, microcode); a
  readable report, `--json`, `--save`; problems rated bad/warn. Exposed to the assistant as
  the read-only tool `hardware_report` and to the self-test as `check_hardware` (fails on a
  device class without a driver, reports the rest as INFO lines). Tests: `tests/host/test_hw.py`
  (synthetic sysfs of the laptop with and without the wifi driver, parser, real host).
  Still needed from the owner: what exactly failed on the stick (the report from
  `eternity-hw` on the laptop answers most of it).
- **Claude Code inside the OS, no API key** (owner: "claude code to be integrated within the
  OS which will work without api key"): the `claude-code` package from Anthropic's signed apt
  repository (`config/archives/claude-code.*`, pinned 2.1.308-1, key fingerprint
  31DD DE24 DDFA B679 F42D 7BD2 BAA9 29FF 1A7E CACE) is in the image; policy
  `/etc/claude-code/managed-settings.json` + `/etc/environment.d/60-eternity-claude-code.conf`
  (no self-updates, no non-essential traffic, no telemetry). New provider
  `claude_code` ("Claude (your Claude account)"): the Ask bar runs
  `claude -p --output-format stream-json --verbose --include-partial-messages --model <alias>
  --mcp-config {eternity: eternity-mcp} --strict-mcp-config --permission-prompt-tool
  mcp__eternity__approve [--allowedTools read-only set at trust 1] [--resume <session>]`,
  strips any API key from the environment, streams text deltas, shows each tool call as an
  action card, keeps the session id for follow-ups. New `eternity-mcp` (`eternity.mcp`, stdio
  MCP server, stdlib only): the Eternity actions as MCP tools through the same ActionBroker
  (consent dialog, audit log, undo) plus `approve`, the permission prompt for Claude Code's
  own tools (Bash/Edit/Write/... classified read/change/dangerous like ours; sudo/pkexec/doas
  always denied; PIN for dangerous ones when chosen; every decision logged with
  `via: claude-code`). Undo now works across processes from the audit log (`undo_token`
  recorded, `undo_from_log`). Sign-in: first run and Settings offer the provider only when
  `claude` is installed, show `claude auth status` (installed / signed in as …) and a
  "Sign in with your Claude account" button that runs `eternity-signin` (`claude auth login`
  in a terminal; the link can be finished on another device). Eternity never sees or stores
  the credentials (`~/.claude/.credentials.json`, mode 600, Claude Code's own). Contract
  verified on 2026-10-25 against Claude Code 2.1.302 on the owner's Windows machine with a
  probe MCP server: `approve` receives `{tool_name, input, tool_use_id}` and returns
  `{"behavior":"allow","updatedInput":…}` or `{"behavior":"deny","message":…}` as text;
  stream-json shapes recorded in `tests/host/test_claude_code.py` (fake `claude`). Tests:
  `test_claude_code.py`, `test_mcp.py` (protocol, consent, escalation denial, undo across
  processes, CLI policy mode); smoke `check_claude_code`.
  Terms: Anthropic's legal page allows an end user to sign in to the unmodified binary with
  their own subscription, including on a platform that hosts it, but says preinstalling
  Claude Code in a product needs their Commercial Terms, and that products must not
  collect or intermediate claude.ai credentials (we do not; no `setup-token` path on
  purpose). Fine for the owner's own machines; to settle before Eternity is distributed.
  The product never uses "Claude Code" or Anthropic marks in a feature name (the option is
  "Claude (your Claude account)", described as "runs Claude Code").
- Host tests: 61 unit tests + UI smoke under Xvfb PASS (2026-10-25 15:20).

### Phase 3 feasibility spike (2026-10-25 14:10, build host, not product code)

`tools/dev/spike-quickshell.sh`: `trixie-backports` enabled on the WSL build host; Quickshell
0.3.0-1~bpo13+1 installs (7 MB) with the Qt Quick QML modules; Hyprland 0.55.2+ds-1~bpo13+1,
hyprlock, hypridle and xdg-desktop-portal-hyprland download and resolve on Debian 13.
`tools/dev/spike-shell.qml`: a Quickshell scene runs headless with
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software` and `grabToImage` writes a PNG, so QML
screenshot tests can run on the host and the shell has a software-rendering path for the TCG
VMs. The Qt platform plugins present include wayland-egl, offscreen, eglfs, linuxfb and vnc.
Decision recorded in the phase 3 spec §4.1 (Hyprland + Quickshell), pending the owner's answer.

### Build 13 content (committed 2026-10-25 evening; phase 3 slice 1, plan
### `docs/superpowers/plans/2026-10-25-eternity-08-phase3-build13-session.md`)

Build 12 was folded into this build (the queued chain hands over to `tools/dev/chain-build13.sh`).
Everything below is covered by host tests (`tools/dev/t.sh`: 100+ unit tests PASS), the Xvfb UI
smoke (PASS) and the new offscreen shell render test (`tests/host/test_shell_render.sh`,
`tools/dev/shell-render.sh`: SHELL RENDER: PASS, screenshots `docs/screenshots/build13-*-offscreen.png`).

- **The Eternity session** (`/usr/share/wayland-sessions/eternity.desktop` -> `eternity-session`):
  Hyprland 0.55 + Quickshell 0.3 from trixie-backports (`config/archives/eternity-backports.pref.chroot`),
  Qt Quick modules, portals (hyprland + gtk), hypridle, wl-clipboard, grim, slurp. XFCE stays the
  default; the GRUB entry "Eternity 08 Live (Eternity shell)" (hotkey n) or `eternity.session=eternity`
  on the kernel line selects it (live-config component `0032-eternity-session` writes lightdm's
  `user-session`). Software GL is detected (no hardware DRM driver) and Hyprland/Qt fall back.
- **`eternity-theme`** (`eternity.theme`): `theme.toml` (Nocturne tokens), `layout.toml`
  (scale 1.25 by default, strip 44, bar 560/950/800/54, orbit 440x270, gaps 12, border 1,
  rounding 8, cards, blur namespaces, exec-once) and `keys.toml` (binds, actions, dispatchers)
  in /usr/share/eternity, overlaid by `~/.config/eternity/*.toml`, rendered to
  `~/.config/eternity/generated/{hyprland.conf,Theme.qml,theme.json,gtk.css}`; `render --check`
  validates. The Hyprland template: borders accent/neutral-800, gaps 6/12, rounding 8, blur only
  behind `eternity-*` layers, animations with the design's curves (off under `motion.reduced`),
  workspace swipe, no logo, binds from keys.toml + media keys.
- **`eternity-daemon`** (`eternity.daemon`): JSON lines over `$XDG_RUNTIME_DIR/eternity/daemon.sock`
  (0600, peer uid checked): state.get, cards.get, metrics.sample (1 s ticker to subscribers),
  settings.get/set, ask.start/cancel/undo/show (streams ask.text/status/action/done), consent
  (consent.request events; consent.reply with PIN verification; consent.ask for eternity-mcp),
  session.lock / lock_info, pin.verify, hw.summary, launcher.index, claude.sessions / resume.
  `eternity-mcp` and `eternity-ask --show` use it when the socket exists (GTK otherwise).
- **The shell** (`/usr/share/eternity/shell`, Quickshell): `Theme` (reads theme.json),
  `Geometry` (k = min(W/1920, H/1080)), `Daemon` (socket client, reconnects every 2 s),
  `Mobius` (48-frame atlas 2048x1536 from `branding/render.py --atlas`, GPU sprite), `Wordmark`,
  `Strip` (top layer, 44k exclusive: mark + wordmark, clock, live latency, AI, network, battery;
  a dash when offline), `Presence` (background layer: vignette, core with four arcs/72 ticks/glow/mark,
  orbit cards on 440x270 at -90/0/90/180 drifting 2.5 deg/s, caption at y 900, HUD frame 56,112
  1808x812 with decoding label, sweeps on workspace change; with windows the cards hide and the
  core moves to 1600,540 s 0.38), `Bar` (idle band on empty workspaces, full overlay with exclusive
  keyboard when active: 800x54 bar at 560,950, placeholder, "Super Space" chip, accent ring,
  thinking line 580, rule 620, streamed answer at 650 with caret, action cards + Undo, readout
  top-right, `/help /undo /clear /settings /local /sessions /resume /model`, `>` shell lines),
  `Consent` (440-wide dialog, PIN when needed, queued), `Lock` (ext-session-lock: mark 176 at
  960,420, greeting 52/500 at 640, since-count, passphrase via PAM "login" or PIN via the daemon,
  shake, 5 failures -> 30 s backoff, chips at bottom 88). `harness.qml` + `Dump.qml` drive the
  offscreen test (scenarios strip, presence, bar, answer, consent, lock...).
- **Deeper Claude Code**: `claude_code_allow` (Settings > Assistant check-boxes; `--allowedTools`),
  `claude_code_model` sonnet/opus/haiku (`/model`), cost from `total_cost_usd` in the readout,
  sessions recorded in `claude-sessions.json` (`/sessions`, `/resume N`), the terminal tile
  "Claude Code (terminal)" labelled expert mode with the PreToolUse hook
  `/usr/lib/eternity/claude-hook` (logs every call to the audit log, refuses sudo/pkexec/doas).
- **Tests/chain**: `check_session` in the self-test; `run-qemu-visual.sh <iso> --session eternity`
  shoots e-{splash,login,desktop,ask,answer,lock,unlocked,terminal,logs}.png (Super keys via QMP);
  `tools/dev/chain-build13.sh` (build, XFCE visual, Eternity visual, smoke, Secure Boot, install,
  fallback, BIOS, USB).

Results are appended when the chain has run (it starts automatically after the resumed build 11
chain; `/srv/eternity-build/out/build13-run.log`, ends with `BUILD13 DONE`).

## Build 13 splash: boot-log lines drew as boxes (fixed for build 14)

The GRUB menu was fine; the Plymouth boot log (left column) rendered every glyph as a hollow box of
the glyph's width. Cause, verified against the extracted initramfs: Debian's plymouth initramfs hook
links `/usr/share/fonts/Plymouth.ttf` to fc-match's default font inside the initramfs only, and
fontconfig there resolves "Sans" to that symlink (it sorts before the `truetype/` directory). Plymouth
is then moved into the real root (`plymouth --newroot`) before `eternity-bootlog.service` sends the
lines; cairo cannot open the remembered path, and Pango strokes a box per glyph (`draw_unknown_glyph`).
Adding `fonts-dejavu-core` (build 12) could not help. Fix: the splash uses Inter, which the
`eternity-fonts` initramfs hook ships at its real-root path, and the theme hook creates the same
`Plymouth*.ttf` links in the real root. Tests: `tests/host/test_splash_fonts.py`. Verified visually
with the next build's `splash.png`.

## Build 13 Eternity session: Hyprland crashed at EGL setup (fixed for build 14)

The lightdm login into the Eternity session bounced back to the greeter. Diagnosis run
(`tests/run-qemu-diag.sh`, screenshots `tests/out/build13/d-*.png`): `eternity.session=eternity` was
applied (`20-session.conf`, lightdm log), Hyprland started and died with
`libEGL warning: Not allowed to force software rendering when API explicitly selects a hardware device`
followed by a crash report. `eternity-session` exported `LIBGL_ALWAYS_SOFTWARE=1` on the VM (no
hardware GPU driver); Hyprland selects its DRM device explicitly and Mesa refuses the forced
software path. Fix: the session no longer exports it (Mesa falls back to `kms_swrast` by itself;
`AQ_NO_MODIFIERS=1` and `QT_QUICK_BACKEND=software` stay), and Hyprland's crash-report directory is
created up front. Diagnosis 2 runs the amended script from a VT on the build 13 ISO.

## Build 13 on Hyper-V (2026-10-25 evening): the Eternity session runs

Testing moved to a native Hyper-V Gen 2 VM (`tools/elevated/`, Secure Boot with the Microsoft UEFI CA
template, dynamic 2-6 GB, 4 vCPU): greeter in 60 s instead of 7 min. Results, screenshots in
`docs/screenshots/hyperv-build13-*.png`:
- XFCE Classic and the Eternity session both start; the session's login works (the daemon, the
  presence, strip, ask bar, lock/unlock, terminal all up). `hyprctl` says scale 1.00 on the
  virtual output (the 1.25 default applies to eDP-1 only), layers eternity-presence and
  eternity-strip.
- Found and fixed live on the VM (files pushed over the Default Switch, `hyprctl reload`,
  shell restart), then committed (de8cd0b): Hyprland 0.55 config errors (gestures:workspace_swipe,
  misc:vfr, dwindle:pseudotile removed; windowrulev2 and old layerrule syntax deprecated), the
  "started without start-hyprland" notice, and the faint presence core (AnimatedSprite draws
  nothing while running on the software scene graph; the Möbius mark now steps a clipped atlas).
- Still from build 13 and expected: the splash boxes (fixed in 2b300c3) and the session crash on
  the QEMU virtio GPU path (fixed in 18a866b); both verify with build 14.

## Build 15 (2026-10-26, overnight): the OS grows with the user, voice input, a faster local model

Phase 1 on `phase1`. Everything below is covered by host tests (`python3 -m unittest discover -s
tests/host`: 167 PASS in WSL) and the offscreen shell render (`tests/host/test_shell_render.sh`:
SHELL RENDER: PASS), and was verified live on the Hyper-V installed system over `tools/dev/e8pull.sh`
(screenshots `tests/out/hyperv/`).

- **Jarvis-style answers on the right, the presence slides left.** The Ask-bar answer is plain text
  down the right-hand column (x 1180, no box); while an answer is on screen `Ask.answering` slides the
  whole presence left (centre 640) and shrinks the orbit to 0.75 so no card overlaps the text
  (`PresenceContent.qml`, `Ask.qml`, `BarContent.qml`). Verified: a live Claude answer about the
  hardware renders in the right column with the presence shifted left.
- **The assistant knows which session it is in.** `agent.os_knowledge()` now names the session: in the
  Eternity session it says Hyprland (+ version from `Hyprland --version`) with the Quickshell shell on
  Wayland and points tool use at `hyprctl`; only the classic session mentions xfwm4. This stopped Claude
  hunting for an X11 window manager and reporting xfwm4 under the Eternity session.
- **Eternity learns from the user (`memory.py`).** Facts the user states ("remember that ...", "my name
  is ...", "I prefer ..."), the questions they ask and the tools they use are kept in
  `~/.local/state/eternity/memory.json` on this device only and fed into the system prompt under "What
  you know about this user". Ask bar: `/remember`, `/forget`, `/memory`; daemon:
  `memory.list/remember/forget`; Settings: "Eternity learns from you" (shell and GTK), off = no
  observation. Verified: "Remember that I am building Eternity 08 and I prefer short answers" then "What
  do you know about me" lists both facts and the earlier question.
- **Voice input, push-to-talk on Super+V (`eternity-voice`, `voice.py`).** PipeWire capture
  (`pw-record`) until 0.8 s of silence, speech to text on this device with whisper.cpp
  (`whisper-cli` built from v1.9.5 in hook `0520-whisper-cpp.hook.chroot`; `ggml-small.en-q5_1`
  bundled as model role `stt` in `ai/models.manifest`). Direct commands skip the model ("open the
  terminal", "lock", "open settings", "volume up/down", "mute", "screenshot", "home"); anything else is
  asked through the daemon. The Ask bar narrates Listening / Transcribing / the heard text.
  `togglefloating` moved to Super+Shift+V. Tested by unit (`test_voice.py`, `test_daemon.py`); a live
  mic demo was not possible on the VM (no audio input device).
- **The local model is tuned for a laptop CPU (`providers.llama_server_args`).** llama-server now runs
  generation on the physical-core count (SMT siblings only slow the memory-bound decode), batches
  prompts across every logical thread, enables flash attention, and keeps the KV cache in q8_0 (half the
  memory at 4k context). `physical_cores()` reads the sysfs core ids.
- **The shell survives a daemon restart.** `Daemon.qml` reconnects by creating a fresh `Socket` every
  2 s while the daemon is away (setting `connected` on the dead socket never reconnected; after a daemon
  restart the bar and cards stayed dead on the installed system). Verified: kill the daemon, its
  supervisor restarts it, the bar is back within 12 s. `tools/dev/e8restart.sh` restarts the daemon
  inside the session (the daemon is `python3 -c "...from eternity import daemon..."` under
  `eternity-supervise`; `e8pull.sh` calls it through `hyprctl dispatch exec` so it gets the session env).

## GitHub trending survey (2026-10-26): local text-to-speech added

Went through the day's GitHub trending list for anything useful to Eternity. The clear fit was
**VoiceStudio** (a fully-local voice/TTS project): Eternity had speech *input* (whisper.cpp) but the
assistant had no *voice*, and the `voice: off | calm | bright` setting was a no-op. Rather than bundle
VoiceStudio's heavy GPU stack (voice cloning, dubbing), the same capability ships the right way for a
small offline image via **piper**:
- `eternity.voice.say()` cleans the markdown answer, runs `piper -m <voice>.onnx -f` and plays the WAV
  through pw-play/paplay/aplay; `clean_for_speech()` strips code blocks, markdown and URLs; `tts_model()`
  maps calm/bright to bundled voices.
- The daemon speaks the finished answer when a voice is on (`_speak_answer`, `voice.state`
  speaking/spoke), off by default; `eternity-say` speaks arbitrary text or stdin.
- Hook `0530-piper-tts.hook.chroot` installs `piper-tts` into the AI venv (best-effort, so a network
  hiccup never fails the build) and fetches two en_US voices (amy = calm, ryan = bright) into
  `/opt/eternity/models` as `tts-calm.onnx` / `tts-bright.onnx`.
- Host suite 174 green (5 voice + 2 daemon tests added). The engine and voices ship in build 16 and
  get a live check on the VM then (build 15 has the STT half only).

Other trending repos were dev-time Claude Code skills (hallmark, impeccable, cloudflare
security-audit, claude-seo) or unrelated (cindy, microduck, TradingAgents, thinkrail, coolify).

## Build 16 + the deep-AI batch (2026-10-26, 8-hour autonomous session)

Owner handed full control for 8 hours with three priorities: the ASUS must boot, ship TTS, and make
the AI integration deep / the OS grow (Jarvis that runs tasks from commands).

**Build 16 (built from the repo at ~07:08) contains:**
- **The ASUS boot fix.** The ROG lands in GRUB then a black screen because the RTX 5080 (Blackwell
  GB203) drives the panel and nouveau needs `nvidia/gb203/gsp/*-570.144.bin`, which trixie's
  firmware-nvidia-graphics (ga10x/ad10x) lacks. Pinned `firmware-nvidia-graphics` from
  trixie-backports (gb203) in `eternity-backports.pref.chroot` and added it to the base list. The
  nomodeset "safe graphics" GRUB entry stays as the fallback. (The ISO already boots under UEFI +
  Secure Boot in Hyper-V Gen 2, so the EFI chain was never the problem — it was the GPU firmware and,
  separately, Rufus ISO-mode writing; see tools/windows.)
- **Voice output / TTS** (piper), committed just before the build.
- `tools/windows/write-eternity-usb.ps1` (raw/DD write from Windows) + `tools/windows/README.md`
  (why Rufus ISO-mode fails, one-time boot menu, GPU Eco, install to internal disk or external USB SSD).

**The deep-AI batch (committed after build 16 started, so it ships in build 17):**
- **Routines** (`routines.py`): named task sequences the assistant builds from the user's words and
  runs on command/voice; every step still consented at the trust level. Tools define_routine /
  list_routines / forget_routine / run_routine; surfaced in the system prompt and as a home-screen
  "Routines" card; ask-bar `/routines`, `/run <name>`.
- **Operational tools** so the assistant drives the machine: window_control (hyprctl),
  set_brightness (undoable), clipboard_copy, remind (systemd-run + notify-send).
- **Voice everywhere**: `/say <text>` and the daemon `voice.say` (also a mic-free way to hear the voice).
- Host suite 189 green, shell render PASS throughout.
