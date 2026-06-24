# Level Graph System

## Status

- [ ] Graph model: Node, Edge, LevelGraph classes (`levelgraph.py`)
- [ ] Graph generation from feature sets
- [ ] Playability validation (graph-level BFS)
- [ ] Item assignment (keys, blocks, plates placed to satisfy playability)
- [ ] Layout algorithm: place nodes onto 30×16 grids (`levellayout.py`)
- [ ] Wall derivation from layout (negative space = walls)
- [ ] Game-format output (same dict format as `game.py` expects)
- [ ] Level 11 generated and playable
- [ ] Levels 12-13 generated with keys/doors/gates
- [ ] Staircase edge type for multi-grid levels
- [ ] Validation at import time
- [ ] Multiple restarts produce visibly different layouts

---

## Overview

A level is a graph. Nodes are rooms, edges are connections. The 30×16 tile
grid is derived from the graph by a layout algorithm. Validation operates on
the graph, not the grid. Random generation produces random graphs constrained
by per-level feature sets.

## Design Principles

1. **The graph is the level.** The grid is a rendering concern.
2. **Edges are the only passages.** Two nodes that share an edge have
   exactly one passage between them — the edge's connection tile. The
   wall between them is otherwise complete and unbroken. Two nodes with
   no edge between them have no passage at all, even if they are
   physically adjacent on the grid. This is the fundamental invariant
   that makes graph-level reasoning (playability, locks, gates) correct:
   the physical layout faithfully represents the graph topology.
3. **Playability is a graph property.** For every not-yet-passable edge,
   the condition that makes it passable must be achievable from the start.
   Because edges are the only passages, validating the graph guarantees
   the grid layout is also valid.
4. **Feature sets define levels.** Each level specifies which edge types,
   node sizes, and architectural features the generator may use.
5. **No hand-authored coordinates.** The layout algorithm places nodes and
   derives walls automatically. Items are placed within their room's floor.
6. **Output is unchanged.** The game engine receives the same dict format.
   No changes to `game.py`, `rooms.py`, or any rendering code.

## Graph Model

### Nodes

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Unique identifier within the level |
| `size` | enum | `CLOSET`, `ROOM`, `HALL`, `CORRIDOR` |
| `items` | list | Treasures, materials, keys, blocks, plates, enemies |
| `is_start` | bool | Player starts here |

Enemies belong to a node and **never leave their room**. The game engine
confines each enemy's movement to the floor tiles of its owning node.
This requires a **tile ownership map**: every floor tile knows which
graph node it belongs to. The layout produces this map alongside the
wall dict. The game uses it to constrain enemy pathfinding — an enemy's
BFS or greedy movement only considers tiles belonging to its room.

**Spawn distance**: enemies must start at least 10 tiles (BFS distance)
from the player. The layout's item placement must enforce this. After
a catch, the respawn distance is also 10 tiles (currently 8 in Act 1;
Act 2 raises it).

**Player spawn room**: the player's start node must be large enough to
have at least one floor tile ≥10 BFS tiles from any enemy in that room.
If a room is too small for both the player and an enemy at safe
distance, it must not contain enemies — or the player must start in a
different room. The graph generator enforces this: the start node never
has enemies if its size category is too small (CLOSET).

**Enemy behaviour depends on whether the player is in the same room:**
- **Same room**: chase the player (BFS/greedy, as in Act 1).
- **Different room**: wander randomly within the room. Each movement
  tick, pick a random passable adjacent tile within the room and step
  there (or stay put). This prevents enemies from clustering at the
  doorway waiting for the player to enter.

Size ranges (width × height of floor area):
- `CLOSET`: 3-4 × 3-4
- `ROOM`: 5-8 × 4-6
- `HALL`: 8-12 × 5-8
- `CORRIDOR`: 8-20 × 2-3

### Edges

| Field | Type | Description |
|-------|------|-------------|
| `node_a` | str | First node name |
| `node_b` | str | Second node name |
| `edge_type` | enum | `OPEN`, `BREAKABLE`, `LOCKED`, `GATED`, `STAIRS` |
| `params` | dict | `key_colour` for LOCKED, `gate_id` for GATED, etc. |

