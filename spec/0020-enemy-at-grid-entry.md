# Enemy at Grid Entry Point

## Status

- [ ] No enemy spawns within MIN_ENEMY_DIST of a BORDER stitch tile

---

## Problem

When two grids are stitched, a wall tile at the border column/row is removed to
create a passage.  The stitching code picks this tile from `tile_owner`: if the
corridor's floor tiles don't reach to the very border column, the stitch tile
may be owned by a *room* node, not the corridor.

Enemies are placed in rooms via `_place_items_in_room` during per-grid
`build_level_dict`.  At that time, the global `player_pos` is only the
first-grid player start.  For rooms on subsequent grids there is no player
proximity guard at all: `player_dist` is `None` so the `min_dist_from_player`
check is skipped entirely, and enemies can land right next to the grid entry
point.

Even for the first grid, if the stitch tile is in a room (not the corridor),
the enemy distance check is relative to the player start, not the stitch tile.

---

## Fix

After computing all stitch positions in `_build_super_grid`, collect a set of
"entry tiles" — the inner-border tiles opened on both sides of each BORDER edge:

```python
entry_tiles: set[tuple[int,int]] = set()
# for each stitched edge:
entry_tiles.add((col_a, pos))   # exit side inner tile
entry_tiles.add((col_b, pos))   # entry side inner tile
```

Then post-process `all_enemy_starts`: remove any entry whose tile is within
`MIN_ENEMY_DIST` BFS steps of any entry tile.  Use the stitched wall map
(walls with stitch openings already applied) to compute passability.

If an enemy is removed, do not try to re-place it — enemy counts are soft
targets; a missing enemy is preferable to a teleport-death.

---

## Files

- `levellayout.py` — `_build_super_grid`: collect entry tiles, post-process
  `all_enemy_starts` in the assembled `room` dict

---

## Done when

- [ ] `poe test` passes
- [ ] Crossing grid borders in levels 12–20 never puts the player in
      immediate melee range of an enemy (user confirmed)
