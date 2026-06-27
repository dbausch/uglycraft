# Large Levels: Challenge Graph Branching, World Graph, Multi-Plane

## Status — Phase 0 (challenge graph branching + corridor layout extensions)

- [ ] Challenge graph (DAG) supports branching: a corridor node can connect to
      more than one grid; room nodes can chain (room → room within a grid)
- [ ] All locks in the physical world trace back to a DAG edge — no ad-hoc locks
- [ ] Physical border connections validated against DAG reachability:
      if the border exit tile is inside a room, that room's place in the DAG
      is used by the solvability checker, not bypassed
- [ ] L-shape corridor layout: two perpendicular arms; 4 variants (tl, tr, bl, br)
- [ ] Dead-end corridor layout: single arm + tip room; no exit on opposite side

## Status — Phase 1 (world graph — spanning tree, no loops)

- [ ] World graph generation produces a spanning tree (no loops, no cycles)
- [ ] Grids occupy unique hyper-grid coordinates; two grids never share a position
- [ ] If a newly placed grid would be adjacent to an existing non-parent grid,
      the adjacency is silently ignored (no connection created)
- [ ] Branching topology: some grids connect to 2+ successors
- [ ] Grid counts per level: level N has (N − 10) grids
- [ ] Each grid's layout strategy chosen to cover its required exits
- [ ] `branch_prob` and `loop_count` (currently 0) added to feature sets

## Status — Phase 2 (loops / shortcut passages — deferred)

- [ ] Loop edges added after spanning tree; always locked (key or gate)
- [ ] Challenge DAG stays acyclic even with world-graph loops, because the
      lock on the loop passage is always a DAG challenge

## Status — Phase 3 (multi-plane — deferred until staircase sprite exists)

- [ ] STAIRCASE edge type; `current_plane` game state; staircase sprite

---

## Core design principle: the DAG invariant

Every challenge in a level — every lock, gate, water crossing, or other
obstacle — must originate as an edge in the **challenge DAG** before it
appears anywhere in the physical world.

**Consequence**: a locked door cannot be placed in the world unless a
corresponding LOCKED edge is present in the DAG, with the key already in a
DAG-reachable node at the time of construction.

This principle already holds for room challenges (room locks, gated rooms).
It also already holds for BORDER barriers (locked grid exits) — those are
created by `_barrier_kw()` which adds the barrier to the DAG edge and places
the key in the current reachable set before switching corridors.

**The gap**: when the physical stitch tile lands inside a room (rather than
the corridor), reaching the other grid requires first entering that room.  If
that room is locked, the DAG edge for that room is the real prerequisite for
the BORDER transition — but the solvability checker currently treats the
BORDER edge as reachable directly from the corridor, ignoring the room.

The fix is not to avoid this situation, but to **validate correctly**: after
layout and stitching, identify which room (if any) owns each BORDER exit tile,
and route the reachability analysis through that room's DAG position.

---

## The design pipeline (DAG first, world second)

```
1. Build challenge DAG
      │  add rooms, locks, gates, BORDER edges, branches
      │  all challenges and all locks are placed here
      ↓
2. Verify DAG solvability
      │  every locked item has its key reachable before it
      │  this is the existing validate_playability() check
      ↓
3. Lay out each grid
      │  position rooms, derive corridor shape, derive walls
      ↓
4. Stitch grids (BORDER exits)
      │  find shared border tiles, cut passages
      ↓
5. Post-stitch DAG validation
      │  re-run reachability with physical routing information:
      │  if BORDER exit is in room_X, reaching the other grid
      │  requires room_X to be reachable first
      │  if this produces a new solvability failure → retry layout
      ↓
6. Physical level is ready
```

The world never introduces a lock that wasn't in the DAG.  If step 5 finds a
failure it means the stitch landed in a room that is locked in the DAG and
the key for that room is unreachable from the entry direction.  The remedy is
to retry layout for that grid (possibly with a different strategy), not to
bypass the DAG.

---

## Phase 0: DAG branching

### Current model

The LevelGraphBuilder produces a star topology per grid: every room connects
directly to the corridor.  Multiple grids form a linear chain of stars.

### Proposed extension

The DAG can branch in two ways:

