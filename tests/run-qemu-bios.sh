#!/bin/bash
# Legacy BIOS (SeaBIOS) boot of the ISO: screenshot the GRUB menu, then run the
# Self-test entry and collect the serial report (check_secureboot reports SKIP).
set -uo pipefail
ISO=${1:-}
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$HERE/out
MEM=${ETERNITY_QEMU_MEM:-4096}
. "$HERE/qemu-env.sh"            # QEMU_ACCEL, TSCALE, grub_settle
[ -n "$ISO" ] && [ -f "$ISO" ] || { echo "ISO not found: '$ISO'" >&2; exit 2; }
mkdir -p "$OUT"
SOCK=/tmp/eternity-qmp-bios.sock
rm -f "$SOCK" "$OUT/serial-bios.log"
echo "INFO accel: $ACCEL_NAME"

qemu-system-x86_64 "${QEMU_ACCEL[@]}" -m "$MEM" -smp 4 \
    -cdrom "$ISO" -boot d -nic none -no-reboot -vga std -display none \
    -serial "file:$OUT/serial-bios.log" -qmp "unix:$SOCK,server,nowait" &
QPID=$!
trap 'kill $QPID 2>/dev/null; wait $QPID 2>/dev/null' EXIT
Q() { python3 "$HERE/qmp.py" "$SOCK" "$@"; }

grub_settle
Q screendump "$OUT/grub-bios.png"
Q keys Down Down Enter            # third entry: "Eternity 08 Self-test"
for i in $(seq 1 $(( 180 * TSCALE ))); do
    sleep 5
    grep -q '^SMOKE_DONE' "$OUT/serial-bios.log" 2>/dev/null && break
    kill -0 $QPID 2>/dev/null || break
done
grep -E '^(INFO|CHECK|SMOKE)' "$OUT/serial-bios.log" | tr -d '\r'
grep -q '^SMOKE: PASS' "$OUT/serial-bios.log"
