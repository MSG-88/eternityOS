#!/usr/bin/env python3
"""Render Eternity 08 branding assets into config/includes.chroot.

Produces (under config/includes.chroot/usr/share/eternity):
  logo.svg, logo-{64,128,256,512}.png (square icon: ring + 08),
  wordmark.png (wide wordmark, transparent),
  wallpaper-{1920x1080,2560x1440,3840x2160}.png, greeter-1920x1080.png
and copies the square icon to the hicolor icon theme and /usr/share/pixmaps.

Idempotent; run by build.sh on the build host (needs cairosvg, Pillow, fonts-inter).
"""
import io
import os
import shutil
import sys

import cairosvg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROOT = os.path.join(ROOT, "config", "includes.chroot")
OUT = os.path.join(CHROOT, "usr", "share", "eternity")
LOGO_SVG = os.path.join(ROOT, "branding", "logo.svg")

BACKGROUND = (0x07, 0x0B, 0x14)
PANEL = (0x0D, 0x13, 0x20)
ACCENT = (0x19, 0xD3, 0xF5)
ACCENT_DIM = (0x0E, 0x8F, 0xA8)
TEXT = (0xE6, 0xF1, 0xFF)
MUTED = (0x7C, 0x8B, 0xA1)

ICON_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <rect x="0" y="0" width="512" height="512" rx="112" fill="#0D1320"/>
  <circle cx="256" cy="256" r="178" fill="none" stroke="#0E8FA8" stroke-width="12"/>
  <circle cx="256" cy="256" r="204" fill="none" stroke="#19D3F5" stroke-width="3" opacity="0.35"/>
  <text x="256" y="328" text-anchor="middle" font-family="Inter, 'Inter Display', sans-serif" font-weight="800" font-size="210" fill="#19D3F5">08</text>
