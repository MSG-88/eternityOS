#!/bin/bash
# Launch build15.sh detached in WSL (run: wsl -d Debian -u root -- bash /mnt/c/.../tools/dev/start-build15.sh).
if pgrep -f "chain-build1[0-9]|dev/build15.sh|run-qemu" >/dev/null; then echo "a build is already running; not starting build 15"; exit 1; fi
pkill -f live-loop.sh 2>/dev/null
setsid nohup bash /mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08/tools/dev/build15.sh > /srv/eternity-build/out/build15.nohup 2>&1 < /dev/null &
echo "build 15 started pid $!"
sleep 15
tail -3 /srv/eternity-build/out/build15-run.log 2>/dev/null
