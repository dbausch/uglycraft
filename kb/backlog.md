# Backlog

Ideas and bugs recorded for future consideration.
None of these are planned or scheduled; each needs a spec before implementation.

Priority: **P1** = correctness bug affecting live gameplay · **P2** = logic/UX bug, rare or non-critical · **P3** = improvement / refactor

→ Level generator invariants referenced by BL-01–BL-05: `kb/requirements.md`
→ Architecture and zone counts referenced by BL-02, BL-05: `kb/architecture.md`

---

## BL-02 · P2 · Bug: Multi-zone layout leaves empty wall areas

`_layout_corridor` distributes rooms round-robin to all valid zones.
When `len(room_names) < len(valid_zones)`, the last zones receive 0 rooms
and appear as large wall areas with no floor tiles or passages.

**Fix:** in `layout_graph`, before `rng.choice(available)`, filter `available`
to strategies whose zone count ≤ `len(regular_rooms)`. Zone counts per strategy
are documented in `kb/architecture.md` (strategy table). This prevents
over-zoned strategies from being selected for small room counts entirely, rather
than papering over the symptom inside the strategy functions.

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

## BL-08 · P2 · Bug: `_spanning_tree` returns fewer nodes than requested

`_spanning_tree` can return fewer nodes than the `n` argument. A confirmed
failing case: `_spanning_tree(9, 0.0, Random(1007084))` returns 8 nodes instead
of 9, violating the invariant `len(result) == n`. The failure occurs for specific
seeds with `p=0.0` (no-branching path) and is recorded in the Hypothesis
database, replaying on every test run.

The test `test_no_branching_at_zero_prob` passes (≤1 child per node), so the
tree structure is not wrong — some node is simply never placed.

**Fix hint:** audit the loop in `_spanning_tree` for an off-by-one or early-exit
condition when `branch_prob=0.0` and `n` is large.
