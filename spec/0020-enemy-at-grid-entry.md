# Enemy at Grid Entry Point

## Status

- [ ] Stitch tiles always land in corridor floor, never in a room
- [ ] No enemy can appear at a grid entry tile by construction

---

## Problem

The stitch code scans `tile_owner` for any floor tile at the border
column/row when looking for a shared position between two grids.  If a room's
floor tiles extend all the way to col 1 or col 28, the selected stitch tile can
be in that room, not the corridor.  Enemies are placed in rooms; corridors have
no enemies.  Entering via a room-owned stitch tile can put the player immediately
next to an enemy.

---

## Insight

Corridors have no enemies.  If stitch tiles are restricted to tiles **owned by
the corridor node**, the entry point is always corridor floor and can never be
adjacent to an enemy.  No post-processing of `enemy_starts` is needed; the
constraint is satisfied structurally.

---

## Fix

In both `_stitch_ok` and the actual stitch loop, filter `tile_owner` to only
include tiles owned by the corridor when searching for shared rows/cols:

```python
# before (checks any floor tile at the border column):
rows_a = {r for (c, r) in room_a['tile_owner'] if c == col_a}

# after (only corridor-owned tiles):
rows_a = {r for (c, r), owner in room_a['tile_owner'].items()
          if c == col_a and owner == edge.node_a}
```

`edge.node_a` and `edge.node_b` are the corridor node names for each grid
(every BORDER edge connects two corridors, so these are the right names).

Apply the same change to the `_stitch_ok` validity check so it agrees with the
actual stitch.

---

## Relationship to the challenge graph

Enemies are already carried on room nodes in the challenge graph.  This fix
enforces the invariant structurally: corridor nodes own the entry tiles and
corridor nodes have no enemies.  No change to graph generation is needed;
the guarantee comes from layout.

---

## Files

- `levellayout.py` — `_stitch_ok` and the BORDER stitch loop in
  `_build_super_grid`

---

## Done when

- [ ] `poe test` passes
- [ ] Crossing grid borders in levels 12–20 never puts the player next to an
      enemy (user confirmed)
