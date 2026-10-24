#!/bin/bash
# Build GRUB .pf2 fonts for the Eternity 08 GRUB theme (ISO menu and installed system).
# Needs grub-mkfont, fonts-inter and fonts-jetbrains-mono on the build host.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
DESTS=("$ROOT/config/bootloaders/grub-pc/themes/eternity" "$ROOT/config/includes.chroot/usr/share/grub/themes/eternity")
command -v grub-mkfont >/dev/null || { echo "grub-mkfont missing" >&2; exit 1; }

find_font() { find /usr/share/fonts -iname "$1" | head -1; }
INTER_MED=$(find_font 'Inter-Medium.*')
INTER_BOLD=$(find_font 'Inter-Bold.*')
MONO=$(find_font 'JetBrainsMono-Regular.ttf')
[ -n "$INTER_MED" ] && [ -n "$INTER_BOLD" ] && [ -n "$MONO" ] || { echo "fonts not found (inter/jetbrains)" >&2; exit 1; }

tmp=$(mktemp -d)
grub-mkfont -s 18 -o "$tmp/inter-18.pf2" "$INTER_MED" 2>/dev/null
grub-mkfont -s 28 -o "$tmp/inter-bold-28.pf2" "$INTER_BOLD" 2>/dev/null
grub-mkfont -s 16 -o "$tmp/mono-16.pf2" "$MONO" 2>/dev/null
for d in "${DESTS[@]}"; do mkdir -p "$d"; cp "$tmp"/*.pf2 "$d/"; done
rm -rf "$tmp"
echo "GRUB fonts written to: ${DESTS[*]}"
