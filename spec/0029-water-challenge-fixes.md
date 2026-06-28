# Spec 0029 — Water challenge solvability fixes

## Status

- [ ] W1 — No collectible is ever dropped during layout: planks are placed first
      (after flames and push puzzles); any item that overflows its room spills to
      the corridor; enemies may share a tile with an item (no reserved tile);
      `LayoutError` only if the corridor is also full (should never happen).
      `planks_dict == 2 × N_water` for every generated level
- [ ] W2 — One bridge per water **room**: as soon as a water room is made
      accessible by a bridge, no further bridge to that room can be built
      (keyed on the room, not on a tile or an edge)
- [ ] W3 — Bridge accounting is per water room; the per-grid `_bridges_remaining`
      cap is removed (the per-room lock + plank inventory are the only limits)
- [ ] W4 — Level dict records, per water tile, which water room it gives access
      to, so W2/W3 can be keyed on the room
- [ ] W5 — `validate_playability` requires two reachable planks per WATER edge
      (counted over non-water-reachable rooms, across grids); drop the
      `has_block` arm (closes BL-04)
- [ ] W6 — Property tests covering W1–W5

## Design intent (confirmed by user)

**Each water room is reached by exactly one bridge. Bridges cannot be wasted.**

- A WATER edge places a single 1-tile-thick stream between a water room and the
  rest of its grid. Crossing requires bridging **one** tile; the bridge persists.
- The two planks that fund that bridge are **fungible and may be distributed
  independently to any reachable room on any grid** — finding one plank on grid 1
  and another on grid 2 to reach a water room on grid 3 is an intended gameplay
  feature, not a defect. The inventory is global, so cross-grid collection works.
- The cap is keyed on the **water room**: once the room is accessible, building
  another bridge toward it is impossible (no waste). Not per tile, not per edge.

## Evidence (headless generation sweep)

Scripts: `scratchpad/repro_water.py`, `scratchpad/repro_water2.py`.
Graph-level vs. built-level over 105 water-bearing Act 2 levels (15 seeds × 10):

| Property | Result | Meaning |
|---|---|---|
| graph planks `== 2 × N_water` | **0/105 wrong** | graph provisioning is correct |
| **planks lost in layout** | **89/105 (85%)** | planks dropped building the level dict |
| craftable bridges `< N_water` | **89/105 (85%)** | most water levels can't be fully completed |
| `_bridges_remaining < N_water` | 20/105 (19%) | runtime cap mis-keyed |

Example (`seed0 idx4`): 3 water rooms → graph places 6 planks → **1 plank
survives** → 0 craftable bridges.

## The defects and resolutions

### W1 — Planks dropped during layout (dominant, ~85% of water levels)

`LevelGraphBuilder.add_water_room` (`levelgraph.py:574`) appends two `('planks',)`
materials per WATER edge into reachable, non-water rooms — verified correct (graph
always has `2 × N_water` planks), and these may already land on different grids
(the picks come from the builder's global reachable set; this is the intended
fungible distribution and must be preserved). But `_place_items_in_room`
(`levellayout.py:1876-1880`) places materials **after** treasures and **silently
drops** any it cannot fit:

```python
materials = []
for (mat_type,) in node.materials:
    p = _next()          # None when the room has no free floor tile left
    if p:                # <-- silent drop on None
        materials.append((*p, mat_type))
```

Treasures (placed first, lines 1869-1874) consume the room's free tiles, so the
planks find no tile and are lost.

**Resolution — drop nothing; spill surplus to the corridor.**

1. **Planks first.** Place planks in a dedicated pass **right after flame jets and
   push puzzles, before any other item** in `build_level_dict`, so they get first
   dibs on their own room and tend to stay near their water room. (Cross-grid
   fungible distribution from `add_water_room` is unchanged.)

2. **Spill, never drop.** Make `_place_items_in_room`'s `_next()` never return
   `None` for a collectible: when the room's own tiles are exhausted, draw the
   next unused tile from the **corridor's** free floor tiles (`spill_floor`,
   passed in from `build_level_dict`; the corridor is the single `CORRIDOR` node,
   the reachability hub, so anything spilled there is trivially reachable). This
   applies to planks, surplus materials, treasures, and keys — the `if p:` drops
   at `levellayout.py:1873/1880/1886` are removed.

3. **Corridor full ⇒ `LayoutError`.** If both the room and the corridor are full,
   raise `LayoutError` so `_generate_act2_level` regenerates. With corridors large
   and items few this should never trigger; it exists only to keep "drop nothing"
   absolute. The corridor is the **only** spill target (no any-tile fallback).

4. **Enemies are exempt from spill.** Corridor enemies put players off, so enemies
   are never spilled. Instead they stop reserving a tile: an enemy may be placed
   **on top of an item**. Enemy placement picks any valid in-room floor tile
   (respecting `MIN_ENEMY_DIST` from the player, avoiding walls/flames) **without**
   adding it to `used`, so enemies always fit in their room and never overflow.

