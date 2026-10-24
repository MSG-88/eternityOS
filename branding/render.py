#!/usr/bin/env python3
"""Render Eternity 08 branding assets into config/includes.chroot.

Design source: docs/design/README.md (Claude Design capture, "Nocturne" tokens, logo 3b
"fading ring" with a Möbius ∞, Michroma wordmark). Produces, under
config/includes.chroot/usr/share/eternity:
  logo.svg, logo-{64,128,256,512}.png (icon plate + mark), mark-{176,512}.png (mark alone,
  transparent), wordmark.png, wordmark-sub.png, lockup.png (mark + wordmark + sub-line),
  wallpaper-{1920x1080,2560x1440,3840x2160}.png, greeter-1920x1080.png
plus the GRUB background, the Plymouth theme images (48 ring frames, wordmark, hairline),
the Calamares branding images, the hicolor icons, /usr/share/pixmaps/eternity.png and the
Michroma font under /usr/share/fonts/truetype/michroma.

Idempotent; run by build.sh on the build host (needs cairosvg, Pillow, fonts-inter).
"""
import io
import math
import os
import shutil
import sys

import cairosvg
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROOT = os.path.join(ROOT, "config", "includes.chroot")
OUT = os.path.join(CHROOT, "usr", "share", "eternity")
MICHROMA = os.path.join(ROOT, "branding", "fonts", "Michroma-Regular.ttf")

# Nocturne tokens (branding/colors.md)
BG, BG_TOP, BG_EDGE = "#161826", "#1b1e31", "#121421"
SURFACE, TEXT, ACCENT = "#232532", "#e9e9ed", "#9184d9"
A100, A300, A400, A600, A700, A800, A900 = "#f5f4ff", "#d2cefd", "#b5abfc", "#796cbf", "#5d5294", "#423a6a", "#2b2741"
N400, N500, N600, N700, N800, N900 = "#b2b6ca", "#9397ab", "#75798c", "#595d6c", "#3f424d", "#292b31"


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(c1, c2, p):
    """p of c1 plus (1-p) of c2, in sRGB (stands in for the design's color-mix in oklch)."""
    a, b = rgb(c1), rgb(c2)
    return "#%02x%02x%02x" % tuple(round(a[i] * p + b[i] * (1 - p)) for i in range(3))


# ----------------------------------------------------------------------------- the mark
MOB_N = 150


def mob_point(t):
    d = 1 + math.sin(t) ** 2
    return 70 + 62 * math.sin(t) * math.cos(t) / d, 70 + 46 * math.cos(t) / d


MOB = [(i / MOB_N * 2 * math.pi,) + mob_point(i / MOB_N * 2 * math.pi) for i in range(MOB_N + 1)]


def mark_svg(draw=1.0, phase=0.0, ring=N400, point=True, light_t=0.0):
    """The 3b mark as SVG (viewBox 0 0 140 140). draw: 0..1 how much of the ring and ribbon
    is drawn; phase: shading rotation along the loop (radians); light_t: light point 0..1."""
    quads = []
    lim = int(draw * MOB_N)
    for i in range(lim):
        t0, x0, y0 = MOB[i]
        t1, x1, y1 = MOB[i + 1]
        nx, ny = -(y1 - y0), x1 - x0
        nl = math.hypot(nx, ny) or 1
        w0 = 7.5 * abs(math.cos(t0)) ** 0.75
        w1 = 7.5 * abs(math.cos(t1)) ** 0.75
        ax, ay = x0 + nx / nl * w0, y0 + ny / nl * w0
        bx, by = x1 + nx / nl * w1, y1 + ny / nl * w1
        cx, cy = x1 - nx / nl * w1, y1 - ny / nl * w1
        dx, dy = x0 - nx / nl * w0, y0 - ny / nl * w0
        sh = 0.5 + 0.5 * math.sin(t0 * 2 + phase)
        lit = 0.5 + 0.5 * math.cos(t0 + phase)
        p = (45 + 55 * (0.55 * sh + 0.45 * lit)) / 100
        col = mix(A100, A600, p)
        quads.append(
            f'<polygon points="{ax:.2f},{ay:.2f} {bx:.2f},{by:.2f} {cx:.2f},{cy:.2f} {dx:.2f},{dy:.2f}" '
            f'fill="{col}" stroke="{col}" stroke-width="0.6"/>')
    k = MOB[int(light_t % 1 * MOB_N)]
    dot = (f'<circle cx="{k[1]:.2f}" cy="{k[2]:.2f}" r="2.2" fill="{A100}" opacity="0.9"/>'
           if point and draw >= 1 else "")
    dash = 402
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 140 140">
  <defs>
    <linearGradient id="ringfade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{ring}" stop-opacity="0"/>
      <stop offset="0.3" stop-color="{ring}" stop-opacity="1"/>
      <stop offset="0.7" stop-color="{ring}" stop-opacity="1"/>
      <stop offset="1" stop-color="{ring}" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <circle cx="70" cy="70" r="64" fill="none" stroke="url(#ringfade)" stroke-width="2.2"
          stroke-dasharray="{dash}" stroke-dashoffset="{dash * (1 - draw):.1f}" transform="rotate(-90 70 70)"/>
  <g>{''.join(quads)}</g>
  {dot}
