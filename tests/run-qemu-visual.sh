#!/bin/bash
# Boot the ISO under QEMU with OVMF Secure Boot (Microsoft keys enrolled) and
# take screenshots: GRUB menu, Plymouth splash, login screen, desktop, terminal.
#
#   tests/run-qemu-visual.sh <iso>              screenshots -> tests/out/{grub,splash,login,desktop,terminal}.png
#   tests/run-qemu-visual.sh <iso> --selftest   choose the "Self-test" GRUB entry and collect the
#                                               serial self-test report (proves Secure Boot + signed kernel)
set -uo pipefail
ISO=${1:-}; MODE=${2:-shots}
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$HERE/out
MEM=${ETERNITY_QEMU_MEM:-4096}
. "$HERE/qemu-env.sh"            # QEMU_ACCEL, TSCALE, S (scaled sleep), grub_settle
[ -n "$ISO" ] && [ -f "$ISO" ] || { echo "ISO not found: '$ISO'" >&2; exit 2; }
mkdir -p "$OUT"
SOCK=/tmp/eternity-qmp.sock   # unix sockets cannot live on /mnt/c
rm -f "$SOCK" "$OUT/serial-visual.log"
cp /usr/share/OVMF/OVMF_VARS_4M.ms.fd "$OUT/OVMF_VARS.fd"
echo "INFO accel: $ACCEL_NAME mode=$MODE"

qemu-system-x86_64 "${QEMU_ACCEL[@]}" -m "$MEM" -smp 4 -machine q35,smm=on \
    -global driver=cfi.pflash01,property=secure,value=on \
    -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.secboot.fd \
    -drive if=pflash,format=raw,file="$OUT/OVMF_VARS.fd" \
    -drive file="$ISO",media=cdrom,if=none,id=cd -device ide-cd,drive=cd,bootindex=1 \
    -nic none -no-reboot -vga virtio -display none \
    -serial "file:$OUT/serial-visual.log" \
    -qmp "unix:$SOCK,server,nowait" &
QPID=$!
trap 'kill $QPID 2>/dev/null; wait $QPID 2>/dev/null' EXIT
Q() { python3 "$HERE/qmp.py" "$SOCK" "$@"; }

t0=$(date +%s)
grub_settle                       # menu is up and its countdown is stopped
Q screendump "$OUT/grub.png"
if [ "$MODE" = "--selftest" ]; then
    Q keys Down Down Enter        # third entry: "Eternity 08 Self-test"
    for i in $(seq 1 $(( 180 * TSCALE ))); do
        sleep 5
        grep -q '^SMOKE_DONE' "$OUT/serial-visual.log" 2>/dev/null && break
        kill -0 $QPID 2>/dev/null || break
    done
    grep -E '^(INFO|CHECK|SMOKE)' "$OUT/serial-visual.log" | tr -d '\r'
    grep -q '^SMOKE: PASS' "$OUT/serial-visual.log"
    exit $?
fi
Q keys Enter                      # boot "Eternity 08 Live"
S 8;  Q screendump "$OUT/splash.png"
S 30; Q screendump "$OUT/login.png"
echo "INFO login screenshot at t=$(( $(date +%s) - t0 ))s"
# lightdm-gtk-greeter preselects the only user, so the password field has focus
Q keys eternity Enter
# Phase 2: the first-run wizard opens on the first login; capture it, then close it (Alt-F4)
# so the keystrokes below reach the terminal. The presence shell is the desktop behind it.
S 25; Q screendump "$OUT/firstrun.png"
Q keys Alt-F4; S 4; Q screendump "$OUT/desktop.png"
Q keys Ctrl-Alt-T; S 6; Q keys "free -m" Enter; S 2; Q screendump "$OUT/terminal.png"
# Where the desktop session's memory goes (build 6 showed 1.3 GB used under XFCE).
Q keys "clear; ps -eo rss,comm --sort=-rss | head -14; grep -E 'AnonPages|Slab|Shmem|KReclaimable' /proc/meminfo" Enter
S 2; Q screendump "$OUT/terminal-mem.png"
# The command bar and the launcher, for the record
Q keys "eternity-ask &" Enter; S 6; Q screendump "$OUT/ask.png"; Q keys Esc; S 2
echo "screenshots in $OUT: grub.png splash.png login.png firstrun.png desktop.png terminal.png terminal-mem.png ask.png"
