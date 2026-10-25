# Eternity 08 design capture

Source: the Claude Design project **"Eternity OS AI Interface Design"**,
<https://claude.ai/design/p/f4409f71-86f6-4ef0-9cc6-babf6d42d16d?file=Eternity+08.dc.html&via=share>
(owner's account; Claude Design moves into Artifacts on 2026-12-14, so this folder is the
durable copy). Captured 2026-10-25 from the downloaded bundle `Eternity-08.dc.html`
(1.4 MB, self-contained: React 18.3.1 + Babel standalone, the Nocturne tokens, the
`eternity08.jsx` piece, the `animations-v3` engine, the tweaks panel, Inter and Michroma
woff2). Open the file in a browser to play it; nothing is fetched from the network.

To refresh: download the file again from the project (Share > download, or the
`?file=Eternity+08.dc.html` link), replace `Eternity-08.dc.html`, update the notes below and
the design section of `docs/backlog.md`, and commit. The source files can be unpacked from
the bundle's `__bundler/manifest` script (gzip + base64 per file).

## What it is

A 1920x1080 animated walkthrough of the Eternity 08 user interface, 1:08 long, nine scenes
in a loop. The thesis, stated by the assistant inside the piece: **one presence, not many
apps; input stays under 50 ms end to end; everything personal is kept on the device.**

| # | Scene | Length | What happens |
|---|---|---|---|
| 01 | Boot | 7 s | A hairline rule draws, the presence assembles ring by ring, the wordmark settles. Boot log: "eternity-kernel 8.0.2 — secure boot verified", "neural runtime · 4 cores online", "memory graph restored · 1.2 GB", "sensors · camera, mic, presence", "realtime scheduler · 240 Hz", "ready". |
| 02 | First run | 11 s | "Hello. I'm Eternity. / I run on this device, in real time. Let's set a few things." Asks the name (Maya), the unlock methods (Face, Passphrase, Voice, PIN), records a voice sample ("Eternity, it's me" → "Voiceprint stored · on device"). Continue / Skip for now. Step indicator 1 of 3. |
| 03 | Unlock | 7 s | Camera circle with a scan line, "Looking for you…", then "Good evening, Maya." with "Face recognised · 38 ms" and "3 things since you left". Other ways to unlock: Passphrase, Voice, PIN. |
| 04 | Home | 8 s | "The presence is the desktop": the core sits in the middle, cards orbit it (Calendar: Design review today 15:00; Mail: 3 new, 1 needs you, summarised; Now playing; Focus: writing block, notifications held). Caption: "Everything stays in orbit — Eternity keeps what matters closest." Status bar (logo, wordmark, clock, "● live · 38 ms", "NPU 12%", Wi-Fi, battery) and a command bar at the bottom: "Ask Eternity, or type a command", shortcut ⌘ Space. |
| 05 | Ask | 9 s | Typed into the command bar: "Move my 3pm to tomorrow and summarise the design doc". "Reading calendar, mail and the spec…", then a streamed reply ("Done — Design review is now tomorrow at 15:00. Priya and Ola were told. The shell spec argues for one presence, not many apps; input stays sub-50 ms end to end; everything personal is kept on the device."). The Calendar card updates in place. Actions: Open spec, Undo move, Tell Priya more. Side readout: "realtime · on device", "first token 41 ms", "~170 tok/s". |
| 06 | Launcher | 6 s | Twelve apps fan out radially around the core (Files, Mail, Calendar, Notes, Music, Photos, Terminal, Browser, Messages, Code, Monitor, Settings); typing "fil" filters to Files. |
| 07 | Files | 7 s | A Files window (sidebar Recents, Desktop, Projects, Photos, Lisbon ★, Shared) with "Search by meaning…": "photos from the Lisbon trip" → "Grouped by Eternity · 32 matches · 3 albums · March 2026 · 24 ms", eight thumbnails, then "Eternity: 'Most of these are from the Alfama walk on the 14th. Want an album?'" |
| 08 | System | 7 s | Monitor: CPU %, NPU %, Memory GB, Input latency ms as sparklines around an NPU load ring; "NPU LOAD · 34% · 240 Hz SCHEDULER · 0 DROPPED FRAMES". |
| 09 | Settings | 6 s | "Settings · Eternity / How she shows up": Voice (Calm / Bright / Off), Verbosity slider, Proactive suggestions (on), Keep everything on device (on), Share anonymous model telemetry (off), Unlock methods. "Changes apply instantly. Verbosity lowered — Eternity will answer in fewer words." The presence returns to centre and the loop closes. |

