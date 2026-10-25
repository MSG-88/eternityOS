#!/bin/bash
# Build 13 chain: the Eternity session (Hyprland + Quickshell shell, daemon, lock) next to XFCE,
# plus deeper Claude Code. Build, then the XFCE visual run, the Eternity-session visual run, smoke,
# Secure Boot self-test, install + boot-disk + boot-fallback, BIOS and USB.
# Log /srv/eternity-build/out/build13-run.log, ends with "BUILD13 DONE".
REPO=/mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08
LOG=/srv/eternity-build/out/build13-run.log
cd /srv/eternity-build || exit 1
[ -f out/eternity-08-0.1.0-amd64-build12.iso ] || cp -f out/eternity-08-0.1.0-amd64.iso out/eternity-08-0.1.0-amd64-build12.iso 2>/dev/null
sync; echo 3 > /proc/sys/vm/drop_caches
export ETERNITY_QEMU_MEM=3072
pgrep -f live-loop.sh >/dev/null || setsid nohup bash "$REPO/tools/dev/live-loop.sh" > /srv/eternity-build/tests/out/live-loop.log 2>&1 < /dev/null &
echo "chain13: build starting $(date)" > "$LOG"
bash "$REPO/build.sh" >> "$LOG" 2>&1; rc=$?
echo "BUILD13 BUILD rc=$rc $(date)" >> "$LOG"
[ -f out/eternity-08-0.1.0-amd64.iso ] && [ out/eternity-08-0.1.0-amd64.iso -nt out/eternity-08-0.1.0-amd64-build12.iso ] || { echo "BUILD13 DONE rc=$rc (no new ISO)" >> "$LOG"; exit 1; }
cp "$REPO"/tests/*.sh "$REPO"/tests/*.py tests/ 2>/dev/null; chmod 755 tests/*.sh
ISO=out/eternity-08-0.1.0-amd64.iso
run() { local name=$1; shift; echo "chain13: $name starting $(date)" >> "$LOG"; "$@" > "tests/out/$name.log" 2>&1; local r=$?
        echo "-> $name rc=$r" >> "$LOG"; grep -E '^(CHECK|SMOKE|INFO|screenshots)' "tests/out/$name.log" | cut -c1-160 >> "$LOG"; }
run visual     bash tests/run-qemu-visual.sh "$ISO"
run visual-eternity bash "tests/run-qemu-visual.sh" "$ISO" --session eternity
mkdir -p "$REPO/tests/out/build13" && cp -f tests/out/*.png tests/out/*.log "$REPO/tests/out/build13/" 2>/dev/null
echo "BUILD13 VISUAL DONE $(date)" >> "$LOG"
run smoke      bash tests/run-qemu-smoke.sh "$ISO"
cp -f tests/out/serial.log tests/out/serial-smoke.log 2>/dev/null
run secureboot bash tests/run-qemu-visual.sh "$ISO" --selftest
echo "BUILD13 SMOKE DONE $(date)" >> "$LOG"
rm -f tests/out/install/*.png tests/out/install/*.ppm tests/out/install/progress-* 2>/dev/null
bash tests/run-qemu-install.sh "$ISO" wipe >> "$LOG" 2>&1
echo "chain13: install auto starting $(date)" >> "$LOG"
bash tests/run-qemu-install.sh "$ISO" auto >> "$LOG" 2>&1; echo "-> install auto rc=$?" >> "$LOG"
bash tests/run-qemu-install.sh "$ISO" stop >> "$LOG" 2>&1; sleep 5
cp -f tests/out/install/serial.log tests/out/install/serial-install.log
echo "chain13: boot-disk starting $(date)" >> "$LOG"
bash tests/run-qemu-install.sh "$ISO" boot-disk >> "$LOG" 2>&1; echo "-> boot-disk rc=$?" >> "$LOG"
sleep 30; bash tests/run-qemu-install.sh "$ISO" stop >> "$LOG" 2>&1; sleep 3
echo "chain13: boot-fallback starting $(date)" >> "$LOG"
bash tests/run-qemu-install.sh "$ISO" boot-fallback >> "$LOG" 2>&1; echo "-> boot-fallback rc=$?" >> "$LOG"
bash tests/run-qemu-install.sh "$ISO" stop >> "$LOG" 2>&1
mkdir -p "$REPO/tests/out/build13-install" && cp -a tests/out/install/. "$REPO/tests/out/build13-install/" 2>/dev/null
echo "BUILD13 INSTALL DONE $(date)" >> "$LOG"
run bios       bash tests/run-qemu-bios.sh "$ISO"
run usb        bash tests/run-qemu-usb.sh "$ISO"
cp -f tests/out/*.png tests/out/*.log "$REPO/tests/out/build13/" 2>/dev/null
echo "BUILD13 DONE rc=$rc $(date)" >> "$LOG"
