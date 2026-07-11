# Spec 0048 — Solver/runtime passability unification + regeneration-net demotion (BL-14, BL-36)

Make the generator's push-puzzle subsystem consume the **same passability
semantics** as the runtime, closing the water leak that produces stuck
blocks (BL-14, P1), and demote the `_verify_blocks` regeneration net so
it can no longer throw the player into a regenerated level on room
re-entry (BL-36, P1). This is a **bug-fix spec**, not a
behaviour-preserving refactor stage: the fixed paths are exactly the ones
no golden covers, and all goldens except (possibly) the two seeded
generator-integration traces must stay byte-identical.

## Status

- [ ] U1 — `RoomCells.blocked(c, r, gate_open)` extracted as THE barrier/
      water passability semantics; `World.blocked` delegates to it
      (behaviour-preserving, goldens byte-identical)
- [ ] U2 — `validate_push_puzzles` builds its obstacle model from
      `build_room_cells(room_data)` via U1's query — water becomes an
      obstacle exactly as at runtime (red-first fixture test)
- [ ] U3 — Placement side: `puzzle_passable` in `build_level_dict`
      subtracts `water_tiles`, so solutions are never routed across water
      in the first place
- [ ] U4 — Post-stitch check: `_build_super_grid` re-runs
      `validate_push_puzzles` on every room of the stitched level;
      failure raises `LayoutError` (→ fresh-seed retry)
- [ ] U5 — `_verify_blocks` demoted: runs only on **first entry of a
      freshly generated room** (never on `RoomState` restore, so
      player-wedged blocks never regenerate the level); after a
      mid-transition regeneration the transition code no longer
      repositions the player onto the stale entry tile
- [ ] U6 — Recreated headless sweep (`scratchpad/sweep_stuck_blocks.py`):
      0 stuck blocks across ≥ 25 seeds × block-bearing Act 2 levels
- [ ] U7 — Full suite green; goldens byte-identical except, at most, the
      two seeded generator traces (see "Golden policy")
- [ ] U8 — Docs: `kb/architecture.md` BL-13/BL-14 section updated (fix
      recorded + stale post-0047 code references refreshed), BL-14 and
      BL-36 closed in the backlog, `kb/requirements.md` R-V2 note

## Background (verified against current code, 2026-07-12)

The runtime treats unbridged water as solid (`World.blocked` →
`cells.is_water and not bridge`, spec 0047; identical semantics to the
pre-refactor grid, proven by goldens). The puzzle subsystem does not:

- `validate_push_puzzles` (`levellayout.py` ~1577): `all_obstacles` =
  walls ∪ locked doors ∪ gates ∪ blocks — **no water**.
- `build_level_dict` (~2304): `puzzle_passable` = interior − walls −
  gate_tiles − lock_tiles — **no water** (water_tiles exist at that
  point, from `derive_walls`).

WATER edges put stream tiles cardinally adjacent to room floor, so a
water tile can sit on a block's only push axis: the solver routes over
it, the runtime refuses, the block is stuck, and `_verify_blocks`
regenerates the whole level on room entry. Empirical rate (kb sweep,
2026-07-10, generator unchanged since): 2 stuck blocks in 175
block-bearing levels, both water-wedged; no other cause occurred —
matching the kb proof that wall/gate/door/block-only stuck states are
unreachable from what the solver models. Everything else the net fires
on is a **false positive** — most damagingly the player legitimately
wedging a block and re-entering the room (BL-36, reproduced + confirmed
pre-refactor).

## Design

### U1 — one passability definition

```python
# cells.py
class RoomCells:
    def blocked(self, c, r, gate_open=frozenset()):
        """Barrier/terrain passability: blocking barrier (gates consult
        gate_open) or unbridged water.  Occupants (blocks) and bounds are
        the caller's layers."""
```

`World.blocked` becomes bounds → `cells.blocked(c, r, self._gate_open)`
→ block-at. The validator uses the same method with `gate_open=∅`
(closed gates are obstacles, as it already assumes) and layers blocks
itself. Any future barrier kind or terrain automatically reaches both
consumers — the BL-13 mismatch *class* is closed, not just the water
instance.

### U2 — validator consumes the model

`validate_push_puzzles` builds `cells = build_room_cells(room_data)`
once and computes

```python
passable = {(c, r) for c in interior for r in interior
            if not cells.blocked(c, r)} - set(blocks)
```

replacing the hand-built `all_obstacles`. Border cells are outside the
interior range either way. Signature and error-string behaviour
unchanged (R-V2 still: must return `[]`).

### U3 — placement side

