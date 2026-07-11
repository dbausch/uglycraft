# 0058 — Enemy and award placement: layout-stage enemies, challenge-based awards (BL-20+)

## Status

- [ ] Red sweep tests: no enemy start in the corridor; per room, enemy count
      `n ≤ s − 2` (`s` = side of the room's largest all-floor square); total
      enemies exactly `2 × G` for `G` grids; every award item lies in a
      challenge-protected room or an enemy room; award conservation
      `#awards = #challenge rooms + #enemies`
- [ ] Graph phase: `add_enemies` removed (`Node.enemies` gone, subgraph
      copies dropped); `add_treasures` replaced by challenge rewards — one
      award per locked / gated / flame / water room; feature-set
      `treasure_count` / `enemy_count` keys retired
- [ ] Challenge scaling: exactly `max(1, G // 2)` flame rooms and
      `max(1, G // 3)` water rooms per level; WATER removed from the
      stochastic edge draw
- [ ] Layout phase: enemy total fixed at `2 × G`; distribution by
      the size rule (fewest-enemies candidate, largest effective size
      `e = s − k`, forge ogre first); one award item placed alongside each
      enemy in its room
- [ ] Goldens: all Act 2 goldens and spec-0054 canonical hashes shift
      (graph stream changes); re-recorded once and reviewed
- [ ] KB updated: R-P9 + R-P10 in `kb/requirements.md`, graph/item-placement
      sections in `kb/architecture.md`, BL-20 closed in `kb/backlog.md`
- [ ] Full suite green (`poe test` exits 0)
- [ ] User play-test confirmation

## Revision history

- **v4.1 (2026-07-11).** Enemy count fixed at exactly `2 × G` (no random
  draw, no per-grid counter). Challenge counts become deterministic
  rules, compensating the removed award sprinkle: **one fire room per 2
  grids and one water room per 3 grids in total** (`⌊G/2⌋` / `⌊G/3⌋`,
  min 1 where the feature is enabled). WATER leaves the stochastic
  edge-type draw. (An intermediate draw-weight variant was discarded —
  Daniel wants counts, not probabilities.)
- **v4 (2026-07-11).** Objective widened (Daniel): enemies and award items
  become one economy. Enemies leave the graph phase entirely (they never
  affected solvability); the layout distributor places exactly 2 per grid
  (`2 × G` total, level-wide) by the v3 size rule, adding **one award item
  per enemy** into the enemy's room. Graph-phase treasures are no longer
  random: **every award item is the reward of a challenge** — a locked,
  gated, flame, or water room (graph phase) or an enemy guard (layout
  phase); no award items exist beyond that.
- **v3 (2026-07-11).** Generalized placement to a level-wide distribution
  rule: fewest-enemies candidate first, largest effective size
  `e = s − k`, each assigned enemy virtually downsizes its room by one tile
  in both dimensions; per-room capacity `s − 2`. Kept in v4.
- **v2 (2026-07-11).** The corridor is never an enemy host (supersedes
  BL-20's "corridor remains eligible" hint); eligibility judged by a
  **3×3 free square** over actual floor tiles, so closet-carved
  (non-rectangular) parents and closets qualify by shape and remain
  eligible when they pass. Kept in v4. (v2's relocation cascade and spread
  preference were superseded by v3's rule.)

## Problem

Two placement defects, one economy:

1. **Enemies in cramped rooms (BL-20).** Enemies can be assigned to rooms
   with no space to dodge — placed bounding-box width or height < 3, and,
   worse, closet-carved parents whose roomy-looking bbox hides an L-shaped
   floor. In a 2-wide room the player and a chasing enemy share a two-lane
   strip; a wrong step is an unavoidable hit. The graph stage
   (`LevelGraphBuilder.add_enemies`, `levelgraph.py` line 681) cannot
   filter by size — a `Node` has no dimensions; the packers legally
   produce rooms down to `w ≥ 2, h ≥ 2` (R-P4); and the enemy pass of
   `_place_items_in_room` (~line 2159) has no size or shape check.
2. **Award items are placed for no reason.** `add_treasures`
   (levelgraph.py line 663) sprinkles `treasure_count` (6–18 per feature
   set) awards over uniformly random nodes, and `add_enemies` seeds one
   more into each enemy room. Awards neither mark nor motivate anything:
   a player can amass most of the score without touching a single
   challenge.

Enemies contribute nothing to solvability — `validate_playability` never
reads `node.enemies` — so nothing anchors them to the graph phase.

Act 1 (levels 1–10) is hand-authored and unaffected; this spec touches the
Act 2 generator only.

## Design

### Objective: every award is the reward of a challenge

The function of award items is to make the player solve all challenges.
Therefore an award item exists in exactly two forms, and no other:

- **Challenge reward (graph phase):** one award in every room protected by
  a challenge — behind a LOCKED edge, behind a GATED edge, a flame room
  (`has_flames`), or a water room (behind a WATER edge).
- **Guard reward (layout phase):** one award per enemy, placed in the room
  the enemy is distributed to.

There are no unconditional award items. Total award count per level
becomes `#challenge rooms + #enemies` instead of the feature set's
`treasure_count` draw — fewer than today's 6–18 sprinkle. To compensate,
challenge counts follow deterministic per-grid rules (v4.1, see
"Challenge scaling" below), so the award economy shrinks less and the
game gains challenge density — which is the point.

### Graph phase: enemies removed, awards attached to challenges

- **`add_enemies` is deleted**, along with the `Node.enemies` field, the
  `enemy_count` feature-set key, the `_build_subgraph` enemy copies
  (levellayout.py lines 2642/2651), and the enemy pass of
  `_place_items_in_room`. `add_flames`' "no enemy room" exclusion drops
  with it (enemy placement excludes flame rooms at layout instead, see
  candidacy below). The graph neither knows nor needs enemy positions.
- **`add_treasures` (uniform random) is replaced.** Each challenge-adding
  builder method — locked room, gated room, water room, flames — appends
  **one award item** (`rng.choice` of item_nos 1–9, as today) to the room
  it protects, atomically at challenge creation, exactly as those methods
  already place their prerequisite items atomically. The
  `treasure_count` feature-set key is retired.
- `has_forge_ogre` stays a feature-set key, consumed by the layout
  distributor (below).
- Out of scope, flagged: locked/gated **BORDER** edges (grid-level
  challenges) do not add a grid-wide award; the protected grid's own
  challenge rooms already carry theirs.

Existing flame-room behaviour is unchanged: layout relocates a flame
room's award to jet far-tiles, so the reward stays collectable.

**Challenge scaling (v4.1)** — deterministic counts derived from the
grid count `G`, compensating the retired award sprinkle. No
probabilities: previously flame rooms were fixed at one (`has_flames` →
one `add_flames()` call) and water rooms emerged stochastically from the
repetition-weighted `edge_types` draw (one guaranteed via `required`,
extras by `rng.choice`). Now:

- **Fire: one flame room per 2 grids** — `flame_count = max(1, G // 2)`
  where `has_flames` is set (levels 15–20: 5–10 grids → 2–5 flame
  rooms); `generate()` calls `add_flames()` that many times. Each call
  marks one candidate room or silently no-ops if none remains
  (candidates exclude push-puzzle and water rooms) — the graph test
  asserts the exact count, tolerating fewer only when candidates ran
  out.
- **Water: one water room per 3 grids** — `water_count = max(1, G // 3)`
  where water is enabled (level 14: 4 grids → 1; level 20: 10 grids →
  3). **WATER is removed from the `edge_types` draw list**; instead
  `water_count` WATER entries are prepended to the `required` room list
  (which already guarantees one room per distinct edge type), so exactly
  that many water rooms are built and the remaining `room_count` slots
  draw from the non-WATER types. Feature sets signal water with a
  `has_water: True` key replacing WATER's presence in `edge_types`.
- Rounding is `floor` with a minimum of 1 wherever the feature is
  enabled (interpretation to confirm; `G // 2` / `G // 3` never hit 0 on
  the current feature sets anyway).
- Plank provisioning auto-scales: `add_water_room` places 2 planks per
  water room (spec 0029 W1), so bridges stay craftable without changes.
- Flame rooms are never enemy hosts, so more of them slightly shrink the
  enemy-candidate pool; the capacity check `Σ max(0, s − 2) ≥ 2G` in the
  tests covers this.

### Layout phase: enemy count, distribution, guard awards

**Count.** Exactly `2 × G` enemies for a `G`-grid level: 2 on a single
grid, 4 on two grids, and so forth. No random draw and no per-grid
counter — enemies are distributed level-wide by the rule below, so which
grid an enemy lands on follows from room sizes alone. Types: all
`chaser`, except that on `has_forge_ogre` feature sets the first enemy is
the (unique) `forge_ogre`.

**Distribution rule (v3, kept).** For each placed node `R`: `s(R)` = side
of the largest all-floor square in `R.floor_tiles` (for rectangles
`min(w, h)`; closet-carved L-shaped floors are judged by actual shape),
`k(R)` = enemies assigned so far, effective size `e(R) = s(R) − k(R)` —
each assigned enemy virtually downsizes its room by one tile in both
dimensions. `R` is a **candidate** iff it is not the CORRIDOR node, has no
`blocks`, `plates`, or `has_flames`, and `e(R) ≥ 3`. Enemies are placed
one at a time (forge ogre first), each into the candidate chosen by:

1. **fewest assigned enemies** `k(R)` (round-robin: every candidate gets
   its 1st before any gets a 2nd, …), then
2. **largest effective size** `e(R)`, then
3. largest floor-tile count, then
4. one `rng.choice` among remaining ties.

An enemy with no candidate room (capacity `Σ max(0, s − 2)` exhausted) is
dropped — never placed in the corridor. Closets and carved parents are
candidates whenever their floor passes; "biggest" means largest free
square (dodge space), with raw area only as tie-break.

**Guard award.** When an enemy is assigned to a room, one award item
(`rng.choice` of item_nos 1–9) is placed in that room through the normal
item pass (tile reservation, room→corridor spill only if the room's floor
is full — rare; enemies themselves reserve no tile and may stand on
items, unchanged).

**Tile selection** for the enemy reuses the existing enemy-pass semantics
of `_place_items_in_room` unchanged: random floor tile (not necessarily
inside the free square), prefer ≥ `MIN_ENEMY_DIST` from the player if the
player starts in that room. Extract into a helper the distributor can
apply to already-built room dicts.

**Where.** The rule needs every grid's `PlacedNode` sizes, so the
distributor (working title `_distribute_enemies(grids, rng)`) runs once
per level: called by `_build_super_grid` after all grids are built and
stitched (grids in BFS build order), and by `build_level_dict` itself as
a final pass on the single-grid path.

### Runtime: no changes needed

`World._tag_enemies_with_rooms` (world.py ~line 344) derives each enemy's
confinement room from the tile owner of its start tile, not from any graph
node. Distributed enemies patrol and stay confined wherever they land;
`world.py`, `entities.py`, `game.py` are untouched (the forge ogre keeps
its runtime behaviour; only where it stands changes).

### Determinism and rng discipline (spec 0054 rule)

- Candidate ranking is deterministic (`k`, `e`, area) with a single
  `rng.choice` among exact ties; pools iterate `graph.nodes` / placed
  dicts (insertion order) and grids in BFS build order — never a str-set.
- The **graph stream changes for every level** (`add_treasures` /
  `add_enemies` draws disappear; challenge methods gain one item draw
  each), and the layout stream gains the distribution pass (the enemy
  count itself is deterministic — no draw). This is inherent to the
  redesign — see golden impact.

### Golden-trace impact

Every Act 2 level's generation stream shifts (graph phase included):
expect **all** Act 2 goldens (`act2_L11_walk`, `act2_L13_walk`) and the
spec-0054 canonical hashes to change. Re-record each once
(`UGLYCRAFT_REGOLD=1`) and review the diffs. The spec-0054 determinism
guard (same hash across processes) must stay green.

### New invariants (kb/requirements.md)

**R-P9** No enemy start tile ever belongs to the corridor. For every room,
the number of enemy starts it holds is at most `s − 2`, where `s` is the
side of the room's largest all-floor square (equivalently: a 3×3 free
square remains after virtually downsizing the room by one tile per enemy
in both dimensions). Enemies are dropped only when no candidate room
remains in the entire level.

**R-P10** Award items exist only as challenge rewards: each locked, gated,
flame, or water room carries one graph-placed award; each enemy adds one
layout-placed award to its room. Total awards per level =
`#challenge rooms + #enemies placed` (modulo full-room spill to the
corridor, which must be the only exception).

## Tests (red first — design only, no code here)

New `tests/test_enemy_room_size.py` (or extension of
`tests/test_placement_rules.py`), run via `poe test`:

1. **Size property sweep (the lock, red today):** many seeds × feature
   sets (grid counts 1–6); for every grid's room dict, resolve each
   `enemy_starts` tile's owner via `tile_owner`, recover the owner's floor
   tiles, assert the owner is not the corridor and holds at most `s − 2`
   enemy starts.
2. **Enemy count:** per level, total enemy starts exactly `2 × G`
   (fewer only if capacity `Σ max(0, s − 2)` < `2G`, which the test
   checks never happens on real feature sets).
3. **Award economy sweep (red today):** every award item's room is
   challenge-protected (reached through a locked/gated passage, has flame
   jets, or lies behind water) or contains ≥ 1 enemy start; total awards
   = challenge rooms + enemies (accounting for corridor spill, expected
   ≈ never).
4. **Distribution order (directed, distributor-level with synthetic
   placed dicts):** (a) first enemy → the level's biggest room (largest
   `s`, cross-grid); (b) round-robin before doubling; (c) largest
   `e = s − k` first within a round; (d) an `s = 3` room never exceeds 1
   enemy, `s = 4` never 2; (e) past capacity → dropped, corridor
   untouched, no exception.
5. **Guard-award pairing (directed):** each enemy's room gained exactly
   one award per enemy assigned to it.
6. **Forge guard:** on `has_forge_ogre` feature sets, exactly one
   `forge_ogre` among the starts, standing in a room of maximal `s`.
7. **Graph phase:** generated graphs carry no enemy data; every
   locked/gated/flame/water room has exactly one graph award; no other
   node has graph awards; flame levels carry exactly `max(1, G // 2)`
   flame rooms (fewer only if candidates ran out) and water levels
   exactly `max(1, G // 3)` water rooms.
8. **Manual detector sweep** (not in suite, per the statistical-sweep
   discipline): scratchpad script counting violations (over-capacity
   rooms, corridor starts, unmotivated awards), validated against the
   pre-fix commit (must find violations there), then 0 violations across
   ≥ 100 generated levels.

## Done when:

- [ ] Sweep tests green: corridor ban + per-room `n ≤ s − 2`; enemy total
      exactly `2 × G`; every award challenge- or enemy-motivated; award
      conservation — all red before the change
- [ ] Directed distributor tests green: biggest-empty-first, round-robin,
      largest-effective within round, capacity stop, drop past capacity,
      guard-award pairing
- [ ] Graph tests green: no enemy data on generated graphs; exactly one
      award per challenge room and none elsewhere; `max(1, G // 2)` flame
      and `max(1, G // 3)` water rooms per enabled level
- [ ] Manual detector sweep: violations found pre-fix, 0 post-fix across
      ≥ 100 levels
- [ ] All shifted goldens and canonical hashes re-recorded once and
      reviewed; `poe test` exits 0
- [ ] R-P9 + R-P10 in `kb/requirements.md`; `kb/architecture.md` graph and
      item-placement sections updated; BL-20 closed in `kb/backlog.md`
- [ ] Daniel confirms in play: no cramped-room or corridor enemies, enemy
      density feels right, and awards read as challenge rewards
