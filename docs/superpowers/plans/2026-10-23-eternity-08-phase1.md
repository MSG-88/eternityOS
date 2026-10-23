# Eternity 08 Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce `eternity-08-0.1.0-amd64.iso`, a branded Debian 13 live/installable ISO with a preinstalled Python ML stack and two bundled open-licensed GGUF models, built by one script and verified by automated QEMU smoke tests plus a Hyper-V boot-and-install run.

**Architecture:** Debian `live-build` drives the whole image from a `config/` tree in this repo: package lists, `includes.chroot/` files copied verbatim into the OS, and `hooks/` that run inside the chroot (venv creation, llama.cpp build, model placement). Branding is plain files (os-release, GRUB/Plymouth/LightDM/XFCE configs, PNG/SVG assets) under `includes.chroot/`. A self-test systemd unit inside the image runs `smoke.sh` when booted with `eternity.test` on the kernel command line and reports over the serial console, so QEMU in WSL2 can verify every build headlessly.

**Tech Stack:** Debian 13 "trixie" (amd64), live-build, debootstrap, squashfs-tools, xorriso, GRUB + shim-signed (Secure Boot), Plymouth, LightDM + lightdm-gtk-greeter, XFCE 4.20, Calamares, Python 3.13 venv (NumPy, pandas, SciPy, scikit-learn, Matplotlib, Jupyter, PyTorch CPU, Transformers, sentence-transformers, llama-cpp-python, huggingface_hub), llama.cpp (CPU), GGUF models, QEMU + OVMF (tests), Hyper-V (PowerShell) for the on-laptop VM run.

**Spec:** `docs/superpowers/specs/2026-10-23-eternity-08-phase1-design.md`

## Global Constraints

- Base: Debian 13 "trixie" at its current point release on build day (13.7 as of 2026-10-23), amd64 only.
- Kernel: newest `trixie-backports` `linux-image-amd64` on build day, not pinned. Fallback to stock trixie kernel only if boot tests fail, with the reason recorded in `docs/build-notes.md`.
- Archive areas: `main contrib non-free non-free-firmware`; `trixie-backports` enabled.
- Names: OS name is exactly `Eternity 08`; `ID=eternity`; `ID_LIKE=debian`; `VERSION_ID=0.1.0`; `PRETTY_NAME="Eternity 08 0.1.0"`; default hostname `eternity`; live user `eternity` with password `eternity`; ISO filename `eternity-08-0.1.0-amd64.iso`.
- Paths inside the OS: venv at `/opt/eternity/venv`; models at `/opt/eternity/models`; branding assets at `/usr/share/eternity`; self-test at `/usr/lib/eternity/smoke.sh`.
- Models: open licences only (Apache 2.0, MIT, or equivalent). No Llama community licence. Licence text shipped next to each model file.
- No size cap on the ISO. Idle RAM after login under 700 MB. Boot to login screen under 30 s in a VM.
- No network access is required at first boot: nothing in the boot path or in `eternity-chat` fetches anything.
- Secure Boot must work: ISO boots with Secure Boot on (Debian signed shim + GRUB + signed kernel). Also boots legacy BIOS.
- Build host: a Debian 13 WSL2 instance named `Debian` on the owner's laptop, run as root. The existing `Ubuntu` WSL instance is not touched. Windows install is never modified.
- One command: `./build.sh` from a clean checkout produces the ISO; `./build.sh --test` builds then runs the QEMU smoke suite.
- Commit after every task. Commit messages end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Repo files use LF line endings (`.gitattributes` `* text=auto eol=lf`), because they are consumed inside Linux.

## Review Focus

1. **A 4 GB RAM machine runs `eternity-chat`.** Expected: it starts the small model without the user choosing. Pinned by the `MemAvailable` selection test in Task 11.
2. **First boot with no network.** Expected: desktop, login, and `eternity-chat` all work; nothing hangs on DNS or apt. Pinned by running the QEMU smoke with `-nic none` in Task 2 and keeping it that way.
3. **A legacy BIOS PC (no UEFI).** Expected: the ISO boots to the same GRUB menu and desktop. Pinned by the SeaBIOS run in Task 12.
4. **The live login screen.** Expected: no autologin; the greeter shows the Eternity 08 background and a hint with the live credentials, and `eternity`/`eternity` logs in. Pinned by the screenshot-and-sendkey test in Task 12.
5. **The installed system (after Calamares) keeps the branding and the AI stack.** Expected: after install and reboot, os-release, Plymouth, the login screen, and `eternity-chat` are identical to the live session, and the live user is gone. Pinned by the Hyper-V install run in Task 13.

---

## File structure

```
eternity-08/
  .gitattributes
  build.sh                       entry point; runs inside WSL Debian as root
  tools/
    wsl-setup.ps1                creates/updates the Debian WSL build instance
    hyperv-test.ps1              creates a Gen2 VM, boots ISO, screenshots, types keys
    hyperv-screenshot.ps1        WMI thumbnail capture helper (dot-sourced)
    write-usb.ps1                lists removable disks; writes ISO to one by number
  config/                        live-build tree (lb config output is NOT committed;
                                 only auto/ and our additions are)
    auto/config                  lb config flags (distribution, archive areas, backports,
                                 bootloaders, secure boot, iso name/volume)
    auto/clean
    auto/build
    archives/backports-kernel.pref.chroot     pin linux-image-amd64 to trixie-backports
    package-lists/
      base.list.chroot           kernel, firmware, live-*, network, shell tools
      desktop.list.chroot        xorg, XFCE, LightDM, Plymouth, themes, apps
      installer.list.chroot      calamares + settings
      ai.list.chroot             python3, venv, build-essential, cmake, libs
    hooks/normal/
      0100-identity.hook.chroot  os-release, issue, hostname, remove Debian branding bits
      0200-theme.hook.chroot     plymouth-set-default-theme, update-initramfs, grub defaults
      0500-ai-venv.hook.chroot   create /opt/eternity/venv from ai/requirements.lock
      0510-llama-cpp.hook.chroot build llama.cpp from tag in ai/llama-cpp.version
      0900-cleanup.hook.chroot   apt clean, remove caches, strip build leftovers
    includes.chroot/
      etc/os-release, etc/issue, etc/motd, etc/hostname, etc/skel/.bashrc,
      etc/lightdm/lightdm.conf, etc/lightdm/lightdm-gtk-greeter.conf,
      etc/default/grub.d/eternity.cfg, etc/xdg/xfce4/..., etc/calamares/...,
      etc/systemd/system/eternity-smoke.service, etc/systemd/system/llama-server.service,
      usr/share/eternity/   (logo.svg, logo-*.png, wallpaper-*.png, fastfetch.txt)
      usr/share/plymouth/themes/eternity/ (eternity.plymouth, eternity.script, images)
      usr/share/grub/themes/eternity/ (theme.txt, background.png, fonts)
      usr/share/applications/eternity-chat.desktop, eternity-install.desktop
      usr/share/calamares/branding/eternity/
      usr/local/bin/eternity-chat, eternity-ai
      usr/lib/eternity/smoke.sh
      opt/eternity/models/      (populated by build.sh from ai/models.manifest; gitignored)
    bootloaders/grub-pc/         copied from live-build template; grub.cfg with theme + self-test entry
  branding/
    logo.svg                     source of truth for the wordmark
    render.py                    renders logo PNGs and wallpapers into includes.chroot
    colors.md                    palette: background #070B14, panel #0D1320, accent #19D3F5, text #E6F1FF
  ai/
    requirements.in              top-level packages
    requirements.lock            pinned, generated on build day by pip-compile
    llama-cpp.version            git tag of llama.cpp to build
    models.manifest              one line per model: name|file|url|sha256|licence-url|role
    fetch-models.sh              downloads to config/includes.chroot/opt/eternity/models, verifies sha256
  tests/
    smoke.sh                     the in-image self-test (copied to /usr/lib/eternity/smoke.sh)
    run-qemu-smoke.sh            direct-kernel boot of the ISO with eternity.test, parses serial log
    run-qemu-visual.sh           OVMF Secure Boot boot; screenshots GRUB, login, desktop via QMP
    run-qemu-bios.sh             SeaBIOS boot; screenshot GRUB menu
    expect/                      expected strings used by smoke.sh (os-release etc.)
  docs/
    build-notes.md               what was built, versions, kernel chosen, test results
```