**Intra-grid branching (room chains and branches)**  
Rooms within a single grid can connect to each other, not just to the corridor:

```
corridor → room_A → room_B          chain: room_B only after room_A
corridor → room_A → room_B
                 → room_C          branch: room_B and room_C both after room_A
```

This creates genuine depth inside a single grid — the player discovers room_B
only after entering room_A, which is impossible with flat star topology.

The layout algorithm must place connected rooms adjacent to each other.
Currently it does not guarantee this.  The fix: when two rooms share a DAG
edge, they must be assigned adjacent positions in the layout (sharing a wall).
The packing algorithm must be aware of room-room adjacency requirements.

**Inter-grid branching (world graph branches)**  
A corridor can have BORDER edges to more than one other corridor.  This creates
a branch in the world graph: the player stands at a junction grid and can
choose which direction to explore.

Both kinds of branching must be designed in the DAG *first*, before any
spatial placement is done.  The world graph topology is then a direct
reflection of the DAG structure, not generated independently.

---

## Phase 0: Generalised corridor model

All corridor layouts are instances of one model: one or more rectangular
corridor segments that form a connected pathway.  Arms extend outward from
the corridor; each arm either reaches a border (giving that grid an exit on
that side) or terminates in a tip room.

### Building up the corridor step by step

**Step 1 — Entry stem**  
Start with one arm entering from a border side (e.g. from the left).  The
arm extends inward to a variable depth.  This gives the corridor one border
exit on the entry side.

**Step 2 — Dead-end or pass-through**  
*Dead-end*: the corridor terminates at the inner end of the entry stem; a
tip room occupies the space beyond the arm's end.  The grid has one exit
(entry side only).

*Pass-through*: no tip room; the corridor extends onward to the opposite
border (or to a perpendicular border for an L-shape).  The grid has two
exits.

**Step 3 — First perpendicular stem (optional)**  
A stem branches off one side of the pass-through corridor at any position
along its length.  The stem position is chosen freely — it is NOT required
to be at the centre.  This stem either:
- Ends with a tip room (grid still has 2 exits).
- Extends to the border, giving the grid a third exit.

**Step 4 — Second perpendicular stem (optional)**  
A stem branches off the *opposite* side of the pass-through corridor.  Its
position along the corridor is independent of the first stem's position.

A 40 % chance is used to align both stems at the same column/row (producing
a cross-like shape); otherwise they are placed at independently chosen
positions (double-T).

This stem can also end with a tip room or extend to the border.

### Named shapes as instances

| Shape      | Arms extending to a border  | Description                            |
|------------|-----------------------------|----------------------------------------|
| dead-end   | 1 (entry only)              | corridor ends before opposite border    |
| horizontal | 2 (left + right)            | full-width spine; current layout        |
| vertical   | 2 (top + bottom)            | full-height spine; current layout       |
| L-shape    | 2 (perpendicular pair)      | entry arm + perpendicular arm; NEW      |
| T-shape    | 3 (straight + 1 perp.)      | current `t`                             |
| double-T   | 4 (straight + 2 perp.)      | current `double_t` / cross              |

### L-shape geometry

An L-shape has two arms meeting at a right angle.  There is no requirement
for a central hub — the bend occurs wherever the arm positions are chosen.
The bend position can be anywhere within roughly the centre half of the grid,
giving layout freedom.

Example: left + top variant (corridor enters from the left, exits via top):

```
top border
    │
    │  vertical arm (v_w cols wide, from top border down to r_bend)
    │
────┤  ← bend point at (c_bend, r_bend)
    │
    └════════════════════════════════════ left border
       horizontal arm (h_h rows tall, from left border to c_bend)
```

Rooms fill the large open zone: above the horizontal arm (left of the bend)
and to the right of the vertical arm (below the bend).

Four variants: top-left, top-right, bottom-left, bottom-right.  The variant
determines which perpendicular pair of borders the arms connect.

### Exit coverage

