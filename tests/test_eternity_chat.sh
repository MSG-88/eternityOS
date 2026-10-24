#!/bin/bash
# Host-side unit test for eternity-chat's model selection (no model or llama.cpp needed).
# ETERNITY_DRY_RUN=1 makes eternity-chat print the chosen model path and exit 0.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
CHAT=$HERE/../config/includes.chroot/usr/local/bin/eternity-chat
MODELS=$(mktemp -d)
touch "$MODELS/default.gguf" "$MODELS/small.gguf"
fail=0
t() { # name expected cmd...
    local name=$1 want=$2; shift 2
    local got
    got=$(ETERNITY_DRY_RUN=1 ETERNITY_MODELS_DIR="$MODELS" "$@" 2>&1 | tail -n 1)
    if [ "$got" = "$want" ]; then echo "PASS $name"; else echo "FAIL $name: want '$want' got '$got'"; fail=1; fi
}
[ -x "$CHAT" ] || { echo "FAIL eternity-chat missing or not executable at $CHAT"; rm -rf "$MODELS"; exit 1; }
t low-memory-picks-small   "$MODELS/small.gguf"   env MEMAVAILABLE_KB=3000000  "$CHAT"
t high-memory-picks-default "$MODELS/default.gguf" env MEMAVAILABLE_KB=12000000 "$CHAT"
t flag-small-wins          "$MODELS/small.gguf"   env MEMAVAILABLE_KB=12000000 "$CHAT" --small
t flag-default-wins        "$MODELS/default.gguf" env MEMAVAILABLE_KB=3000000  "$CHAT" --default
t explicit-model-path      "/x/y.gguf"            env MEMAVAILABLE_KB=12000000 "$CHAT" --model /x/y.gguf
rm -rf "$MODELS"
exit $fail
