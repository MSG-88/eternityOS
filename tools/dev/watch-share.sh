#!/bin/bash
# Host-side watcher over the \wsl.localhost share (works while the WSL service refuses new
# sessions): emit new CHECK/SMOKE/run-result lines from build 6 and build 9 logs.
B=//wsl.localhost/Debian/srv/eternity-build
declare -A seen
if [ "${SKIP_EXISTING:-0}" = 1 ]; then for f in "$B/out/build6-run.log" "$B/out/build9-run.log" "$B/tests/out/serial.log" "$B/tests/out/serial-visual.log" "$B/tests/out/serial-bios.log"; do [ -f "$f" ] && seen[$f]=$(wc -l < "$f" 2>/dev/null); done; fi
emit() { local f=$1 pat=$2 n
    [ -f "$f" ] || return
    n=$(wc -l < "$f" 2>/dev/null) || return
    [ "$n" -lt "${seen[$f]:-0}" ] && seen[$f]=0
    if [ "$n" -gt "${seen[$f]:-0}" ]; then
        tail -n +$(( ${seen[$f]:-0} + 1 )) "$f" | tr -d '\r' | grep --line-buffered -aE "$pat" | stdbuf -oL cut -c1-170 | stdbuf -oL sed "s|^|$(basename "$f"): |"
        seen[$f]=$n
    fi
}
while true; do
    emit "$B/out/build6-run.log" '^(#### |-> rc=|  (smoke|secureboot|visual|bios|Secure)|BUILD6 DONE|WARN|self-test did not|no serial|screenshots|INFO login)'
    emit "$B/out/build9-run.log" '^(chain:|==> (ISO|lb build|Running)|#### |-> rc=|  (smoke|secureboot|visual|bios|Secure)|BUILD9 DONE|WARN|self-test did not|no serial|screenshots|INFO login|no ISO produced|E: )'
    for f in serial.log serial-visual.log serial-bios.log; do emit "$B/tests/out/$f" '^(ETERNITY|CHECK |SMOKE|INFO (virt|memory|bench|chat|idle))|Kernel panic|Out of memory|Failed to start'; done
    grep -q 'BUILD9 DONE' "$B/out/build9-run.log" 2>/dev/null && { echo "watch: build 9 and its suite finished"; exit 0; }
    sleep 90
done
