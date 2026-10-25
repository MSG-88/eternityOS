# Test machine: ASUS ROG Strix SCAR 16 G635LW ("MSG laptop")

Captured 2026-10-25 by a Claude Code session on the machine itself (summary relayed by the
owner); the development machine is the MSI Alpha 15 A3DDK (`docs/build-notes.md`, build 12).
This file is the reference for every test run on the ASUS: what the hardware is, what the
current image already handles (checked against the build 13 ISO of 2026-10-25 18:43 and its
build chroot), what is missing, and the order in which to test. Refresh it whenever the
machine or the image changes.

## 1. Captured configuration

| Area | Finding |
|---|---|
| Model / firmware | ASUS ROG Strix SCAR 16 G635LW, AMI UEFI `G635LW.338`. UEFI only, no legacy/CSM boot path. |
| Secure Boot | Enabled. |
| TPM | TPM 2.0, PCR7 bound: BitLocker is almost certainly on and will ask for the recovery key if Secure Boot state or the boot path changes. |
| CPU | Intel Core Ultra 9 275HX (family 6, model 0xC6, stepping 2): 8 P-cores + 16 E-cores, no SMT, 24 threads, sparse x2APIC IDs. 42-bit physical addressing, no AVX-512, no LA57. One IOAPIC, HPET at 0xFED00000, invariant TSC at 3.072 GHz. |
| Memory | 32 GiB DDR5-5600, one SO-DIMM. Usable RAM 1 MiB to about 1.4 GiB below 4 GiB, then 4 GiB to 34 GiB. |
| Storage | 2 TB WD SN8000S NVMe **behind Intel VMD** (the controller is hidden until the `vmd` driver binds). **Zero free space on the disk.** |
| Graphics | NVIDIA RTX 5080 Laptop (Blackwell, GB203) drives the panel; the firmware GOP framebuffer therefore comes from the NVIDIA path. Panel 2560x1600 at 240 Hz. Intel iGPU (Arrow Lake) presence depends on the MUX mode (see 3.4). |
| Input | No PS/2 controller. Built-in keyboard is USB HID on xHCI; touchpad is I2C-HID. |
| Debug serial | DBG2/DBGP advertise a 16550-subset port at I/O 0x3F8, but no connector is wired. |
| IOMMU | VT-d present, DMA remapping opted in by the firmware. |
| Network (Windows) | 192.168.29.137 over Wi-Fi. OpenSSH server installed but stopped; RDP off. |

Still to capture from the ASUS (run `C:\Users\muthu.MSG\Documents\Claude\capture-laptop-config.ps1`
there, or `eternity-hw --json` from the live session): PCI/USB vendor:device IDs of the Wi-Fi and
Bluetooth adapter, the Ethernet controller, the audio codec, the camera, the touchpad and the
keyboard; the GPU MUX mode in use (Armoury Crate); the BitLocker protection status; the UEFI boot
entries (`bcdedit /enum firmware`); the Wi-Fi driver name. Add them to the table above.

## 2. What the current image already covers (verified)

Checked in the ISO's initramfs (`/live/initrd.img-7.2.9+deb13-amd64`, `MODULES=most`, 3526
entries) and in the build chroot (`/srv/eternity-build/chroot`, kernel `7.2.9+deb13-amd64`):

| Need | In the initramfs | Note |
|---|---|---|
| NVMe behind VMD | `vmd.ko`, `nvme.ko`, `nvme-core.ko` | the live boot does not need the disk; an install does, and the installed system's initramfs is built with the same `MODULES=most` |
| USB keyboard | `xhci-pci.ko`, `xhci-hcd.ko`, `usbhid.ko`, `hid-generic.ko`, `hid-asus.ko` | keyboard works in the initramfs (persistence prompts, emergency shell) |
| I2C touchpad | `i2c-hid-acpi.ko`, `i2c-hid.ko`, `hid-multitouch.ko`, `intel-lpss-pci.ko`, `i2c-i801.ko` | |
| Intel graphics | `i915.ko`, `xe.ko`; firmware `i915/mtl_*` (Arrow Lake uses the Meteor Lake files), `firmware-intel-graphics 20250410-2` | only matters in hybrid/Eco MUX mode |
| NVIDIA graphics | `nouveau.ko` (7.2.9 knows GB203 and requests `nvidia/gb203/gsp/{gsp,bootloader,fmc}-570.144.bin`) | **firmware missing**, see 3.1 |
| Wi-Fi 7 candidates | `mt7925e.ko` + `btmtk.ko` (MediaTek MT7925, firmware in `firmware-mediatek`), `iwlwifi` (Intel BE200/BE1750, `firmware-iwlwifi`) | confirm which one the ASUS has |
| Ethernet | `r8169.ko` (Realtek 2.5G is the usual part) | confirm |
| ASUS platform | `asus-wmi.ko` in the initramfs, `asus-nb-wmi.ko`, `hid-asus.ko` in the system | Fn keys, keyboard backlight, fan/profile interfaces |
| Thunderbolt/USB4 | `thunderbolt.ko` | with VT-d DMA remapping the kernel applies IOMMU-based DMA protection to those ports |
| Microcode | `intel-microcode 3.20251111.1~deb13u1` | covers Arrow Lake |
| CPU features | llama.cpp built for x86-64-v3 (AVX2/FMA/F16C), no AVX-512 required | matches this CPU |

