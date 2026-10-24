#!/bin/bash
# Host-side wrapper: run the install harness inside WSL with retries (the WSL service
# refuses new sessions now and then while a VM runs). Usage: inst.sh <cmd> [args...]
export MSYS_NO_PATHCONV=1
for i in 1 2 3 4 5 6; do
    out=$(timeout 600 wsl -d Debian -u root -- bash -c "cd /srv/eternity-build && bash tests/run-qemu-install.sh out/eternity-08-0.1.0-amd64.iso $*" 2>&1 | tr -d '\0' | grep -v 'screen size')
    if ! echo "$out" | grep -q 'Wsl/Service'; then echo "$out"; exit 0; fi
    sleep 20
done
echo "WSL unreachable after retries"; exit 1
