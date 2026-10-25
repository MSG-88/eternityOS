#!/bin/sh
# Restart the Eternity daemon and shell inside a running session. Run as the session user with
# XDG_RUNTIME_DIR and HYPRLAND_INSTANCE_SIGNATURE set (e8pull.sh does this). Lives in its own file so
# that no pkill pattern below appears on the command line of the shell running it.
#
# The daemon is "python3 -c '...from eternity import daemon...'" under eternity-supervise: kill the
# supervisor and the daemon, then start a fresh supervisor through the compositor so it gets the
# session environment. The shell's supervisor stays and restarts quickshell by itself.
eternity-theme render >/dev/null 2>&1
hyprctl reload >/dev/null 2>&1
pkill -f "eternity-supervise eternity-daemon"
pkill -f "from eternity import daemon"
sleep 1
if hyprctl dispatch exec "eternity-supervise eternity-daemon" >/dev/null 2>&1; then
    echo "daemon restarted"
else
    echo "hyprctl exec FAILED: start it by hand with: eternity-supervise eternity-daemon &"
fi
pkill quickshell