---

### Task 1: Build host (Debian 13 under WSL2)

**Files:**
- Create: `tools/wsl-setup.ps1`, `.gitattributes`, `.gitignore`
- Test: running `tools/wsl-setup.ps1` then a version check

**Interfaces:**
- Produces: a WSL distro named `Debian`, default user root, with `live-build debootstrap squashfs-tools xorriso mtools dosfstools qemu-system-x86 ovmf python3 python3-pip python3-venv python3-cairosvg python3-pil git curl ca-certificates librsvg2-bin fonts-inter fonts-jetbrains-mono` installed. Later tasks run every Linux command as `wsl -d Debian -u root -- bash -lc '<cmd>'` from the repo path `/mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08`.

- [ ] **Step 1: Write `.gitattributes` (`* text=auto eol=lf`) and `.gitignore`** (`config/` except `config/auto config/archives config/package-lists config/hooks config/includes.chroot config/bootloaders`; `config/includes.chroot/opt/eternity/models/*.gguf`; `*.iso`; `*.log`; `cache/`; `build/`; `.build/`; `chroot/`; `binary/`; `tests/out/`).
- [ ] **Step 2: Write `tools/wsl-setup.ps1`**: if `wsl -l -q` lacks `Debian`, run `wsl --install -d Debian --no-launch`; then `wsl -d Debian -u root -- bash -lc` with: write `/etc/wsl.conf` (`[user] default=root`, `[boot] systemd=true`), `apt-get update && apt-get -y full-upgrade`, install the package list above, and `wsl --terminate Debian`. Fallback if the installed image is not trixie (`VERSION_CODENAME`): `wsl --unregister Debian`, download the current `debian-13` rootfs tarball from `https://salsa.debian.org/debian/WSL/-/releases` (or `wsl --install --from-file` with the official `.wsl` image), import as `Debian`, and repeat.
- [ ] **Step 3: Run `tools/wsl-setup.ps1`** (elevated PowerShell).
- [ ] **Step 4: Verify**: `wsl -d Debian -u root -- bash -lc 'cat /etc/os-release | grep VERSION_CODENAME; lb --version; debootstrap --version; qemu-system-x86_64 --version | head -1; ls /usr/share/OVMF/'` prints `trixie`, a live-build version `1:20250*` or newer, and `OVMF_CODE_4M.secboot.fd` plus `OVMF_VARS_4M.ms.fd` exist.
- [ ] **Step 5: Verify nested virtualization**: `wsl -d Debian -u root -- bash -lc 'ls -l /dev/kvm'` exists. If absent, add `[wsl2] nestedVirtualization=true` to `C:\Users\muthu.MSG\.wslconfig`, `wsl --shutdown`, and re-check. Record the result in `docs/build-notes.md`.
- [ ] **Step 6: Commit** `git add .gitattributes .gitignore tools/wsl-setup.ps1 docs/build-notes.md` / `chore: WSL Debian 13 build host setup`.

---

### Task 2: Minimal bootable ISO and the self-test harness

**Files:**
- Create: `build.sh`, `config/auto/config`, `config/auto/clean`, `config/auto/build`, `config/archives/backports-kernel.pref.chroot`, `config/package-lists/base.list.chroot`, `config/includes.chroot/etc/systemd/system/eternity-smoke.service`, `tests/smoke.sh`, `tests/run-qemu-smoke.sh`, `tests/expect/os-release.txt`
- Test: `./build.sh --test` prints `SMOKE: PASS`

**Interfaces:**
- Produces: `build.sh [--test] [--clean]` (root, inside WSL Debian). Writes the ISO to `out/eternity-08-0.1.0-amd64.iso` and a log to `out/build.log`. Exit code 0 on success.
- Produces: `tests/smoke.sh` contract. It runs as root inside the booted image, prints one line per check as `CHECK <name>: PASS` or `CHECK <name>: FAIL <reason>`, then `SMOKE: PASS` or `SMOKE: FAIL`, then `SMOKE_DONE`, then powers off. Checks are added by later tasks as functions named `check_<name>`; a loop calls every `check_` function.
- Produces: `tests/run-qemu-smoke.sh <iso>`: extracts `live/vmlinuz` and `live/initrd.img` with `xorriso -osirrox on -extract`, runs `qemu-system-x86_64 -enable-kvm -m 8192 -smp 4 -nic none -display none -cdrom <iso> -kernel vmlinuz -initrd initrd.img -append "boot=live components eternity.test console=ttyS0,115200 quiet" -serial file:tests/out/serial.log` with a 15-minute timeout, waits for `SMOKE_DONE`, prints the serial log's `CHECK` and `SMOKE` lines, exits 0 only on `SMOKE: PASS`.
- Produces: the `config/auto/config` flags later tasks extend: `lb config noauto --distribution trixie --archive-areas "main contrib non-free non-free-firmware" --backports true --architectures amd64 --linux-flavours amd64 --binary-images iso-hybrid --bootloaders "grub-pc,grub-efi" --uefi-secure-boot enable --debian-installer none --iso-application "Eternity 08" --iso-volume "ETERNITY08" --iso-publisher "Eternity 08" --image-name eternity-08-0.1.0 --bootappend-live "boot=live components quiet splash locales=en_US.UTF-8 username=eternity hostname=eternity live-config.noautologin" --apt-recommends false --cache-packages true --firmware-chroot true --firmware-binary true "${@}"`.

