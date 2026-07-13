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

Single row at `y = ROWS * TILE = 512`, height `STATUS_H = 28 px`. Built as an
**HBox** (`hud.py`, spec 0072): `_render_hud` constructs a list of `HudElement`s in
display order and calls `HBox(LOGICAL_W, margin=10, gap_color=HUD_GAP).blit(...)`. Each
element reports its tight width; the box spreads the leftover width evenly across the
`n-1` inter-element gaps (`positions()` gives the left edges) and fills a subtle
brighter band in each gap (see below). Most elements are `LabelValue(font, label, value,
colour)` — rendered `f"{label} {value}"`, or label-only when `value == ""`; the key
tracker is an `IconStrip`. **Conditional elements are simply omitted from the list**
(no `None` sentinel, no magic index) — this replaced the old `(text,colour)`-tuple
list + `imgs.insert(4, strip)` splice. Element order:

**One text colour throughout (spec 0072):** every HUD text element is `HUD_TEXT`; inactive/empty counters (`SHIELD --`, `WALLS 0`, `BRIDGE 0`) use `HUD_DIM = (115,92,48)`, a darker shade of the *same* hue, so active vs inactive still reads at a glance without a second colour. The seven old colours (`HUD_LIFE`/`GOLD`/`MAGENTA`/`RED`/`LTBLUE`/`LTGREEN`/`YELLOW`) are gone from the HUD; partial WALLS/BRIDGE state is conveyed by the `.` dot alone. Key **icons** keep their own colours (they are icons, not text).

1. `SCORE NNNNNNN` (7-char right-padded score)
2. `LEVEL  N` (2-char right-padded level)
3. `LIVES  N`
4. `SEEK: name` (padded to longest treasure name) — or `LOOT c/t` in `preplaced` spawn mode
5. **Key tracker** (spec 0071 `_key_strip_element` → `IconStrip`): one 20 px slot (`_KEY_SLOT=23`) per key colour **present in the current level** — `World._level_key_colours`, the union of `data['rooms'][*]['keys']` colours ordered by `KEY_NAMES`, exposed to `game.py` via `_WORLD_ATTRS` delegation. Each slot draws `icon_key_{colour}` **lit** when held and **ghosted** (~15 % opacity, `_KEY_GHOST_ALPHA=38` via `icon.fill((255,255,255,38), BLEND_RGBA_MULT)` on a copy — the icons carry per-pixel alpha, so `set_alpha` is ignored). The colour set is fixed for the level, so the strip width is constant and the HUD never reflows during play; it differs only between levels. Keys are consumed on door-open, so a used key reverts from lit to ghosted. **A level with no keys omits the strip entirely** (`_key_strip_element()` returns `None` → not added to the HBox), and the space is redistributed.
6. `BOSS` or `HARD` or nothing (easy non-boss shows nothing)
7. `SHIELD XX` (active) or `SHIELD --` (dim `HUD_DIM` placeholder, inactive) — 9 chars, always present so the layout never shifts when a shield is gained/lost. (Was rendered invisibly in `HUD_BG` before spec 0072 D4; the gap band made a blank reserved slot look like an empty element, so it now shows a dim placeholder — chosen over merging/omitting the separator there.)
8. **BRIDGE counter** (spec 0072 D2): shown **only when the level contains planks** (`World._level_has_planks`, computed at level load), immediately left of WALLS; omitted (space redistributed) on plankless levels. Value = buildable bridges (`planks // 2` plus any pre-crafted bridge). Trailing indicator: `_` when the plank count is even, or a **drawn lower-half block** when odd (half a bridge banked). `HUD_TEXT` when ≥ 1 buildable, else `HUD_DIM`.
9. **WALLS counter**: value = `_place_credits`. Trailing indicator: `_` when the crushed-wall count is even (no half credit), or a **drawn lower-half block** when `_breaks_toward_credit > 0` (half an earned credit; `BREAKS_PER_CREDIT == 2` so this is binary). `HUD_TEXT` if credits > 0, else `HUD_DIM`.

**Trailing indicators** — the `_` (even/whole) is a font glyph; the half marker is a **drawn** filled rectangle in the lower half of one character cell (`LabelValue(tail_block=True)`), because ShareTechMono has *no* block-drawing glyphs (they all render as tofu). Replaces the earlier `.` dot.

**Dash leaders** (`hud.dash_fill`, spec 0072): every HUD string is tidied before rendering, **preserving length** (so fixed-width fields never reflow). A run of **> 2** spaces becomes `" " + "-"*(n-2) + " "` — one space, the padding rendered as dashes, one space — linking a right-justified value to its label (`SCORE ----- 0`; as the value grows the dash run shrinks but the field's right edge is fixed). A remaining trailing space then becomes a `-`, so left-justified padding like `SEEK: Coin␣␣␣` reads `SEEK: Coin ---` at the same reserved width. Runs of ≤ 2 spaces (e.g. `LEVEL  1`) are left alone. Because the HUD font is monospace, dashes and spaces share a cell, so the pixel width is identical.

Each element is vertically centred by its own height (`cy = top + (STATUS_H - img.height)//2`), so the 20 px key strip and the shorter text share a common centre line. Keys are unique per colour (`levelgraph.py:441` distinct-colour pool), so neither the HUD nor the inventory shows a count next to a key.

**Gap bands** (spec 0072 D4): the `HBox` fills each of the `n-1` inter-element gaps with a full-HUD-height rectangle of `HUD_GAP = (24,24,36)` (`HUD_BG` ×1.5, 50 % brighter — the near-black background needed a bigger multiplier than 1.1 to be visible) — a subtle brighter column that separates elements without the visual noise of a line (the original 1 px line read as too busy). Each band is inset `gap_inset = 6` px from the flanking elements (like the old line), drawn behind the elements, and never in the outer `margin`; a gap too narrow for the inset draws nothing. Opt-in via the `HBox(gap_color=...)` argument; the HUD passes `HUD_GAP`.

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
