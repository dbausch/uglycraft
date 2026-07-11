# 0058 — Enemy distribution by room size: biggest-first with virtual downsizing (BL-20)

## Status

- [ ] Red sweep test: no enemy start in the corridor; per room, enemy count
      `n ≤ s − 2` where `s` = side of the room's largest all-floor square
      (many seeds × feature sets)
- [ ] Guard tests: all graph enemies placed whenever level capacity
      `Σ max(0, s − 2)` suffices; the forge ogre always survives on
      `has_forge_ogre` levels; directed tests for biggest-empty-first order,
      round-robin before doubling, downsizing capacity stop, drop past
      capacity
- [ ] Implementation: level-wide layout-stage enemy distribution
      (fewest-enemies room first, largest effective size within a round),
      replacing per-node enemy placement; corridor never a host
- [ ] Goldens: all enemy-bearing Act 2 goldens and spec-0054 canonical hashes
      expected to shift; re-recorded once and reviewed
- [ ] KB updated: new invariant R-P9 in `kb/requirements.md`, item-placement
      section in `kb/architecture.md`, BL-20 closed in `kb/backlog.md`
- [ ] Full suite green (`poe test` exits 0)
- [ ] User play-test confirmation

## Revision history

- **v3 (2026-07-11).** Generalized from "check + relocate" to a **full
  layout-stage distribution rule** for all enemies (Daniel: "derive a
  sensible generalized rule"): every enemy goes to the candidate room with
  the fewest assigned enemies, largest **effective size** first, where each
  already-assigned enemy virtually downsizes its room by one tile in both
  dimensions (`s → s − k`). The v2 relocation cascade and spread preference
  become corollaries. Graph-stage `add_enemies` is untouched; its per-node
  room assignment is no longer used for placement.
- **v2 (2026-07-11).** Against v1: (1) the corridor is **never** an enemy
  host — supersedes BL-20's "corridor remains eligible" hint; (2) relocation
  cascades same grid → other grids → drop (superseded by v3's level-wide
  rule); (3) eligibility strengthened from *floor bbox ≥ 3×3* to *floor
  contains a 3×3 free square*, so closet-carved (non-rectangular) parents
  and closets are judged by actual floor shape and **remain eligible** when
  they pass; (4) spread preference — enemy-free rooms first (superseded by
  v3, which extends it to a full round-robin).

## Problem

Enemies can be assigned to narrow rooms — placed bounding box width < 3 or
height < 3 — where the player has no space to dodge: in a 2-wide room the
player and a chasing enemy share a two-lane strip, and a wrong step is an
unavoidable hit. BL-20: restrict enemy starts to rooms of at least 3×3.

Why it happens:

- **Graph stage** (`LevelGraphBuilder.add_enemies`, `levelgraph.py` line 681):
  enemies are distributed by `rng.choice` over all ROOM/HALL nodes that have no
  blocks, plates, or flames. At this point **room dimensions do not exist** —
  a `Node` has no size in tiles; dimensions are decided later by the zone
  packers at layout time. The graph stage cannot filter by size.
- **Layout stage** (`levellayout.py`): the packers legally produce rooms down
  to `w ≥ 2, h ≥ 2` (invariant R-P4). `_pack_band` rooms span the full zone
  height (which can be 2); per-room width can be 2. `_pack_band_vertical`
  symmetrically. So 2-wide / 2-high rooms are a normal, common outcome.
- **Closet carving** (`_carve_closets`, `levellayout.py` line 1383): a carved
  parent keeps its pre-carve `w/h` bbox while its floor shrinks and may become
  L-shaped, so even a bbox that looks roomy can hide a floor with no open
  fighting space. Closets themselves are small by construction (back/side
  office ~⅓ of the parent, corner toilet ~⅕).
- **Enemy placement** (`_place_items_in_room`, `levellayout.py` ~line 2159):
  each `node.enemies` entry gets a random in-room floor tile (preferring
  tiles ≥ `MIN_ENEMY_DIST = 10` BFS steps from the player if the player starts
  in that room). There is no size or shape check anywhere.

Act 1 (levels 1–10) is hand-authored and unaffected; this spec touches the
Act 2 generator only.

## Design

### The distribution rule

For each placed node `R`, define:

- `s(R)` — the side length of the largest **all-floor square** inside
  `R.floor_tiles` (for rectangular rooms this is `min(w, h)`).
- `k(R)` — the number of enemies assigned to `R` so far during distribution.
- **Effective size** `e(R) = s(R) − k(R)`: each already-assigned enemy
  virtually downsizes the room by one tile in both dimensions.

`R` is a **candidate** for the next enemy iff:

- it is **not** the CORRIDOR node, and
- it has no `blocks`, `plates`, or `has_flames` (the `add_enemies`
  exclusions — an enemy must not break a push puzzle or hold a flame room),
  and
- `e(R) ≥ 3` — it still has a `3×3` free square *after* the virtual
  downsizing for the enemies it already holds.

The level's enemies (see "What is distributed" below) are placed **one at a
time**, the forge ogre first, each into the candidate room selected by:

1. **fewest assigned enemies** `k(R)` (round-robin: every candidate receives
   its 1st enemy before any receives a 2nd, its 2nd before any 3rd, …), then
2. **largest effective size** `e(R)` (within a round, "the still biggest
   room after deducting"), then
3. largest floor-tile count (raw area as tie-break), then
4. one `rng.choice` among remaining ties.

An enemy with **no candidate room** (level capacity exhausted, or a level
with no `s ≥ 3` room at all) is **dropped** — never placed in the corridor.
Per-room capacity falls out of the rule as `s − 2` (a 3×3 room holds 1 enemy,
4×4 holds 2, 5×5 holds 3, …); level capacity is `Σ max(0, s(R) − 2)` over
candidate rooms.

Corollaries — the rule subsumes all earlier revisions:

- v1/BL-20: no enemy ever stands in a room without a 3×3 free square
  (candidacy requires `e ≥ 3 ⇒ s ≥ 3`).
- v2 corridor ban and closet handling: the corridor is categorically
  excluded; closets and carved parents are candidates whenever their actual
  floor passes the free-square test (`s` is computed from `floor_tiles`, so
  L-shaped post-carve floors are judged by shape, not bbox).
- v2 spread preference: criterion 1 is exactly "all big enough rooms receive
  an enemy before any receives a second", extended recursively to later
  rounds.

**Interpretations to confirm** (my generalization choices):

- *"Biggest room" = largest free square, area only as tie-break.* Dodge
  space is what BL-20 protects, and the free-square side is the downsizing
  dimension; a 3×20 strip (s=3) therefore ranks below a 5×5 room (s=5)
  despite its larger area.
- *Strict round-robin across all rounds* (criterion 1), not just
  "empty rooms first, then pure biggest-effective": it extends your
  stated pattern recursively and keeps enemies spread.
- *No hard drop threshold besides capacity:* drops occur only when
  `Σ max(0, s − 2)` is exhausted — rare on real feature sets, but no longer
  impossible on enemy-dense seeds; the conservation test is conditioned on
  capacity sufficing.

### What is distributed: the graph's enemy list; `add_enemies` untouched

`add_enemies` (levelgraph.py lines 681–702) keeps deciding **how many**
enemies exist, their types, and forge-ogre uniqueness — the graph rng stream
stays byte-identical. Its per-node room assignment is simply no longer used
for placement: the layout stage collects the level-wide enemy list by
iterating `graph.nodes` (dict — insertion order) and concatenating
`node.enemies` (forge ogre moved to the front), then runs the distribution
rule.

Consequences, both flagged for confirmation:

- **Guarded treasure decouples.** `add_enemies` seeds a treasure into each
  room it assigns an enemy to (lines 700–702); treasures stay where the
  graph put them while enemies now stand wherever the rule sends them. The
  pairing was declared flavour, not an invariant, in v1; if it should be
  preserved, treasure placement would have to follow enemy distribution —
  out of scope unless requested.
- **Enemies of unplaced nodes are no longer dropped.** The collection walks
  *all* nodes, so the C7 enemy-drop path (enemies of nodes the packer
  dropped) closes as a side effect: those enemies enter the pool like any
  others. (`add_flames`' exclusion of graph-enemy rooms keeps flame rooms
  from being *graph-designated* enemy rooms; actual enemy placement excludes
  flame rooms via candidacy, so no enemy ever lands in one regardless.)

### Where: one level-wide pass at layout time

The rule needs every grid's `PlacedNode` sizes, so it cannot run per grid.
The item-placement loop in `build_level_dict` (~line 2465) **stops placing
enemies**; a new distributor (working title `_distribute_enemies(grids,
rng)`) runs once per level:

- **multi-grid:** called by `_build_super_grid` after all grids are built
  and stitched, over all grids' placed dicts / room dicts (grids in BFS
  build order).
- **single-grid:** called by `build_level_dict` itself as a final pass when
  it is not part of a super-grid build (the existing call-shape distinction
  between the two paths decides; no transient room-dict keys needed — the
  distributor writes `enemy_starts` directly).

Placement inside the chosen room reuses the existing enemy pass of
`_place_items_in_room` semantics unchanged: random floor tile (not
necessarily inside the free square), prefer ≥ `MIN_ENEMY_DIST` from the
player if the player starts in that room, no tile reservation (enemies may
stand on items), no spill. Extract that enemy pass into a helper the
distributor can apply to already-built room dicts.

### Runtime: no changes needed

`World._tag_enemies_with_rooms` (world.py ~line 344) derives each enemy's
confinement room from the **tile owner of its start tile**, not from the graph
node it was assigned to. An enemy distributed to any room on any grid
automatically patrols and is confined there. `world.py`, `entities.py`,
`game.py` are untouched.

### Determinism and rng discipline (spec 0054 rule)

- The candidate ranking is deterministic (k, e, area) with a single
  `rng.choice` among exact ties; pools are built by iterating `graph.nodes` /
  placed dicts (insertion order) and grids in BFS build order — never a
  str-set — so distribution is process-independent.
- The graph stream is untouched (`add_enemies` unchanged). The layout stream
  changes on **every enemy-bearing level**: enemy tile draws move from the
  per-node item loop to the final distribution pass. This is inherent to the
  design — see golden impact.

### Golden-trace impact

Unlike v1/v2 (which shifted only levels containing a too-small enemy room),
v3 moves enemy placement for **every** level with enemies: expect all Act 2
goldens (`act2_L11_walk`, `act2_L13_walk`) and the spec-0054 canonical hashes
to shift. Re-record each once (`UGLYCRAFT_REGOLD=1`) and review the diffs;
levels without enemies (if any feature set produces one) must stay
byte-identical.

### New invariant (kb/requirements.md)

**R-P9** No enemy start tile ever belongs to the corridor. For every room,
the number of enemy starts it holds is at most `s − 2`, where `s` is the side
of the room's largest all-floor square (equivalently: every room with `n`
enemies still has an `(n+2)×(n+2)` free square — a 3×3 square remains after
virtually downsizing by one tile per enemy in both dimensions). Enemies are
dropped only when no candidate room remains in the entire level — then, and
only then, may the enemy count shrink from graph to level dict.

