# Installing / running Eternity 08 from Windows

The ASUS ROG lands in a `grub>` prompt (or a black screen after the GRUB menu) for two separate
reasons. Both are fixed now; this is how to make a working stick from Windows and boot it.

## 1. Why it failed before

- **Wrong USB write mode.** Rufus in **ISO** mode extracts the ISO and rebuilds the bootloader,
  which breaks a Debian hybrid ISO and drops the firmware to `grub>`. The ISO must be written
  **raw** (DD mode).
- **No GPU firmware.** The RTX 5080 (Blackwell GB203) drives the ROG panel. The kernel's nouveau
  driver needs `nvidia/gb203/gsp/*-570.144.bin`, which earlier builds did not carry, so the panel
  went black right after GRUB. Build 16 onward bundles it (from trixie-backports).

## 2. Make the stick (raw write, from Windows)

From an **elevated** PowerShell, in the repo:

```powershell
# see your USB disks (note the Number of the stick)
powershell -ExecutionPolicy Bypass -File tools\windows\write-eternity-usb.ps1 -List

# write to that disk (ERASES it) — example: disk 2
powershell -ExecutionPolicy Bypass -File tools\windows\write-eternity-usb.ps1 -DiskNumber 2
```

It copies the ISO byte-for-byte to the whole disk, like `dd`, preserving the Secure Boot layout.
Alternatives that also work: **Rufus in "DD Image" mode** (not "ISO Image"), or **balenaEtcher**.

## 3. Boot it on the ASUS ROG

1. **Export the BitLocker recovery key first** (`manage-bde -protectors -get C:` elevated, or
   Settings > Privacy & security > Device encryption > back up). Keep it off the machine.
2. Power on and open the **one-time boot menu** (Esc or F8). Pick the USB stick. Do **not** change
   Secure Boot, CSM, or the permanent boot order — the image's shim is Microsoft-signed, so
   BitLocker/PCR7 stays happy.
3. At the GRUB menu pick **Eternity 08 Live**. If the screen goes black, pick
   **Eternity 08 Live (safe graphics)** (nomodeset), or set the GPU to **Eco (iGPU)** in Armoury
   Crate before booting.

## 4. Installing

Eternity installs from the live session (the **Install Eternity 08** tile / Calamares). There is no
in-Windows installer for a full Secure-Boot Linux — you boot the stick, then install.

- **Internal disk:** the ROG's 2 TB NVMe is full. To install alongside Windows you must first free
  space: suspend BitLocker, shrink the C: partition from Disk Management by 40 GB or more, then
  install to that free space. The installer adds an `Eternity_08` UEFI entry and leaves the Windows
  loader alone.
- **External USB SSD (safest):** plug one in and run the installer's **Erase disk** on *that device
  only*. Nothing on the internal disk changes. This is the recommended way to try the full OS on the
  ROG without touching Windows.

See `docs/hardware/asus-g635lw.md` for the full hardware notes and test plan.
