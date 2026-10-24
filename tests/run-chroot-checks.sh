#!/bin/bash
# Run the smoke.sh check_* functions inside the live-build chroot left by the last
# `lb build` (file-level checks only; boot-dependent ones report SKIP/FAIL).
# Usage: tests/run-chroot-checks.sh [chroot-dir] [check-name ...]
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
CHROOT=${1:-/srv/eternity-build/chroot}
shift || true
[ -d "$CHROOT/usr" ] || { echo "no chroot at $CHROOT" >&2; exit 2; }
mkdir -p "$CHROOT/usr/lib/eternity/expect"
cp "$HERE/smoke.sh" "$CHROOT/tmp/smoke-funcs.sh"
cp -a "$HERE/expect/." "$CHROOT/usr/lib/eternity/expect/" 2>/dev/null || true
names="$*"
chroot "$CHROOT" /bin/bash -c '
    export ETERNITY_SMOKE_SOURCE_ONLY=1
    . /tmp/smoke-funcs.sh
    failed=0
    for fn in $(declare -F | awk "{print \$3}" | grep "^check_" | sort); do
        name=${fn#check_}
        if [ -n "'"$names"'" ] && ! echo " '"$names"' " | grep -q " $name "; then continue; fi
        reason=$($fn 2>&1); rc=$?
        case $rc in
            0) echo "CHECK $name: PASS" ;;
            2) echo "CHECK $name: SKIP $reason" ;;
            *) echo "CHECK $name: FAIL $reason"; failed=1 ;;
        esac
    done
    rm -f /tmp/smoke-funcs.sh
    exit $failed
'
