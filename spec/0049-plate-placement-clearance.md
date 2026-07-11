# Spec 0049 — Pressure-plate clearance: entrances and water (BL-19 + bridge rule)

Two placement rules for pressure plates, plus one runtime rule:

1. **BL-19 (P1):** a plate must not be placed on or cardinally adjacent to
   a room's entrance — nor adjacent to the tile the player lands on when
   stepping through it ("step in and you're immediately beside the plate").
2. **New rule (Daniel, 2026-07-12):** no bridge can be built next to a
   pressure plate. Generator side: a plate is never placed cardinally
   adjacent to a water tile (so the situation cannot be generated).
   Runtime side: `_try_auto_bridge` refuses a water tile cardinally
   adjacent to a plate (so the rule holds even for hand-authored or
   legacy levels).

## Status

- [ ] P1 — `_place_puzzle` takes a `plate_excluded` set; plate candidates
      (`P` loop) skip it — blocks and solution paths are NOT restricted
- [ ] P2 — `build_level_dict` computes per-room exclusions: connection
      tiles + their cardinal neighbours + the landing tile's cardinal
      neighbours, for every edge of the plate's room (entrance rule)
- [ ] P3 — exclusions also cover every tile cardinally adjacent to a
      water tile (bridge rule, generator side)
- [ ] P4 — `World._try_auto_bridge` refuses water tiles cardinally
      adjacent to a plate of the current room (bridge rule, runtime side;
      no sound, inventory untouched — like every other failed bridge
      condition)
- [ ] P5 — Tests red→green: runtime refusal fixture; `plate_excluded`
      unit test; multi-seed generation property (no plate adjacent to
      entrance-landing or water across the seed sweep)
- [ ] P6 — Full suite green, goldens byte-identical unless a seeded
      generator trace legitimately changes (same policy as spec 0048 —
      re-record only with a reviewed diff)
- [ ] P7 — Docs: `kb/requirements.md` new invariants, BL-19 closed,
      backlog note

## Geometry (rule of this repo: confirm these diagrams before any code)

### Entrance clearance (P2)

Doorway `E` at **(13,5)** in the wall line between the corridor (row 4)
and the room (rows 6+). The player stepping through lands on `L` =
**(13,6)**. Excluded plate positions are `E`, `L`, and the cardinal
neighbours of both (only floor tiles matter — wall/corridor tiles were
never candidates):

```
      col:  10  11  12  13  14  15  16
row 4        .   .   .   e   .   .   .    corridor floor (e = E's outside neighbour)
row 5        #   #   #   E   #   #   #    wall line, doorway E = (13,5)
row 6        .   .   x   L   x   .   .    room floor;  L = (13,6) landing tile
row 7        .   .   .   x   .   .   .
row 8        .   .   .   .   .   .   .    ← nearest allowed plate row on this axis
```

Excluded floor tiles in the room: **L=(13,6)**, **(12,6)**, **(14,6)**,
**(13,7)**. Applied for **every** edge incident to the plate's room
(rooms can be entered through any of their doorways, not just the
corridor one).

### Water clearance (P3, generator) — and the runtime mirror (P4)

Water is not free-standing floor decoration: a WATER edge converts the
shared **partition wall** between two rooms into the stream. Here the
partition is column **20**, separating room A (cols ≤ 19) from room B
(cols ≥ 21); rows 6–7 of it are the stream, the rest stays wall. Each
water tile's along-axis neighbours are wall or more water — the only
floor neighbours are the two flanking tiles, one per room:

```
      col:  17  18  19  20  21  22  23
row 5        .   .   .   #   .   .   .     # = partition wall (col 20)
row 6        .   .   P   W   x   .   .     W = water (20,6);  P = (19,6)
row 7        .   .   x   W   x   .   .     W = water (20,7)
row 8        .   .   .   #   .   .   .
            ── room A ──  │  ── room B ──
                     partition col 20
```

