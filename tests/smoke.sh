#!/bin/bash
# Eternity 08 in-image self-test.
# Runs as root inside the booted image when the kernel command line contains
# `eternity.test`. Output goes to the serial console (see eternity-smoke.service).
#
# Contract: one line per check  ->  "CHECK <name>: PASS" | "CHECK <name>: FAIL <reason>" | "CHECK <name>: SKIP <reason>"
#           then                 ->  "SMOKE: PASS" | "SMOKE: FAIL"
#           then                 ->  "SMOKE_DONE"
# Every function named check_<name> is run, in sorted order. A check returns 0 (pass),
# 1 (fail), or 2 (skip); anything it prints is appended as the reason.

EXPECT_DIR=/usr/lib/eternity/expect

echo "ETERNITY SMOKE START"
echo "INFO kernel: $(uname -r)"
echo "INFO cmdline: $(cat /proc/cmdline)"
echo "INFO memory: $(free -k | awk '/^Mem:/ {print "total="$2"kB used="$3"kB available="$7"kB"}')"

check_os_release() {
    # Every expected line must be present verbatim; live-build may add IMAGE_ID/BUILD_ID lines.
    local line
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        grep -qxF -- "$line" /etc/os-release || { echo "missing line: $line"; return 1; }
    done < "$EXPECT_DIR/os-release.txt"
    grep -qE '^(ID=debian|NAME="Debian)' /etc/os-release && { echo "Debian identity still present"; return 1; }
    grep -qxF 'ID=eternity' /usr/lib/os-release || { echo "/usr/lib/os-release not branded"; return 1; }
    return 0
}

check_identity() {
    [ "$(cat /etc/hostname)" = eternity ] || { echo "hostname file is '$(cat /etc/hostname)'"; return 1; }
    grep -q 'Eternity 08' /etc/issue || { echo "/etc/issue lacks Eternity 08"; return 1; }
    [ -s /usr/share/eternity/fastfetch.txt ] || { echo "fastfetch.txt missing"; return 1; }
    fastfetch --logo-type file --logo /usr/share/eternity/fastfetch.txt --pipe >/dev/null 2>&1 || { echo "fastfetch failed"; return 1; }
}

check_assets() {
    local d=/usr/share/eternity f
    for f in logo.svg logo-64.png logo-128.png logo-256.png logo-512.png \
             wallpaper-1920x1080.png wallpaper-2560x1440.png wallpaper-3840x2160.png greeter-1920x1080.png; do
        [ -s "$d/$f" ] || { echo "missing $d/$f"; return 1; }
    done
    file "$d/wallpaper-1920x1080.png" | grep -q '1920 x 1080' || { echo "wallpaper-1920x1080 wrong size"; return 1; }
    file "$d/wallpaper-2560x1440.png" | grep -q '2560 x 1440' || { echo "wallpaper-2560x1440 wrong size"; return 1; }
    file "$d/wallpaper-3840x2160.png" | grep -q '3840 x 2160' || { echo "wallpaper-3840x2160 wrong size"; return 1; }
    file "$d/greeter-1920x1080.png" | grep -q '1920 x 1080' || { echo "greeter wrong size"; return 1; }
    file "$d/logo-512.png" | grep -q '512 x 512' || { echo "logo-512 wrong size"; return 1; }
}

check_desktop() {
    dpkg -s xfce4 >/dev/null 2>&1 || { echo "xfce4 not installed"; return 1; }
    dpkg -s lightdm-gtk-greeter >/dev/null 2>&1 || { echo "lightdm-gtk-greeter not installed"; return 1; }
    grep -q 'Arc-Dark' /etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xsettings.xml 2>/dev/null || { echo "xsettings.xml lacks Arc-Dark"; return 1; }
    grep -q 'wallpaper-1920x1080.png' /etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml 2>/dev/null || { echo "xfce4-desktop.xml lacks wallpaper"; return 1; }
    grep -q 'whiskermenu' /etc/xdg/xfce4/panel/default.xml 2>/dev/null || { echo "panel default.xml lacks whiskermenu"; return 1; }
    grep -qx 'button-icon=eternity' /etc/xdg/xfce4/panel/whiskermenu-1.rc 2>/dev/null || { echo "whiskermenu rc lacks eternity icon"; return 1; }
    [ -x /usr/lib/eternity/set-wallpaper.sh ] || { echo "set-wallpaper.sh missing or not executable"; return 1; }
    [ -s /usr/share/icons/hicolor/256x256/apps/eternity.png ] || { echo "hicolor eternity icon missing"; return 1; }
    [ -s /usr/share/pixmaps/eternity.png ] || { echo "pixmaps eternity.png missing"; return 1; }
}