- [ ] **Step 1: Write `tests/smoke.sh`** with the contract above and one check, `check_os_release`: `grep -qx 'ID=debian' /etc/os-release` for now (Task 3 flips it to the Eternity values from `tests/expect/os-release.txt`). Also write `config/includes.chroot/etc/systemd/system/eternity-smoke.service`: `ConditionKernelCommandLine=eternity.test`, `After=multi-user.target`, `Wants=multi-user.target`, `ExecStart=/usr/lib/eternity/smoke.sh`, `StandardOutput=tty`, `TTYPath=/dev/ttyS0`, `[Install] WantedBy=multi-user.target`; the hook in Step 3 enables it. `smoke.sh` ends with `systemctl poweroff`.
- [ ] **Step 2: Write `tests/run-qemu-smoke.sh`** per the interface. Expect a failing run (no ISO yet): `bash tests/run-qemu-smoke.sh out/eternity-08-0.1.0-amd64.iso` exits non-zero with "ISO not found".
- [ ] **Step 3: Write `config/auto/config`, `config/auto/clean` (`lb clean noauto "${@}"; rm -rf config/binary config/bootstrap config/chroot config/common config/source`), `config/auto/build` (`lb build noauto "${@}" 2>&1 | tee build.log`), `config/archives/backports-kernel.pref.chroot`** (`Package: linux-image-amd64 linux-image-*-amd64 linux-headers-* / Pin: release n=trixie-backports / Pin-Priority: 600`), and **`config/package-lists/base.list.chroot`**: `linux-image-amd64 live-boot live-config live-config-systemd systemd-sysv firmware-linux firmware-linux-nonfree firmware-amd-graphics firmware-iwlwifi firmware-realtek firmware-atheros firmware-brcm80211 amd64-microcode intel-microcode network-manager sudo bash-completion openssh-client curl wget git vim nano htop less man-db locales console-setup keyboard-configuration xdg-user-dirs ca-certificates grub-efi-amd64-signed shim-signed grub-pc-bin`. Add `config/hooks/normal/0050-smoke.hook.chroot` that copies nothing (smoke.sh is placed by build.sh) but runs `systemctl enable eternity-smoke.service`.
- [ ] **Step 4: Write `build.sh`**: `set -euo pipefail`; refuse to run unless `id -u` is 0 and `/etc/os-release` says trixie; `cd` to repo; copy `tests/smoke.sh` to `config/includes.chroot/usr/lib/eternity/smoke.sh` (mode 755); `--clean` runs `lb clean --purge`; always `lb clean` then `lb config` (via `auto/config`) then `lb build`; move the produced `*.iso` to `out/eternity-08-0.1.0-amd64.iso`; print size; with `--test` run `tests/run-qemu-smoke.sh out/...iso`. Because the repo lives on `/mnt/c` (slow, no chroot-safe permissions), `build.sh` must rsync the repo to `/srv/eternity-build/` inside WSL, build there, and copy `out/` back. Make that explicit in a comment.
- [ ] **Step 5: Run `./build.sh --test`** from WSL Debian root. Expected: ISO produced, `CHECK os_release: PASS`, `SMOKE: PASS`. Record kernel version booted (from serial log `uname -r` line printed by smoke.sh at the top) in `docs/build-notes.md`; it must be the backports 7.x kernel. If `lb build` fails on Secure Boot packages or backports, fix the config, not the requirement; only after a verified boot failure may the kernel fall back (Global Constraints).
- [ ] **Step 6: Commit** `feat: minimal trixie live ISO with QEMU self-test harness`.

---

### Task 3: System identity

**Files:**
- Create: `config/includes.chroot/etc/os-release`, `config/includes.chroot/etc/issue`, `config/includes.chroot/etc/issue.net`, `config/includes.chroot/etc/motd`, `config/includes.chroot/etc/hostname`, `config/includes.chroot/etc/skel/.bashrc`, `config/includes.chroot/usr/share/eternity/fastfetch.txt`, `config/includes.chroot/etc/skel/.config/fastfetch/config.jsonc`, `config/hooks/normal/0100-identity.hook.chroot`, `tests/expect/os-release.txt`
- Modify: `tests/smoke.sh` (`check_os_release`, add `check_identity`), `config/package-lists/base.list.chroot` (add `fastfetch`)

**Interfaces:**
- Produces: `/etc/os-release` with exactly: `PRETTY_NAME="Eternity 08 0.1.0"`, `NAME="Eternity 08"`, `VERSION_ID="0.1.0"`, `VERSION="0.1.0 (Genesis)"`, `VERSION_CODENAME=genesis`, `ID=eternity`, `ID_LIKE=debian`, `HOME_URL="https://eternity08.local"`, `LOGO=eternity`, `ANSI_COLOR="0;36"`. Note: `/etc/os-release` on Debian is a symlink to `/usr/lib/os-release`; the hook replaces `/usr/lib/os-release` and keeps the symlink.
- Produces: `/usr/share/eternity/fastfetch.txt`, an ASCII-art wordmark used by the fastfetch config (`"logo": {"source": "/usr/share/eternity/fastfetch.txt", "type": "file"}`), and `.bashrc` in skel that runs `fastfetch` on interactive login shells and sets `PS1` to `\[\e[36m\]eternity\[\e[0m\]:\w\$ `.

- [ ] **Step 1: Write `tests/expect/os-release.txt`** with the exact os-release lines above, and change `check_os_release` to `diff <(sort /etc/os-release) <(sort /usr/lib/eternity/expect/os-release.txt)`; add `check_identity`: `/etc/hostname` is `eternity`, `/etc/issue` contains `Eternity 08`, `fastfetch --logo-type file --logo /usr/share/eternity/fastfetch.txt` exits 0. `build.sh` copies `tests/expect/` into `config/includes.chroot/usr/lib/eternity/expect/`.
- [ ] **Step 2: Run the smoke against the Task 2 ISO** (`tests/run-qemu-smoke.sh`): expected `CHECK os_release: FAIL`, because the live image is still Debian.
- [ ] **Step 3: Write the identity files and `0100-identity.hook.chroot`**: `cp /etc/os-release.eternity /usr/lib/os-release` pattern (ship the file as `includes.chroot/usr/lib/os-release` directly instead; then the hook only needs to `rm -f /etc/os-release && ln -s ../usr/lib/os-release /etc/os-release`), remove `/etc/update-motd.d/10-uname`, set `/etc/issue` to `Eternity 08 0.1.0 \n \l` and `/etc/motd` to a two-line banner. `/etc/hostname` = `eternity`. The `live-config` hostname is already set by `--bootappend-live hostname=eternity`.
- [ ] **Step 4: Rebuild and test**: `./build.sh --test`. Expected `CHECK os_release: PASS`, `CHECK identity: PASS`, `SMOKE: PASS`.
- [ ] **Step 5: Commit** `feat: Eternity 08 system identity (os-release, issue, motd, fastfetch)`.

---

### Task 4: Visual assets (logo, wallpapers, palette)

