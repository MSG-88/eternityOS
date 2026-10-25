#!/bin/bash
# Run the host-side unit tests inside WSL from the Windows checkout (bash tools/dev/host-tests.sh [pattern] [tail]).
cd "${E8ROOT:-/mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08}" || exit 1
export HOME=$(mktemp -d) ETERNITY_NO_KEYRING=1
python3 -m unittest discover -s tests/host -p "${1:-test_*.py}" > "$HOME/tests.log" 2>&1; rc=$?
tail -${2:-30} "$HOME/tests.log"
exit $rc