| Strategy      | Left | Right | Top | Bottom |
|---------------|:----:|:-----:|:---:|:------:|
| `horizontal`  | ✓    | ✓     |     |        |
| `vertical`    |      |       | ✓   | ✓      |
| `off_centre`  | ✓    | ✓     |     |        |
| `t`           | ✓    | ✓     | ½   | ½      |
| `double_t`    | ✓    | ✓     | ✓   | ✓      |
| `z`           | ✓    | ✓     | ✓   | ✓      |
| `l` (tl)      | ✓    |       | ✓   |        |
| `l` (tr)      |      | ✓     | ✓   |        |
| `l` (bl)      | ✓    |       |     | ✓      |
| `l` (br)      |      | ✓     |     | ✓      |

`t` (½): the spine guarantees left+right; the stem reaches *one* of {top,
bottom} at random.  Use `t` only for grids where exactly left+right exits
are required.

`l`: suitable only for grids with exactly two perpendicular exits.  The
variant is chosen based on which two exits are needed.

---

## Phase 1: World graph (spanning tree)

### No loops for now

The world graph is a **spanning tree**: exactly one path between any two
grids.  When the placement algorithm places a new grid adjacent to an
existing non-parent grid, that adjacency is silently ignored — no connection
is created.  Two grids must never share the same hyper-grid coordinate.

Shortcut passages (loop edges) are deferred to Phase 2.  This simplifies
the challenge DAG: it remains acyclic with no special handling needed for
loops.

### Hyper-grid positions

Each grid occupies a unique `(meta_col, meta_row)` cell on a logical
integer grid.  BORDER connections only exist between grids whose positions
differ by exactly 1 in one coordinate (Manhattan distance 1).  This is a
hard constraint of the stitching mechanism.

### World graph generation algorithm

**Input**: N grids (from `grid_count`), `branch_prob` p.

**Step 1 — Place start grid**  
Place grid 0 at (0, 0).  `placed = {(0,0): 0}`, `frontier = [0]`.

**Step 2 — Grow spanning tree**  
Repeat until `len(placed) == N`:

1. Pick a random grid G from `frontier` (uniform random — neither pure BFS
   nor pure DFS; gives varied tree shapes naturally).
2. Shuffle the 4 cardinal directions.
3. For each direction D (in shuffled order):
   - Compute candidate position P = pos(G) + D.
   - If P is already occupied (by any grid, parent or not): skip.
   - Otherwise: place new grid K at P, record BORDER edge (G→K, exit_side=D),
     add K to `frontier`.
   - With probability (1 − p): **stop** after placing one grid.
   - With probability p: **continue** to the next direction, potentially
     placing a second new grid from G in the same step (creating a branch).
4. If no direction yielded a new grid: remove G from `frontier`.

The result is a spanning tree where some nodes have degree ≥ 3 (branch
nodes) depending on `branch_prob`.

### Grid counts and parameters by level

| Level | Grids | branch_prob | Notes                            |
|-------|-------|-------------|----------------------------------|
| 11    | 1     | 0           | trivial — single grid            |
| 12    | 2     | 0           | always linear                    |
| 13    | 3     | 0.20        | first branching opportunity      |
| 14    | 4     | 0.25        |                                  |
| 15    | 5     | 0.30        |                                  |
| 16    | 6     | 0.30        |                                  |
| 17    | 7     | 0.35        | multi-plane here in Phase 3      |
| 18    | 8     | 0.35        |                                  |
| 19    | 9     | 0.40        |                                  |
| 20    | 10    | 0.40        | full scale for current Act 2     |

`branch_prob` values are first-guesses; playtesting will tune them.

### Strategy selection per grid

After the spanning tree is built, each grid's required exits are known.
The layout strategy must be chosen to cover those exits:

```python
def _pick_strategy(exits, available, rng):
    compatible = [s for s in available if _covers(s, exits)]
    return rng.choice(compatible) if compatible else 'double_t'
```

`_covers` rules:

| Required exits                         | Compatible strategies            |
|----------------------------------------|----------------------------------|
| ∅ (isolated or start grid, 1 exit)     | all                              |
| subset of {left, right}                | horizontal, off_centre, t, double_t, z |
| subset of {top, bottom}                | vertical, double_t, z            |
| {left, top}                            | l (tl), double_t, z              |
| {left, bottom}                         | l (bl), double_t, z              |
| {right, top}                           | l (tr), double_t, z              |
| {right, bottom}                        | l (br), double_t, z              |
| {left, right} + one of {top, bottom}   | double_t, z                      |
| 3 or 4 exits                           | double_t, z                      |

