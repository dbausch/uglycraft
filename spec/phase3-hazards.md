# Phase 3: Water Streams and Flame Jets

## Status

- [ ] Water stream tiles (visual, directional flow)
- [ ] Player carried by water (visible tile-by-tile animation)
- [ ] Bridge crafting (2 planks, covers 1 water tile)
- [ ] Pushable blocks into water (permanent stepping stone)
- [ ] WATER edge type in graph system
- [ ] Flame jet tiles (rhythmic on/off, 2s cycle)
- [ ] Shield protects against flames
- [ ] Flame source blockable by walls/blocks
- [ ] Flame hazard as room property in graph system
- [ ] Levels 14-15 feature sets
- [ ] Sprites: water, bridge, flames

---

## Water Streams

### Graph model

New edge type: `WATER` — a passage between two rooms blocked by a stream.
The player must place a bridge (2 planks) or push a block to cross.

Like GATED edges require a plate+block, WATER edges require planks in
inventory. The playability validator checks that planks are reachable
from the start side.

### Game mechanics

Water tiles are defined per-room as a list of `(col, row, flow_dcol, flow_drow)`
tuples. They act as impassable floor (like a wall) until bridged.

When the player steps onto an unbridged water tile:
- The player is carried tile-by-tile in the flow direction
- Movement is visible (one tile per game tick)
- Continues until hitting a non-water tile or a wall
- Player ends up at the last water tile (the drain)
- Not lethal — just repositions

Bridging: place a bridge item on a water tile (SPACE with bridge selected).
The water tile becomes passable floor with a bridge sprite.

Pushing a block into water: the block fills the water tile permanently
(stepping stone), same as bridging.

### Level data format

```python
'water_tiles': [(col, row, flow_dc, flow_dr), ...]
'bridged_tiles': set()  # grows as player places bridges
```

## Flame Jets

### Graph model

Flame jets are a **room property**, not an edge type. A room can have
flame sources that periodically fill tiles with fire.

The graph generator adds flame jets to rooms in levels 15+.

### Game mechanics

A flame source is at a fixed position. It fills a line of tiles in a
direction (like a wall segment). The source cycles on/off with a period
(default 2 seconds on, 2 seconds off).

When active: flame tiles are hazardous. Contact = catch (life lost),
same as enemy contact. Shield protects — walking through active flames
with shield active is safe.

A flame source can be permanently blocked by placing a wall or pushing
a block onto the source tile.

### Level data format

```python
'flame_jets': [
    {'source': (col, row), 'dir': (dc, dr), 'length': 3,
     'on_ms': 2000, 'off_ms': 2000},
    ...
]
```

## Placement rules

These rules govern how flame jets and water edges are distributed by the
level-graph builder.  They are structural invariants that must hold for every
generated level.

### Flame room rules

**R-F1 — No fire and enemies in the same room.**
A node with `has_flames = True` must have no enemies, and a node that already
has enemies must not receive `has_flames`.  `add_flames()` filters out nodes
with enemies; `add_enemies()` filters out nodes with `has_flames`.

**R-F2 — Flame rooms are never behind a WATER edge.**
`add_flames()` excludes any node that has an incident WATER edge.  This
guarantees the entry to the flame room is a plain dry doorway, making the
BFS for near/far tile splitting reliable.

**R-F3 — The jet is never placed at the entry row or column.**
`_generate_flame_jets()` receives the entry tile and skips any jet row (for
horizontal jets) or jet column (for vertical jets) that coincides with the
entry tile's row or column.  This ensures the entry tile is never inside a jet,
so the BFS flood from the entry tile always has a valid starting position.

**R-F4 — Award items in a flame room are only on the far side of the jet.**
Far side = tiles not reachable from the entry tile when jet tiles are treated
as walls (BFS flood).  `_place_items_in_room()` skips `node.treasures` for
flame rooms entirely; the far-tiles pass in `build_level_dict()` places exactly
one treasure per jet into `jet['far_tiles']`.

**R-F5 — Flame placement happens before enemy distribution.**
`LevelGraph.generate()` calls `add_flames()` before `add_treasures()`,
`add_materials()`, and `add_enemies()`.  This prevents enemy saturation from
filling every eligible room and leaving no candidates for flame placement.

### Water edge rules

**R-W1 — Each WATER edge supplies exactly 2 planks on the player's side.**
`add_water_room()` places two plank items.  Each plank is placed independently
in a room chosen from `_dry = [r for r in _reachable if r not in _water_rooms]`.
This prevents circular dependencies where planks land behind an earlier water
edge.

## Feature sets

Level 14: + WATER edge type, planks, bridge crafting
Level 15: + flame jets, shield-vs-flames

## Done when

- [ ] Water tiles render with directional flow animation
- [ ] Player is carried by water visibly
- [ ] Bridge covers water tile, player can walk on it
- [ ] Block pushed into water creates stepping stone
- [ ] Flame jets cycle on/off with visible fire sprites
- [ ] Contact with active flames = catch
- [ ] Shield protects against flames
- [ ] Wall/block on flame source permanently blocks it
- [ ] Levels 14-15 generate with water/flame features