check_boot_theme() {
    [ "$(plymouth-set-default-theme 2>/dev/null)" = eternity ] || { echo "plymouth default theme is '$(plymouth-set-default-theme 2>/dev/null)'"; return 1; }
    [ -s /usr/share/grub/themes/eternity/theme.txt ] || { echo "installed-system GRUB theme missing"; return 1; }
    grep -qs 'Eternity 08' /etc/default/grub.d/eternity.cfg || { echo "grub.d/eternity.cfg lacks Eternity 08"; return 1; }
    local initrd
    initrd=$(ls /boot/initrd.img-* 2>/dev/null | head -1)
    [ -n "$initrd" ] || { echo "no initrd in /boot"; return 1; }
    lsinitramfs "$initrd" 2>/dev/null | grep -q 'plymouth/themes/eternity' || { echo "initrd lacks plymouth eternity theme"; return 1; }
}

check_secureboot() {
    [ -d /sys/firmware/efi ] || { echo "not an EFI boot"; return 2; }
    mokutil --sb-state 2>/dev/null | grep -q 'SecureBoot enabled' || { echo "$(mokutil --sb-state 2>&1 | head -1)"; return 1; }
}

check_login() {
    grep -qs 'greeter-1920x1080.png' /etc/lightdm/lightdm-gtk-greeter.conf || { echo "greeter conf lacks Eternity background"; return 1; }
    grep -qsx 'autologin-user=' /etc/lightdm/lightdm.conf.d/10-eternity.conf || { echo "10-eternity.conf lacks empty autologin-user"; return 1; }
    [ "$(systemctl is-enabled lightdm 2>/dev/null)" = enabled ] || { echo "lightdm not enabled"; return 1; }
    if grep -qs 'autologin-user=eternity' /etc/lightdm/lightdm.conf.d/*.conf /etc/lightdm/lightdm.conf; then
        echo "live autologin is enabled"; return 1
    fi
    if grep -q 'boot=live' /proc/cmdline; then
        getent passwd eternity >/dev/null || { echo "live user eternity missing"; return 1; }
    fi
}

check_installer() {
    dpkg -s calamares >/dev/null 2>&1 || { echo "calamares not installed"; return 1; }
    grep -qs 'productName: *Eternity 08' /etc/calamares/branding/eternity/branding.desc || { echo "branding.desc lacks Eternity 08"; return 1; }
    grep -qs '^branding: *eternity' /etc/calamares/settings.conf || { echo "settings.conf does not select eternity branding"; return 1; }
    [ -x /usr/lib/eternity/post-install.sh ] || { echo "post-install.sh missing"; return 1; }
    [ -s /usr/share/applications/eternity-install.desktop ] || { echo "eternity-install.desktop missing"; return 1; }
}

run_all() {
    local failed=0 name fn reason rc
    for fn in $(declare -F | awk '{print $3}' | grep '^check_' | sort); do
        name=${fn#check_}
        reason=$($fn 2>&1); rc=$?
        case $rc in
            0) echo "CHECK $name: PASS" ;;
            2) echo "CHECK $name: SKIP $reason" ;;
            *) echo "CHECK $name: FAIL $reason"; failed=1 ;;
        esac
    done
    return $failed
}

# When sourced by tests/run-chroot-checks.sh only the functions are wanted.
if [ -z "${ETERNITY_SMOKE_SOURCE_ONLY:-}" ]; then
    if run_all; then echo "SMOKE: PASS"; else echo "SMOKE: FAIL"; fi
    echo "SMOKE_DONE"
    sync
    systemctl poweroff
fi
