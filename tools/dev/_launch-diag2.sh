#!/bin/bash
# Diagnosis 2: run the session script without LIBGL_ALWAYS_SOFTWARE from the VT (the proposed fix).
export DIAG_SKIP_GREETER=1
export DIAG_SESSION_CMD="sed 's/^export LIBGL_ALWAYS_SOFTWARE=1//' /usr/local/bin/eternity-session > /tmp/es; mkdir -p ~/.cache/hyprland; sh /tmp/es"
exec bash /mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08/tools/dev/run-diag13.sh
