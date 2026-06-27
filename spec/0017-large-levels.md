# Large Levels: Branching Topology and Multi-Plane

## Status — Phase 1 (branching world graph)

- [ ] World graph supports branching (one grid → 2+ successors) and loops
- [ ] World graph grown as spanning tree, then loop edges added on top
- [ ] Each grid's layout strategy chosen to match its required exits
- [ ] Level 11: 1 grid (trivially linear)
- [ ] Level 12–14: small trees, no/few loops
- [ ] Level 15+: branching + loops visible; exploration is non-linear

## Status — Phase 2 (multi-plane, out of scope until staircase sprite exists)

- [ ] STAIRCASE edge type connecting two grids on different floors
- [ ] `current_plane` game state in game.py
- [ ] Staircase sprite (prerequisite — see kb/findings.md)

---

## Vision

Act 2 should feel like a dungeon, not a corridor chain.  From level 13
onward the player encounters branch points — junctions where they must
choose left or right, up or down.  At level 15+ loops appear: you can
circle back to earlier grids, reducing dead-end backtracking and rewarding
a player who remembers the map.

Each 30×16 grid is unchanged in size.  The difference is in how many grids
exist and how they connect.

---

## World graph

A **world graph** is the meta-level structure:

- **Nodes**: corridor nodes, one per 30×16 grid
- **Edges**: BORDER edges — transitions through a shared border wall

Each corridor node has a 2D position `(meta_col, meta_row)`.  BORDER edges
only exist between **spatially adjacent** nodes (Manhattan distance 1).
This is not a policy choice — it is a hard constraint of the stitching
mechanism: two grids share a border wall only when they are adjacent.

### Vocabulary

| Term           | Definition                                               |
|----------------|----------------------------------------------------------|
| dead-end grid  | 1 exit (leaf node in world graph)                        |
| pass-through   | exactly 2 exits (current behavior)                       |
| branch grid    | 3 or 4 exits (hub; multiple routes diverge here)         |
| loop edge      | BORDER edge that closes a cycle (not part of span. tree) |

---

## Grid counts by level

Level N has exactly N−10 grids.

| Level | Grids | branch_prob | loop_count | Notes                       |
|-------|-------|-------------|------------|-----------------------------|
| 11    | 1     | 0           | 0          | trivial — single grid       |
| 12    | 2     | 0           | 0          | always linear               |
| 13    | 3     | 0.20        | 0          | first branching opportunity |
| 14    | 4     | 0.25        | 0          |                             |
| 15    | 5     | 0.30        | 1          | first loop                  |
| 16    | 6     | 0.30        | 1          |                             |
| 17    | 7     | 0.35        | 1          | multi-plane here in Phase 2 |
| 18    | 8     | 0.35        | 2          |                             |
| 19    | 9     | 0.40        | 2          |                             |
| 20    | 10    | 0.40        | 2          | full roguelike scale        |

`branch_prob` and `loop_count` are first-guess values; playtesting will tune
them.  The grid count is fixed (not random).

---

## World graph generation algorithm

**Input**: N grids, `branch_prob` p, `loop_count` L.

### Step 1 — Place the start grid

Place grid 0 at position (0, 0).
`placed = {(0,0): 0}`, `frontier = [0]`.

### Step 2 — Grow spanning tree

Repeat until `len(placed) == N`:

1. Pick a random grid G from `frontier` (uniform random — neither pure BFS
   nor pure DFS; gives varied tree shapes).
2. Shuffle the 4 cardinal directions.
3. For each direction D (in shuffled order):
   - Compute neighbor position P = pos(G) + D.
   - If P is unoccupied and `len(placed) < N`: place new grid K at P, record
     BORDER edge (G→K, exit_side=D), add K to `frontier`, then:
     - With probability (1 − p): **stop** (only one new grid per turn).
     - With probability p: **continue** to the next direction, possibly
       adding a second branch from G in the same turn.
4. If no direction yielded a new grid: remove G from `frontier`.

After this step the world graph is a spanning tree.  The start grid is the
root; dead-end grids are leaves.

### Step 3 — Add loop edges

Collect all adjacent pairs of placed grids that do **not** already share a
BORDER edge.  Shuffle the list.  Pick the first L pairs and add a BORDER
edge to each.  If fewer than L valid pairs exist, add as many as possible
and continue without error.

---

## Exit compatibility and strategy selection

A grid's **required exits** are the faces (left, right, top, bottom) that
have a BORDER edge.  The chosen layout strategy must guarantee a floor tile
at each required face's border, otherwise stitching fails.

### Coverage table

| Strategy    | Left | Right | Top | Bottom |
|-------------|:----:|:-----:|:---:|:------:|
| `horizontal`  | ✓   | ✓     |     |        |
| `vertical`    |     |       | ✓   | ✓      |
| `off_centre`  | ✓   | ✓     |     |        |
| `t`           | ✓   | ✓     | ½   | ½      |
| `double_t`    | ✓   | ✓     | ✓   | ✓      |
| `z`           | ✓   | ✓     | ✓   | ✓      |
| `l`           | *   | *     | *   | *      |

