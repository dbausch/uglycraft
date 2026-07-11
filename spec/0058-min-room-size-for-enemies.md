# 0058 — Minimum room size for enemies: relocate out of sub-3×3 rooms (BL-20)

## Status

- [ ] Red sweep test: every generated enemy start lies in the corridor or in a
      room whose **floor bounding box** is ≥ 3×3 (many seeds × feature sets)
- [ ] Guard tests: enemy count conserved graph → level dict (no drops); the
      forge ogre always survives on `has_forge_ogre` levels
- [ ] Implementation: layout-stage relocation of enemies whose room is too
      small, into an eligible host room (corridor fallback), same grid
- [ ] Goldens checked; any shifted Act 2 golden re-recorded once and reviewed
- [ ] KB updated: new invariant R-P9 in `kb/requirements.md`, item-placement
      section in `kb/architecture.md`, BL-20 closed in `kb/backlog.md`
- [ ] Full suite green (`poe test` exits 0)
- [ ] User play-test confirmation

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
- **Enemy placement** (`_place_items_in_room`, `levellayout.py` ~line 2159):
  each `node.enemies` entry gets a random in-room floor tile (preferring
  tiles ≥ `MIN_ENEMY_DIST = 10` BFS steps from the player if the player starts
  in that room). There is no size check anywhere.

Act 1 (levels 1–10) is hand-authored and unaffected; this spec touches the
Act 2 generator only.

## Design

### Where: layout stage, in `build_level_dict`

The check must live at layout time because that is the first point where room
dimensions exist (`PlacedNode.w/h/floor_tiles`). `build_level_dict` runs once
per grid (the multi-grid path `_build_super_grid` calls it per grid), so a
per-grid implementation covers single- and multi-grid levels uniformly.

Hook point: the item-placement loop in `build_level_dict` (~line 2465), which
calls `_place_items_in_room(node, placed[name], …)` for every placed node.

### Eligibility criterion: floor bounding box ≥ 3×3, corridor exempt

A placed node is an **eligible enemy host** iff:

- it is the CORRIDOR node (`NodeSize.CORRIDOR`) — always eligible per BL-20
  ("the corridor is large and remains eligible"): its band is long even where
  it is only 2–3 tiles wide, so there is always room to dodge along it; **or**
- the bounding box of its **actual floor tiles**
  (`max(col) − min(col) + 1 ≥ 3` **and** `max(row) − min(row) + 1 ≥ 3`
  over `PlacedNode.floor_tiles`) is at least 3×3.

Deliberately the *floor-tile* bbox, not `PlacedNode.w/h`: a closet-carved
parent room keeps its pre-carve `w/h` while its floor shrinks
(`_carve_closets`, `levellayout.py` line 1383 — the reduced room is rebuilt
with the old bbox and a smaller `floor_tiles` set), so `w/h` would overstate
carved rooms. For plain rectangular rooms the two are identical.

Known accepted limitation (BL-20 wording is explicitly bbox-based): a
non-rectangular room whose bbox is ≥ 3×3 but whose arms are thin (corner-carve
L-shapes today, BL-07 L-rooms later) passes the check. Corner carves remove
only ~⅕ of the parent, so this is not a practical trap.

### What happens to enemies of a too-small room: relocate, never drop

For each placed node that has `node.enemies` but is **not** an eligible host,
its enemies are placed **in another room of the same grid** instead:

1. Build the host pool: placed nodes with `size in (ROOM, HALL)`, no
   `blocks`/`plates`/`has_flames` (the same exclusions `add_enemies` applies —
   a relocated enemy must not break a push puzzle or land in a flame room),
   and floor bbox ≥ 3×3.
2. For each enemy of the too-small room, draw one host uniformly from that
   pool (one `rng.choice` per enemy, mirroring `add_enemies`' per-enemy
   distribution).
3. If the pool is empty, the host is the **corridor** (always placed, always
   eligible) — placement is therefore guaranteed; there is no drop path.
4. Placement inside the host uses the existing enemy pass of
   `_place_items_in_room` semantics unchanged: random floor tile, prefer
   ≥ `MIN_ENEMY_DIST` from the player, no tile reservation (enemies may stand
   on items), no spill.

Why relocate rather than drop (the two candidate behaviours):

