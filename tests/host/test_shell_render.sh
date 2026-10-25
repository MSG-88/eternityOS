#!/bin/bash
# The Eternity shell rendered offscreen (Quickshell, software Qt Quick) through the harness
# <shell>/harness.qml, which loads the shell's components into plain windows at a
# chosen logical size, writes a geometry dump (JSON) and screenshots. Asserts design geometry.
# Run on the build host (WSL): bash tests/host/test_shell_render.sh   -> "SHELL RENDER: PASS"
set -u
cd "${E8ROOT:-$(dirname "$0")/../..}" || exit 1
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

# command bar (design: 800x54 at 560,950; placeholder; chip "Super Space"; accent ring when focused)
render 1536 864 bar && {
    check bar 'near(it["bar"][0], 560*k, 1) and near(it["bar"][1], 950*k, 1) and near(it["bar"][2], 800*k, 1) and near(it["bar"][3], 54*k, 1)' "bar at (560k, 950k) 800k x 54k"
    check bar 'it["placeholder"][4] == "Ask Eternity, or type a command" and it["chip"][4] == "Super Space"' "placeholder and chip text"
    check bar 'd["focused"] is False and d["active"] is False' "idle: not focused"
}
render 1536 864 bar-focused && check bar-focused 'd["focused"] is True and d["active"] is True and d["ring"] is True' "focused: accent ring, active overlay"
# streamed answer: three text deltas then done (harness feeds the events)
render 1536 864 answer && {
    check answer 'it["answer"][4] == "Done. Design review is now tomorrow at 15:00." and near(it["answer"][0], 560*k, 1) and near(it["answer"][1], 650*k, 2) and near(it["answer"][2], 800*k, 1)' "answer text at (560k, 650k) w 800k"
    check answer 'near(it["rule"][1], 620*k, 1) and near(it["rule"][2], 800*k, 1)' "rule at y 620k"
    check answer 'd["caret"] is False and it["readout"][4].find("tok/s") >= 0' "caret hidden after done, readout shows tok/s"
    check answer 'd["thinking"] is False' "thinking line hidden after done"
    check answer 'near(it["readout"][0] + it["readout"][2], 1536 - 40*k, 2) and near(it["readout"][1], 60*k, 2)' "readout top-right (right 40k, top 60k)"
}
render 1536 864 answer-streaming && check answer-streaming 'd["caret"] is True and it["answer"][4] == "Done. Design review"' "caret visible while streaming"
# consent dialog from a consent.request event
render 1536 864 consent && {
    check consent 'it["consent_kicker"][4] == "ALLOW WRITE NOTE?" and d["pin_visible"] is False' "consent kicker, no PIN"
    check consent 'near(it["consent"][2], 440*k, 1) and near(it["consent"][0] + it["consent"][2]/2, 1536/2, 2)' "dialog 440k wide, centred"
}
render 1536 864 consent-pin && check consent-pin 'd["pin_visible"] is True and it["consent_kicker"][4] == "ALLOW RUN COMMAND?"' "PIN field when required"
for s in bar answer consent; do [ -f "$OUT/$s/$s.png" ] && ok "$s.png written" || bad "$s.png missing"; done

# lock scene (design scene 03 without the camera): mark 176 at (960, 420), greeting 52/500 at y 640,
# passphrase field, "n things since you left", chips at bottom 88 and the "Other ways" line at bottom 56
render 1536 864 lock && {
    check lock 'near(it["mark"][0] + it["mark"][2]/2, 960*k, 1) and near(it["mark"][1] + it["mark"][3]/2, 420*k, 1) and near(it["mark"][2], 176*k, 1)' "mark 176k at (960k, 420k)"
    check lock 'it["greeting"][4] == "Good evening, Maya." and near(it["greeting"][1], 640*k, 2) and near(it["greeting"][0] + it["greeting"][2]/2, 1536/2, 2)' "greeting at y 640k, centred"
    check lock 'it["since"][4] == "3 things since you left"' "since-count line"
    check lock 'near(it["chips"][1] + it["chips"][3], 864 - 88*k, 2) and near(it["other"][1] + it["other"][3], 864 - 56*k, 2)' "chips at bottom 88k, other-ways at bottom 56k"
    check lock 'd["locked"] is True and d["backoff_ms"] == 0 and d["failures"] == 0' "locked, no backoff"
}
render 1536 864 lock-backoff && check lock-backoff 'd["failures"] == 5 and d["backoff_ms"] == 30000 and d["locked"] is True and d["shake"] is True' "5 wrong passphrases: 30 s backoff, still locked"
render 1536 864 lock-pin && check lock-pin 'd["mode"] == "pin" and it["field_placeholder"][4] == "PIN"' "PIN chip switches the field to PIN"
[ -f "$OUT/lock/lock.png" ] && ok "lock.png written" || bad "lock.png missing"