## Tests (red first — design only, no code here)

New `tests/test_enemy_room_size.py` (or extension of
`tests/test_placement_rules.py`), run via `poe test`:

1. **Size property sweep (the lock, red today):** over many seeds × feature
   sets (grid counts 1–6, enemy counts high enough to hit small rooms),
   generate `LevelGraph.generate` + `build_level_dict` /
   `_build_super_grid`; for every grid's room dict, resolve each
   `enemy_starts` tile's owning node via the room's `tile_owner`, recover the
   owner's floor tiles from `tile_owner`, and assert the owner is **not**
   the corridor and holds at most `s − 2` enemy starts (`s` from its floor
   tiles).
2. **Conservation guard:** in the same sweep, compute level capacity
   `Σ max(0, s − 2)` over candidate rooms and assert that whenever capacity
   ≥ the graph's total enemy count (expected on every real feature set),
   total `enemy_starts` across grids equals the graph total over **all**
   nodes — proves nothing is dropped while room remains, and covers the C7
   unplaced-node enemies.
3. **Distribution order (directed, distributor-level with synthetic placed
   dicts):**
   (a) the first enemy lands in the level's biggest room (largest `s`,
   cross-grid);
   (b) round-robin: every candidate room receives one enemy before any
   receives a second;
   (c) within a round, the room with the largest `e = s − k` is served
   first;
   (d) capacity: an `s = 3` room never exceeds 1 enemy, `s = 4` never
   exceeds 2.
