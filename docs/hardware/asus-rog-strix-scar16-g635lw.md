# Test machine: ASUS ROG Strix SCAR 16 G635LW (owner's GPU laptop)

Recorded 2026-10-25 from the owner's specification. This is the machine on which Eternity 08
is to be tested completely, including the AI and local LLM features. It boots from the USB
stick only (the 2 TB NVMe has no free space and sits behind Intel VMD).

| Item | Value | Consequence for Eternity 08 |
|---|---|---|
| Firmware | AMI UEFI G635LW.338, UEFI only, Secure Boot on | The raw-written stick boots through Debian's signed shim (as on the MSI). No legacy path: the BIOS test run is irrelevant here. |
| TPM 2.0, PCR7 bound, BitLocker very likely on | | **Export the BitLocker recovery key before the first test.** Use the firmware's one-time boot menu (F8 on ASUS) to pick the stick; do not change Secure Boot or the permanent boot order. |
| CPU | Intel Core Ultra 9 275HX (Arrow Lake HX): 8 P + 16 E cores, no SMT, no AVX-512 | llama.cpp CPU build (AVX2) runs well on 24 threads; `eternity-llama` already uses `os.cpu_count()` threads. The chip carries an Intel NPU (intel_vpu, `/sys/class/accel/accel0`): the Monitor's AI panel honestly becomes "NPU" there, but nothing uses it yet (OpenVINO, later). |
| Memory | 32 GiB DDR5-5600 | The 4B default model loads by default (`ETERNITY_MIN_MEM_KB` satisfied). |
| Disk | 2 TB WD SN8000S behind **Intel VMD**, zero free space | Live USB only; no install. The kernel's `vmd` module autoloads, so the installer would see the disk, but there is nothing to install into. USB persistence (slice 2b) is what makes this machine a real daily test. |
| GPU | NVIDIA RTX 5080 (Blackwell) drives the panel; Intel Xe iGPU present | Debian 13's kernel 6.12 nouveau does not drive Blackwell: on the stick the panel comes up on the firmware framebuffer (simpledrm). `eternity-session` detects that and runs Hyprland and Qt with **software rendering** (same path as the VM runs). For GPU rendering, switch the laptop to iGPU/Eco (Optimus) mode in Armoury Crate before booting the stick: the panel is then on the Intel Xe GPU, which Mesa drives (`xe`/`i915`, `firmware-intel-graphics` is in the image). The proprietary NVIDIA driver is out of reach on a Secure Boot live stick (unsigned DKMS module). |
| Panel | 2560×1600 at 240 Hz | Scale 1.25 by default (logical 2048×1280, k = 1.067: the design renders at 107 % of its pixels). 1.5 may read better on 16 inches; it is one line in `layout.toml`. Hyprland picks the preferred mode (240 Hz). |
| Input | USB HID keyboard on xHCI, I2C-HID touchpad, no PS/2 | Standard drivers. |
| Serial | 16550 at 0x3F8 advertised, no connector | The self-test's serial log is unreadable here; use the on-screen checks and `eternity-hw`. |
| Network | Wi-Fi (Intel, iwlwifi), reachable at 192.168.29.137 under Windows | Eternity ships no sshd by design; remote test access is a Settings > Security opt-in (later). |

## Test plan on this machine (after build 13 is green on the stick)

1. Export the BitLocker recovery key. Set the GPU mode to iGPU/Eco in Armoury Crate (optional, for GPU rendering).
2. Boot the stick from the one-time boot menu (F8). GRUB: "Eternity 08 Live (Eternity shell)" (hotkey n) boots the new session; the first entry boots XFCE Classic.
3. In the Eternity session: the presence desktop, Super+Space → "hardware report" (the `eternity-hw` output answers what works: Xe or simpledrm, iwlwifi, Bluetooth, NPU present, touchpad), Super (release) → launcher, Super+L → lock.
4. AI: ask the on-device model (24-thread CPU, 4B model); sign in to Claude in Settings > Assistant and ask again; check the readout (first token, tok/s) and the Monitor's panels.
5. Report back: `eternity-hw` text, the Monitor screenshot, and anything that did not work.

Open points for this machine: NPU use (OpenVINO) and a Vulkan llama.cpp build for the Xe iGPU are
possible later; NVIDIA on a Secure Boot live stick is not.
