#!/bin/bash
# Every host-side check in one go (build host / WSL, no VM, about a minute):
#   unit tests (settings, providers, actions, agent, cards, launcher index, find),
#   the branding renderer test, and the Xvfb smoke of every GTK window.
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT" || exit 1
rc=0
echo "#### unit tests"
HOME=$(mktemp -d) python3 -m unittest discover -s tests/host -p 'test_*.py' 2>&1 | tail -4 || rc=1
echo "#### branding"
bash tests/host/test_branding.sh | tail -1 || rc=1
echo "#### ui smoke (Xvfb)"
bash tests/host/test_ui_smoke.sh | tail -1 || rc=1
[ $rc = 0 ] && echo "HOST: PASS" || { echo "HOST: FAIL"; exit 1; }
