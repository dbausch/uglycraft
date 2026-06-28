# Spec 0031 — Overlay message box overflows long text (BL-24)

## Status

- [ ] B1 — `_render_overlay_text` uses one **universal** box: a **medium minimum
      width**, widened to fit larger content (text + padding). `"THE FORGE IS
      DEFEATED!"` no longer spills past the border
- [ ] B2 — All overlay messages (LEVEL, PAUSED, GAME OVER, win, PLAY AGAIN?) and
      their sub-lines stay inside the box (manual visual check)

## The defect

The win screen for finishing Act 2 shows `"THE  FORGE  IS  DEFEATED!"` via
`_render_overlay_text` (`game.py:1182-1183`, `_render_overlay_text` at
`game.py:1400-1415`):

```python
win_msg = "THE  FORGE  IS  DEFEATED!" if self._final_level >= 20 else "YOU  WON!"
self._render_overlay_text(win_msg, sub=f"Final score: {self._final_score}", color=YELLOW)
...
def _render_overlay_text(self, text, sub="", color=WHITE):
    ...
    box_w, box_h = 420, 90 if sub else 60          # <-- fixed width
    bx = (LOGICAL_W - box_w) // 2
    ...
    img = self.font_big.render(text, True, color)
    self.surf.blit(img, (LOGICAL_W // 2 - img.get_width() // 2, by + 10))  # centred on screen, not clamped to box
```

The box width is hard-coded to **420 px**, but the text is rendered centred on the
**screen** (not clamped to the box), so a string wider than 420 px spills past the
border on both sides.

Measured widths (`fonts/ShareTechMono-Regular.ttf`, the game's font):

| Text | font | width | vs box (420) |
|---|---|---|---|
| `THE  FORGE  IS  DEFEATED!` (current, double spaces) | big 36 | **475 px** | **overflows ~55 px** |
| `THE FORGE IS DEFEATED!` (single spaces) | big 36 | 418 px | just fits |
| `FORGE DEFEATED!` | big 36 | 285 px | fits |
| `YOU  WON!` | big 36 | 171 px | fits |
| `Final score: 123456` (sub) | small 16 | 171 px | fits |

`LOGICAL_W` is 960, so there is ample room to widen the box. The other overlay
callers (`LEVEL  N`, `PAUSED`, `GAME  OVER`, `PLAY AGAIN?`, `YOU  WON!`) are all
well under 420 px and are unaffected today — but the fixed width is fragile.

## Resolution

Make `_render_overlay_text` a **universal** box that sizes to its contents instead
of using a fixed 420 px. One sizing rule serves every overlay message:

1. Render the main text (and sub, if any) first; take the **max** of their pixel
   widths.
2. `box_w = clamp(max_text_width + 2*PAD, MIN_BOX_W, LOGICAL_W - 2*SCREEN_MARGIN)`
   — `MIN_BOX_W` is a **medium minimum** (the current 420 px is a good value) so
   short messages keep a consistent, not-too-small look; the box **widens** for
   larger content; the max keeps it on-screen (with `LOGICAL_W = 960` even the
   475 px text fits comfortably with padding).
3. Recompute `bx` from the new `box_w`; keep text/sub centred (they remain centred
   on `LOGICAL_W`, which equals the box centre, so they stay inside the border).

This is deliberately general: no per-message special-casing — any current or
future overlay string is framed correctly by the same medium-min/grow rule.

No message-text change is required (the box grows to fit), but double spaces in the
win string may also be normalised to single spaces as a tidy-up — optional, not
load-bearing once the box is dynamic.

## Verification

- **B2 — manual visual check (user acceptance):** finish/observe the Act 2 win
  screen (level 20) and confirm `THE FORGE IS DEFEATED!` sits inside the box;
  spot-check LEVEL / PAUSED / GAME OVER / PLAY AGAIN? overlays still look right.
  Debug entry: `poe run --level 20` and complete it (or temporarily trigger the
  win state).
- **B1 — optional automated guard:** extract the width computation into a small
  pure helper (e.g. `_overlay_box_width(main_w, sub_w)`) and unit-test that the
  returned width ≥ each input width + padding and ≤ `LOGICAL_W`. This needs no
  display, only `pygame.font`.

## Done when:

- [ ] B1 — The overlay box width is computed from the text; for any message the
      text fits within the border (helper unit-test green if added).
- [ ] B2 — Visual check confirms the win screen and all other overlays render
      cleanly inside their boxes (user-confirmed).