- **The forge ogre.** `add_enemies` places at most one `forge_ogre` per level
  (`has_forge_ogre` feature sets). If it lands in a 2-wide room and were
  dropped, the level's boss silently disappears — real content loss, not a
  cosmetic difference.
- **Difficulty is a feature-set contract.** `enemy_count` ranges in
  `ACT2_FEATURE_SETS` define the intended challenge; sub-3×3 rooms are common
  enough (R-P4 permits w=2 / h=2 routinely) that dropping would visibly thin
  out enemies on some seeds.
- **Consistency with the C7 philosophy** ("content is relocated, never
  dropped"): keys/treasures/materials of unplaced nodes already spill rather
  than vanish. (C7 does drop the enemies of *unplaced* nodes — that existing
  behaviour is out of scope and unchanged here; this spec is only about
  *placed but too small* rooms.)

Side effect, accepted: `add_enemies` guarantees a treasure in each enemy room
("guarded treasure"). After relocation the treasure stays in the small room
while its guard moves elsewhere. The pairing is flavour, not an invariant;
the treasure remains collectable.

### Runtime: no changes needed

`World._tag_enemies_with_rooms` (world.py ~line 344) derives each enemy's
confinement room from the **tile owner of its start tile**, not from the graph
node it was assigned to. A relocated enemy therefore automatically patrols and
is confined to its host room. `world.py`, `entities.py`, `game.py` are
untouched.

### Determinism and rng discipline (spec 0054 rule)

- The host pool must be built by iterating `graph.nodes` (a dict — insertion
  order) — never a str-set — so `rng.choice` pools are process-independent.
- Extra rng draws happen **only** when a too-small enemy room exists in the
  grid. Levels without such a room keep a byte-identical generation stream.

### Golden-trace impact

Seeds whose generation contains a too-small enemy room get a shifted stream /
different enemy starts. Check the Act 2 goldens (`act2_L11_walk`,
`act2_L13_walk`) and the spec-0054 canonical hashes; re-record any changed
golden once (`UGLYCRAFT_REGOLD=1`) and review the diff. Unaffected goldens
must stay byte-identical.

### New invariant (kb/requirements.md)

**R-P9** Every enemy start tile belongs to the corridor or to a node whose
floor-tile bounding box is ≥ 3×3; enemies of placed nodes are never dropped
(enemy count is conserved from graph to level dict over placed nodes).

## Tests (red first — design only, no code here)

New `tests/test_enemy_room_size.py` (or extension of
`tests/test_placement_rules.py`), run via `poe test`:

1. **Size property sweep (the lock, red today):** over many seeds × feature
   sets (grid counts 1–6, enemy counts high enough to hit small rooms),
   generate `LevelGraph.generate` + `build_level_dict` /
   `_build_super_grid`; for every grid's room dict, resolve each
   `enemy_starts` tile's owning node via the room's `tile_owner`, compute
   that owner's floor bbox from `tile_owner`, and assert the owner is the
   corridor or its bbox is ≥ 3×3 in both axes.
2. **Conservation guard:** in the same sweep, total `enemy_starts` across
   grids equals the total `node.enemies` over placed nodes — proves the fix
   relocates instead of dropping (guards against a "skip" implementation).
3. **Forge guard:** for a `has_forge_ogre` feature set over several seeds,
   exactly one `forge_ogre` appears among the enemy starts.
4. **Manual detector sweep** (not in suite, per the statistical-sweep
   discipline): a scratchpad script counting violations, validated against
   the pre-fix commit (must find violations there), then 0 violations
   post-fix across ≥ 100 generated levels.

## Done when:

- [ ] Sweep test asserts every enemy start is in the corridor or a room with
      floor bbox ≥ 3×3 — red before, green after
- [ ] Conservation test: enemy count preserved graph → dict (no drops);
      forge ogre present on every `has_forge_ogre` level tested
- [ ] Manual detector sweep: violations found on the pre-fix commit,
      0 violations post-fix across ≥ 100 generated levels
- [ ] Unaffected levels generate byte-identically (spec-0054 probe); shifted
      goldens re-recorded once and reviewed; `poe test` exits 0
- [ ] R-P9 added to `kb/requirements.md`; `kb/architecture.md` item-placement
      section updated; BL-20 closed in `kb/backlog.md`
- [ ] Daniel confirms in play that no enemy appears in a cramped room
