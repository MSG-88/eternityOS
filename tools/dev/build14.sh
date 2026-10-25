#!/bin/bash
# Build 14 (phase1 at the merge of slice 2 + the Hyper-V fixes): build only. Testing happens on
# the Hyper-V VM from Windows (tools/elevated), not on QEMU TCG. Log: out/build14-run.log,
# ends with "BUILD14 BUILD rc=<n>"; the ISO lands in /srv/eternity-build/out and in the repo's out/.
REPO=/mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08
LOG=/srv/eternity-build/out/build14-run.log
cd /srv/eternity-build || exit 1
[ -f out/eternity-08-0.1.0-amd64-build13.iso ] || cp -f out/eternity-08-0.1.0-amd64.iso out/eternity-08-0.1.0-amd64-build13.iso 2>/dev/null
pgrep -f qemu-system >/dev/null && { echo "BUILD14 BUILD rc=99 (a QEMU VM is running; refusing to build next to it)" >> "$LOG"; exit 1; }
sync; echo 3 > /proc/sys/vm/drop_caches
echo "build14: build starting $(date)" > "$LOG"
bash "$REPO/build.sh" >> "$LOG" 2>&1; rc=$?
echo "BUILD14 BUILD rc=$rc $(date)" >> "$LOG"
