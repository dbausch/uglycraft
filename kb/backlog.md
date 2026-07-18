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

## BL-03 · BY-DESIGN · Bug: Challenge items placed in wrong grid for border barriers

Closed by design decision (Daniel, 2026-07-12): this item was originally about
SOLVABILITY, and hunting across grids for a border barrier's key/plate is an
intentional part of the challenge — prerequisite locality is not a goal. A
review measured the scope (40 seeds x grid_count>=3 levels: 75% of
locked-border keys and 58% of gated-border plates sit in a grid other than the
source) and confirmed solvability is guaranteed on three layers:
(1) validate_playability (R-V3) proves prerequisites reachable before their
barrier at graph level; (2) layout drops of prerequisite rooms degrade the
border to an open passage instead of leaving it locked; (3) cross-grid
channels persist at runtime (spec 0050 errata cad68ba — the only real
solvability threat found here, already fixed and test-locked). No unsolvable
level was observed across the refactor play-testing. See the design note in
kb/requirements.md.

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

## BL-04 · FIXED · `validate_playability` water-crossing check too permissive

Fixed by spec 0029 W5 (commit 4e59245). `validate_playability` now opens a
WATER edge only when **two or more planks are reachable** (a craftable bridge),
and the bogus `has_block` arm is gone (a pushable block cannot cross water).
See spec/0029-water-challenge-fixes.md (W5) and tests/test_water_challenge.py.

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

## BL-12 · FIXED · Grid entry tiles always display stairs instead of the source exit type

Fixed in b62f370 (spec/0056-grid-entry-tile-type.md, supersedes spec 0039),
confirmed by Daniel 2026-07-11. Stitching records `border_barriers` on both
room dicts; the render loop mirrors the source barrier's live appearance and
draws nothing for open borders — stairs are reserved for floor-to-floor
travel and never appear on same-floor exits.

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

## BL-13 · CLOSED (investigated) · How unplayable levels slip through "playability-preserving" transformations

Root cause found: it is NOT a lossy graph transformation. The graph transforms
and single-grid push-puzzle placement are sound (`_place_puzzle` runs a full
backward Sokoban BFS; `validate_push_puzzles` re-checks and raises). The leak is
a MODEL MISMATCH: `puzzle_passable` (block placement) and `validate_push_puzzles`
both OMIT `water_tiles` (treating water as walkable floor), while
`_build_walls_multiroom` makes unbridged water SOLID. WATER edges place a stream
on the 1-tile wall between rooms, so water sits adjacent to room floor and can
land on a block's only push axis. Result: a block "solvable" on paper but
wall-flanked at runtime. Every other thing the `_verify_blocks` net can fire on
(another block / closed gate / locked door in the sole axis) is a false positive
the solver already models. Empirical sweep (25 seeds × 10 levels, 175
block-bearing levels): 2 stuck blocks, both 100% water-caused. Full analysis:
kb/architecture.md "Playability validation: the model boundary (BL-13)" and
kb/findings.md. The fix is tracked as a new backlog item (see below). Related:
BL-04.

---

## BL-14 · FIXED · Make the push-puzzle subsystem water-aware (remove the _verify_blocks safety net)

Fixed by spec 0048 (commit bcfd1b7, 2026-07-12): validate_push_puzzles builds
its obstacle model from build_room_cells via the shared RoomCells.blocked
(water solid, matching the runtime exactly); puzzle_passable subtracts water at
placement; _build_super_grid re-validates every stitched room (LayoutError ->
fresh-seed retry). Sweep (scratchpad/sweep_stuck_blocks.py): 0 stuck blocks
across 250 levels / 175 block-bearing (baseline 2/175).

The level generator can place a pushable block beside an inter-room water stream
so that the block's only clear push axis runs along/onto a water tile.
`puzzle_passable` (in `build_level_dict`, levellayout.py) is computed as
`interior - walls - gate_tiles - lock_tiles` and never subtracts `water_tiles`;
`validate_push_puzzles` builds `all_obstacles` from walls+doors+gates+blocks
only. Both treat water as walkable floor. But `_build_walls_multiroom` (game.py)
makes unbridged water solid, so such a block is unsolvable/stuck at runtime. The
runtime `_verify_blocks` net masks this by force-regenerating the level (and also
produces false-positive regenerations on already-visited grids the player has
rearranged).

Fix hint:
1. Subtract `water_tiles` from `puzzle_passable` before placing puzzles, and add
   them to `all_obstacles` in `validate_push_puzzles`. Water is solid until a
   bridge is crafted, which the puzzle solver has no model for, so treat it as a
   permanent obstacle for puzzle solvability.
2. Add a global post-stitch playability check in `_build_super_grid` (validation
   currently runs per-grid inside `build_level_dict` and never on the stitched
   whole).
3. Once placement is water-aware and the global check exists, `_verify_blocks` in
   game.py becomes a should-never-fire assertion rather than a load-bearing
   safety net — downgrade or remove it.
Verification: extend the headless sweep in scratchpad/repro_bl13.py (or a proper
test) to confirm zero water-caused stuck blocks across many seeds. Cross-reference
kb/architecture.md "Playability validation: the model boundary (BL-13)". Related:
BL-04 (water-crossing check too permissive) is part of the same water-model story
and may be folded into this fix.

---

## BL-15 · FOLDED INTO spec 0030 · Place keys with priority in the layout item-placement order

The collectible placement order has been decided as **keys → planks → treasures
(award items) → other materials** (after flames and push puzzles), with
spill-to-corridor for overflow. NOTE the order changed: keys are now placed
FIRST, BEFORE planks (not "right after planks" as originally written here). This
item is fully covered by `spec/0030-key-placement-fixes.md` (K1) and
`spec/0029-water-challenge-fixes.md` (W1); see those specs for the authoritative
resolution.

---

## BL-16 · FIXED · Don't place items on the player start tile (next to the entrance)

Fixed in 8ddf94b (spec/0057-no-items-on-player-start.md), confirmed by
Daniel 2026-07-11. `global_used` is seeded with `player_start` and the
entrance tile on the start grid (invariant R-P8 in kb/requirements.md);
sweep went from 8 violations in 40 seeds to 0, goldens byte-identical.

Treasures, materials, and keys can currently spawn on the `player_start` tile
because `player_start` is never added to `global_used` in `build_level_dict`
(levellayout.py). An item under the player at spawn is auto-collected or visually
wrong.

**Fix hint:** add `player_start` (and consider the entrance tile) to `global_used`
before any item placement, or exclude it inside `_place_items_in_room`, so nothing
lands on the player's starting position.

---

## BL-17 · WONTFIX · Completely empty rooms are still generated

Dropped by design decision (Daniel, 2026-07-12): the fix is expected to do
more harm than good — forcing an item into every room would hurt more than
the dead space it fixes. Empty rooms stay as acceptable variety.

Some generated Act 2 rooms contain no items or enemies at all (dead space) —
observed during testing. Treasure/material/enemy distribution in
`LevelGraph.generate` / the builder assigns to `rng.choice(all_nodes)`, so some
nodes receive nothing.

**Fix hint:** guarantee every non-corridor room gets at least one item — e.g. a
round-robin seeding pass over rooms before the random distribution, or a
post-layout check that drops a treasure into any room that ended up empty. Verify
with a headless sweep that no non-corridor room is empty across many seeds.

---

## BL-18 · P3 · Bridge-building variety: 4-plank bridges from mixed plank sources (single planks, packs of two, wooden doors)

Goal: add variety to how the player gathers the planks needed to bridge to a
water room.

Changes:
1. A bridge costs 4 planks instead of 2, matching the bridge sprite (which
   depicts four planks). Update the `CRAFT_BRIDGE` recipe in `crafting.py` from
   `{MAT_PLANKS: 2}` to `{MAT_PLANKS: 4}`.
2. Floor plank pickups come in two forms: a single plank (1 plank — NEW item
   type and NEW sprite) and a pack of two planks (2 planks — existing-style
   plank sprite). Today planks are placed only as individual `('planks',)`
   materials worth 1 each; this adds an explicit single vs. pack distinction
   with distinct sprites.
3. Breaking down a wooden door (smashing a wooden entry) yields HALF a bridge's
   worth of planks — 2 planks under the 4-plank scheme, NOT a full 4-plank
   bridge (Daniel, 2026-07-14) — as a non-scavenging partial alternative to
   collecting loose planks. This ties plank-sourcing to the existing breakable
   wooden wall/door mechanic (`WALL_WOODEN` / `BREAKABLE` edges).
4. The `add_water_room` algorithm (`levelgraph.py`) provisions, per water room,
   ANY valid combination of these sources whose total equals the equivalent of
   4 planks — e.g. 4 singles, 2 packs, 1 pack + 2 singles, or one wooden door
   (=2) plus a pack of two — chosen at random. All sources must remain reachable on the dry side
   and may be distributed across grids (fungible), per spec 0029.

Dependencies / interactions:
- Builds on and SUPERSEDES spec 0029's "2 planks per water room" provisioning:
  the invariant becomes "4-plank-equivalent per water room." The
  `validate_playability` check and the test targets from spec 0029 (W5/W6) must
  update from "2 reachable planks" to "4-plank-equivalent reachable."
- Requires new material/item handling (single vs pack) and sprites (a
  single-plank sprite; confirm the bridge sprite shows 4 planks).
- The "wooden door gives planks" rule interacts with the existing wall-break
  credit mechanic — decide whether a wooden barrier that funds a bridge still
  awards break credits.
- Needs its own spec before implementation; depends on spec 0029 landing first.

---

## BL-19 · FIXED · Push plates must not be placed next to a room's entrance tile

Fixed by spec 0049 (commits 21cd542 + eff31c8, 2026-07-12), generalised to
invariant R-P7: a plate never sits on the landing tile of any passage of its
room, existing or buildable — the solved puzzle (block parked on the plate)
must never seal a passage. Covers doorway landing tiles AND water flanks
(bridge landings); World._try_auto_bridge mirrors it at runtime. Note: the
first implementation scanned orig_walls (synthetic all-reinforced map) and
missed every doorway — caught by the statistical sweep
(scratchpad/sweep_plate_clearance.py): 61/1400 plates violated pre-fix,
0/1400 after; a 50-seed hypothesis property now guards it permanently.

Pressure plates for push puzzles can currently land on a tile cardinally
adjacent to the room's entrance/connection tile. That is awkward (the player
steps in and is immediately beside the plate) and can trivialise or cramp the
puzzle.

**Fix hint:** in the push-puzzle placement (`_place_puzzle` / `build_level_dict`
in `levellayout.py`), exclude tiles cardinally adjacent to the room's entry tile
(the connection tile from the corridor, found via `_find_connection_tile` — the
same way flame-jet entry detection works) from the plate candidate set.

---

## BL-20 · FIXED · Place enemies only in rooms of width >= 3 and height >= 3

Fixed in bbf02ea (spec/0058-enemy-award-placement.md — the enemy & award
economy redesign), confirmed by Daniel 2026-07-12. Enemies are
layout-distributed (2 x G per level, capacity s - 2 over the largest
all-floor square, corridor banned); invariant R-P9.

Enemies placed in narrow rooms (bounding box width < 3 or height < 3) can trap
the player with no room to dodge. Restrict enemy start placement to rooms whose
placed bounding box is at least 3x3.

**Fix hint:** in enemy distribution (`LevelGraph.generate` / builder
`add_enemies` in `levelgraph.py`) or at layout time (`_place_items_in_room`
`enemy_starts` in `levellayout.py`), skip placed nodes with `w < 3` or `h < 3`;
only assign/place enemies in rooms meeting the threshold (the corridor is large
and remains eligible). Verify with a headless sweep that no enemy start lands in
a sub-3x3 room.

---

## BL-21 · FIXED · Reduce the number of rooms in level 11

Fixed in 7d4cfd5 (spec/0060-act2-room-scaling.md), confirmed by Daniel
2026-07-12: level 11 is (2, 4) rooms on plain spines.

Level 11 (the first Act 2 level, `ACT2_FEATURE_SETS` index 0) generates too many
rooms for an introductory Act 2 level. Reduce its `room_count` range.

**Fix hint:** in `levels.py` (`_act2_feature_sets`), lower the `room_count`
tuple for index 0 (level 11).

---

## BL-22 · FIXED · Remove the more complex layout options from levels 11-13

Fixed in 7d4cfd5 (spec/0060-act2-room-scaling.md), confirmed by Daniel
2026-07-12: 11-12 = horizontal/vertical, 13 = horizontal/vertical/l;
l added to 14-20; exit sides constrained to strategy coverage.

Early Act 2 levels (11-13, `ACT2_FEATURE_SETS` indices 0-2) should ease the
player in with simpler corridor layouts. Remove the more complex strategies
(`z/s`, `l`, `double_t`) from their `layout_strategies`, leaving simpler ones
(`horizontal`, `vertical`, `off_centre`, `t`).

**Fix hint:** in `levels.py` (`_act2_feature_sets`), trim the
`'layout_strategies'` lists for indices 0-2.

---

## BL-23 · FIXED · Silent node (room) drops during layout — multi-grid closets

