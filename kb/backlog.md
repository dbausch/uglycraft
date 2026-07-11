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

## BL-03 · P1 · Bug: Challenge items placed in wrong grid for border barriers

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

## BL-14 · P1 · Make the push-puzzle subsystem water-aware (remove the _verify_blocks safety net)

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

## BL-16 · P2 · Don't place items on the player start tile (next to the entrance)

Treasures, materials, and keys can currently spawn on the `player_start` tile
because `player_start` is never added to `global_used` in `build_level_dict`
(levellayout.py). An item under the player at spawn is auto-collected or visually
wrong.

**Fix hint:** add `player_start` (and consider the entrance tile) to `global_used`
before any item placement, or exclude it inside `_place_items_in_room`, so nothing
lands on the player's starting position.

---

## BL-17 · P2 · Completely empty rooms are still generated

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
3. Breaking down a wooden door yields 4 planks in one go — a full bridge's worth
   — as a non-scavenging alternative to collecting loose planks. This ties
   plank-sourcing to the existing breakable wooden wall/door mechanic
   (`WALL_WOODEN` / `BREAKABLE` edges).
4. The `add_water_room` algorithm (`levelgraph.py`) provisions, per water room,
   ANY valid combination of these sources whose total equals the equivalent of
   4 planks — e.g. 4 singles, 2 packs, 1 pack + 2 singles, or one wooden door
   (=4) — chosen at random. All sources must remain reachable on the dry side
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

## BL-19 · P1 · Push plates must not be placed next to a room's entrance tile

Pressure plates for push puzzles can currently land on a tile cardinally
adjacent to the room's entrance/connection tile. That is awkward (the player
steps in and is immediately beside the plate) and can trivialise or cramp the
puzzle.

**Fix hint:** in the push-puzzle placement (`_place_puzzle` / `build_level_dict`
in `levellayout.py`), exclude tiles cardinally adjacent to the room's entry tile
(the connection tile from the corridor, found via `_find_connection_tile` — the
same way flame-jet entry detection works) from the plate candidate set.

---

## BL-20 · P2 · Place enemies only in rooms of width >= 3 and height >= 3

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

## BL-21 · P3 · Reduce the number of rooms in level 11

Level 11 (the first Act 2 level, `ACT2_FEATURE_SETS` index 0) generates too many
rooms for an introductory Act 2 level. Reduce its `room_count` range.

**Fix hint:** in `levels.py` (`_act2_feature_sets`), lower the `room_count`
tuple for index 0 (level 11).

---

## BL-22 · P3 · Remove the more complex layout options from levels 11-13

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

## BL-24 · P2 · "The forge is defeated" text overflows the message box

The message shown when the forge (forge ogre) is defeated — text along the lines
of "The forge is defeated" — is too long and overflows its message/dialog box.

**Fix hint:** locate the exact string (it may be a gettext-translated string in a
.po/.pot locale file or a dialog/message call — grep the codebase and locale
files for "forge"/"defeat"), and the routine that renders the message box
(`game.py` / `main.py`). Either shorten the message, wrap the text across lines,
or size the box to the text. Check other in-game messages don't overflow either.

---

## BL-25 · P3 · Scale room count with grid count so late Act 2 levels aren't boring full-border grids

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

## BL-26 · P2 · Gate unfinished crafting content behind constants (hide unused recipes/tools, disable rubble & scrap-metal drops)

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

---

## BL-27 · P2 · Key inventory display: drop the counter (keys are unique) and check for a display bug

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

## BL-28 · P3 · Auto-craft a bridge when bumping water (no crafting-menu step)

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

## BL-30 · P2 · Widen corridor spine width to 2-5 (match unified stem range) after closet redesign

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

## BL-31 · P2 · Ensure the level entrance is created next to a corridor tile, which becomes the player start position

The level entrance should be guaranteed to be placed adjacent to a corridor
floor tile, and that adjacent corridor tile should be the player's start
position. This ensures the player always begins on the corridor spine with
proper connectivity, rather than potentially being placed in a room interior or
somewhere disconnected.

**Fix hint:** when placing the level entrance / player_start in the layout,
anchor it to a corridor tile (the shared spine) and validate the chosen player
start is corridor-owned and adjacent to the entrance. Relates to BL-16 (don't
place items on the player start tile) and the border-corridor stitch work in
spec 0042.

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

## BL-35 · P2 (in progress) · World-model refactor, staged

World-model refactor, staged (→ kb/world-model-review.md §3, §6.6): make
gameplay logic testable and new elements cheap to add. Step 0 (spec 0044
characterization harness) and Stage 1 (spec 0045 World extraction, commit
abe3d16) are DONE; remaining: Stage 2 (Act 1 as one-room Act 2 level, delete
the `_is_multiroom` fork), Stage 3 (layered cell model, walls→barriers,
shadow-grid migration), Stage 4 (behaviour dispatch table + signal channels),
Stage 5 (Room as live object, delete RoomState).

**Fix hint:** one numbered spec per stage, each behaviour-preserving and gated
by the spec-0044 goldens; next up is Stage 2; fine-grained World unit tests
accumulate from Stage 2 onward.