Memory map, HPET, invariant TSC, x2APIC and 42-bit addressing need nothing special from a 7.2 kernel.

## 3. Gaps and risks, in order of impact

### 3.1 No GSP firmware for the RTX 5080: nouveau cannot start, so no DRM device

The image carries `firmware-nvidia-graphics 20250410-2` (trixie), whose newest families are
`ad10x` and `ga10x`. nouveau 7.2.9 drives GB203 only through GSP and needs
`nvidia/gb203/gsp/*-570.144.bin`; without the files it logs a firmware load failure and
leaves the card unbound. Consequences on the ASUS in the default (dGPU) MUX mode:

- The console and X run on the firmware framebuffer (`CONFIG_FB_EFI=y`; `CONFIG_DRM_SIMPLEDRM`
  is **not** set in the Debian kernel, so there is no simpledrm KMS device either). XFCE comes
  up through the fbdev X driver at 2560x1600, software rendering, no brightness control.
- The **Eternity session cannot start**: Hyprland needs a DRM/KMS device and there is none.
  Every phase 3 shell test is blocked on this machine until the firmware lands.
- Fix: `trixie-backports` has `firmware-nvidia-graphics 20260916-1~bpo13+1` (seen by
  `apt-cache policy` in the build chroot). Pin it the way Hyprland is pinned
  (`config/archives/eternity-backports.pref.chroot`) and confirm with
  `dpkg -L firmware-nvidia-graphics | grep gb203` in the chroot before the next build.
  nouveau on Blackwell is new code; expect to also test the `nomodeset` ("safe graphics")
  entry and keep it as the fallback.
- Until then, the way to get a hardware-accelerated desktop on the ASUS is the MUX: set the
  GPU mode to **Eco** (iGPU only) in Armoury Crate before booting the stick; the panel is then
  driven by the Intel iGPU and i915 handles it (firmware present). Revert afterwards.

### 3.2 The disk is full: live sessions only

No install, "Install alongside" or persistence partition is possible on the internal disk.
Until Windows frees space (shrink from Disk Management with BitLocker suspended, 40 GB or
more, as the README says), every ASUS test is a USB live session. Options that do not touch
the internal disk: a USB persistence partition on a larger stick (backlog section 5) or an
external USB SSD as the install target (Calamares "Erase disk" on that device only).

### 3.3 Secure Boot + TPM + BitLocker: do not change firmware state

- Export the BitLocker recovery key before the first boot
  (`manage-bde -protectors -get C:` from an elevated prompt, or Settings > Privacy & security
  > Device encryption > back up your recovery key) and keep it off the machine.
- Boot the stick from the **one-time boot menu** (Esc or F8 at power-on) rather than changing
  the boot order; do not toggle Secure Boot, CSM or Fast Boot. The image's shim is signed by
  the Microsoft UEFI CA, so Secure Boot stays on; no MOK enrollment happens (no PCR7 change).
- If the one-time menu does not list the stick, the firmware's Fast Boot may skip USB
  initialisation; turning it off changes nothing PCR7-relevant, but note it in the results.
- On an eventual install, `post-install.sh` adds the `Eternity_08` firmware entry and leaves
  `EFI/Microsoft/Boot` alone; Windows keeps its own loader, so BitLocker should not trip.

### 3.4 Display and scale: 2560x1600 at 240 Hz, 16 inch (about 189 PPI)

The shipped wallpapers are 16:9 (1920x1080, 2560x1440, 3840x2160); the greeter conf, the
GRUB theme and the Plymouth frames use the 1080p set, and the panel is 16:10. Check on the
ASUS: GRUB (`gfxmode=auto` picks the GOP mode, probably 2560x1600), Plymouth, the greeter,
XFCE at 100 % (small) and the Eternity session's 125 % (`layout.toml`), which the design chose
for a 1080p-class panel. The Hyprland template gets 240 Hz only if the mode line is read from
the output; record `hyprctl monitors` and `xrandr`.

### 3.5 The Self-test GRUB entry is silent here

The entry appends `console=ttyS0,115200`; the ASUS has the port in DBG2 but no connector, so
the kernel makes the invisible serial port the primary console and the self-test report goes
nowhere. On this machine run the checks from a terminal in the live session instead (the
script `eternity-smoke.service` calls, and `eternity-hw --save`). Proposed image change: a
"Self-test (screen)" entry without the serial console, or `console=tty0` appended last.

### 3.6 Hybrid CPU: thread counts

`llama-server.service` hard-codes `ETERNITY_THREADS=4`; `eternity-chat` and
`eternity.providers` use `nproc`/`os.cpu_count()` = 24 (8 P + 16 E). Mixing core types slows
llama.cpp's barrier-synchronised threads to E-core pace. Measure `llama-bench` for the 4B model at
`-t 8` (P-cores only), `-t 16` and `-t 24`, and record first-token and tok/s in the Ask bar
readout; pick the thread policy from the numbers (likely: the P-core count, from
`/sys/devices/cpu_core/cpus`).