Root cause: 432/434 dropped nodes were CLOSETS; the multi-grid path
(_build_super_grid._build_subgraph) copied only the corridor's direct room
neighbours, so closets (which attach to a room, not the corridor) were never
copied into any per-grid subgraph and were silently dropped (single-grid dropped
0%). Fixed by spec 0032: closets are generated one-per-room at ~10%, copied into
per-grid subgraphs (C6), and CARVED from the parent's own tiles as a back/side
office or corner toilet (C2-C5); content of any un-carvable closet or dropped
room is spilled to the room/corridor so nothing is lost (C7). Also: closets are
excluded from zone room-count (no unoccupied zones) and never carved from a
push-puzzle room. Commits e0691e0, 86647dd, 48ca6ed, 1da849e. Full suite 415
passed; user-confirmed in-game (closets render well, no bad layouts across many
grids). Invariants now hold: keys_dict==keys_graph, planks_dict==planks_graph.

---

## BL-24 · FIXED · "The forge is defeated" text overflows the message box

Fixed in 0f2b59f (spec/0059-overlay-box-fit-text.md), accepted via
screenshot goldens 2026-07-12. The win message is now an unconditional
"YOU  WON!" (the forge sentence was rejected in review; its branch was
dead code), and overlay_box_width makes every overlay box auto-fit its
text (min 420 px, clamped to LOGICAL_W - 40) as a permanent safety net.

The message shown when the forge (forge ogre) is defeated — text along the lines
of "The forge is defeated" — is too long and overflows its message/dialog box.

**Fix hint:** locate the exact string (it may be a gettext-translated string in a
.po/.pot locale file or a dialog/message call — grep the codebase and locale
files for "forge"/"defeat"), and the routine that renders the message box
(`game.py` / `main.py`). Either shorten the message, wrap the text across lines,
or size the box to the text. Check other in-game messages don't overflow either.

---

## BL-25 · FIXED · Scale room count with grid count so late Act 2 levels aren't boring full-border grids

Fixed in 7d4cfd5 (spec/0060-act2-room-scaling.md), confirmed by Daniel
2026-07-12: per-grid ramp (2, 4) at level 11 up to (40, 60) at level 20;
generation got FASTER (level 20 worst 1.5 s, was 3.8 s).

Levels 19-20 are visually boring: most grids are laid out with the `full_border`
strategy because each grid contains only ONE room. Cause: in
`LevelGraph.generate` the total `room_count` is split across grids
(`rooms_per_grid = room_count // grid_count`, ~line 410); with grid_count up to
10 and a small room_count, each grid gets ~1 room, and a 1-room grid can only use
full_border (1 zone).

**Fix:** scale total room_count with grid_count so each grid receives several
rooms. Target progression: about 2-4 rooms in level 11 (1 grid), increasing
smoothly to about 40-60 rooms in level 20 (10 grids) — i.e. roughly 4-6 rooms per
grid at the top end. Adjust the `room_count` ranges in the `ACT2_FEATURE_SETS`
(`levels.py` / `_act2_feature_sets`).

Cross-reference BL-21 (reduce rooms in level 11 — this scaling subsumes/refines
it; reconcile the two) and BL-22 (remove complex layouts from levels 11-13).
Verify with a headless sweep that few/no grids fall back to full_border at high
levels.

---

## BL-26 · FIXED · Gate unfinished crafting content behind constants (hide unused recipes/tools, disable scrap-metal drops; rename user walls → BLOCKs)

Fixed by spec 0073 (`spec/0073-tester-build-gating-blocks-rubble-metal.md`, all
six deliverables D1–D6 ticked), confirmed in-game by Daniel 2026-07-14. The
user-built wall was renamed to BLOCK throughout, including code, with plural HUD
labels BLOCKS/BRIDGES (commit f01b3a1, D1). Blocks and bridges are now earned as
half-credits (mining a wall or collecting rubble = half a block; a pack of planks
= half a bridge; two halves make one), and the block/bridge recipes plus the
crafting-menu placement path were dropped — rubble and planks are credit-only
(commit c634c31, D2). Scrap-metal drops are gated off by `ENABLE_METAL=False`
(commit ad6fb76, D4); rubble was instead sprinkled more generously via
`RUBBLE_BUDGET_SCALE=2.0` (~9–24 per level, commit 6d0b22d, D3); and the
inventory/crafting overlay is disabled by `ENABLE_INVENTORY_MENU=False` (commit
d21a967, D5).

`ENABLE_METAL` and `ENABLE_INVENTORY_MENU` (both in `constants.py`) are the
flip-back-on gating constants for the metal and inventory content. The metal
reinforce feature (BL-54) depends on metal being re-enabled.

To present a clean "unfinished but nice" build for user testing, hide crafting
content that has no gameplay yet. (1) Add constants to disable placing the
material pickups the user calls "rubble" (MAT_ROCKS, display 'Rocks') and "scrap
metal" (MAT_METAL, display 'Scrap Metal') in generated levels. (2) Add constants
to hide the currently-unused recipes — Bell, Barricade, Portal Pair, Compass —
and the tools only those recipes use — Hammer, Chisel, Runestone — from the
crafting UI. Used content stays: Bridge (planks) and Stone Wall
(rocks→quick-place).

**Fix hints:** material distribution lives in `levelgraph.py` (`add_materials` /
`_act2` distribution); recipes/tools/UI live in `crafting.py` (`RECIPES`,
`TOOL_*`, the crafting menu render in `game.py`).

**CAVEAT:** MAT_ROCKS currently also feeds the *used* Stone Wall recipe and the
quick-place-wall path (`Inventory.can_quick_place_wall`), so disabling rubble
drops must not break wall placement — resolve in the spec (e.g. keep rocks usable
but stop dropping them as loose pickups, or rework quick-place). Crystal (Forge
Crystal) feeds only unused recipes too — consider including it.

**Note:** crafting a stone wall currently does not increment the wall counter, so
it does not let the player place more walls (crafted stone walls and the
placeable-wall counter are decoupled).

**CLARIFICATIONS (Daniel, 2026-07-14).** The full spec is being written as
`spec/0073` (or the next free number); these amend the scope above:

1. **Rename user-built WALLs to BLOCKs throughout the game, including code.**
   This covers the "WALLS" HUD counter, the `CRAFT_STONE_WALL` craftable, the
   placed-wall sprite/colour, the place-credit vocabulary, and the related
   events/sounds — everything referring to the *user-built* wall becomes
   "block". This is ONLY the user-built walls: the level's own wall terrain
   (`WALL_STONE` etc.) is NOT renamed.
2. **Collecting rubble automatically earns HALF a BLOCK** (i.e. 2 rubble = 1
   placeable block), reusing the existing half-credit "lower-half-block" HUD
   indicator shipped in spec 0072.
3. **Rubble stays — do NOT hide or remove it.** Rubble now feeds the
   block-credit mechanic above, so it is intended content. Only METAL (scrap
   metal, MAT_METAL) drops are hidden/disabled. This OVERRIDES the original
   "disable rubble & scrap-metal drops" wording, which should now read
   "disable scrap-metal (metal) drops only."

The existing recipe/tool-hiding scope (Bell/Barricade/Portal Pair/Compass +
Hammer/Chisel/Runestone) is unchanged, and the CAVEAT stands: MAT_ROCKS also
feeds the Stone-Block path — which is now the intended path (via the half-block
rubble credit above), no longer merely a used side effect to preserve.

---

## BL-27 · FIXED · Key inventory display: drop the counter (keys are unique) and check for a display bug

Fixed by spec 0071 (`spec/0071-key-display.md`, all four deliverables D1–D4
ticked), commits 041e394 and 6ef8709. The inventory key counter was dropped
(keys are unique), and a coloured key strip was added to the HUD status line:
per-level colours, ghost icons for keys not yet held, hidden entirely when the
level has no keys (`World._level_key_colours` + `_hud_key_strip`). The suspected
display bug was resolved as part of the redesign.

Keys are unique — at most one of each colour — so the inventory should not show a
quantity counter next to a key. During play the key inventory sometimes looked
wrong.

**Fix hints:** find the inventory rendering in `game.py` (the inventory/crafting
screen that lists keys alongside materials) and render keys without a count; while
there, investigate the suspected display bug (e.g. stale entry, wrong colour,
miscount, or a key shown/not shown incorrectly). Cross-reference spec 0030 (keys
are now reliably placed, so a wrong display is a UI bug, not a generation bug).

**Note:** Display the coloured key icons also in the status line (HUD), not only
in the inventory view.

---

## BL-28 · FIXED · Auto-craft a bridge when bumping water (no crafting-menu step)

Fixed by spec 0072 (`spec/0072-auto-craft-bridge-and-hud-counter.md`, all five
deliverables D1–D5 ticked), confirmed in-game by Daniel 2026-07-13. Bumping
water now auto-CRAFTS a bridge from planks and places it in one action, with no
crafting-menu step (commit bc151ce), and a HUD BRIDGE counter was added to the
left of the WALL counter (commit ac86c96), shown only when the level contains
planks. Scope grew well beyond the original ask: spec 0072 also delivered an
object-oriented HBox HUD redesign in a new `hud.py` (commit fbbbe45), with
gap-separator bands, one unified HUD text colour, a dim SHIELD placeholder,
length-preserving dash leaders, and drawn underscore / lower-half-block tail
indicators. See the spec for the full record.

Bridges are already auto-PLACED by bumping into a water tile if the player holds a
bridge item (`game.py` `_try_auto_bridge`). Extend this so bumping water also
auto-CRAFTS the bridge from planks when the player has none crafted: if
`not inventory.has_item(CRAFT_BRIDGE)` but `inventory.can_craft(<bridge recipe
index>)` (>= 2 planks), craft it then place it in one action, without opening the
crafting menu. Keep the one-bridge-per-water-room lock (spec 0029 W2) and the
far-side-open check unchanged.

**Fix hint:** in `_try_auto_bridge`, before the `has_item` check, attempt an
auto-craft; the bridge recipe is `CRAFT_BRIDGE` in `crafting.py` `RECIPES`.

Follow-on UI: with bridges auto-crafted and auto-placed on bump, the player never
needs the crafting menu for bridges. Add a BRIDGE counter to the HUD, to the LEFT
of the existing WALL counter, showing how many bridges the player currently has
(or can craft). With that in place we could disable the crafting menu entirely for
the user tests, simplifying the UI for testers. Fix hints: the HUD/counter
rendering is in game.py (find where the WALL/placement counter is drawn); the
crafting-menu open/handler is also in game.py — gate it behind a constant so it can
be hidden for the test build (ties in with BL-26's 'hide unfinished content'
constants).

