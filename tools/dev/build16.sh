#!/bin/bash
# Build 16 (phase1: voice output/TTS, and the ASUS RTX 5080 GSP firmware so the panel boots).
# Build only; testing is on the Hyper-V VM (tools/elevated), not QEMU. Log out/build16-run.log,
# ends with "BUILD16 BUILD rc=<n>"; ISO in /srv/eternity-build/out and the repo's out/.
REPO=/mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08
LOG=/srv/eternity-build/out/build16-run.log
cd /srv/eternity-build 2>/dev/null || { mkdir -p /srv/eternity-build/out; cd /srv/eternity-build || exit 1; }
mkdir -p out
[ -f out/eternity-08-0.1.0-amd64-build15.iso ] || cp -f out/eternity-08-0.1.0-amd64.iso out/eternity-08-0.1.0-amd64-build15.iso 2>/dev/null
pgrep -f qemu-system >/dev/null && { echo "BUILD16 BUILD rc=99 (a QEMU VM is running; refusing to build next to it)" >> "$LOG"; exit 1; }
sync; echo 3 > /proc/sys/vm/drop_caches 2>/dev/null
echo "build16: build starting $(date)" > "$LOG"
bash "$REPO/build.sh" >> "$LOG" 2>&1; rc=$?
if [ -f out/eternity-08-0.1.0-amd64.iso ]; then
    ls -la out/eternity-08-0.1.0-amd64.iso >> "$LOG"
    cp -f out/eternity-08-0.1.0-amd64.iso "$REPO/out/eternity-08-0.1.0-amd64.iso" 2>/dev/null
fi
echo "BUILD16 BUILD rc=$rc $(date)" >> "$LOG"
