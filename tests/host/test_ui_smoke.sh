#!/bin/bash
# Headless smoke test of the GTK windows under Xvfb (build host / WSL with python3-gi and xvfb).
# Each window is constructed with ETERNITY_UI_SMOKE=1, walks its states and exits 0.
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
PY=$ROOT/config/includes.chroot/usr/lib/eternity/py
export ETERNITY_ASSETS=$ROOT/config/includes.chroot/usr/share/eternity
export ETERNITY_NO_KEYRING=1 ETERNITY_UI_SMOKE=1
export HOME=$(mktemp -d) XDG_CONFIG_HOME=$HOME/.config XDG_STATE_HOME=$HOME/.local/state
command -v xvfb-run >/dev/null || { echo "SKIP xvfb-run missing"; exit 0; }
python3 -c "import gi" 2>/dev/null || { echo "SKIP python3-gi missing"; exit 0; }
fail=0
run() { local name=$1; shift
    if xvfb-run -a -s "-screen 0 1280x800x24" timeout 60 python3 -c "import sys; sys.path.insert(0, '$PY'); $*" >"$HOME/$name.log" 2>&1; then
        echo "PASS $name"
    else
        echo "FAIL $name"; sed 's/^/    /' "$HOME/$name.log" | tail -15; fail=1
    fi
}
run firstrun "from eternity.ui import firstrun; sys.exit(firstrun.main([]))"
[ -f "$XDG_CONFIG_HOME/eternity/settings.json" ] && echo "PASS firstrun wrote settings" || { echo "FAIL firstrun settings missing"; fail=1; }
for mod in ask shell launcher monitor settingsui; do
    [ -f "$PY/eternity/ui/$mod.py" ] || continue
    run "$mod" "from eternity.ui import $mod; sys.exit($mod.main([]))"
done
rm -rf "$HOME"
[ $fail = 0 ] && echo "UI SMOKE: PASS" || { echo "UI SMOKE: FAIL"; exit 1; }
