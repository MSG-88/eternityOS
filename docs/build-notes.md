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
