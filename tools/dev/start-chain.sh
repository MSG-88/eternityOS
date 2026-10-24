#!/bin/bash
cd /srv/eternity-build && bash tests/run-qemu-install.sh out/eternity-08-0.1.0-amd64.iso stop 2>/dev/null; sleep 3; pkill -f qemu-system 2>/dev/null; sleep 2
pkill -f live-loop.sh 2>/dev/null
setsid nohup bash /mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08/tools/dev/live-loop.sh > /srv/eternity-build/tests/out/live-loop.log 2>&1 < /dev/null &
setsid nohup bash /mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08/tools/dev/chain-build-test-install.sh > /dev/null 2>&1 < /dev/null &
echo "chain 9 started pid $!"; sleep 5; head -2 /srv/eternity-build/out/build9-run.log
