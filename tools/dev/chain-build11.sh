#!/bin/bash
# Build 11 chain: build 10 plus the first-run/keyring/runner fixes. Build, then the visual run
# first (it answers whether the first-run wizard now opens), then smoke, Secure Boot self-test,
# BIOS and USB-disk boots. Detached in WSL; log /srv/eternity-build/out/build11-run.log ends
# with "BUILD11 DONE". "BUILD11 VISUAL DONE" marks the point where the stick can be written.
REPO=/mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08
LOG=/srv/eternity-build/out/build11-run.log
cd /srv/eternity-build || exit 1
[ -f out/eternity-08-0.1.0-amd64-build10.iso ] || cp -f out/eternity-08-0.1.0-amd64.iso out/eternity-08-0.1.0-amd64-build10.iso 2>/dev/null
mkdir -p "$REPO/tests/out/build10" && cp -f tests/out/*.log tests/out/*.png "$REPO/tests/out/build10/" 2>/dev/null
sync; echo 3 > /proc/sys/vm/drop_caches
export ETERNITY_QEMU_MEM=3072
pgrep -f live-loop.sh >/dev/null || setsid nohup bash "$REPO/tools/dev/live-loop.sh" > /srv/eternity-build/tests/out/live-loop.log 2>&1 < /dev/null &
echo "chain11: build starting $(date)" > "$LOG"
bash "$REPO/build.sh" >> "$LOG" 2>&1; rc=$?
echo "BUILD11 BUILD rc=$rc $(date)" >> "$LOG"
[ -f out/eternity-08-0.1.0-amd64.iso ] && [ out/eternity-08-0.1.0-amd64.iso -nt out/eternity-08-0.1.0-amd64-build10.iso ] || { echo "BUILD11 DONE rc=$rc (no new ISO)" >> "$LOG"; exit 1; }
cp "$REPO"/tests/*.sh "$REPO"/tests/*.py tests/ 2>/dev/null; chmod 755 tests/*.sh
ISO=out/eternity-08-0.1.0-amd64.iso
run() { local name=$1; shift; echo "chain11: $name starting $(date)" >> "$LOG"; "$@" > "tests/out/$name.log" 2>&1; local r=$?
        echo "-> $name rc=$r" >> "$LOG"; grep -E '^(CHECK|SMOKE|INFO|screenshots)' "tests/out/$name.log" | cut -c1-160 >> "$LOG"; }
run visual     bash tests/run-qemu-visual.sh "$ISO"
mkdir -p "$REPO/tests/out/build11" && cp -f tests/out/*.png tests/out/*.log "$REPO/tests/out/build11/" 2>/dev/null
echo "BUILD11 VISUAL DONE $(date)" >> "$LOG"
rm -f tests/out/install/*.png tests/out/install/*.ppm tests/out/install/progress-* 2>/dev/null
bash tests/run-qemu-install.sh "$ISO" wipe >> "$LOG" 2>&1
echo "chain11: install auto starting $(date)" >> "$LOG"
bash tests/run-qemu-install.sh "$ISO" auto >> "$LOG" 2>&1
bash tests/run-qemu-install.sh "$ISO" stop >> "$LOG" 2>&1; sleep 5
cp -f tests/out/install/serial.log tests/out/install/serial-install.log
echo "chain11: boot-disk starting $(date)" >> "$LOG"
bash tests/run-qemu-install.sh "$ISO" boot-disk >> "$LOG" 2>&1
sleep 30; bash tests/run-qemu-install.sh "$ISO" stop >> "$LOG" 2>&1; sleep 3
echo "chain11: boot-fallback starting $(date)" >> "$LOG"
bash tests/run-qemu-install.sh "$ISO" boot-fallback >> "$LOG" 2>&1; echo "-> boot-fallback rc=$?" >> "$LOG"
bash tests/run-qemu-install.sh "$ISO" stop >> "$LOG" 2>&1
mkdir -p "$REPO/tests/out/build11-install" && cp -a tests/out/install/. "$REPO/tests/out/build11-install/" 2>/dev/null
echo "BUILD11 INSTALL DONE $(date)" >> "$LOG"
run smoke      bash tests/run-qemu-smoke.sh "$ISO"
cp -f tests/out/serial.log tests/out/serial-smoke.log 2>/dev/null
run secureboot bash tests/run-qemu-visual.sh "$ISO" --selftest
run bios       bash tests/run-qemu-bios.sh "$ISO"
run usb        bash tests/run-qemu-usb.sh "$ISO"
cp -f tests/out/*.png tests/out/*.log "$REPO/tests/out/build11/" 2>/dev/null
echo "BUILD11 DONE rc=$rc $(date)" >> "$LOG"
