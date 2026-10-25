#!/bin/bash
# Windows-side wrapper: run the host tests in WSL (bash tools/dev/t.sh [pattern] [tail]); exit code = unittest's.
MSYS_NO_PATHCONV=1 wsl -d Debian -- bash /mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08/tools/dev/host-tests.sh "$@" 2>&1 | grep -v "screen size is bogus"
exit ${PIPESTATUS[0]}
