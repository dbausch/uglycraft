# 0043 — Native-resolution rendering (GamePi 800×480 + desktop)

## Status

- [ ] Grid changed to **29×15** (`COLS=29`, `ROWS=15`, odd×odd) in `constants.py`;
      all derived code paths follow
- [ ] **`TILE` derived at startup** from the display size (formula below);
      no `pygame.transform.scale` anywhere — the frame is blitted 1:1, centred
- [ ] **HUD height rule** `HUD_H = min(leftover, 3·TILE)` implemented;
      remainder becomes symmetric black bezel
- [ ] All `sprites.py` `draw_*` functions are **fully proportional to `size`**
      (no hard-coded 32 px coordinates left)
- [ ] Font sizes derived from `TILE` (not fixed points)
- [ ] Menu / overlay / dialog screens laid out **proportionally** to the surface
      (no hard-coded 960×540 coordinates left in `game.py`)
- [ ] Window resize (desktop windowed mode) re-derives `TILE`, rebuilds the
      sprite dict and relayouts — still playable mid-game
- [ ] **`poe render-sprites`** — renders every sprite into one labelled grid
      PNG per target tile size (27, 32, 35, 66), or specific sizes via
      arguments: `poe render-sprites 41 99`
- [ ] **`poe render-levels`** — renders all Act 1 levels to PNG files, or
      specific levels via arguments: `poe render-levels 4 7`
- [ ] Act 1 levels (1–10) adapted to 29×15 (mechanical adaptation; artistic
      odd-symmetry redesign is a separate spec)
- [ ] Act 2 generator produces valid levels at 29×15 — full pytest suite green,
      seed sweep passes
- [ ] Manual check: GamePi34 at 800×480 fullscreen — pixel-perfect, bezel
      ≤ 9 px/side, no vertical bezel (user acceptance)
- [ ] Manual check: 1920×1080 desktop — 3 px side bezels, no vertical bezel
      (user acceptance)

## Motivation

Port UGLYCRAFT to the GamePi34 (ARM, 800×480 fullscreen) with **unscaled,
native-resolution sprites** — no fractional scaling, no blur, at most a few
pixels of black bezel. Today the game renders a fixed 960×540 logical surface
with integer-only upscaling (`best_scale` clamps to ≥ 1), so an 800×480 screen
would show the playfield *cropped* (−80 px left/right, −30 px top/bottom).

Decisions made (2026-07-09 session):

1. **Native rendering everywhere** — desktop targets (1920×1080, 1024×768) also
   render at a per-resolution native tile size instead of integer-scaling a
   fixed logical surface. pygame's procedural drawing renders *smoother* at
   larger tile sizes, not blockier.
2. **Grid 29×15** (was 30×16) — odd×odd improves level symmetry and is the
   all-rounder for bezels across all three targets (table below).

## Geometry (approved diagrams)

Grid is fixed at **29 columns × 15 rows**; `TILE` varies per display:

```
TILE  = min(display_w // COLS, (display_h − HUD_MIN) // ROWS)   HUD_MIN = 28
field = (COLS·TILE) × (ROWS·TILE)
HUD_H = min(display_h − ROWS·TILE, 3·TILE)
bezel = remainder, split symmetrically (odd px → extra on right/bottom)
```

| Target | TILE | Playfield | HUD | Bezels |
|---|---|---|---|---|
| GamePi 800×480 | 27 | 783×405 | 75 px | 8/9 px sides, 0 vertical |
| Desktop 1920×1080 | 66 | 1914×990 | 90 px | 3 px sides, 0 vertical |
| Desktop 1024×768 | 35 | 1015×525 | 105 px | 4/5 px sides, 69 px top/bottom |

### GamePi 800×480 — TILE = 27

```
      x=0 x=8                            x=791 x=800
y=0    ┌─┬────────────────────────────────────┬─┐
       │ │ playfield 783 × 405                │ │   29×27 = 783
       │ │ interior 27 × 13 playable tiles    │ │   15×27 = 405
y=405  ├─┴────────────────────────────────────┴─┤
       │ HUD 800 × 75 (full width)              │
y=480  └────────────────────────────────────────┘
```

### Desktop 1920×1080 — TILE = 66

```
      x=0 x=3                           x=1917 x=1920
y=0    ┌─┬────────────────────────────────────┬─┐
       │ │ playfield 1914 × 990               │ │   29×66 = 1914
       │ │                                    │ │   15×66 = 990
y=990  ├─┴────────────────────────────────────┴─┤
       │ HUD 1920 × 90 (full width)             │
y=1080 └────────────────────────────────────────┘
```

1024×768 keeps a 4:3 letterbox (69 px top/bottom) — inherent to showing a wide
grid on a 4:3 panel; it has a 114 px letterbox today.

## Rendering changes

- The logical-surface concept survives, but its size becomes
  `COLS·TILE × (ROWS·TILE + HUD_H)` computed at startup (and on
  `VIDEORESIZE`), not a constant. `present()` blits it 1:1 at the bezel
  offset — the scaling branch is deleted.
- HUD spans the full display width (drawn on the screen surface or on a
  full-width strip), so the side bezels only flank the playfield.
- F11 fullscreen toggle stays; on toggle, `TILE` is re-derived like a resize.

## Sprites

