# Level Generator: Formal Requirements

Numbered invariants for `levelgraph.py` and `levellayout.py`.
Load this file at the start of any session that touches level generation.

→ Data structures: `kb/architecture.md`
→ Open bugs against these invariants: `kb/backlog.md`

---

## G — Grid

**R-G1** Interior bounds: cols 1–28, rows 1–14.
Constants: `MIN_C=1`, `MAX_C=28`, `MIN_R=1`, `MAX_R=14`, `INT_W=28`, `INT_H=14`.

**R-G2** Border tiles (col 0, col 29, row 0, row 15) are always wall.
They are never part of any node's `floor_tiles`.

---

## P — Placement

**R-P1** Floor tile sets are disjoint.
No two `PlacedNode` instances share a tile. Violation = layout error.

**R-P2** Every floor tile lies within interior bounds.
`MIN_C ≤ c ≤ MAX_C` and `MIN_R ≤ r ≤ MAX_R` for all tiles.

**R-P3** Every node in the graph appears in the `placed` dict.
Unplaced nodes are a bug; `derive_walls` will raise on any edge whose endpoint is absent.

**R-P4** Minimum usable room dimensions: `w ≥ 3`, `h ≥ 2`.
Smaller rooms are silently skipped by the packing functions.

**R-P5** Packing functions leave exactly 1 wall tile gap between adjacent rooms.
`_pack_band` advances `col += widths[i] + 1`; `_pack_band_vertical` advances `row += h + 1`.
This 1-tile gap is what becomes the shared-boundary wall tile.

---

## W — Walls

**R-W1** Every interior tile that is not a floor tile is a wall (`WALL_REINFORCED` by default).

**R-W2** Two rooms are separated by at least 1 wall tile on every boundary they share.
Guaranteed by R-P1 (disjoint floors) + R-P5 (1-tile packing gap).

**R-W3** A *shared-boundary tile* is a wall tile cardinally adjacent to floor tiles of BOTH rooms.
Used by `_find_connection_tile` and `validate_layout`.

**R-W4** Direct floor adjacency between two different rooms is always a layout error.
`validate_layout` reports it as: `"Rooms A and B have adjacent floor tiles at …"`.

---

## E — Edges

**R-E1** For every non-WATER edge between two placed nodes:
exactly **1** shared-boundary wall tile is converted to a passage.

**R-E2** For every WATER edge:
all shared-boundary wall tiles are converted (multi-tile stream).

**R-E3** For every pair of nodes with **no edge** between them:
**0** passable tiles on their shared boundary.

**R-E4** `derive_walls()` **must raise `ValueError`** when a non-WATER edge has
no shared-boundary tile. Silent `continue` is forbidden.

**R-E5** The connection tile is chosen as the centre of the shared boundary
(closest to the average position); ties broken by `(col, row)`.

---

## T — Topology

**R-T1** Every graph contains exactly **one** `CORRIDOR` node (`NodeSize.CORRIDOR`).

**R-T2** Every non-closet room must be adjacent to the corridor node.
Closet rooms (nodes with no direct corridor edge) are nested inside their parent.

**R-T3** Closet rooms share two outer walls with their parent (corner placement).
`_nest_closets` cuts a notch from the parent and places the closet at a corner.

**R-T4** For BORDER edges: the two corridor nodes must be in adjacent super-grid cells
(Manhattan distance 1 on the super-grid).

---

## S — Layout strategies

**R-S1** The corridor floor tiles must reach at least one tile on each border side
named in `required_exits`.
Example: `required_exits={'left', 'right'}` → corridor must touch col `MIN_C` AND col `MAX_C`.

**R-S2** Room zones must not overlap with corridor floor tiles.
They are always separated by at least 1 tile (the wall between corridor and room).

**R-S3** Zone boundaries are computed from the corridor's geometry and must be correct
before any room is packed. Wrong zone bounds → rooms placed where there is no shared
boundary with the corridor → `derive_walls` raises.

**R-S4** For the `l` strategy, Zone T (the corner zone) receives at most 1 room.
That room must span the full zone width to guarantee it reaches the v-arm base tiles.

**R-S5** Zone packing function and zone bounds must together guarantee that every
placed room has at least one wall tile adjacent to a corridor floor tile.

For `_pack_band` zones (rooms span full height): the arm/connector must cover the
zone's full **column** range, so every room's bottom or top wall is corridor-adjacent
regardless of horizontal placement.

For `_pack_band_vertical` zones (rooms span full width): the arm must cover the
zone's full **row** range, so every room's left or right wall is corridor-adjacent
regardless of vertical placement.

When this condition holds, `max_rooms=None` (no cap) is correct. A cap is only
needed when the condition cannot be satisfied for every position in the zone.

→ See the zone connectivity tables in `kb/architecture.md` for how each z/s/l
zone satisfies this invariant.

---

## V — Validation

**R-V1** `validate_layout(graph, placed, walls)` must return `[]` for a correct layout.
Any non-empty return is a bug in the layout algorithm, not the validator.

**R-V2** `validate_push_puzzles(room_data, tile_owner)` must return `[]` for every
puzzle to be solvable.

**R-V3** `graph.validate_playability()` must return `[]` before `build_level_dict` is called.
Unplayable graphs must never reach the layout stage.
