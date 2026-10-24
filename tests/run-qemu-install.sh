#!/bin/bash
# Install test without Hyper-V: boot the ISO under OVMF Secure Boot with an empty 40 GB
# virtio disk, log in, launch "Install Eternity 08", and keep the VM running with a QMP
# socket so the Calamares pages can be driven step by step:
#
#   tests/run-qemu-install.sh <iso> start        boot, log in, start the installer, screenshot
#   tests/run-qemu-install.sh <iso> shot NAME    screenshot -> tests/out/install/NAME.png
#   tests/run-qemu-install.sh <iso> keys K...    send keys/text (qmp.py syntax: Tab Enter Down "text")
#   tests/run-qemu-install.sh <iso> click X Y    click at screen pixel (1280x800; usb-tablet pointer)
#   tests/run-qemu-install.sh <iso> stop         power the VM off (keeps the disk and the OVMF vars)
#   tests/run-qemu-install.sh <iso> boot-disk    boot the installed system from the disk (no ISO)
#   tests/run-qemu-install.sh <iso> wipe         delete the disk image and the OVMF vars
#
# The same OVMF_VARS file is reused across runs so the boot entry grub-install adds with
# efibootmgr survives into the boot-disk run.
set -uo pipefail
ISO=${1:-}; CMD=${2:-}; shift 2 2>/dev/null
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$HERE/out/install
MEM=${ETERNITY_QEMU_MEM:-3072}
DISK=$OUT/install.qcow2
VARS=$OUT/OVMF_VARS.fd
SOCK=/tmp/eternity-install.sock
PIDF=$OUT/qemu.pid
. "$HERE/qemu-env.sh"
mkdir -p "$OUT"
Q() { python3 "$HERE/qmp.py" "$SOCK" "$@"; }

launch() { # launch [extra qemu args...]; detached, pid in $PIDF
    rm -f "$SOCK"
    setsid nohup qemu-system-x86_64 "${QEMU_ACCEL[@]}" -m "$MEM" -smp 4 -machine q35,smm=on \
        -global driver=cfi.pflash01,property=secure,value=on \
        -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.secboot.fd \
        -drive if=pflash,format=raw,file="$VARS" \
        -drive file="$DISK",if=virtio,format=qcow2 \
        -nic none -no-reboot -vga virtio -display none -device qemu-xhci -device usb-tablet \
        -serial "file:$OUT/serial.log" -qmp "unix:$SOCK,server,nowait" "$@" \
        > "$OUT/qemu.log" 2>&1 < /dev/null &
    echo $! > "$PIDF"
    sleep 2; kill -0 "$(cat "$PIDF")" 2>/dev/null || { echo "qemu did not start:"; cat "$OUT/qemu.log"; exit 1; }
}

case "$CMD" in
start)
    [ -n "$ISO" ] && [ -f "$ISO" ] || { echo "ISO not found: '$ISO'" >&2; exit 2; }
    [ -f "$DISK" ] || qemu-img create -f qcow2 "$DISK" 40G >/dev/null
    [ -f "$VARS" ] || cp /usr/share/OVMF/OVMF_VARS_4M.ms.fd "$VARS"
    launch -drive file="$ISO",media=cdrom,if=none,id=cd -device ide-cd,drive=cd,bootindex=1
    echo "INFO accel: $ACCEL_NAME"
    grub_settle; Q screendump "$OUT/grub.png"; Q keys Enter
    S 38; Q screendump "$OUT/login.png"
    Q keys eternity Enter; S 25; Q screendump "$OUT/desktop.png"
    # Launch the installer from a terminal. In the live session polkit lets the sudo-group
    # user run calamares without a prompt (observed in build 8), so nothing is typed blindly
    # here: a stray keystroke would land in the installer's language box.
    Q keys Ctrl-Alt-T; S 6; Q keys "eternity-install" Enter; S 40; Q screendump "$OUT/installer-welcome.png"
    echo "installer started; drive it with: $0 $ISO click X Y / keys ... / shot NAME"
    echo "notes: libpwquality rejects dictionary-based passwords such as eternity08; the test used Genesis08-vm"
    ;;
