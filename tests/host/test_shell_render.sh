#!/bin/bash
# The Eternity shell rendered offscreen (Quickshell, software Qt Quick) through the harness
# <shell>/harness.qml, which loads the shell's components into plain windows at a
# chosen logical size, writes a geometry dump (JSON) and screenshots. Asserts design geometry.
# Run on the build host (WSL): bash tests/host/test_shell_render.sh   -> "SHELL RENDER: PASS"
set -u
cd "$(dirname "$0")/../.." || exit 1
SHELL_DIR=config/includes.chroot/usr/share/eternity/shell
OUT=${OUT:-$(mktemp -d)}
fail=0
ok() { echo "PASS $1"; }
bad() { echo "FAIL $1"; fail=1; }

command -v quickshell >/dev/null || { echo "SKIP quickshell not installed"; exit 0; }

render() {  # render <w> <h> <scenario> -> $OUT/<scenario>/dump.json
    local w=$1 h=$2 scen=$3
    mkdir -p "$OUT/$scen"
    ETERNITY_SHELL_DUMP="$OUT/$scen" ETERNITY_HARNESS_W=$w ETERNITY_HARNESS_H=$h ETERNITY_HARNESS_SCENARIO=$scen \
    ETERNITY_SOCK=/nonexistent/daemon.sock QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software QML_IMPORT_PATH=$SHELL_DIR \
        timeout 60 quickshell -p "$SHELL_DIR/harness.qml" > "$OUT/$scen/log.txt" 2>&1
    [ -s "$OUT/$scen/dump.json" ] || { bad "$scen: no dump (see $OUT/$scen/log.txt)"; tail -5 "$OUT/$scen/log.txt"; return 1; }
    grep -E "is not a type|TypeError|ReferenceError|SyntaxError" "$OUT/$scen/log.txt" && bad "$scen: QML errors"
    return 0
}

check() {  # check <scenario> <python expression over d (the dump)> <label>
    local scen=$1 expr=$2 label=$3
    if python3 - "$OUT/$scen/dump.json" "$expr" <<'PY'
import json, sys, math
d = json.load(open(sys.argv[1]))
k = d["k"]; it = d["items"]
def near(a, b, tol=2): return abs(a - b) <= tol
sys.exit(0 if eval(sys.argv[2]) else 1)
PY
    then ok "$scen: $label"; else bad "$scen: $label ($(python3 -c "import json;d=json.load(open('$OUT/$scen/dump.json'));print(d['k'], {k:v for k,v in d['items'].items() if k in ('strip','clock','mark','core','bar')})"))"; fi
}

# atlas asset: 48 frames of the Möbius mark, 8 columns x 6 rows of 256 px
A=$SHELL_DIR/assets/mobius-atlas.png
if [ -f "$A" ] && python3 -c "
import struct,sys; f=open('$A','rb'); f.read(16); w,h=struct.unpack('>II', f.read(8)); sys.exit(0 if (w,h)==(2048,1536) else 1)"; then ok "atlas 2048x1536"; else bad "atlas missing or wrong size"; fi

# 1536x864 is a 1920x1080 panel at 125 %: k = 0.8
render 1536 864 strip && {
    check strip 'near(k, 0.8, 0.001)' "k = 0.8"
    check strip 'near(it["strip"][3], 44*k, 1) and near(it["strip"][2], 1536, 1)' "strip 44k high, full width"
    check strip 'near(it["clock"][0] + it["clock"][2]/2, 1536/2, 2)' "clock centred"
    check strip 'near(it["mark"][0], 28*k, 1) and near(it["mark"][2], 20*k, 1)' "mark at 28k, 20k wide"
    check strip 'd["connected"] is False and it["latency"][4] == "—"' "offline: not connected, readouts show —"
    grep -iE "error|exception" "$OUT/strip/log.txt" | grep -vE "ServerNotFoundError|theme.json" | grep -q . && bad "strip: errors in log" || ok "strip: clean log"
}
render 1920 1080 strip100 && check strip100 'near(k, 1.0, 0.001) and near(it["strip"][3], 44, 1)' "k = 1.0 at native 1080p"

[ -f "$OUT/strip/strip.png" ] && ok "strip.png written ($OUT/strip/strip.png)" || bad "strip.png missing"

# presence desktop with the four design cards (harness injects the state; rot frozen at 0)
render 1536 864 presence && {
    check presence 'near(it["core"][0] + it["core"][2]/2, 960*k, 1) and near(it["core"][1] + it["core"][3]/2, 540*k, 1)' "core centred at (960k, 540k)"
    check presence 'near(it["core"][2], 600*0.5*k, 2)' "core box 600k at s 0.5"
    check presence 'len([x for x in it if x.startswith("card") and x[4:].isdigit()]) == 4 and all(near(it[x][2], 300*k, 1) for x in it if x.startswith("card") and x[4:].isdigit())' "four cards 300k wide"
    check presence 'near(it["card0"][0] + 150*k, (960 + 0)*k, 2) and near(it["card0"][1] + 60*k, (540 - 270)*k, 2)' "card 0 at angle -90 (top of the orbit)"
    check presence 'near(it["card1"][0] + 150*k, (960 + 440)*k, 2) and near(it["card1"][1] + 60*k, 540*k, 2)' "card 1 at angle 0 (right)"
    check presence 'near(it["card3"][0] + 150*k, (960 - 440)*k, 2)' "card 3 at angle 180 (left)"
    check presence 'near(it["caption"][1], 900*k, 2) and it["caption"][4].startswith("Everything stays in orbit")' "caption at y 900k"
    check presence 'near(it["hud"][0], 56*k, 1) and near(it["hud"][2], 1808*k, 1) and near(it["hudleg"][2], 22*k, 1)' "HUD frame 56,112 1808x812 with 22k legs"
    check presence 'it["card0"][4] == "Calendar" and it["card1"][4] == "Mail"' "cards show kicker text"
    grep -iE "error|exception" "$OUT/presence/log.txt" | grep -vE "ServerNotFoundError|theme.json" | grep -q . && bad "presence: errors in log" || ok "presence: clean log"
}
# the same workspace with windows: cards hide, the core moves to the Files placement
render 1536 864 presence-windows && {
    check presence-windows 'it["cards_visible"] is False' "windows: cards hidden"
    check presence-windows 'near(it["core"][0] + it["core"][2]/2, 1600*k, 1) and near(it["core"][2], 600*0.38*k, 2)' "windows: core at (1600k, 540k) s 0.38"
}
[ -f "$OUT/presence/presence.png" ] && ok "presence.png written" || bad "presence.png missing"

if [ $fail = 0 ]; then echo "SHELL RENDER: PASS"; else echo "SHELL RENDER: FAIL (artifacts in $OUT)"; exit 1; fi
