#!/bin/bash
# Stop the build 11 re-verification chain (it only re-checks a build that already passed) and
# start the build 13 chain now: the new Eternity session is what needs to be seen.
pkill -f chain-build11-resume.sh 2>/dev/null; pkill -f chain-build12.sh 2>/dev/null; sleep 1
pkill -f run-qemu-smoke.sh 2>/dev/null; pkill -f qemu-system 2>/dev/null; sleep 3
rm -f /srv/eternity-build/out/build12.go
echo "chain11 stopped $(date) (smoke re-verification cut short on purpose; build 13 starts now)" >> /srv/eternity-build/out/build11-run.log
exec bash /mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08/tools/dev/start-chain13.sh