**`t` (½)**: the spine guarantees left+right; the stem extends to **one** of
{top, bottom} at random.  `t` cannot be relied upon for a specific third
side — it may or may not reach top or bottom.  Use it only for grids needing
exactly {left, right}.

**`l`**: covers 2 specific borders depending on which variant is chosen;
unsuitable for grids with 3+ exits.  Safest to restrict `l` to dead-end
grids (1 exit only) in the feature set.

### Selection rule

After the world graph is built and each grid's required exits are known:

```python
def _pick_strategy(exits, available, rng):
    compatible = [s for s in available if _covers(s, exits)]
    return rng.choice(compatible) if compatible else 'double_t'
```

`_covers(s, exits)` table:

| Required exits                                  | Compatible strategies            |
|-------------------------------------------------|----------------------------------|
| ∅                                               | all                              |
| subset of {left, right}                         | horizontal, off_centre, t, double_t, z |
| subset of {top, bottom}                         | vertical, double_t, z            |
| {left, right} + one of {top, bottom}            | double_t, z                      |
| 3 or 4 exits, or any mix of both axes           | double_t, z                      |

The existing stitch-failure fallback (rebuild all grids with `double_t`)
stays, but should fire rarely once strategy selection is correct.

---

## Architecture changes

### levelgraph.py

**`_super_grid_positions(n)`** — replaced by a new function:

```python
def _world_graph(n, branch_prob, loop_count, rng):
    """Return (positions, tree_edges, loop_edges).

    positions: list[(meta_col, meta_row)], index = grid index
    tree_edges: list[(grid_a, grid_b, exit_side, entry_side)]
    loop_edges: list[(grid_a, grid_b, exit_side, entry_side)]
    """
```

**`LevelGraphBuilder.start_next_grid()`** — add a `source` parameter so
branches can be added from any already-placed corridor:

```python
def start_next_grid(self, super_col, super_row, exit_side,
                    source=None, ...)
# source defaults to _current_corridor when None
```

**`LevelGraphBuilder.add_border_loop(corridor_a, corridor_b, exit_side, ...)`**
— new method.  Creates a BORDER edge between two existing corridors without
adding a new corridor node (for loop edges).

**`LevelGraph.generate()`** — updated call sequence:

```
1. Call _world_graph(N, branch_prob, loop_count, rng).
2. BFS from grid 0; for each non-root grid: call start_next_grid(source=parent).
3. For each loop edge: call add_border_loop(a, b, ...).
4. Distribute rooms round-robin as today.
```

### levels.py

Add `branch_prob` and `loop_count` to each Act 2 feature set using the
values from the grid-count table above.

### levellayout.py

**`_build_super_grid()`** — `required_sides` is already computed (lines
1982–1987) but currently not used for strategy selection.  Wire it:

```python
for corridor in corridor_order:
    exits = required_sides[corridor]
    strategy = _pick_strategy(exits, strategies, rng)
    d = build_level_dict(sub, rng=rng, strategies=[strategy], grid_count=1)
    ...
```

---

## Phase 2: multi-plane (future)

Multi-plane levels have 2+ floors connected by staircases.  A staircase is
a floor tile that, when stepped on, transitions the player to a different
floor — a different world graph entirely.

Deferred requirements:
- Staircase sprite (prerequisite; tracked in kb/findings.md)
- `EdgeType.STAIRCASE` — new edge type; not a border wall connection
- `current_plane` state in game.py
- Plane generation: each plane has its own world graph; a staircase pair
  links one grid on plane P to one grid on plane P+1

Not scoped here.  Revisit when the staircase sprite exists.

---

## Open questions

1. **Bounded meta-grid**: should the generator cap the bounding box (e.g.,
   5×5 cells) to keep levels compact?  Uncapped growth produces very long
   arms; a cap keeps the map denser and navigation shorter.

2. **Exit / goal placement**: currently grid 0 = start, last grid = exit.
   With branching the "last grid" is the last one added (a dead-end arm),
   which is interesting.  Alternative: place the exit at the grid with the
   greatest BFS distance from the start.

3. **Loop edge barriers**: same barrier options as tree edges (locked/gated/
   open)?  Or always open, since secondary paths should not block progress?

4. **`branch_prob` and `loop_count` tuning**: first-guess values; needs
   playtesting especially at levels 15–20.

---

## Done when — Phase 1

- [ ] `poe test` passes
- [ ] Level 13 (3 grids): branching topology appears on some seeds (verified by visual inspection)
- [ ] Level 15 (5 grids): branching + 1 loop present in most runs; player has real choices
- [ ] Level 20 (10 grids): web-like topology; multiple arms and loops visible (verified by inspection)
- [ ] No level fails to generate — world graph + stitching never raises
- [ ] Strategy selection uses exit compatibility; `double_t` fallback fires rarely
