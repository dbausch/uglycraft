# Spec 0027 — Scope bridge state per grid (BL-10)

## Status

- [x] `_bridged_tiles` scoped per room key — water on unrelated grids no longer auto-bridged
- [x] `_bridges_remaining` counter still decrements globally (one bridge consumed per placement)
- [x] Confirmed working by manual play test

## Problem

`self._bridged_tiles` in `game.py` is a flat `set[tuple[int, int]]`.  A bridge
placed at tile `(c, r)` on grid A adds `(c, r)` to this set.  Any other grid in
the same multi-grid level that has a water tile at the same `(c, r)` coordinate
will:

1. Treat that water tile as passable (wall collision map built without blocking it).
2. Render a bridge sprite instead of a water sprite.

Water tiles only need to share a coordinate by coincidence — grids are
independently laid out, so the same interior tile position can appear on
multiple grids.

## Root cause

`_bridged_tiles` is indexed solely by `(col, row)`, with no grid/room
discriminator.

## Fix

Change `_bridged_tiles` from `set[tuple[int, int]]` to
`dict[str, set[tuple[int, int]]]`, keyed by `self._current_room` (the room key
already encodes the grid identity, e.g. `"g_0_0"`, `"g_1_0"`).

Five callsites in `game.py` need updating:

| Line (approx) | Current | After |
|---|---|---|
| 265 (init) | `self._bridged_tiles = set()` | `self._bridged_tiles = {}` |
| 467 (`_build_walls_multiroom`) | `not in getattr(self, '_bridged_tiles', set())` | `not in self._bridged_tiles.get(room_key, set())` — `room_key` is already in scope at line 447 |
| 925 (`_try_auto_bridge`) | `bridged = getattr(self, '_bridged_tiles', set())` | `bridged = self._bridged_tiles.get(self._current_room, set())` |
| 939 (`_try_auto_bridge`) | `self._bridged_tiles.add((col, row))` | `self._bridged_tiles.setdefault(self._current_room, set()).add((col, row))` |
| 1238 (render) | `if (wc, wr) in self._bridged_tiles:` | `if (wc, wr) in self._bridged_tiles.get(self._current_room, set()):` |

`_bridges_remaining` (the total bridge-item budget) remains a single integer
across the whole level — it is deliberately shared, not a bug.

## Verification (manual)

No automated suite covers `game.py` game logic.  Verification steps:

1. Run the game at an Act 2 level that generates a water edge (`poe run --level 11`
   or higher; re-run until a level with water appears — it is not guaranteed every
   seed produces one, but occurs frequently).
2. Craft a bridge and place it over the water edge on the current grid.
3. Cross to another grid (any BORDER exit).
4. Confirm that any water tile on the new grid is **not** pre-bridged: it must
   block movement and render as water, not as a bridge.
5. Also confirm the original grid's bridge is still in place when you return.

## Done when

- [x] `_bridged_tiles` is a dict keyed by room key (600b3fd)
- [x] Bridge placed on one grid does not affect water on any other grid (confirmed
  by manual play test per steps above)
- [x] Original grid's bridge persists across grid transitions (confirmed same test)
