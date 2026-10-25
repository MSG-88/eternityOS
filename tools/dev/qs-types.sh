#!/bin/bash
# Quickshell QML type lookup (dev helper): bash qs-types.sh Type [Type...]  -> file + property/method names
Q=/usr/lib/x86_64-linux-gnu/qt6/qml/Quickshell
for t in "$@"; do
  f=$(grep -rl --include=*.qmltypes "name: \"$t\"" $Q 2>/dev/null | head -1)
  [ -z "$f" ] && { echo "== $t: NOT FOUND"; continue; }
  echo "== $t (${f#$Q/}) exports: $(grep -A3 "name: \"$t\"" "$f" | grep -oE 'exports: \[[^]]*\]' | head -1 | cut -c1-120)"
  python3 - "$f" "$t" <<'PY'
import re, sys
s = open(sys.argv[1]).read()
m = re.search(r'\n    Component \{(?:(?!\n    Component \{).)*?name: "%s".*?\n    \}' % re.escape(sys.argv[2]), s, re.S)
if not m: sys.exit()
blk = m.group(0)
props = re.findall(r'Property \{ name: "([A-Za-z]+)"', blk)
meths = re.findall(r'Method \{ name: "([A-Za-z]+)"', blk) + re.findall(r'Method \{\n\s+name: "([A-Za-z]+)"', blk)
sigs = re.findall(r'Signal \{ name: "([A-Za-z]+)"', blk) + re.findall(r'Signal \{\n\s+name: "([A-Za-z]+)"', blk)
enums = re.findall(r'Enum \{\n\s+name: "([A-Za-z]+)"\n\s+values: \[([^\]]*)\]', blk)
print("   props:", " ".join(sorted(set(props))))
if meths: print("   methods:", " ".join(sorted(set(meths))))
if sigs: print("   signals:", " ".join(sorted(set(sigs))))
for n, v in enums: print("   enum", n, ":", v.replace('"', '').replace('\n', ' ')[:200])
PY
done
