#!/bin/bash
# Full verification suite for a built ISO. Exit 0 only when every run passes.
#   1. direct-kernel smoke (no network, no bootloader)
#   2. UEFI Secure Boot via GRUB "Self-test" entry (proves shim + signed kernel + GRUB menu)
#   3. UEFI visual run: GRUB / splash / login / desktop / terminal screenshots
#   4. legacy BIOS boot via GRUB "Self-test" entry
set -uo pipefail
ISO=${1:-}
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$HERE/out
[ -n "$ISO" ] && [ -f "$ISO" ] || { echo "ISO not found: '$ISO'" >&2; exit 2; }
mkdir -p "$OUT"
declare -A R
run() { local name=$1; shift; echo; echo "#### $name"; "$@" > "$OUT/$name.log" 2>&1; R[$name]=$?; grep -E '^(INFO|CHECK|SMOKE|screenshots)' "$OUT/$name.log" | cut -c1-200; echo "-> rc=${R[$name]}"; }

run smoke        bash "$HERE/run-qemu-smoke.sh" "$ISO"
cp -f "$OUT/serial.log" "$OUT/serial-smoke.log" 2>/dev/null || true
run secureboot   bash "$HERE/run-qemu-visual.sh" "$ISO" --selftest
run visual       bash "$HERE/run-qemu-visual.sh" "$ISO"
run bios         bash "$HERE/run-qemu-bios.sh" "$ISO"

echo; echo "#### summary"
fail=0
for k in smoke secureboot visual bios; do
    if [ "${R[$k]}" = 0 ]; then s=PASS; else s=FAIL; fail=1; fi
    printf '  %-11s %s\n' "$k" "$s"
done
grep -q 'CHECK secureboot: PASS' "$OUT/secureboot.log" 2>/dev/null && echo "  Secure Boot: enabled in the UEFI run" || { echo "  Secure Boot: NOT confirmed"; fail=1; }
exit $fail