## Visual system ("Nocturne")

Tokens from the bundle (`:root` custom properties; the piece mirrors them as hex for
gradients and SVG):

| Token | Value |
|---|---|
| background | `#161826` (page vignette from `#1b1e31` to `#121421`) |
| surface | `#232532` |
| text | `#e9e9ed` |
| accent (violet) | `#9184d9`; ramp 100 `#f5f4ff`, 300 `#d2cefd`, 400 `#b5abfc`, 600 `#796cbf`, 700 `#5d5294`, 800 `#423a6a`, 900 `#2b2741` |
| accent 2 | `#a7a1db` |
| neutrals | 400 `#b2b6ca`, 500 `#9397ab`, 600 `#75798c`, 700 `#595d6c`, 800 `#3f424d`, 900 `#292b31` |
| section | `#262a60`, glow `#353b80`, ghost `#4c5397` |
| divider | `#e9e9ed` at 16 % |
| radii | 4 / 8 / 14 px |
| shadows | 1 px neutral ring, plus 6 px and 16 px drops at 55-65 % black |
| spacing | 2.8 px base scale (1 to 8) |
| body and headings | Inter (400; headings 500) |
| wordmark | Michroma 400, wide tracking (0.34 em), with a three-bar "E" drawn as three lines at Michroma's stem weight; sub-line "PERSONAL OS · 08" in Michroma at 0.3 em tracking |

Component classes defined by the system: `btn` (primary / secondary / ghost / icon / block),
`card` (kicker, title, body, meta), `dialog`, `input`, `radio`, `seg` / `seg-opt`, `table`
with row-level fading rules, `tag` (accent / accent-2 / neutral / outline), `nav`,
elevation `elev-sm/md/lg`. Rules and row dividers fade out at both ends ("rule-fade",
48 px), which the piece reuses everywhere a line appears.

Motion: eased entrances (easeOutCubic), drawn strokes (easeInOutSine), pops (easeOutBack);
typed text at about 24 characters per second; the core glides between per-scene positions
(±0.5 s around each cue) and its glow is a tweakable (default 1, range 0.3 to 1.8).

## The mark

Logo option **3b "Fading ring"**, chosen from four refinements of a prior "2c": a 0 drawn as
a ring whose stroke fades top and bottom (Nocturne rule-fade on the circle), with an upright
∞ inside drawn as a **Möbius ribbon**: the band thins to an edge at the crossing, its shading
rotates continuously along the loop, and a light point travels the path. The ring strokes in
during boot. It appears in the core (176 px), the boot lock-up and the status bar (20 px).
Direction given by the owner: "3b with animated Möbius strip style"; the wordmark "needs to
reflect Jarvis a bit in a tech fashion", hence Michroma. Alternatives on the table if it
should go further: more angular (Orbitron / Audiowide) or more condensed. The design system
is otherwise Inter-only, so the tech face is a deliberate, contained departure.

## Relation to the phase 1 OS

Phase 1 ships Debian 13 + XFCE with the Eternity GRUB theme, Plymouth splash, greeter
wallpaper and `eternity-chat` (local Qwen3.5 via llama.cpp). The design describes the target
experience of phases 2 and later: the first-run flow, the presence-centred desktop, the
command bar, semantic file search, the monitor and the settings page. The palette already
matches the phase 1 branding (dark navy, violet accent, Inter); the Möbius mark and
Michroma wordmark are new and should replace the current logo assets in `branding/`.
See the design section of `docs/backlog.md` for the work items derived from this capture.

## Unpacked sources (2026-10-25)

`docs/design/src/` holds the files the bundle carries, unpacked from its manifest:
`eternity08.jsx` (the piece: geometry, tokens, motion, copy), `animations-v3.jsx` (the
composition engine), `tweaks-panel.jsx`, `nocturne.css` (the design-system tokens and
component classes), `template.html` (the page), `dc-runtime.js` (the runtime), `scenes.js`
(scene list) and the Inter/Michroma woff2 fonts. The phase 3 shell is built from
`eternity08.jsx` element by element; see
`docs/superpowers/specs/2026-10-25-eternity-08-phase3-design.md` §4.2 for the extracted
geometry. The live project can be read through the design MCP once the owner runs
`/design-login`.
