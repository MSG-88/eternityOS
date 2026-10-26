#!/bin/bash
# Diagnosis 3: two Hyprland start variants from the VT on the build 13 ISO, without the forced
# software flag. A = plain (Mesa device platform on virtio_gpu), C = MESA_LOADER_DRIVER_OVERRIDE=kms_swrast.
export DIAG_SKIP_GREETER=1
export DIAG_SESSION_CMD="{ export QT_QPA_PLATFORM=wayland QT_QUICK_BACKEND=software XDG_SESSION_TYPE=wayland XDG_CURRENT_DESKTOP=Eternity AQ_NO_MODIFIERS=1 HYPRLAND_EGL_NO_MODIFIERS=1; unset LIBGL_ALWAYS_SOFTWARE; mkdir -p ~/.cache/hyprland; eternity-theme render; C=/home/eternity/.config/eternity/generated/hyprland.conf; Hyprland --config \$C > /tmp/a.log 2>&1; echo A-DONE; MESA_LOADER_DRIVER_OVERRIDE=kms_swrast Hyprland --config \$C > /tmp/c.log 2>&1; echo C-DONE; grep -hiE 'EGL|crash|renderer|error' /tmp/a.log /tmp/c.log /run/user/1000/hypr/*/hyprland.log 2>/dev/null | cut -c1-150 | tail -n 16; }"
exec bash /mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08/tools/dev/run-diag13.sh
