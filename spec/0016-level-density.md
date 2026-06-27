# Level Density: Room Content Guarantee

## Status

- [ ] Every room has at least one award item or challenge

---

*Grid count progression has been superseded by spec 0017 (large levels /
roguelike architecture), which specifies a much more ambitious scale.*

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

**Open question — "reachable side" of a gated edge**: the current graph
does not explicitly tag which side the player approaches from.  May need
to check graph traversal order from the start node, or tag edges at
`add_gates` time.

Files: `levelgraph.py` — `LevelGraph.generate()`, new helpers.

---

## Done when

- [ ] `poe test` passes
- [ ] No room in any Act 2 level is content-empty (verified by visual
      inspection of several generated levels)
