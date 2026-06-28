# Spec 0033 — Don't place items on the player start tile (BL-16)

## Status

- [ ] S1 — `build_level_dict` reserves `player_start` in `global_used` **before**
      any item or push-puzzle placement, so no treasure, material, key, plate,
      block, or flame-far treasure can land on the tile the player spawns on
- [ ] S2 — The fix holds in every grid of a multi-grid level (each
      `build_level_dict` call reserves its own computed `player_start`); the
      border-wall entrance tile needs no reservation (it is outside interior
      bounds and never a floor tile)
- [ ] S3 — A pytest regression asserts, across many seeds × all Act 2 feature
      sets, that no placed collectible shares the `player_start` tile

## The defect

`build_level_dict` computes the spawn tile early (`levellayout.py:2026`):

```python
pn = placed[start_name]
entrance_tile, player_start = _pick_entrance(pn.floor_tiles, occupied_sides)
```

`_pick_entrance` (`levellayout.py:219-239`) returns a pair: `entrance_tile` is a
**border-wall** tile (col 0 / `COLS-1`, row 0 / `ROWS-1`), and `player_start` is
the **interior corridor floor tile** cardinally adjacent to it — where the player
actually stands at spawn:

```python
player_tile = pick_center(on_side)
return to_entrance(player_tile), player_tile   # (entrance_tile, player_start)
```

`player_start` is therefore a floor tile of the start node (the `CORRIDOR`), and
it is **never added to `global_used`**. `global_used` is created empty at
`levellayout.py:2124`:

```python
all_plates = []
all_blocks = []
global_used = set()
```

and is the shared "no two items on the same tile" set threaded through every
placement pass. `player_start` is passed into `_place_items_in_room` only as
`player_pos` (`levellayout.py:2182`), and that argument is used **solely for
distance weighting**, never to reserve the tile:

```python
# _place_items_in_room, levellayout.py:1842-1846
player_dist = None
if player_pos and player_pos in placed_node.floor_tiles:
    passable = set(placed_node.floor_tiles) - set(walls.keys())
    player_dist = _bfs_dist(player_pos, passable)
```

The tile-picker `_next()` (`levellayout.py:1848-1858`) only skips tiles already
in `used` (= `global_used`); since `player_start` was never added, it is a free
candidate:

```python
def _next():
    """Next free tile: this room first, then the corridor (spill)."""
    for p in floor:
        if p not in used:
            used.add(p); return p
    for p in spill:
        if p not in used:
            used.add(p); return p
    return None
```

There are **three** concrete paths that can drop an item onto `player_start`:

1. **The corridor's own items.** The placement loop iterates over *every* placed
   node, including the `CORRIDOR` start node (`levellayout.py:2177-2183`). Per
   spec 0030, `start_next_grid` can place a border key (or treasures/materials)
   on the corridor, so the corridor node's collectibles are placed on corridor
   floor — one of which is `player_start`.

2. **Spill overflow.** `spill_floor` is built from the corridor's free floor
   tiles (`levellayout.py:2171-2175`) and `player_start` is one of them, so any
   room that exhausts its own floor can spill a collectible onto `player_start`:

   ```python
   spill_floor = sorted(t for t in placed[corridor_name].floor_tiles
                        if t not in item_walls)
   ```

3. **Flame-far treasures.** The far-side flame-treasure pass
   (`levellayout.py:2191-2198`) guards only on `global_used`, so it too can pick
   `player_start` if a flame room reaches it.

When an item lands under the player at spawn it is either auto-collected on the
first frame (silent freebie) or rendered under the player sprite (visually
wrong). Push-puzzle plates/blocks are placed only inside their puzzle room (never
the corridor), so they cannot currently reach `player_start`, but reserving the
tile before puzzle placement keeps the invariant total and future-proof.

The `entrance_tile` itself is a **border-wall** tile (R-G1/R-G2 in
`kb/requirements.md`: borders col 0 / 29, row 0 / 15 are always wall and never a
floor tile), so no item can ever be placed there — only `player_start` needs
reserving.

## Resolution

Reserve `player_start` in `global_used` **once**, immediately after the set is
created at `levellayout.py:2124`, before push-puzzle placement and before the
item loop:

```python
all_plates = []
all_blocks = []
global_used = set()
global_used.add(player_start)   # spec 0033 / BL-16: never spawn an item under the player
```

Because every downstream placement pass consults this single `global_used` set —
`_place_puzzle` exclusions, `_place_items_in_room`'s `_next()` (room floor **and**
spill), and the flame-far-treasure pass at `2191-2198` — this one line closes all
three paths above with no per-pass special-casing.

Chosen over excluding inside `_place_items_in_room`: the corridor-spill and
flame-far-treasure paths live in `build_level_dict`, not in
`_place_items_in_room`, so reserving in the shared set is the only point that
covers every path. It also keeps `player_pos`'s existing distance-weighting role
untouched.

`player_start` is computed per `build_level_dict` call, so each grid of a
multi-grid level reserves its own spawn tile (`_build_super_grid` calls
`build_level_dict` once per grid). Only the start grid's `player_start` is the
real spawn (`_build_super_grid` picks `all_player_starts[corridor_order[0]]`), but
reserving one corridor tile per grid is harmless and keeps the rule uniform. No
change to `entrance_tile` handling is required.

## Verification

This is level-generator logic; verify with a pytest regression in the existing
suite (run via `poe test`). Following the `test_act2_solvability.py` pattern
(`_build(fs, seed)` retries on `LayoutError`, mirroring `_generate_act2_level`):

Across many seeds × all `ACT2_FEATURE_SETS` (plus the crowded multi-grid sets
`FS_CROWDED_LOCKED` / `FS_CROWDED_WATER`, which fill rooms and force spill),
build each level and assert that **no placed collectible occupies any grid's
`player_start`**:

- Gather `level['player_start']` and every collectible tile in the start room
  (`level['rooms'][level['start_room']]`) — `keys` (`(c, r, colour)`),
  `materials` (`(c, r, type)`), `treasures` (`(c, r, item_no)`), and for
  completeness `pressure_plates` / `pushable_blocks` — and assert `player_start`
  is in none of their `(c, r)` projections.
- For a single-grid feature set, additionally call `build_level_dict` directly
  and assert against its returned `player_start` so the per-grid reservation is
  exercised without depending on `_build_super_grid`'s start-grid selection.
- Add a focused single-grid property test (Hypothesis, like
  `test_single_grid_levels_solvable`) over a crowded feature set so the spill
  path is exercised: force a high `treasure_count` so rooms overflow into the
  corridor, then assert `player_start` stays item-free.

The test must be **red** before the one-line fix and **green** after.

## Done when:

- [ ] S1 — `global_used` contains `player_start` before puzzle and item
      placement; no treasure / material / key / plate / block / flame-far
      treasure is ever placed on it. —
- [ ] S2 — Verified per grid in multi-grid levels; entrance border-wall tile
      confirmed never a floor tile (no reservation needed). —
- [ ] S3 — pytest regression over many seeds × all Act 2 feature sets asserts no
      collectible shares `player_start`; red before the fix, green after
      (`poe test`). —
