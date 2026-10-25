#!/bin/bash
# Kill any leftover chain/QEMU processes and start the build 13 chain fresh.
pgrep -af "chain-build|run-qemu|qemu-system|live-loop" | cut -c1-100
pkill -f "chain-build1" 2>/dev/null; pkill -f run-qemu 2>/dev/null; pkill -f qemu-system 2>/dev/null; pkill -f live-loop.sh 2>/dev/null; sleep 3
rm -f /srv/eternity-build/out/build13-run.log
cd /srv/eternity-build || exit 1
setsid nohup bash /mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08/tools/dev/chain-build13.sh > /srv/eternity-build/out/chain13.nohup 2>&1 < /dev/null &
echo "chain 13 started pid $!"
sleep 15; head -2 /srv/eternity-build/out/build13-run.log
