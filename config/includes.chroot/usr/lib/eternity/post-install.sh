#!/bin/sh
# Eternity 08: runs inside the freshly installed system (Calamares shellprocess@eternity).
# Removes live-session leftovers so the installed system is a clean Eternity 08.
set -e

# live-config writes autologin overrides for the live user; the installed system must log in normally
rm -f /etc/lightdm/lightdm.conf.d/*live* /etc/lightdm/lightdm.conf.d/*autologin* 2>/dev/null || true
rm -f /etc/systemd/system/getty@tty1.service.d/override.conf 2>/dev/null || true

# Greeter: no live-credentials hint on an installed system
if [ -f /etc/lightdm/lightdm-gtk-greeter.conf ]; then
    sed -i 's|^background=.*|background=/usr/share/eternity/wallpaper-1920x1080.png|' /etc/lightdm/lightdm-gtk-greeter.conf
fi

# Self-test and installer launchers are live-only
systemctl disable eternity-smoke.service >/dev/null 2>&1 || true
rm -f /usr/share/applications/eternity-install.desktop /etc/skel/Desktop/eternity-install.desktop
for home in /home/*; do
    rm -f "$home/Desktop/eternity-install.desktop" 2>/dev/null || true
done

# Make sure the branded identity survived
grep -q '^ID=eternity' /etc/os-release || cp /usr/share/eternity/os-release /usr/lib/os-release

# EFI fallback loader (EFI/boot/bootx64.efi). Calamares no longer copies the bare signed
# GRUB there (bootloader.conf installEFIFallback: false): launched from EFI/boot that image
# finds no grub.cfg and stops at a `grub>` prompt. Debian's grub-install can install a
# removable fallback (shim + GRUB + mokmanager) but still leaves out grub.cfg, so copy the
# stub that grub-install wrote for EFI/Eternity_08 next to it. Verified in QEMU with fresh
# firmware variables (no NVRAM entry): menu instead of `grub>`.
# On an ESP shared with Windows, EFI/boot/bootx64.efi is Windows' own fallback copy and is
# left alone; the firmware entry "Eternity_08" created by grub-install boots Eternity 08.
ESP=/boot/efi
if [ -d /sys/firmware/efi ] && [ -f "$ESP/EFI/Eternity_08/grub.cfg" ] && command -v grub-install >/dev/null 2>&1; then
    if [ ! -d "$ESP/EFI/Microsoft/Boot" ]; then
        grub-install --target=x86_64-efi --efi-directory="$ESP" --bootloader-id=Eternity_08 \
            --uefi-secure-boot --force-extra-removable --no-nvram >/dev/null 2>&1 || true
        mkdir -p "$ESP/EFI/BOOT"
        cp -f "$ESP/EFI/Eternity_08/grub.cfg" "$ESP/EFI/BOOT/grub.cfg" 2>/dev/null || true
    fi
fi

exit 0
