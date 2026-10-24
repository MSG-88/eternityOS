#!/bin/bash
# Boot the ISO's kernel+initrd directly under QEMU/KVM with `eternity.test` and
# collect the self-test report from the serial console.
# Usage: tests/run-qemu-smoke.sh <iso>   (exit 0 only on "SMOKE: PASS")
set -uo pipefail

ISO=${1:-}
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$HERE/out
MEM=${ETERNITY_QEMU_MEM:-4096}
. "$HERE/qemu-env.sh"                    # QEMU_ACCEL, TSCALE (10x without KVM)
TIMEOUT=${ETERNITY_QEMU_TIMEOUT:-$(( 900 * TSCALE ))}
APPEND_EXTRA=${ETERNITY_QEMU_APPEND:-}   # extra kernel arguments, e.g. systemd.mask=...

[ -n "$ISO" ] && [ -f "$ISO" ] || { echo "ISO not found: '$ISO'" >&2; exit 2; }
mkdir -p "$OUT"
rm -f "$OUT/serial.log" "$OUT/vmlinuz" "$OUT/initrd.img"

# Find the kernel and initrd inside the ISO without extracting the squashfs.
listing=$(xorriso -indev "$ISO" -ls /live/ 2>/dev/null)
kernel=$(echo "$listing" | grep -o "vmlinuz[^' ]*" | sort | head -1)
initrd=$(echo "$listing" | grep -o "initrd.img[^' ]*" | sort | head -1)
[ -n "$kernel" ] && [ -n "$initrd" ] || { echo "no kernel/initrd under /live in $ISO" >&2; echo "$listing" >&2; exit 2; }
xorriso -osirrox on -indev "$ISO" -extract "/live/$kernel" "$OUT/vmlinuz" -extract "/live/$initrd" "$OUT/initrd.img" >/dev/null 2>&1 \
    || { echo "xorriso extract failed" >&2; exit 2; }

# The command line mirrors the ISO's "Self-test" GRUB entry (auto/config bootappend + the
# self-test additions) so live-config creates the same user/hostname as a real boot.
echo "INFO accel: $ACCEL_NAME timeout=${TIMEOUT}s"
timeout --foreground "$TIMEOUT" qemu-system-x86_64 \
    "${QEMU_ACCEL[@]}" -m "$MEM" -smp 4 \
    -nic none -display none -no-reboot \
    -cdrom "$ISO" \
    -kernel "$OUT/vmlinuz" -initrd "$OUT/initrd.img" \
    -append "boot=live components quiet splash locales=en_US.UTF-8 username=eternity hostname=eternity live-config.noautologin noeject eternity.test console=ttyS0,115200 $APPEND_EXTRA" \
    -serial "file:$OUT/serial.log" >"$OUT/qemu-smoke.log" 2>&1
qrc=$?

if [ ! -f "$OUT/serial.log" ]; then echo "no serial output (qemu rc=$qrc)" >&2; cat "$OUT/qemu-smoke.log" >&2; exit 1; fi
grep -E '^(INFO|CHECK|SMOKE)' "$OUT/serial.log" | tr -d '\r'
if ! grep -q '^SMOKE_DONE' "$OUT/serial.log"; then
    echo "self-test did not finish (qemu rc=$qrc, timeout=${TIMEOUT}s); last serial lines:" >&2
    tail -n 30 "$OUT/serial.log" >&2
    exit 1
fi
grep -q '^SMOKE: PASS' "$OUT/serial.log"
