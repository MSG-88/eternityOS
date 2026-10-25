#!/bin/bash
# Pull the current shell, daemon and session files from the dev host into a running Eternity
# system (live or installed) and restart the daemon and the shell. One short line in the VM:
#   curl -fsS http://HOST:8790/tools/dev/e8pull.sh | sudo bash -s HOST
# The host serves the repository root on port 8790 (python -m http.server from the repo).
set -u
HOST=${1:-172.24.208.1}
BASE="http://$HOST:8790/config/includes.chroot"
pull() {   # pull <path-under-root>
    local p=$1 tmp
    tmp=$(mktemp) || return 1
    if curl -fsS "$BASE/$p" -o "$tmp"; then
        install -m "$(stat -c %a "/$p" 2>/dev/null || echo 644)" "$tmp" "/$p" && echo "updated /$p"
    else
        echo "FAILED $p"
    fi
    rm -f "$tmp"
}
for f in cards.py providers.py settings.py actions.py mcp.py daemon.py agent.py theme.py find.py hw.py launcher_index.py memory.py voice.py; do
    curl -fsS --head "$BASE/usr/lib/eternity/py/eternity/$f" >/dev/null 2>&1 && pull "usr/lib/eternity/py/eternity/$f"
done
for f in $(curl -fsS "$BASE/usr/share/eternity/shell/" | grep -oE 'href="[A-Za-z0-9_]+\.qml"' | cut -d'"' -f2 | sort -u); do
    pull "usr/share/eternity/shell/$f"
done
pull usr/share/eternity/shell/qmldir            # singletons are registered here (a new one needs it)
pull usr/share/eternity/keys.toml
for f in eternity-session eternity-lock eternity-supervise eternity-ask eternity-settings eternity-monitor eternity-launcher eternity-voice; do
    curl -fsS --head "$BASE/usr/local/bin/$f" >/dev/null 2>&1 && pull "usr/local/bin/$f" && chmod 755 "/usr/local/bin/$f"
done
pull usr/share/eternity/hyprland.base.conf
# greeter copies of the shared scene files (see hook 0460)
for f in LockContent.qml GreeterContent.qml Theme.qml Geometry.qml Mobius.qml Wordmark.qml PamAuth.qml Daemon.qml Latency.qml; do
    [ -f /usr/share/eternity/greeter/$f ] && cp -f /usr/share/eternity/shell/$f /usr/share/eternity/greeter/$f
done
U=${SUDO_USER:-eternity}
UID_U=$(id -u "$U"); RT=/run/user/$UID_U; SIG=$(ls "$RT/hypr" 2>/dev/null | head -1)
# Restart daemon and shell as the session user (tools/dev/e8restart.sh; hyprctl needs the instance
# signature, which sudo -H drops, hence env).
RS=$(mktemp) && curl -fsS "http://$HOST:8790/tools/dev/e8restart.sh" -o "$RS" && chmod 644 "$RS"     && sudo -u "$U" -H env XDG_RUNTIME_DIR="$RT" HYPRLAND_INSTANCE_SIGNATURE="$SIG" sh "$RS"; rm -f "$RS"
echo "e8pull done: daemon and shell restarting"
