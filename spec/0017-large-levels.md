# Large Levels: Roguelike Scale, Branching Topology, Multi-Plane

## Status

- [ ] World graph supports branching (one grid connects to 2+) and loops
- [ ] Level configs scaled up: 5 grids at level 11, growing to 20–30+ by level 20
- [ ] Grid arrangement algorithm places grids on a 2D meta-grid
- [ ] Multi-plane: levels 17–20 have 2–3 planes (floors) connected by stairs

---

## Vision

Act 2 should feel like a roguelike dungeon — large, non-linear, full of
decisions about where to go next.  The current linear chain of grids (A→B→C)
must become a proper graph: branches, loops, dead-ends, and eventually
multiple vertical planes (floors connected by stairs).

---

## World graph

A **world graph** is the meta-level structure: nodes are grids; edges are
border transitions between grids.  Currently the world graph is always a
path (linear chain).  This spec upgrades it to an arbitrary connected graph.

### Topology types

| Type      | Description                                                |
|-----------|------------------------------------------------------------|
| path      | A → B → C (current)                                       |
| branch    | A connects to B and C; player chooses direction            |
| loop      | A → B → C → A; player can return to earlier grids         |
| tree      | A tree of depth 2–3; multiple dead-end branches            |
| web       | Dense graph with multiple loops                           |

All types are mixed within a single level by the world graph generator.

### Grid exits

Each grid has 4 potential exits: `top`, `bottom`, `left`, `right`.  An exit
is a BORDER edge connecting two grids at one of their shared border walls.
A grid can have more than one exit in the same direction only if the two
exits lead to different grids (they'd be at different row/col positions
along that border).

In practice, aim for 1–2 exits per grid face.  A grid with exits on 3 or 4
faces is a hub; 1 exit is a dead-end arm.

### World graph generation

```
1.  Pick a target grid count N for the level.
2.  Start with one grid (the start grid).
3.  Repeat until N grids placed:
      a. Pick a placed grid that still has free faces.
      b. Pick a free face.
      c. Place a new grid on that face (or, with probability p_loop,
         connect to an already-placed grid that has a matching free face).
4.  Ensure start grid is reachable from all others (always true since
    we grew from the start).
5.  Assign exit_side/entry_side for each BORDER edge based on which
    face was connected.
```

`p_loop` (probability of creating a loop instead of a new grid) increases
with N and with the current loop count — more loops in larger levels.

Suggested: `p_loop = 0.1 + 0.02 * current_loop_count` (capped at 0.4).

### Spatial layout

For display on the world map (and for stitching to work), each grid needs a
2D position on a meta-grid.  The meta-grid is a logical 2D array of grid
slots; each slot holds exactly one grid.

Growing algorithm: track occupied slots; when adding a grid on face F of
grid G at position (gx, gy), place the new grid at (gx+dx, gy+dy) where
(dx, dy) = face direction.  If that slot is already occupied (loop case),
record the BORDER edge between the two grids instead.

---

## Grid counts by level

| Level | Grid count (target) | World graph style           |
|-------|---------------------|-----------------------------|
| 11    | 5                   | path or simple tree         |
| 12    | 8                   | tree with 1–2 branches      |
| 13    | 12                  | tree + 1 loop               |
| 14    | 15                  | tree + 2 loops              |
| 15    | 20                  | web                         |
| 16    | 25                  | web                         |
| 17    | 30 (2 planes)       | web per plane + stairs      |
| 18    | 40 (2 planes)       | web per plane + stairs      |
| 19    | 50 (3 planes)       | web per plane + stairs      |
| 20    | 60 (3 planes)       | web per plane + stairs      |

Grid counts are targets; the generator may produce ±2 depending on the
random walk outcome.

---

## Multi-plane levels

A **plane** is one floor of the dungeon.  Levels 17–20 have 2–3 planes.
Each plane is a world graph of grids.  Planes are connected by **staircase
pairs**: one staircase in a grid on plane N leads to a staircase in a grid
on plane N+1.

### Staircases

- A staircase occupies one floor tile in a grid (at a specific col, row).
- It is distinct from a door or border exit: it leads to a different plane,
  not an adjacent grid on the same plane.
- The destination staircase is in a randomly chosen grid on the target plane
  (not necessarily adjacent spatially).
- Staircase sprite: already noted as a future feature in findings/kb.

### Plane generation

```
1.  Generate plane 0 (the start plane) with its world graph.
2.  For each additional plane p:
      a. Generate world graph for plane p.
      b. Pick a grid on plane p-1 to place the upward staircase.
      c. Pick a grid on plane p to place the downward staircase.
      d. Record staircase pairs.
3.  Player starts on plane 0.
```

---

## Architecture changes

### levelgraph.py

- `LevelGraph.generate()` currently produces a flat star-topology graph for
  one grid.  This does not change — each grid's internal room graph is still
  a star.
- No changes needed here.

### levellayout.py / build_level_dict

Currently `build_level_dict(..., grid_count=N)` builds a linear chain.
Replace the chain builder with a **world graph builder**:

```python
def build_world_graph(feature_set, rng, n_grids, p_loop=None):
    """Return a list of (corridor_name, BORDER edges) describing the meta-graph."""
    ...

def build_level_dict_v2(feature_sets, rng, strategies, world_graph):
    """Build all grids and stitch them according to the world graph."""
    ...
```

The existing `_stitch_ok` / stitch logic stays but must handle arbitrary
exit directions (grids can connect via top/bottom as well as left/right).

### levels.py

Feature sets gain a `'world_style'` key describing the topology target:
`'path'`, `'tree'`, `'web'`.  The world graph builder uses this as a hint.

### game.py

Multi-plane transitions require a new game state: `current_plane`.
Staircase tiles trigger a plane switch (like grid exits trigger a grid
switch).  The HUD may show the current plane number.

---

## Open questions

1. **Room counts per grid on large levels**: with 60 grids each having 6–10
   rooms, a level 20 has 360–600 rooms.  Is that the right scale, or should
   individual grids have fewer rooms on large levels?

2. **Staircase sprite**: already on the backlog (kb/findings.md).  Needed
   before multi-plane can be playable.

3. **World map / minimap**: with 30–60 grids, players need some way to track
   where they've been.  Out of scope for this spec but worth noting.

4. **p_loop tuning**: the formula `p_loop = 0.1 + 0.02 * loop_count` is a
   first guess.  Needs playtesting.

---

## Done when

- [ ] `poe test` passes
- [ ] Level 11 generates with 5 grids, non-linear branching topology visible
- [ ] Level 15 generates with ~20 grids, multiple loops navigable
- [ ] Level 17 generates with 2 planes; staircase carries player between them
- [ ] Level 20 generates with 3 planes and ~60 total grids
