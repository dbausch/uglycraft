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

**R-P4** Minimum usable room dimensions: `w ≥ 2`, `h ≥ 2`.
Rooms below these thresholds are silently skipped by the packing functions.
Note: `_pack_band_vertical` rooms span the full zone width, and vertical zones are
always ≥ 3 wide by construction, so effective minimum width is 3 for those rooms.

**R-P5** Packing functions leave exactly 1 wall tile gap between adjacent rooms.
`_pack_band` advances `col += widths[i] + 1`; `_pack_band_vertical` advances `row += h + 1`.
This 1-tile gap is what becomes the shared-boundary wall tile.

**R-P6** Each packing function caps the room count to the maximum that fits at minimum
dimensions (min w=3 for `_pack_band`; min h=2 for `_pack_band_vertical`) accounting for
the (n−1) inter-room gaps:

  n_max = (band_w + 1) // 3   for `_pack_band`       [2 cols/room + 1 gap = 3]
  n_max = (band_h + 1) // 3   for `_pack_band_vertical`  [2 rows/room + 1 gap = 3]

Without this cap, a zone that receives more rooms than it can hold gets an inflated
`base` dimension for the first room (base=3 or base=2), drops the remaining rooms
at the overflow check, and leaves dead wall space inside the zone.  With the cap,
`base = usable // n ≥ minimum` always holds, and placed rooms fill the zone correctly.

→ See "Zone capacity and n-capping" in `kb/architecture.md`.

**R-P7** A pressure plate never sits on a **landing tile** (spec 0049): the
floor tile just inside any passage of its room — existing (doorway hole, door,
gate, breakable boundary wall) or buildable (the floor flanks of a water tile,
where a bridge would create a passage).  Rationale: the solved state of a push
puzzle is a block parked on the plate; a block on a landing tile seals that
passage, so a plate there would let the player trap themselves *by solving the
puzzle*.  Enforced at placement (`_plate_exclusions` in `levellayout.py`) and
mirrored at runtime (`World._try_auto_bridge` refuses to create a passage whose
landing tile carries a plate).

**R-P8** No treasure, material, key, plate, or block may occupy the start
grid's `player_start` tile or the `entrance` tile (spec 0057 / BL-16).
Enforced by seeding `global_used` with both tiles in `build_level_dict`
when `is_start_grid` — every collectible path (room floor, corridor spill,
flame far-tiles) consults that one set.  Plates/blocks additionally hold by
construction (`_puzzle_candidates` excludes corridors + R-T6); the entrance
tile is border ring (R-G2), excluded as a zero-cost guard for BL-43's
future openable entrance.  Tests: `tests/test_entrance.py` (R-P8 section);
sweep: `scratchpad/sweep_items_on_start.py`.

**R-P9** No enemy start tile ever belongs to the corridor (spec 0058 /
BL-20). For every room, the number of enemy starts it holds is at most
`s − 2`, where `s` is the side of the room's largest all-floor square
(equivalently: a 3×3 free square remains after virtually downsizing the
room by one tile per enemy in both dimensions).  Enemy hosts are candidate
rooms only — never a flame, plate, or block room; closets qualify by
actual floor shape.  A level holds exactly `2 × G` enemies (`G` grids;
forge ogre first on `has_forge_ogre` levels); enemies are dropped only
when no candidate room remains in the entire level.  Enforced by
`_distribute_enemies` in `levellayout.py`; locked by
`tests/test_enemy_room_size.py`.

**R-P10** Award items exist only as challenge rewards (spec 0058): each
locked, gated, flame, or water room carries one graph-placed award (one
per **room**, not per protection — a locked room that also gains flames
keeps a single award); each enemy adds one layout-placed guard award to
its room.  Total awards per level = `#challenge rooms + #enemies placed`
(modulo full-room spill to the corridor, the only exception).  Challenge
counts scale with the grid count: `max(1, G // 2)` flame rooms and
`max(1, G // 3)` water rooms per enabled level; closets are never flame
candidates (an uncarvable closet would spill its award into its parent
and break the accounting).  → `spec/0058-enemy-award-placement.md`.

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

