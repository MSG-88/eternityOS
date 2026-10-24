#!/bin/bash
# Build 9 -> full suite -> unattended install -> boot the installed disk. Detached in WSL.
REPO=/mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08
LOG=/srv/eternity-build/out/build9-run.log
cd /srv/eternity-build || exit 1
mkdir -p "$REPO/tests/out/build8-install" && cp -a tests/out/install/. "$REPO/tests/out/build8-install/" 2>/dev/null
rm -f tests/out/install/*.png tests/out/install/*.ppm tests/out/install/progress-*
sync; echo 3 > /proc/sys/vm/drop_caches
export ETERNITY_QEMU_MEM=3072
echo "chain9: build starting $(date)" > "$LOG"
bash "$REPO/build.sh" --test >> "$LOG" 2>&1; rc=$?
echo "BUILD9 SUITE rc=$rc $(date)" >> "$LOG"
cp "$REPO/tests/run-qemu-install.sh" "$REPO/tests/qmp.py" "$REPO/tests/qemu-env.sh" tests/; chmod 755 tests/run-qemu-install.sh
bash tests/run-qemu-install.sh out/eternity-08-0.1.0-amd64.iso wipe >> "$LOG" 2>&1
echo "chain9: install auto starting $(date)" >> "$LOG"
bash tests/run-qemu-install.sh out/eternity-08-0.1.0-amd64.iso auto >> "$LOG" 2>&1
bash tests/run-qemu-install.sh out/eternity-08-0.1.0-amd64.iso stop >> "$LOG" 2>&1; sleep 5
cp -f tests/out/install/serial.log tests/out/install/serial-install.log
echo "chain9: boot-disk starting $(date)" >> "$LOG"
bash tests/run-qemu-install.sh out/eternity-08-0.1.0-amd64.iso boot-disk >> "$LOG" 2>&1
sleep 30; bash tests/run-qemu-install.sh out/eternity-08-0.1.0-amd64.iso stop >> "$LOG" 2>&1
mkdir -p "$REPO/tests/out/build9-install" && cp -a tests/out/install/. "$REPO/tests/out/build9-install/" 2>/dev/null
echo "BUILD9 DONE rc=$rc $(date)" >> "$LOG"
