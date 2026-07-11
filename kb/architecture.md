# Level Generator: Architecture

Read this at the start of any session touching `levelgraph.py` or `levellayout.py`.

→ Formal invariants: `kb/requirements.md`
→ Open bugs and improvements: `kb/backlog.md`

---

## Pipeline

```
LevelGraph                   ← topology: nodes (rooms) + edges (connections)
    │
    │  layout_graph()
    ▼
{name: PlacedNode}           ← spatial: each node has (col, row, w, h, floor_tiles)
    │
    │  derive_walls()
    ▼
walls: {(c,r): WALL_TYPE}    ← tile grid: every non-floor interior tile
water_tiles: [(c,r), ...]    ← water stream tiles (from WATER edges)
    │
    │  build_level_dict()
    ▼
level dict                   ← runtime format (world.py): walls, enemies, …
```

Multi-grid levels use `_build_super_grid()` instead, which runs the single-grid
pipeline once per grid, then stitches results together.

---

## Files

| File | Owns |
|------|------|
| `levelgraph.py` | `LevelGraph`, `Node`, `Edge`, `NodeSize`, `EdgeType`; graph generation (`LevelGraphBuilder`); playability validation |
| `levellayout.py` | `PlacedNode`; all layout strategies; `derive_walls`; Sokoban solver; `build_level_dict` |
| `levels.py` | Act 1 hand-authored level dicts; `ACT2_FEATURE_SETS` + lazy per-level Act 2 generation (`get_level`, `new_game_levels`, `regenerate_level`) |

---

## Key data structures

### `Node` (in `LevelGraph`)
```
name            str
size            NodeSize  (CLOSET | ROOM | HALL | CORRIDOR)
is_start        bool
super_pos       (col, row)  — super-grid position (corridor nodes only)
treasures       [(item_no,)]
materials       [(mat_type,)]
keys            [(key_colour,)]
blocks          [count]
plates          [(gate_id,)]
enemies         [(enemy_type, ...)]
has_flames      bool
```

### `PlacedNode` (in `levellayout`)
```
name        str
col, row    int  — top-left corner of bounding box
w, h        int  — bounding box dimensions
floor_tiles frozenset of (col, row)  — actual floor tiles (may differ from bbox for L-shapes)
```

For rectangular rooms: `floor_tiles = {(c,r) for c in [col..col+w) for r in [row..row+h)}`.
For L-shaped rooms and corridors: `floor_tiles` is a custom subset of the bbox.

### `EdgeType`
```
OPEN       — always-passable doorway (wall tile removed)
BREAKABLE  — stone or wooden wall (wall tile set to WALL_STONE or WALL_WOODEN)
LOCKED     — key required (wall tile removed, door entity placed)
GATED      — pressure plate + pushable block required (wall tile removed, gate placed)
WATER      — all shared-boundary wall tiles removed (stream tiles)
STAIRS     — connects nodes on different grids (floor transition)
BORDER     — connects corridors across 30×16 grid boundaries (super-grid)
```

---

## Layout strategies

Each strategy places the CORRIDOR node first (as an irregular `floor_tiles` set),
then divides remaining interior space into rectangular zones for room packing.

```
Strategy      Corridor shape                    Min zones   Max zones   Required exits
──────────────────────────────────────────────────────────────────────────────────────
horizontal    Full-width horizontal band        2           2           left + right
vertical      Full-height vertical band         2           2           top + bottom
off_centre    Asymmetric horizontal band        2           2           left + right
t             Horizontal band + 1 stem          2           3           left + right
double_t      Horizontal band + 2 stems         3           4           left + right + top/bottom
z_h / s_h     Two horizontal arms + v-conn      4           4           left + right
z_v / s_v     Two vertical arms + h-conn        4           4           top + bottom
l             L-shape (h-arm + v-arm)           4           4           one lr + one tb side
full_border   Rectangular frame                 1           1           any (covers all borders)
```

"Min zones" is the minimum number of zones that will receive rooms after `valid`
filtering (zones with `w ≥ 3, h ≥ 2`). In practice zone count can fall below
"min" if the rng produces very tight geometry.