**Target:** `planks_dict == 2 × N_water` for every generated level (W6 asserts);
no collectible silently dropped.

### W2 — One bridge per water room (user-specified; currently absent)

`_try_auto_bridge` (`game.py:945`) guards only the **individual tile** bumped:

```python
bridged = self._bridged_tiles.get(self._current_room, set())
if (col, row) not in water or (col, row) in bridged:
    return False
```

`_water_tiles` / `bridged` are flat per-grid sets with no room identity, so a
player can bridge several tiles of the same stream — each bump of a not-yet-bridged
tile builds another bridge and spends another bridge item. Bridges can be wasted.

**Resolution:** key the lock on the **water room**. Using the per-tile → water-room
map from W4, when the player bridges any tile that makes water room `R` accessible:
build the one bridge and mark `R` accessed. Once `R` is accessed, refuse every
further bridge build that would lead to `R` (the room is already reachable; extra
bridges serve no purpose and must not be spendable). The lock is on `R`, never on
the tile or the edge.

### W3 — Bridge budget keyed per grid, not per water room (~19%)

`_bridges_remaining` (`game.py:312`) is `sum(1 for rdata in
data['rooms'].values() if rdata.get('water_tiles'))` — **one unit per grid that
contains any water**, regardless of how many water rooms that grid holds. A grid
with `k ≥ 2` water rooms gets budget 1 but needs `k`.

**Resolution:** with the W2 per-room lock, a global cap is redundant — each water
room can be bridged at most once, and the player's only real limit is owning a
crafted bridge (2 planks). **Remove `_bridges_remaining`.** The constraint becomes:
have a bridge item crafted **and** the target room not yet accessed.

### W4 — Level dict lacks water-room identity (enabler for W2/W3)

`derive_walls` returns a flat `water_tiles` list; `game.py` loads it into a flat
`self._water_tiles` set. There is no mapping from a water tile to the water room
it borders, which W2/W3 need.

**Resolution:** in `build_level_dict` (water tiles are already grouped per WATER
edge by `derive_walls`, and `tile_owner` maps floor tiles to node names), emit a
mapping the runtime can key on — e.g. `room['water_tile_room'] = {tile:
water_room_node}`, where the water room is the non-corridor node owning the floor
on the far side of the stream. Carry it into `game.py`. Preserve the per-grid
bridge-state keying from spec 0027 / BL-10 (`_bridged_tiles` stays
`{room_key: set}`).

### W5 — `validate_playability` water check too permissive (closes BL-04)

`validate_playability` (`levelgraph.py:268-279`) opens a WATER edge when
`has_planks OR has_block`, where `has_planks` is true if **any single** plank is
reachable and `has_block` is always wrong (a pushable block cannot bridge water).

**Resolution:** require **two** reachable planks per WATER edge — counted over
rooms reachable **without** crossing water (across grids, since planks are
fungible) — and drop the `has_block` arm. Because all planks are placed before
any water room joins the reachable set, a greedy "collect reachable planks, cross
the nearest water room, repeat" order always works when the global count is
`2 × N_water`. Closes **BL-04**.

## Verification (W6)

No automated suite exists for game.py runtime, but the generator is testable.
Add pytest property tests (per project test-suite discipline) that, across many
seeds and all Act 2 feature sets, assert for every generated level:

1. `planks_dict == 2 × N_water` (W1) — no planks lost; planks may sit on any grid.
2. Every water tile maps to exactly one water room; one bridge tile makes that
   room accessible (W2/W4).
3. The number of water rooms is recoverable from the level dict and there is no
   per-grid bridge cap that can bind below it (W3).
4. `validate_playability` rejects a WATER edge with fewer than two reachable
   planks (over non-water-reachable rooms) and ignores blocks (W5).

The push-block runtime net (`_verify_blocks`, BL-13 / BL-14) does **not** cover
water; after these fixes the water challenge is solvable by construction.

## Done when:

- [ ] W1 — Every graph plank reaches the level dict (`planks_dict == 2 × N_water`),
      placed after flames and push puzzles and before all other items; planks may
      be distributed across grids; surplus collectibles spill to the corridor and
      nothing is silently dropped; enemies may overlap items; `LayoutError` only if
      the corridor is full.
- [ ] W2 — Building a bridge that makes a water room accessible marks that room
      accessed; no further bridge to it can be built; bridges cannot be wasted.
- [ ] W3 — `_bridges_remaining` removed; bridge availability is governed solely by
      the per-room lock and crafted bridge inventory; multi-water-room grids are
      fully crossable.
- [ ] W4 — The level dict maps each water tile to the water room it gives access
      to; `game.py` keys the bridge lock on that room.
- [ ] W5 — `validate_playability` requires two reachable planks per WATER edge
      (across grids) and ignores blocks; BL-04 closed.
- [ ] W6 — Property tests for W1–W5 pass (`poe test`).
