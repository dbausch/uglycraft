# 0058 — Minimum room size for enemies: relocate out of cramped rooms (BL-20)

## Status

- [ ] Red sweep test: every generated enemy start lies in a room whose floor
      tiles contain a full **3×3 free square** — and never in the corridor
      (many seeds × feature sets)
- [ ] Guard tests: enemy count conserved graph → level dict whenever the level
      has ≥ 1 eligible room; the forge ogre always survives on `has_forge_ogre`
      levels; cross-grid spill and last-resort drop each covered by a directed
      test
- [ ] Implementation: relocation cascade — eligible room in the same grid →
      eligible room in another grid → drop; the corridor is never a host
- [ ] Goldens checked; any shifted Act 2 golden re-recorded once and reviewed
- [ ] KB updated: new invariant R-P9 in `kb/requirements.md`, item-placement
      section in `kb/architecture.md`, BL-20 closed in `kb/backlog.md`
- [ ] Full suite green (`poe test` exits 0)
- [ ] User play-test confirmation

## Revision history

- **v2 (2026-07-11).** Three changes against v1:
  1. The corridor is **never** an enemy host — not even as fallback
     (supersedes BL-20's fix-hint clause "the corridor is large and remains
     eligible").
  2. Relocation cascades **same grid → other grids → drop** (v1 fell back to
     the corridor and never dropped).
  3. Eligibility strengthened from *floor bounding box ≥ 3×3* to *floor
     contains a **3×3 free square***, so closet-carved (non-rectangular)
     parents and closets are judged by their actual floor shape. Closets and
     carved parents **remain eligible hosts** when they pass the test.

## Problem

Enemies can be assigned to narrow rooms — placed bounding box width < 3 or
height < 3 — where the player has no space to dodge: in a 2-wide room the
player and a chasing enemy share a two-lane strip, and a wrong step is an
unavoidable hit. BL-20: restrict enemy starts to rooms of at least 3×3.

Why it happens:

- **Graph stage** (`LevelGraphBuilder.add_enemies`, `levelgraph.py` ~line 681):
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

### Where: layout stage — per-grid check plus a super-grid resolution pass

The check must live at layout time because that is the first point where room
dimensions exist (`PlacedNode.w/h/floor_tiles`). Two hook points:

- **`build_level_dict`** (item-placement loop ~line 2465, which calls
  `_place_items_in_room(node, placed[name], …)` for every placed node):
  classifies each enemy-bearing placed node. Eligible → enemies placed as
  today. Ineligible → relocate to an eligible host **of the same grid**; if
  the grid has none, the enemies are **deferred** (multi-grid) or **dropped**
  (single-grid — no other grid exists).
- **`_build_super_grid`**: after all grids are built, a resolution pass places
  every deferred enemy into an eligible host of **any** grid; enemies with no
  eligible host anywhere in the level are dropped.

Deferred enemies travel from `build_level_dict` to `_build_super_grid` via an
extra return value or a transient room-dict key — implementer's choice, but a
transient key must be stripped before the dict leaves the layout stage (the
runtime level dict format is unchanged).

### Eligibility criterion: a 3×3 free square; the corridor is never a host

A placed node is an **eligible enemy host** iff:

- it is **not** the CORRIDOR node, and
- it has no `blocks`, `plates`, or `has_flames` (the same exclusions
  `add_enemies` applies — a relocated enemy must not break a push puzzle or
  land in a flame room), and
- its `floor_tiles` contain at least one **3×3 free square**: some `(c, r)`
  such that all nine tiles `(c..c+2) × (r..r+2)` are floor.

For plain rectangular rooms the free-square test is exactly v1's
bbox ≥ 3×3 test. For non-rectangular floors it is strictly stronger,
deliberately: a closet-carved parent keeps its pre-carve `w/h` while its
floor shrinks and may become L-shaped, so both `w/h` **and** the floor bbox
can overstate the actual open space. The free-square test measures real dodge
room and automatically covers today's office/corner carves and future L-rooms
(BL-07). v1's "known accepted limitation" (thin-armed rooms passing on bbox)
disappears.

**Closets are eligible hosts** when they pass the test (Daniel, 2026-07-11):
no categorical exclusion by node size — a large closet may receive relocated
enemies just like a room. Note that `add_enemies` draws only from ROOM/HALL
nodes, so closets (like the corridor) never have *graph-assigned* enemies;
they enter the picture only as relocation hosts. The graph-stage distribution
is unchanged by this spec.

**The corridor is never a host** (v2; overrides BL-20's "the corridor is
large and remains eligible"): it is the mandatory transit artery — an enemy
confined to it patrols the player's only route between rooms, including
`player_start` — and its band is mostly 2–3 tiles wide, exactly the no-dodge
geometry this spec removes. Since `add_enemies` never assigns enemies to the
corridor, the ban binds only the relocation path. (Item spill to the corridor
— spec 0030 `spill_floor` — is untouched; this spec is about enemies only.)

### What happens to enemies of an ineligible room: cascade, drop last

For each placed node that has `node.enemies` but is not an eligible host:

1. **Same grid.** Build the host pool: eligible hosts among the grid's placed
   nodes. For each enemy, draw one host uniformly (`rng.choice` per enemy,
   mirroring `add_enemies`' per-enemy distribution).
2. **Other grids.** If the same-grid pool is empty and the level is
   multi-grid, defer; the `_build_super_grid` resolution pass builds the
   level-wide pool (grids in BFS build order, eligible hosts per grid) and
   draws one host per enemy the same way.
3. **Drop.** If no eligible host exists in the entire level, the enemy is
   dropped. It is never placed in the corridor.

Placement inside the host uses the existing enemy pass of
`_place_items_in_room` semantics unchanged: random floor tile (not
necessarily inside the free square), prefer ≥ `MIN_ENEMY_DIST` from the
player if the player starts in that room, no tile reservation (enemies may
stand on items), no spill. Extract that enemy pass into a helper so the
super-grid resolution pass can apply it to already-built room dicts.

**No capacity notion** (interpretation to confirm): hosts are drawn with
replacement, as `add_enemies` already does, so there is no per-room enemy cap
and "no adequately sized room left" is read as "none *exists*", not "all are
full". Drops therefore occur only when a level has **zero** eligible rooms —
a degenerate outcome essentially unseen on real feature sets.

Why cascade rather than v1's corridor fallback, or dropping immediately:

- **The forge ogre.** `add_enemies` places at most one `forge_ogre` per level
  (`has_forge_ogre` feature sets). Relocation preserves it whenever *any*
  eligible room exists anywhere in the level — true for every realistic
  `has_forge_ogre` feature set. In the degenerate zero-eligible-room case it
  drops with the rest: accepted.
- **Difficulty is a feature-set contract.** `enemy_count` ranges in
  `ACT2_FEATURE_SETS` define the intended challenge; sub-3×3 rooms are common
  enough (R-P4 permits w=2 / h=2 routinely) that dropping instead of
  relocating would visibly thin out enemies on some seeds.
- **C7 alignment.** Keys/treasures/materials keep the strict "relocated,
  never dropped" guarantee. Enemies were already outside it — C7 drops the
  enemies of *unplaced* nodes today (out of scope, unchanged) — so v2's
  last-resort drop adds a second, rarer drop path rather than breaking an
  invariant.

Side effect, accepted: `add_enemies` guarantees a treasure in each enemy room
("guarded treasure"). After relocation the treasure stays in the small room
while its guard moves elsewhere. The pairing is flavour, not an invariant;
the treasure remains collectable.

### Runtime: no changes needed

`World._tag_enemies_with_rooms` (world.py ~line 344) derives each enemy's
confinement room from the **tile owner of its start tile**, not from the graph
node it was assigned to. A relocated enemy therefore automatically patrols and
is confined to its host room — including a cross-grid relocated enemy, which
simply appears in the host grid's `enemy_starts` and is tagged by that grid.
`world.py`, `entities.py`, `game.py` are untouched.

### Determinism and rng discipline (spec 0054 rule)

- Host pools must be built by iterating `graph.nodes` / the `placed` dict
  (dicts — insertion order) — never a str-set — so `rng.choice` pools are
  process-independent. The level-wide pool iterates grids in BFS build order.
- Extra rng draws happen **only** when an ineligible enemy room exists in the
  level. Same-grid draws happen inside that grid's stream segment; deferred
  cross-grid draws happen after all grids are built, appended at the end of
  the stream. Levels without an ineligible enemy room keep a byte-identical
  generation stream.

### Golden-trace impact

Seeds whose generation contains an ineligible enemy room get a shifted stream /
different enemy starts. Check the Act 2 goldens (`act2_L11_walk`,
`act2_L13_walk`) and the spec-0054 canonical hashes; re-record any changed
golden once (`UGLYCRAFT_REGOLD=1`) and review the diff. Unaffected goldens
must stay byte-identical.

### New invariant (kb/requirements.md)

**R-P9** No enemy start tile ever belongs to the corridor. Every enemy start
tile belongs to a node whose floor tiles contain a full 3×3 free square.
Enemies of an ineligible placed node are relocated to an eligible room of the
same grid, else of another grid; they are dropped only when the level has no
eligible room at all — then, and only then, may the enemy count shrink from
graph to level dict.

## Tests (red first — design only, no code here)

New `tests/test_enemy_room_size.py` (or extension of
`tests/test_placement_rules.py`), run via `poe test`:

1. **Size property sweep (the lock, red today):** over many seeds × feature
   sets (grid counts 1–6, enemy counts high enough to hit small rooms),
   generate `LevelGraph.generate` + `build_level_dict` /
   `_build_super_grid`; for every grid's room dict, resolve each
   `enemy_starts` tile's owning node via the room's `tile_owner`, recover the
   owner's floor tiles from `tile_owner`, and assert the owner is **not** the
   corridor and its floor contains a 3×3 free square.
2. **Conservation guard:** in the same sweep, assert each level has ≥ 1
   eligible room (expected to hold for every real feature set), then that
   total `enemy_starts` across grids equals the total `node.enemies` over
   placed nodes — proves the cascade relocates instead of dropping (guards
   against a "skip" implementation).
3. **Cross-grid spill (directed):** a multi-grid case where one grid's only
   enemy room is ineligible while another grid has an eligible room → the
   enemy appears in the other grid's `enemy_starts`, total count conserved.
   If steering the packers into that shape is impractical, exercise the
   relocation resolver directly with synthetic placed dicts.
4. **Last-resort drop (directed):** resolver-level case with only ineligible
   rooms in the whole (single-grid) level → the enemies are dropped, the
   corridor's tiles carry no enemy start, and no exception is raised.
5. **Forge guard:** for a `has_forge_ogre` feature set over several seeds,
   exactly one `forge_ogre` appears among the enemy starts.
6. **Manual detector sweep** (not in suite, per the statistical-sweep
   discipline): a scratchpad script counting violations (ineligible-room
   starts *and* corridor starts), validated against the pre-fix commit (must
   find violations there), then 0 violations post-fix across ≥ 100 generated
   levels.

## Done when:

- [ ] Sweep test asserts every enemy start is in a non-corridor room whose
      floor contains a 3×3 free square — red before, green after
- [ ] Conservation test: enemy count preserved graph → dict on every level
      with ≥ 1 eligible room; forge ogre present on every `has_forge_ogre`
      level tested
- [ ] Directed tests: cross-grid spill places the enemy in another grid;
      zero-eligible-room level drops enemies without error and without
      touching the corridor
- [ ] Manual detector sweep: violations found on the pre-fix commit,
      0 violations post-fix across ≥ 100 generated levels
- [ ] Unaffected levels generate byte-identically (spec-0054 probe); shifted
      goldens re-recorded once and reviewed; `poe test` exits 0
- [ ] R-P9 added to `kb/requirements.md`; `kb/architecture.md` item-placement
      section updated; BL-20 closed in `kb/backlog.md`
- [ ] Daniel confirms in play that no enemy appears in a cramped room or the
      corridor
