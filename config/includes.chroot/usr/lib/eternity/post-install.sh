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

exit 0