### Playability Rule

For each edge E of type T, the condition to traverse E must be satisfiable
from the player's reachable set without crossing E:

- `OPEN`: always passable
- `BREAKABLE`: always passable (player can break walls)
- `LOCKED(colour)`: a key of `colour` is reachable without crossing E
- `GATED(gate_id)`: a plate with `gate_id` AND a pushable block are both
  reachable without crossing E
- `STAIRS`: always passable (walk onto staircase tile)

## Generation Pipeline

```
Feature sets → Graph → Items → Validate → Partition → Layout → Walls → Output
```

1. **Generate graph**: corridor backbone + rooms attached with allowed edge
   types
2. **Assign items**: treasures, materials distributed; keys/blocks/plates
   placed to satisfy playability
3. **Validate**: BFS from start node through progressively opened edges
4. **Partition**: split into grid groups if needed; cross-grid edges become
   border exits or staircases
5. **Layout**: arrange nodes spatially within 30×16, tight packing.
   Every pair of nodes must be separated by at least one tile of wall
   on every shared boundary. No two rooms may touch directly — there
   is always wall between them.
6. **Derive walls**: floor = room tiles; wall = everything else (reinforced).
   For each edge in the graph, exactly one wall tile on the shared
   boundary is converted to the edge's connection type (doorway, stone,
   locked door, gate). All other shared-boundary tiles remain wall.
   This guarantees the edge is the only passage between the two rooms.
7. **Output**: game-format dict

## Level Feature Sets

### Gameplay features

| Level | Allowed edge types | Allowed items |
|-------|-------------------|---------------|
| 11 | OPEN, BREAKABLE | treasures, materials, rocks |
| 12 | + LOCKED | + keys |
| 13 | + GATED | + pushable blocks, pressure plates |
| 14+ | (per spec/act2-beyond-the-vault.md) | |

### Architectural features

| Level | Allowed node sizes | Grid count | Shapes |
|-------|-------------------|------------|--------|
| 11-12 | ROOM, HALL, CORRIDOR | 1 | rectangular |
| 13-14 | + CLOSET | 1 | rectangular |
| 15-16 | + L-shaped rooms | 2 (staircases) | rectangular + L |
| 17+ | all | 2-3 | all |

### Difficulty parameters

| Parameter | Description |
|-----------|-------------|
| `room_count` | range, e.g. (4, 6) |
| `enemy_count` | range |
| `treasure_count` | range |
| `material_budget` | total materials to distribute |

## Files

| File | Role |
|------|------|
| `levelgraph.py` | Node, Edge, LevelGraph, generation, validation |
| `levellayout.py` | Layout algorithm, wall derivation, game-format output |
| `levels.py` | Feature set definitions, `generate_act2_levels()` |

## Layout Invariant Checks

After layout and wall derivation, the following must hold on the grid:

1. **Separation**: for every pair of nodes (whether or not they share an
   edge), their floor tiles are never adjacent without a wall between them.
   No floor tile of node A is cardinally adjacent to a floor tile of node B.
2. **Single passage**: for every edge in the graph, there is exactly one
   non-wall tile on the shared boundary. That tile is the connection point.
3. **No unintended passages**: for every pair of nodes with NO edge, there
   is no non-wall tile on their shared boundary. The wall is complete.
4. **Items inside rooms**: every placed item (treasure, material, key,
   block, plate, enemy) is on a floor tile of its owning node.
5. **Player start on floor**: the player start tile is floor.

If any check fails, the layout is invalid and must be regenerated.

## Done when

- [ ] `levelgraph.py` generates valid graphs from feature sets
- [ ] Playability validation catches all unreachable/bypassed items
- [ ] `levellayout.py` produces tight-packed floor plans on 30×16 grids
- [ ] Layout invariant: edges are the only passages between rooms (unit-tested)
- [ ] Generated levels are playable in `poe run --level N`
- [ ] Restarting the game produces different layouts
- [ ] Levels 1-10 remain byte-identical
- [ ] No changes to `game.py`, `rooms.py`, or rendering code
