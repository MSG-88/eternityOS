#!/bin/bash
# Start chain-build13.sh detached inside WSL once no other chain runs
# (run as: wsl -d Debian -u root -- bash /mnt/c/.../tools/dev/start-chain13.sh).
cd /srv/eternity-build || exit 1
if pgrep -f "chain-build1[123]" >/dev/null; then echo "another chain is running; not starting build 13"; exit 1; fi
pkill -f live-loop.sh 2>/dev/null
setsid nohup bash /mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08/tools/dev/chain-build13.sh > /srv/eternity-build/out/chain13.nohup 2>&1 < /dev/null &
echo "chain 13 started pid $!"
sleep 20
head -3 /srv/eternity-build/out/build13-run.log
