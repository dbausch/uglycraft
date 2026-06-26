# Level Layout Expansion

## Status

- [ ] Key/door colors: 7 colors total (add yellow, cyan, purple, orange)
- [ ] Key/door color uniqueness: exactly one door per color per level
- [ ] Non-rectangular PlacedNode (optional floor_tiles)
- [ ] L-shaped rooms (≥35% of large rooms)
- [ ] Cross corridor layout (+ shaped corridor, rooms in 4 corner quadrants)
- [ ] T corridor layout (T shaped corridor, any of 4 orientations, rooms in 3 zones)
- [ ] Chain corridor layout (compact hub, rooms in 4 bands around it)
- [ ] N-grid support: BORDER edges carry exit_side/entry_side; super_pos on corridor nodes
- [ ] _build_super_grid: arbitrary 2D grid arrangement, all 4 exit directions
- [ ] Remove NodeSize.CLOSET from all Act 2 levels
- [ ] Increase room counts; grid_count 2 for levels 13-16, 3 for 17-20
- [ ] Enemy speed: ACT2_BASE_ENEMY_MS 160→200; no level-20 speed boost
- [ ] Staircase sprite at grid border exits

---

## Key/door colors

Seven colors replace the previous three.  `crafting.py` defines the new
constants; `sprites.py` adds key + door sprites for each; `levelgraph.py`
assigns colors without replacement (shuffled pool, cycling on overflow).

Colors: red, blue, green, yellow (220,200,50), cyan (50,200,220),
purple (160,80,255), orange (230,120,40).

## Non-rectangular PlacedNode

`PlacedNode.__init__` gains optional `floor_tiles=None`.  When supplied it
overrides the default rectangular computation; `w` and `h` remain the
bounding-box dimensions used for packing arithmetic only.

All existing consumers (`_find_connection_tile`, `derive_walls`, `tile_owner`,
Sokoban BFS) already iterate `pn.floor_tiles`, so no downstream changes.

## L-shaped rooms

Helper `_l_shape_tiles(col, row, w, h, rng)` cuts a random corner (30-50% of
each dimension) from the bounding rectangle.  Applied in `_pack_band` and
`_pack_band_vertical` with p≈0.35 for rooms with w≥6 and h≥5.

## New corridor layouts

All three new layouts are added to STRATEGIES and dispatched in `layout_graph`.
The old `test_chain_strategy_not_available` test is removed.

**Cross**: corridor = horizontal arm (full width) ∪ vertical arm (full height),
both centred.  Rooms packed round-robin into the 4 corner quadrants.

**T** (4 orientations, chosen randomly): spine = full arm in one axis;
stem = half-arm on one side of spine.  Rooms in 3 zones (1 large band opposite
stem + 2 smaller bands flanking stem).

**Chain**: small rectangular hub in centre; rooms in 4 linear bands (above,
below, left, right).  Every band directly adjoins a hub side, so
`_find_connection_tile` is guaranteed to succeed.

## N-grid / super-grid architecture

```
Plane (2D super-grid)  ←  STAIRS edges between planes (deferred)
  Grid (30×16)         ←  BORDER edges between adjacent grids
    Room               ←  OPEN / LOCKED / … edges
      Tile
```

BORDER edges carry `exit_side` ('right'/'left'/'top'/'bottom') and
`entry_side` (opposite).  Each corridor node carries `super_pos=(col,row)`.

`LevelGraphBuilder.start_next_grid(super_col, super_row, exit_side, **kw)`
replaces `start_second_grid`.  `LevelGraph.generate()` computes a 2D
arrangement for N grids and wires all adjacent pairs.

`_build_multi_grid` → `_build_super_grid` in `levellayout.py`:
iterates all BORDER edges; stitches exits on correct sides (shared row for
left/right, shared column for top/bottom).

STAIRS (multi-plane transitions) are architecturally planned but not
implemented in this task.  Staircase sprite renders at every exit tile as a
visual hint.

## Levels

- Remove NodeSize.CLOSET everywhere in Act 2.
- room_count: +2 to +4 across all levels.
- grid_count: 2 for levels 13-16; 3 for levels 17-20.

## Enemy speed

`ACT2_BASE_ENEMY_MS` 160 → 200.  Level-20 special-case (`ACT2_BOSS_MOVE_MS`)
removed; formula is uniform across all Act 2 levels.

## Done when

- [ ] `poe test` passes
- [ ] `poe run --level 12`: all locked doors have distinct colors
- [ ] `poe run --level 15`: two-grid level, staircase visible at border
- [ ] `poe run --level 17`: three-grid level, navigable via 3 grids
- [ ] L-shaped rooms appear and are navigable (no isolated pockets)
- [ ] Cross / T / chain layouts appear and feel distinct
- [ ] Enemy noticeably more relaxed in early Act 2 levels
