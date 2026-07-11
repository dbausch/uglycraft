# Spec 0059 — Overlay message box sized to fit its text (BL-24)

## Overview

The "THE  FORGE  IS  DEFEATED!" win message overflows the fixed-width overlay
message box. Fix: size the box to the widest of the title and sub-line texts
(plus padding), keeping the current 420 px as a minimum so all existing
overlays render pixel-identically.

### Status checklist

- [ ] Pure box-width helper (`overlay_box_width`) added to `game.py`, computing
      `max(420, title_w + 2·PAD, sub_w + 2·PAD)` clamped to `LOGICAL_W − 40`
- [ ] `_render_overlay_text` uses the helper instead of the hard-coded
      `box_w = 420`; vertical layout unchanged
- [ ] Headless pytest coverage: formula properties + real-font fit check for
      the forge win message (`poe test` green)
- [ ] Manual check: forge-defeat message fits inside the box border
- [ ] Manual check: all other overlays (level intro, pause, game over,
      you-won, play-again) look unchanged

## Background (current behaviour)

Backlog item **BL-24 (P2)**: the message shown when the forge is defeated is
too long and overflows its message/dialog box.

The game renders to a 960 × 540 logical surface (`LOGICAL_W × LOGICAL_H` in
`constants.py`); the playfield above the HUD is `ROWS * TILE = 16 × 32 =
512 px` tall. Fonts (created in `Renderer.__init__`, `game.py:76-80`) all use
`fonts/ShareTechMono-Regular.ttf`:

| Attribute | Size |
|---|---|
| `font_big` | 36 pt |
| `font_med` | 22 pt |
| `font_small` | 16 pt |
| `font_hud` | 16 pt |

`_render_overlay_text(text, sub="", color=WHITE)` (`game.py:667-682`) draws a
dimming layer over the playfield, then a rounded box, then the texts:

```python
box_w, box_h = 420, 90 if sub else 60
bx = (LOGICAL_W - box_w) // 2
by = (ROWS * TILE - box_h) // 2
pygame.draw.rect(self.surf, (30, 30, 50), (bx, by, box_w, box_h), border_radius=8)
pygame.draw.rect(self.surf, color, (bx, by, box_w, box_h), 2, border_radius=8)

img = self.font_big.render(text, True, color)
self.surf.blit(img, (LOGICAL_W // 2 - img.get_width() // 2, by + 10))
if sub:
    simg = self.font_small.render(sub, True, GRAY)
    self.surf.blit(simg, (LOGICAL_W // 2 - simg.get_width() // 2, by + 58))
```

The box width is a **fixed 420 px**, but the title is centred on the screen
centre regardless of its width — a title wider than 420 px spills
symmetrically past both box edges.

### Call sites (all in `game.py`)

| Line | Title (`font_big`, 36 pt) | Sub (`font_small`, 16 pt) |
|---|---|---|
| 424 | `LEVEL  {n}` | `press any key` |
| 435 | `PAUSED` | `[P] to resume` |
| 439 | `GAME  OVER` | `press any key` |
| 443-444 | `THE  FORGE  IS  DEFEATED!` (if final level ≥ 20) or `YOU  WON!` | `Final score: {n}` |
| 448 | `PLAY AGAIN?` | `[Y] yes   [N] no` |

### Measured rendered widths (ShareTechMono-Regular, actual game font)

| String | Font | Width (px) |
|---|---|---|
| `THE  FORGE  IS  DEFEATED!` | big | **475** |
| `PLAY AGAIN?` | big | 209 |
| `GAME  OVER` | big | 190 |
| `YOU  WON!` / `LEVEL  20` | big | 171 |
| `PAUSED` | big | 114 |
| `Final score: 1234567` (7-digit max) | small | 180 |
| `[Y] yes   [N] no` | small | 144 |

Only the forge message exceeds 420 px: it overflows by 55 px total
(~28 px past each side of the box border). Every other title fits with
≥ 100 px to spare, and every sub-line fits easily.

## Design

### Approach chosen

**Size the box to the text** (option 3 from the backlog hint). Shortening the
message would lose flavour; multi-line wrapping is disproportionate for a
one-line overflow and would complicate the fixed vertical layout. Sizing is a
strict superset fix: any future long title or sub-line is handled too.