4. **Last-resort drop (directed):** a level whose candidate capacity is
   below its enemy count → the surplus is dropped, the corridor's tiles
   carry no enemy start, and no exception is raised.
5. **Forge guard:** for a `has_forge_ogre` feature set over several seeds,
   exactly one `forge_ogre` appears among the enemy starts; placed first, it
   stands in a room of maximal `s`.
6. **Manual detector sweep** (not in suite, per the statistical-sweep
   discipline): a scratchpad script counting violations (rooms over
   `s − 2` capacity *and* corridor starts), validated against the pre-fix
   commit (must find violations there), then 0 violations post-fix across
   ≥ 100 generated levels.

## Done when:

- [ ] Sweep test asserts no corridor enemy starts and per-room
      `n ≤ s − 2` — red before, green after
- [ ] Conservation test: enemy count preserved graph → dict (all nodes,
      including unplaced) on every level whose capacity suffices; forge ogre
      present on every `has_forge_ogre` level tested
- [ ] Directed distributor tests: biggest-empty-first, round-robin before
      doubling, largest-effective-first within a round, per-room capacity
      stop, drop past capacity without touching the corridor
- [ ] Manual detector sweep: violations found on the pre-fix commit,
      0 violations post-fix across ≥ 100 generated levels
- [ ] All shifted goldens and canonical hashes re-recorded once and
      reviewed; `poe test` exits 0
- [ ] R-P9 added to `kb/requirements.md`; `kb/architecture.md` item-placement
      section updated; BL-20 closed in `kb/backlog.md`
- [ ] Daniel confirms in play that no enemy appears in a cramped room or the
      corridor, and enemy spread across rooms feels right