Every `draw_*(size=TILE)` in `sprites.py` currently defaults to 32 and most
bodies hard-code pixel coordinates for 32 (e.g. `draw_ogre_1` ears at
x = 5/27) — the `size` parameter is vestigial (→ noted in
`kb/uglycraft-display.md`). Each function is converted to proportional
geometry: coordinates as fractions of `size`, line widths and small details
guarded with `max(1, …)`. Known fiddly cases: boss 4-phase animation,
necklace Bézier, flame edges/nozzles, crack overlays.

The sprite dict is rebuilt whenever `TILE` changes (startup, resize,
fullscreen toggle) — procedural generation is cheap enough for that.

## Render-check poe tasks

Two headless render tasks (pygame with a hidden/dummy surface, output PNG)
serve as the visual verification tooling for this spec and for the later
level redesign:

- **`poe render-sprites [SIZE ...]`** — draws every sprite in the sprite dict
  into a single grid image per tile size, each cell labelled with the sprite
  key, written to e.g. `build/sprites-27.png`. With no arguments it renders
  all four target sizes (27, 32, 35, 66); any number of explicit sizes can be
  given instead: `poe render-sprites 41 99`. Multi-variant sprites (boss
  phases 0–3, crack levels, key/door colours, gate open/closed) each get
  their own cell.
- **`poe render-levels [N ...]`** — renders Act 1 levels as they would appear
  in-game (walls, floor, treasure, enemy start positions, player start) to
  `build/level-01.png` … `build/level-10.png`. With no arguments it renders
  all ten; any number of level numbers can be given: `poe render-levels 4 7`.
  Primary tool for checking the 29×15 adaptation and, later, the artistic
  redesign.

## Fonts & menus

- Font sizes become `TILE`-relative (current 64/36/22/16 pt were tuned for
  TILE 32 → factor `TILE/32`, rounded, minimum sizes guarded).
- **HUD font is the exception — it is width-constrained, not TILE-constrained.**
  The single HUD row is already horizontally full (7 elements: SCORE, LEVEL,
  LIVES, SEEK, BOSS/HARD, SHIELD, WALLS → see `kb/uglycraft-display.md`), so
  scaling its font by `TILE/32` would overflow on some targets (at 1080p the
  font factor 66/32 = 2.06 outgrows the width factor 1920/960 = 2.0). Instead
  the HUD font size is chosen by a **fit check**: render the worst-case
  content string (max-width values for every element, longest treasure name)
  and pick the largest size that fits the display width with a safety margin.
  The generous HUD heights (75–105 px) become vertical padding — they must
  not tempt the font upward past the fit check.
- All menu/overlay coordinates in `game.py` currently hard-code the 960×540
  layout (title at y=140, footer at y=510, …). These become fractions of the
  surface size.

## Grid-change fallout

- `COLS=29, ROWS=15`: `levellayout.py` derives `MIN_C/MAX_C`, `MIN_R/MAX_R`
  from these imports, so bounds follow automatically; tuned parameters
  (band/stem widths, room minima) are reviewed against the pytest suite and a
  seed sweep rather than re-derived on paper.
- `kb/requirements.md` and `kb/architecture.md` mention 30×16 explicitly —
  update after the change lands.
- Act 1 levels in `levels.py` are hand-authored 30×16 arrays: adapt each to
  29×15 mechanically (keep border ring, drop one interior column + row,
  verify solvability by playthrough). The *artistic* redesign exploiting odd
  symmetry is deliberately out of scope → follow-up spec.

## Out of scope (follow-up specs / backlog)

- GamePi function-key remapping (input translation shim in `main.py`)
- High-score name entry without a keyboard (on-screen picker)
- ARM packaging / on-device build task
- Artistic 29×15 level redesign using odd-row/column symmetry

## Verification

Python work has no automated UI suite; verification is:

1. `poe test` — full pytest suite (generator invariants at 29×15) green.
2. `poe render-sprites` — visual review of the sprite sheets at all four
   target sizes (plus spot-checks at odd sizes like 41).
3. `poe render-levels` — visual review of all ten adapted Act 1 levels.
4. Manual: `poe run` on the desktop at 1920×1080 fullscreen and in a resized
   window; visual check of bezels, HUD, sprites at TILE 66 and odd sizes.
5. Manual: run from source on the GamePi34 at 800×480 fullscreen; visual
   check of pixel-perfect rendering and bezels; play a full Act 1 level and
   an Act 2 level.

## Done when:

- [ ] `COLS=29, ROWS=15` everywhere; game boots and plays on desktop
- [ ] `TILE` derived from display size; no `transform.scale` call remains in
      the render path
- [ ] HUD rule implemented as specified (75 px @ GamePi, 90 px @ 1080p,
      105 px @ 1024×768); HUD font passes the worst-case fit check at all
      three targets
- [ ] All sprites proportional; sprite sheets from `poe render-sprites`
      reviewed at TILE 27, 32, 35, 66
- [ ] `poe render-sprites` and `poe render-levels` work with no arguments
      (all sizes / all levels) and with multiple explicit arguments
- [ ] Menus readable and centred at all three target resolutions
- [ ] Live resize re-derives everything without crash or artefact
- [ ] Act 1 levels playable at 29×15; Act 2 pytest suite + seed sweep green
- [ ] User confirms GamePi 800×480 rendering (manual check)
- [ ] User confirms 1920×1080 rendering (manual check)