### Box-width formula

Add a small **pure, module-level helper** in `game.py` (pure so it is
headlessly unit-testable without constructing a `Renderer`):

```
overlay_box_width(title_w, sub_w) =
    min( max(420, title_w + 2*PAD, sub_w + 2*PAD),  LOGICAL_W - 40 )
```

- `PAD = 24` — horizontal padding between text edge and box border on each
  side. For the forge message: `475 + 48 = 523 px` box.
- **Minimum 420** — the current width; all existing short-title overlays keep
  exactly the same box and are pixel-identical after the change.
- **Clamp to `LOGICAL_W − 40` = 920 px** — defensive upper bound leaving a
  20 px margin to each screen edge; unreachable with current strings but
  guarantees the box itself can never spill off the 960 px logical surface.
- Arguments are the already-rendered surface widths
  (`font_big.render(text, …).get_width()`, and the sub surface width or `0`
  when `sub` is empty), so the helper needs no pygame font objects.

### Changes in `_render_overlay_text`

1. Render `img` (and `simg` if `sub`) **before** computing the box rect.
2. `box_w = overlay_box_width(img.get_width(), simg.get_width() if sub else 0)`.
3. Everything else stays as-is: `box_h` (90/60), `bx = (LOGICAL_W - box_w) // 2`,
   `by`, fill/border colours, `border_radius=8`, text blit positions. Title
   and box are both centred on `LOGICAL_W // 2`, so widening the box
   symmetrically keeps the text centred inside it with exactly `PAD` px
   (or more, when the 420 minimum applies) on each side — no blit changes.

### Out of scope

- The inventory/crafting overlay, difficulty select, history, and high-score
  screens have their own rendering code and no reported overflow — untouched.
- No changes to fonts, message wording, or `constants.py`.

## Verification

### Headless tests (`poe test`)

`tests/harness.py` already forces `SDL_VIDEODRIVER=dummy` /
`SDL_AUDIODRIVER=dummy`, and `pygame.font` rendering works under the dummy
driver, so this is unit-testable. New test module (e.g.
`tests/test_overlay_box.py`) covering:

1. **Formula properties** (pure, no pygame):
   - short texts → exactly 420 (`overlay_box_width(171, 180) == 420`);
   - wide title → `title_w + 48` (`overlay_box_width(475, 180) == 523`);
   - wide sub dominates when wider than the title;
   - never exceeds `LOGICAL_W - 40` for absurd inputs.
2. **Real-font fit check**: load `fonts/ShareTechMono-Regular.ttf` at 36 pt,
   render each title string used at the call sites (including
   `THE  FORGE  IS  DEFEATED!`), and assert
   `rendered_width + 2*PAD <= overlay_box_width(rendered_width, 0) <= LOGICAL_W - 40`
   — i.e. every actual in-game title fits inside its computed box.

### Manual verification (visual, user acceptance)

The actual on-screen appearance cannot be asserted headlessly; confirm by eye:

1. `poe run --level 20`, defeat the forge → the
   `THE  FORGE  IS  DEFEATED!` title sits fully inside the box border with
   visible padding on both sides; the `Final score: …` sub-line is centred
   below it.
2. In any level: pause (`PAUSED` box), level-intro box, and — after losing all
   lives — `GAME  OVER` and `PLAY AGAIN?` boxes all look exactly as before
   (420 px wide, unchanged layout).
3. Win on a non-forge final level (e.g. `poe run --level 10`, easy) →
   `YOU  WON!` box unchanged.

## Done when:

- [ ] `overlay_box_width` exists as a pure module-level function in `game.py`
      implementing `min(max(420, title_w + 2·24, sub_w + 2·24), LOGICAL_W − 40)`
- [ ] `_render_overlay_text` computes `box_w` from the rendered text surfaces
      via that helper; box height, colours, radius, and text positions
      unchanged
- [ ] New headless tests (formula properties + real-font fit for all call-site
      titles) pass; full suite `poe test` exits 0
- [ ] Manual check confirmed by the user: forge-defeat message fits inside its
      box (`poe run --level 20`)
- [ ] Manual check confirmed by the user: level-intro, pause, game-over,
      you-won, and play-again overlays are visually unchanged