`puzzle_passable -= {tuple(t) for t in water_tiles}` where it is built.
The reverse-BFS/Sokoban machinery of `_place_puzzle` is untouched — it
just stops seeing water tiles as floor, so placements that would need a
water crossing are never proposed (instead of being proposed and then
rejected at validation, wasting retries — or worse, slipping through).

### U4 — post-stitch re-validation

`_build_super_grid` currently never re-validates the stitched whole (kb
scope gap 1). After stitching, run `validate_push_puzzles` per stitched
room; any error raises `LayoutError` like the per-grid call. Stitching
only opens borders, so this should never fire — it is the cheap
insurance that turns "should be impossible" into "checked".

### U5 — the net stops punishing the player (BL-36)

- `_enter_room` calls `_verify_blocks` **only in the fresh branch**
  (room built from generator data). Restored rooms — the only place
  player-wedged blocks exist — are never re-checked, so leaving and
  re-entering a room can never regenerate the level. A wedged block is
  a solved-or-failed puzzle, not a broken level; death already resets
  blocks (`_reset_blocks`).
- `_try_room_transition` captures a level-generation marker (identity of
  `self._level_data`) before `_enter_room`; if entering triggered a
  regeneration, it returns without repositioning the player, without the
  transition flash, and without emitting `moved` — the player stands at
  the fresh level's start position with the level-start music/intro the
  inner `start_level` already emitted. (Today it teleports the player to
  the stale entry tile of a level that no longer exists.)
- With U1–U4 in place the fresh-entry check should never fire; it stays
  as the last-resort recovery for generator bugs, now incapable of
  eating player progress mid-game beyond the level it just started.

### Golden policy

U1, U2, U4, U5 touch no golden-covered path (no golden triggers
regeneration or contains a water-adjacent puzzle solution). U3 changes
**generation**: for a seed whose level places a puzzle near water, the
candidate sets — and therefore the RNG draws and the generated level —
legitimately change. The two seeded generator traces
(`act2_L11_walk`/`act2_L13_walk`, seed 777) are re-recorded **only if**
they actually change, with the diff reviewed and the reason (generator
bug fix alters generated content) stated in the commit; every other
golden must stay byte-identical. No other re-record is acceptable.

## Non-goals

- `_compute_dead_squares` keeps its permanent-walls-only model: water is
  bridgeable, so marking water-adjacent squares dead would over-restrict
  pushes after a bridge is built.
- Water-crossing *reachability* (bridge craftability, cross-grid keys)
  stays BL-04/kb scope-gap-2 territory.
- No changes to plate/gate mechanics (Stage 4) or room persistence
  (Stage 5).

## Tests (red first)

1. `tests/test_sokoban.py` (or new file): a hand-built room dict
   reproducing the kb wedge — a block whose only push axis crosses a
   water tile — where `validate_push_puzzles` must return an error.
   **Red today** (returns `[]`), green after U2.
2. `tests/test_cells.py`: `RoomCells.blocked` truth table (barrier,
   closed/open gate, water, bridged water) — red until U1.
3. `tests/test_world.py`: (a) wedge a block, leave, re-enter → same
   level object, no `level_started` event, block still wedged (red
   today: regenerates); (b) fixture with a pre-stuck block on a
   *fresh* room → regeneration still fires, and after it the player
   stands at the fresh level's start, not the stale entry tile (red
   today: stale teleport).
4. Recreated sweep script (U6) as the statistical verification —
   run manually, not part of the suite (generation cost).

## Verification

1. `poe test` green; `git status tests/golden/` clean except at most the
   two reviewed generator-trace re-records (U7).
2. Sweep: 0 stuck blocks over ≥ 25 seeds (U6); include the two kb
   reference seeds that produced `(26,3)`/`(26,12)` if recoverable.
3. Manual gate: user plays Act 2 levels with water + blocks; wedging a
   block and re-entering the room must NOT regenerate the level.

## Done when:

- [ ] U1 — `RoomCells.blocked` extracted, `World.blocked` delegates
- [ ] U2 — validator obstacle model comes from `build_room_cells`
- [ ] U3 — `puzzle_passable` subtracts water tiles
- [ ] U4 — post-stitch `validate_push_puzzles` gate in `_build_super_grid`
- [ ] U5 — `_verify_blocks` fresh-entry-only; no stale reposition after
      mid-transition regeneration
- [ ] U6 — sweep recreated, 0 stuck blocks
- [ ] U7 — suite green; golden policy honoured
- [ ] U8 — docs + backlog (BL-14, BL-36 closed; BL-35 fix hint updated)
