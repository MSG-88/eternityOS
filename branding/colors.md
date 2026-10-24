# Eternity 08 palette ("Nocturne", from the Claude Design capture, docs/design/README.md)

| Token        | Hex       | Use |
|--------------|-----------|-----|
| background   | `#161826` | page base; vignette from `#1b1e31` (top) to `#121421` (edges) |
| surface      | `#232532` | panels, cards, terminal background, icon plate |
| text         | `#e9e9ed` | primary text on dark |
| accent       | `#9184d9` | the presence, selections, progress, links, cursor |
| accent-100   | `#f5f4ff` | ribbon highlights, light point |
| accent-300   | `#d2cefd` | selected menu item |
| accent-400   | `#b5abfc` | hover |
| accent-600   | `#796cbf` | ribbon shadow side |
| accent-700   | `#5d5294` | numbering, muted accent |
| accent-800   | `#423a6a` | borders on accent surfaces |
| accent-900   | `#2b2741` | deep accent fill |
| neutral-400  | `#b2b6ca` | ring stroke, menu items |
| neutral-500  | `#9397ab` | secondary text, hints |
| neutral-600  | `#75798c` | tertiary text |
| neutral-700  | `#595d6c` | faint labels |
| neutral-800  | `#3f424d` | hairlines |
| neutral-900  | `#292b31` | deepest neutral |
| divider      | text at 16 % | rules fade out over 48 px at both ends |

Radii 4 / 8 / 14 px. Shadows: 1 px neutral ring plus 6 px and 16 px drops at 55 to 65 % black.

Typography: Inter (UI, 400; headings 500), JetBrains Mono (terminal, code), **Michroma**
(wordmark only; `branding/fonts/Michroma-Regular.ttf`, OFL).

## The mark (logo 3b "fading ring", Möbius ∞)

A 0 drawn as a ring (r 64 in a 140 viewBox, stroke 2.2) whose stroke fades out at the top
and bottom, with an upright ∞ inside drawn as a Möbius ribbon: 150 segments along
`x = 70 + 62·sin t·cos t / (1 + sin²t)`, `y = 70 + 46·cos t / (1 + sin²t)`, half-width
`7.5·|cos t|^0.75` (the band thins to an edge at the crossing), shaded from accent-100 to
accent-600 along the loop, with a light point travelling the path. `branding/render.py`
renders it statically (icons, wallpaper, GRUB, greeter) and as 48 Plymouth frames (24 for
the ring drawing in, 24 for the shading loop).

## The wordmark

"E" as three bars at Michroma's stem weight, then "TERNITY" in Michroma 400 with 0.34 em
tracking; sub-line "PERSONAL OS · 08" in Michroma at 0.3 em tracking in neutral-500.
