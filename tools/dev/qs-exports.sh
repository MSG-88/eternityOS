#!/bin/bash
# Quickshell QML lookup by *export* name (dev helper): bash qs-exports.sh Name [Name...]
Q=/usr/lib/x86_64-linux-gnu/qt6/qml/Quickshell
[ "$1" = "--list" ] && { grep -rhoE --include=*.qmltypes 'exports: \["[^"]+"' $Q | sed 's/exports: \["//; s/"$//' | sort -u | tr '\n' ' '; echo; exit 0; }
for t in "$@"; do
python3 - "$Q" "$t" <<'PY'
import re, sys, glob
Q, want = sys.argv[1], sys.argv[2]
for f in sorted(glob.glob(Q + "/**/*.qmltypes", recursive=True)):
    s = open(f).read()
    for m in re.finditer(r'\n    Component \{\n(.*?)\n    \}', s, re.S):
        blk = m.group(1)
        ex = re.search(r'exports: \[([^\]]*)\]', blk)
        if not ex or ('/' + want + ' ') not in ex.group(1).replace('"', '') + ' ':
            continue
        name = re.search(r'name: "([^"]+)"', blk).group(1)
        print(f"== {want} -> C++ {name} ({f[len(Q)+1:]}) exports {ex.group(1).replace(chr(34), '')[:90]}")
        print("   props:", " ".join(sorted(set(re.findall(r'Property \{\s*name: "([A-Za-z]+)"', blk)))))
        ms = sorted(set(re.findall(r'Method \{\s*name: "([A-Za-z]+)"', blk)))
        if ms: print("   methods:", " ".join(ms))
        for n, v in re.findall(r'Enum \{\s*name: "([A-Za-z]+)"\s*values: \[([^\]]*)\]', blk):
            print("   enum", n, ":", v.replace('"', '').replace('\n', ' ')[:160])
PY
done
