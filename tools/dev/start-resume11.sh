#!/bin/bash
# Start chain-build11-resume.sh detached inside WSL (run as: wsl -d Debian -u root -- bash /mnt/c/.../tools/dev/start-resume11.sh).
cd /srv/eternity-build || exit 1
pkill -f live-loop.sh 2>/dev/null
setsid nohup bash /mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08/tools/dev/chain-build11-resume.sh > /srv/eternity-build/out/chain11-resume.nohup 2>&1 < /dev/null &
echo "resume started pid $!"
sleep 25
tail -4 /srv/eternity-build/out/build11-run.log
pgrep -af "qemu-system|chain-build11-resume|live-loop" | cut -c1-120
