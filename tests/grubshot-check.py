#!/usr/bin/env python3
"""Classify a GRUB screenshot: themed menu, bare prompt, or something else.

  grubshot-check.py SHOT.png            prints "GRUBSHOT menu|prompt|other nonblack=.. gray=.."
  grubshot-check.py SHOT.png menu       exit 0 only when the themed menu is on screen

The themed menu draws the Eternity background (tens of percent of the pixels are not
black); the `grub>` prompt and firmware text are a few gray glyphs on pure black.
"""
import sys

from PIL import Image

img = Image.open(sys.argv[1]).convert("RGB").resize((320, 200))
px = list(img.get_flattened_data()) if hasattr(img, "get_flattened_data") else list(img.getdata())
n = len(px)
nonblack = sum(1 for r, g, b in px if r + g + b > 30) / n
gray = sum(1 for r, g, b in px if abs(r - g) < 12 and abs(g - b) < 12 and r > 120) / n
if nonblack > 0.25:
    kind = "menu"
elif gray > 0.002 and nonblack < 0.08:
    kind = "prompt"
else:
    kind = "other"
print(f"GRUBSHOT {kind} nonblack={nonblack:.3f} gray={gray:.4f}")
if len(sys.argv) > 2:
    sys.exit(0 if kind == sys.argv[2] else 1)
