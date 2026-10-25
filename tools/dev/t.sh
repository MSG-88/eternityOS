#!/bin/bash
# Windows-side wrapper: run the host tests in WSL (bash tools/dev/t.sh [pattern] [tail]); exit code = unittest's.
HERE=$(cd "$(dirname "$0")/../.." && pwd)
WROOT=/mnt/c${HERE#/c}
MSYS_NO_PATHCONV=1 wsl -d Debian -- env E8ROOT="$WROOT" bash "$WROOT/tools/dev/host-tests.sh" "$@" 2>&1 | grep -v "screen size is bogus"
exit ${PIPESTATUS[0]}