`P` at **(19,6)** is the hypothesised plate this rule forbids: it is
cardinally adjacent to `W`(20,6) — the player bumping that water tile to
build the bridge into room B would be standing **on the plate** while
doing it. Excluded plate tiles: **(19,6), (19,7)** in room A and
**(21,6), (21,7)** in room B (marked `P`/`x`; the along-axis neighbours
(20,5)/(20,8) are partition wall and were never candidates). The rule is
stated as "all cardinal neighbours of every water tile" so it holds
unchanged for horizontal streams, where the flanking floor is above and
below.

Runtime mirror (P4): if a level nevertheless contains the `P`(19,6)
plate, bumping `W`(20,6) refuses to build the bridge; `W`(20,7) — not
plate-adjacent — still works, so the water room stays reachable.

## Design

### Generator (P1–P3)

`_place_puzzle(room_name, gate_id, placed, passable, excluded, rng,
prior_puzzles=(), plate_excluded=frozenset())` — the new set is checked
**only** in the plate-candidate loop (`if P in plate_excluded:
continue`). It must not be merged into `excluded`, which also constrains
block positions and solution tiles: blocks may still pass near the
entrance, only the plate may not sit there.

`build_level_dict` computes the set before the puzzle-placement loop,
per plate room:

- entrance part: for each `graph.neighbors(room)` edge with both ends
  placed, `conn = _find_connection_tile(...)` (the flame-jet entry
  pattern); exclude `conn`, its 4 cardinal neighbours, and — for each
  conn-neighbour inside the room's `floor_tiles` (the landing tile) —
  that tile's 4 cardinal neighbours.
- water part: 4 cardinal neighbours of every tile in the grid's
  `water_tiles`.

Over-exclusion in a cramped room can leave `_place_puzzle` without
candidates — it already raises a retryable `LayoutError`; the existing
fresh-seed retry absorbs it (the multi-seed generation tests guard
against a systematic failure rate).

### Runtime (P4)

In `World._try_auto_bridge`, after the water/water-room checks and
before the inventory check:

```python
for pc, pr, _gid in self._room_plates.get(self._current_room, []):
    if abs(pc - col) + abs(pr - row) == 1:
        return False    # design rule: no bridge next to a plate
```

Ordering keeps all failure paths side-effect-free (no sound, no
inventory use), like every other refused bridge.

### Tests (P5, red first)

1. Runtime (`tests/test_world.py`): water fixture with a plate placed
   cardinally adjacent to the stream tile → bump the water → no
   `bridge_built` event, bridge item still in inventory, tile still
   blocked. Red today (the bridge builds).
2. Unit (`tests/test_placement_rules.py` or `test_sokoban.py`):
   `_place_puzzle` with a `plate_excluded` covering an otherwise-valid
   plate tile never returns that tile as the plate. Red until P1.
3. Property (multi-seed, mirroring the existing generation tests): for
   generated levels across the standard seed range, every plate is
   (a) not cardinally adjacent to any `water_tiles` entry of its room,
   (b) not on/adjacent to any connection tile or landing tile of its
   room. Red today for whatever fraction of seeds currently violates it;
   green after.

## Non-goals

- No changes to block placement, solution paths, or the Sokoban solver.
- No re-positioning of existing water/entrances; only plate candidates
  shrink.
- `dead_squares`, flame jets, item placement: untouched.

## Verification

1. `poe test` green; goldens per the spec-0048 policy (byte-identical
   expected; seeded generator traces re-recorded only if legitimately
   changed, with reviewed diff).
2. Manual gate: user plays Act 2 gated levels — plates no longer hug
   entrances; bumping water next to a plate (if encounterable) builds
   no bridge.

## Done when:

- [ ] P1 — `plate_excluded` parameter, plate-loop-only
- [ ] P2 — entrance clearance computed per plate room
- [ ] P3 — water clearance in the same set
- [ ] P4 — runtime bridge refusal beside plates
- [ ] P5 — tests red→green (runtime, unit, multi-seed property)
- [ ] P6 — suite green; golden policy honoured
- [ ] P7 — docs + backlog updated
