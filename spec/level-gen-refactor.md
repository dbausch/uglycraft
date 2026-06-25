# Level Generation Refactor: Constructive Transformations

## Status

- [ ] `LevelGraphBuilder` class in `levelgraph.py` — each `add_*` method maintains `_reachable`
- [ ] `generate()` replaced: uses builder, no retry loop
- [ ] `chain` layout strategy removed; `_find_connection_tile` failure is an error, not silent skip
- [ ] Block placement guaranteed-solvable by 1-push construction
- [ ] `enemy_eligible` flag set on nodes at graph-build time; runtime exclusion rules removed
- [ ] `validate_playability()` always returns `[]` on first try
- [ ] `validate_layout()` always returns `[]` on first try
- [ ] `validate_push_puzzles()` always passes on first try
- [ ] Retry loop removed from `_generate_act2()`
- [ ] Levels 11-20 playable via `poe run --level N`

---

## The Problem

The existing pipeline is random-generate → validate → retry. Solvability is checked
after the fact; failures are masked by the retry loop. Patches for enemy placement,
dead square detection, and block fallbacks have accumulated on top of a flawed
foundation. This spec replaces that approach with a pipeline where **every
transformation preserves solvability by construction**.

---

## Principle: Transformation Invariant

```
Challenge Sequence
      ↓  build via LevelGraphBuilder   invariant: graph is always solvable
Abstract Graph (LevelGraph)
      ↓  layout_graph()                invariant: every edge has a shared boundary
Positioned Graph (PlacedNode map)
      ↓  derive_walls() + place_items() invariant: puzzles solvable without BFS retry
Tile Grid (game dict)
```

The validators `validate_playability()`, `validate_layout()`, and
`validate_push_puzzles()` become **sanity checks that must always pass**. If they
ever fail it is a bug in the transformation, not bad luck.

---

## Transformation 1: Challenge Sequence → Abstract Graph

### `LevelGraphBuilder` API

```python
class LevelGraphBuilder:
    def __init__(self, rng):
        # Creates corridor node (is_start=True). self._reachable = {'corridor'}.

    def add_open_room(self, size=None, parent='corridor') -> str:
        # Attaches a new room via OPEN edge. Room joins _reachable. Always valid.

    def add_breakable_room(self, wall_type='stone', size=None, parent='corridor') -> str:
        # Attaches a new room via BREAKABLE edge. Always valid (player can break).

    def add_locked_room(self, colour, size=None, parent='corridor') -> str:
        # Attaches a new room via LOCKED edge.
        # Places key of `colour` in a room already in _reachable (not the new room).
        # New room joins _reachable. Valid by construction.

    def add_gated_room(self, gate_id, size=None, parent='corridor') -> str:
        # Attaches a new room via GATED edge.
        # Designates one reachable non-corridor, non-closet room as the puzzle room.
        # Marks that room with plate(gate_id) + block(1).
        # New room joins _reachable. Valid at graph level.

    def add_water_room(self, size=None, parent='corridor') -> str:
        # Attaches a new room via WATER edge.
        # Places 2 planks in a reachable room. Valid by construction.

    def add_treasures(self, count) -> None:
        # Distributes treasures across all rooms (including unreachable-until-solved).

    def add_materials(self, mat_types, count) -> None:
        # Distributes materials similarly.

    def add_enemies(self, count) -> None:
        # Distributes enemies across enemy_eligible rooms only.
        # enemy_eligible = ROOM or HALL size, no puzzle (blocks/plates), no flames.
        # Sets node.enemy_eligible = True. No runtime exclusion rules needed.

    def add_flames(self) -> None:
        # Marks one suitable room (ROOM or HALL, no puzzle) as has_flames = True.
        # Adds a treasure on the far side.

    def build(self) -> LevelGraph:
        # Returns the completed graph. assert graph.validate_playability() == [].
```

### Replacing `generate()` and `_assign_items()`

`LevelGraph.generate(feature_set, rng)` is replaced by a method that uses the
builder. The feature set maps to builder calls:

```python
@classmethod
def generate(cls, feature_set, rng=None):
    rng = rng or random.Random()
    b = LevelGraphBuilder(rng)
    edge_types = feature_set['edge_types']
    node_sizes = feature_set.get('node_sizes', [NodeSize.ROOM, NodeSize.HALL])
    room_count = rng.randint(*feature_set['room_count'])
    required = list(dict.fromkeys(edge_types))  # first occurrence of each type

    for i in range(room_count):
        size = rng.choice(node_sizes)
        et = required[i] if i < len(required) else rng.choice(edge_types)
        if et == EdgeType.OPEN:
            b.add_open_room(size=size)
        elif et == EdgeType.BREAKABLE:
            b.add_breakable_room(wall_type=rng.choice(['stone','wooden']), size=size)
        elif et == EdgeType.LOCKED:
            b.add_locked_room(rng.choice(['red','blue','green']), size=size)
        elif et == EdgeType.GATED:
            b.add_gated_room(f'gate_{i}', size=size)
        elif et == EdgeType.WATER:
            b.add_water_room(size=size)

    b.add_treasures(rng.randint(*feature_set['treasure_count']))
    b.add_materials(feature_set.get('material_types', []),
                    rng.randint(*feature_set.get('material_count', (4,8))))
    b.add_enemies(rng.randint(*feature_set.get('enemy_count', (1,3))))
    if feature_set.get('has_flames'):
        b.add_flames()
    return b.build()
```

