#!/bin/bash
# Windows-side wrapper: run the offscreen shell render test in WSL (bash tools/dev/shell-render.sh).
MSYS_NO_PATHCONV=1 wsl -d Debian -u root -- bash -c 'cd /mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08 && OUT=/tmp/e8shell bash tests/host/test_shell_render.sh' 2>&1 | grep -v "screen size is bogus"
exit ${PIPESTATUS[0]}
