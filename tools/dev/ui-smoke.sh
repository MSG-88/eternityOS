#!/bin/bash
cd "${E8ROOT:-/mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08}" || exit 1
export HOME=$(mktemp -d) ETERNITY_NO_KEYRING=1
bash tests/host/test_ui_smoke.sh 2>&1 | tail -25
