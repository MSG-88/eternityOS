#!/bin/bash
# Overnight progress page for the owner: `tools/dev/progress.sh "message"` appends a timestamped
# line to tests/out/live/progress.log and regenerates tests/out/live/index.html (self-contained,
# reloads every 30 s, shows the latest test-VM screenshot from live-loop.sh when one exists).
# `tools/dev/progress.sh --phase "name" "state"` records the state of a work phase (todo/doing/done/blocked).
cd "$(dirname "$0")/../.." || exit 1
D=tests/out/live; mkdir -p "$D"; LOG=$D/progress.log; PH=$D/phases.tsv
ts() { TZ=Asia/Kolkata date '+%Y-%m-%d %H:%M IST'; }
if [ "${1:-}" = --phase ]; then
    name=$2; state=$3; touch "$PH"
    grep -vF "	$name	" "$PH" > "$PH.tmp" 2>/dev/null; printf '%s\t%s\t%s\n' "$(ts)" "$name" "$state" >> "$PH.tmp"; mv "$PH.tmp" "$PH"
elif [ -n "${1:-}" ]; then
    printf '%s  %s\n' "$(ts)" "$1" >> "$LOG"
fi
esc() { sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'; }
latest=$(tail -1 "$LOG" 2>/dev/null | esc)
{
cat <<HTML
<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Eternity 08 overnight</title>
<meta http-equiv="refresh" content="30"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--bg:#161826;--surface:#232532;--text:#e9e9ed;--muted:#9397ab;--accent:#9184d9;--ok:#7fd1a8;--warn:#e8c07a;--bad:#e88a8a;--line:rgba(233,233,237,.16)}
body{margin:0;background:radial-gradient(1200px 600px at 50% -10%,#1b1e31,#121421);color:var(--text);font:15px/1.55 Inter,system-ui,sans-serif;padding:20px 16px;min-height:100vh}
h1{font:500 22px/1.2 Inter,system-ui;margin:0 0 4px;letter-spacing:.01em}h1 b{color:var(--accent);font-weight:500}
.sub{color:var(--muted);margin-bottom:18px;font-size:13px}
.grid{display:grid;grid-template-columns:1fr;gap:16px;max-width:1400px}@media(min-width:1000px){.grid{grid-template-columns:3fr 2fr}}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px 18px}
.k{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin-bottom:8px}
.now{font-size:17px;margin-bottom:14px;padding:12px 14px;border-radius:8px;background:rgba(145,132,217,.12);border:1px solid rgba(145,132,217,.35)}
ol{list-style:none;margin:0;padding:0}ol li{padding:6px 0;border-bottom:1px solid var(--line);display:grid;grid-template-columns:150px 1fr;gap:12px}ol li:last-child{border:0}
ol li time{color:var(--muted);font-variant-numeric:tabular-nums;font-size:13px}
table{width:100%;border-collapse:collapse}td{padding:6px 4px;border-bottom:1px solid var(--line);vertical-align:top}td:last-child{text-align:right;white-space:nowrap}
.s-done{color:var(--ok)}.s-doing{color:var(--accent)}.s-todo{color:var(--muted)}.s-blocked{color:var(--bad)}.s-partial{color:var(--warn)}
img{max-width:100%;border:1px solid var(--line);border-radius:8px;display:block;background:#000}
.foot{color:var(--muted);font-size:12px;margin-top:18px}
</style></head><body>
<h1>Eternity <b>08</b> · overnight session</h1>
<div class="sub">Page regenerated $(ts) · reloads every 30 s · file: tests/out/live/index.html</div>
<div class="grid"><div>
<div class="card"><div class="k">Now</div><div class="now">${latest:-starting}</div>
<div class="k">Timeline (newest first)</div><ol>
HTML
tac "$LOG" 2>/dev/null | esc | sed -E 's/^([0-9-]+ [0-9:]+ IST)  (.*)$/<li><time>\1<\/time><span>\2<\/span><\/li>/'
cat <<HTML
</ol></div></div><div>
<div class="card"><div class="k">Work phases</div><table>
HTML
if [ -s "$PH" ]; then sort -t$'\t' -k2 "$PH" | esc | awk -F'\t' '{printf "<tr><td>%s</td><td class=\"s-%s\">%s<br><small style=\"color:#9397ab\">%s</small></td></tr>\n",$2,tolower($3),$3,$1}'; else echo '<tr><td colspan=2 class="s-todo">no phases recorded yet</td></tr>'; fi
cat <<HTML
</table></div>
<div class="card" style="margin-top:16px"><div class="k">Test VM, live</div>
<img src="../install/live.png?$(date +%s)" alt="no VM screenshot yet" onerror="this.alt='no VM running right now'">
<div class="foot">$(cat tests/out/install/live.txt 2>/dev/null | esc) · screenshots refresh every 30 s while a QEMU test runs</div></div>
</div></div></body></html>
HTML
} > "$D/index.html.tmp" && mv -f "$D/index.html.tmp" "$D/index.html"
