#!/bin/bash
# Host-side test for the branding renderer (runs on the build host / WSL, no VM).
# Renders the assets, then checks that every file the image expects exists with the right
# geometry and that the palette is Nocturne (violet accent on #161826), not the old cyan.
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT" || exit 1
fail=0
ok()   { echo "PASS $1"; }
bad()  { echo "FAIL $1"; fail=1; }

python3 branding/render.py >/dev/null || { echo "FAIL render.py exited $?"; exit 1; }

E=config/includes.chroot/usr/share/eternity
P=config/includes.chroot/usr/share/plymouth/themes/eternity
for f in logo.svg logo-64.png logo-128.png logo-256.png logo-512.png mark-176.png mark-512.png wordmark.png wordmark-sub.png lockup.png \
         wallpaper-1920x1080.png wallpaper-2560x1440.png wallpaper-3840x2160.png greeter-1920x1080.png; do
    [ -s "$E/$f" ] && ok "$f exists" || bad "$f missing"
done
[ "$(ls "$P"/ring-draw-*.png 2>/dev/null | wc -l)" = 24 ] && ok "24 ring-draw frames" || bad "ring-draw frames"
[ "$(ls "$P"/ring-loop-*.png 2>/dev/null | wc -l)" = 24 ] && ok "24 ring-loop frames" || bad "ring-loop frames"
for f in wordmark.png wordmark-plain.png rule.png rule-accent.png eternity.script eternity.plymouth; do
    [ -s "$P/$f" ] && ok "plymouth $f" || bad "plymouth $f missing"
done
for f in config/bootloaders/grub-pc/themes/eternity/background.png config/includes.chroot/usr/share/grub/themes/eternity/background.png \
         config/includes.chroot/usr/share/grub/themes/eternity/theme.txt config/includes.chroot/etc/calamares/branding/eternity/welcome.png \
         config/includes.chroot/usr/share/fonts/truetype/michroma/Michroma-Regular.ttf config/includes.chroot/usr/share/pixmaps/eternity.png \
         config/includes.chroot/usr/share/icons/hicolor/256x256/apps/eternity.png; do
    [ -s "$f" ] && ok "$(basename "$(dirname "$f")")/$(basename "$f")" || bad "$f missing"
done

python3 - "$E" "$P" <<'PY' || fail=1
import sys
from PIL import Image
E, P = sys.argv[1], sys.argv[2]
def px(img):
    return list(img.get_flattened_data()) if hasattr(img, "get_flattened_data") else list(img.getdata())
rc = 0
def check(cond, msg):
    global rc
    print(("PASS " if cond else "FAIL ") + msg); rc |= (not cond)
for name, w, h in (("wallpaper-1920x1080.png", 1920, 1080), ("wallpaper-2560x1440.png", 2560, 1440),
                   ("wallpaper-3840x2160.png", 3840, 2160), ("greeter-1920x1080.png", 1920, 1080)):
    im = Image.open(f"{E}/{name}")
    check(im.size == (w, h), f"{name} is {w}x{h}")
im = Image.open(f"{E}/wallpaper-1920x1080.png").convert("RGB")
corner = im.getpixel((20, 20)); centre = im.getpixel((960, 497))
check(abs(corner[0] - 0x12) < 8 and abs(corner[2] - 0x21) < 10, f"vignette edge is Nocturne navy {corner}")
check(centre[2] > centre[0] and centre[2] > 150, f"the mark at the centre is violet-white {centre}")
cols = px(im.resize((192, 108)))
cyan = sum(1 for r, g, b in cols if b > 180 and g > 150 and r < 80)
check(cyan == 0, "no old cyan accent left in the wallpaper")
for s in (64, 128, 256, 512):
    im = Image.open(f"{E}/logo-{s}.png")
    check(im.size == (s, s) and im.mode == "RGBA", f"logo-{s}.png is {s}x{s} RGBA")
    check(im.getpixel((0, 0))[3] == 0, f"logo-{s}.png has rounded transparent corners")
f0 = Image.open(f"{P}/ring-draw-00.png"); f23 = Image.open(f"{P}/ring-draw-23.png")
a0 = sum(1 for p in px(f0) if p[3] > 0); a23 = sum(1 for p in px(f23) if p[3] > 0)
check(a23 > a0 * 3, f"ring draws in across the frames ({a0} -> {a23} opaque px)")
check(f0.size == f23.size == Image.open(f"{P}/ring-loop-00.png").size, "all Plymouth frames share one size")
g = Image.open("config/bootloaders/grub-pc/themes/eternity/background.png")
check(g.size == (1920, 1080), "GRUB background is 1920x1080")
sys.exit(rc)
PY

grep -q '#9184d9' config/bootloaders/grub-pc/themes/eternity/theme.txt && ok "GRUB theme uses the accent" || bad "GRUB theme palette"
grep -qi '19d3f5' config/bootloaders/grub-pc/themes/eternity/theme.txt config/includes.chroot/etc/xdg/xfce4/terminal/terminalrc \
    config/includes.chroot/etc/calamares/branding/eternity/branding.desc && bad "old cyan still referenced" || ok "no old cyan in theme, terminal, Calamares"
cmp -s config/bootloaders/grub-pc/themes/eternity/theme.txt config/includes.chroot/usr/share/grub/themes/eternity/theme.txt && ok "GRUB theme copies identical" || bad "GRUB theme copies differ"

[ $fail = 0 ] && echo "BRANDING: PASS" || { echo "BRANDING: FAIL"; exit 1; }
