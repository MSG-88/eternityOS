#!/bin/bash
# Download the bundled models listed in ai/models.manifest into the image tree,
# verify SHA-256, fetch licence texts, and write models.json + SHA256SUMS + role symlinks.
# Idempotent: existing files with matching checksums are kept.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
MANIFEST=$ROOT/ai/models.manifest
DEST=${ETERNITY_MODELS_DEST:-$ROOT/config/includes.chroot/opt/eternity/models}
mkdir -p "$DEST"

dl() { # url out
    curl -L --fail --retry 5 --retry-delay 5 -C - --progress-bar -o "$2" "$1"
}

json_entries=()
: > "$DEST/SHA256SUMS"
while IFS='|' read -r role name file url sha licence licence_url; do
    case "$role" in ''|\#*) continue ;; esac
    path=$DEST/$file
    if [ -f "$path" ] && [ "$sha" != "-" ] && echo "$sha  $path" | sha256sum --quiet -c - 2>/dev/null; then
        echo "ok      $file"
    else
        echo "fetch   $file"
        dl "$url" "$path"
        got=$(sha256sum "$path" | cut -d' ' -f1)
        if [ "$sha" = "-" ]; then
            # record the checksum into the manifest for next time
            sed -i "s#^$role|$name|$file|$url|-|#$role|$name|$file|$url|$got|#" "$MANIFEST"
            sha=$got
        elif [ "$got" != "$sha" ]; then
            echo "checksum mismatch for $file: $got != $sha" >&2; exit 1
        fi
    fi
    [ -s "$path.LICENSE" ] || dl "$licence_url" "$path.LICENSE"
    ln -sfn "$file" "$DEST/$role.gguf"
    echo "$(sha256sum "$path" | cut -d' ' -f1)  $file" >> "$DEST/SHA256SUMS"
    size=$(stat -c %s "$path")
    json_entries+=("  \"$role\": {\"name\": \"$name\", \"file\": \"$file\", \"size\": $size, \"licence\": \"$licence\", \"source\": \"$url\"}")
done < "$MANIFEST"

{
    echo "{"
    IFS=,; echo "${json_entries[*]}" | sed 's/},/},\n/g'
    echo "}"
} > "$DEST/models.json"
python3 -c "import json,sys; json.load(open('$DEST/models.json'))" || { echo "models.json invalid" >&2; exit 1; }
echo "models ready in $DEST:"; ls -la "$DEST"
