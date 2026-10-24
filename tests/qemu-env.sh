#!/bin/bash
# Sourced by the QEMU runners: choose the accelerator and a time scale.
#
# With /dev/kvm the VMs run at native speed. Without it (nested virtualization lost,
# e.g. Windows update KB5127648 on AMD hosts, October 2026) QEMU falls back to TCG
# software emulation, which is roughly ten times slower, so every wait and timeout in
# the runners is multiplied by TSCALE. Override with ETERNITY_QEMU_ACCEL=tcg to force
# emulation and ETERNITY_QEMU_TSCALE=N to tune the factor.
if [ -c /dev/kvm ] && [ "${ETERNITY_QEMU_ACCEL:-kvm}" = kvm ]; then
    QEMU_ACCEL=(-enable-kvm -cpu host)
    TSCALE=1
    ACCEL_NAME=kvm
else
    QEMU_ACCEL=(-accel tcg,thread=multi -cpu max)
    TSCALE=${ETERNITY_QEMU_TSCALE:-10}
    ACCEL_NAME=tcg
    echo "WARN: no usable /dev/kvm; QEMU runs under TCG software emulation with ${TSCALE}x timeouts" >&2
fi
export QEMU_ACCEL TSCALE ACCEL_NAME

# Scaled sleep: S 6 waits 6 s under KVM, 60 s under TCG (TSCALE=10).
S() { sleep $(( $1 * TSCALE )); }

# Wait until GRUB has drawn its menu and freeze its 8 s countdown so screenshots and key
# presses are deterministic. Firmware reaches GRUB after ~3 s under KVM and anywhere from
# 10 to 25 s under TCG, so Down+Up is pressed every second from early on: it leaves the
# selection on the first entry, and keys that arrive before GRUB is up are harmless.
# Needs a Q() function (qmp.py wrapper).
grub_settle() {
    local i
    sleep 2
    for i in $(seq 1 $(( 4 + 3 * TSCALE ))); do
        Q keys Down Up >/dev/null 2>&1
        sleep 1
    done
}
