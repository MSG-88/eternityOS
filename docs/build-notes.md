# Eternity 08 build notes

## Build host (Task 1)

- WSL2 distro `Debian` installed via `wsl --install -d Debian` (Microsoft's
  Debian 13 image, 13.5 on arrival, `full-upgrade` to 13.7 on 2026-10-23).
- live-build 1:20250505+deb13u1, debootstrap 1.0.141, QEMU 10.0.13, OVMF
  (`OVMF_CODE_4M.secboot.fd`, `OVMF_VARS_4M.ms.fd` present).
- `/dev/kvm` present inside WSL2 (nested virtualization works on this
  Windows 11 build without extra config). `.wslconfig` set to 10 GB RAM,
  8 processors, 4 GB swap, `nestedVirtualization=true` so QEMU tests have
  room. Host has 14 GB, so QEMU test VMs use 6 GB, not the 8 GB the plan
  first suggested.
- Gotchas found: `wsl --install -d Debian` returns before the distro is
  launchable (retry loop added); a `$VAR` inside `bash -lc '...'` passed
  through wsl.exe from PowerShell arrives empty, so scripts use grep/cut
  instead; salsa.debian.org serves a bot challenge to scripted downloads,
  so the fallback rootfs comes from the debuerreotype GitHub artifacts.
