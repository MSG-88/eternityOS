#!/bin/bash
# Run the Eternity-session diagnosis (tests/run-qemu-diag.sh) against the build 13 ISO on the build
# host. Log: /srv/eternity-build/out/diag13-run.log, ends with "DIAG13 DONE". Start detached:
#   wsl -d Debian -- bash -c 'setsid nohup bash /mnt/c/.../tools/dev/run-diag13.sh >/dev/null 2>&1 < /dev/null &'
REPO=/mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08
LOG=/srv/eternity-build/out/diag13-run.log
cd /srv/eternity-build || exit 1
export ETERNITY_QEMU_MEM=3072
sync; echo 3 > /proc/sys/vm/drop_caches
cp "$REPO"/tests/*.sh "$REPO"/tests/*.py tests/ 2>/dev/null; chmod 755 tests/*.sh
echo "diag13: starting $(date)" > "$LOG"
bash tests/run-qemu-diag.sh out/eternity-08-0.1.0-amd64.iso > tests/out/diag.log 2>&1; rc=$?
grep -E '^(INFO|WARN)' tests/out/diag.log | cut -c1-200 >> "$LOG"
mkdir -p "$REPO/tests/out/build13" && cp -f tests/out/d-*.png tests/out/diag.log "$REPO/tests/out/build13/" 2>/dev/null
echo "DIAG13 DONE rc=$rc $(date)" >> "$LOG"
