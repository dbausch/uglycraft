# Spec 0034 — No completely empty rooms (BL-17)

## Status

- [ ] E1 — Every non-corridor node in a generated graph carries at least one
      content item (treasure / material / key / block / plate / enemy / flames).
      A guaranteed-content seeding pass runs at the end of `LevelGraph.generate`
      and drops one treasure into any node that the random distribution left bare
- [ ] E2 — Definition of "empty" pinned down: a placed non-corridor room with
      **no items AND no enemies**. The seeding pass uses exactly this predicate
- [ ] E3 — Property test: across many seeds × all Act 2 feature sets, every
      **placed** non-corridor room contains at least one item. Rooms dropped at
      layout (BL-23, R-P4) are excluded — the test inspects placed nodes only

## The defect

Content is distributed across graph nodes by `LevelGraphBuilder` inside
`LevelGraph.generate` (`levelgraph.py:327-441`). Three of the distribution
methods scatter a *fixed count* of items with **independent** `rng.choice` draws
over the node set, so a node that wins none of the draws receives nothing:

```python
# levelgraph.py:626-631
def add_treasures(self, count) -> None:
    all_nodes = list(self._graph.nodes.keys())
    item_nos  = list(range(1, 10))
    for _ in range(count):
        t = self._rng.choice(all_nodes)               # independent draw, all nodes
        self._graph.nodes[t].treasures.append((self._rng.choice(item_nos),))
```

```python
# levelgraph.py:633-642
def add_materials(self, mat_types, count) -> None:
    if not mat_types:
        return                                        # whole pass can be a no-op
    mats = [m for m in mat_types if m != 'planks']
    if not mats:
        return
    all_nodes = list(self._graph.nodes.keys())
    for _ in range(count):
        t = self._rng.choice(all_nodes)
        self._graph.nodes[t].materials.append((self._rng.choice(mats),))
```

```python
# levelgraph.py:644-665
def add_enemies(self, count) -> None:
    candidates = [n for n, node in self._graph.nodes.items()
                  if node.size in (NodeSize.ROOM, NodeSize.HALL)
                  and not node.blocks and not node.plates and not node.has_flames]
    ...
    for _ in range(count):
        t = self._rng.choice(candidates)
        ...                                           # enemy room also gets a treasure (663-665)
```

The counts are small relative to the room count: `treasure_count` defaults to
`(6, 10)`, `material_count` to `(4, 8)`, `enemy_count` to `(1, 3)` (the enemy
loop runs `max(1, randint(e_min, e_max))` times), while a level has
`room_count` nodes (`generate` line 354-355, feature-set `room_count`). Because
every draw is independent over *all* nodes — not a partition or round-robin —
the draws can collectively miss a node. With `~4-6` rooms and, say, 6 treasures,
the probability that a particular plain room wins **zero** of the 6 treasure
draws, **zero** material draws, and **zero** enemy draws is small but non-zero,
and it is realised in practice (BL-17: "observed during testing").

Some node kinds are immune because their content is placed **deterministically
per challenge** when the room is added, not via the random scatter:

- locked rooms get a key (`add_locked_room`),
- gated rooms get a plate **and** a block (`add_gated_room`),
- water rooms get two planks (`add_water_room`),
- flame rooms get `has_flames=True` (`add_flames`, `levelgraph.py:667-680`),
- any room that wins an enemy draw also gets a treasure (`add_enemies:663-665`).

So the empty-room risk is exactly the **plain `OPEN` / `BREAKABLE` rooms** that
hold no challenge prerequisite and happen to win none of the treasure / material
/ enemy draws. (The dead helper `_assign_items`, `levelgraph.py:688-846`, kept
only as the "formerly… — replaced by `LevelGraphBuilder`" reference, repeats the
identical `rng.choice(all_nodes)` pattern; the live path is the builder.)

Nothing downstream backfills the gap. At layout time `_place_items_in_room`
(`levellayout.py:1823-1908`) places exactly the items the node already holds —
`node.keys`, `node.materials`, `node.treasures`, `node.enemies` — so an empty
graph node becomes an empty placed room: floor space with nothing to collect and
no enemy. `build_level_dict` calls it once per placed node
(`levellayout.py:2169-2179`) and never adds default content.

## Resolution

Guarantee content **in the graph**, with a single guaranteed-content seeding
pass added as the final step of `LevelGraph.generate`, after all rooms,
challenges, and the random `add_treasures` / `add_materials` / `add_enemies`
draws have run. The pass walks every node and, for any **empty non-corridor**
node, appends exactly one treasure:

- **"Empty"** = `not (node.treasures or node.materials or node.keys or
  node.blocks or node.plates or node.enemies) and not node.has_flames`. This is
  the literal "no items AND no enemies" predicate from BL-17 (E2). `node.blocks`
  / `node.plates` / `node.has_flames` are interactive content and count as
  non-empty, so puzzle and flame rooms are never re-seeded.
