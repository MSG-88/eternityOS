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
