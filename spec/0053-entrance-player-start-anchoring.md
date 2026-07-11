# 0053 — Entrance / player-start anchoring (BL-31)

## Status

- [ ] `_pick_entrance` fallback places the entrance adjacent to the player start
- [ ] Unit test: fallback path returns adjacent (entrance, player_start) pair
- [ ] Property test: generated level's entrance is border-placed, cardinally
      adjacent to `player_start`, and `player_start` is corridor-owned
- [ ] Property test: entrance tile never coincides with a border-exit tile
- [ ] Sweep re-run shows 0 adjacency violations (was 6/150)

## Problem

BL-31: the level entrance must be created next to a corridor tile, and that
corridor tile must be the player start.

`_pick_entrance` (levellayout.py:225) has two paths:

- **Main path** — already correct: it walks sides in order (left, top, bottom,
  right), skips sides occupied by BORDER exits, and on the first side the
  corridor reaches it picks the centre-most on-side corridor tile as
  `player_start` and the border tile directly outside as `entrance`.
  Adjacency and corridor ownership hold by construction.
- **Fallback** — fires when *every* side the corridor reaches is occupied by a
  BORDER exit (e.g. a `horizontal` spine with BORDER exits on both left and
  right, or a 4-exit start grid). It returns:

  ```python
  any_tile = min(corridor_tiles, key=lambda t: (t[1], t[0]))   # topmost-leftmost
  return (0, any_tile[1]), any_tile
  ```

  The entrance lands at `(0, row)` on the left border regardless of where
  `any_tile` is — typically 13–14 tiles away from the player start, embedded
  in the border next to some unrelated room.

Measured incidence (15 seeds × levels 11–20 = 150 generated levels):

| Check | Violations |
|---|---|
| entrance cardinally adjacent to player_start | **6 / 150 (4 %)** |
| player_start corridor-owned | 0 |
| entrance collides with a border-exit tile | 0 |

All six failures: entrance `(0, 1)`, player start `(13–14, 1)` — the fallback
fired on a multi-grid start grid (3–8 grids) whose corridor's reachable sides
were all BORDER-occupied.

So the player start is *always* corridor-owned already (both paths pick a
corridor floor tile); the defect is solely the broken entrance ↔ player-start
adjacency in the fallback.

## Geometry

Before (fallback today; seed 4, level 13 shape — top stem band at cols 13–14,
all reachable sides BORDER-occupied):

```
col:   0 1 2 ......... 12 13 14 15 ......... 29
row 0: # # # ......... #  #  ▓  # .......... #   ▓ = BORDER opening (top_14)
row 1: E . . room .... #  P  c  # .. room ... #   c = corridor stem tile
                          ↑
       ↑ entrance (0,1)   player start (14,1) — Manhattan distance 14
```

(The exact start tile is the topmost-leftmost corridor tile; entrance is
always forced to col 0 at that tile's row.)

After (fix): the fallback picks an occupied side the corridor *does* reach —
first in the same (left, top, bottom, right) order — and anchors the entrance
at the **low end** of the corridor's face band on that side:

```
col:   0 1 2 ......... 12 13 14 15 ......... 29
row 0: # # # ......... #  E  ▓  # .......... #   E = entrance (13,0)
row 1: # . . room .... #  P  c  # .. room ... #   P = player start (13,1)
                          ↑ adjacent: distance 1
```

Face band = the corridor's floor positions on the innermost ring of that side
(rows at col 1/28 for left/right, cols at row 1/14 for top/bottom) — the same
positions the border stitch intersects.

### Why the low end never collides with the border opening

The stitch (in `_build_super_grid`) opens the border at
`pos = shared[len(shared) // 2]`, where `shared` is the intersection of both
corridors' face bands:

- Continuation (R-T5) makes the child's band equal the parent's, so
  `shared` equals the start grid's own band; with band width ≥ 2 (spines 2–3,
  stems 2–5, `full_border` frame = full face), `shared[len // 2]` is never
  `shared[0]`.
- A `full_border` start grid's child is anchored to a `_varied_band`
  (`chosen_pos` ∈ rows 4–10 / cols 7–21), which never includes the full-face
  band's low end (position 1).

So `entrance ≠ opening` holds structurally; the property test pins it.

Worst case (band width 2): entrance and opening sit on adjacent border tiles —
accepted cosmetic outcome, both remain functionally correct (the entrance
border tile stays solid wall; it is a sprite only, `game.py:499`).

## Fix

Replace the `_pick_entrance` fallback (levellayout.py:243–245):

1. Walk `_ENTRANCE_SIDES` in the same fixed order, this time **ignoring**
   `occupied_sides`.
2. On the first side the corridor reaches, take the on-side corridor tile with
   the **lowest position** (min row for left/right, min col for top/bottom) as
   `player_start`; `entrance` is the border tile directly outside it.
3. The old col-0 fallback is deleted. (Every corridor strategy reaches ≥ 1
   border — R-S1 — so step 2 always succeeds.)

No signature change; callers (`build_level_dict` single-grid and per-grid via
`_build_grid`) are untouched. `player_start` keeps being computed before item
placement, so the corridor enemy min-distance logic (`MIN_ENEMY_DIST` in
`_place_items_in_room`) is unaffected. BL-16 (items may spawn on the player
start tile) stays an independent follow-up.

## Tests (red first)

In `tests/test_layout.py` (or a new `tests/test_entrance.py`):

1. **Unit, deterministically red today** — call `_pick_entrance` with a
   corridor reaching only left+right (e.g. a horizontal band of tiles) and
   `occupied_sides={'left', 'right'}`; assert the returned pair is cardinally
   adjacent, `player_start` is in the corridor tiles, and `entrance` is on the
   border ring.
2. **Property (hypothesis over seeds, multi-grid)** — build levels with
   `grid_count` 3–8 (reusing the `_build` retry helper style from
   `test_border_continuity.py`); assert for the start grid:
   - `entrance` is on the border ring,
   - Manhattan distance to `player_start` == 1,
   - `tile_owner[player_start]` is the corridor node,
   - `entrance` ∉ the border-exit tiles derived from `rooms[start]['exits']`.
3. **Sweep** — re-run the BL-31 detector (15 seeds × levels 11–20): 0
   violations on all three checks (pre-fix: 6 adjacency violations).

## Done when:

- [ ] Fallback replaced; `_pick_entrance` always returns an adjacent
      (entrance, player_start) pair with `player_start` corridor-owned
- [ ] New unit test red before the fix, green after
- [ ] Property tests green (`poe test` exits 0, no existing test broken)
- [ ] Detector sweep shows 0/150 violations
- [ ] BL-31 closed in `kb/backlog.md`; insight recorded in `kb/architecture.md`
      (entrance selection + fallback semantics)
