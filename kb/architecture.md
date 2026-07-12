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
treasures       [(item_no,)]  — challenge awards only (spec 0058)
materials       [(mat_type,)]
keys            [(key_colour,)]
blocks          [count]
plates          [(gate_id,)]
has_flames      bool
```

(No enemy data: enemies are distributed at layout time — spec 0058.)

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

**Layout failure log (spec 0065 D2).** Every `LayoutError` escaping the
top-level `build_level_dict` call appends a diagnostic entry to
`levellayout.LAYOUT_LOG_PATH` (`uglycraft-layout.log` in the working
directory, same convention as `uglycraft.hsc`) before propagating into the
retry: timestamp, failing grid, message, and — when grids were already
built — an annotated super-grid canvas rendered by
`leveldump.render_rooms` (the dict-level renderer: raw room dicts via
`Room.from_data`, no `World`, no `get_level` — the BL-48(a) enabler).
Per-strategy candidates absorbed inside `_build_grid` never log (the
recursive per-grid builds pass `_log=False`); context rides on the
exception (`failing_grid`, `rooms_so_far`, `super_positions` from the
corridors' `super_pos` — the stitch exits do not exist yet).  The test
suite redirects the path via a session-scoped autouse fixture in
`tests/conftest.py`.

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
level number). Generation cost (re-measured after the spec-0060 room rescale,
40–60 rooms at level 20): worst ~1.5 s for level 20, all ten together ≈ 5–6.5 s
— **faster** than the pre-rescale ~3.8 s / ~10.6 s despite 4–5× the rooms,
because fuller grids retry less and the coverable-sides constraint removes
doomed layout attempts. Script: `scratchpad/time_generation.py`.

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

### Generation performance (spec 0070)

`cProfile` of the build path (150 representative sweep builds ≈ 25 s) is
dominated by two functions, both in `levellayout.py`:

- **`_place_puzzle`** (~59 % cumulative) — the backward Sokoban BFS. Its nested
  `_comp_map(block_pos)` (connected-component map of `effective_pass − {block}`)
  is memoized in `comp_cache`, so its million-plus calls are cache **hits**;
  the cost is Python call overhead in the BFS inner loop. `curr_block` is
  constant across the 4-direction expansion, so `cm_curr = _comp_map(curr_block)`
  is hoisted once per node and the old `get_zone` wrapper is inlined/removed.
- **`validate_layout`** (~22 %) — was O(rooms²) × the full 28×14 interior grid.
  Now a **bounding-box prune** skips no-edge room pairs whose floor boxes
  (expanded by 1) cannot intersect — they can have no adjacent floor and no
  shared-boundary passage. Edge pairs are always scanned (a misplaced far-apart
  edge must still be flagged as 0-passage). `floor_tiles ⊆ (col,row,w,h)` box,
  so the bbox test is a safe over-approximation.

Both are byte-output-preserving (verified by `test_golden_*` +
`test_generation_determinism`); together ≈ −16 % generation wall. Harness:
`scratchpad/profile_generation.py` (six sweep feature sets × 25 seeds).

**Why generation speed matters for the tests.** The property sweeps are
generation-bound, and the suite is **CPU-core-bound**: `poe test` uses
`pytest-xdist -n auto`, but a dual-core machine caps the parallel win at ≈ 2.1×
(10:30 → ~4:57) regardless of test splitting. Build **memoization across tests
is useless** — hypothesis draws independent seeds, so measured duplicate
`(fs, seed)` builds are only 1–3 %. The only lever left below that core ceiling
is making generation itself cheaper. → `kb/backlog.md` BL-47; spec 0069/0070.

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

1. **Spanning tree** — `_spanning_tree(grid_count, rng, root, blocked,
   root_sides, strategies)` returns a list of
   `(parent_idx, exit_side, (super_col, super_row))` entries. This fixes which
   corridors connect to which and from which side. Since spec 0060 **exit
   sides are dictated by the strategy list**: a growth step is admissible
   only if the parent's accumulated side set (entrance included, for the
   start grid) stays coverable by a listed strategy — anchor-aware via
   `coverable_sides` (non-start grids lose the arm strategies `z`/`s`/`l`,
   R-T5), with the coverage tables now living in `levelgraph.py`. Grid
   zero's pseudo-exit draw is filtered the same way. Consequence: levels
   11–12 (spines only) are straight grid chains; level 13
   (`horizontal, vertical, l`) may turn once, at the start grid.
   `full_border` remains only for anchor-honouring failures — never for
   side mismatch. Room counts scale per grid since spec 0060: (2, 4) at
   level 11 rising to (40, 60) at level 20 (BL-21/BL-25).

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
6. Places locked-door or gate entities at the border tile if the edge has a barrier
   (surviving-prerequisite guarded), and records
   `border_barriers[exit_key] = (kind, param, home)` on **both** room dicts
   (spec 0056 / BL-12) — render metadata, never a cells entry, so the entry
   side can mirror the source barrier's appearance and live state
   (`border_exit_sprite` in game.py). Kinds: `('locked', colour,
   (home_room_key, border_tile))` / `('gated', gate_id, None)` /
   `('open', None, None)` for open and degraded borders. Open borders draw
   nothing — stairs are reserved for floor-to-floor travel.

The old all-or-nothing fallback (any unstitchable edge → rebuild *every* grid as
`full_border`) is gone — it would have collapsed ~33–54 % of multi-grid levels to
frame layouts once openings were corridor-restricted. `full_border` is now chosen
per grid only when no spine/stem strategy can honour that grid's anchor.

### Entrance & grid zero (spec 0053, BL-31)

The outside of the dungeon is **grid zero** at super-grid origin `(0,0)` —
reserved, empty, invisible, non-reachable (no `Node`, no `Edge`; the entrance
border tile stays solid wall and the entrance is a sprite, `game.py`).

- `LevelGraph.generate` draws grid zero's pseudo-exit side `S` for **every**
  generated graph (single-grid included since spec 0055 / BL-41 — the old
  scanning path gave level 11 a 64 %-left / 0 %-right entrance bias), puts
  the spanning-tree root at `delta(S)`, sets the root corridor's `super_pos`
  explicitly, and records `graph.entrance_side = opposite(S)`.
  `_spanning_tree(n, rng, root, blocked)` skips blocked cells (`{(0,0)}`) on
  every Prim step, so no grid — root child or later frontier growth — can
  occupy the origin, and no BORDER edge can ever use the entrance face.
  Start grid branching is therefore capped at 3 BORDER exits.
- `_build_super_grid` adds `entrance_side` to the start corridor's
  `required_sides` (strategy must cover it; R-S1 makes the corridor reach it;
  3 BORDER exits + entrance ⇒ `full_border`) and threads it into
  `build_level_dict` → `_pick_entrance`.
- `_pick_entrance` has two modes: with `entrance_side` (any generated start
  grid) it places the entrance deterministically — centre-most on-side
  corridor tile = `player_start`, border tile outside = `entrance` — and
  raises `LayoutError` if the corridor misses the side (unreachable per
  R-S1). Single-grid levels reach this mode via `build_level_dict`, which
  resolves `graph.entrance_side`, pre-picks a covering strategy with
  `_pick_strategy`, and passes `required_exits={entrance_side}` (spec 0055).
  The scanning mode (sides in left/top/bottom/right order, skipping
  `occupied_sides`) remains only for manually built graphs and the non-start
  grids' enemy-distance reference tile; the old col-0 fallback survives only
  as the never-surfaced reference-tile case for non-start grids whose
  reached sides are all BORDER-occupied.
- Golden note: the multi-grid rng stream shifted (one extra draw + blocked
  origin); `act2_L13_walk` was re-recorded. (Its subsequent per-process
  flake was PYTHONHASHSEED-dependent generation — fixed, see "Process
  determinism" below.)
- Grid zero must stay upgradeable to a real grid: a future spec may open the
  entrance on a condition (e.g. all loot collected) into a generated
  grid-zero area (per-level boss arena). The entrance sits at a stitch-
  compatible border-face position, so the upgrade is an `exits` entry plus a
  condition-gated barrier.

→ Invariant: R-T6 in `kb/requirements.md`. Tests: `tests/test_entrance.py`.

### Process determinism (spec 0054, BL-40)

Generation must be a pure function of the seed — identical output in every
Python process. `PYTHONHASHSEED` salts **str** hashing only, so iteration
over a set of *strings* (node names, side names) varies per process while
sets of int tuples (tiles) are stable. The rule for all generator code:
**never let a str-set's iteration order reach an rng pool or placement
order.** `LevelGraphBuilder._reachable` is therefore a dict-as-ordered-set
(insertion = reachability order) and `_current_grid_rooms` returns a list in
edge order; membership-only str-sets (`_water_rooms`, `required_exits`,
strategy `_COVERS_*`) are fine. Guard test:
`tests/test_generation_determinism.py` compares canonical level hashes
(probe `tests/_gen_hash.py`) across subprocesses with different
`PYTHONHASHSEED` values. → `kb/findings.md` BL-40 entry.

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
  fixed obstacle. It raises if no solvable pair exists.  Since spec 0063 the
  acceptance is **anchored**: the forward-start player zone must be reachable
  from the corridor through the player-augmented graph (openable barriers
  traversable for entry; the block itself never), and block starts are barred
  from landing tiles (`block_excluded`, R-P7 mirror) — pre-0063 the solvers
  accepted puzzles solvable only from components the block itself sealed off
  (BL-45's forced-push wedge).  → R-P11.
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

## Enemy & award economy (spec 0058)

**Enemies are a layout concern.** The graph carries no enemy data (the
old `add_enemies` / `Node.enemies` are gone — enemies never affected
solvability). `_distribute_enemies` (`levellayout.py`) runs once per
level — called by `_build_super_grid` after stitching, and by the
single-grid tail of `build_level_dict` (per-grid builds pass
`place_enemies=False`) — and places exactly `2 × G` enemies by the size
rule: candidates are non-corridor nodes without blocks/plates/flames
whose effective size `e = s − k ≥ 3` (`s` = largest all-floor square,
`k` = enemies assigned; capacity per room `s − 2`); selection is fewest
enemies → largest `e` → largest floor area → one rng tie-break; the
forge ogre (flagged via `graph.has_forge_ogre`) is placed first, hence
into the level's biggest room. Enemy tile choice keeps the old
enemy-pass semantics (`_pick_enemy_tile`).

**Every award is a challenge reward.** Graph phase: each locked, gated,
or water room gets exactly one award at creation; no unconditional
sprinkles (`add_treasures` is gone, `treasure_count`/`enemy_count`
retired). Layout phase: each enemy adds one guard award to its room,
and each flame room gets its award behind the jet. Challenge scaling:
`max(1, G // 2)` flame rooms (via `graph.flame_count`),
`max(1, G // 3)` water rooms via WATER entries prepended to `required`
(`has_water` flag; WATER left the stochastic edge draw).
→ R-P9/R-P10 in `kb/requirements.md`; tests:
`tests/test_enemy_room_size.py`, `tests/test_flames.py`.

**Flames are a layout concern too (spec 0062).** `add_flames` /
`Node.has_flames` are gone — the graph records only `graph.flame_count`.
`_place_flames` (`levellayout.py`) runs level-wide after stitching and
**before** `_distribute_enemies`: it picks jet-capable rooms by actual
geometry (non-corridor/closet, no plates/blocks, no WATER passage, a
real `_generate_flame_jets` cut with far tiles from the dict-derived
entry), relocates items off the jet line (near-side first, corridor
spill fallback, never onto far tiles), and places the flame award on a
far tile — a doubly-protected room's existing graph award *moves* there
(one award per room). Zero jet-capable rooms on a `has_flames` level is
a loud `LayoutError`. Rationale: jet generation silently failed in
small post-0060 rooms, leaving flameless "flame rooms" with free awards
(~1 per 4–5 levels, found by the final-world sweep
`scratchpad/sweep_award_visibility2.py`).

**EASY free awards are a feature (design decision, Daniel 2026-07-12).**
`Room.from_data` keeps at most one regular chaser per grid on EASY, so
about half the guard awards stand unguarded there — intentional
difficulty tuning. Do not "re-fix" by trimming awards or retiring the
cap; player-visible economy checks run on HARD.

## Item placement, spill, and barrier prerequisites (spec 0030)

**Placement order & spill (shared infra, also spec 0029 W1).**
`_place_items_in_room` places a node's collectibles in priority order **keys →
planks → treasures (awards) → other materials**. When the node's own floor is
exhausted, items **spill to the corridor** (`spill_floor`, the `CORRIDOR` node's
free tiles, passed from `build_level_dict`) instead of being silently dropped;
on the start grid `global_used` is pre-seeded with `player_start` and the
entrance tile (spec 0057, R-P8), so neither the room pass, the spill, nor the
flame far-tile pass can put an item under the spawning player;
`LayoutError` is raised only if the corridor is also full (→ regenerate; should
never happen). Enemies are exempt: they reserve no tile (may stand on an item)
and never spill, so they always fit in-room. This replaced the old `if p:`
silent-drop, which lost ~85% of planks and dropped keys in ~43% of key levels.

**Barrier ↔ prerequisite coupling (reworked in spec 0061).** The original
spec-0030 rule — barrier created only if its prerequisite survived — was
evaluated per grid, which silently elided every interior door whose key sat
on another grid (cross-grid keys are intended, R-V3): orphan keys — found
in play 2026-07-11 (5 keys, 3 doors on level 13).  Now:

- **Doors**: created unconditionally for every LOCKED edge between placed
  nodes.  Keys never drop (spill, K1), so a colour with no key anywhere in
  the **full graph** raises `LayoutError` (loud safety net) — the full
  graph's key colours are threaded into per-grid builds
  (`global_key_colours`).
- **Gates**: plates CAN drop with their puzzle room (not spilled), so
  gates keep degrade-to-open — at **global** scope: per-grid builds create
  interior gates unconditionally (`defer_gate_elision`) and
  `_build_super_grid` elides against surviving plates across all grids,
  exactly like border gates.  Interior-gate plates roam like keys since
  spec 0061 (`_puzzle_candidates` spans every reachable room; the Sokoban
  solver runs on the plate's grid; channels are global, spec 0050).

→ R-K1 in `kb/requirements.md`.

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
So **keys, treasures, and materials are never lost** (flame rooms relocate
their treasures to jet far-tiles; since spec 0058 that relocation falls back
to room floor / corridor spill, so even those are never dropped, and the C7
spill places an unplaced flame room's treasures too). Push-puzzle plates are
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
