# Backlog

Ideas and bugs recorded for future consideration.
None of these are planned or scheduled; each needs a spec before implementation.

Priority: **P1** = correctness bug affecting live gameplay · **P2** = logic/UX bug, rare or non-critical · **P3** = improvement / refactor

→ Level generator invariants referenced by BL-01–BL-05: `kb/requirements.md`
→ Architecture and zone counts referenced by BL-02, BL-05: `kb/architecture.md`

---

## BL-02 · FIXED · Multi-zone layout leaves empty wall areas

Fixed: `layout_graph` filters `available` to strategies where
`n_rooms >= _STRATEGY_MAX_ZONES[s]` before `rng.choice`; `_pick_strategy`
does the same for the super-grid path. Both fall back to `full_border` if
no strategy passes. Confirmed by code inspection (no spec/commit reference).

---

## BL-03 · P2 · Bug: Challenge items placed in wrong grid for border barriers

`LevelGraphBuilder.start_next_grid` picks challenge items using
`self._current_corridor`, not the `source` (prev_corridor) argument.
In a branching super-grid (Grid_A → Grid_B, Grid_A → Grid_C), when Grid_C is
added after Grid_B, `self._current_corridor` is already Grid_B's corridor.
The plate+block for a gated Grid_A↔Grid_C border therefore lands in Grid_B.
Similarly, keys for a locked Grid_A↔Grid_C border may land in Grid_B.

The level remains technically solvable (cross-grid gates use the global
`_gate_open` set; Grid_B is reachable from Grid_A), but the player has no
indication to look there.

**Fix A (locked border):** restrict key search to `prev_corridor`'s rooms first;
fall back to all `_reachable` only if that set is empty.
**Fix B (gated border):** use `prev_corridor`'s room set for
`_puzzle_candidates()` instead of `self._current_corridor`'s rooms.

---

## BL-04 · P2 · Bug: `validate_playability` water-crossing check too permissive

`validate_playability` opens a WATER edge when `has_planks OR has_block` is True.

Problems:
1. `has_planks` is True when *any* plank is reachable — not both planks required
   to craft `CRAFT_BRIDGE`.
2. `has_block` opens the edge when a pushable block is reachable, but blocks
   cannot bridge water in the game (only `CRAFT_BRIDGE` can).

In practice planks are always placed in pairs by `add_water_room`, so the
"missing second plank" scenario is rare; the `has_block` path is always wrong
but does not cause deadlocks when planks are present.

**Fix:** require exactly two reachable planks; drop the `has_block` arm.

---

## BL-05 · P3 · Generalised corridor construction

All corridor shapes can be derived from a single generative model:

1. Start with one arm orthogonal to a border side at any position.
2. The arm can end (dead end) or continue:
   - Extend straight to the opposite border → straight corridor
   - Turn left or right to meet a parallel border → L-shape
3. The turned segment can be shorter (not reaching its border), enabling a
   second turn back toward the original direction → Z/S-shape
4. Add a branch arm → T-shape
5. Add a second branch arm → double-T; stems may be aligned or offset

One parametrised function for corridor floor tiles + zone boundary derivation
would replace the seven separate `_layout_*` functions. See `kb/architecture.md`
("Target architecture") for design notes.

---

## BL-07 · P3 · L-shaped room for 'l' strategy with 2 rooms

For the `'l'` layout strategy with 2 rooms and perpendicular exits, the current
algorithm packs both rooms into rectangular zones, leaving 2 zones empty. A
better layout exists: use an L-shaped corridor and fill the entire non-corridor
space with a large L-shaped room for one of the two rooms, with the second room
occupying the remaining rectangular zone.

This requires support for non-rectangular room `floor_tiles` in the packing
functions.

**Fix hint:** extend `PlacedNode` to support arbitrary `floor_tile` sets
(already the case for corridors), then add an `_l_two_room` variant of
`_layout_l` that computes one L-shaped room covering the full non-corridor
interior minus one rectangular zone reserved for the second room.

---

## BL-06 · P3 · Test suite too slow for TDD cycles

345 tests take ~90 seconds, making red-green-refactor loops expensive. The
hypothesis-based property tests (`max_examples=150-200`) are the main driver.

**Fix hint:** (1) Reduce `max_examples` to 50 for the slower hypothesis suites
— the database still replays historical failures, so coverage does not regress
much. (2) Explore `@settings(deadline=...)` or a named Hypothesis profile that
caps wall-clock time per test rather than example count. (3) Split the suite
into a fast tier (pure unit tests, no Hypothesis or small `max_examples`) and a
slow tier, then add a `poe test-fast` task that runs only the fast tier so TDD
cycles stay under ~10 seconds.