**Files:**
- Create: `branding/logo.svg`, `branding/colors.md`, `branding/render.py`, outputs under `config/includes.chroot/usr/share/eternity/`: `logo.svg`, `logo-64.png`, `logo-128.png`, `logo-256.png`, `logo-512.png`, `wallpaper-1920x1080.png`, `wallpaper-2560x1440.png`, `wallpaper-3840x2160.png`, `greeter-1920x1080.png`
- Test: `tests/smoke.sh` `check_assets` (all files above exist and are non-empty; `file` reports PNG with the right dimensions)

**Interfaces:**
- Produces: the palette in `branding/colors.md`: background `#070B14`, panel `#0D1320`, accent `#19D3F5`, accent-dim `#0E8FA8`, text `#E6F1FF`, muted `#7C8BA1`. The wordmark: "ETERNITY" in Inter (bold, letter-spaced) with "08" in the accent colour, a thin ring motif behind "08". Wallpaper: background colour with a soft radial accent glow in the lower right and the wordmark small at the lower right (greeter variant: wordmark centred, larger).
- Produces: `python3 branding/render.py` is idempotent and run by `build.sh` before `lb build` (so PNGs can be regenerated, though they are also committed).

- [ ] **Step 1: Add `check_assets` to `tests/smoke.sh`** asserting each path exists and `python3 -c "from PIL import Image; ..."`-free: use `file wallpaper-1920x1080.png | grep -q '1920 x 1080'` style checks (`file` is in base).
- [ ] **Step 2: Write `branding/logo.svg` and `branding/colors.md`**; write `branding/render.py` using `cairosvg` for logo PNGs and `Pillow` for wallpapers (draw gradient + glow + paste logo). Fonts: `fonts-inter` path `/usr/share/fonts/truetype/inter/`; verify the path on the build host and embed as `font-family` in the SVG.
- [ ] **Step 3: Run `python3 branding/render.py`** on the build host; open `wallpaper-1920x1080.png` and `logo-512.png` with the Read tool and confirm they match the description (dark navy, cyan 08, legible wordmark). Iterate until they do.
- [ ] **Step 4: Rebuild and test**: `./build.sh --test` → `CHECK assets: PASS`.
- [ ] **Step 5: Commit** `feat: Eternity 08 logo, palette and wallpapers`.

---

### Task 5: Desktop (XFCE), theme defaults, and essential apps

**Files:**
- Create: `config/package-lists/desktop.list.chroot`, `config/includes.chroot/etc/xdg/xfce4/xfconf/xfce-perchannel-xml/{xsettings.xml,xfce4-desktop.xml,xfwm4.xml,xfce4-panel.xml}`, `config/includes.chroot/etc/xdg/xfce4/panel/default.xml`, `config/includes.chroot/etc/xdg/xfce4/helpers.rc`, `config/includes.chroot/etc/gtk-3.0/settings.ini`, `config/includes.chroot/usr/share/icons/hicolor/{64x64,128x128,256x256}/apps/eternity.png` (copies of the logo), `config/includes.chroot/usr/share/pixmaps/eternity.png`, `config/includes.chroot/etc/xdg/autostart/eternity-firstrun.desktop` (sets wallpaper per monitor via `xfconf-query` once, then removes its marker)
- Modify: `tests/smoke.sh` (`check_desktop`)

**Interfaces:**
- Produces package list: `xorg xserver-xorg-video-amdgpu xserver-xorg-video-intel xserver-xorg-video-nouveau xserver-xorg-input-libinput mesa-vulkan-drivers xfce4 xfce4-terminal xfce4-whiskermenu-plugin xfce4-power-manager xfce4-screenshooter xfce4-pulseaudio-plugin xfce4-notifyd thunar thunar-archive-plugin xarchiver mousepad ristretto atril firefox-esr network-manager-gnome pipewire pipewire-pulse wireplumber pavucontrol arc-theme papirus-icon-theme fonts-inter fonts-jetbrains-mono fonts-noto-core fonts-noto-color-emoji dbus-x11 policykit-1 xdg-utils gvfs gvfs-backends file`.
- Produces: GTK theme `Arc-Dark`, icon theme `Papirus-Dark`, window theme `Arc-Dark`, UI font `Inter 10`, monospace `JetBrains Mono 10`, wallpaper `/usr/share/eternity/wallpaper-1920x1080.png` (xfce4-desktop `last-image` for every monitor key), panel: top, 28 px, Whisker menu with `eternity.png` as button icon and label `Eternity`, then tasklist, separator, pulseaudio, network (nm-applet via autostart), clock. Whisker menu title text "Eternity 08".

- [ ] **Step 1: Add `check_desktop`**: `dpkg -s xfce4 lightdm-gtk-greeter >/dev/null`; `grep -q 'Arc-Dark' /etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xsettings.xml`; `grep -q 'wallpaper-1920x1080.png' /etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml`; `grep -q eternity.png /etc/xdg/xfce4/panel/default.xml`.
- [ ] **Step 2: Write the package list and the XML/ini files.** Generate the xfconf XML by installing XFCE on the build host is not possible; write them by hand following the xfconf perchannel schema (`<channel name="xsettings" version="1.0"><property name="Net" type="empty"><property name="ThemeName" type="string" value="Arc-Dark"/>...`).
- [ ] **Step 3: Rebuild and test**: `./build.sh --test` → `CHECK desktop: PASS`. Also check the serial log for `uname -r` still 7.x and that the ISO size is printed.
- [ ] **Step 4: Visual check**: write `tests/run-qemu-visual.sh <iso>`: boots with `-bios`-free OVMF Secure Boot (`-drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.secboot.fd -drive if=pflash,format=raw,file=tests/out/OVMF_VARS.fd` copied from `OVMF_VARS_4M.ms.fd`), `-machine q35,smm=on -global driver=cfi.pflash01,property=secure,value=on`, `-m 8192 -smp 4 -nic none -vga virtio -display none -qmp unix:tests/out/qmp.sock,server,nowait`; a Python helper `tests/qmp.py` sends `screendump` at t=5 s (GRUB), t=40 s (login), then `send-key` sequences to type `eternity` + Enter, wait 15 s, `screendump` (desktop); saves `tests/out/{grub,login,desktop}.png` (convert PPM to PNG with Pillow). Open the three PNGs with the Read tool. At this task only `desktop.png` must show the Arc-Dark panel and wallpaper; GRUB and login are still unthemed (Tasks 6–7).
- [ ] **Step 5: Commit** `feat: XFCE desktop with Eternity 08 theme defaults and essential apps`.

---

### Task 6: GRUB theme (ISO menu and installed system) and Plymouth splash

