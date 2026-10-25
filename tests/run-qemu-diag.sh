#!/bin/bash
# Diagnose the Eternity session under lightdm (build 13: the login attempt bounced back to the
# greeter). Boots the "Eternity shell" GRUB entry, tries the greeter login, then logs in on tty3
# and captures lightdm's log, ~/.xsession-errors and the Eternity logs as screenshots, and finally
# starts eternity-session from the VT so its own output lands in /tmp/es.log.
#   tests/run-qemu-diag.sh <iso>   -> tests/out/d-*.png
#   DIAG_SKIP_GREETER=1 skips the greeter attempt; DIAG_SESSION_CMD overrides what runs on the VT.
set -u
ISO=${1:-}
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$HERE/out
MEM=${ETERNITY_QEMU_MEM:-4096}
. "$HERE/qemu-env.sh"
[ -n "$ISO" ] && [ -f "$ISO" ] || { echo "ISO not found: '$ISO'" >&2; exit 2; }
mkdir -p "$OUT"
SOCK=/tmp/eternity-qmp-diag.sock
rm -f "$SOCK" "$OUT/serial-diag.log" "$OUT"/d-*.png
cp /usr/share/OVMF/OVMF_VARS_4M.ms.fd "$OUT/OVMF_VARS-diag.fd"
echo "INFO accel: $ACCEL_NAME mode=diag"

qemu-system-x86_64 "${QEMU_ACCEL[@]}" -m "$MEM" -smp 4 -machine q35,smm=on \
    -global driver=cfi.pflash01,property=secure,value=on \
    -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.secboot.fd \
    -drive if=pflash,format=raw,file="$OUT/OVMF_VARS-diag.fd" \
    -drive file="$ISO",media=cdrom,if=none,id=cd -device ide-cd,drive=cd,bootindex=1 \
    -nic none -no-reboot -vga virtio -display none \
    -serial "file:$OUT/serial-diag.log" \
    -qmp "unix:$SOCK,server,nowait" &
QPID=$!
trap 'kill $QPID 2>/dev/null; wait $QPID 2>/dev/null' EXIT
Q() { python3 "$HERE/qmp.py" "$SOCK" "$@"; }

t0=$(date +%s)
grub_settle
Q keys Down Down Down Enter                      # "Eternity 08 Live (Eternity shell)"
S 38; Q screendump "$OUT/d-login.png"
echo "INFO greeter at t=$(( $(date +%s) - t0 ))s"
if [ -z "${DIAG_SKIP_GREETER:-}" ]; then
    Q keys eternity Enter                        # the login attempt lightdm bounces
    S 25; Q screendump "$OUT/d-after-login.png"
    echo "INFO after-login at t=$(( $(date +%s) - t0 ))s"
fi

Q keys Ctrl-Alt-F3; S 3
Q keys eternity Enter; S 3; Q keys eternity Enter; S 4
Q screendump "$OUT/d-vt.png"
Q keys "cat /etc/lightdm/lightdm.conf.d/20-session.conf; sudo -n grep -hiE 'session|fail|exit|greeter' /var/log/lightdm/lightdm.log 2>&1 | tail -n 12 | cut -c1-150" Enter
S 5; Q screendump "$OUT/d-lightdm-log.png"
Q keys "clear; tail -n 22 ~/.xsession-errors 2>&1 | cut -c1-150; ls ~/.local/state/eternity/ 2>&1" Enter
S 5; Q screendump "$OUT/d-xsession-errors.png"
Q keys "clear; tail -n 18 ~/.local/state/eternity/ui.log ~/.local/state/eternity/*.log 2>&1 | cut -c1-150" Enter
S 5; Q screendump "$OUT/d-eternity-logs.png"
CMD=${DIAG_SESSION_CMD:-eternity-session}
Q keys "clear; $CMD > /tmp/es.log 2>&1; tail -n 25 /tmp/es.log | cut -c1-150" Enter
S 45; Q screendump "$OUT/d-vt-session.png"      # the shell if it comes up on tty3, else the log tail
S 45; Q screendump "$OUT/d-vt-session2.png"
echo "INFO done at t=$(( $(date +%s) - t0 ))s; screenshots: $(ls "$OUT"/d-*.png | xargs -n1 basename | tr '\n' ' ')"
exit 0
