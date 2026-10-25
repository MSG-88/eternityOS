#!/bin/bash
# Start chain-build14.sh detached inside WSL once no other chain runs
# (run as: wsl -d Debian -u root -- bash /mnt/c/.../tools/dev/start-chain14.sh).
cd /srv/eternity-build || exit 1
if pgrep -f "chain-build1[1234]" >/dev/null; then echo "another chain is running; not starting build 14"; exit 1; fi
pkill -f live-loop.sh 2>/dev/null
setsid nohup bash /mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08/tools/dev/chain-build14.sh > /srv/eternity-build/out/chain14.nohup 2>&1 < /dev/null &
echo "chain 14 started pid $!"
sleep 20
head -3 /srv/eternity-build/out/build14-run.log
