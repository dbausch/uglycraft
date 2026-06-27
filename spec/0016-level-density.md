# Level Density: Grid Count Progression and Room Content Guarantee

## Status

- [ ] Grid count increases by 1 per level starting at level 12
- [ ] Every room has at least one award item or challenge

---

## Grid count progression

### Current

| Levels  | Grid count |
|---------|------------|
| 11–12   | 1          |
| 13–16   | 2          |
| 17–20   | 3          |

### New

| Level | Grid count |
|-------|------------|
| 11    | 1          |
| 12    | 2          |
| 13    | 3          |
| 14    | 3          |
| 15    | 4          |
| 16    | 4          |
| 17    | 5          |
| 18    | 5          |
| 19    | 5          |
| 20    | 5          |

The pattern is +1 per level from 12–17, then capped at 5.  Adjust the cap
if 5 grids turns out too much or too little during play testing.

Files: `levels.py` — `feature_sets` list, `'grid_count'` entries.

---

## Room content guarantee

### Problem

Some rooms end up with no treasure, no materials, no key, and no
challenge.  Empty rooms feel like pointless dead-ends.

### Rule

Every non-corridor room in the generated graph must have **at least one**
of the following:

| Content type | Examples                                       |
|--------------|------------------------------------------------|
| Award item   | treasure gem, material (rocks/metal), key      |
| Challenge    | gated exit (push puzzle on the room's side),   |
|              | planks to collect (WATER edge accessible from  |
|              | this room)                                     |

"Gated exit on the room's side" means the room is the reachable side of a
GATED edge — the player can reach the push puzzle box from this room.

### Implementation

Add a post-processing step in `LevelGraph.generate()`, called after all
`add_*` calls complete, that audits each room node:

```python
def _ensure_content(self):
    for name in self._rooms:          # all non-corridor room nodes
        if not self._has_content(name):
            self._add_treasure(name)  # place one treasure directly
```

`_has_content(name)` returns True if the node already has:
- `len(self._node_treasures.get(name, [])) > 0`, OR
- `len(self._node_materials.get(name, [])) > 0`, OR
- `name in self._node_keys`, OR
- `name in self._node_planks`, OR
- any edge from `name` is GATED and `name` is the reachable side

`_add_treasure(name)` adds one treasure coin to `self._node_treasures[name]`.

Files: `levelgraph.py` — `LevelGraph.generate()`, new helpers.

---

## Open questions

1. **Grid count cap**: is 5 grids the right ceiling, or should levels 19–20
   go higher (6)?  Can only be answered by playing.

2. **"Reachable side" of a gated edge**: push puzzles are on the reachable
   side of the gate (the player pushes the box from outside the locked room).
   The current graph does not explicitly tag which side is reachable.  May
   need to check the graph traversal order or tag edges at `add_gates` time.

---

## Done when

- [ ] `poe test` passes
- [ ] Level 12 generates with 2 grids; level 13 with 3; level 15 with 4
- [ ] No room in any Act 2 level is content-empty (verified by visual inspection
      of several generated levels)