The existing stitch-failure fallback (rebuild all grids with `double_t`)
stays but should fire rarely once strategy selection is correct.

---

## Phase 2: Loops / shortcut passages (deferred)

When loop edges are added later, they will always be locked (key or gate).
Because the lock originates in the DAG, the challenge DAG remains acyclic
even though the world graph has a cycle.  The player can only traverse the
shortcut after acquiring the key — which is placed in a DAG-reachable
position determined before the lock is created.

---

## Phase 3: Multi-plane (deferred)

Multiple floors connected by staircases.  Requires staircase sprite (see
kb/findings.md), `EdgeType.STAIRCASE`, and `current_plane` in game.py.
Out of scope until the staircase sprite exists.

---

## Architecture changes

### levelgraph.py

**`LevelGraphBuilder`** — add support for intra-grid room-to-room edges:
a room can be connected to another specific room rather than always to the
corridor.  The playability invariant (prerequisites in already-reachable
nodes) must still hold: the parent room must be reachable before the child
room is added.

**`_super_grid_positions(n)`** — replace with `_world_graph(n, branch_prob,
rng)` that returns `(positions, edges)` for a spanning tree using the
algorithm above.  Unique positions guaranteed; adjacency with existing
non-parent grids silently skipped.

**`LevelGraphBuilder.start_next_grid()`** — add `source` parameter: branch
can originate from any already-placed corridor, not only `_current_corridor`.

**Post-stitch DAG validation** — new step after physical stitching: determine
which room (if any) owns each BORDER exit tile; re-run reachability analysis
routing through those rooms.  If a new solvability failure is found, retry
the grid layout before accepting the level.

### levellayout.py

**`_build_super_grid()`** — wire `required_sides` (already computed at
lines 1982–1987 but currently unused for strategy selection) into
`_pick_strategy()` per the coverage table above.

**Room-room adjacency** — when two rooms share a non-BORDER DAG edge, the
packing algorithm must place them adjacent (sharing a wall).  This is a new
constraint for intra-grid room chains and branches.

**`_layout_l()`** — new function implementing the L-shape corridor (two
perpendicular arms, bend at a freely chosen position, rooms in the large
open zone between the arms).

### levels.py

Add `branch_prob` to each Act 2 feature set using the table above.

---

## Open questions

1. **Post-stitch retry budget**: how many times should the layout retry a
   grid when post-stitch validation fails?  Retrying with `double_t` once is
   cheap; unlimited retries could loop.

2. **Exit / goal grid placement**: currently the last-placed grid holds the
   level exit.  With branching, this may be a short dead-end arm.  Should
   the exit instead be placed at the grid with the greatest BFS distance
   from the start?

3. **Intra-grid branching depth**: how many hops from the corridor before a
   room is considered "too deep"?  A chain of length 3+ creates a maze within
   a grid, which can be either interesting or frustrating.

4. **`branch_prob` tuning**: the table values are first-guesses; they will
   need adjustment after the first playtest at levels 15–20.

---

## Done when — Phase 0

- [ ] `poe test` passes
- [ ] Challenge graph supports room-to-room chains and branches within a grid
- [ ] Connected rooms are placed adjacent to each other in layout (no
      solvability failures from room-room edge stitching)
- [ ] L-shape corridor renders correctly in all 4 variants
- [ ] Dead-end corridor renders (single arm + tip room, no opposite exit)
- [ ] Post-stitch DAG validation catches and retries unsolvable stitch positions

## Done when — Phase 1

- [ ] `poe test` passes
- [ ] Hyper-grid has no duplicate coordinates; non-parent adjacency ignored
- [ ] Level 13 (3 grids): branching topology appears on some seeds (verified visually)
- [ ] Level 15 (5 grids): branching visible; player has real route choices
- [ ] Level 20 (10 grids): tree with multiple branch nodes and dead-end arms
- [ ] No generation failure — world graph + stitching never raises
- [ ] Strategy selection uses exit compatibility; `double_t` fallback fires rarely
