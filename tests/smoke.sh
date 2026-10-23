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
    local d
    d=$(diff <(sort /etc/os-release) <(sort "$EXPECT_DIR/os-release.txt") 2>&1) || { echo "os-release differs: $(echo "$d" | tr '\n' ' ')"; return 1; }
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
    grep -q 'eternity' /etc/xdg/xfce4/panel/default.xml 2>/dev/null || { echo "panel default.xml lacks eternity icon"; return 1; }
    [ -s /usr/share/icons/hicolor/256x256/apps/eternity.png ] || { echo "hicolor eternity icon missing"; return 1; }
    [ -s /usr/share/pixmaps/eternity.png ] || { echo "pixmaps eternity.png missing"; return 1; }
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

if run_all; then echo "SMOKE: PASS"; else echo "SMOKE: FAIL"; fi
echo "SMOKE_DONE"
sync
systemctl poweroff