**HUD bridge counter — conditional visibility** (Daniel, 2026-07-13, established
while implementing spec 0071 / BL-27's HUD key tracker): show the BRIDGE counter
only when the level actually contains planks (a plank/plank-pack material somewhere
in the level); if the level has no planks, omit the counter entirely and let the
HUD's even-spacing redistribute its space — do not reserve an empty slot. This
mirrors the spec 0071 key tracker (`World._level_key_colours` + `_hud_key_strip`
returning `None` when the level has no keys). Reuse the same mechanism: a HUD
element in `game.py` `_render_hud` that may be a pre-rendered `pygame.Surface` OR
absent (`imgs.insert` only when non-None), so its space is redistributed once per
level. See spec 0071 D3 and `kb/uglycraft-display.md` 'HUD Layout' (item 5, key
tracker) for the pattern to copy.

---

## BL-29 · FIXED · Unsolvable level: grid edge attaches to a gate-locked zone of a corridor-based room

Fixed by spec 0042 (commits a564670, 4737109, 0e8d284). Grid connections into
corridor-based rooms now stitch to a reachable corridor/spine segment instead of
a gate-locked interior zone. See spec/0042-border-corridor-stitch.md (checklist
complete) and user-confirmed in play ("Much better now", levels 13/16). Follow-up
spine widening is tracked separately as BL-30.

A grid connection from a border-layout room entered a double-T-layout room at the
top-right zone (a gate-locked sub-room) rather than at the top vertical corridor
segment. The double-T room's push puzzle for that gate was in a *different*
sub-room of the same grid, so the player was locked inside the room connected to
the grid entry, unable to reach the puzzle — the level is unsolvable.

**Expected:** a grid connection into a double-T (or any corridor-based) layout
should attach to a corridor/spine segment that is reachable without first passing
through a gate, not to a gate-locked interior zone.

**Fix hint:** when choosing the attachment cell/door for a grid edge into a
multi-zone room layout, prefer the shared corridor (vertical/horizontal spine)
over gate-locked zones; validate that the entry zone is reachable from the rest of
that room's grid without the gate, else relocate the connection.

---

## BL-30 · P3 · Widen corridor spine width to 2-5 (match unified stem range) after closet redesign

Spec 0042 (BL-29) unified stem widths to 2-5 but deferred spines: widening spine
width regresses corner-closet nesting (a wider corridor starves the parent room
band; `_nest_closets` fails the notch and `_place_closet_adjacent` drops the
closet into the corridor, causing direct floor adjacency / multiple passages).
Closets are being redesigned by another agent.

After that redesign, widen the spine width draws in `_layout_horizontal`
(`cor_h`), `_layout_vertical` (`cor_w`), `_layout_off_centre` (`cor_h`) and
`_layout_corridor` spine (`arm_h`) from `randint(2, 3)` to `randint(2, 5)`, and
verify `tests/test_room_shapes.py::TestCornerCloset` plus the full suite stay
green.

Purpose: more strategy variety when a child grid must match a wide parent
corridor band during cross-grid continuation.

**Fix hint:** see `spec/0042-border-corridor-stitch.md` "Spine widening deferred"
and `kb/requirements.md` R-T5.

---

## BL-31 · FIXED · Ensure the level entrance is created next to a corridor tile, which becomes the player start position

Fixed in a8e5997 (spec/0053-entrance-player-start-anchoring.md), confirmed by
Daniel 2026-07-12. The player start was always corridor-owned; the actual
defect was the `_pick_entrance` col-0 fallback (all corridor-reached sides
BORDER-occupied, 6/150 Act 2 levels) placing the entrance up to 14 tiles from
the start. Fix: **grid zero** — the outside of the dungeon occupies super-grid
origin (0,0), blocked for the spanning tree on every Prim step; the start grid
sits at delta(S) of grid zero's random pseudo-exit side and its face back
toward the origin (`graph.entrance_side`) never carries a BORDER edge and
holds the entrance, with player_start on the corridor tile inside. Fallback
deleted (LayoutError guard). Detector sweep post-fix: 0/150 violations.
Invariant R-T6; tests/test_entrance.py; golden act2_L13_walk re-recorded (and
flaky per process until BL-40). Grid zero is kept upgradeable (future: door
opens on full loot into a grid-zero boss arena — see spec 0053).

The original fix hint related this to BL-16 (don't place items on the player
start tile), which remains open and independent.

---

## BL-32 · P3 · Native-resolution rendering port (GamePi 800×480 + desktop native TILE)

Implement spec/0043-native-resolution.md: grid 29×15, per-display TILE
(27/66/35), sprite proportionalization, HUD font fit rule,
poe render-sprites / render-levels tasks.

**Fix hint:** spec 0043 is committed and awaiting confirmation; start with the
render tasks as verification harness.

---

## BL-33 · FIXED · Act 1 crashes on first render: `_current_room_data` unset in single-room path

Fixed in ec6ffcd ("fix: guard entrance sprite render for single-room levels").
Test-first via tests/test_render.py::test_act1_render_smoke (spec 0044 H8).

`_render_field` (game.py:1230) unconditionally reads `self._current_room_data`,
which is only assigned in `_enter_room` (multiroom/Act 2 path). Any Act 1 game
(`_full_reset` → `_start_level(1)` → render) raises `AttributeError`.

Regression introduced by 04be23e (feat: render level_entrance sprite,
2026-06-28), i.e. after v1.5 — unreleased.

Repro: headless `Game(surface); g._full_reset(); g.render()` with
state=playing.

**Fix hint:** the entrance/staircase render block only applies to multiroom
levels — guard it with `if self._is_multiroom:` (the staircase loop below it
already is), or initialise `self._current_room_data = None` in the
`_start_level` single-room branch and guard both reads.

---

## BL-34 · FIXED · Act 1 enemies never chase the player — wander on both difficulties

Fixed in df1456f ("fix: Act 1 enemies chase again — unconfined enemies pursue").
Test-first via tests/test_harness.py::test_act1_enemy_chases; the 17 spec-0044
goldens were re-recorded and reviewed.

Act 1 enemies wander randomly regardless of difficulty. The enemy-dispatch
condition in `_update_playing` (game.py,
`elif (enemy.room_name and player_room == enemy.room_name)`) requires a truthy
`enemy.room_name`, but Act 1 enemies keep the `Enemy.__init__` default
`room_name = None`, so the chase branch (greedy easy / BFS hard) is unreachable
and every Act 1 enemy falls through to `wander()`. Hard mode computes the BFS
distance map and never uses it.

Regression introduced by 9b9ed4a (fix: enemies wander when player is on
doorway/connection tiles, 2026-06-25), i.e. after v1.5 — unreleased.

Found by the spec-0044 characterization harness (hard and easy level-1 traces
came out identical).

**Fix hint:** chase when unconfined OR the player is in the enemy's room —
e.g. `elif enemy.room_name is None or player_room == enemy.room_name:` — while
preserving 9b9ed4a's intent (Act 2 enemies wander when the player is outside
their room / on connection tiles, where `_player_room()` returns None). After
fixing, re-record the affected spec-0044 goldens (`UGLYCRAFT_REGOLD=1`) and
review the diff.

---

## BL-35 · DONE · World-model refactor, staged

World-model refactor, staged (→ kb/world-model-review.md §3, §6.6): make
gameplay logic testable and new elements cheap to add. Step 0 (spec 0044
characterization harness) and Stage 1 (spec 0045 World extraction, commit
abe3d16) are DONE; Stage 2 (spec 0046 Act 1 as one-room Act 2 level, commit
aa9b050) DONE — pending user play-test acceptance; Stage 3 (spec 0047 layered
cell model, commits 182367a..32361be) DONE — user-accepted after shadow play +
post-deletion check; Stage 4 (spec 0050 behaviour dispatch + signal channels,
commit 401ac18) DONE — pending user play-test; Stage 5 (spec 0051 Room
objects, commit 42b4e8f) DONE — user-accepted 2026-07-12. ALL FIVE STAGES
COMPLETE; the candidate Stage 6 (content registry) is designed in
kb/world-model-review.md §7 and would be a new backlog item when picked up.

**Fix hint:** complete — one numbered spec per stage, each
behaviour-preserving and gated by the spec-0044 goldens; the solver-side reuse
of World.blocked landed as spec 0048; fine-grained World unit tests accumulate
from Stage 2 onward. Possible continuation: content registry (Stage 6), see
kb/world-model-review.md §7 — file as a new backlog item when picked up.

---

## BL-36 · FIXED · Room re-entry with a stuck block silently regenerates the whole level

Fixed by spec 0048 (commit bcfd1b7, 2026-07-12): _verify_blocks runs only on
first entry of a freshly generated room — player-wedged blocks on revisited
rooms never regenerate the level (user-confirmed in play with two mutually
wedged blocks); a mid-transition regeneration no longer teleports the player to
the stale entry tile. See BL-37 for the planned friendlier recovery (explode +
respawn), which will also supersede the on-death block reset.

