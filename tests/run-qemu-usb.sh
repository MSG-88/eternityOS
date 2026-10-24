#!/bin/bash
# Boot the ISO the way a raw-written USB stick appears to a laptop: as a USB mass-storage
# DISK, not a CD-ROM. The other runners attach the ISO as a CD-ROM, which takes the
# El Torito path; a disk takes the hybrid MBR/GPT path (EFI System Partition 2 holding
# shim+GRUB, ISO9660 on the raw device found via /.disk/info). Real hardware does the latter.
#
#   tests/run-qemu-usb.sh <iso>          OVMF Secure Boot (Microsoft keys): GRUB menu screenshot,
#                                        then the Self-test entry and its serial report
#   tests/run-qemu-usb.sh <iso> bios     same under SeaBIOS (hybrid MBR boot code)
#
# Outputs: tests/out/grub-usb-<fw>.png, tests/out/serial-usb-<fw>.log. Exit 0 on SMOKE: PASS.
set -uo pipefail
ISO=${1:-}; FW=${2:-uefi}
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$HERE/out
MEM=${ETERNITY_QEMU_MEM:-4096}
. "$HERE/qemu-env.sh"            # QEMU_ACCEL, TSCALE, grub_settle
[ -n "$ISO" ] && [ -f "$ISO" ] || { echo "ISO not found: '$ISO'" >&2; exit 2; }
case "$FW" in uefi|bios) ;; *) echo "firmware must be uefi or bios" >&2; exit 2;; esac
mkdir -p "$OUT"
SOCK=/tmp/eternity-qmp-usb.sock   # unix sockets cannot live on /mnt/c
OVL=/tmp/eternity-usb-overlay.qcow2
rm -f "$SOCK" "$OVL" "$OUT/serial-usb-$FW.log"
# A thin writable overlay: usb-storage wants a writable backend, the ISO stays untouched.
qemu-img create -q -f qcow2 -b "$ISO" -F raw "$OVL"
echo "INFO accel: $ACCEL_NAME firmware=$FW"

FWARGS=()
if [ "$FW" = uefi ]; then
    cp /usr/share/OVMF/OVMF_VARS_4M.ms.fd "$OUT/OVMF_VARS_usb.fd"
    FWARGS=(-machine q35,smm=on -global driver=cfi.pflash01,property=secure,value=on
            -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.secboot.fd
            -drive if=pflash,format=raw,file="$OUT/OVMF_VARS_usb.fd" -vga virtio)
else
    FWARGS=(-vga std)
fi

qemu-system-x86_64 "${QEMU_ACCEL[@]}" -m "$MEM" -smp 4 "${FWARGS[@]}" \
    -device qemu-xhci,id=xhci \
    -drive if=none,id=usbstick,format=qcow2,file="$OVL" \
    -device usb-storage,bus=xhci.0,drive=usbstick,bootindex=1 \
    -nic none -no-reboot -display none \
    -serial "file:$OUT/serial-usb-$FW.log" -qmp "unix:$SOCK,server,nowait" &
QPID=$!
trap 'kill $QPID 2>/dev/null; wait $QPID 2>/dev/null; rm -f "$OVL"' EXIT
Q() { python3 "$HERE/qmp.py" "$SOCK" "$@"; }

grub_settle
Q screendump "$OUT/grub-usb-$FW.png"
Q keys Down Down Enter            # third entry: "Eternity 08 Self-test"
for i in $(seq 1 $(( 180 * TSCALE ))); do
    sleep 5
    grep -q '^SMOKE_DONE' "$OUT/serial-usb-$FW.log" 2>/dev/null && break
    kill -0 $QPID 2>/dev/null || break
done
grep -E '^(INFO|CHECK|SMOKE)' "$OUT/serial-usb-$FW.log" | tr -d '\r'
grep -q '^SMOKE: PASS' "$OUT/serial-usb-$FW.log"
