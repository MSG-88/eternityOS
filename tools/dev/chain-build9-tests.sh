#!/bin/bash
# Build 9 tests only (the ISO already exists in /srv/eternity-build/out): smoke + Secure Boot self-test, unattended install, boot the installed
# disk through its NVRAM entry and through the EFI/BOOT fallback path. Detached in WSL.
# Log: /srv/eternity-build/out/build9-tests.log, ends with "BUILD9 DONE".
REPO=/mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08
LOG=/srv/eternity-build/out/build9-tests.log
cd /srv/eternity-build || exit 1
rm -f tests/out/install/*.png tests/out/install/*.ppm tests/out/install/progress-* 2>/dev/null
sync; echo 3 > /proc/sys/vm/drop_caches
export ETERNITY_QEMU_MEM=3072
echo "chain9-tests: starting $(date)" > "$LOG"; rc=0
cp "$REPO"/tests/*.sh "$REPO"/tests/*.py tests/ 2>/dev/null; chmod 755 tests/*.sh
ISO=out/eternity-08-0.1.0-amd64.iso
echo "chain9: smoke $(date)" >> "$LOG"
bash tests/run-qemu-smoke.sh "$ISO" > tests/out/smoke.log 2>&1; echo "-> smoke rc=$?" >> "$LOG"
grep -E '^(CHECK|SMOKE)' tests/out/smoke.log >> "$LOG"
echo "chain9: secureboot $(date)" >> "$LOG"
bash tests/run-qemu-visual.sh "$ISO" --selftest > tests/out/secureboot.log 2>&1; echo "-> secureboot rc=$?" >> "$LOG"
grep -E '^(CHECK|SMOKE|INFO)' tests/out/secureboot.log >> "$LOG"
bash tests/run-qemu-install.sh "$ISO" wipe >> "$LOG" 2>&1
echo "chain9: install auto starting $(date)" >> "$LOG"
bash tests/run-qemu-install.sh "$ISO" auto >> "$LOG" 2>&1
bash tests/run-qemu-install.sh "$ISO" stop >> "$LOG" 2>&1; sleep 5
cp -f tests/out/install/serial.log tests/out/install/serial-install.log
echo "chain9: boot-disk starting $(date)" >> "$LOG"
bash tests/run-qemu-install.sh "$ISO" boot-disk >> "$LOG" 2>&1
sleep 30; bash tests/run-qemu-install.sh "$ISO" stop >> "$LOG" 2>&1; sleep 3
echo "chain9: boot-fallback starting $(date)" >> "$LOG"
bash tests/run-qemu-install.sh "$ISO" boot-fallback >> "$LOG" 2>&1; echo "-> boot-fallback rc=$?" >> "$LOG"
bash tests/run-qemu-install.sh "$ISO" stop >> "$LOG" 2>&1
mkdir -p "$REPO/tests/out/build9-install" && cp -a tests/out/install/. "$REPO/tests/out/build9-install/" 2>/dev/null
cp -f tests/out/smoke.log tests/out/secureboot.log "$REPO/tests/out/" 2>/dev/null
echo "BUILD9 DONE rc=$rc $(date)" >> "$LOG"