**Files:**
- Create: `config/bootloaders/grub-pc/` (copy of `/usr/share/live/build/bootloaders/grub-pc/` with `grub.cfg` edited: `set theme=/boot/grub/themes/eternity/theme.txt`, menu entries titled `Eternity 08 Live`, `Eternity 08 Live (safe graphics)` (adds `nomodeset`), `Eternity 08 Self-test` (adds `eternity.test console=ttyS0,115200`), timeout 8; remove the Debian splash and Debian text), `config/bootloaders/grub-pc/themes/eternity/{theme.txt,background.png,unicode.pf2}` (fonts via `grub-mkfont` on build host from Inter and JetBrains Mono), `config/includes.chroot/usr/share/grub/themes/eternity/` (same theme for installed systems), `config/includes.chroot/etc/default/grub.d/eternity.cfg` (`GRUB_DISTRIBUTOR="Eternity 08"`, `GRUB_THEME=/usr/share/grub/themes/eternity/theme.txt`, `GRUB_TIMEOUT=3`, `GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"`), `config/includes.chroot/usr/share/plymouth/themes/eternity/{eternity.plymouth,eternity.script,logo.png,progress-*.png}`, `config/hooks/normal/0200-theme.hook.chroot` (`plymouth-set-default-theme -R eternity`; `sed -i 's/^GRUB_DISTRIBUTOR=.*/GRUB_DISTRIBUTOR="Eternity 08"/' /etc/default/grub`).
- Modify: `config/package-lists/desktop.list.chroot` (add `plymouth plymouth-themes plymouth-label`), `tests/smoke.sh` (`check_boot_theme`)

**Interfaces:**
- Produces: GRUB theme: background `#070B14` with the wordmark, menu box centred, selected item in accent colour, title text `Eternity 08`. Plymouth: script theme, logo centred, a thin accent progress bar below it, same background colour.

- [ ] **Step 1: Add `check_boot_theme`**: `plymouth-set-default-theme` prints `eternity`; `/usr/share/grub/themes/eternity/theme.txt` exists; `grep -q 'Eternity 08' /etc/default/grub /etc/default/grub.d/eternity.cfg`; `lsinitramfs /boot/initrd.img-* | grep -q plymouth/themes/eternity`.
- [ ] **Step 2: Write the theme files and hook.** live-build note: the ISO's GRUB reads the theme from the ISO at `/boot/grub/themes/eternity/`; live-build copies `config/bootloaders/grub-pc/` contents into the ISO's `/boot/grub/`, so put the theme at `config/bootloaders/grub-pc/themes/eternity/` and reference `($root)/boot/grub/themes/eternity/theme.txt`. Keep `grub.cfg` placeholders (`@LB_BOOTAPPEND_LIVE@`, `@KERNEL@`, `@INITRD@`, `@LINUX_LIVE@`) exactly as the template uses them.
- [ ] **Step 3: Rebuild and test**: `./build.sh --test` → `CHECK boot_theme: PASS`. Then `tests/run-qemu-visual.sh`: open `tests/out/grub.png` (themed menu with three entries) and take an extra screenshot at t=12 s saved as `splash.png` (Plymouth logo). Also run a Self-test entry boot via GRUB (not direct kernel) once: in `run-qemu-visual.sh` add `--selftest` which sends Down, Down, Enter at the menu and waits for `SMOKE_DONE` on serial; this proves Secure Boot + signed kernel + self-test entry together. Expected `SMOKE: PASS` and `check_secureboot` (added here: `mokutil --sb-state` prints `SecureBoot enabled` when `/sys/firmware/efi` exists; skipped on BIOS) PASS.
- [ ] **Step 4: Commit** `feat: Eternity 08 GRUB theme and Plymouth splash`.

---

### Task 7: Login screen (LightDM)

**Files:**
- Create: `config/includes.chroot/etc/lightdm/lightdm.conf`, `config/includes.chroot/etc/lightdm/lightdm-gtk-greeter.conf`, `config/includes.chroot/etc/lightdm/lightdm.conf.d/10-eternity.conf`
- Modify: `config/package-lists/desktop.list.chroot` (add `lightdm lightdm-gtk-greeter lightdm-gtk-greeter-settings`), `tests/smoke.sh` (`check_login`)

**Interfaces:**
- Produces: `lightdm-gtk-greeter.conf`: `background=/usr/share/eternity/greeter-1920x1080.png`, `theme-name=Arc-Dark`, `icon-theme-name=Papirus-Dark`, `font-name=Inter 11`, `default-user-image=/usr/share/eternity/logo-128.png`, `indicators=~spacer;~clock;~spacer;~power`, `clock-format=%H:%M`, `position=50%,center 50%,center`, `panel-position=bottom`, `hide-user-image=false`. `10-eternity.conf`: `[Seat:*] greeter-session=lightdm-gtk-greeter`, `user-session=xfce`, `autologin-user=` (empty), `greeter-hide-users=false`, `greeter-show-manual-login=true`, `allow-guest=false`. Live hint: live-config's `--bootappend-live live-config.noautologin` keeps the greeter; the hint text is placed in the greeter via the `default-user-image` area being the logo and a `xgreeters`-independent banner: use the greeter's `[greeter] font-name` plus a `panel` clock, and show the credentials on the greeter background image itself (render `greeter-1920x1080.png` in Task 4 with the line "Live session: user eternity / password eternity" in muted text at the bottom; the installed system's greeter uses `wallpaper-1920x1080.png` without the hint, switched by `0100-identity.hook.chroot`? No: by Calamares' post-install script in Task 9).

- [ ] **Step 1: Add `check_login`**: `grep -q 'greeter-1920x1080.png' /etc/lightdm/lightdm-gtk-greeter.conf`; `grep -q '^autologin-user=$' /etc/lightdm/lightdm.conf.d/10-eternity.conf`; `systemctl is-enabled lightdm` prints `enabled`; `getent passwd eternity` exists in the live boot.
- [ ] **Step 2: Update `branding/render.py`** to add the credential hint line to `greeter-1920x1080.png` only; re-render.
- [ ] **Step 3: Write the LightDM files.** Also confirm live-config does not re-enable autologin: `live-config` writes `/etc/lightdm/lightdm.conf.d/` overrides unless `noautologin` is set; keep `live-config.noautologin` in `auto/config` and verify by reading `/etc/lightdm/lightdm.conf.d/` in the smoke (`check_login` asserts no file there contains `autologin-user=eternity`).
- [ ] **Step 4: Rebuild and test**: `./build.sh --test` → `CHECK login: PASS`; `tests/run-qemu-visual.sh`: `login.png` shows the greeter with the Eternity background, logo avatar, and hint; `desktop.png` shows the desktop after typing the password. Save both PNGs as `docs/screenshots/{login,desktop}.png` and commit them.
- [ ] **Step 5: Commit** `feat: Eternity 08 login screen`.

---

### Task 8: Installer (Calamares) branding

**Files:**
- Create: `config/package-lists/installer.list.chroot` (`calamares calamares-settings-debian`), `config/includes.chroot/etc/calamares/settings.conf`, `config/includes.chroot/etc/calamares/branding/eternity/{branding.desc,show.qml,logo.png,welcome.png,slide-1.png,slide-2.png}`, `config/includes.chroot/etc/calamares/modules/{bootloader.conf,unpackfs.conf,users.conf,displaymanager.conf,packages.conf,finished.conf,shellprocess-eternity.conf}`, `config/includes.chroot/usr/share/applications/eternity-install.desktop`, `config/includes.chroot/etc/skel/Desktop/eternity-install.desktop`, `config/includes.chroot/usr/lib/eternity/post-install.sh`
- Modify: `tests/smoke.sh` (`check_installer`)