**R-T3** Closet rooms are **carved from their parent's own tiles** (spec 0032):
`_carve_closets` splits off a back office / side office (~⅓ of the room) or a
corner toilet (~⅕, near-square), separated from the reduced room by a 1-tile
wall; the closet door is cut to the **room**, never the corridor.  Each room has
at most one closet (~10%, `closet_prob`).  In multi-grid levels closets are
copied into the per-grid subgraph by `_build_subgraph` (without that they were
silently dropped — BL-23).  A closet that cannot be carved (parent dropped or too
small) is currently skipped; content spill / puzzle elision is spec 0032 C7.

**R-T4** For BORDER edges: the two corridor nodes must be in adjacent super-grid cells
(Manhattan distance 1 on the super-grid).

**R-T5** BORDER openings land on the **corridor**, and corridors **continue**
across the border (BL-29 / spec 0042). Two parts:
- *Corridor-only stitch:* the inter-grid opening is punched only on a tile owned
  by the corridor node on **both** endpoints — never a room that happens to reach
  the border face. (Pre-fix, ~40 % of openings landed in rooms on every side; a
  gate-sealed entry room made the level unsolvable.)
- *Continuation:* grids are built in BFS order, so a grid's spanning-tree parent
  is placed first. The child's corridor segment at the shared face reproduces the
  parent's corridor **band** (same rows/cols + width). For a BORDER edge between
  two non-`full_border` grids the two corridor face bands are therefore identical.
  Enforced via `corridor_anchor=(side, lo, w)` threaded into the spine/stem
  strategies (horizontal/off_centre/vertical/t/double_t), which fix the segment
  position+width instead of drawing them. Arm strategies (z/s/l) cannot reproduce
  an arbitrary band and are filtered out when an anchor is active; `full_border`
  (frame reaches every position) is the per-grid last resort. A `full_border`
  **parent** is not passive: it **actively picks a varied exit band** within an
  attachable range (`_varied_band`: rows ~4–10 for left/right, cols ~7–21 for
  top/bottom) and anchors the child to continue it, with the chosen opening
  position recorded so a `full_border`↔`full_border` edge does not collapse to
  grid centre.
  Note: only **stems** are currently width 2–5; **spines** stay 2–3 (widening
  them regresses closet nesting, under redesign — see spec 0042 "Spine widening
  deferred"). Band coverage is still complete: left/right bands come from spines
  (≤ 3) and wide top/bottom bands from stems.

**R-T6** Grid zero (specs 0053/0055): **every generated graph** reserves the
super-grid origin `(0,0)` as the outside of the dungeon. The spanning tree
may never occupy it (blocked on every Prim step); the start grid sits at
`delta(S)` of grid zero's random pseudo-exit side `S` (uniform over the four
sides, single-grid included — BL-41), and `graph.entrance_side = opposite(S)`
— the start grid's face toward the origin — never carries a BORDER edge.
That side is part of the start grid's required exits, so the corridor
reaches it (R-S1), and holds the **level entrance**: the border tile outside
the centre-most on-side corridor tile, with `player_start` on the corridor
tile directly inside (adjacent by construction, and never beside a
locked/gated border door). Only manually built graphs (tests) have
`entrance_side = None` and use the unoccupied-side scan. Grid zero must stay
upgradeable to a real grid (condition-gated entrance opening, e.g. boss
arena) — see spec 0053 "Future extension" and BL-42/BL-43.

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
puzzle to be solvable.  Since spec 0048 its obstacle model is the runtime's own
(`RoomCells.blocked` from `cells.py`: walls, doors, closed gates, **unbridged
water**), it is re-run per stitched room after `_build_super_grid`, and a
failure raises `LayoutError` (fresh-seed retry) instead of `ValueError`.

**R-V3** `graph.validate_playability()` must return `[]` before `build_level_dict` is called.
Unplayable graphs must never reach the layout stage.

*Design note (Daniel, 2026-07-12, closing BL-03):* border-barrier
prerequisites (keys, plate+block) may legitimately be placed in **any**
earlier-reachable grid, not the barrier's source grid — hunting for them
is an intentional part of the challenge. The only requirement is
solvability, which is guaranteed three-fold: R-V3 at graph level; layout
drops of a prerequisite room degrade the border to an open passage; and
cross-grid channels persist at runtime (spec 0050 errata). Do not
"re-fix" prerequisite locality.