</svg>
"""

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/inter/Inter-Medium.otf",
    "/usr/share/fonts/truetype/inter/Inter-Medium.ttf",
    "/usr/share/fonts/opentype/inter/Inter-Regular.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def svg_to_png(svg_text, width, height):
    data = cairosvg.svg2png(bytestring=svg_text.encode(), output_width=width, output_height=height)
    return Image.open(io.BytesIO(data)).convert("RGBA")


def wordmark(width):
    with open(LOGO_SVG, encoding="utf-8") as f:
        svg = f.read()
    return svg_to_png(svg, width, width // 4)


def gradient_background(w, h):
    """Dark navy base with a soft cyan glow in the lower right."""
    img = Image.new("RGB", (w, h), BACKGROUND)
    # vertical gradient background -> panel
    top = Image.new("RGB", (1, h), BACKGROUND)
    px = top.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = tuple(int(BACKGROUND[i] * (1 - t) + PANEL[i] * t) for i in range(3))
    img.paste(top.resize((w, h)))
    # radial glow
    glow = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(glow)
    cx, cy = int(w * 0.82), int(h * 0.88)
    r = int(min(w, h) * 0.55)
    for i in range(40, 0, -1):
        rr = int(r * i / 40)
        a = int(28 * (1 - i / 40) ** 1.2)
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(a, int(a * 2.2), int(a * 2.6)))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=max(8, w // 60)))
    # additive blend of glow
    from PIL import ImageChops
    img = ImageChops.add(img, glow)
    # subtle ring motif, lower right
    ring = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    R = int(min(w, h) * 0.42)
    rd.ellipse((cx - R, cy - R, cx + R, cy + R), outline=ACCENT_DIM + (60,), width=max(2, w // 900))
    img = Image.alpha_composite(img.convert("RGBA"), ring)
    return img


def wallpaper(w, h, path, hint=None, centered=False):
    img = gradient_background(w, h)
    if centered:
        wm = wordmark(int(w * 0.46))
        x = (w - wm.width) // 2
        y = int(h * 0.36) - wm.height // 2
    else:
        wm = wordmark(int(w * 0.26))
        x = w - wm.width - int(w * 0.04)
        y = h - wm.height - int(h * 0.05)
    img.alpha_composite(wm, (x, y))
    if hint:
        d = ImageDraw.Draw(img)
        f = font(max(16, h // 48))
        tw = d.textlength(hint, font=f)
        d.text(((w - tw) / 2, int(h * 0.90)), hint, font=f, fill=MUTED)
    img.convert("RGB").save(path, optimize=True)


def text_card(w, h, path, title, subtitle, wordmark_frac=0.5):
    """Dark card with the wordmark on top and two lines of text (Calamares slides)."""
    img = gradient_background(w, h)
    wm = wordmark(int(w * wordmark_frac))
    img.alpha_composite(wm, ((w - wm.width) // 2, int(h * 0.16)))
    d = ImageDraw.Draw(img)
    f1, f2 = font(max(18, h // 14)), font(max(14, h // 24))
    for txt, fnt, y, col in ((title, f1, 0.60, TEXT), (subtitle, f2, 0.74, MUTED)):
        tw = d.textlength(txt, font=fnt)
        d.text(((w - tw) / 2, int(h * y)), txt, font=fnt, fill=col)
    img.convert("RGB").save(path, optimize=True)


def boot_assets():
    """GRUB background + theme copy, Plymouth images, Calamares branding images."""
    grub_iso = os.path.join(ROOT, "config", "bootloaders", "grub-pc", "themes", "eternity")
    grub_sys = os.path.join(CHROOT, "usr", "share", "grub", "themes", "eternity")
    for d in (grub_iso, grub_sys):
        os.makedirs(d, exist_ok=True)
    bg = gradient_background(1920, 1080)
    wm = wordmark(int(1920 * 0.40))
    bg.alpha_composite(wm, ((1920 - wm.width) // 2, int(1080 * 0.10)))
    for d in (grub_iso, grub_sys):
        bg.convert("RGB").save(os.path.join(d, "background.png"), optimize=True)
    shutil.copyfile(os.path.join(grub_iso, "theme.txt"), os.path.join(grub_sys, "theme.txt"))

    ply = os.path.join(CHROOT, "usr", "share", "plymouth", "themes", "eternity")
    os.makedirs(ply, exist_ok=True)
    wordmark(720).save(os.path.join(ply, "logo.png"))
    Image.new("RGBA", (520, 6), PANEL + (255,)).save(os.path.join(ply, "progress-bg.png"))
    Image.new("RGBA", (520, 6), ACCENT + (255,)).save(os.path.join(ply, "progress-fg.png"))

    cal = os.path.join(CHROOT, "etc", "calamares", "branding", "eternity")
    os.makedirs(cal, exist_ok=True)
    svg_to_png(ICON_SVG, 128, 128).save(os.path.join(cal, "logo.png"))
    text_card(640, 360, os.path.join(cal, "welcome.png"), "Welcome", "A lightweight Linux with local AI built in", 0.6)
    text_card(760, 428, os.path.join(cal, "slide-1.png"), "Local AI, no cloud required",
              "Qwen models run offline with llama.cpp — try eternity-chat after install")
    text_card(760, 428, os.path.join(cal, "slide-2.png"), "Python ML stack ready",
              "PyTorch, Transformers, scikit-learn, pandas and Jupyter in /opt/eternity/venv")


def main():
    os.makedirs(OUT, exist_ok=True)
    boot_assets()
    shutil.copyfile(LOGO_SVG, os.path.join(OUT, "logo.svg"))
    wordmark(1600).save(os.path.join(OUT, "wordmark.png"))
    for size in (64, 128, 256, 512):
        svg_to_png(ICON_SVG, size, size).save(os.path.join(OUT, f"logo-{size}.png"))
    for w, h in ((1920, 1080), (2560, 1440), (3840, 2160)):
        wallpaper(w, h, os.path.join(OUT, f"wallpaper-{w}x{h}.png"))
    wallpaper(1920, 1080, os.path.join(OUT, "greeter-1920x1080.png"),
              hint="Live session  ·  user: eternity   password: eternity", centered=True)
    # icon theme + pixmaps
    for size in (64, 128, 256):
        dst = os.path.join(CHROOT, "usr", "share", "icons", "hicolor", f"{size}x{size}", "apps")
        os.makedirs(dst, exist_ok=True)
        shutil.copyfile(os.path.join(OUT, f"logo-{size}.png"), os.path.join(dst, "eternity.png"))
    pix = os.path.join(CHROOT, "usr", "share", "pixmaps")
    os.makedirs(pix, exist_ok=True)
    shutil.copyfile(os.path.join(OUT, "logo-256.png"), os.path.join(pix, "eternity.png"))
    print("rendered branding assets to", OUT)


if __name__ == "__main__":
    sys.exit(main())
