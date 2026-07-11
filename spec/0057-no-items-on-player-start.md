# 0057 — No items on the player start or entrance tile (BL-16)

## Status

- [ ] `build_level_dict` seeds `global_used` with `player_start` and the
      entrance tile for the start grid, before any item placement
- [ ] Property test (grid counts 1–6): no treasure, material, or key of the
      start room sits on `player_start` or `entrance`; plates and blocks
      locked too (already safe by construction)
- [ ] Pinned regression seed from the sweep: red before the fix, green after
- [ ] Detector sweep (validated against the pre-fix commit): 0 violations
      post-fix across many seeds × levels 11–20
- [ ] Goldens `act2_L11_walk` / `act2_L13_walk` verified byte-identical, or
      re-recorded once with a reviewed diff if their seeds are affected
- [ ] `poe test` exits 0
- [ ] kb updated (new invariant R-P8 in `kb/requirements.md`; item-placement
      section in `kb/architecture.md`); BL-16 closed in `kb/backlog.md`

## Problem

BL-16: treasures, materials, and keys can spawn on the `player_start` tile.
An item under the player at spawn is auto-collected on the first step or
simply looks wrong (the player sprite covers it).

`player_start` is the corridor tile directly inside the level entrance
(grid zero, specs 0053/0055, invariant R-T6). In `build_level_dict`
(`levellayout.py`) it is computed early, by `_pick_entrance` at ~line 2302 —
**before** any item is placed — but the shared exclusion set for item
placement, `global_used`, is initialised **empty** at ~line 2405. Nothing
ever adds `player_start` (or the entrance tile) to it.

### How an item reaches `player_start`

`_place_items_in_room(node, placed_node, walls, rng, player_pos,
global_used, spill_floor)` places a node's collectibles in priority order
(keys → planks → treasures → other materials) by walking a shuffled list of
the node's free floor tiles, then the corridor `spill_floor`, skipping tiles
already in `global_used` (`_next()`). `player_pos` is used **only** for the
enemy `MIN_ENEMY_DIST` distance filter — collectible placement ignores it
entirely. Two paths can therefore select `player_start`:

1. **The corridor's own items.** `player_start` is a corridor floor tile, so
   it is in the corridor node's shuffled `floor` list. The corridor node
   regularly carries collectibles: `start_next_grid` can place border keys
   (and treasures/materials) on a corridor via `_pick(list(self._reachable))`,
   and `_build_subgraph` copies the corridor node's own items into each
   per-grid subgraph (spec 0030).
2. **Spill overflow.** `spill_floor` is *all* free corridor tiles (shuffled),
   used as the overflow target whenever any room's floor is exhausted, and by
   the unplaced-node content spill (spec 0032 C7). Both spill call sites can
   land an item on `player_start`.

### What is already safe by construction (no change needed, lock it anyway)

- **Pressure plates and pushable blocks** never reach `player_start`:
  `_puzzle_candidates` (`levelgraph.py` ~line 522) excludes CORRIDOR nodes,
  and `_place_puzzle` confines the block to the puzzle room's own
  `floor_tiles` — never the corridor, which owns `player_start` (R-T6).
- **Flame far-tile treasures** are drawn from a flame room's `far_tiles` —
  room floor only, never the corridor.
- **The entrance tile itself** is a border-ring tile (col 0/29, row 0/15).
  Border tiles are never in any node's `floor_tiles` (R-G2), so no item can
  land there today. It is excluded anyway (see Design) as a zero-cost guard:
  BL-43 plans to make the entrance an openable passage, at which point a
  stray future placement path onto that tile would be a real bug.
- **Enemies** are out of scope for BL-16 (backlog wording covers items).
  They reserve no tile and already avoid the player via the
  `MIN_ENEMY_DIST` filter (`player_dist` is computed for the corridor since
  `player_pos ∈ floor_tiles`); only the degenerate all-tiles-near fallback
  pool could pick `player_start`. If that ever shows up in play it is a
  separate backlog item.

## Design

One change, in `build_level_dict` (`levellayout.py`), at the point where the
shared exclusion set is created (~line 2405, before push-puzzle placement
and both `_place_items_in_room` passes):

- **Seed `global_used` with `player_start` and `entrance_tile` when
  `is_start_grid` is true** (instead of starting empty). For non-start grids
  `global_used` stays empty as today.

That single seeding covers every collectible path, because all of them
consult the same set:

| Placement path | Guarded by |
|---|---|
| room-floor items (`_place_items_in_room`, `_next()` room pass) | `p not in used` |
| corridor spill (`_next()` spill pass, both call sites) | `p not in used` |
| flame far-tile treasures (`build_level_dict` far-tiles pass) | `t not in global_used` |
| plates/blocks | safe by construction (above); seeding adds nothing but costs nothing |

### Why gate on `is_start_grid`

In multi-grid levels `_build_super_grid` calls `build_level_dict` once per
grid with `is_start_grid=(i == 0)`. For non-start grids `_pick_entrance`
runs in scanning mode purely to derive the **enemy-distance reference
tile**; its result is never surfaced as an entrance or player position
(spec 0053). Excluding that tile from item placement would pointlessly
block a good tile in every non-start grid and shift item placement (and
hence golden traces) across far more levels than necessary. Only the start
grid's pair is real.

Single-grid levels call `build_level_dict` directly with the default
`is_start_grid=True`, so they are covered by the same condition.

### Manually built graphs (tests)

Manually built graphs have no `graph.entrance_side`; `_pick_entrance` falls
back to scanning mode but still returns a real `(entrance, player_start)`
pair that `build_level_dict` surfaces. The seeding applies identically — no
special case.

### RNG-stream / golden impact

No rng draw is added or removed: `_next()` consumes no randomness (it walks
the already-shuffled lists), and the enemy pools do not consult
`global_used`. Placement therefore shifts **only** in levels where an item
would previously have landed on `player_start` — for those seeds the item
silently takes the next tile in the shuffled order.

The spec-0044 golden traces (`act2_L11_walk`, `act2_L13_walk`) are expected
to stay byte-identical unless their specific seeds are affected. Verify;
if one shifts, re-record once (`UGLYCRAFT_REGOLD=1`) and review the diff —
the only acceptable difference is an item position moving off
`player_start`. The spec-0054 determinism test compares hashes across
`PYTHONHASHSEED` values within one code version, so it stays green
regardless.

### New invariant

Add to `kb/requirements.md` as **R-P8**: no treasure, material, key, plate,
or block may occupy the start grid's `player_start` tile or the `entrance`
tile. (Plates/blocks hold by construction via `_puzzle_candidates` +
R-T6; the test locks them so a future corridor-puzzle change cannot
silently regress.)

## Verification (design only — tests written after spec confirmation)

The project has a pytest suite (`poe test`).

1. **Property test** — extend `tests/test_entrance.py` (it already has the
   seed/grid-count build-with-retry helper and covers `player_start`):
   hypothesis over seeds with `grid_count` 1–6. Build the level, take the
   start room dict (`lv['rooms'][lv['start_room']]`) — item coordinates are
   per-grid, so only the start grid's lists may be compared against
   `player_start` — and assert that neither `lv['player_start']` nor
   `room['entrance']` appears among the `(c, r)` positions in the room's
   `treasures`, `materials`, `keys`, `pressure_plates`, or
   `pushable_blocks` lists (keys present only when non-empty).
2. **Pinned regression case** — the property test alone may go red only
   rarely (violations need an item to hit one specific corridor tile), so
   pin at least one deterministic `(seed, level)` violation found by the
   pre-fix sweep as a plain test — red before the fix, green after.
3. **Statistical sweep** (scratchpad, not in suite — per the
   statistical-sweeps practice): a detector over ~40 seeds × levels 11–20
   that flags any start-room item on `player_start`/`entrance`. Run it on
   the **pre-fix commit first** to validate the detector (it must report
   ≥ 1 violation there — this also yields the pinned seed), then post-fix:
   0 violations.
4. Golden check as described above; full suite via `poe test`.

## Done when:

- [ ] `global_used` is seeded with `player_start` and the entrance tile for
      the start grid before push-puzzle and item placement in
      `build_level_dict`; non-start grids unchanged
- [ ] Property test over grid counts 1–6 asserts no treasure, material, key,
      plate, or block on `player_start`/`entrance` in the start room; a
      pre-fix violating seed is pinned and was red before the fix
- [ ] Detector sweep validated against the pre-fix commit (≥ 1 violation
      found there), 0 violations post-fix across ~40 seeds × levels 11–20
- [ ] `act2_L11_walk` / `act2_L13_walk` byte-identical, or re-recorded once
      with the diff reviewed (only an item moving off `player_start`)
- [ ] `poe test` exits 0
- [ ] R-P8 added to `kb/requirements.md`; `kb/architecture.md` item-placement
      section updated; BL-16 closed in `kb/backlog.md`