**Interfaces:**
- Produces: `settings.conf` module sequence: `welcome, locale, keyboard, partition, users, summary` (show) then `partition, mount, unpackfs, machineid, fstab, locale, keyboard, localecfg, users, displaymanager, networkcfg, hwclock, shellprocess@eternity, initramfs, grubcfg, bootloader, umount` (exec) then `finished`. `branding.desc`: `productName: Eternity 08`, `shortProductName: Eternity 08`, `version: 0.1.0`, `shortVersion: 0.1.0`, `versionedName: Eternity 08 0.1.0`, `bootloaderEntryName: Eternity 08`, `productUrl`, `windowTitle: Install Eternity 08`, `sidebarBackground: "#0D1320"`, `sidebarText: "#E6F1FF"`, `sidebarTextSelect: "#19D3F5"`, `images: productLogo: logo.png, productIcon: logo.png, productWelcome: welcome.png`. `displaymanager.conf`: `displaymanagers: [lightdm]`, `defaultDesktopEnvironment: executable: startxfce4`. `post-install.sh` (run by `shellprocess@eternity` in the target): remove `live-boot live-config live-config-systemd` packages, delete `/etc/lightdm/lightdm.conf.d/` live overrides, set greeter `background=/usr/share/eternity/wallpaper-1920x1080.png`, `systemctl disable eternity-smoke.service`, `update-grub`.

- [ ] **Step 1: Add `check_installer`**: `dpkg -s calamares`; `grep -q 'productName: *Eternity 08' /etc/calamares/branding/eternity/branding.desc`; `grep -q 'branding: *eternity' /etc/calamares/settings.conf`; `test -x /usr/lib/eternity/post-install.sh`; `calamares --help` exits 0 under `xvfb-run`? No, keep it to file checks; the real install is Task 13.
- [ ] **Step 2: Write the Calamares files.** Start from `/etc/calamares/` shipped by `calamares-settings-debian` (inspect inside the chroot after a build: `chroot/etc/calamares`), copy the module configs that work for Debian live (`unpackfs.conf` source `/run/live/medium/live/filesystem.squashfs`), and rebrand. `eternity-install.desktop`: `Name=Install Eternity 08`, `Exec=pkexec calamares`, `Icon=eternity`.
- [ ] **Step 3: Rebuild and test**: `./build.sh --test` → `CHECK installer: PASS`. Visual: `desktop.png` shows the `Install Eternity 08` icon on the desktop.
- [ ] **Step 4: Commit** `feat: branded Calamares installer`.

---

### Task 9: Python ML stack in `/opt/eternity/venv`

**Files:**
- Create: `config/package-lists/ai.list.chroot` (`python3 python3-venv python3-pip python3-dev build-essential cmake ninja-build pkg-config git libopenblas-dev libgomp1 jupyter-notebook`-free: use pip for Jupyter), `ai/requirements.in`, `ai/requirements.lock`, `config/hooks/normal/0500-ai-venv.hook.chroot`, `config/includes.chroot/etc/profile.d/eternity-venv.sh`, `config/includes.chroot/etc/pip.conf`
- Modify: `tests/smoke.sh` (`check_venv`)

**Interfaces:**
- Produces: `ai/requirements.in`: `numpy pandas scipy scikit-learn matplotlib jupyterlab notebook ipykernel torch transformers tokenizers safetensors sentence-transformers accelerate huggingface_hub llama-cpp-python` with `--extra-index-url https://download.pytorch.org/whl/cpu` so `torch` resolves to the CPU wheel. `ai/requirements.lock` is produced on the build host by `pip-compile --generate-hashes` (pip-tools in a throwaway venv) on build day and committed.
- Produces: the hook creates `/opt/eternity/venv` with `python3 -m venv --system-site-packages=false`, `pip install --require-hashes -r /tmp/requirements.lock`, builds `llama-cpp-python` with `CMAKE_ARGS="-DGGML_NATIVE=OFF -DGGML_AVX2=ON"` (portable binary, not host-tuned), then `find venv -name '__pycache__' -prune -exec rm -rf {} +` and strips tests dirs. `eternity-venv.sh` prepends `/opt/eternity/venv/bin` to PATH for all users. `pip.conf` sets `[global] break-system-packages=false`.
- Produces: `python -c "import torch, transformers, sklearn, pandas, numpy, scipy, matplotlib, sentence_transformers, llama_cpp; print(torch.__version__)"` works offline in the image.

- [ ] **Step 1: Add `check_venv`**: the import line above via `/opt/eternity/venv/bin/python`, plus `torch.cuda.is_available()` is False and `torch.tensor([1.,2.]).sum().item() == 3.0`; `which jupyter` resolves under `/opt/eternity/venv`.
- [ ] **Step 2: Generate `ai/requirements.lock`** on the build host (`python3 -m venv /tmp/pt && /tmp/pt/bin/pip install pip-tools && /tmp/pt/bin/pip-compile --generate-hashes --extra-index-url https://download.pytorch.org/whl/cpu -o ai/requirements.lock ai/requirements.in`). Record versions in `docs/build-notes.md`.
- [ ] **Step 3: Write the hook and the package list.** `build.sh` copies `ai/requirements.lock` to `config/includes.chroot/tmp/requirements.lock`? No: live-build `includes.chroot` lands before hooks run, so place it at `config/includes.chroot/usr/lib/eternity/requirements.lock` and have the hook read it from there (it stays in the image as a record).
- [ ] **Step 4: Rebuild and test**: `./build.sh --test` → `CHECK venv: PASS`. Note the chroot build downloads about 1 GB of wheels; live-build's `cache/` does not cache pip, so set `PIP_CACHE_DIR=/srv/eternity-build/pip-cache` bind-mounted into the chroot by `build.sh` (`mount --bind` before `lb build`, unmount after) to keep rebuilds fast. Record ISO size.
- [ ] **Step 5: Commit** `feat: preinstalled Python ML stack in /opt/eternity/venv`.

---

### Task 10: llama.cpp runtime

**Files:**
- Create: `ai/llama-cpp.version` (a release tag, e.g. the newest `bNNNN` tag on build day, verified with `git ls-remote --tags https://github.com/ggml-org/llama.cpp | tail`), `config/hooks/normal/0510-llama-cpp.hook.chroot`, `config/includes.chroot/etc/systemd/system/llama-server.service`
- Modify: `tests/smoke.sh` (`check_llama`)