The free function `_assign_items()` is deleted.

---

## Transformation 2: Abstract Graph → Positioned Graph

### Guarantee: every edge has a shared boundary tile

For the star topology (all rooms connect to the corridor, no room-to-room edges),
the horizontal, vertical, and off_centre strategies already guarantee adjacency:
- The corridor spans the full grid width (horizontal) or height (vertical).
- Every room is packed into a band directly adjacent to the corridor.
- Therefore the wall tile between any room and the corridor always exists.

The `chain` strategy does NOT maintain this guarantee for star topology: it places
rooms in a 2D grid by position, ignoring which rooms are graph-connected. It is
**removed**.

### Making violations visible

In `derive_walls()`, the current code does:

```python
conn = _find_connection_tile(pa, pb, walls)
if conn is None:
    continue   # ← silently drops the edge
```

This is replaced by:

```python
conn = _find_connection_tile(pa, pb, walls)
if conn is None:
    raise ValueError(
        f"Edge {edge.node_a!r}<->{edge.node_b!r} has no shared boundary tile")
```

`validate_layout()` remains as an end-to-end sanity check.

---

## Transformation 3: Positioned Graph → Tile Grid + Items

### Block placement: guaranteed-solvable by 1-push construction

After placing the pressure plate at `(px, py)`, find **1-push positions**: tiles
`(bx, by)` where:
- The block starts at `(bx, by) = plate + D` for some direction `D = (dc, dr)`.
- The player stands at `plate + 2*D`.
- Both `plate + D` and `plate + 2*D` are passable (not permanent walls, not the
  plate tile, not already occupied).

Place the block at any such position. This guarantees the puzzle is solvable in
exactly one push, so `validate_push_puzzles()` cannot fail.

If no 1-push position exists (plate is in an unreachable corner — layout bug),
`derive_walls()` has already errored. This case does not need a fallback.

Dead squares are still computed and stored for the visual floor indicator, but
they no longer control block placement.

### Enemy placement: graph-time attribute, no runtime rules

`LevelGraphBuilder.add_enemies()` sets a node-level attribute `enemy_eligible`
at graph-build time. Eligible rooms are: ROOM or HALL size, no puzzle
(blocks/plates on the node), no flames. The item placer reads `node.enemies`
directly; no runtime exclusion rules are needed in `levellayout.py`.

The existing exclusion conditions (corridor, border-adjacent, puzzle room, flame
room) collapse into: "did the builder put an enemy on this node?"

---

## Files Changed

| File | Change |
|---|---|
| `levelgraph.py` | Add `LevelGraphBuilder`; rewrite `LevelGraph.generate()`; delete `_assign_items()` |
| `levellayout.py` | Remove `chain` from `STRATEGIES`; raise on `None` connection; replace stochastic block placement with 1-push construction; simplify enemy placement |
| `levels.py` | Remove retry loop from `_generate_act2()`; feature sets unchanged |

Kept intact: `LevelGraph`, `Node`, `Edge`, `PlacedNode`, `build_tile_owner()`,
`derive_walls()`, `validate_layout()`, `validate_playability()`,
`validate_push_puzzles()`, `_sokoban_bfs()`, `_compute_dead_squares()`,
`_generate_flame_jets()`, `_place_items_in_room()`.

---

## Manual Verification

There is no automated test suite for Python/UGLYCRAFT. Verification:

1. After each step, run `poe run --level N` for N = 11 through 20 and confirm each
   level loads without ValueError and is playable.
2. Check that `validate_playability()`, `validate_layout()`, and
   `validate_push_puzzles()` never raise during import of `levels.py`.
3. Run `poe run` several times (fresh seeds) to confirm variety is maintained.
4. The retry loop counter (if temporarily left as a debug log) should show 0
   retries for every level.

---

## Done when

- [ ] `LevelGraphBuilder` exists and `generate()` uses it — commit ___
- [ ] `chain` removed, `None`-connection raises — commit ___
- [ ] 1-push block placement in place — commit ___
- [ ] `enemy_eligible` attribute replaces runtime exclusion rules — commit ___
- [ ] Retry loop removed from `_generate_act2()` — commit ___
- [ ] `poe run --level 11` through `--level 20` each load and play correctly — user confirmed ___
