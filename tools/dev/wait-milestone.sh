#!/bin/bash
# Wait (poll every 60 s) until one of the chain logs shows a new milestone, then print it and exit.
# Usage: bash tools/dev/wait-milestone.sh "<regex>" [log basename]   (runs from Windows; reads the WSL share)
PAT=${1:-"BUILD11 INSTALL DONE|BUILD11 DONE|BUILD13 VISUAL DONE|BUILD13 DONE|rc=[1-9]"}
for i in $(seq 1 600); do
  for log in build11-run.log build13-run.log; do
    f="//wsl.localhost/Debian/srv/eternity-build/out/$log"
    [ -f "$f" ] && grep -E "$PAT" "$f" 2>/dev/null | tail -3 | grep -q . && { echo "== $log"; grep -E "$PAT" "$f" | tail -3; exit 0; }
  done
  sleep 60
done
echo "timeout waiting for: $PAT"; exit 1
