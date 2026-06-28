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
level dict                   ← game.py format: walls, enemies, treasures, …
```

Multi-grid levels use `_build_super_grid()` instead, which runs the single-grid
pipeline once per grid, then stitches results together.

---

## Files

| File | Owns |
|------|------|
| `levelgraph.py` | `LevelGraph`, `Node`, `Edge`, `NodeSize`, `EdgeType`; graph generation (`LevelGraphBuilder`); playability validation |
| `levellayout.py` | `PlacedNode`; all layout strategies; `derive_walls`; Sokoban solver; `build_level_dict` |
| `levels.py` | Act 1 hand-authored level dicts; Act 2 feature-set builders that produce `LevelGraph` objects |

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

**Room-count filtering is not done.** `layout_graph` picks the strategy from
`available` with no knowledge of `len(regular_rooms)`. A 2-room graph can draw
`double_t` (4 zones) leaving 2 zones empty — large wall areas with no floor tiles
or passages. This is BL-02. The fix is to filter `available` to strategies whose
zone count ≤ `len(regular_rooms)` before calling `rng.choice`, or alternatively
clamp the active zone count inside each strategy function.

---

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
   spanning tree order).
2. Reads `required_sides` from BORDER edge params (`exit_side`/`entry_side`).
3. Calls `build_level_dict()` for each grid independently, passing
   `required_exits=frozenset(exits)` so the chosen strategy guarantees corridor
   floor tiles reach the required border sides.
4. **Stitching**: for each BORDER edge, finds the intersection of floor
   rows/cols that both corridor floor sets reach at the shared border face, then
   picks the middle position. This one decision — the exact tile position of the
   border opening — is not predetermined; it depends on where corridor tiles land.
5. Punches the border wall at that position and records the `exits` dict entry
   pointing from each grid to the other.
6. Places locked-door or gate entities at the border tile if the edge has a barrier.

If any stitch fails (no shared floor rows/cols), all grids are rebuilt with the
`full_border` strategy, which puts corridor floor tiles on all four grid edges,
guaranteeing overlap.

### Data flow summary

```
_spanning_tree()                     → super-grid topology (which connects to which, from where)
start_next_grid(exit_side, barrier)  → BORDER edge with exit_side/entry_side/barrier in params
                                       + node.super_pos on each corridor node

_build_super_grid()
  reads: BORDER edge params          → required_sides per corridor
  decides: layout strategy           → compatible with required_sides
  decides: stitch position           → middle of shared floor rows/cols at border face
  punches border wall at stitch pos  → exit/entry recorded in rooms['exits']
```

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
