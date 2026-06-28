# Spec 0036 — Place enemies only in rooms at least 3x3 (BL-20)

## Status

- [ ] N1 — Enemies are placed only in a **placed** node whose bounding box has
      `w >= 3` **and** `h >= 3`. The size floor is enforced at **layout time**
      (the only layer where `PlacedNode.w/.h` exist), not at graph distribution
      time
- [ ] N2 — An enemy whose home node is placed sub-3x3 is **reassigned** to an
      eligible (`w >= 3, h >= 3`) placed room rather than dropped; the corridor
      (always large, always eligible) is the guaranteed last-resort target, so no
      enemy — including the `forge_ogre` — is ever lost. No new enemies are
      introduced ("place only")
- [ ] N3 — Pytest sweep over many seeds × all Act 2 feature sets asserting no
      enemy start lands on a tile owned by a placed node with `w < 3` or `h < 3`

## The defect

Enemy distribution happens in two stages and **neither stage knows a room's
final size**:

1. **Graph time** — `LevelGraphBuilder.add_enemies` (`levelgraph.py:644-665`,
   the live path; reached via `LevelGraph.generate` at `levelgraph.py:439`) picks
   enemy host nodes purely by **category**:

   ```python
   candidates = [
       n for n, node in self._graph.nodes.items()
       if node.size in (NodeSize.ROOM, NodeSize.HALL)
       and not node.blocks and not node.plates and not node.has_flames
   ]
   ...
   self._graph.nodes[t].enemies.append(('chaser',))   # or ('forge_ogre',)
   ```

   `NodeSize.ROOM`/`HALL` is a topology label, **not** a size guarantee. The
   actual bounding box is decided much later by zone packing, which can legally
   produce a room as small as `w=2, h=2` (R-P4 in `kb/requirements.md`: "Minimum
   usable room dimensions: `w >= 2`, `h >= 2`"). So the graph cannot enforce a
   geometric `3x3` floor — it has no `w`/`h` to test.
   (The module-level `_assign_items` enemy block at `levelgraph.py:804-828` is
   **dead code** — `levelgraph.py:688` "formerly `_assign_items` — replaced by
   `LevelGraphBuilder`" — and is not part of the fix.)

2. **Layout time** — `_place_items_in_room` (`levellayout.py:1896-1906`) receives
   the `PlacedNode` (which *does* carry `.w`/`.h`, set at `levellayout.py:37-38`)
   but emits an enemy start for **any** in-room floor tile with no size check:

   ```python
   enemy_starts = []
   enemy_tiles: set = set()
   for enemy_info in node.enemies:
       far = [p for p in floor if p not in enemy_tiles
              and (not player_dist or player_dist.get(p, 0) >= MIN_ENEMY_DIST)]
       pool = far or [p for p in floor if p not in enemy_tiles]
       if pool:
           p = rng.choice(pool)
           enemy_tiles.add(p)
           enemy_starts.append((*p, enemy_info[0]))
   ```

   The caller loop in `build_level_dict` (`levellayout.py:2169-2179`) walks every
   placed node and concatenates results into `all_enemy_starts`
   (`levellayout.py:2152, 2233-2234`). At no point is `placed[name].w`/`.h`
   consulted for enemies.

**Consequence:** an enemy can spawn in a `2`-wide or `2`-tall (or L-shaped,
narrow-bbox) room. In such a room the player has no lateral tile to dodge into and
can be cornered with no escape — the BL-20 trap. Because the size floor can only
be evaluated once `w`/`h` are known, the **layout layer is the correct (and only
possible) place** to enforce it; this spec does not touch `add_enemies`.

## Resolution

Enforce the size floor at **layout time**, where `PlacedNode.w/.h` are available.

**N1 — size-floor gate.** An enemy is emitted into a node only if that node's
placed bounding box satisfies `placed.w >= 3 AND placed.h >= 3`. Equivalently:
in `build_level_dict` (`levellayout.py:2169-2179`) / `_place_items_in_room`
(`levellayout.py:1896-1906`), a node whose `PlacedNode` is sub-3x3 contributes
**no** enemy start at its own tiles. The corridor's bounding box is always far
larger than `3x3`, so the corridor passes this filter unconditionally and remains
eligible (it just normally carries no enemies — `add_enemies` never targets it).

**N2 — reassign, never drop ("place only").** An enemy whose home node is placed
sub-3x3 is **moved**, not deleted:

1. Build the set of **eligible host nodes** for this grid — placed nodes with
   `w >= 3 AND h >= 3` (preferring non-corridor `ROOM`/`HALL` hosts, consistent
   with the graph's intent that corridors are transition zones).
2. Reassign the orphaned enemy to one such eligible room, placing it with the
   **same** far-from-player tile rule already used in `_place_items_in_room`
   (`>= MIN_ENEMY_DIST`, falling back to any free in-room tile), so the relocated
   enemy obeys the existing spawn-distance behaviour.
3. If — and only if — **no** non-corridor eligible room exists in the grid (a
   degenerate seed where every room packs sub-3x3), the **corridor** is the
   guaranteed-available fallback host (it always passes the `3x3` filter). This is
   the literal meaning of "the corridor is large and remains eligible": it is the
   safety net that makes the no-drop guarantee total.

Because step 3 always succeeds, **no enemy is ever lost** — in particular the
single `forge_ogre` boss (placed first in `add_enemies`, `levelgraph.py:658-660`)
always survives, where a naive "skip and drop" would silently delete the boss
whenever its room happened to pack narrow. The total enemy count is preserved and
**no new enemies are created** — relocation only.

**Layer decision, stated explicitly.** Graph-time filtering in `add_enemies` is
**rejected**: the graph has only `NodeSize` categories, never the post-packing
`w`/`h`, so it cannot evaluate `w >= 3 AND h >= 3` (R-P4 lets a `ROOM` pack down
to `2x2`). The size floor is therefore a layout-time invariant, enforced once the
`placed` dict exists.

## Verification

**N3 — level-generator logic sweep (pytest, suite under `tests/`, run via
`poe test`).** Add a property test (Hypothesis, mirroring
`tests/test_placement_rules.py` style) that, across many seeds **×** every Act 2
feature set (`ALL_FEATURE_SETS` in `tests/conftest.py`:
`FS_OPEN, FS_LOCKED, FS_GATED, FS_WATER, FS_ALL`, plus `FS_FLAMES`/`FS_WATER_FLAMES`):

1. Generates the graph (`LevelGraph.generate(fs, random.Random(seed))`) and builds
   the level (`build_level_dict`).
2. For each grid room, reads `room['enemy_starts']` (the `(c, r, enemy_type)`
   tuples) and `room['tile_owner']` (tile → placed-node name).
3. For each enemy start, resolves its owning placed node via `tile_owner[(c, r)]`,
   reconstructs that owner's bounding box from the extent of the tiles it owns
   (`w = max_c - min_c + 1`, `h = max_r - min_r + 1`; for the rectangular
   `ROOM`/`HALL` hosts that carry enemies this equals the `PlacedNode` bbox), and
   **asserts `w >= 3 AND h >= 3`**.

The test fails today (enemies land in `2`-wide/`2`-tall rooms) and passes once the
size-floor gate + reassignment land. A complementary count check — total
`enemy_starts` across the level equals the graph's total `node.enemies` count
(no enemy dropped, the `forge_ogre` present whenever the feature set sets
`has_forge_ogre`) — guards the N2 "place only / never drop" guarantee.

## Done when:

- [ ] N1 — Enemy starts are emitted only for placed nodes with `w >= 3` and
      `h >= 3`; the size floor is enforced at layout time, `add_enemies`
      unchanged. —
- [ ] N2 — Enemies orphaned by a sub-3x3 home node are reassigned to an eligible
      room (corridor as guaranteed fallback); none dropped, `forge_ogre` always
      survives, no new enemies created. —
- [ ] N3 — Pytest sweep over many seeds × all Act 2 feature sets confirms no
      enemy start lands in a placed room with `w < 3` or `h < 3`; total enemy
      count is preserved. —
