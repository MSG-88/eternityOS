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
