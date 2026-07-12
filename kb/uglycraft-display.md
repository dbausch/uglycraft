# UGLYCRAFT — Display and Rendering Reference

## Integer Scaling

`best_scale(display_w, display_h) = max(1, min(display_w // LOGICAL_W, display_h // LOGICAL_H))`

Recalculated every frame from the current window size. The game renders to a `LOGICAL_W × LOGICAL_H` (960 × 540) surface, then `pygame.transform.scale` stretches it to `scale × logical_size`. Black bars fill the remainder. F11 toggles fullscreen via `pygame.display.toggle_fullscreen()`.

**Screens smaller than 960×540 crop the playfield.** `best_scale` clamps to a
minimum of 1, and `present()` centres the logical surface, so on e.g. an
800×480 display the blit offsets go negative (−80 px left/right, −30 px
top/bottom): the outer border tiles and part of the HUD row are cut off.
Downscaling to fit would need a fractional-scale branch in `present()` (or
`pygame.SCALED` display mode); there is no support for it today.

**Sprite `size` parameters are partly vestigial.** Every `draw_*` function in
`sprites.py` takes `size=TILE`, but most bodies use hard-coded pixel
coordinates that assume 32 px (e.g. `draw_ogre_1` ears at x = 5/27). Only a few
(e.g. `draw_player`) derive geometry from `size`. Changing `TILE` therefore
breaks most sprites — reducing the logical resolution is a rework of ~40 sprite
functions, not a constant change.

## HUD Layout

Single row at `y = ROWS * TILE = 512`, height `STATUS_H = 28 px`. Elements spaced evenly across full width in this order:

1. `SCORE NNNNNNN` (7-char right-padded score)
2. `LEVEL  N` (2-char right-padded level)
3. `LIVES  N` (red)
4. `SEEK: name` (padded to longest treasure name) — or `LOOT c/t` (gold) in `preplaced` spawn mode
5. **Key tracker** (spec 0071 `_hud_key_strip`): one 20 px slot (`_KEY_SLOT=23`) per key colour **present in the current level** — `World._level_key_colours`, the union of `data['rooms'][*]['keys']` colours ordered by `KEY_NAMES`, exposed to `game.py` via `_WORLD_ATTRS` delegation. Each slot draws `icon_key_{colour}` **lit** when held and **ghosted** (~15 % opacity, `_KEY_GHOST_ALPHA=38` via `icon.fill((255,255,255,38), BLEND_RGBA_MULT)` on a copy — the icons carry per-pixel alpha, so `set_alpha` is ignored). The colour set is fixed for the level, so the strip width is constant and the HUD never reflows during play; it differs only between levels. Keys are consumed on door-open, so a used key reverts from lit to ghosted. **A level with no keys omits the strip entirely** (`_hud_key_strip()` returns `None`), and the even-spacing loop redistributes its space.
6. `BOSS` (magenta) or `HARD` (red) or nothing (easy non-boss shows nothing)
7. `SHIELD XX` or `SHIELD   ` (9 chars; rendered in `HUD_BG` when inactive — invisible, maintains layout)
8. `WALLS  N.` (dot if `_breaks_toward_credit > 0`; colour: LTGREEN if credits > 0, YELLOW if partial progress, GRAY otherwise)

Each element is vertically centred by its own height (`cy = hud_y + (STATUS_H - img.height)//2`), so the 20 px key strip and the shorter text share a common centre line. The key strip is inserted into the rendered image list at index 4 (right after SEEK/LOOT) **only when non-`None`**. The upcoming **bridge counter** (BL-28) reuses the same convention — a HUD element that may be a pre-rendered surface or absent (shown only when the level has planks, else omitted and space redistributed). Keys are unique per colour (`levelgraph.py:441` distinct-colour pool), so neither the HUD nor the inventory shows a count next to a key.

## Enemy Sprite Selection

```python
ekey = f'enemy_{(self.level - 1) // 3 + 1}'
```
- Levels 1–3: `enemy_1` (green ogre)
- Levels 4–6: `enemy_2` (orange ogre with horns)
- Levels 7–9: `enemy_3` (purple ogre with war paint)
- Level 10: `boss_0`–`boss_3` (4-frame animation)

Boss animation frame: `(pygame.time.get_ticks() // 120) % 4` — one frame every 120 ms. Frames 0 and 2: small eyes (radius 3), mouth closed. Frames 1 and 3: large eyes (radius 4), mouth open (showing upper and lower teeth). Eye colours cycle orange → yellow → dim orange → bright yellow.

## Red Death Flash

On death: `_flash_timer = 600` ms. Each frame renders a `220, 20, 20, alpha` surface over the game field where `alpha = min(180, int(_flash_timer * 0.3))`. At 600 ms: alpha = 180. Fades linearly to 0 as timer counts down.

## Non-Obvious Sprite Details

**Player smiley smile:** computed point-by-point using `cos`/`sin` at 6° steps (0°–180°, 31 points) instead of `pygame.draw.arc` to avoid rendering artifacts. Half-width: `r * 5 // 12`; depth: `r // 4`.

**Necklace chain (item 7):** beads follow a quadratic Bézier with control point at `(cx, 17)`. The on-curve midpoint at t=0.5 lands at approximately y=11 (Bézier formula: endpoint + 2×control + endpoint / 4).

**Crack sprites:** `crack1` (1 hit) and `crack2` (2 hits) are transparent surfaces drawn over any wall. No `crack3` — at 3 hits the wall is removed. Crack sprites are stored pre-rendered in the sprite dict at init.

**Placed wall vs level wall:** placed walls use fill `(30, 30, 80)` (blue-grey); level walls use `(90, 22, 22)` (dark red). Visually distinct without additional markers.

**Boss sprites:** 4 `pygame.Surface` objects (`boss_0`–`boss_3`) pre-rendered at `SoundManager.__init__` time and stored in the sprite dict. Frame selection is computed at render time from `get_ticks()`, not pre-baked.

## Title Screen Ogres

Four bouncing ogres (one of each type: `enemy_1`, `enemy_2`, `enemy_3`, boss phase 0), each with independently seeded velocity: `random.uniform(45, 75)` px/s horizontal, `random.uniform(35, 60)` px/s vertical. Velocities are randomised at game start and preserved until the title screen is re-entered.
