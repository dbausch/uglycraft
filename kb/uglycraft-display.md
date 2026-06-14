# UGLYCRAFT — Display and Rendering Reference

## Integer Scaling

`best_scale(display_w, display_h) = max(1, min(display_w // LOGICAL_W, display_h // LOGICAL_H))`

Recalculated every frame from the current window size. The game renders to a `LOGICAL_W × LOGICAL_H` (960 × 540) surface, then `pygame.transform.scale` stretches it to `scale × logical_size`. Black bars fill the remainder. F11 toggles fullscreen via `pygame.display.toggle_fullscreen()`.

## HUD Layout

Single row at `y = ROWS * TILE = 512`, height `STATUS_H = 28 px`. Elements spaced evenly across full width in this order:

1. `SCORE NNNNNNN` (7-char right-padded score)
2. `LEVEL  N` (2-char right-padded level)
3. `LIVES  N` (red)
4. `SEEK: name` (padded to longest treasure name)
5. `BOSS` (magenta) or `HARD` (red) or nothing (easy non-boss shows nothing)
6. `SHIELD XX` or `SHIELD   ` (9 chars; rendered in `HUD_BG` when inactive — invisible, maintains layout)
7. `WALLS  N.` (dot if `_breaks_toward_credit > 0`; colour: LTGREEN if credits > 0, YELLOW if partial progress, GRAY otherwise)

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