Reported during spec-0046 acceptance play (2026-07-11): "sometimes a grid exit
leads you to a completely different level (you can't go back)". Root mechanism,
reproduced headlessly and confirmed identical on pre-refactor commit 6fc59a7
(NOT a 0045/0046 regression): `_verify_blocks` (world.py) runs on every
`_enter_room` and, if any pushable block in the entered room has zero push
directions, calls `regenerate_level` + `start_level` — the entire level is
rebuilt and all progress (loot, opened doors, broken walls) is lost. Two
triggers: (a) the player legitimately wedges a block into a corner/dead end,
leaves the room, and returns; (b) generator-produced stuck blocks from the
water-unaware push-puzzle validation (BL-14's known masking effect).
Compounding bug: `_try_room_transition` continues after the regeneration and
overwrites the player position with the STALE entry coordinates (e.g. a border
tile like (29,8)) in the freshly regenerated start room — the player can
materialise on a border/wall tile of an unrelated layout.

**Fix hint:** `_verify_blocks` should never fire for rooms whose blocks moved
only by player pushes (a player-wedged block is a solved/failed puzzle, not a
broken level) — restrict the check to first entry of a freshly generated room,
or drop the regeneration net entirely once BL-14 makes the generator's
push-puzzle validation water-aware (kb/architecture.md fix direction). If any
regeneration path is kept, `_try_room_transition` must not reposition the
player after a regeneration (check whether `start_level` ran, e.g. compare
`_level_data` identity, and skip the entry-coordinate write). Repro script: was
scratch repro_regen.py (job tmp, wedge block at (2,2) behind three walls in a
two-grid fixture, exit right, return).

---

## BL-37 · DONE · Wedged push-block explodes and respawns after an animated countdown

Feature idea (Daniel, 2026-07-12): when a pushable block is pushed onto a tile
from which its puzzle becomes unsolvable (zero remaining push directions, or
provably unable to reach its plate), the block should visibly react — start a
short animated countdown on the tile, then explode and respawn at its starting
position — instead of silently staying wedged. This is the player-friendly
in-game recovery for self-inflicted wedges; it complements spec 0048
(BL-14/BL-36), under which wedged blocks simply stay wedged until death resets
them, and the regeneration net no longer fires on re-entry. Detection can start
simple (zero push directions, the old `_verify_blocks` condition, evaluated per
push) and later use the Sokoban solvability check; "unsolvable" must respect
bridged water and open gates at evaluation time (use `World.blocked` /
`RoomCells.blocked` from spec 0047/0048, never a private obstacle model — that
is the BL-13 bug class).

Mutually-wedged blocks ignite together (Daniel, 2026-07-12): when blocks wedge
each other — e.g. two blocks pushed adjacent so neither has a push direction,
confirmed reproducible in play during spec-0048 acceptance — the unsolvability
detection must treat the group as one: ALL blocks that are part of the wedged
configuration start their countdown and explode together, not just the
last-pushed one.

Supersedes the on-death reset of push puzzles (Daniel, 2026-07-12): once wedged
blocks self-recover by exploding and respawning, the `_reset_blocks`-on-death
mechanism (world.py: blocks reset to `_room_blocks_initial` and gates closed
when a life is lost) becomes redundant and should be removed in the same spec.
The game is then fully self-healing with respect to push puzzles, and dying no
longer wipes legitimately-solved puzzle progress.

**Fix hint:** needs its own spec. Runtime: hook detection into
`_try_push_block` (world.py) after a successful push; the detection must
identify the whole wedged group (not just the pushed block) so that all blocks
in a mutually-wedged configuration ignite together; add a per-block countdown
timer ticked in `World.update`, an event kind for the explosion (Game maps it
to a sound + flash/animation), and respawn from `_room_blocks_initial` for
every block in the wedged group. In the same spec, remove the now-redundant
`_reset_blocks`-on-death path in world.py (and its gate-closing on life loss).
Rendering: countdown/explosion animation in game.py/sprites.py. Interactions
to decide in the spec: blocks resting on plates must not count as wedged
(holding a gate open is the goal state), and the respawned block must not
materialise on top of the player/an enemy.

**Resolution:** Implemented by spec 0068
(`spec/0068-exploding-wedged-blocks.md`), user-accepted in-game 2026-07-12.
A push-block pushed out of its plate's safe area lights a 5 s red-glow fuse,
then explodes (4-frame blast, -500 points via `BLOCK_EXPLOSION_PENALTY`) and
respawns at its start (or nearest open tile); the block is confined to its
room floor. The safe area is computed by `cells.safe_block_positions` — a
player-zone reverse Sokoban confined to the room's own walkable floor
(openings/gates/doors excluded; every pull requires the player to be able to
walk to the push tile around the block) — stored on each plate fixture as
`plate.safe_tiles` and unioned by `Room.safe_tile_set`. The on-death
`_reset_blocks` path was removed (dying preserves solved-puzzle progress;
the spec 0067 player+enemy reset stays). Commits: 3a5b5a2 (feature) and
61eaf7a (final safe-set solver). 800 tests pass.

---

## BL-38 · DONE · Content registry — Stage 6 of the world model (consolidation only)

Picked up 2026-07-12 (Daniel: "do stage 6, but without introducing new
features yet"). Implements kb/world-model-review.md §7 minus the new-element
validation: a parse/behaviour/sprite registry over the four cell layers;
plates and flame nozzles become fixtures in the cell model; pushable blocks
become occupant objects with identity (prerequisite for BL-37);
build_room_cells iterates the registry so new kinds stop touching the parser.
Explicitly deferred, because they are behaviour changes / features: ray-cast
flame fields (beam occlusion by blocks), levers/buttons/machines (spec 0007),
BL-12 edge-type rendering. Behaviour-preserving, gated by the spec-0044
goldens as all prior stages.

**Fix hint:** spec 0052 (in flight); follow-up items when features come: lever
as first registry-validated element, ray-cast fields, BL-37 explosion using
Block identity.

**Resolution:** Done by spec 0052 (commit 75a166a, user-accepted 2026-07-12):
CONTENT_PARSERS registry drives build_room_cells; plates and flame nozzles are
generic fixtures; pushable blocks are Block occupants with identity (BL-37's
hook); sprite table + pinned system-order contract. 528 tests, goldens
byte-identical. The deferred feature halves (ray-cast beams, lever/machines
validation, wiring nets) remain listed in kb/world-model-review.md §7 for
their future feature specs.

---

## BL-39 · UNREPRODUCIBLE · Placing a second crafted bridge silently consumes it without effect

Long-standing observation from kb/findings.md that claimed to be "Backlog." but
was never actually filed (discovered during the 2026-07-12 housekeeping audit).
When the player has crafted multiple bridges, only the first placement
succeeds; subsequent attempts consume the bridge item from inventory without
placing anything. Root cause unknown — suspicion: `_try_auto_bridge` (world.py)
checks the one-bridge-per-water-room rule via `_bridged_water_rooms` BEFORE the
inventory check, so a refused re-bridge should NOT consume... the reported
consumption path needs reproducing first. May predate spec 0029's per-room
bridge lock.

**Fix hint:** reproduce headlessly first (craft two bridges via inventory, bump
the same/another stream, assert inventory count) — the world.py API makes this
a ~10-line unit test now; if the consumption is real, the bug is in the
ordering of `inventory.use_item` vs the refusal conditions in
`_try_auto_bridge`; add the red test to tests/test_world.py.

Closed as unreproducible (2026-07-12, prompted by Daniel suspecting staleness):
the prescribed reproduction (two crafted bridges, repeated bumps on an
already-bridged water room across multiple stream tiles) passes on current
code — every refusal path in `_try_auto_bridge` (world.py) returns before
`inventory.use_item`, so a refused bridge cannot consume. The permanent guard
test `test_refused_bridge_never_consumes_the_item` (tests/test_world.py,
commit 7343bbb) pins the ordering. The original observation probably predates
spec 0029, whose per-water-room lock replaced the old per-grid
`_bridges_remaining` cap. kb/findings.md entry updated accordingly (97d41bc).

---

## BL-40 · FIXED · Level generation output depends on PYTHONHASHSEED (cross-process nondeterminism; flaky golden act2_L13_walk)

Fixed in b7ffefb (spec/0054-deterministic-generation.md), confirmed by Daniel
2026-07-12. PYTHONHASHSEED salts **str** hashing only, so iteration over
str-sets of node names fed `rng.choice` pools in per-process order — five
sites in `LevelGraphBuilder` (`_reachable` and `_current_grid_rooms`).
`_reachable` is now a dict-as-ordered-set (insertion = reachability order),
`_current_grid_rooms` returns a list in edge order, and the dead
`_assign_items` (same pattern, no callers) was deleted. Draw sequence
unchanged, only pool ordering. Probe hashes identical across
PYTHONHASHSEED=0..3 for levels 11 and 13 (level 11 byte-identical to
pre-fix); act2_L13_walk re-recorded once and the golden suite passes 3× in
fresh processes; full suite 534 green. Guard:
`tests/test_generation_determinism.py` + probe `tests/_gen_hash.py`.
Rule for future generator code in `kb/architecture.md` "Process determinism".

---

## BL-41 · FIXED · Single-grid entrance side biased by fixed scan order (level 11: never right/bottom-rare)

Fixed in f30f8eb (spec/0055-single-grid-grid-zero.md), confirmed by Daniel
2026-07-12. Observed while play-testing level 11: the entrance was never
right, rarely bottom (200-seed measurement: left 64%, top 30%, bottom 6%,
right 0%) — `_pick_entrance`'s scanning mode took the first side the
corridor reached in fixed left/top/bottom/right order. Fix: grid zero
extended to single-grid levels — the pseudo-exit draw in
`LevelGraph.generate` is unconditional, and `build_level_dict`'s single-grid
path pre-picks a covering strategy and passes
`required_exits={entrance_side}` so the entrance lands deterministically on
the uniformly drawn side. Post-fix distribution: 53/52/50/45 over 200 seeds.
Multi-grid streams byte-identical (level 13 hash unchanged);
act2_L11_walk re-recorded once. R-T6 updated; tests in
tests/test_entrance.py (uniformity + anchoring down to grid_count 1).

---

## BL-42 · FIXED · Act 1 levels (1–10) shall have an entrance door at a fixed per-level position

Landed in 4677ce1 (Act 1 `entrance` keys + repositioned player/enemy starts)
and a141822 (`--dump-level` export), spec/0064-act1-entrance-doors.md.
Accepted by Daniel 2026-07-12 (manual check of levels 1–10). BL-43 (entrance
opens after all awards, level ends by leaving through it) builds on this.

Generated Act 2 levels (11–20) display a level entrance (stairs sprite on a
border tile next to the player start — spec 0053/0055 grid zero). The
hand-authored Act 1 levels (1–10) have no entrance at all. They shall get one
too, at a FIXED position defined per level (hand-authored, like their wall
layouts) — requested by Daniel 2026-07-12. Related: BL-43 (entrance door as
level exit) builds on this.

**Fix hint:** add an `entrance` key to each Act 1 level dict in levels.py (a
border tile per level, sensibly adjacent to the level's `player_start`);
`game.py` already renders `room['entrance']` when present (level-entrance
sprite blit, around game.py:499). Choose the 10 positions in a spec first
since they are per-level design decisions.

---

## BL-43 · FIXED · Entrance door opens after all awards are collected; level ends by leaving through it

Landed in 9076676 (spec/0066-entrance-exit-completion.md), sound in 87950fa
+ 1ab2a77. Accepted by Daniel 2026-07-12 (sprite, item collection, ta-daa
fanfare, and the two-press walk-out all confirmed on Act 1 and Act 2). The
entrance is a gate barrier on a reserved ENTRANCE_CHANNEL; collecting the
last award latches it open (walkable exit gap via the ordinary
cells.blocked query); an off-screen press while on the open door advances
the level. Act 1 enemies now confined to INTERIOR_TILES. The
_reset_blocks channel-preservation is temporary — it dies with BL-37.

For ALL levels (1–20): today a level ends the instant the last award item is
collected. Instead, collecting all awards shall OPEN the entrance door, and
the level shall end only when the player leaves the grid through that door —
requested by Daniel 2026-07-12. This realises the spec 0053 "Future
extension": the opened entrance gives way to grid zero (the outside). Depends
on BL-42 (Act 1 levels need an entrance first). Needs its own spec: touches
the world.py completion rules/event stream (replace instant level-up with a
door-open event + a transition trigger on the entrance tile), game.py
rendering (open vs closed entrance sprite) and sounds, and possibly
enemy/hazard behaviour while walking back to the entrance.

**Fix hint:** world.py holds the award-completion check (the 'level_up'
path); split it into award-completion → entrance-open state (new event for
game.py to switch sprite + play a sound) and a separate level-complete
trigger when the player steps onto the entrance border tile while it is open.
The entrance tile position is in room['entrance'] (Act 2; Act 1 after BL-42).
Mind death/reset semantics (does the door stay open after death?) — decide in
the spec.

---

## BL-45 · FIXED · Unsolvable push puzzle: block on the entrance landing tile of a 2-high room

Fixed in b0e86bd (spec/0063-anchored-push-puzzles.md), accepted via the
validated detector sweep 2026-07-12 (rare generative property — in lieu
of a play-test): pre-fix 14 landing-tile blocks + 5 entry-unsolvable
puzzles in 120 levels, post-fix 0. Solvers anchored to the player's
real entry (R-P11); block starts barred from landing tiles.

Observed in play by Daniel 2026-07-12. A 2-row room entered from the top; the
pushable block sits directly inside the entrance (on its landing tile), the
plate in the same top row further right:

```
Wall:                      #### #######
1st row of the room        #   B   P  #
2nd (last row of the room) #          #
Wall:                      ############

B = Moveable Block, P = Push Plate
```

Entering the room forces a push (the only way in is through B's tile), shoving
B into the bottom row. In a 2-high room a block in the bottom row can never be
pushed back up (no standing row below), so the plate is unreachable — the level
is unsolvable. The `_verify_blocks` net stays blind: the block still has free
left/right push axes, so `push_dirs > 0`.

**Fix hint:** this is the block-side mirror of R-P7 (spec 0049, plates never on
landing tiles): `_place_puzzle` / `validate_push_puzzles` in levellayout.py
should never place (or accept) a block START on a doorway landing tile — the
first entry is a forced, unmodelled push. Alternatively/additionally the
Sokoban solver's initial state must model entry: the player begins OUTSIDE the
room, and if the sole entrance's landing tile holds the block, the forced entry
push must be part of the search. Frequency likely raised by spec 0060's smaller
rooms (2-high rooms are common now). Needs its own spec; verify with a detector
sweep validated on a reproducing seed.

---

## BL-44 · FIXED · Interior locked doors silently elided when their key sits on another grid (orphan keys)

Fixed in c941f9c + 9060129 (spec/0061-no-silent-door-elision.md),
confirmed by Daniel 2026-07-12. Doors unconditional with a loud
LayoutError net; interior-gate plates roam; gate elision at global
scope; invariant R-K1 (sweep: 421 -> 0 violations / 120 levels).

Found in play 2026-07-11 (level 13: 5 keys, 3 doors). The spec-0030
barrier↔prerequisite coupling checked `placed_key_colours` per grid, but keys
roam cross-grid (R-V3), so doors were degraded to open passages and their keys
orphaned — also exposed challenge awards (spec 0058) in seemingly open rooms.

Note: fix already implemented in `spec/0061-no-silent-door-elision.md`
(commit c941f9c: unconditional doors + loud LayoutError; gate elision moved to
global scope; interior-gate plates roam) — awaiting Daniel's play-test
confirmation before closing this entry.

---

## BL-46 · FIXED · R-K1 violation found by hypothesis: per-colour key count != locked-door count (seed 584, single grid)

Fixed in c393fcc (spec/0065-loud-locked-edge-elision.md): the
build_level_dict barrier loop raises LayoutError for a LOCKED edge with
an unplaced endpoint or missing connection tile — door elision / orphan
key impossible; the standard fresh-seed retry absorbs the raise, and
escaping LayoutErrors now append a diagnostic entry to
uglycraft-layout.log. KB reconciled (R-P3/R-K1) in 32a2c7d. Pinned
regression: tests/test_key_placement.py::test_pinned_dropped_locked_room
(FS_ALL seed 584). Resolved 2026-07-12. Verification: full suite 727
passed; 300-build sweep_orphan_keys: 0 violations.

Found by hypothesis on 2026-07-12:
`tests/test_key_placement.py::test_key_door_pairing` failed with
"seed=584 fs grids=1: keys={'blue': 1, 'orange': 1, 'cyan': ...} != doors —
orphan keys or key-less doors" (message truncated in the log; per-colour key
count != locked-door count in a generated single-grid level). Not related to
spec 0064 (that session touched only Act 1 data and a read-only dump tool).

Note: hypothesis persists the failing example in `.hypothesis/`, so the full
suite will keep re-failing this test until fixed.

**Fix hint:** reproduce with the test's own `_build_retry(fs, 584)` over its
feature sets (tests/test_key_placement.py:~156). If a colour has MORE doors
than keys it is a soft-lock and should be re-triaged P1; an orphan key is
cosmetic. Suspect key/door elision paths in `levellayout.py` (gate/door
elision around line 794 was exercised only by failing examples per the
hypothesis coverage note). Related: BL-44 (R-K1, spec 0061).

**Investigated (2026-07-12), root cause found.** Deterministic repro:
`_build_retry(FS_ALL, 584)` (tests/test_key_placement.py helpers) succeeds on
attempt 0 and yields keys {blue, orange, cyan} but doors {blue, orange}. The
cyan LOCKED edge is corridor–room_5; **room_5 was dropped by the zone packer**
(absent from tile_owner), its spec-0032-C7 spill kept the level building, and
the cyan key — placed cross-room in room_3 by add_locked_room — survived per
K1. The edge loop in build_level_dict (levellayout.py ~2925, `if edge.node_a
not in placed or edge.node_b not in placed: continue`) silently skips the
door. Direction confirmed benign: orphan KEY, not a key-less door — no
soft-lock, P2 stands (the earlier levellayout.py:794 suspicion was a red
herring — that's z-layout geometry).

**Why spec 0061 missed it:** D1 explicitly preserved this path ("unplaced
endpoints keep today's behaviour") and its 8-seed diagnosis contained no
dropped locked rooms ("with no locked room ever dropped by the packer"), so
R-K1 was recorded stronger than the implementation guarantees. There is a real
invariant tension: K1 (keys are never lost) and R-K1 (per-colour #keys ==
#doors) cannot both hold when a locked room is dropped — one must yield.

**Incidence:** detector sweep 2026-07-12: 0/720 levels (300 FS_LOCKED + 300
FS_ALL + 60 FS_CROWDED_LOCKED + 60 real level-13 sets, seeds 0..N) — well
under 0.2% per build; hypothesis found the one needle at seed 584, now
persisted in `.hypothesis/` so the suite re-fails until fixed.

**Recommended fix (needs its own spec):** make the residual case loud,
matching the 0061/0048 philosophy — in the build_level_dict edge loop, a
LOCKED edge with an unplaced endpoint raises LayoutError (standard fresh-seed
retry; sweep says the retry cost is ~zero) instead of silently continuing.
This also covers an uncarvable closet on a LOCKED edge. Alternatives
considered and rejected: dropping the orphan key too (violates K1 and its
tests; hides the spilled-award-without-challenge side effect), weakening the
R-K1 test (hides the same). The sibling silent path in the same loop
(`conn is None` for a LOCKED edge between placed nodes) should get the same
loud treatment — R-E4 makes it should-be-unreachable, so a raise costs
nothing. Cross-ref: spec/0061-no-silent-door-elision.md D1,
kb/requirements.md R-K1 + R-P3 (whose "unplaced nodes are a bug" note is
contradicted by legitimate packer drops + C7 spill — reconcile wording when
fixing).

---

## BL-47 · DONE · Speed up the test suite (10:30 wall clock)

**DONE (specs 0069 + 0070).** Shipped pytest-xdist: `poe test` now runs
`-n auto` (spec/0069-parallelize-test-suite.md) — measured ~2.1× on this
machine (~10:30 serial → ~4:57 parallel), zero code change. Then a generation
hot-path optimization (spec/0070-generation-hot-path.md): bounding-box prune in
`validate_layout` plus a `_comp_map` hoist / `get_zone` inline in
`_place_puzzle` — byte-identical generator output; cProfile 29.4 s → 24.8 s
(−15.6 %), full suite ~4:57 → ~4:03 (−18 %). Combined with xdist: ~10:30 →
~4:03 ≈ **2.6×**. See the "Generation performance" section of
kb/architecture.md.

Key finding: this machine is 2 physical cores (i5-3320M, HT → 4 logical), so
the suite is CPU-core-bound. The xdist ceiling is ~2.1× and item-splitting adds
no wall-clock gain here — only ≥3–4 physical cores (or CI) would benefit, and
none exists. Build memoization is useless: measured 1–3 % duplicate (fs, seed)
builds because hypothesis draws independent seeds. Fix-hint options (b)
hypothesis profile and (c) shared memoized build fixture are therefore NOT
pursued — (c) is disproven by the 1–3 % measurement; (b) would weaken coverage.
Further speedup would need deeper generation optimization (diminishing returns
beyond spec 0070) or more physical cores.

From the 2026-07-12 test-suite review (to be discussed before implementation).
Measured with `--durations=50` on 2026-07-12: 722 tests in 10:30. Act 2
generator property sweeps ≈ 6 min (worst single test:
`test_key_placement.py::test_key_door_pairing` 61 s = 25 hypothesis examples ×
4 feature sets; `test_entrance` ≈ 58 s, `test_border_continuity` ≈ 41 s,
`test_sokoban` ≈ 39 s, `test_placement_rules` ≈ 34 s, `test_act2_solvability`
≈ 30 s per file). Pygame harness/golden/screenshot tests ≈ 3 min at a flat
~2.5 s each.

**Fix hint:** in order of effort: (a) pytest-xdist `-n auto` — tests are
independent and CPU-bound, likely 4-8× wall-clock cut, zero code change;
(b) a hypothesis settings profile (fewer `max_examples` for local runs, full
sweep on demand via env var); (c) structural: the sweep files each rebuild
near-identical (feature-set, seed) levels — a shared memoized build fixture
would dedupe most generation work but touches many test files.

---

## BL-48 · P3 · Reuse leveldump in existing tests: failure diagnostics + readable goldens

From the spec 0064 review (2026-07-12 test-suite review; to be discussed
before implementation). Enabler: a small public dict-level entry point in
`leveldump.py` that renders an already-built level dict via `Room.from_data`
(no World, no `get_level`) — generator sweeps build raw dicts from custom
feature sets which `dump_level` cannot reach.

**Enabler landed** (commit c393fcc, spec 0065 D2):
`leveldump.render_rooms(rooms, positions, failed=None, difficulty=HARD)`
renders raw room dicts via `Room.from_data` at explicit super positions —
no World, no `get_level`; unit-tested in `tests/test_layout_log.py`.
Items (a)–(d) below remain open.

Then: (a) attach the ASCII render to assertion failures in the generator
sweeps (`test_act2_solvability`, `test_key_placement`, `test_placement_rules`,
`test_entrance`) — hypothesis failures currently print bare counters (see
BL-46 for a live example that would have benefited); (b) `tests/_gen_hash.py`
emits the dump alongside the sha256 so a determinism failure yields a readable
diff; (c) dump-goldens for the hand-written mechanic fixtures in
`tests/act2_fixtures.py` (their comment diagrams can drift); (d) extend
`tests/test_leveldump.py`'s masked verbatim pin from level 2 to all ten Act 1
spec-0064 diagrams, locking spec drawings to shipped data.

---

## BL-49 · P3 · New dump-based robustness tests (content conservation, canvas topology)

From the spec 0064 review (2026-07-12 test-suite review; to be discussed
before implementation). Depends on BL-48's dict-level entry point.

(a) Rendered-content conservation: every key/material/treasure/enemy/block in
a built level dict must appear as its symbol in the ASCII render — a symbol
swallowed by a wall/water tile is a placement bug invisible to dict-level
counting; piggyback on levels the existing sweeps already build (near-zero
extra generation cost); needs per-kind stacking rules (a plate under a block
is legitimate). (b) Canvas topology invariants over shipping content (levels
11-20 × a seed or two): exactly one E/P, both in the start grid; border rings
closed except X/D/G/E; facing stitch openings aligned; the canvas BFS in
`leveldump` already raises on inconsistent stitch topology, doubling as a free
structural validator. (c) Compare dump text across `PYTHONHASHSEED` values in
the existing subprocess probe (`test_generation_determinism.py`) as a readable
BL-40 regression net.

---

## BL-50 · DONE · On death, player AND all enemies respawn at their original start positions

On any life loss, the player and every enemy should return to their level/room
start positions. Currently `_lose_life` (world.py) moves the player back to
`player_start` and resets blocks, but enemies are NOT returned to their level
start positions — they stay wherever they had wandered to. `_respawn_enemy`
only relocates a single caught enemy far from the player, not a full reset. On
death the level should snap back to its initial actor layout: player at
`player_start`, each enemy at its original `enemy_starts` position for the
current room/level.

**Fix hint:** in `_lose_life` (world.py), after repositioning the player, also
restore each enemy's (col, row) from the room's original `enemy_starts`.
`Room.from_data` builds enemies from `data['enemy_starts']`; the initial
positions likely need to be captured at room construction (analogous to
`blocks_initial` / `_room_blocks_initial`) so the original coordinates survive
enemy movement. Relates to spec 0066 death semantics and BL-37 (exploding
blocks / self-healing level, which will supersede `_reset_blocks`).

**Resolution:** Implemented by spec 0067
(`spec/0067-death-respawn-reset.md`, commit cbfe8ea), user-accepted
2026-07-12. Enemy respawn is made safe in every grid (never into a wall,
never on/beside the player, never sealed in a pocket) via
`World._reset_enemies` / `_player_reach` / `_respawn_enemy`; the caught
enemy is reset with the rest (pre-death relocation now only on a shielded
hit).

---

## BL-51 · DONE · Disallow placing a user-crafted block/wall at the player respawn position

A player-placed wall (or crafted block) on the `player_start` tile would trap
the player on respawn after death — they would materialise inside a wall. Forbid
placing a wall or crafted item on the current room's/level's `player_start`
(respawn) tile.

**Fix hint:** guard the placement paths in world.py (`_place_wall` and
`_act2_place`) — reject placement when (c, r) == the current room's
player_start / respawn tile. Depends conceptually on BL-50 (which defines the
respawn position that must stay clear).

**Resolution:** Implemented by spec 0067
(`spec/0067-death-respawn-reset.md`, commit cbfe8ea), user-accepted
2026-07-12. `World._is_respawn_tile` guards both `_place_wall` (Act 1) and
`_act2_place` (Act 2); placement on the start room's `player_start` is
rejected silently without consuming the credit/item.

---

## BL-52 · FIXED · A single shared "disallowed action" SFX, played whenever a deliberate action is refused

Today when the player attempts a deliberate action that the rules refuse, the
game is silent — there is no audio feedback that the action was disallowed. Add
ONE shared sound effect (the same sound for every case) that plays whenever such
an attempted action is rejected. This is about refused DELIBERATE actions
(SPACE / bump-to-interact), NOT walking into a plain wall (that already has the
'bump' sound and would be too noisy).

Surveyed refusal sites in the code (all currently return silently with no
distinct event/sound) — the SFX should fire at each:
- **Locked door bumped without the matching key:** world.py `_try_auto_open_door`
  (barrier is a door but `inventory.has_key(colour)` is False).
- **Bridge refused:** world.py `_try_auto_bridge` — no bridge item / not enough
  planks (`inventory.has_item(CRAFT_BRIDGE)` False), water room already bridged,
  landing tile carries a plate, or no open floor on the far side.
- **Wall/block placement refused:** world.py `_place_wall` (Act 1: no
  `_place_credits`, target blocked, or target is the respawn tile) and
  `_act2_place` (Act 2: no crafted wall item and can't quick-place, target
  blocked, or respawn tile).
- **Placement on the respawn tile / player_start** (spec 0067 `_is_respawn_tile`),
  and any future "no placing right next to an entry/entrance" rule — Daniel
  explicitly wants the denial sound here.
- **Buy shield refused:** world.py `buy_shield` — insufficient score or already
  shielded.
- **Crafting a recipe without enough materials:** game.py inventory handler
  (~line 405) where `inventory.can_craft(cursor)` is False so `craft()` is not
  called.

Bumping an indestructible/inert barrier (border / reinforced / closed gate,
`BARRIER_BUMP[kind] is None` in world.py `_register_bump`) is explicitly OUT OF
SCOPE (Daniel, 2026-07-12): it counts as normal navigation, not a deliberate
disallowed action, and gets no denial sound.

**Fix hint:** introduce a single new world event (e.g. `'action_denied'`) emitted
via `self._emit('action_denied')` at each refusal site listed above, immediately
before the early `return` / `return False`. Map it to one new SFX in game.py's
`_EVENT_SOUNDS` table (a short buzzer/thunk `sfx_denied` added to `_build_sfx` in
sounds.py and its return dict). Guard against spamming the sound when a bump key
is held (reuse the `_bump_consumed` / key-release gate that walls already use, so
a held key doesn't retrigger). Needs its own spec: enumerate the exact set of
denial sites, the event name, and the SFX character.

**Chosen SFX (Daniel, 2026-07-14):** "wrongbeep" — a flat low square-wave beep
with a fast rasp tremolo. Auditioned against `low_buzz`, `double_buzz`,
`descend`, `downchirp`, and `thud`; "wrongbeep" won. Reproducible recipe (same
chiptune synth style as sounds.py, to become `sfx_denied` in `_build_sfx`) —
approximately:
- square wave at 147 Hz, ~180 ms
- multiplied by a 32 Hz half-amplitude square-wave tremolo:
  `trem = 1.0 + 0.5*sign(sin(2*pi*32*t))` (the "rasp")
- ADSR envelope `env(atk=0.003, dec=0.02, sus=0.85, rel=0.06)`
- soft-saturate with drive ~2.5

---

## BL-53 · OBSOLETE · Draw movable box on top of door/gate/bridge fixtures so it stays visible when overlapping

Closed as obsolete (2026-07-12): the premise no longer holds. Push-blocks are
now confined to their own room floor (`World._room_floor`) — a block can never be
pushed through a passage and out of its room, and a wall opening / gate / door is
never a valid push-stand tile (spec 0068 / BL-37; safe set is player-reachability
-bound over the room's own walkable floor). A movable box therefore can no longer
come to occupy the same cell as a door/gate/bridge fixture, so the draw-order
overlap this item set out to fix cannot occur. See
`spec/0068-exploding-wedged-blocks.md` and the "Doomed push-blocks & the safe
set" section of `kb/findings.md`.

Movable blocks can be pushed through a passage and out of their room, so a
movable box can end up occupying the same cell as a door/gate/bridge fixture.
Currently the draw order can cause the box to be hidden behind (or visually
conflict with) the door/gate/bridge sprite. The movable box sprite must be drawn
LATER (on top of / after) the door/gate/bridge sprite so it remains visible when
it overlaps one of those fixtures.

**Fix hint:** in the rendering path (game.py presentation layer), order the
sprite draw so terrain/fixture sprites (door, gate, bridge) are painted first and
the movable box sprite is painted afterward, on the same cell. Check the per-cell
draw loop that renders cells.py fixtures vs. block/box sprites and ensure boxes
come after fixtures.

---

## BL-54 · P3 · Metal-reinforced blocks the forge enemy cannot destroy

Collected metal scrap can reinforce a user-built BLOCK so the forge enemy cannot
destroy it. Reinforcing is done right after placing the block, while the player
is still standing on the block's tile, by pressing spacebar a second time (the
first press places the block; the immediate second press, from the same tile,
spends the metal to reinforce it). A reinforced block is immune to the forge
enemy's wall-break behaviour.

This feature — and metal being sprinkled into levels at all — is only available
again once the inventory and metal are re-enabled later. It DEPENDS on BL-26's
metal gating being lifted and on the BLOCK rename (BL-26), and it interacts with
the forge enemy.

**Fix hint:** the placement lives on the quick-place-block path in `world.py`
(the same path that consumes the block credit and stands the player on the new
tile); add a "reinforce the block I'm standing on" branch to the spacebar/bump
handling that fires on a second press from the block's own tile and spends
`MAT_METAL`. The immunity is enforced in the forge-enemy wall-break logic — skip
destroying a block flagged as reinforced.

---

## BL-55 · FIXED · Exploded block respawns onto an unsafe tile

Fixed by spec 0076 (`spec/0076-block-respawn-into-safe-area.md`, all deliverables
ticked), user-accepted in-game 2026-07-14. `_block_respawn_tile` (world.py) now
picks a random free **non-plate** tile inside the safe area of the block's **own
room** (`safe_tile_set & _room_floor(b)`, sorted candidates → `random.choice`),
never preferring home; a plate tile is used only as a last resort (a very small
room) and the block stays put if its room's safe area is fully occupied. Two
defects were fixed: (1) the old nearest-open BFS could flood past the safe area
onto an unsafe tile — commit a37fe3a; (2) drawing from the grid-wide
`Room.safe_tile_set` union could teleport the block into a different,
disconnected room and strand its puzzle (found during acceptance) — commit
5c0fb09, confined to the block's own `tile_owner` room floor. Tests in
`tests/test_exploding_blocks.py` (home-free, home-blocked, plate-last-resort,
cross-room), full suite 887 passed.

When a moveable block explodes and would respawn at the player's location, the
fallback picks an adjacent alternative tile, but the fallback algorithm does not
check whether that alternative tile is inside the safe area. (Reported by a
tester.)

**Fix hint:** change the respawn algorithm so that whenever a block explodes it
respawns to a *completely random free tile within the safe area* — it should no
longer prefer/return to its original home tile at all. Ensure the chosen tile is
free and inside the safe area. Look in `world.py` for the block-respawn logic
(the explode/respawn path from spec 0068 / BL-37, which currently respawns at the
start tile or nearest open tile).

---

## BL-56 · FIXED · Sweep: are there levels with duplicate-colour keys and/or doors?

Fixed by spec 0075 (`spec/0075-duplicate-colour-keys.md`, all four deliverables
D1–D4 ticked), user-accepted in-game 2026-07-14. Sweep
(`scratchpad/sweep_dup_colour.py`, 300 levels): **46 % of levels have
duplicate-colour keys**, and doors duplicate in lockstep (R-K1: `#keys ==
#doors` per colour). Per-colour counts: 62 % ×1, 31 % ×2, 6.7 % ×3, 0.2 % ×4;
**max 4** — because the colour pool cycles all 7 before refilling, so counts are
`ceil(T/7)` and `T` never exceeded 24. Decision (Daniel): live with it, but
(D1, 8c5aec6) cap each colour at `MAX_KEYS_PER_COLOUR = 4` in `_next_color`
(overflow → open passage, hard limit 28 doors/level — see R-K2), and (D2,
ab8bd52/2251efa/a688deb) make it legible in the HUD via a stack of overlaid key
icons per colour (opaque 15 % ghosts, 1 px rim, held-in-front, centred, 1px up).
Docs (D3, 2d6176b): R-K2, `kb/findings.md`, display KB, spec 0071 errata. Tests:
`tests/test_dup_colour.py` (detector-validated on a forced >28-door grid) +
`tests/test_render.py`; full suite 883 pass.

**Follow-ups still open:** BL-57 (build block on door/gate tile) and BL-58
(build block on border passage) were reported alongside this but are separate
topics, untouched here.

---

## BL-57 · FIXED · Allow blocks to be built on top of a door or gate tile (block becomes invisible)

Fixed by spec 0077 (`spec/0077-no-block-on-door-or-gate.md`), implementation
commit `dd250d7`, user-confirmed in-game 2026-07-14. A door is now a
channel-latched barrier (opened doors stay in the cell model, `_opened_doors`
deleted), so `_place_block` (world.py) refuses on any tile whose
`barrier.kind in ('door', 'gate')` — a block can no longer be built hidden under
a door/gate fixture or on top of an open gate. The shared 'action denied' SFX
(spec 0074 / BL-52) plays on the refusal.

It was possible to build a moveable block on a tile that already holds a gate or
door. The door/gate is drawn later, so the block is hidden underneath it.
(Reported by a tester.)

**Fix hint:** disallow building a block on any door or gate tile; play the shared
'action denied' SFX (see spec 0074 / BL-52) when the build is rejected. Look at
the build/crafting-place logic in `game.py` and the passability/fixture queries
in `world.py` / `cells.py`.

---

## BL-58 · FIXED · Building a block on a border passage tile draws it with the border-wall sprite

Fixed by spec 0078 (`spec/0078-no-block-on-border-passage.md`) via approach (a),
disallow placement — implementation commit `0211448`, user-accepted in-game
2026-07-15 (spec 0078 B5). A new `_is_border_passage_tile` predicate (a bare
positional `is_border` test) was added to `_place_block`'s (world.py) refusal
chain, so a block can no longer be placed on a punched border passage tile; the
refusal reuses the spec-0074 'action_denied' feedback and spends no credit. No
rendering change was needed — the border-wall sprite symptom is now unreachable
for placed blocks. Full test suite green (893 passed).

When the tester built a moveable block on the passage tile of the border, the
border wall sprite was used to draw the block. Unclear how to handle this because
that tile is mirrored to the opposite side of the grid.

**Fix hint:** open design question — the handling approach is UNDECIDED. Decide
whether to (a) disallow building on border passage tiles, or (b) handle the
mirroring so the block draws correctly on both sides. Border/passage mirroring and
the border-wall sprite selection are the relevant areas (`levellayout.py` wall
derivation, `sprites.py`, `game.py` rendering).

---

## BL-59 · P3 · Generation-bound Hypothesis property tests flake with `DeadlineExceeded` under parallel `poe test` load

Generation-bound Hypothesis property tests flake with `DeadlineExceeded` under
parallel `poe test` (`-n auto`) load. Observed this session across two full-suite
runs: the failing set VARIED run-to-run (run 1:
`test_layout.py::test_invariant_l_all_edges_realised[vertical]`, `[double_t]`;
run 2: `test_invariant_l_all_edges_realised[z]`, `[l]`,
`test_invariant_l_all_feature_sets[fs2]`, `[fs4]`,
`test_placement_rules.py::test_flame_room_never_has_water_edge`,
`test_flames_always_placed_when_requested`) — all `DeadlineExceeded` (211–621ms
vs the default 200ms Hypothesis deadline), never assertion failures, and every one
passes green when run serially in isolation. Root cause: these tests generate
levels (CPU-bound) inside a 200ms per-example deadline while competing for cores
under xdist, so the deadline breaches non-deterministically; the suite wall time
swings with load (7:14 → 10:56 observed). Not a correctness issue.

**Fix hint:** set `@settings(deadline=None)` (or a generous fixed deadline, e.g.
2000ms) on the generation-bound property tests in `tests/test_layout.py` and
`tests/test_placement_rules.py`, mirroring
`tests/test_border_continuity.py::test_border_barrier_records_on_both_sides`,
which already uses `deadline=None` for exactly this reason. Grep the two files for
`@settings(` and audit which property tests build levels/graphs.

---

## BL-60 · DONE · Push block must not be pushed onto (or respawn onto) a collectable-item tile

A push block must not be pushable onto a tile that holds a collectable item
(rubble, metal, keys, award/treasure items, materials/planks — anything in the
cell item layer). Likewise, after a wedged block explodes it must not respawn
onto such a tile. Rationale: it removes an unintuitive interaction and a weird
overlapping-sprite display situation (block drawn on top of a pickup). It does
NOT affect the safe-area mechanic or push-puzzle solvability in any way, because
the player can simply collect the item first, after which the block can be pushed
there — so no puzzle re-validation is needed.

**Fix hint:**
- Runtime, `world.py`. In `_try_push_block(bc, br, dcol, drow)` the target tile
  is `(nc, nr) = (bc+dcol, br+drow)`; today it is accepted when
  `not self.blocked(nc, nr) and (nc, nr) in self._room_floor(bc, br)`. Add a
  guard that refuses the push when the target tile carries a collectable, i.e.
  when `self.cells.items(nc, nr)` is non-empty (the item layer holds
  `Item(kind, payload)` for kind in treasure/material/key — see `cells.py`
  `RoomCells.items` / `items_of_kind`). A refused push should behave like the
  existing failed-push path (no move; it currently falls through to
  `_register_bump`), matching how a block push into a wall already fails.
- Explosion respawn: `_detonate_block` calls `_block_respawn_tile(b)` (spec 0076,
  respawn into the safe area). Exclude item-bearing tiles from that respawn
  candidate pool the same way — filter out any tile with `self.cells.items(tile)`
  non-empty when choosing the respawn position.
- No generator/levellayout change and no push-puzzle re-validation are required
  (the constraint is strictly permissive of existing solutions — collect-then-push
  always remains available).
- Verification: add pygame-free `tests/test_world.py` cases — a block cannot be
  pushed onto an item tile (push refused, block stays), and a detonated block
  never respawns onto an item tile.

**Resolution:** Done by spec 0079 (commit a481076), user-accepted 2026-07-15.
A single extra `not self.cells.items(...)` term now gates both runtime paths:
`World._try_push_block` (a push onto an item tile returns False → the caller's
inert `_register_bump` runs, no move) and the `free` comprehension in
`World._block_respawn_tile` (item tiles never enter the explosion-respawn pool).
Strictly permissive — collect-then-push reaches the same tile — so no
generator/levellayout/puzzle-validation change and goldens byte-identical;
full suite 893 passed. Tests: tests/test_exploding_blocks.py (push-refused +
collect-then-push; respawn never on an item tile). → spec/0079-no-block-push-or-respawn-onto-item.md

---

## BL-61 · FIXED · uglycraft package installs only 8 of 16 Python modules (game crashes on launch)

Fixed in 8c70f7b (spec/0080-uglycraft-source-package.md), confirmed by Daniel
2026-07-18 (spec 0080 D7, AUR package test). package_uglycraft() no longer
installs an explicit module list at all — it now installs the whole
`src/uglycraft` package into site-packages as one unit (PKGBUILD:46 comment:
"Install the whole package into site-packages as one unit ... so the install
list can never go stale again (BL-61)"), so the stale-list bug is structurally
impossible. Original bug description follows for history.

`packaging/PKGBUILD:47-48` and `packaging/PKGBUILD-git:51-52` install a hardcoded
list of 8 modules (main, game, constants, sprites, levels, entities, hiscore,
sounds). The game is now 16 modules; the wrapper runs
`python /usr/share/uglycraft/main.py`, which crashes at `game.py:12`
(`from hud import …`) before the window opens. Missing runtime modules: hud,
world, crafting, cells, rooms, levelgraph, levellayout (plus leveldump, lazily
imported at main.py:71 for --dump-level). The list went stale after the
world/hud/crafting split (specs 0045–0047, 0072). The `ugli` (Pascal) half is
unaffected. This is a release blocker — the published uglycraft is unrunnable.
→ kb/arch-packaging.md

**Fix hint:** replace the explicit list in both PKGBUILDs with a glob.
`git ls-files '*.py' | grep -v /` is exactly the 16 game files (repo root has no
other .py; tests/ is a subdir), so from inside the source dir:
`install -m644 *.py "$pkgdir/usr/share/uglycraft/"`. Future-proof and picks up
leveldump too.

---

## BL-62 · FIXED · Redundant `provides=($pkgname)` in package_uglycraft and package_ugli

Fixed by spec 0085 (commit 96a60f2), confirmed 2026-07-18. Both redundant
`provides` lines were removed from `packaging/PKGBUILD` (`package_uglycraft`,
`package_ugli`); `.SRCINFO` regenerated in the same commit (spec 0084
mechanism) shows exactly those two lines gone, nothing else. `-git`/`-dev`
PKGBUILDs left untouched, as intended (their provided names differ from
`$pkgname` and are load-bearing). namcap (system-installed) raises no
provides-related warning.

Arch guideline: "Do not add $pkgname to provides, as it is always implicitly
provided." Violated in package_uglycraft (`provides=('uglycraft')`, PKGBUILD:41)
and package_ugli (`provides=('ugli')`, :77). Note: the `provides` in the -git
packages (PKGBUILD-git:45,81) are CORRECT and must stay — there $pkgname is
uglycraft-git/ugli-git, so providing the non-git name satisfies deps and pairs
with conflicts. → kb/arch-packaging.md

**Fix hint:** delete the two redundant `provides` lines from the release
PKGBUILD only; leave the -git PKGBUILD untouched. Regenerate .SRCINFO afterwards
(see BL-66).

---

## BL-63 · FIXED · Release tarball uses SKIP instead of a real checksum

Fixed by spec 0090 (commit 3712eee), confirmed 2026-07-18. `updpkgsums
packaging/PKGBUILD` was run; source index 0 (the `v$pkgver.tar.gz` tarball)
now carries a real sha256
(`6fd94d423b5daed0966c63baaab297b103cb326c657712d883d140f8d27bd200`).
Sequenced after spec 0089/BL-65 pinned the four external sources, so those
four sums were only re-verified, not rewritten. `makepkg --verifysource
-p PKGBUILD` passes against the live v1.5 GitHub tag. `PKGBUILD-git`/
`PKGBUILD-dev` correctly keep SKIP for their VCS-clone source only.

Arch guideline requires integrity variables to hold correct values (updpkgsums);
CLAUDE.md § Arch packaging also says to run updpkgsums at release time, but
PKGBUILD:15-19 is still all-SKIP. At minimum the versioned `v$pkgver.tar.gz`
(source index 0) must carry a real sha256. The git PKGBUILD legitimately keeps
SKIP (VCS clone). The other four SKIPs are forced by the moving-branch sources —
see BL-65. → kb/arch-packaging.md

**Fix hint:** `updpkgsums packaging/PKGBUILD` after BL-65 pins the external
sources; if BL-65 is deferred, at least set a real sha256 for the release
tarball (index 0) and keep SKIP only for the branch-tip sources.

---

## BL-64 · FIXED · uglycraft ships the OFL-1.1 font but declares only GPL-3.0-only

Fixed by spec 0086 (commit eaf3976), confirmed 2026-07-18.
`license=('GPL-3.0-only' 'OFL-1.1')` added inside `package_uglycraft()` (and
the `-git`/`-dev` equivalents); `ugli*` stays GPL-only (ships no font).
`.SRCINFO`/`.SRCINFO-git` regenerated in the same commit. The built
`uglycraft-dev` package's `.PKGINFO` carries both `license =` lines, and
namcap (system-installed) raises no license warning — both SPDX ids resolve,
license files present under `/usr/share/licenses/`.

`license` is set once at pkgbase level (GPL-3.0-only) and never overridden, but
package_uglycraft installs fonts/ShareTechMono-Regular.ttf and
OFL-1.1-ShareTechMono.txt (PKGBUILD:50,68). The license field must list all
licenses of distributed content. `ugli` ships no font (GPL-only correct there).
pygame/numpy are runtime deps, not bundled, so their licenses do not belong here.
→ kb/arch-packaging.md

**Fix hint:** override per split package —
`license=('GPL-3.0-only' 'OFL-1.1')` inside package_uglycraft (and
package_uglycraft-git). Regenerate .SRCINFO (BL-66).

---

## BL-65 · FIXED · Non-reproducible moving-branch external sources

Fixed by spec 0089 (commit a9f6282), confirmed 2026-07-18. All four external
files pinned to fixed commit hashes —
`_uos_commit=ffd165382aeae1cc1bf80673d5c02497c06f4efa`,
`_themes_commit=e144651f75891cf4795ef1e7c24bb3e27c47aa06` (looked up via
`git ls-remote` at implementation time; these were the branch heads the
builds already used, so built content is unchanged) — in all three
PKGBUILDs *and* in `poe build-original`, with real sha256 sums for all four.
Unblocked spec 0090/BL-63 (the moving tips were the reason the release
tarball's SKIP couldn't be cleanly `updpkgsums`-filled before). `.SRCINFO`
regenerated in the same commit.

uos.pas/uos_flat.pas/uos_portaudio.pas are pulled from `…/uos/main/…` and
ANSI-87.conf from `…/kitty-themes/master/…` (PKGBUILD:11-14, PKGBUILD-git:10-13).
Unversioned branch tips make the build non-reproducible and are the reason four
sha256sums are pinned to SKIP. Reproducibility is an explicit Arch goal.
→ kb/arch-packaging.md

**Fix hint:** pin each URL to a specific commit hash / tag and give it a real
sha256 (updpkgsums). Apply to both PKGBUILD and PKGBUILD-git.

---

## BL-66 · FIXED · .SRCINFO is hand-copied, never regenerated (drift risk)

Fixed by spec 0084 (commit c31b855), confirmed 2026-07-18. `poe deploy-aur`/
`deploy-aur-git` now **regenerate** `.SRCINFO`/`.SRCINFO-git` via
`makepkg --printsrcinfo` immediately before the `cp` step, instead of copying
a hand-maintained static file. Both tasks also gained `executor = "simple"`
(applying BL-71 Part A's rule to these two makepkg-invoking tasks). The
already-stale `.SRCINFO-git` was regenerated once in the same commit. This is
the infrastructure spec every other spec in this pass (0085–0090) rides on —
from here on, any PKGBUILD metadata edit re-flows into `.SRCINFO`
automatically at deploy time.

deploy-aur/deploy-aur-git (pyproject.toml:187-) `cp` a static
.SRCINFO/.SRCINFO-git. It matches now for the release (makepkg --printsrcinfo
diff = MATCH) but any PKGBUILD edit silently drifts it — .SRCINFO-git already
shows a stale pkgver (1.4.r0.gf95b776 vs the PKGBUILD's 1.4.r20.g21ad119). Every
provides/license fix above must be re-flowed into .SRCINFO. → kb/arch-packaging.md

**Fix hint:** in the deploy tasks, regenerate rather than copy:
`cd packaging && makepkg --printsrcinfo > .SRCINFO` (and `> .SRCINFO-git` from
PKGBUILD-git). Keep the committed .SRCINFO files in sync in the same commit as
any PKGBUILD change.

---

## BL-67 · FIXED · arch=('x86_64') on the pure-Python uglycraft split package

Fixed by spec 0087 (commit c7b4e7a), confirmed 2026-07-18. `arch=('any')`
added inside `package_uglycraft()` (and the `-git`/`-dev` equivalents); the
pkgbase-level array and `package_ugli*()` stay `x86_64` unchanged. One
`poe package-dev` run produces an `…-any.pkg.tar.zst` alongside the x86_64
`ugli-dev` package; the extracted `any` package's headless `--dump-level` run
passed, and namcap's `anyelf` rule (which flags ELF files inside an
`arch=any` package) found none.

`arch` is overridable per split package. `uglycraft` is architecture-independent
(pure Python) and could set `arch=('any')` so it installs on aarch64 etc.;
`ugli` (compiled FPC binary) correctly stays x86_64. The pkgbase-level array must
still include every arch the split members need. → kb/arch-packaging.md

**Fix hint:** add `arch=('any')` inside package_uglycraft (and
package_uglycraft-git); leave pkgbase arch and package_ugli as x86_64. Confirm
the resulting `uglycraft-…-any.pkg.tar.zst` still installs alongside the x86_64
`ugli`.

---

## BL-68 · FIXED · Compiled UGLI_2 binary installed under /usr/share

Fixed by spec 0088 (commit b49b587), confirmed 2026-07-18 — including D4's
real-terminal-launch leg, accepted by the user 2026-07-18 (commit b598874)
after installing and testing freshly built uglycraft-dev/ugli-dev packages.
`UGLI_2` moved
to `/usr/lib/ugli/UGLI_2` in all three PKGBUILDs; `packaging/ugli.sh`'s
`UGLI=` path updated to match. **Discovered mechanism:** `UGLI_2` resolves
`translations/*.mo` and `history_*.txt` relative to its own executable path
(`ParamStr(0)`/`ExeDir`), not a compiled-in `/usr/share` constant — confirmed
by reading `original/UGLI_2_Core.inc`'s `LoadTranslation` (lines 1978–2007)
and `LoadHistoryText` (lines 1524–1568). So `translations/` moved with the
binary to `/usr/lib/ugli/translations/`, while `ANSI-87.conf` — read only by
the wrapper script via a `-c` kitty flag, never by the Pascal binary — stays
under `/usr/share/ugli/` as wrapper-only data. Positively verified by running
the extracted binary from an unrelated CWD with a forced German locale and
observing translated `--help` output. namcap (system-installed): the
`elfpaths` rule (allows `usr/lib/`, not `usr/share/`) no longer fires; only
the unrelated RELRO/PIE hardening warning remains (filed as BL-74 below). The
real-terminal-launch check (opening the game in an actual terminal) is now
accepted by the user. → spec/0088, kb/arch-packaging.md

UGLI_2 (an ELF executable) is installed to /usr/share/ugli/UGLI_2 (PKGBUILD:82,
PKGBUILD-git:86). /usr/share is for architecture-independent data; a private,
wrapper-invoked binary is more idiomatic in /usr/lib/ugli/. namcap warns ("ELF
file in /usr/share"). Harmless but non-canonical. → kb/arch-packaging.md

**Fix hint:** install the binary to /usr/lib/ugli/UGLI_2 and update the `UGLI=`
path at the top of packaging/ugli.sh to match; update both PKGBUILDs. Data files
(ANSI-87.conf, translations) can stay in /usr/share/ugli.

---

## BL-69 · FIXED · Installed Python modules are not byte-compiled

Fixed as part of spec 0080 (DEC-2, spec/0080-uglycraft-source-package.md:79:
"byte-compiles, folding in BL-69"): package_uglycraft() now runs
`python -m compileall -q -d "$_site/uglycraft" "$pkgdir$_site/uglycraft"`
(packaging/PKGBUILD:52, packaging/PKGBUILD-git:56). The `-d` flag (reproducible
embedded paths) was a later refinement from BL-71 Part B. Original bug
description follows for history.

The loose .py files land in root-owned /usr/share/uglycraft; at first run Python
tries to write __pycache__ there, fails silently, and recompiles every launch.
Proper Python packaging precompiles bytecode. Minor; commonly skipped for
loose-script games. → kb/arch-packaging.md

**Fix hint:** after installing the modules, run
`python -m compileall "$pkgdir/usr/share/uglycraft"` in package_uglycraft (and
the -git variant); consider `--invalidation-mode=unchecked-hash` for
reproducibility.

---

## BL-70 · FIXED · Stale pyproject.toml [project] metadata

Fixed as part of spec 0080 (DEC-3, spec/0080-uglycraft-source-package.md:84-85:
"also fix BL-70?"). `pyproject.toml [project]` now reads `version = "1.5"` and
`description = "A remake of UGLI (1996), a DOS maze-chase game"` — both the
version and the year (1993 → 1996) corrected. Original bug description follows
for history.

Not an AUR file but packaging metadata — `[project]` says `version = "1.0"` and
`description = "…UGLI (1993)…"` (pyproject.toml:1-4), vs the real v1.5 / 1996.
Independent of the AUR fixes. → kb/arch-packaging.md

**Fix hint:** bump version to the current release and fix the year in the
description (1993 → 1996) to match README/CLAUDE.md. Low priority; verify nothing
reads [project].version at runtime first.

---

## BL-71 · P3 · PKGBUILD `_site` detection is poe-executor-fragile, plus cosmetic `$pkgdir`-embedded .pyc paths

Found while implementing spec 0083 (`packaging/PKGBUILD-dev`, a local-only AUR
packaging variant with a new `poe package-dev` task).

**Part A — poe's "auto" executor can redirect `_site` into the project's own
venv.** All three PKGBUILDs' `package_uglycraft*()` functions share:
`_site=$(python -c "import site; print(site.getsitepackages()[0])")`. When
`makepkg` is invoked through a `poe` task, poethepoet's default `"auto"`
executor detects the project's `.venv/` and prepends `.venv/bin` to `PATH` for
the task's subprocess (poethepoet's `executor/virtualenv.py` +
`executor/base.py` `resolve_implementation`, which tries poetry/uv/virtualenv
executors before falling back to `"simple"`). That makes `_site` resolve to
`/path/to/uglycraft/.venv/lib/python3.14/site-packages` instead of the
system Python's site-packages, so a package built under such a task would
silently try to install into the venv path rather than the real system
location. spec 0083's `poe package-dev` task was fixed by adding
`executor = "simple"` to its `pyproject.toml` definition (pins it to poe's
no-op executor, no venv injection). `PKGBUILD` and `PKGBUILD-git` are NOT
affected today — poe only copies `PKGBUILD`+`.SRCINFO` to the AUR sibling repos
and pushes; the actual `makepkg` build always runs on an AUR builder's or
user's own machine, outside this project's poe environment — but the same
`_site` detection logic is present verbatim in all three PKGBUILDs, so any
future `poe`-based makepkg task for the release/git variants would hit the
identical bug unless it also sets `executor = "simple"`.

**Partial progress (spec 0084, commit c31b855, 2026-07-18):** `deploy-aur`
and `deploy-aur-git` themselves started shelling out to `makepkg
--printsrcinfo` (to regenerate `.SRCINFO`, BL-66) — the first real case of a
`poe` task in this project invoking `makepkg`. Both were given
`executor = "simple"` in the same commit, applying Part A's rule exactly as
prescribed. This does **not** close Part A: `--printsrcinfo` only sources the
PKGBUILD statically and never runs `package_uglycraft*()`'s `_site`
detection, so the two deploy tasks were never actually at risk of the venv-
leak bug Part A describes — the fix was precautionary, matching the rule
rather than curing an observed instance of it. Part A remains open as a
standing rule for any *future* `poe` task that runs a real `makepkg build`
(as opposed to `--printsrcinfo`) against these PKGBUILDs.

**Part B — compileall bakes the fakeroot staging path into .pyc metadata
(cosmetic, pre-existing, not introduced by spec 0083).** makepkg's own
"packaging issues" checker prints `WARNING: Package contains reference to
$pkgdir` for every compiled `.pyc` under
`usr/lib/python3.14/site-packages/uglycraft/__pycache__/` in all three
PKGBUILDs' `package_uglycraft*()` functions, because
`python -m compileall -q "$pkgdir$_site/uglycraft"` embeds the fakeroot staging
path (which contains the literal `$pkgdir` prefix) as each .pyc's source-file
metadata, instead of the final runtime path. Only affects traceback
source-path display, not functionality.

> **RESOLVED — Part B, confirmed 2026-07-18.** Changed
> `python -m compileall -q "$pkgdir$_site/uglycraft"` to
> `python -m compileall -q -d "$_site/uglycraft" "$pkgdir$_site/uglycraft"` in
> all three PKGBUILDs (`packaging/PKGBUILD`, `packaging/PKGBUILD-git`,
> `packaging/PKGBUILD-dev`). `compileall`'s `-d DESTDIR` flag (verified against
> CPython 3.14's `compileall.py`) strips the compiled directory's own prefix
> and substitutes `DESTDIR` in each .pyc's embedded `co_filename`/traceback
> path, rather than the literal fakeroot path. `.SRCINFO`/`.SRCINFO-git` needed
> no changes — the fix is inside a function body, not build metadata. Verified
> empirically: before the fix, `strings` on the installed .pyc showed the full
> fakeroot build path; after, only the correct runtime path (e.g.
> `/usr/lib/python3.14/site-packages/uglycraft/main.py`) is embedded, and a
> `poe package-dev` rebuild produced zero makepkg packaging-issue warnings,
> with the package still installing and running correctly (font + history
> load fine from the installed tree). **BL-71 Part B closed.** Part A remains
> open (see fix hint above) for any future `poe`-based makepkg task on the
> release/git PKGBUILDs.

**Fix hint (Part A):** always pair any future `poe` task that shells out to
`makepkg` with `executor = "simple"` in its `pyproject.toml` definition.

> **RESOLVED — Part A, 2026-07-18 (spec 0094). BL-71 fully closed.** The
> `_site` detection was removed from all three PKGBUILDs at the root by
> switching `package_uglycraft*()` to the Arch-idiomatic PEP 517 flow:
> `python -m build --wheel --no-isolation` in `build()`, `python -m installer
> --destdir="$pkgdir" dist/*.whl` in `package()`. There is no site-packages
> computation left to mis-resolve; `installer` also byte-compiles with
> correct runtime paths, superseding Part B's `compileall -d` workaround, and
> generates `/usr/bin/uglycraft` from `[project.scripts]`, replacing the bash
> wrapper. The `executor = "simple"` rule for makepkg-running poe tasks
> **remains in force** as defence-in-depth (the PKGBUILDs still invoke
> whatever `python` PATH resolves to). Verified via `poe package-dev`: clean
> makepkg run, file list identical to the old flow plus `.dist-info` +
> `.opt-1.pyc`, namcap clean, `.pyc`s embed only runtime paths.
> → see spec/0094-pkgbuild-wheel-flow.md, kb/arch-packaging.md

---

## BL-72 · FIXED · uglycraft-git split package missing makedepends for python/pygame/numpy (namcap)

Fixed by spec 0092 (commit ed3539f), confirmed 2026-07-18. Pkgbase-level
`makedepends` in all three PKGBUILDs (release, `-git`, `-dev`) now includes
`python`, `python-numpy`, `python-pygame` alongside the existing entries;
`.SRCINFO`/`.SRCINFO-git` regenerated in the same commit. **Key insight from
the spec 0092 investigation:** namcap's split-makedeps rule
(`SplitPkgMakedepsRule`) resolves each subpackage's dependency coverage
against the **local pacman database**, not the PKGBUILD in isolation — the
release PKGBUILD's clean namcap run at audit time was an accident of the
machine having `uglycraft-dev` installed (which `provides=('uglycraft')`, so
`load_from_db('uglycraft')` resolved through it and pulled its real `depends`
into coverage, silencing the check by chance). No installed package
`provides` `uglycraft-git`, so the same accidental coverage never happened
there, and the rule fired only on `-git` — a clean-DB/CI run would have
flagged the release PKGBUILD identically. Also confirmed empirically that
`makedepends=('python')` alone is **insufficient**: namcap still flagged the
remaining `['python-numpy', 'python-pygame']`, since the rule does a literal
subset check of subpackage `depends` against pkgbase `makedepends`/its
transitive closure — the full triple was required. Final state (after spec
0093's D6 addition, commit 8f3c117) is clean of every split-makedeps finding
on both PKGBUILDs. → spec/0092-split-package-makedepends.md

namcap flagged `PKGBUILD-git`: "Split PKGBUILD needs additional makedepends
[python, python-numpy, python-pygame] to work properly" for the
`uglycraft-git` split package. `package_uglycraft-git()` declares only
`depends=('python' 'python-pygame' 'python-numpy')` (runtime) — namcap's
split-package heuristic wants build-time-needed packages (here, `python`
itself, needed to run `compileall` during `package()`) declared in
`makedepends` too. Structurally the release `PKGBUILD` has the identical
shape — pkgbase-level `makedepends=('fpc')` (`+git` only in `-git`),
`package_uglycraft()`/`package_uglycraft-git()` both declare only the
runtime `depends`, no python-related `makedepends` at all — so the same
finding plausibly applies to the release PKGBUILD too; this namcap pass only
observed the warning on `-git`, it was not confirmed absent on the release
one.

**Fix hint:** add `makedepends=('python')` (or namcap's full suggested
triple) to `package_uglycraft-git()`, and run namcap against the release
`packaging/PKGBUILD` under the same rule — if it also flags, fix both
PKGBUILDs together (and `PKGBUILD-dev` for consistency, though it is never
deployed). `python-pygame`/`python-numpy` are only import-time deps of the
shipped `.py` source, not needed merely to `compileall`, so `makedepends=
('python')` alone may already satisfy namcap — verify against its rationale
before adding the full triple. Regenerate `.SRCINFO`/`.SRCINFO-git`
afterwards (spec 0084 mechanism).

---

## BL-73 · FIXED · Missing hicolor-icon-theme dependency for the split packages installing icons (namcap)

Fixed by spec 0093 (commits c0d7973 + 8f3c117), confirmed 2026-07-18. All
eight `package_*()` functions across the three PKGBUILDs (release, `-git`,
`-dev`) now declare `depends=(... 'hicolor-icon-theme')` (a new `depends`
array for `ugli*`, which previously had none at all); `.SRCINFO`/
`.SRCINFO-git` regenerated. **D6 interaction discovered during
implementation:** adding `hicolor-icon-theme` to each subpackage's `depends`
re-triggered the same `SplitPkgMakedepsRule` spec 0092 had just fixed for the
Python triple — a subpackage's `depends` entry must also be covered by
pkgbase-level `makedepends` for namcap's split-makedeps rule to pass, so
`hicolor-icon-theme` was additionally added to pkgbase-level `makedepends` in
all three PKGBUILDs (spec amendment commit ad56f62, fix commit 8f3c117).
Verified against built `uglycraft-dev`/`ugli-dev` packages: `.PKGINFO` lists
`depend = hicolor-icon-theme`; namcap on both built packages and both source
PKGBUILDs is clean of the finding (only benign `Missing Maintainer tag` /
implicitly-satisfied notes remain). → spec/0093-hicolor-icon-theme-dependency.md

namcap flagged: "Dependency hicolor-icon-theme detected and not included
(needed for hicolor theme hierarchy)" on the `uglycraft` package. Both
`uglycraft`/`uglycraft-git` and `ugli`/`ugli-git` install a `.svg` under
`/usr/share/icons/hicolor/scalable/apps/` (`packaging/PKGBUILD:64-65,94-95`
and the `-git`/`-dev` equivalents) but none of the four split packages
depend on `hicolor-icon-theme`, which owns the hicolor directory hierarchy
and the `gtk-update-icon-cache` trigger.

**Fix hint:** add `hicolor-icon-theme` to `depends` of `package_uglycraft*()`
and `package_ugli*()` in all three PKGBUILDs (release, `-git`, `-dev`).
Regenerate `.SRCINFO`/`.SRCINFO-git` afterwards (spec 0084 mechanism).

---

## BL-74 · P3 · UGLI_2 binary lacks FULL RELRO and PIE hardening (namcap)

namcap warns on the built `ugli`/`ugli-git`/`ugli-dev` packages' `UGLI_2`
ELF binary: it lacks FULL RELRO and lacks PIE. This is a compiler/linker
hardening gap in the FPC build (`build()` in all three PKGBUILDs runs plain
`fpc -Fuuos UGLI_2.pp`), not a packaging-metadata issue — unlike every other
namcap finding from this pass (BL-62/64/66/67/68, all fixed at the PKGBUILD
level), this one needs FPC compiler/linker flags instead. Low priority
polish; the binary already worked and shipped without hardening for the
v1.5 release.

**Fix hint:** research FPC linker/hardening flags before implementing —
candidates are passing `-z,relro,-z,now` to the linker via FPC's `-k` option
for RELRO/BIND_NOW, and enabling PIE codegen (FPC's PIE support varies by
target/FPC version and may need `-Cg`-style options, or may not be available
at all for this target — needs a research pass into FPC docs first). Apply
in `build()` in all three PKGBUILDs (release, `-git`, `-dev`) if achievable,
then re-run `poe test-original`/`poe build-original` to confirm `UGLI_2`
still runs correctly with hardening enabled.

---

## BL-75 · FIXED · Unpatched FPC warnings/notes from the fetched UOS sources clutter build output

Fixed by spec 0091 (commit bbcd22e), confirmed 2026-07-18. A sentinel-guarded
FPC directive block (`{$WARN 4105 OFF} {$WARN 5025 OFF} {$WARN 5027 OFF}
{$WARN 5089 OFF} {$WARN 5093 OFF} {$WARN 6058 OFF}` + a
`UGLYCRAFT-WARN-SUPPRESS` comment) is idempotently prepended to each of the
three fetched UOS units (`uos.pas`, `uos_flat.pas`, `uos_portaudio.pas`)
right after fetch/copy, in `pyproject.toml`'s `build-original` task and in
the `prepare()` of all three PKGBUILDs — FPC message directives are scoped
to the compiled unit and do not cross the `uses` boundary, so suppression
had to live inside the third-party sources themselves, not in project code.
`poe build-original` dropped from 5 warnings + 18 notes to 0 UOS-originated
messages; scoping was proven by confirming a deliberately introduced warning
in `UGLI_2.pp` still surfaced. The `UOSSound.pp(57,3)` 6058 note is
deliberately left untouched — it is project-own code (not a fetched UOS
unit), out of this spec's scope; extending the existing `{$WARN 6058 OFF}`
precedent to `UOSSound.pp` is a separate future change. `poe test-original`
surfaced three pre-existing, unrelated `UGLI_2_Core.inc` warnings
(TTYFd/SavedTio/RawTio) not caused by this change — filed separately as
BL-76 (commit 04cde01). → spec/0091-silence-uos-thirdparty-warnings.md

`poe build-original` (and, transitively, the `build()` step of all three
PKGBUILDs) compiles the fetched `uos.pas`/`uos_flat.pas`/`uos_portaudio.pas`
as-is, and FPC emits a batch of warnings and notes against them on every
build. Confirmed by running `fpc -Fuuos uos/uos.pas` directly against the
already-fetched `original/uos/` tree (FPC 3.2.2): 5 warnings, 18 notes,
including —

```
uos.pas(2239,67) Warning: function result variable of a managed type does not seem to be initialized
uos.pas(10640,38) Warning: Local variable "BufferplugFL" of a managed type does not seem to be initialized
uos.pas(11754,20) Warning: Implicit string type conversion with potential data loss from "UnicodeString" to "UTF8String"
uos.pas(12148,43) Warning: Implicit string type conversion with potential data loss from "UnicodeString" to "UTF8String"
uos.pas(12149,44) Warning: Implicit string type conversion with potential data loss from "UnicodeString" to "UTF8String"
uos.pas(4505,3) Note: Local variable "chan" not used
uos.pas(4505,9) Note: Local variable "sr" not used
uos.pas(6174,3) Note: Call to subroutine "...FillLookupTable(...)" marked as inline is not inlined
uos.pas(7811,6) Note: Local variable "x2" not used
uos.pas(7812,3) Note: Local variable "PipeBufferSize" not used
uos.pas(10256,3) Note: Local variable "err" not used
uos.pas(10594,11) Note: Local variable "err" is assigned but never used
```

(full list is longer; the above is representative of each distinct
category). These are all in third-party code, not in `UGLI_2.pp`/
`UOSSound.pp`, and drown out any warning/note FPC might emit for the
project's own Pascal sources in the same build log.

**Fix hint:** the UOS sources are pinned to a fixed commit since spec 0089
(`_uos_commit=ffd165382aeae1cc1bf80673d5c02497c06f4efa`), so a local patch
applied after fetch (in `build()`, right after the `curl`/extract step, in
all three PKGBUILDs) would be stable and reproducible against that exact
source snapshot. Alternatives: per-unit FPC warning suppression — e.g.
`{$WARN ... OFF}`/`{$NOTE ... OFF}` directive blocks wrapped around just the
flagged constructs (would require patching the units anyway to insert the
directives), or scoping a warning-filter flag (FPC has no unit-scoped
`-Sew`/`-vw-` equivalent, so this would likely mean compiling `uos*.pas` in
a separate invocation with relaxed `-v` flags and linking the resulting
`.o`/`.ppu` in). Do **not** blanket-silence warnings/notes for the project's
own Pascal code (`UGLI_2.pp`, `UOSSound.pp`, etc.) — scope any suppression
strictly to the three UOS units.

---

## BL-76 · P3 · `poe test-original` emits 3 FPC warnings not seen in `poe build-original`

`poe test-original` (building `UGLI_2_Test.pp`) emits 3 FPC warnings not
seen when `poe build-original` builds `UGLI_2.pp`:

```
UGLI_2_Core.inc(53,3) Warning: Variable "TTYFd" read but nowhere assigned
UGLI_2_Core.inc(54,3) Warning: Variable "SavedTio" read but nowhere assigned
UGLI_2_Core.inc(54,13) Warning: Variable "RawTio" read but nowhere assigned
```

These three vars are assigned in the raw-terminal-mode init routine in
`original/UGLI_2_Core.inc` (used around line ~1900s, `tcsetattr` calls). The
warnings appear only in the test binary's compile (`UGLI_2_Test.pp`), not
the main binary's (`UGLI_2.pp`) — likely because the test binary's reachable
code never calls whatever procedure performs the assignment
(`fpOpen('/dev/tty')`-based init), so FPC's per-routine analysis in the test
binary sees the vars read (in `tcsetattr`/`fpIoctl`/`fpRead` calls) but
never assigned within reachable code. Confirmed reproducible across two
consecutive `poe test-original` runs on 2026-07-18.

**Fix hint:** either call the init routine (or a stub) reachably in the
test build, or explicitly initialize `TTYFd`/`SavedTio`/`RawTio` in test
setup, or investigate whether this is a false positive from FPC's
whole-program dead-code analysis in test mode. Low priority — cosmetic
warning, not a correctness bug, and does not affect `poe build-original`.

---

## BL-77 · P3 · Two remaining benign namcap warnings on the PKGBUILDs

After specs 0092/0093 resolved BL-72/BL-73 (split makedepends,
hicolor-icon-theme), `namcap` still emits two benign warnings on the
PKGBUILDs, which should be addressed before/at the first AUR push:

1. **`W: Missing Maintainer tag`** on both `packaging/PKGBUILD` and
   `packaging/PKGBUILD-git` (and `packaging/PKGBUILD-dev` for consistency,
   even though it is local-only and never pushed to an AUR sibling repo).
   AUR convention is a `# Maintainer: Name <email>` comment on line 1 of
   the PKGBUILD; namcap checks for it.
2. **`PKGBUILD (ugli) W: Description should not contain the package
   name.`** — the `ugli` split package's `pkgdesc` starts with/contains
   "UGLI". Arch guideline: `pkgdesc` should not include the package name
   redundantly. Reword the `pkgdesc` so it describes the game without
   leading with the package name.

**Fix hint:** one small commit touching the three PKGBUILDs, plus
`.SRCINFO`/`.SRCINFO-git` regeneration via the spec 0084 mechanism since
`pkgdesc` is metadata that's mirrored into `.SRCINFO` — the `# Maintainer:`
comment does **not** appear in `.SRCINFO` (only `pkgdesc`/`pkgver`/etc. are
mirrored), so that half of the fix only touches the PKGBUILD files
themselves. Verify with `namcap` on both `packaging/PKGBUILD` and
`packaging/PKGBUILD-git` afterwards — expected: zero warnings. Reference:
these two warnings are the only namcap output left on the PKGBUILDs after
specs 0092/0093 (see `kb/arch-packaging.md` operational notes).

---
