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
2. **Playability is a graph property.** For every not-yet-passable edge,
   the condition that makes it passable must be achievable from the start.
3. **Feature sets define levels.** Each level specifies which edge types,
   node sizes, and architectural features the generator may use.
4. **No hand-authored coordinates.** The layout algorithm places nodes and
   derives walls automatically. Items are placed within their room's floor.
5. **Output is unchanged.** The game engine receives the same dict format.
   No changes to `game.py`, `rooms.py`, or any rendering code.

## Graph Model

### Nodes

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Unique identifier within the level |
| `size` | enum | `CLOSET`, `ROOM`, `HALL`, `CORRIDOR` |
| `items` | list | Treasures, materials, keys, blocks, plates, enemies |
| `is_start` | bool | Player starts here |

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
5. **Layout**: arrange nodes spatially within 30×16, tight packing
6. **Derive walls**: floor = room tiles; wall = everything else (reinforced);
   edge tiles get their connection type (doorway/stone/locked/gate)
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

## Done when

- [ ] `levelgraph.py` generates valid graphs from feature sets
- [ ] Playability validation catches all unreachable/bypassed items
- [ ] `levellayout.py` produces tight-packed floor plans on 30×16 grids
- [ ] Generated levels are playable in `poe run --level N`
- [ ] Restarting the game produces different layouts
- [ ] Levels 1-10 remain byte-identical
- [ ] No changes to `game.py`, `rooms.py`, or rendering code
