# Player Spawn in Solid Wall

## Status

- [ ] Player always spawns on a corridor floor tile

---

## Problem

`player_start` is computed as `(pn.col + 1, pn.row + pn.h // 2)` where `pn` is
the `PlacedNode` for the start corridor.  This formula picks the second column
and vertical midpoint of the node's *bounding box* — a tile that is not
necessarily inside the node's `floor_tiles`.

For `z_h` layout the bounding box covers the entire grid interior, but the
floor only exists in the two horizontal arms (rows 1–arm_th and MAX_R−arm_th to
MAX_R) plus a narrow bridge.  The midpoint row (~8) falls in the empty zone
between the arms.  If the bridge doesn't pass through column 2, the computed
tile is solid wall and the player spawns inside it.

The same flaw affects `l` layouts whose L-shape clips a corner of the bounding
box.

---

## Root cause

Line 1730 of `levellayout.py`:

```python
player_start = (pn.col + 1, pn.row + pn.h // 2)
```

The formula assumes the entire bounding box is floor space (true for rectangular
nodes) but breaks for nodes with custom `floor_tiles`.

---

## Fix

Replace the formula with a search over `pn.floor_tiles` — pick the tile closest
(Manhattan distance) to the bounding-box centre:

```python
cx = pn.col + pn.w // 2
cy = pn.row + pn.h // 2
player_start = min(pn.floor_tiles,
                   key=lambda t: (abs(t[0]-cx) + abs(t[1]-cy), t))
```

File: `levellayout.py`, line 1730.

---

## Verification

Manual: run `poe run --level 11` through `--level 20` (several times each).
Player must always appear on open floor, never inside a wall.

---

## Done when

- [ ] `poe test` passes
- [ ] Player never spawns in a wall across levels 11–20 (user confirmed)