- **"Non-corridor"** = `node.size != NodeSize.CORRIDOR`. The single CORRIDOR
  node (R-T1) is excluded; it is connective spine, not a content room. Closets
  (`NodeSize.CLOSET`) are real enterable rooms and **are** seeded — an empty
  closet is dead space too.
- The seeded item is **one treasure**, `(rng.choice(range(1, 10)),)` — the same
  universal reward the builder already uses as the fallback for enemy rooms
  (`add_enemies:663-665`) and flame rooms. A treasure fits any room and needs no
  prerequisite, unlike keys/plates/planks.

New builder method, e.g. `ensure_room_content(self)`, called from `generate`
immediately before `return b.build()` (`levelgraph.py:441`):

```python
def ensure_room_content(self):
    item_nos = list(range(1, 10))
    for node in self._graph.nodes.values():
        if node.size == NodeSize.CORRIDOR:
            continue
        if (node.treasures or node.materials or node.keys
                or node.blocks or node.plates or node.enemies
                or node.has_flames):
            continue
        node.treasures.append((self._rng.choice(item_nos),))
```

**Why graph-level seeding, not a post-layout backfill.** The fix hint offers
either a pre-distribution round-robin seed or a post-layout "drop a treasure into
any empty placed room" pass. Graph-level is preferred because:

1. The graph is the single source of truth that `validate_playability`, the
   layout, and the verification test all consult; content guarantees belong
   there next to the existing per-challenge and enemy-reward guarantees.
2. `_place_items_in_room` already owns tile allocation **and** corridor spill
   (spec 0029/0030): a graph-seeded treasure is automatically given a floor tile
   (or spilled to the corridor if the room is somehow full), so the seed cannot
   be dropped. A post-layout pass would have to re-implement free-tile finding
   and `global_used` bookkeeping.
3. A post-layout backfill mutates the level **after** `validate_push_puzzles` /
   `validate_playability` have run — the "mutate after validation" smell that
   spec 0030 (K2) deliberately removed from stitching. Seeding before `build`
   keeps all validation downstream of the final content.

Running the pass **after** the random draws (rather than a round-robin *before*)
means it only touches nodes that would otherwise be empty: it leaves the existing
random distribution — counts, positions, the enemy-reward coupling — untouched,
and adds the minimum needed. Empty rooms become rare-but-possible → impossible.

This operates on graph nodes, so it also covers nodes that are later **dropped**
at layout (BL-23): those simply never reach `placed` and are out of scope here —
seeding them is harmless and free.

## Verification

Add a pytest property test under `tests/` (run with `poe test`), mirroring the
existing Act 2 regression harness in `tests/test_act2_solvability.py`:

- Reuse its `_build(fs, seed)` helper (generate the graph + `build_level_dict`,
  retrying on `LayoutError`) and `_placed_names(level)` helper (the set of node
  names that own at least one tile, read from each room's `tile_owner`).
- Parametrise over **all** `ACT2_FEATURE_SETS` (`from levels import
  ACT2_FEATURE_SETS`) × many seeds (e.g. `range(20)`), so single-grid and
  multi-grid feature sets are all exercised.
- For each generated level, for every **placed non-corridor** node
  (`n in _placed_names(level)` with `graph.nodes[n].size != NodeSize.CORRIDOR`),
  assert the **graph node** carries at least one content item:

  ```python
  node = graph.nodes[n]
  assert (node.treasures or node.materials or node.keys
          or node.blocks or node.plates or node.enemies
          or node.has_flames), f"placed room {n!r} is completely empty"
  ```

  The assertion reads graph-node content (as the existing K1/W1 checks do at
  lines 57-67) rather than mapping item tiles back through `tile_owner`, because
  `_place_items_in_room` may **spill** a placed room's item onto a corridor tile
  — a tile-level check would mis-attribute the spilled item and report a false
  empty. Checking the graph node for nodes that survived to `placed` directly
  expresses the invariant the resolution establishes.

- **Excluded:** nodes dropped during layout (BL-23, R-P4) are never in
  `_placed_names`, so the test does not flag them. This is intentional — empty
  *placed* rooms are the BL-17 concern; silent node drops are BL-23.

A failing pre-fix run (some seed/feature-set combination yields a placed
non-corridor room with all-empty graph content) turns green once
`ensure_room_content` lands.

## Done when:

- [ ] E1 — `ensure_room_content` (or equivalent) runs at the end of
      `LevelGraph.generate` and seeds one treasure into every empty non-corridor
      node; the per-challenge and enemy-reward content paths are untouched. —
- [ ] E2 — "Empty" is defined as no items AND no enemies (the exact predicate
      above); corridor nodes are excluded, closets are included. —
- [ ] E3 — Property test over all Act 2 feature sets × many seeds asserts every
      placed non-corridor room has ≥1 item; passes under `poe test`; BL-23 drops
      excluded. —