**Interfaces:**
- Produces: `/usr/local/bin/llama-cli`, `/usr/local/bin/llama-server`, `/usr/local/bin/llama-bench`, and `/usr/local/lib/libggml*.so libllama.so` (hook runs `ldconfig`). Built with `cmake -B build -DGGML_NATIVE=OFF -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON -DBUILD_SHARED_LIBS=ON -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release` and `cmake --install build --prefix /usr/local`. Source cloned at depth 1 at the tag into `/usr/src/llama.cpp` and deleted after install.
- Produces: `llama-server.service`: `ExecStart=/usr/local/bin/llama-server -m /opt/eternity/models/default.gguf --host 127.0.0.1 --port 8080 -c 4096`, `User=nobody`-free (runs as a dedicated `eternity-ai` system user created by the hook), `[Install] WantedBy=multi-user.target`, **not enabled**.

- [ ] **Step 1: Add `check_llama`**: `llama-cli --version` exits 0; `systemctl is-enabled llama-server` prints `disabled`; `test -f /etc/systemd/system/llama-server.service`.
- [ ] **Step 2: Write the hook and unit; pick the tag.**
- [ ] **Step 3: Rebuild and test**: `./build.sh --test` → `CHECK llama: PASS`.
- [ ] **Step 4: Commit** `feat: llama.cpp CPU runtime and disabled llama-server unit`.

---

### Task 11: Models, `eternity-chat`, and `eternity-ai`

**Files:**
- Create: `ai/models.manifest`, `ai/fetch-models.sh`, `config/includes.chroot/usr/local/bin/eternity-chat`, `config/includes.chroot/usr/local/bin/eternity-ai`, `config/includes.chroot/usr/share/applications/eternity-chat.desktop`, `config/includes.chroot/etc/skel/Desktop/eternity-chat.desktop`, `config/includes.chroot/opt/eternity/models/README.md`, `tests/test_eternity_chat.sh` (host-side unit test of model selection), `docs/models.md` (the research: candidates considered, licences, sizes, why chosen)
- Modify: `build.sh` (run `ai/fetch-models.sh` before `lb build`), `tests/smoke.sh` (`check_models`, `check_chat`)