`_pack_band(col, row, w, h)` fills a horizontal zone with rooms left-to-right,
1-tile gap between each.
`_pack_band_vertical(col, row, w, h)` fills a vertical zone top-to-bottom.

### Zone capacity and n-capping

Both packers cap `n` to the maximum rooms that physically fit at minimum dimensions
**before** computing per-room sizes. This ensures rooms use the full available space
rather than leaving dead wall area when too many rooms are assigned to a narrow zone.

| Packer | Min room dim | Per-room cost | n_max formula |
|--------|-------------|---------------|---------------|
| `_pack_band` | w ≥ 2 | 2 + 1 gap = 3 cols | `(band_w + 1) // 3` |
| `_pack_band_vertical` | h ≥ 2 | 2 + 1 gap = 3 rows | `(band_h + 1) // 3` |

After capping, `base = usable // n` is always ≥ the minimum (3 or 2 respectively),
so no special-case branch is needed.

**Why this matters:** without the cap, assigning 2 rooms to a 4-row vertical zone
gave `base=3`, placed the first room at h=3, then dropped the second because
`row+2 > band_end`. The placed room occupied 3 of 4 rows, leaving 1 row wasted.
With the cap: n_max = (4+1)//3 = 1, so only 1 room is assigned and it gets h=4
(full zone). The same logic applies horizontally: a 5-col zone with min w=2 now
fits n_max = (5+1)//3 = 2 rooms (2+1+2=5), whereas the old min w=3 allowed only
1 room (3 of 5 cols used).

→ See R-P4 and R-P6 in `kb/requirements.md`.

### Room-to-zone distribution (greedy, BL-09 fix)

`_layout_corridor` uses a greedy algorithm to assign rooms to zones, replacing
the old round-robin that silently dropped rooms in narrow zones.

**`_next_room_tiles(zw, zh, fn, k)`** — tile count the `(k+1)`-th room would
receive in a zone.  With `k+1` rooms there are `k` inter-room gaps:

```
_pack_band:          base = (zw - k) // (k + 1);  tiles = base * zh  (0 if base < 2)
_pack_band_vertical: base = (zh - k) // (k + 1);  tiles = zw * base  (0 if base < 2)
```

**Assignment loop:** for each room in the (pre-shuffled) queue:
1. If any zone has 0 rooms assigned, restrict candidates to those empty zones
   (every zone must receive at least one room before any zone gets a second).
2. Among candidates, pick the zone with the highest tile count.
3. Tie-break: larger zone area (`zw × zh`) → fewer rooms already assigned →
   per-zone random shuffle index.
4. If no candidate has tiles > 0, raise `LayoutError` (all zones full).

**`LayoutError`** propagates through `layout_graph` → `build_level_dict` to
`_generate_act2`, which retries indefinitely with a fresh RNG on each failure.
Failure is rare and always resolves: some seed will produce a room count within
the chosen strategy's zone capacity.

### Zone connectivity invariant

The packing function must be chosen so that **every placed room** has a wall tile
adjacent to a corridor floor tile, regardless of where in the zone it lands.

- `_pack_band` — rooms span the full zone **height**. The top or bottom wall is
  always corridor-adjacent. The arm/connector must cover the zone's full **column**
  range. Then all rooms connect regardless of horizontal position. ✓
- `_pack_band_vertical` — rooms span the full zone **width**. The left or right
  wall is always corridor-adjacent. The arm must cover the zone's full **row**
  range. Then all rooms connect regardless of vertical position. ✓

