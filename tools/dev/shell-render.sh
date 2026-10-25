#!/bin/bash
# Windows-side wrapper: run the offscreen shell render test in WSL (bash tools/dev/shell-render.sh).
HERE=$(cd "$(dirname "$0")/../.." && pwd)
WROOT=/mnt/c${HERE#/c}
MSYS_NO_PATHCONV=1 wsl -d Debian -u root -- env E8ROOT="$WROOT" OUT=/tmp/e8shell bash "$WROOT/tests/host/test_shell_render.sh" 2>&1 | grep -v "screen size is bogus"
exit ${PIPESTATUS[0]}