# branch review fixes (2026-10-25): tests that drive the real code paths
render 1536 864 lock-backoff-submit && check lock-backoff-submit 'd["failures"] == 5 and d["backoff_ms"] == 30000 and d["locked"] is True and d["submits"] == 5' "5 wrong submits through LockContent.submit(): 30 s backoff"
render 1536 864 consent-queue && check consent-queue 'd["consent_id"] == "c2" and d["queue_len"] == 0 and d["answered"] == ["c1:false"]' "two consents queue; declining the first shows the second"
render 1536 864 consent-wrong-pin && check consent-wrong-pin 'd["consent_id"] == "c2" and d["consent_message"].find("PIN") >= 0 and d["pin_visible"] is True' "a wrong PIN keeps the dialog open with a message"
render 1536 864 consent-closed && check consent-closed 'd["consent_id"] == "" and d["queue_len"] == 0' "consent.closed removes the dialog"
render 1536 864 consent-dismiss && check consent-dismiss 'd["answered"] == ["c1:false"] and d["consent_id"] == ""' "Esc/outside click declines the pending consent explicitly"
render 1920 1080 rescale && check rescale 'near(k, 0.8, 0.001) and near(it["strip"][3], 44*0.8, 1)' "scale change at runtime re-lays out (1920x1080 -> 1536x864: k 0.8)"
render 1536 864 screens && check screens 'd["panel_edp"] is True and d["panel_hdmi"] is False and d["panel_only_hdmi"] is True' "the presence lives on the laptop panel (or the only screen)"
# slice 2: the greeter scene (no personal data before login; accounts + session chooser)
render 1536 864 greeter && {
    check greeter 'd["users"] == ["maya", "eternity"] and d["sessions"] == ["Eternity", "Eternity Classic"]' "accounts and sessions listed"
    check greeter 'd["since_visible"] is False and d["pin_chip_visible"] is False and it["field_placeholder"][4] == "Passphrase"' "no since-line, no PIN, passphrase field"
    check greeter 'near(it["mark"][0] + it["mark"][2]/2, 960*k, 1) and it["greeting"][4] == "Good evening."' "mark centred, greeting without a name"
    check greeter 'd["selected_user"] == "maya" and d["selected_session"] == "eternity"' "first account and the Eternity session selected"
}
render 1536 864 greeter-fail && check greeter-fail 'd["failures"] == 1 and d["shake"] is True and d["locked"] is True' "a wrong passphrase shakes and stays"
[ -f "$OUT/greeter/greeter.png" ] && ok "greeter.png written" || bad "greeter.png missing"
# slice 2: launcher ring (12 tiles on the 1.35r x r ellipse, r 350 when settled), filter, window ring
render 1536 864 launcher && {
    check launcher 'd["tile_count"] == 12 and all(near(it["tile" + str(i)][2], 64*k, 1) for i in range(12))' "12 tiles of 64k"
    check launcher 'near(it["tile0"][0] + 32*k, 960*k, 2) and near(it["tile0"][1] + 32*k, (540 - 350)*k, 2)' "tile 0 at the top of the ring (angle -90, r 350)"
    check launcher 'near(it["tile3"][0] + 32*k, (960 + 350*1.35)*k, 2) and near(it["tile3"][1] + 32*k, 540*k, 2)' "tile 3 at the right (angle 0)"
    check launcher 'it["filter"][4].startswith("Type to filter") and near(it["filter"][1], 100*k, 2)' "filter line at y 100k"
    check launcher 'it["tile0"][4] == "Files" and d["selected"] == "Files"' "first tile Files, selected"
}
render 1536 864 launcher-filter && check launcher-filter 'd["tile_count"] == 1 and it["tile0"][4] == "Files" and d["selected"] == "Files" and d["query"] == "fil"' "typing fil leaves Files selected"
render 1536 864 launcher-nomatch && check launcher-nomatch 'd["tile_count"] == 0 and it["filter"][4].find("No match") >= 0 and d["launched"] == []' "no match: nothing to launch"
render 1536 864 launcher-page && check launcher-page 'd["tile_count"] == 4 and d["page"] == 1 and d["pages"] == 2 and it["tile0"][4] == "App13"' "16 apps: page 2 shows the rest"
render 1536 864 windowring && check windowring 'd["tile_count"] == 3 and it["tile0"][4] == "Terminal" and d["selected"] == "Terminal"' "window ring lists toplevels"
[ -f "$OUT/launcher/launcher.png" ] && ok "launcher.png written" || bad "launcher.png missing"
# slice 2: notification cards under the strip (300k wide, top-right), a storm holds the rest, the OSD
render 1536 864 notify && {
    check notify 'd["cards_visible"] == 1 and near(it["card0"][2], 300*k, 1) and near(it["card0"][0] + it["card0"][2], 1536 - 28*k, 2) and near(it["card0"][1], 44*k + 12*k, 2)' "one card 300k at top-right under the strip"
    check notify 'it["card0"][4] == "Mail" and d["held"] == 0' "card shows the app as kicker; nothing held"
}
render 1536 864 notify-storm && check notify-storm 'd["cards_visible"] == 3 and d["held"] == 47 and d["queued"] == 47' "50 notifications: three cards, 47 held"
render 1536 864 notify-dnd && check notify-dnd 'd["cards_visible"] == 0 and d["held"] == 2' "do not disturb: nothing shown, two held"
render 1536 864 osd && check osd 'near(it["osd"][2], 240*k, 1) and near(it["osd"][1], 900*k, 2) and near(it["osd_fill"][2], 240*k*0.65, 2) and it["osd_label"][4] == "Volume 65%"' "OSD bar 240k at y 900k, 65 % fill"
[ -f "$OUT/notify-storm/notify-storm.png" ] && ok "notify-storm.png written" || bad "notify-storm.png missing"
# slice 2: Settings window (nav + the design's 700-wide column at x 1000 / y 200 inside a 1920 reference)
render 1536 864 settings-eternity && {
    check settings-eternity 'it["kicker"][4] == "SETTINGS \u00b7 ETERNITY" and it["title"][4] == "How she shows up" and near(it["column"][2], 700*k, 2)' "kicker, title, 700k column"
    check settings-eternity 'd["rows"] >= 5 and near(it["row0"][3], it["row1"][3], 2) and near(it["slider"][2], 240*k, 1)' "rows of equal height; verbosity slider 240k"
    check settings-eternity 'd["pages"] == ["Eternity", "Assistant", "Devices", "Network", "Sound", "Power", "Appearance", "Keys"] and d["page"] == "Eternity"' "eight pages, Eternity first"
    check settings-eternity 'd["telemetry_enabled"] is False and d["telemetry_on"] is False' "telemetry switch off and disabled"
}
render 1536 864 settings-offline && check settings-offline 'd["controls_enabled"] is False and it["offline"][4].find("not running") >= 0' "daemon down: controls disabled with a line"
render 1536 864 settings-appearance && check settings-appearance 'd["page"] == "Appearance" and d["presets"] == ["Nocturne", "Nocturne Light", "Mono", "High contrast", "Quiet"] and d["scales"] == [1, 1.25, 1.5]' "appearance: presets and scales"
render 1536 864 settings-assistant && check settings-assistant 'd["page"] == "Assistant" and d["providers"] >= 3 and d["allow_tools"] >= 8' "assistant: providers and allow-list"
[ -f "$OUT/settings-eternity/settings-eternity.png" ] && ok "settings-eternity.png written" || bad "settings-eternity.png missing"
render 1536 864 latency && check latency 'd["lat_count"] == 20 and near(d["lat_p95"], 19, 1) and d["lat_file"].endswith("/eternity/latency.json")' "latency samples: p95 of 20 samples"

if [ $fail = 0 ]; then echo "SHELL RENDER: PASS"; else echo "SHELL RENDER: FAIL (artifacts in $OUT)"; exit 1; fi
