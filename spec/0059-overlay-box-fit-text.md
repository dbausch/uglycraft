# Spec 0059 — Win message "YOU WON!", overlay box sized to fit its text (BL-24)

## Overview

The "THE  FORGE  IS  DEFEATED!" win message overflows the fixed-width overlay
message box — and the review (Daniel, 2026-07-12) disliked the sentence
itself. Two deliverables:

1. **The win message becomes "YOU  WON!"** — the forge string and its
   conditional are deleted. (The `else "YOU  WON!"` branch was dead code
   anyway: the WIN state only triggers on completing level `NUM_LEVELS`
   = 20 — `world.py`, `_end_game(won=True)` — so `_final_level` is always
   20 and the forge string was the *only* reachable win message.)
2. **Any overlay box auto-adapts to longer text**: size the box to the
   widest of the title and sub-line texts (plus padding), keeping the
   current 420 px as a minimum so all existing overlays render
   pixel-identically. With the short message nothing overflows today;
   the formula is the permanent guarantee for future strings.

### Status checklist

- [ ] Win message is `YOU  WON!` unconditionally; forge string and the
      dead `_final_level` conditional removed
- [ ] Pure box-width helper (`overlay_box_width`) added to `game.py`, computing
      `max(420, title_w + 2·PAD, sub_w + 2·PAD)` clamped to `LOGICAL_W − 40`
- [ ] `_render_overlay_text` uses the helper instead of the hard-coded
      `box_w = 420`; vertical layout unchanged
- [ ] Headless pytest coverage: formula properties + real-font fit check for
      every remaining call-site title + a synthetic overlong title
- [ ] Screenshot goldens: pause/game-over/intro/play-again pre-recorded and
      unchanged post-implementation; `shot_overlay_win` shows `YOU  WON!`
      in its box (replaces manual acceptance — review 2026-07-12)

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

**Change the message AND size the box to the text** (review, 2026-07-12 —
supersedes the original size-only approach; "shortening loses flavour" no
longer applies since the flavour sentence itself was rejected).

**Message change**: in the WIN branch of `render()` (game.py, currently
~line 466) the conditional

```python
win_msg = "THE  FORGE  IS  DEFEATED!" if self._final_level >= 20 else "YOU  WON!"
```

becomes the constant `"YOU  WON!"` (double-space style as elsewhere). The
conditional is dead: wins only occur at level 20.

**Box sizing** stays as the general mechanism — any overlay box adapts to
longer text automatically; sizing is a strict superset fix for any future
long title or sub-line.

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
   render each title string used at the call sites (now all short) plus one
   synthetic overlong title (e.g. the retired forge string as a fixture),
   and assert
   `rendered_width + 2*PAD <= overlay_box_width(rendered_width, 0) <= LOGICAL_W - 40`
   — i.e. every title, current or hypothetical, fits inside its computed box.
3. **Message test**: the WIN state renders `YOU  WON!` (assert the forge
   string no longer occurs in `game.py`; a harness WIN-state render smoke
   works headlessly).

### Screenshot goldens (replaces manual acceptance — review, 2026-07-12)

Overlay appearance is asserted via the spec-0044 screenshot-golden tier
(`tests/harness.py` `screen_hash` / `assert_golden`, headless dummy video
driver, re-recordable with `UGLYCRAFT_REGOLD=1`), extending
`tests/test_render.py` with one shot per overlay state (state set directly
on the harness game, as `test_shot_title` already does; `_final_score` /
`_final_level` seeded deterministically for the win screen):

1. `shot_overlay_pause`, `shot_overlay_game_over`, `shot_overlay_intro`,
   `shot_overlay_play_again` — goldens recorded **BEFORE** the
   implementation (red phase): they must still pass unchanged afterwards,
   which machine-proves the four existing overlays stay pixel-identical
   (the 420 px minimum doing its job).
2. `shot_overlay_win` — golden recorded **after** the implementation
   (the message changes by design); red until then (missing golden), then
   pinned: `YOU  WON!` centred in its box with the score sub-line.

Per review, the closing gate is the affected test modules
(`tests/test_overlay_box.py`, `tests/test_render.py`), not a full-suite
run.

## Done when:

- [ ] The win message is `YOU  WON!` unconditionally; the forge string and
      the dead conditional are gone from `game.py`
- [ ] `overlay_box_width` exists as a pure module-level function in `game.py`
      implementing `min(max(420, title_w + 2·24, sub_w + 2·24), LOGICAL_W − 40)`
- [ ] `_render_overlay_text` computes `box_w` from the rendered text surfaces
      via that helper; box height, colours, radius, and text positions
      unchanged
- [ ] New headless tests (formula properties + real-font fit for call-site
      titles and a synthetic overlong one + win-message assertion) pass
- [ ] Screenshot goldens: the four pre-recorded overlay shots (pause,
      game-over, intro, play-again) pass **unchanged** after the
      implementation; `shot_overlay_win` recorded once showing
      `YOU  WON!` inside its box
- [ ] Affected test modules green (`tests/test_overlay_box.py`,
      `tests/test_render.py`); no full-suite rerun required (review,
      2026-07-12)
