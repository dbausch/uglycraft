# Level Entrance: Border-Adjacent Player Start and Entrance Sprite

## Status

- [ ] `levellayout.py` computes the entrance tile and stores it in the start room dict
- [ ] `player_start` is the corridor tile immediately inside the entrance
- [ ] `sprites.py` adds `draw_level_entrance()` — a new entrance sprite
- [ ] `game.py` renders the entrance sprite at the entrance tile for the start grid

---

## Problem

Player start is currently computed as a bounding-box formula
`(pn.col + 1, pn.row + pn.h // 2)` that can land on a wall tile for
non-rectangular corridors (observed with `full_border`; patched with a
nearest-floor-tile fallback, but the result is still an arbitrary interior
position with no visual signal to the player).

The player should enter the grid from a clearly marked point on the grid's
outer border, matching the visual convention already established for
inter-grid BORDER exits (staircase sprite on border tiles).

---

## Design

### Entrance tile selection

An **entrance tile** is a border-wall tile (col 0, col 29, row 0, or row 15)
that is cardinally adjacent to a corridor floor tile.

Selection order for the start corridor:

1. **Left side** — collect all `(MIN_C, r)` corridor floor tiles; if any
   exist, pick the one closest to the vertical midpoint; entrance = `(0, r)`.
2. **Top side** — collect all `(c, MIN_R)` corridor floor tiles; pick the one
   closest to the horizontal midpoint; entrance = `(c, 0)`.
3. **Bottom side** — same, entrance = `(c, ROWS−1)`.
4. **Right side** — same, entrance = `(COLS−1, r)`.

For multi-grid levels, sides that already carry a BORDER exit are skipped (a
side with a BORDER exit is an inter-grid passage, not the world entrance).

This guarantees a valid entrance tile exists for every possible corridor
strategy, because every strategy reaches at least one border side.

### Player start

`player_start` = the corridor floor tile adjacent to the entrance tile
(i.e., one step inward: `(MIN_C, r)` for a left entrance, `(c, MIN_R)` for
a top entrance, etc.).

### Level dict

The start grid's room dict gains a key:

```python
room_dict['entrance'] = (col, row)   # the border tile
```

`player_start` is the adjacent corridor tile as described above.

For non-start grids, no `entrance` key is added.

### Entrance sprite (`sprites.py`)

A new function `draw_level_entrance()` that produces a sprite visually
distinct from the staircase (which marks inter-grid BORDER exits).

Design intention: an archway or marked opening — different colour/shape from
the grey stone staircase. Exact appearance to be confirmed by the user after
a first implementation.

### Rendering (`game.py`)

In the tile-drawing loop, after drawing the staircase sprites, draw the
entrance sprite at `room_data.get('entrance')` when the current grid is the
start grid.

```python
if 'entrance' in self._current_room_data:
    ec, er = self._current_room_data['entrance']
    self.surf.blit(sp['level_entrance'], (ec * TILE, er * TILE))
```

---

## Verification

Manual — no automated test suite for this feature:

- Run `poe run --level 11` through `--level 20`; confirm entrance sprite
  appears on the outer border of the start grid.
- Confirm player spawns at the corridor tile immediately inside the entrance.
- Confirm no entrance sprite appears on non-start grids.
- Confirm the staircase sprite (inter-grid exits) is unaffected.

---

## Done when

- [ ] Entrance sprite visible on start grid border in all generated levels
      (user confirmed)
- [ ] Player spawns at the corridor tile adjacent to the entrance (not an
      arbitrary interior tile)
- [ ] Staircase sprites on BORDER exits unaffected (no regression)
- [ ] `poe test` passes
