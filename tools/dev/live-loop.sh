#!/bin/bash
# Live view of whatever Eternity 08 test VM is running: every 30 s screendump the first
# QMP socket that answers into live.png (WSL and Windows side), note which VM it was,
# press Shift every 3 min so the guest display never blanks, and keep a 5-minute history.
# Runs forever (until killed); it idles when no VM is up.
cd /srv/eternity-build || exit 1
WIN=/mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08/tests/out/install
OUT=/srv/eternity-build/tests/out/install
mkdir -p "$WIN" "$OUT"
SOCKS="/tmp/eternity-install.sock:install /tmp/eternity-qmp.sock:visual-or-secureboot /tmp/eternity-qmp-bios.sock:bios /tmp/eternity-qmp-smoke.sock:smoke"
i=0; n=$(ls "$OUT"/progress-*.png 2>/dev/null | wc -l)
while true; do
    i=$((i+1)); got=
    for entry in $SOCKS; do
        s=${entry%%:*}; name=${entry##*:}
        [ -S "$s" ] || continue
        if [ $((i % 6)) -eq 0 ]; then python3 tests/qmp.py "$s" key shift 2>/dev/null; sleep 2; fi
        if python3 tests/qmp.py "$s" screendump "$OUT/live.png" 2>/dev/null; then
            cp -f "$OUT/live.png" "$WIN/live.png.tmp" && mv -f "$WIN/live.png.tmp" "$WIN/live.png"
            echo "$(TZ=Asia/Kolkata date '+%H:%M:%S IST') ($name VM)" > "$WIN/live.txt"
            [ $((i % 10)) -eq 0 ] && { n=$((n+1)); cp -f "$OUT/live.png" "$OUT/progress-$n.png"; }
            got=1; break
        fi
    done
    [ -n "$got" ] || echo "$(TZ=Asia/Kolkata date '+%H:%M:%S IST') no VM running (build or idle)" > "$WIN/live.txt"
    sleep 30
done
