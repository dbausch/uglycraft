# Spec 0029 — Water challenge solvability fixes

## Status

- [ ] W1 — Planks survive layout: `planks_dict == 2 × N_water` for every generated level
- [ ] W2 — One bridge per water room: bridging any tile of a stream marks that water room accessed; no second bridge can be built for it (no waste)
- [ ] W3 — Bridge budget keyed per water room (not per grid); never binds below need
- [ ] W4 — Level dict records water-stream identity (tile → water-room/stream id) to enable W2/W3
- [ ] W5 — `validate_playability` requires two reachable planks per WATER edge; drop the `has_block` arm (closes BL-04)
- [ ] W6 — Property tests covering W1–W5

## Design intent (confirmed by user)

**Each water room is reached by exactly one bridge. Bridges cannot be wasted.**
A WATER edge places a single 1-tile-thick stream along the boundary between the
corridor (or a room) and the water room behind it. Crossing requires bridging
**one** tile of that stream; the bridge persists. Provisioning is therefore
exactly **one bridge's worth of planks (2 planks) per water room**, and the
runtime must (a) make those planks actually obtainable and (b) allow exactly one
bridge per water room.

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

## The defects

### W1 — Planks dropped during layout (dominant, ~85% of water levels)

`LevelGraphBuilder.add_water_room` (`levelgraph.py:574`) appends exactly two
`('planks',)` materials per WATER edge into reachable, non-water rooms — verified
correct (graph always has `2 × N_water` planks). But
`_place_items_in_room` (`levellayout.py:1876-1880`) places materials **after**
treasures and **silently drops** any it cannot place:

```python
materials = []
for (mat_type,) in node.materials:
    p = _next()          # None when the room has no free floor tile left
    if p:                # <-- silent drop on None
        materials.append((*p, mat_type))
```

Treasures (placed first, lines 1869-1874) consume the room's free tiles, so in a
small or item-dense room the planks find no tile and are lost. Result: the final
level has fewer than `2 × N_water` planks → the player cannot craft a bridge per
water room → the level is unplayable for full completion.

**Fix:** guarantee that the two planks for every water room survive into the
level dict. Approach (to be finalised in implementation):
1. Place mandatory challenge items (planks, keys, plate/block — anything a
   barrier depends on) **before** treasures, so they win the tile contest; and
2. If the assigned room still cannot hold its planks, spill them to another
   reachable dry room (or the corridor) rather than dropping; and
3. If no reachable dry tile exists anywhere, raise `LayoutError` so
   `_generate_act2_level` regenerates — matching how unsolvable push puzzles are
   handled. Silent drops are forbidden.

**Target:** `planks_dict == 2 × N_water` for every generated level (W6 asserts).

### W2 — One bridge per water room (user-specified; currently absent)

`_try_auto_bridge` (`game.py:945`) guards only the **individual tile** just
bumped:

```python
bridged = self._bridged_tiles.get(self._current_room, set())
if (col, row) not in water or (col, row) in bridged:
    return False
```

`_water_tiles` / `bridged` are flat per-grid sets with no stream identity, so a
player can bridge several tiles of the **same** stream — each bump of a
not-yet-bridged tile builds another bridge, spends another bridge item, and
decrements the shared budget. Bridges can be wasted; the docstring's claim
("one bridge per water edge") is not enforced.

**Fix:** key the guard on the **water room / stream**, not the tile. Once any
tile of stream `S` is bridged, mark `S` accessed and refuse further bridge builds
for `S` (the player can already cross; extra bridges serve no purpose and must
not be spendable). Needs the stream→tile mapping from W4.

### W3 — Bridge budget keyed per grid, not per water room (~19%)

`_bridges_remaining` (`game.py:312`) is:

```python
self._bridges_remaining = sum(
    1 for rdata in data['rooms'].values() if rdata.get('water_tiles'))
```

i.e. **one unit per grid that contains any water**, regardless of how many water
rooms that grid holds. A grid with `k ≥ 2` water rooms gets budget 1 but needs
`k`, so the player is blocked from crossing the remaining streams even with
enough planks.

**Fix:** with W2's per-stream lock in place, a global cap is redundant — each
stream can be bridged at most once, and provisioning (W1) gives exactly one
bridge per water room. Remove `_bridges_remaining`, or recompute it as the number
of distinct water streams (`= N_water`) and keep it only as an assertion that
must never bind below need.

### W4 — Level dict lacks water-stream identity (enabler for W2/W3)

`derive_walls` returns a flat `water_tiles` list and `build_level_dict` stores it
as `room['water_tiles']`; `game.py` loads it into a flat `self._water_tiles`
set. There is no mapping from a water tile to the water room / WATER edge it
belongs to, which W2 and W3 both need.

**Fix:** emit per-WATER-edge groupings from `derive_walls` / `build_level_dict`
(e.g. `room['water_streams'] = [[tiles…], …]` or `water_tile_stream = {tile:
stream_id}`), and carry them into `game.py` so the bridge lock and budget can be
keyed per stream. Preserve the existing per-grid bridge-state keying from spec
0027 / BL-10 (`_bridged_tiles` is `{room_key: set}`).

### W5 — `validate_playability` water check too permissive (closes BL-04)

`validate_playability` (`levelgraph.py:268-279`) opens a WATER edge when
`has_planks OR has_block`, where `has_planks` is true if **any single** plank is
reachable and `has_block` is always wrong (a pushable block cannot bridge water).

**Fix:** require **two** reachable planks (one craftable bridge) on the dry side
of each WATER edge; drop the `has_block` arm. Closes **BL-04**.

## Verification (W6)

No automated suite exists for game.py runtime, but the generator is testable.
Add pytest property tests (per project test-suite discipline) that, across many
seeds and all Act 2 feature sets, assert for every generated level:

1. `planks_dict == 2 × N_water` (W1) — no planks lost.
2. Every water stream is a single 1-tile-thick crossing reachable from the dry
   side; one bridge tile suffices (W2/W4).
3. Distinct water streams `== N_water`; the bridge budget never binds below the
   number of water rooms (W3).
4. `validate_playability` rejects a WATER edge with fewer than two reachable
   planks and ignores blocks (W5).

The existing runtime safety net is push-block-only (`_verify_blocks`, BL-13 / BL-14)
and does **not** cover water; after these fixes the water challenge is solvable by
construction with no runtime net required.

## Done when:

- [ ] W1 — `planks_dict == 2 × N_water` holds for every generated Act 2 level;
      planks are never silently dropped (spilled or `LayoutError` instead).
- [ ] W2 — Building a bridge on any tile of a stream marks that water room
      accessed; no further bridge can be built for it; bridges cannot be wasted.
- [ ] W3 — Bridge availability is keyed per water room; a grid with multiple
      water rooms is fully crossable; the global cap never binds below need.
- [ ] W4 — The level dict carries water-stream identity sufficient for W2/W3.
- [ ] W5 — `validate_playability` requires two reachable planks per WATER edge
      and ignores blocks; BL-04 closed.
- [ ] W6 — Property tests for W1–W5 pass (`poe test`).
