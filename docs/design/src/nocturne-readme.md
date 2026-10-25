# Nocturne design system

(Live copy of `_ds/nocturne-c5d7fab8-3b36-4f18-bead-d530e00ff658/readme.md` from the Claude
Design project, read through the design MCP on 2026-10-25. `nocturne.css` next to this file is
the project's `styles.css`.)

Nocturne is a quiet, compact dark interface: a near-neutral blue-grey ground, Inter at medium weight, soft 8px radii and an accent used as a line and a glow rather than a flood. Rules fade to transparent at their ends — over 48px a side — rather than stopping cleanly; short accent marks stay solid. Contrast comes from the tonal ramps, not from saturation, and photographs blend into the page with their dark values falling away.

## How to use this

- Link the one stylesheet from every page and take every color, font, spacing, radius and shadow from its variables (`var(--color-*)`, `var(--font-*)`, `var(--space-*)`, `var(--radius-*)`, `var(--shadow-*)`). Never hard-code a hex, a font name or a px value the tokens already carry.
- Build with the classes below rather than inventing parallel ones.
- The whole system was derived from `theme.json`. To change the look, edit the tokens at the top of `styles.css`.

## Direction

Left-aligned, asymmetric layouts. Flush-left headings; content hugs the left edge with whitespace on the right. Buttons are outlined (1px accent border on transparent), not solid-filled. In decks, section dividers lift to a saturated deep-indigo ground (the `--color-section` tokens); everywhere else grounds stay desaturated, with soft gradient depth rather than flat fills. Wrap hero and inline images in the `.lighten` class (`mix-blend-mode: lighten`). Prefer photographs shot on dark or black backgrounds.

## Color

A dark ground (`--color-bg` #161826) with `--color-text` #e9e9ed and a single accent #9184d9 — a blurple in the product's own Pro-accent hue (OKLCH hue 289.2, L 0.660, C 0.125). This is a mono scheme: the `--color-accent-2-*` variables are a machine-derived stand-in; treat them as one role. Each role carries a 100–900 tonal ramp generated in OKLCH on a shared perceptual lightness scale. On this dark ground use the dark steps (700–900) for tinted fills, hovers and subtle borders, 500 as the role's base, and the light steps (100–300) for text on those tints and for pressed states; prefer ramp steps over ad-hoc `color-mix()`. For elevation use `--shadow-sm/md/lg`.

## Type

Inter for headings over Inter for body text. Density 0.70× and radius 8px are baked into the `--space-*` / `--radius-*` scales.

## Icons

Phosphor icons (https://phosphoricons.com) throughout.

## Interaction states

Every interactive element gets a `:hover` tint and a pressed state from the accent ramp (`--color-accent-400` on a dark ground, or a `color-mix()` tint for outlined/ghost variants); keyboard focus is `outline: 2px solid var(--color-accent); outline-offset: 2px`; never the default blue ring. Disabled controls drop to 45 % opacity. The accent-to-ground pair is tuned to at least 3:1 — for paragraph-size text in the accent use `--color-accent-300`.

## Components

| Class | What it is |
| --- | --- |
| `.btn` with `.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.btn-icon`, `.btn-block` | Actions — the primary is an accent outline, never a fill |
| `.tag` with `.tag-accent`, `.tag-accent-2`, `.tag-neutral`, `.tag-outline` | Small labels tinted from the ramps |
| `.field` + `label`, `.input`, `.radio` + `.dot`, `.seg` + `.seg-opt` | Form fields and choices |
| `.card` with `.card-kicker`, `.card-title`, `.card-body`, `.card-meta`; `.elev-sm/md/lg` | Surface-filled content cards; elevation utilities |
| `.nav` + `.nav-brand` | The header bar |
| `.table` | Data tables with themed header and fading row rules |
| `.dialog-backdrop` + `.dialog` (+ `.dialog-title/-body/-actions`) | A modal at the top elevation |
| `.hr` | A horizontal rule — present, but this system prefers whitespace |
| `.lighten` | The image wrapper |

## Do / Don't

- Keep chroma low outside the accent; lean on the neutral steps for surfaces, borders and muted text. Use the compact spacing scale. Outline primary actions.
- Do not flood large areas with the accent or any saturated fill. Do not use pure black or pure white. Do not stack heavy shadows; on a dark ground elevation is an edge plus ambient darkness. Do not bolden headings past 500 — hierarchy is size and space.