auto)
    # Unattended install: pages are driven by clicks at the 1280x800 positions verified on
    # build 8 (Next, Erase disk, user fields, Install, Install Now); completion is read from
    # Calamares' session log, which a second terminal streams to the serial port.
    "$0" "$ISO" start || exit 1
    U=${ETERNITY_INSTALL_USER:-muthu}; P=${ETERNITY_INSTALL_PASSWORD:-Genesis08-vm}
    Q keys Ctrl-Alt-T; S 6
    Q keys 'sudo sh -c "tail -n +1 -F /root/.cache/calamares/session.log > /dev/ttyS0"' Enter; S 3
    Q click 600 108; S 2                       # raise the installer window again
    Q click 1013 745; S 12; Q screendump "$OUT/auto-location.png"
    Q click 1013 745; S 12; Q screendump "$OUT/auto-keyboard.png"
    Q click 1013 745; S 25; Q screendump "$OUT/auto-partitions.png"
    Q click 337 192;  S 8;  Q screendump "$OUT/auto-erase.png"      # Erase disk
    Q click 1013 745; S 15
    Q click 430 171; S 2; Q keys "Muthu"; S 3
    Q click 430 287; S 2; Q keys Ctrl-A; S 1; Q keys "eternity-vm"; S 3
    Q click 430 349; S 2; Q keys "$P"; S 2
    Q click 635 349; S 2; Q keys "$P"; S 4; Q screendump "$OUT/auto-users.png"
    Q click 1013 745; S 15; Q screendump "$OUT/auto-summary.png"
    Q click 1013 751; S 10; Q screendump "$OUT/auto-confirm.png"   # Install
    Q click 749 449; S 10; Q screendump "$OUT/auto-installing.png" # Install Now
    t0=$(date +%s)
    while true; do
        sleep 60
        grep -q 'Unmounting file systems' "$OUT/serial.log" 2>/dev/null && break
        grep -qE 'Installation Failed|job failed|ERROR:' "$OUT/serial.log" 2>/dev/null && { echo "install reported a failure (see $OUT/serial.log)"; break; }
        kill -0 "$(cat "$PIDF")" 2>/dev/null || { echo "qemu exited during the install"; break; }
        [ $(( $(date +%s) - t0 )) -gt $(( 5400 * TSCALE / 10 + 1800 )) ] && { echo "install timed out"; break; }
    done
    S 9; Q screendump "$OUT/auto-done.png"
    grep -aE 'Starting job|Installation|failed' "$OUT/serial.log" | tr -d '\r' | tail -8
    echo "install phase finished after $(( ( $(date +%s) - t0 ) / 60 )) min; next: $0 $ISO stop && $0 $ISO boot-disk"
    ;;
shot)  Q screendump "$OUT/$1.png" && echo "$OUT/$1.png" ;;
keys)  Q keys "$@" ;;
click) Q click "$@" ;;
type)  Q keys "$1" ;;   # text only (no key-name lookup)
stop)  [ -f "$PIDF" ] && { kill "$(cat "$PIDF")" 2>/dev/null; sleep 2; }; rm -f "$PIDF"; echo stopped ;;
boot-disk)
    [ -f "$DISK" ] && [ -f "$VARS" ] || { echo "no installed disk/vars in $OUT" >&2; exit 2; }
    launch
    echo "INFO accel: $ACCEL_NAME (booting the installed disk)"
    grub_settle; Q screendump "$OUT/installed-grub.png"; Q keys Enter
    S 38; Q screendump "$OUT/installed-login.png"
    # Installed user as entered in Calamares during the test (see docs/build-notes.md).
    U=${ETERNITY_INSTALL_USER:-muthu}; P=${ETERNITY_INSTALL_PASSWORD:-Genesis08-vm}
    Q keys "$P" Enter; S 25; Q screendump "$OUT/installed-desktop.png"
    Q keys Ctrl-Alt-T; S 6
    Q keys "head -2 /etc/os-release; getent passwd eternity || echo 'no live user'; systemctl is-enabled eternity-smoke lightdm; ls /usr/share/applications | grep -c eternity-install; grep background= /etc/lightdm/lightdm-gtk-greeter.conf; ls /etc/lightdm/lightdm.conf.d/ /etc/calamares 2>&1 | head -3; dpkg -l live-config calamares 2>&1 | grep -c '^ii'; mokutil --sb-state; free -m | head -2" Enter
    S 4; Q screendump "$OUT/installed-terminal.png"
    Q keys "clear; eternity-chat --small --ask 'Reply with the single word PONG.'" Enter
    S 60; Q screendump "$OUT/installed-chat.png"
    echo "installed-system screenshots in $OUT (user $U)"
    ;;
wipe)  rm -f "$DISK" "$VARS"; echo wiped ;;
*)     echo "usage: $0 <iso> start|shot NAME|keys K...|stop|boot-disk|wipe" >&2; exit 2 ;;
esac