</svg>
'''


def svg_to_png(svg_text, width, height):
    data = cairosvg.svg2png(bytestring=svg_text.encode(), output_width=width, output_height=height)
    return Image.open(io.BytesIO(data)).convert("RGBA")


def mark(size, draw=1.0, phase=0.0, glow=1.0, ring=N400, light_t=0.0):
    """Mark rendered at `size` px with a violet glow (the design's drop-shadow), on a canvas
    enlarged by the glow margin so nothing is clipped."""
    margin = int(size * 0.18) if glow else 0
    canvas = size + 2 * margin
    sharp = svg_to_png(mark_svg(draw, phase, ring, True, light_t), size, size)
    img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    if glow:
        alpha = sharp.split()[3]
        tint = Image.new("RGBA", sharp.size, rgb(ACCENT) + (0,))
        tint.putalpha(alpha.point(lambda a: int(a * 0.75 * glow)))
        halo = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
        halo.alpha_composite(tint, (margin, margin))
        halo = halo.filter(ImageFilter.GaussianBlur(radius=max(2, size * 0.045 * glow)))
        img.alpha_composite(halo)
    img.alpha_composite(sharp, (margin, margin))
    return img


# ------------------------------------------------------------------------- the wordmark
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/inter/Inter-Regular.otf",
    "/usr/share/fonts/truetype/inter/Inter-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
FONT_MEDIUM = [
    "/usr/share/fonts/opentype/inter/Inter-Medium.otf",
    "/usr/share/fonts/truetype/inter/Inter-Medium.ttf",
] + FONT_CANDIDATES


def font(size, candidates=FONT_CANDIDATES):
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def michroma(size):
    if os.path.exists(MICHROMA):
        return ImageFont.truetype(MICHROMA, size)
    return font(size, FONT_MEDIUM)


def tracked_text(text, fnt, color, tracking_px):
    """Text drawn glyph by glyph with letter-spacing, returned as a tight RGBA image."""
    widths = [fnt.getlength(ch) for ch in text]
    asc, desc = fnt.getmetrics()
    w = int(sum(widths) + tracking_px * (len(text) - 1)) + 4
    img = Image.new("RGBA", (w, asc + desc + 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 2.0
    for ch, cw in zip(text, widths):
        d.text((x, 1), ch, font=fnt, fill=color)
        x += cw + tracking_px
    return img


def wordmark(size, color=TEXT, tracking=0.34, sub=False):
    """'E' as three bars + TERNITY in Michroma, optionally the PERSONAL OS · 08 sub-line."""
    fnt = michroma(size)
    letters = tracked_text("TERNITY", fnt, color, size * tracking)
    # cap height of the face, measured on a T, so the bars match the letters exactly
    bbox = fnt.getbbox("T")
    cap_top, cap_bottom = bbox[1] + 1, bbox[3] + 1
    cap = cap_bottom - cap_top
    stem = max(1, round(size * 0.1))
    ew = round(size * 0.74)
    gap = round(size * tracking)
    w = ew + gap + letters.width
    img = Image.new("RGBA", (w, letters.height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in (cap_top + stem / 2, cap_top + cap / 2, cap_bottom - stem / 2):
        d.rectangle((0, y - stem / 2, ew, y + stem / 2), fill=color)
    img.alpha_composite(letters, (ew + gap, 0))
    img = img.crop(img.getbbox())
    if not sub:
        return img
    subline = tracked_text("PERSONAL OS · 08", michroma(max(8, round(size * 0.42))), N500, size * 0.42 * 0.3)
    subline = subline.crop(subline.getbbox())
    out = Image.new("RGBA", (max(img.width, subline.width), img.height + round(size * 0.55) + subline.height), (0, 0, 0, 0))
    out.alpha_composite(img, ((out.width - img.width) // 2, 0))
    out.alpha_composite(subline, ((out.width - subline.width) // 2, img.height + round(size * 0.55)))
    return out


def lockup(mark_px, word_px):
    """Mark above wordmark + sub-line, as one transparent image."""
    m = mark(mark_px)
    w = wordmark(word_px, sub=True)
    gap = round(mark_px * 0.16)
    out = Image.new("RGBA", (max(m.width, w.width), m.height + gap + w.height), (0, 0, 0, 0))
    out.alpha_composite(m, ((out.width - m.width) // 2, 0))
    out.alpha_composite(w, ((out.width - w.width) // 2, m.height + gap))
    return out


# ------------------------------------------------------------------------ backgrounds
def vignette(w, h, cx=0.5, cy=-0.1, radius=1.1):
    """Nocturne page vignette: #1b1e31 near (cx, cy) fading to #121421 at the edges."""
    small_w, small_h = 192, max(2, round(192 * h / w))
    img = Image.new("RGB", (small_w, small_h))
    px = img.load()
    c1, c2 = rgb(BG_TOP), rgb(BG_EDGE)
    for y in range(small_h):
        for x in range(small_w):
            dx = (x / small_w - cx) * (w / h)
            dy = y / small_h - cy
            t = min(1.0, math.hypot(dx, dy) / radius)
            t = t * t * (3 - 2 * t)
            px[x, y] = tuple(round(c1[i] * (1 - t) + c2[i] * t) for i in range(3))
    return img.resize((w, h), Image.BICUBIC).convert("RGBA")


def presence_rings(img, cx, cy, unit, alpha=1.0):
    """The concentric rings of the presence (design radii 92/134/176/214 at 1080p scale)."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i, r in enumerate((92, 134, 176, 214)):
        rr = r * unit
        a = int(255 * alpha * (0.30 - 0.06 * i))
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=rgb(N400) + (a,), width=max(1, round(unit * 1.2)))
    # ticks on the outer ring
    rr = 214 * unit
    for k in range(60):
        ang = k / 60 * 2 * math.pi
        l = unit * (6 if k % 5 == 0 else 3)
        x0, y0 = cx + math.cos(ang) * rr, cy + math.sin(ang) * rr
        x1, y1 = cx + math.cos(ang) * (rr + l), cy + math.sin(ang) * (rr + l)
        d.line((x0, y0, x1, y1), fill=rgb(N400) + (int(255 * alpha * 0.22),), width=max(1, round(unit)))
    layer = layer.filter(ImageFilter.GaussianBlur(radius=0.4))
    img.alpha_composite(layer)


def wallpaper(w, h, path, hint=None):
    """The presence at the centre of a Nocturne vignette; wordmark lock-up beneath it."""
    img = vignette(w, h)
    unit = h / 1080
    cx, cy = w // 2, int(h * 0.46)
    presence_rings(img, cx, cy, unit, alpha=0.9)
    m = mark(round(176 * unit), glow=1.2)
    img.alpha_composite(m, (cx - m.width // 2, cy - m.height // 2))
    wm = wordmark(round(22 * unit), sub=True)
    img.alpha_composite(wm, (cx - wm.width // 2, int(cy + 240 * unit)))
    if hint:
        d = ImageDraw.Draw(img)
        f = font(max(14, round(15 * unit)))
        tw = d.textlength(hint, font=f)
        d.text(((w - tw) / 2, int(h * 0.90)), hint, font=f, fill=rgb(N500))
    img.convert("RGB").save(path, optimize=True)


def hairline(width, height=2, color=N800, alpha=255):
    """A rule that fades out over 48 px at both ends (the design's rule-fade)."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    px = img.load()
    c = rgb(color)
    fade = min(48, width // 4)
    for x in range(width):
        a = min(1.0, x / fade, (width - 1 - x) / fade)
        for y in range(height):
            px[x, y] = c + (int(alpha * a),)
    return img


def text_card(w, h, path, title, subtitle):
    """Dark card with the lock-up on top and two lines of text (Calamares slides)."""
    img = vignette(w, h, cx=0.5, cy=0.2, radius=1.0)
    lk = lockup(round(h * 0.26), round(h * 0.045))
    img.alpha_composite(lk, ((w - lk.width) // 2, int(h * 0.08)))
    d = ImageDraw.Draw(img)
    f1, f2 = font(max(18, h // 15), FONT_MEDIUM), font(max(13, h // 25))
    for txt, fnt, y, col in ((title, f1, 0.64, TEXT), (subtitle, f2, 0.77, N500)):
        tw = d.textlength(txt, font=fnt)
        d.text(((w - tw) / 2, int(h * y)), txt, font=fnt, fill=rgb(col))
    img.convert("RGB").save(path, optimize=True)


def icon(size):
    """App/system icon: the mark on a Nocturne surface plate with the 14 px radius scaled."""
    plate = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(plate)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=round(size * 0.22), fill=rgb(SURFACE))
    m = mark(round(size * 0.70), glow=0.8)
    plate.alpha_composite(m, ((size - m.width) // 2, (size - m.height) // 2))
    return plate


# -------------------------------------------------------------------------- outputs
def boot_assets():
    grub_iso = os.path.join(ROOT, "config", "bootloaders", "grub-pc", "themes", "eternity")
    grub_sys = os.path.join(CHROOT, "usr", "share", "grub", "themes", "eternity")
    for d in (grub_iso, grub_sys):
        os.makedirs(d, exist_ok=True)
    bg = vignette(1920, 1080)
    lk = lockup(120, 20)
    bg.alpha_composite(lk, ((1920 - lk.width) // 2, 56))
    for d in (grub_iso, grub_sys):
        bg.convert("RGB").save(os.path.join(d, "background.png"), optimize=True)
    shutil.copyfile(os.path.join(grub_iso, "theme.txt"), os.path.join(grub_sys, "theme.txt"))

    ply = os.path.join(CHROOT, "usr", "share", "plymouth", "themes", "eternity")
    os.makedirs(ply, exist_ok=True)
    for old in os.listdir(ply):
        if old.startswith("ring-") or old in ("logo.png", "progress-bg.png", "progress-fg.png"):
            os.remove(os.path.join(ply, old))
    frames = 24
    for i in range(frames):
        mark(176, draw=(i + 1) / frames, glow=1.0).save(os.path.join(ply, f"ring-draw-{i:02d}.png"))
    for i in range(frames):
        mark(176, draw=1.0, phase=i / frames * 2 * math.pi, glow=1.0, light_t=i / frames).save(
            os.path.join(ply, f"ring-loop-{i:02d}.png"))
    wordmark(24, sub=True).save(os.path.join(ply, "wordmark.png"))
    wordmark(24, sub=False).save(os.path.join(ply, "wordmark-plain.png"))
    hairline(520, 2, N800).save(os.path.join(ply, "rule.png"))
    hairline(520, 2, ACCENT).save(os.path.join(ply, "rule-accent.png"))

    cal = os.path.join(CHROOT, "etc", "calamares", "branding", "eternity")
    os.makedirs(cal, exist_ok=True)
    icon(128).save(os.path.join(cal, "logo.png"))
    text_card(640, 360, os.path.join(cal, "welcome.png"), "Welcome to Eternity 08", "One presence, not many apps. Everything personal stays on this device.")
    text_card(760, 428, os.path.join(cal, "slide-1.png"), "Local AI, no cloud required",
              "Qwen models run offline with llama.cpp. Ask Eternity from the command bar after install.")
    text_card(760, 428, os.path.join(cal, "slide-2.png"), "You stay in control",
              "Every action the assistant proposes is shown, confirmed and logged. Undo is one click away.")


def main():
    os.makedirs(OUT, exist_ok=True)
    boot_assets()
    with open(os.path.join(OUT, "logo.svg"), "w", encoding="utf-8") as f:
        f.write(mark_svg())
    with open(os.path.join(ROOT, "branding", "logo.svg"), "w", encoding="utf-8") as f:
        f.write(mark_svg())
    for size in (176, 512):
        mark(size).save(os.path.join(OUT, f"mark-{size}.png"))
    for size in (64, 128, 256, 512):
        icon(size).save(os.path.join(OUT, f"logo-{size}.png"))
    wordmark(96).save(os.path.join(OUT, "wordmark.png"))
    wordmark(96, sub=True).save(os.path.join(OUT, "wordmark-sub.png"))
    lockup(352, 44).save(os.path.join(OUT, "lockup.png"))
    for w, h in ((1920, 1080), (2560, 1440), (3840, 2160)):
        wallpaper(w, h, os.path.join(OUT, f"wallpaper-{w}x{h}.png"))
    wallpaper(1920, 1080, os.path.join(OUT, "greeter-1920x1080.png"),
              hint="Live session  ·  user: eternity   password: eternity")
    for size in (64, 128, 256):
        dst = os.path.join(CHROOT, "usr", "share", "icons", "hicolor", f"{size}x{size}", "apps")
        os.makedirs(dst, exist_ok=True)
        shutil.copyfile(os.path.join(OUT, f"logo-{size}.png"), os.path.join(dst, "eternity.png"))
    pix = os.path.join(CHROOT, "usr", "share", "pixmaps")
    os.makedirs(pix, exist_ok=True)
    shutil.copyfile(os.path.join(OUT, "logo-256.png"), os.path.join(pix, "eternity.png"))
    fonts = os.path.join(CHROOT, "usr", "share", "fonts", "truetype", "michroma")
    os.makedirs(fonts, exist_ok=True)
    if os.path.exists(MICHROMA):
        shutil.copyfile(MICHROMA, os.path.join(fonts, "Michroma-Regular.ttf"))
        shutil.copyfile(os.path.join(ROOT, "branding", "fonts", "OFL-Michroma.txt"), os.path.join(fonts, "OFL.txt"))
    print("rendered branding assets to", OUT)


if __name__ == "__main__":
    sys.exit(main())