**Interfaces:**
- Produces: `ai/models.manifest` lines `role|name|filename|url|sha256|licence|licence_url`. Two roles: `default` (4B class, Q4_K_M) and `small` (1–2B class, Q4_K_M). Research on build day with the Hugging Face tools: compare current Apache-2.0/MIT instruct models under 5B (Qwen3 family and any newer Apache releases, Gemma is not Apache so excluded, Phi is MIT so eligible, SmolLM is Apache so eligible); choose by common benchmark standing and GGUF availability from the model author or a reputable quantizer (bartowski, unsloth, or the author's own GGUF repo). Write `docs/models.md`. Leading candidates per the spec: Qwen3-4B (default), Qwen3-1.7B (small).
- Produces: `fetch-models.sh` downloads each file to `config/includes.chroot/opt/eternity/models/<filename>` if missing or checksum-mismatched, verifies `sha256sum`, downloads the licence text to `<filename>.LICENSE`, and creates symlinks `default.gguf` and `small.gguf`. Also writes `models.json` (`{"default": {...}, "small": {...}}` with name, file, size bytes, licence) next to them for `eternity-ai`.
- Produces: `eternity-chat [--small|--default|--model PATH] [--system TEXT] [-- extra llama-cli args]`: bash; picks `small.gguf` automatically when `MemAvailable` from `/proc/meminfo` is below `ETERNITY_MIN_MEM_KB` (default 5 500 000 kB) and no flag given; runs `llama-cli -m <model> -c 4096 -t $(nproc) --color -cnv -p "<system>"` with system prompt `You are Eternity, the local assistant of Eternity 08. Answer concisely.`; prints a one-line banner `Eternity 08 · <model name> · <threads> threads` first. The selection logic lives in a function `select_model` that reads `MEMAVAILABLE_KB` from an env override when set (for the host test).
- Produces: `eternity-ai status`: prints OS pretty name, kernel, CPU model and threads, RAM total/available, each model with size and licence, versions of python/torch/transformers from the venv, and llama.cpp version. `eternity-ai models` lists models. `eternity-ai serve` prints the command to enable `llama-server`.
- Produces: `eternity-chat.desktop`: `Name=Eternity Chat`, `Exec=xfce4-terminal --title "Eternity Chat" -e eternity-chat`, `Icon=eternity`, `Terminal=false`, `Categories=Utility;`.

- [ ] **Step 1: Write `tests/test_eternity_chat.sh`** (runs on the build host against `config/includes.chroot/usr/local/bin/eternity-chat` with `ETERNITY_DRY_RUN=1`, which makes the script print the chosen model path and exit): asserts `MEMAVAILABLE_KB=3000000` → `small.gguf`; `MEMAVAILABLE_KB=12000000` → `default.gguf`; `--small` with high memory → `small.gguf`; `--model /x.gguf` → `/x.gguf`. Run it: fails (script missing).
- [ ] **Step 2: Research models** with the Hugging Face tools; write `docs/models.md` and `ai/models.manifest` with real URLs and the SHA-256 values published on the Hub (`hub_repo_details` file metadata or the `.sha256` from the LFS pointer). Download with `fetch-models.sh` on the build host and confirm checksums match.
- [ ] **Step 3: Write `eternity-chat`, `eternity-ai`, the desktop files, `README.md`.** Run `tests/test_eternity_chat.sh`: PASS.
- [ ] **Step 4: Add `check_models`** (both symlinks resolve, `sha256sum -c` against a `SHA256SUMS` written by `fetch-models.sh`, licence files exist) **and `check_chat`**: `timeout 300 llama-cli -m /opt/eternity/models/small.gguf -p "Reply with the single word PONG." -n 8 -no-cnv --temp 0 2>/dev/null | grep -qi pong`; also `eternity-ai status` exits 0 and mentions `Eternity 08`. Record the tokens/s from `llama-bench -m small.gguf -p 64 -n 32` in the serial log.
- [ ] **Step 5: Rebuild and test**: `./build.sh --test` → `CHECK models: PASS`, `CHECK chat: PASS`, `SMOKE: PASS`. Record ISO size, tokens/s, in `docs/build-notes.md`.
- [ ] **Step 6: Commit** `feat: bundled open-licensed models, eternity-chat and eternity-ai` (the `.gguf` files stay gitignored; the manifest and checksums are committed).

---

### Task 12: Full verification suite (`build.sh --test`)

**Files:**
- Create: `tests/run-qemu-bios.sh`, `tests/run-all.sh`, `config/hooks/normal/0900-cleanup.hook.chroot`
- Modify: `build.sh` (`--test` runs `tests/run-all.sh`), `tests/smoke.sh` (`check_memory`: `free -k` `used` after boot into multi-user is under 450 000 kB as a proxy; the desktop figure is measured in the visual run), `tests/run-qemu-visual.sh` (also run `free -m` via a `send-key`-typed terminal? No: measure in Task 13 on Hyper-V by typing `free -m` and screenshotting), `docs/build-notes.md`

**Interfaces:**
- Produces: `tests/run-all.sh <iso>` runs, in order: `run-qemu-smoke.sh` (direct kernel, no network), `run-qemu-visual.sh --selftest` (OVMF Secure Boot via GRUB self-test entry; must print `SecureBoot enabled`), `run-qemu-visual.sh` (screenshots grub/splash/login/desktop to `tests/out/`), `run-qemu-bios.sh` (SeaBIOS: screenshot of GRUB menu at t=6 s, then boots the self-test entry and expects `SMOKE: PASS` with `check_secureboot` reported as `SKIP`). Prints a summary table and exits non-zero on any failure. Timing: `run-qemu-visual.sh` records seconds from QEMU start to the first frame where the greeter is up (poll `screendump` every 2 s and compare the image to a solid frame) and asserts under 30 s... simpler and sufficient: record the time at which the login screenshot was taken, require the greeter visible in a screenshot taken at t=30 s.
- Produces: `0900-cleanup.hook.chroot`: `apt-get clean`, `rm -rf /var/lib/apt/lists/*` (live-build regenerates), `rm -rf /root/.cache /tmp/*`, remove `/usr/src/llama.cpp`, `fc-cache -f`.

- [ ] **Step 1: Write `run-qemu-bios.sh`, `run-all.sh`, the cleanup hook; wire `--test`.**
- [ ] **Step 2: Run `./build.sh --clean --test`** from a clean state (`git clean -xfd -e out -e cache` first, keep `cache/` and the downloaded models). Expected: all four runs pass; screenshots show themed GRUB (UEFI and BIOS), Plymouth, greeter, desktop.
- [ ] **Step 3: Open every screenshot with the Read tool** and confirm branding against the spec's Goal 2 list. Copy them to `docs/screenshots/`.
- [ ] **Step 4: Write `docs/build-notes.md`**: Debian point release, kernel version, llama.cpp tag, model names and sizes, ISO size, build time, idle memory, tokens/s, test summary table.
- [ ] **Step 5: Commit** `test: full QEMU verification suite and build notes`.

---

### Task 13: Hyper-V run on the laptop (boot, login, chat, install, reboot)

**Files:**
- Create: `tools/hyperv-screenshot.ps1`, `tools/hyperv-test.ps1`, `docs/screenshots/hyperv-*.png`
- Modify: `docs/build-notes.md`

**Interfaces:**
- Produces: `tools/hyperv-screenshot.ps1 -VMName <name> -Path <png>`: uses WMI `Msvm_VirtualSystemManagementService.GetVirtualSystemThumbnailImage` (namespace `root\virtualization\v2`, width 1280 height 720) and writes a PNG via `System.Drawing` (the method returns RGB565 bytes; convert).
- Produces: `tools/hyperv-test.ps1 -Iso <path> [-Install]`: creates VM `Eternity08-Test` (Generation 2, 8 GB static memory, 4 vCPU, 40 GB dynamic VHDX at `C:\Users\muthu.MSG\Documents\Claude\eternity-08\out\Eternity08-Test.vhdx`, Default Switch), `Set-VMFirmware -EnableSecureBoot On -SecureBootTemplate MicrosoftUEFICertificateAuthority`, DVD first in boot order, starts it, screenshots at 10 s (GRUB), 25 s (splash), 60 s (login) to `docs/screenshots/hyperv-{grub,splash,login}.png`; types `eternity` + Enter via WMI `Msvm_Keyboard.TypeText`/`TypeKey`, screenshot desktop; opens a terminal (`Ctrl+Alt+T` via `TypeKey` scancodes), types `free -m; eternity-ai status` and screenshots; types `eternity-chat --small`, waits 60 s, types `Say hello in five words.` + Enter, waits 90 s, screenshots. With `-Install`: launches `pkexec calamares` from the terminal and then the operator (this session) drives the installer by screenshot-and-key steps: Next, Next, Next, "Erase disk", user `muthu` / password `eternity08`, hostname `eternity-vm`, Install, wait for `Done`, restart; after reboot screenshots `hyperv-installed-{grub,login,desktop}.png`, logs in and runs `cat /etc/os-release | head -1; getent passwd eternity; eternity-chat --small` and screenshots. Ends with `Stop-VM -TurnOff`; the VM is kept for the owner.
- Idle memory: read from the `free -m` screenshot; must be under 700 MB used.

- [ ] **Step 1: Write both scripts.** Test the screenshot helper first against the VM with the ISO at the GRUB menu (open the PNG with the Read tool).
- [ ] **Step 2: Run the live path** (`tools/hyperv-test.ps1 -Iso out\eternity-08-0.1.0-amd64.iso`), inspecting each screenshot. Fix any boot problem in the image (this is where a backports-kernel regression would show; apply the fallback rule only on a reproduced boot failure).
- [ ] **Step 3: Run the install path** (`-Install`) and inspect the post-install screenshots: branding intact, `eternity` user gone, chat works.
- [ ] **Step 4: Record results in `docs/build-notes.md`** (idle memory, boot time, install time, tokens/s in the VM) and commit screenshots.
- [ ] **Step 5: Commit** `test: Hyper-V boot, login, chat and install verified on the laptop`.

---

### Task 14: USB writer and hand-off

**Files:**
- Create: `tools/write-usb.ps1`, `README.md`
- Modify: `docs/build-notes.md`

**Interfaces:**
- Produces: `tools/write-usb.ps1 [-List] [-DiskNumber N -Iso <path>]`: `-List` prints removable disks (`Get-Disk | Where-Object BusType -eq USB`) with number, model, size; with `-DiskNumber`, refuses unless that disk's `BusType` is `USB` and it is not the system disk, then prints the model and size and requires the literal confirmation argument `-Confirm:$true`, clears the disk (`Clear-Disk -RemoveData -RemoveOEM`), takes it offline, and writes the ISO with a 4 MB-buffered `FileStream` to `\\.\PhysicalDriveN`, then verifies by reading back the first 64 MB and comparing SHA-256 with the ISO's first 64 MB.
- Produces: `README.md`: what Eternity 08 is, how to build (`tools/wsl-setup.ps1`, then `wsl -d Debian -u root -- bash -lc 'cd /mnt/c/.../eternity-08 && ./build.sh --test'`), how to test in Hyper-V, how to write a USB stick and boot the laptop (F11 boot menu on MSI, Secure Boot stays on), live credentials, `eternity-chat` usage, where the models live, and how to enable `llama-server`.

- [ ] **Step 1: Write `write-usb.ps1`**; test `-List` (no USB disk present prints "no removable USB disks"), and test the refusal paths (`-DiskNumber 0` must refuse as the system disk).
- [ ] **Step 2: Write `README.md`.**
- [ ] **Step 3: Final `docs/build-notes.md`** section "What was not run": the physical USB boot of the MSI Alpha 15 needs the owner to plug in a stick, run `tools/write-usb.ps1`, and reboot the laptop; this session cannot reboot the machine it runs on.
- [ ] **Step 4: Commit** `docs: README, USB writer and hand-off notes`.