### 3.7 Unknowns until the IDs are in

Wi-Fi/Bluetooth (MediaTek MT7925 vs Intel BE200: both have drivers and firmware in the image,
but the `btusb` autosuspend and `rtw88` ASPM quirks in `eternity-hardware.conf` are for the
MSI's Realtek part and do nothing here), audio (Intel HDA + SOF: `firmware-sof-signed` and
`firmware-intel-sound` are in the image; check `aplay -l` and speakers vs headphones), camera
(UVC or MIPI IPU; a MIPI camera would not work), keyboard backlight / Fn keys (`asus-nb-wmi`),
suspend-resume (s2idle on Arrow Lake), battery and charge threshold (`asus-wmi`).

## 4. Test plan on the ASUS

Pre-flight (Windows, elevated):

1. Export the BitLocker recovery key (3.3). Record `manage-bde -status`.
2. Run the capture script; add `laptop-config-<date>.md` to this folder as
   `asus-g635lw-windows-inventory.md`.
3. Note the GPU MUX mode. For the first boot of an image without the gb203 firmware, set Eco.
4. Write the stick raw on the MSI (`tools\write-usb.ps1`, elevated, or Rufus **DD Image mode**);
   never ISO Image mode (NTFS cannot be read under Secure Boot lockdown).
5. Bring a second FAT32 stick for results (the internal disk is BitLocker-encrypted and full).

Boot (power on, Esc/F8, pick "UEFI: <stick>"), then in order:

| # | Step | Pass when | Collect |
|---|---|---|---|
| 1 | GRUB menu | themed menu, no error lines, all five entries | photo |
| 2 | **Eternity 08 Live** (XFCE) | Plymouth splash with the boot log, greeter, login `eternity`/`eternity`, first-run wizard, presence desktop | photos; `journalctl -b -p warning` |
| 3 | `eternity-hw --save` and `eternity-hw --json > /tmp/asus-hw.json` | no "without a driver" lines; firmware failures listed | copy both to the results stick |
| 4 | Graphics | `ls /dev/dri`; kernel log lines for nouveau, i915, xe, drm; `xrandr`; `glxinfo -B` | renderer name, resolution, refresh |
| 5 | Input | keyboard in GRUB, in the greeter and on the desktop; touchpad tap, two-finger scroll; Fn brightness/volume keys; keyboard backlight | `libinput list-devices` |
| 6 | Storage visibility | `lsblk` shows the NVMe; `lspci -k` shows the VMD domain with the NVMe under it | `lsblk -o NAME,SIZE,MODEL,TRAN` |
| 7 | Network | Wi-Fi scan + connect (NetworkManager), `rfkill list`, Bluetooth scan (`bluetoothctl scan on`) | `lspci -nnk`, `lsusb` |
| 8 | Audio | speakers, headphone jack, mic | `aplay -l`, `wpctl status` |
| 9 | Power | `powerprofilesctl list`, suspend to idle and resume (lid), battery readout in the strip | `cat /sys/power/mem_sleep` |
| 10 | AI | Ask bar question on the default 4B model (32 GiB allows it); `llama-bench` at -t 8/16/24 (3.6) | tok/s table |
| 11 | **Eternity 08 Live (Eternity shell)** | only once a DRM device exists (3.1): strip, presence, Super+Space, consent, lock/unlock | `hyprctl monitors`, screenshots via `grim` |
| 12 | Self-test from a terminal (3.5) | `SMOKE: PASS`, `check_secureboot` PASS, `check_hardware` PASS | the script output |
| 13 | Safe graphics entry | desktop on `nomodeset` | note resolution |
| 14 | Reboot into Windows | no BitLocker recovery prompt | note |

Install testing (steps "Install alongside", Windows in GRUB, `Eternity_08` firmware entry,
BitLocker untouched) waits until the disk has free space or an external SSD is attached.

## 5. Results

Fill in per image build; keep the newest at the top.

| Date | Image | MUX | Steps passed | Blocking findings |
|---|---|---|---|---|
| | | | | |

## 6. Image changes this machine asks for

1. `firmware-nvidia-graphics` from `trixie-backports` (3.1), then a static check in the host
   tests that the chroot contains `nvidia/gb203/gsp/gsp-570.144.bin` and the initramfs carries
   `vmd`, `xhci-pci`, `usbhid`, `i2c-hid-acpi`, `hid-asus`, `mt7925e`, `iwlwifi`, `nouveau`,
   `xe` and `i915` (QEMU cannot emulate VMD, GB203 or I2C-HID, so the static check is the only
   host-side guard for this machine).
2. A Self-test entry that reports to the screen (3.5).
3. Thread policy for hybrid CPUs (3.6) once the numbers are in.
4. 16:10 assets or resolution-independent rendering (3.4) once the screenshots are in.
5. Quirks in `eternity-hardware.conf` for the ASUS's Wi-Fi/Bluetooth part if the live run
   shows disconnects or failed resume (3.7).
