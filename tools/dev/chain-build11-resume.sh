#!/bin/bash
# Resume of the build 11 chain after the laptop's unexpected shutdown on 2026-10-25 (the chain
# died at the install step). Skips build and visual (both done, results in tests/out/build11),
# runs install -> boot-disk -> boot-fallback -> smoke -> Secure Boot -> BIOS -> USB, then waits
# for out/build12.go and runs chain-build12.sh. Log: /srv/eternity-build/out/build11-run.log
# (appended), ends with "BUILD11 DONE".
REPO=/mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08
LOG=/srv/eternity-build/out/build11-run.log
cd /srv/eternity-build || exit 1
sync; echo 3 > /proc/sys/vm/drop_caches
export ETERNITY_QEMU_MEM=3072
pgrep -f live-loop.sh >/dev/null || setsid nohup bash "$REPO/tools/dev/live-loop.sh" > /srv/eternity-build/tests/out/live-loop.log 2>&1 < /dev/null &
cp "$REPO"/tests/*.sh "$REPO"/tests/*.py tests/ 2>/dev/null; chmod 755 tests/*.sh
ISO=out/eternity-08-0.1.0-amd64.iso
echo "chain11-resume: starting $(date) (laptop shut down unexpectedly during the install run)" >> "$LOG"
run() { local name=$1; shift; echo "chain11: $name starting $(date)" >> "$LOG"; "$@" > "tests/out/$name.log" 2>&1; local r=$?
        echo "-> $name rc=$r" >> "$LOG"; grep -E '^(CHECK|SMOKE|INFO|screenshots)' "tests/out/$name.log" | cut -c1-160 >> "$LOG"; }
bash tests/run-qemu-install.sh "$ISO" stop >> "$LOG" 2>&1; pkill -f qemu-system 2>/dev/null; sleep 3
rm -f tests/out/install/*.png tests/out/install/*.ppm tests/out/install/progress-* 2>/dev/null
bash tests/run-qemu-install.sh "$ISO" wipe >> "$LOG" 2>&1
echo "chain11: install auto starting $(date)" >> "$LOG"
bash tests/run-qemu-install.sh "$ISO" auto >> "$LOG" 2>&1; echo "-> install auto rc=$?" >> "$LOG"
bash tests/run-qemu-install.sh "$ISO" stop >> "$LOG" 2>&1; sleep 5
cp -f tests/out/install/serial.log tests/out/install/serial-install.log
echo "chain11: boot-disk starting $(date)" >> "$LOG"
bash tests/run-qemu-install.sh "$ISO" boot-disk >> "$LOG" 2>&1; echo "-> boot-disk rc=$?" >> "$LOG"
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
mkdir -p "$REPO/tests/out/build11" && cp -f tests/out/*.png tests/out/*.log "$REPO/tests/out/build11/" 2>/dev/null
echo "BUILD11 DONE $(date)" >> "$LOG"
# Build 12 starts when the repo is ready for it (marker written by the dev session).
echo "chain11-resume: waiting for out/build12.go $(date)" >> "$LOG"
for i in $(seq 1 1440); do [ -f out/build12.go ] && break; sleep 60; done
if [ -f out/build12.go ]; then rm -f out/build12.go; exec bash "$REPO/tools/dev/chain-build12.sh"; fi
echo "chain11-resume: no build12.go after 24 h, exiting $(date)" >> "$LOG"