---

## BL-08 · FIXED · `_spanning_tree` returns fewer nodes than requested

Fixed in 7cabe8a (spec/0026-wilson-spanning-tree.md).
Replaced the biased random-walk with **randomized Prim's**: grow the tree from
the full frontier of all placed nodes, pick a random frontier edge each step.
Wilson's algorithm was attempted first but is unsuitable for infinite grids
(2D random walk is null-recurrent — n=2 seed=2 took 2M+ steps). Prim's
terminates in exactly n−1 successful steps. `branch_prob` retired; all 336
tests green in ~92 s.

---

## BL-09 · FIXED · T/double-T `_layout_corridor` round-robin overloads narrow sub-zones

Fixed in c921ca8 + ad25ef0 (spec/0025-greedy-zone-assignment.md).
Replaced round-robin with greedy assignment: each room goes to the zone offering
the most tiles; empty zones are filled before any zone gets a second room;
`LayoutError` raised if rooms exceed total capacity.

---

## BL-10 · FIXED · Bug: Bridge state leaks across grids with water edges at the same position

Fixed in 600b3fd (spec/0027-bridge-state-per-grid.md).
Changed `_bridged_tiles` in `game.py` from a flat `set[(col, row)]` to a
`dict[room_key, set[(col, row)]]`. Room keys encode the grid identity, so
bridges on one grid no longer affect water tiles at the same coordinate on
other grids.

---

## BL-11 · FIXED · Tick accumulation on level load causes enemy burst-movement

Fixed in 8bed7e1 (spec/0028-lazy-level-generation.md).

Root cause was twofold: (1) all ten Act 2 levels were generated eagerly at
`import levels` **and again** in `_full_reset` via `regenerate_act2` (~20 s of
mostly-discarded work, blank window), and (2) the first `clock.tick()` after that
returned an ~11 s `dt` that drained one enemy step per frame, causing the
1–2 s burst. Fixes: lazy per-level Act 2 generation (`levels.get_level`,
`new_game_levels`, `regenerate_level`) so `--level 11` went ~9.9 s → ~0.02 s,
plus a `dt` clamp to `MAX_DT_MS` in the main loop. A "Loading . . ." progress
screen covers the (now per-level) generation. → see `kb/architecture.md`
("Lazy Act 2 generation").

---

## BL-12 · P2 · Bug: Grid entry tiles always display stairs instead of the source exit type

Grid entry tiles unconditionally render as stairs regardless of what barrier
type the player just passed through. If the source grid has an open doorway,
a locked door, or a gate at the border tile, the corresponding entry tile on
the destination grid should display the same passage type — mirroring what the
player sees when they look back.

**Fix hint:** Find where BORDER edge entry tiles are rendered (likely in
`game.py` or `levellayout.py`). Instead of unconditionally drawing stairs,
look up the barrier type stored in the BORDER edge params (open / locked /
gated) and draw the matching tile — open passage, locked door, or gate — so
the entry tile reflects what the player crossed to get there.

---

## BL-13 · P2 · Investigate how unplayable levels still slip through "playability-preserving" transformations

The level generator builds levels via a chain of graph transformations
(`levelgraph.py` / `levellayout.py`), each of which is supposed to preserve a
playability invariant — playable before, playable after. Yet `game.py` keeps a
runtime safety net `_verify_blocks` that detects stuck push-blocks and
force-regenerates the level (now via `levels.regenerate_level()`). The mere
existence of that net proves unplayable levels still slip through: some
transformation does *not* in fact preserve the invariant.

The task is to find which one. Candidate culprits:
1. **Layout / packing step** placing a push-block flush against walls so it has
   zero pushable directions.
2. **Multi-grid stitching** (`_build_super_grid`) altering tiles *after*
   per-grid playability was already validated, invalidating the earlier check.
3. **`validate_playability` gaps** already tracked in BL-04 (water-crossing
   check too permissive).

**Fix hint:** Audit each transformation to determine where the invariant is
actually violated, then either tighten that transformation's validation or add
a post-transformation playability check so the runtime `_verify_blocks` net
becomes redundant. Cross-reference `kb/requirements.md` (the formal playability
invariants) and `kb/architecture.md` (the pipeline and super-grid stitching).
