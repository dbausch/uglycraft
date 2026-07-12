# 0062 — Flames placed after layout, in rooms that can host them

## Status

> **Confirmed working (Daniel, 2026-07-12).** Red tests 0044c2c, implementation 5843af7, conservation formula b1da648, kb 37dc0f9. Final-world sweep on HARD: 0 unguarded awards / 1990 rooms (was 18); L11/L13 goldens byte-identical; suite 663 passed. (No standalone backlog entry existed — the defect was found during the 0058 review.)

- [x] Red tests: flame-room count == max(1, G // 2) with real jets in the
      dict; every flame room's award on far tiles; no jetless flame room
      with an award; graph carries no flame data; flame ∩ enemy and
      flame ∩ puzzle rooms empty; no item left on a jet line
- [x] Graph phase: `add_flames` and `Node.has_flames` removed;
      `has_flames` stays a feature-set key consumed at layout
- [x] Layout phase: level-wide flame pass — jet-capable room selection
      by geometry, conflicting items relocated off the jet line,
      challenge award on far tiles, before enemy distribution;
      `LayoutError` only when no room in the level can host a jet
- [x] Final-world sweep (`sweep_award_visibility2.py`): HARD E2
      violations 0 across ≥ 80 levels (currently ~18: jetless flame
      rooms with free awards)
- [x] Goldens/hashes checked (only levels 15–20 streams shift; the
      L11/L13 golden walks are expected byte-identical); `poe test`
      exits 0
- [x] KB updated (architecture flame section; R-P10 wording; EASY
      free-award design note); backlog entry closed
- [x] User play-test confirmation: every flame room has visible jets
      with its award behind them; no more free awards in plain rooms on
      HARD

## Problem

`add_flames` marks flame rooms at graph time, where a `Node` has no
dimensions — but `_generate_flame_jets` (layout) is demanding: room
extent ≥ 4 in one dimension, a full wall-to-wall interior cross-cut of
≥ 3 tiles, floor on both sides, not on the entry lane, and a reinforced
anchor tile for the nozzle.  When no candidate survives, the generator
returns **no jets and nobody notices**: the room keeps `has_flames`
(excluding it from enemy hosting) and keeps its spec-0058 challenge
award, which the far-tile pass then drops onto plain floor.

The final-world sweep (`scratchpad/sweep_award_visibility2.py`,
2026-07-12) measured the result: ~18 of 80 levels contain a "flame"
room with no flames and a freely accessible award (verified: level 17,
game seed 0, `room_18` — `has_flames` in the graph, empty `flame_jets`,
award behind a plain breakable wall).  Spec 0060's smaller rooms
(4–6 per grid) made the marginal geometry common.

This is the same disease spec 0058 cured for enemies: the graph
promises what only the layout can geometrically honour, and the failure
is silent.  Flames, like enemies, never affect solvability
(`validate_playability` ignores them; flame tiles stay passable floor —
a timing hazard, not a wall), so nothing anchors them to the graph
phase (Daniel, 2026-07-12).

## Design

### Graph phase: flames removed

- `LevelGraphBuilder.add_flames` is deleted; `Node.has_flames` is
  deleted (with its `_build_subgraph` copies and every
  `node.has_flames` consumer).  The graph neither knows nor needs flame
  rooms.
- The flame challenge award moves with it: no graph award for flames
  (locked/gated/water keep theirs).  `has_flames` remains a feature-set
  key, consumed by the layout pass.

### Layout phase: level-wide flame pass

A new pass (working title `_place_flames(level, graph, rng)`) runs
after all grids are built and stitched — mirror of
`_distribute_enemies`, and ordered **before** it:

1. **Count**: `max(1, G // 2)` flame rooms per level where the feature
   set has `has_flames` (unchanged scaling, now enforced at layout).
2. **Candidates**: non-corridor, non-closet placed rooms without
   plates, blocks, or a WATER passage, on any grid, in deterministic
   order (rooms in grid BFS order, nodes in tile_owner order).  A
   candidate qualifies iff `_generate_flame_jets` produces a jet by
   **geometry alone** (size, interior cross-cut, floor on both sides,
   entry lane, nozzle anchor — items do not disqualify a cut).  Entry
   lanes are derived from the room's passages in the room dict
   (doorway holes, doors, gates, breakable walls adjacent to its
   floor).
3. **Selection**: `rng.choice` among qualifying rooms per flame, no
   room twice.  Fewer qualifying rooms than the count → place as many
   as qualify; **zero** on a `has_flames` level → `LayoutError`
   (fresh-seed retry) — a flame level without flames is not generated
   silently.
4. **Item relocation, not avoidance** (review, 2026-07-12: requiring
   item-free cuts would gut the pool in exactly the small rooms that
   are already marginal).  Among a room's geometric cuts, prefer one
   without item conflicts; otherwise take one and **relocate** every
   item sitting on the jet line or the nozzle tile to a free near-side
   tile of the same room — corridor spill as fallback, never onto far
   tiles, so no key or material gets accidentally flame-gated (C7
   philosophy: content relocated, never dropped).
5. **Award**: the pass places one award item (`rng.choice` of item_nos
   1–9) on a free far tile of the jet — if every far tile is occupied,
   one far-side item is first relocated near-side to make room.  The
   flame challenge reward is thus layout-placed like guard awards;
   R-P10's challenge-room set becomes "locked/gated/water (graph) +
   flame rooms (layout)".
6. **Enemy interaction**: `_distribute_enemies` runs after and excludes
   the chosen flame rooms (replacing its `node.has_flames` check).
   Flame rooms and enemy rooms stay disjoint, as today.

The old per-grid flame machinery in `build_level_dict` (jets before
items, `item_walls` flame exclusion, the far-tile award relocation
pass, `flame_treasures` spill flag) is removed — the jet now claims its
line and displaces items instead of items claiming tiles first.

### Related design decision (recorded, not implemented)

**EASY free awards are a feature** (Daniel, 2026-07-12): on EASY,
`Room.from_data` keeps at most one chaser per grid, so roughly half the
guard awards stand unguarded — accepted as intentional difficulty
tuning (easier loot on EASY).  The final-world sweep therefore
validates E2 (no unguarded open-room awards) on **HARD only**; a KB
design note protects the EASY trim from being "re-fixed".

### RNG / golden impact

Only `has_flames` levels (15–20) change their generation streams; the
recorded golden walks (levels 11 and 13) are expected to stay
byte-identical — verify rather than re-record.  The spec-0054
cross-process determinism guard must stay green (the pass iterates
dicts in insertion order).

## Verification (tests red-first after spec confirmation)

1. **Flame count & integrity** (extends `tests/test_enemy_room_size.py`
   or new module): for generated `has_flames` levels, the number of
   rooms owning `flame_jets` tiles == `max(1, G // 2)` (fewer only if
   candidates ran out — assert equality on the real feature sets);
   every such room has exactly one award, on a far tile of its jet;
   **no award-bearing room without jets, challenge passage, or enemy**
   (the jetless-flame case — red today); **no item on a jet line or
   nozzle tile**.
2. **No graph flame data**: generated graphs have no `has_flames`
   anywhere (attribute gone) — red today.
3. **Disjointness**: flame rooms ∩ enemy rooms == ∅ and ∩ puzzle rooms
   == ∅.
4. **Economy tests updated**: `_challenge_rooms` switches from
   `nd.has_flames` to dict-level jet ownership; totals unchanged.
5. **Final-world sweep**: `sweep_award_visibility2.py` on HARD — E2
   violations 0 across ≥ 80 levels (currently ~18); EASY reported for
   information only.
6. Goldens verified byte-identical (L11/L13); full `poe test` green.

## Done when:

- [x] Flame count/integrity, no-graph-flames, and disjointness tests
      green (red before)
- [x] Economy tests green with the dict-level challenge-room definition
- [x] Final-world sweep: 0 HARD E2 violations across ≥ 80 levels
- [x] L11/L13 goldens byte-identical; `poe test` exits 0
- [x] KB: architecture flame section rewritten, R-P10 updated, EASY
      free-award design note added; backlog entry closed
- [x] Daniel confirms in play: flame rooms always burn, their award
      sits behind the jet, and HARD shows no free awards in plain rooms