If this condition holds, no `max_rooms` cap is needed on the zone.  A cap is only
required when the arm does not cover the full perpendicular extent of the zone
(rooms placed outside the arm's range would be disconnected).

### z_h / s_h zones — all `_pack_band`, no cap

| Zone | Position | Connects via |
|------|----------|-------------|
| A | above first arm | bottom wall → first arm (arm spans Zone A's full col range) |
| B | right/left of connector, **extended to `MIN_R`** | bottom wall → second arm (arm spans Zone B's full col range) |
| C | below first arm, left/right of connector | side wall → connector (rooms span full height, always include connector rows) |
| D | below second arm | top wall → second arm (arm spans Zone D's full col range) |

### z_v / s_v zones — all `_pack_band_vertical`, no cap

| Zone | Position | Connects via |
|------|----------|-------------|
| A | beside first arm (left/right) | side wall → first arm (arm spans Zone A's full row range) |
| B | above connector, **extended to outer border** | inner side wall → first arm (arm rows `MIN_R..r_break+arm_h-1` ⊇ Zone B rows `MIN_R..r_break-2`) |
| C | beside second arm, **starts at `r_break`** | side wall → second arm (Zone C rows = `r_break..MAX_R` = second arm row range exactly) |
| D | below connector, **extended to outer border** | top wall → connector (connector covers the inner part of Zone D's col range) |

Zone C's no-cap guarantee: Zone C rows start at exactly `r_break`, so every room
(regardless of how many are stacked) is within `r_break..MAX_R` — the second arm's
row range — and the side wall is always corridor-adjacent.

Previously Zone C was extended to `MIN_R` with `max_rooms=1`. That approach was
fragile: a second room stacked above the first could land entirely above the
second arm's row range → disconnected. The fix was to extend Zone B to fill the
corner gap instead, and restrict Zone C to start at `r_break`.

### Strategy selection

**Exit-side filtering is done** — but only in `_build_super_grid`. It calls
`_pick_strategy(frozenset(exits), strategies, rng)` which filters against the
`_COVERS_*` sets before passing a single-element list into `build_level_dict`.
`layout_graph` itself just does `rng.choice(available)` with no exit awareness;
it relies on the caller to pre-filter `available`.

**Room-count filtering is done.** `layout_graph` filters `available` to strategies
where `n_rooms >= _STRATEGY_MAX_ZONES[s]` before `rng.choice` (lines 329–333),
falling back to `full_border` if nothing passes. `_pick_strategy` applies the same
filter for the super-grid path (lines 268–271, 277–280). Zone counts are in
`_STRATEGY_MAX_ZONES` (lines 185–194). BL-02 is closed.

---

## Lazy Act 2 generation (spec 0028 / BL-11)

Act 2 levels (11–20) are **not** generated at import. `levels.get_level(n)`
builds a single level on first access and caches it in `_act2_cache` (keyed by
level number). Generation is expensive — measured ~20 ms for a 1-grid level
(11) up to ~3.6 s for a 10-grid level (20); all ten together ≈ 10.6 s.

- Per-level seed is `_rnd.Random(_game_seed + index)`, so a given game produces
  the same level whether reached by play or by `--level N`.
- `new_game_levels()` picks a fresh `_game_seed` and clears the cache (a new game
  reshuffles, generating nothing up front).
- `regenerate_level(n)` force-rebuilds one level with fresh entropy — used by the
  `game._verify_blocks` safety net when a generated level has a stuck push-block
  (see BL-13: such unplayable levels should not slip through in the first place).
- `build_level_dict` / `_build_super_grid` accept an optional `progress(done,
  total)` callback (one unit per grid) so the loading screen can show progress.

History: previously all ten levels were generated eagerly at `import levels`
**and again** in `_full_reset` via `regenerate_act2` (~20 s of mostly-discarded
work, blank window). The main loop also clamps `dt` to `MAX_DT_MS` so the long
generation hitch no longer dumps a huge accumulated time into the update step
(which caused the level-start enemy "burst").

## The geometric challenge

The critical constraint (R-E1): every edge between two placed nodes needs exactly
one shared-boundary wall tile to convert into a passage.

A shared-boundary wall tile is a wall tile cardinally adjacent to floor tiles of
BOTH nodes. It exists only if the two floor sets are separated by exactly 1 tile,
and the corridor's floor tiles must reach that 1-tile boundary.

**Where this goes wrong:**

1. A room is packed into a zone that doesn't actually touch the corridor.
   → `derive_walls` raises: "Edge A↔B has no shared boundary tile."

2. Two rooms are placed with 0-tile gap (floor tiles touch directly).
   → `validate_layout` reports direct floor adjacency (layout error).

3. Two rooms share >1 shared-boundary wall tile and the connection finder picks
   one arbitrarily — usually fine, but must be in the centre.

4. For L-shaped and Z/S strategies: rooms must span the full dimension perpendicular
   to their corridor-adjacency wall (see "Zone connectivity invariant" above).
   For `l` Zone T: must span full width to reach the v-arm base tiles.
   For `z`/`s` zones: packing function and zone bounds must be chosen so the
   relevant arm covers the zone's full perpendicular extent — otherwise a cap or
   a zone redesign is required.

**Debugging rule:** before changing any zone boundary calculation, draw the
layout as an ASCII diagram with exact column/row numbers. Confirm the diagram
is correct before writing code.

---

## Super-grid (multi-room Act 2 levels)

Multiple 30×16 grids are placed on a super-grid (a 2D array of grid positions).
Each grid has one CORRIDOR node. BORDER edges connect corridor nodes in adjacent
super-grid cells (Manhattan distance 1).

### What is predetermined at graph generation time

Everything about the inter-grid topology is decided in `LevelGraph.generate()`:

1. **Spanning tree** — `_spanning_tree(grid_count, branch_prob, rng)` returns a list
   of `(parent_idx, exit_side, (super_col, super_row))` entries. This fixes which
   corridors connect to which and from which side.

2. **Exit/entry sides** — stored in each BORDER edge's `params` as `exit_side` and
   `entry_side` (always the opposite face). Example: `exit_side='right'` on grid A
   means `entry_side='left'` on grid B.

3. **Barrier type** — `_barrier_kw()` picks `open`, `locked`, or `gated` for each
   BORDER edge and stores `barrier`, `key_colour`, or `gate_id` in `params`.

4. **Super-grid positions** — each corridor node gets `node.super_pos = (sc, sr)`.

At graph generation time, the layout algorithm does not exist yet — only the
topology is recorded. The graph is the complete specification for multi-grid
structure.

### What is determined at layout time

`_build_super_grid()` in `levellayout.py`:

1. BFS-discovers corridors from the start corridor (respects the predetermined
   spanning tree order). Each grid's spanning-tree **parent is built before it**.
2. Reads `required_sides` from BORDER edge params (`exit_side`/`entry_side`).
3. **Coordinate at layout (continuation, BL-29 / spec 0042, R-T5).** For each
   grid in BFS order, computes its `corridor_anchor` from the already-built
   parent's corridor band at the shared face: `(child_side, lo, w)`. Builds the
   grid with `build_level_dict(..., corridor_anchor=anchor)` so its corridor
   segment reproduces the parent's band — the corridor runs straight through the
   border. The anchor is threaded into the spine/stem strategies, which fix the
   segment position+width. Arm strategies (z/s/l) are filtered out when an anchor
   is active; `full_border` (frame reaches every position) is the per-grid last
   resort. The start grid (no parent) is built unanchored. A `full_border`
   **parent** actively picks a varied exit band (`_varied_band`) and anchors the
   child to continue it — the chosen opening position is recorded (`chosen_pos`)
   so a `full_border`↔`full_border` edge does not collapse to grid centre.
4. **Stitching (corridor-only):** for each BORDER edge, intersects the rows/cols
   that both **corridor** floor sets (not rooms) reach at the shared face, then
   picks the middle position. Continuation guarantees this intersection is
   non-empty; opening on a room is impossible.
5. Punches the border wall at that position and records the `exits` dict entry
   pointing from each grid to the other.
6. Places locked-door or gate entities at the border tile if the edge has a barrier.

The old all-or-nothing fallback (any unstitchable edge → rebuild *every* grid as
`full_border`) is gone — it would have collapsed ~33–54 % of multi-grid levels to
frame layouts once openings were corridor-restricted. `full_border` is now chosen
per grid only when no spine/stem strategy can honour that grid's anchor.

### Data flow summary

```
_spanning_tree()                     → super-grid topology (which connects to which, from where)
start_next_grid(exit_side, barrier)  → BORDER edge with exit_side/entry_side/barrier in params
                                       + node.super_pos on each corridor node

_build_super_grid()  (grids built in BFS order, parent before child)
  reads: BORDER edge params          → required_sides per corridor
  computes: corridor_anchor          → parent's corridor band at the shared face
  decides: layout strategy           → spine/stem honouring the anchor (else full_border)
  decides: stitch position           → middle of shared CORRIDOR rows/cols at border face
  punches border wall at stitch pos  → exit/entry recorded in rooms['exits']
```

---

## Playability validation: the model boundary (BL-13)

**Why the runtime `_verify_blocks` safety net still fires even though every
generator step "preserves playability."** The answer is *not* that a graph
transformation is secretly lossy. The graph-level transformations and the
single-grid push-puzzle placement are genuinely sound:

- `_place_puzzle` (levellayout) selects each `(plate, block)` pair via a full
  **backward Sokoban BFS** — block confined to the room floor, player
  reachability computed across the whole grid, every *other* block treated as a
  fixed obstacle. It raises if no solvable pair exists.
- `validate_push_puzzles` then re-verifies all puzzles together and `build_level_dict`
  **raises** on failure (→ `_generate_act2_level` retries with a fresh seed).

So at placement time every block provably has ≥1 clear push axis. That makes the
net's `push_dirs == 0` condition **unreachable from any obstacle the solver knew
about** (walls, other blocks, gates, locked doors — the solver models blocks as
movable and gates/locks as openable, or conservatively excludes their tiles).

The real leak is a **model mismatch between the puzzle subsystem and the runtime
collision map**, not a lossy transform:

| Tile kind | `puzzle_passable` / `validate_push_puzzles` | runtime `_build_walls_multiroom` |
|-----------|---------------------------------------------|----------------------------------|
| reinforced / breakable wall | obstacle ✓ | solid ✓ |
| locked door (interior) | obstacle ✓ | solid ✓ |
| gate (interior) | obstacle ✓ | solid (until plate pressed) ✓ |
| other block | obstacle ✓ | solid ✓ |
| **water tile** | **OMITTED — treated as walkable floor** | **solid (until bridged)** |

`build_level_dict` computes `puzzle_passable = interior − walls − gate_tiles −
lock_tiles` (it never subtracts `water_tiles`), and `validate_push_puzzles`
builds `all_obstacles` from walls+doors+gates+blocks only (no water). But
`_build_walls_multiroom` sets `self.walls[wc][wr] = True` for every unbridged
water tile. WATER edges convert the 1-tile wall *between two rooms* into stream,
so a water tile is cardinally adjacent to room floor (R-E2/R-W3) — it can sit on
a block's only clear push axis or be a player push-from tile. The solver routes
the block over/along it; at runtime it's a wall. → genuinely unplayable, and the
subset where it leaves the block with zero push axes is exactly what
`_verify_blocks` catches.

Everything else the net can fire on is a **false positive**: a block whose sole
push axis is momentarily blocked by another block, a *closed* gate, or a locked
door — all of which the solver already accounted for as movable/openable.
`_verify_blocks` is a crude single-frame static check (treats blocks, closed
gates, locked doors, and water all as immovable) and re-runs on every
`_enter_room`, so it can also regenerate the whole level after the *player*
pushes a block into a corner on a previously-visited grid.

**Two further scope gaps (latent, not the block culprit):**
1. `validate_push_puzzles` runs **per grid** inside `build_level_dict`;
   `_build_super_grid` never re-validates the stitched whole. For push-blocks
   this is harmless — stitching only *opens* border walls and places barriers on
   out-of-bounds border tiles (col 0/29, row 0/15), which can't trap an interior
   block — but it matters for cross-grid water/key reachability.
2. Water-crossing solvability (reaching the *plate room across water*, bridge
   craftability) is separately loose — see BL-04.

**Empirical confirmation.** A headless sweep of 25 seeds × 10 Act 2 levels
(175 generated levels that contain blocks) replicated `_build_walls_multiroom`
+ `_verify_blocks` on start positions. **2 stuck blocks, both 100% water-caused**
(`(26,3)`: right+up water; `(26,12)`: right+down water — each wedged in an L of
two water tiles, one per axis, beside a vertical inter-room stream near the right
border). No wall/block/gate/door-only stuck cases occurred, matching the proof
that those are unreachable. Rate ≈ 1% of block-bearing multi-grid levels — rare
but real. Script: `scratchpad/repro_bl13.py`.

**FIXED (spec 0048, 2026-07-12).** Exactly the fix direction above, plus
structural unification: `RoomCells.blocked` (`cells.py`, spec 0047) is now
THE passability semantics — `World.blocked` folds in live gate state and
blocks at runtime, and `validate_push_puzzles` builds its obstacle model
from `build_room_cells(room_data)` with gates closed and its own block
set, so any future barrier kind or terrain reaches both consumers
automatically. `puzzle_passable` subtracts `water_tiles` at placement;
`_build_super_grid` re-validates every stitched room (`LayoutError` →
fresh-seed retry). `_verify_blocks` is demoted to a should-never-fire
last resort: it runs only on first entry of a freshly generated room
(player-wedged blocks on revisited rooms never regenerate the level —
BL-36), and a mid-transition regeneration no longer teleports the player
to the stale entry tile. Sweep: `scratchpad/sweep_stuck_blocks.py`
(successor to the lost repro_bl13.py) — 0 stuck blocks post-fix.

*Note on the table above:* the runtime column predates the spec-0047
refactor — `_build_walls_multiroom` and the walls grid no longer exist;
their semantics (water solid until bridged, etc.) live on byte-identically
in `World.blocked` / `RoomCells.blocked`.

→ Invariants: R-V2/R-V3 in `kb/requirements.md`. Water-reachability: BL-04.
→ Block-placement code: `_place_puzzle`, `validate_push_puzzles`, `_compute_dead_squares`
  in `levellayout.py`; runtime collision: `World.blocked` + `_verify_blocks`
  in `world.py` (specs 0045/0047/0048; → `kb/world-model-review.md`).

---

## Item placement, spill, and barrier prerequisites (spec 0030)

**Placement order & spill (shared infra, also spec 0029 W1).**
`_place_items_in_room` places a node's collectibles in priority order **keys →
planks → treasures (awards) → other materials**. When the node's own floor is
exhausted, items **spill to the corridor** (`spill_floor`, the `CORRIDOR` node's
free tiles, passed from `build_level_dict`) instead of being silently dropped;
`LayoutError` is raised only if the corridor is also full (→ regenerate; should
never happen). Enemies are exempt: they reserve no tile (may stand on an item)
and never spill, so they always fit in-room. This replaced the old `if p:`
silent-drop, which lost ~85% of planks and dropped keys in ~43% of key levels.

**Barrier ↔ prerequisite coupling.** A locked door / gate is created **only when
its key / plate actually survived placement**, never from the graph's
`node.keys`/`node.plates`. `build_level_dict` derives `placed_key_colours` /
`placed_gate_ids` from the surviving `all_keys` / `all_plates`; `_build_super_grid`
guards **border** barriers the same way, keyed on surviving keys/plates across all
grids. If a prerequisite is missing the passage is left **open** rather than a
soft-locked door. (With spill, a placed node's keys never drop, so this is mostly
a safety net — but it is the correct invariant and removes the BL-13-style
"mutate after validation" smell from stitching.)

**`_build_subgraph` copies the corridor's own items.** Multi-grid subgraph
construction previously copied items only for the corridor's *neighbour* rooms,
not the corridor node itself. `start_next_grid` can place a **border key** (or
treasures/materials) on a corridor via `_pick(list(self._reachable))`, so those
items were lost → key dropped → border door soft-locked. Fixed: copy the corridor
node's keys/treasures/materials/plates/blocks/enemies/has_flames too.

**Node drops (BL-23).** Investigation found 432/434 dropped nodes were CLOSETS:
multi-grid dropped 100% of closets because `_build_subgraph` copied only the
corridor's direct room neighbours, never the closets hanging off those rooms.
Fixed (spec 0032 step 1): closets are generated one-per-room at ~10%
(`closet_prob`), copied into per-grid subgraphs, and **carved from the parent's
own tiles** by `_carve_closets` (back/side office ~⅓, corner toilet ~⅕
near-square; door to the room; carve validated to keep the room's boundary with
corridor + every sibling).  `_place_puzzle` now raises `LayoutError` (retryable)
if a carve shrinks a room below its push-puzzle needs.

**C7 (step 2) closes the content-loss residual.** `build_level_dict` spills the
content of any **unplaced** node — a closet that could not be carved, or a room
dropped by the packer (R-P4) — into a placed neighbour (the closet's room if
placed, else the corridor), via `_place_items_in_room`'s room→corridor spill.
So **keys, treasures, and materials are never lost** (treasures excepted in flame
rooms, which relocate them to jet far-tiles by design). Push-puzzle plates are
**not** spilled: a dropped puzzle room's gate is elided by the surviving-
prerequisite coupling (gate created only if its plate is in `all_plates`). This
also closes the W1 node-drop residual (dropped plank rooms spill their planks).
Net invariant: `keys_dict == keys_graph`, `planks_dict == planks_graph`, and no
content-bearing node's items vanish — a node may be unplaced, but its content is
relocated, never dropped.

Two closet/zone rules: (1) closets are **excluded from the room count** used for
strategy selection (`_build_super_grid` counts only ROOM/HALL, matching
`layout_graph`) — otherwise a grid picks a layout with more zones than it has
regular rooms, leaving unoccupied zones. (2) `_carve_closets` never carves a
closet out of a **push-puzzle room** (parent with plates/blocks), since shrinking
it could make the puzzle unsolvable; that closet's content spills via C7.

→ Code: `_place_items_in_room`, `_build_subgraph`, `_build_super_grid` border
  stitch in `levellayout.py`. Spec: `spec/0030-key-placement-fixes.md`,
  `spec/0029-water-challenge-fixes.md` (W1). Invariants: R-P3/R-P4 in
  `kb/requirements.md`.

## Water bridge mechanics (spec 0029)

**Provisioning (W1).** `add_water_room` places exactly 2 planks per WATER edge
into reachable, non-water rooms (fungible, may be on any grid incl. the
corridor). With the spec 0030 spill + `_build_subgraph` corridor-items fix,
those planks never drop during layout (was 85% loss → 0%). A bridge costs 2
planks (`CRAFT_BRIDGE`); N water rooms ↔ 2N planks ↔ N bridges.

**Water-room identity (W4).** `build_level_dict` emits
`room['water_tile_room'] = {(c,r): water_room_node}`, mapping each water tile to
the node behind its WATER edge (`edge.node_b`), computed via
`_build_water_stream` over `orig_walls`. WATER edges are always intra-grid (never
BORDER), so each grid's room dict carries its own map.

**One bridge per water room (W2/W3).** Runtime `_try_auto_bridge` (`world.py`)
looks up the bumped tile's water room and refuses if it is already in
`self._bridged_water_rooms`; otherwise it builds the one bridge — a `Bridge`
fixture in the room's cells since spec 0047 (per-grid persistence now rides on
the Room object; the old `_bridged_tiles` dict is gone) — and records the room
in `_bridged_water_rooms`. The lock is keyed on the **room**, not the tile or edge,
so bridges cannot be wasted. The old per-grid `_bridges_remaining` cap (counted
grids-with-water, not water rooms → under-budget in ~19% of multi-water-room
grids) is **removed**; the per-room lock + crafted-bridge inventory are the only
limits.

**Validation (W5, closes BL-04).** `validate_playability` opens a WATER edge only
when **≥ 2 planks are reachable** (a craftable bridge); a pushable block no longer
counts as a water crossing. This is a graph-level gate; plank *survival* through
layout is the W1 guarantee (a dropped node still loses planks — BL-23 — with no
graceful fallback for water, unlike keys).

→ Code: `build_level_dict` (`water_tile_room`), `validate_playability` WATER block
  in `levelgraph.py`; `_try_auto_bridge`, `start_level`, `_enter_room` in
  `world.py`. Spec: `spec/0029-water-challenge-fixes.md`. Tests:
  `tests/test_water_challenge.py`.

---

## Target architecture (backlog BL-05)

All corridor shapes can be derived from a single parametric model:

1. One or more **arms**, each defined by: `(start_border, position_fraction, length, width)`
2. Arms connect at turns (L, Z/S) or branch (T, double-T)
3. Zone boundaries are computed analytically from arm geometry

This would replace the seven separate `_layout_*` functions with one parametric
function plus a zone-derivation pass. The geometric correctness proof becomes
easier because the zone boundaries are derived from the arm positions by
construction, rather than hardcoded per-strategy.

Prerequisite: `_build_super_grid` and `required_exits` plumbing must stay intact.
