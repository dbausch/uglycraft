# 0060 — Act 2 room scaling with grid count (BL-21 + BL-22 + BL-25)

## Status

- [ ] Red tests: enemy capacity/total (2 × G) extended to **all** ten
      feature sets; per-grid room-count bounds contract; strategy-trim
      contract for levels 11–13; coverable-side-set test (no structural
      full_border fallback on trimmed levels)
- [ ] `room_count` rescaled per the table below (levels 11–20)
- [ ] Strategy lists trimmed for levels 11–13 (BL-22)
- [ ] Spanning tree + entrance draw constrained to strategy-coverable
      side sets (`_COVERS_*` moved to `levelgraph.py`)
- [ ] Detector sweep (`scratchpad/sweep_enemy_awards.py`): **0** violations
      including TOTAL across ≥ 120 levels
- [ ] Generation time measured for levels 11–20; level 20 within budget
      (see "Performance"), loading screen still acceptable
- [ ] Act 2 goldens + canonical hashes re-recorded once, diffs reviewed;
      `poe test` exits 0
- [ ] KB updated (`kb/architecture.md` lazy-generation timings, room-count
      note); BL-21, BL-22, BL-25 closed in `kb/backlog.md`
- [ ] User play-test confirmation: early levels feel simpler, late levels
      feel populated, level-load wait acceptable

## Problem

Three backlog items and one hard constraint meet here:

- **BL-21**: level 11 has too many rooms for an introduction level
  (currently 6–8 on a single grid).
- **BL-22**: levels 11–13 draw complex corridor layouts (`z`/`s`, `l`,
  `double_t`) that make the early Act 2 levels harder to read than
  intended.
- **BL-25**: `room_count` barely grows with `grid_count` (9–12 rooms
  spread over up to 10 grids ⇒ ~1 room per grid), so late Act 2 levels
  degenerate into near-empty border-frame grids.
- **Spec 0058 capacity**: the enemy distributor must place exactly
  `2 × G` enemies, each in a candidate room with a ≥ 3×3 free floor
  square (R-P9). With today's room counts, levels 17–20 run out of
  capacity: the post-0058 sweep found 12 TOTAL violations in 120 levels
  (worst: level 19 with **1** enemy instead of 18). Room scaling is what
  makes the 0058 economy actually hold on late levels.

## Design

### Room counts (the deliverable table)

`room_count` in `levels.py` `_act2_feature_sets()` becomes a per-grid
ramp: ~2–4 rooms per grid on early levels rising to ~4–6 per grid at
level 20 (BL-25's ~40–60 total). `generate()` splits
`room_count // grid_count` rooms per grid, remainder to the first grids
— unchanged mechanics, new numbers:

| Level | Grids | room_count today | **new room_count** | per grid |
|---|---|---|---|---|
| 11 | 1  | (6, 8)  | **(2, 4)**   | 2–4 |
| 12 | 2  | (6, 8)  | **(5, 8)**   | 2.5–4 |
| 13 | 3  | (8, 10) | **(8, 12)**  | 2.7–4 |
| 14 | 4  | (8, 10) | **(11, 17)** | 2.8–4.3 |
| 15 | 5  | (8, 10) | **(15, 22)** | 3–4.4 |
| 16 | 6  | (8, 10) | **(19, 28)** | 3.2–4.7 |
| 17 | 7  | (9, 12) | **(24, 34)** | 3.4–4.9 |
| 18 | 8  | (9, 12) | **(29, 41)** | 3.6–5.1 |
| 19 | 9  | (9, 12) | **(34, 50)** | 3.8–5.6 |
| 20 | 10 | (9, 12) | **(40, 60)** | 4–6 |

- Level 11 shrinks (BL-21): an introduction level with 2–4 generous
  rooms on one grid.
- The `max(draw, len(required))` guard in `generate()` keeps every
  distinct edge type + the deterministic water rooms feasible on every
  level (level 20: ~4 distinct types + 3 water ⇒ 7 ≤ 40).
- Zone feasibility: at most ~6 rooms per grid; a 2-zone strategy alone
  packs up to ~9 rooms per zone (`n_max = (band_w + 1) // 3`, R-P6), so
  no strategy is capacity-stressed.
- Enemy capacity: level 20 worst case ≈ 40 rooms − 5 flame − ~25%
  gated-puzzle exclusions ⇒ ~25 candidates × (s − 2 ≥ 1) ≥ 20 with wide
  margin; the red tests and the sweep verify this for every level, not
  by estimate.

### Strategy trim, levels 11–13 (BL-22)

Full `layout_strategies` table for all Act 2 levels — levels 14–20 are
unchanged and listed for completeness:

| Level | today | **new** |
|---|---|---|
| 11 | horizontal, vertical, double_t, t, z, l | **horizontal, vertical** |
| 12 | horizontal, vertical, double_t, t, z | **horizontal, vertical** |
| 13 | horizontal, vertical, off_centre, double_t, t, z | **horizontal, vertical, l** |
| 14 | horizontal, vertical, off_centre, double_t, t, z | horizontal, vertical, off_centre, double_t, t, z, **+ l** |
| 15 | horizontal, vertical, off_centre, double_t, t, z | horizontal, vertical, off_centre, double_t, t, z, **+ l** |
| 16 | horizontal, vertical, off_centre, double_t, t, z | horizontal, vertical, off_centre, double_t, t, z, **+ l** |
| 17 | horizontal, vertical, off_centre, double_t, t, z | horizontal, vertical, off_centre, double_t, t, z, **+ l** |
| 18 | horizontal, vertical, off_centre, double_t, t, z | horizontal, vertical, off_centre, double_t, t, z, **+ l** |
| 19 | horizontal, vertical, off_centre, double_t, t, z | horizontal, vertical, off_centre, double_t, t, z, **+ l** |
| 20 | horizontal, vertical, off_centre, double_t, t, z | horizontal, vertical, off_centre, double_t, t, z, **+ l** |

Levels 11–12 keep only the two plain spines; level 13 introduces the
corner (`l`), and `l` joins every later level's pool (review,
2026-07-11 — replaces the earlier `t`-at-13 trim).

### Exit sides constrained by the strategy list (review, 2026-07-11)

Today the pipeline runs topology-first: `_spanning_tree` fixes every
BORDER `exit_side` (and grid zero's pseudo-exit fixes the entrance side)
knowing nothing about layouts; each grid then picks a covering strategy,
falling back to `full_border` when the level's list covers no superset
of its required sides. With the trimmed lists above, that fallback would
fire on every mixed-axis draw (e.g. entrance left + exit bottom on level
12) and render frame grids. Daniel's review inverts the dependency:
**the possible exit sides are dictated by the strategies the level may
use.**

- The per-strategy side-coverage table (today's `_COVERS_*` data in
  `levellayout.py`) moves to `levelgraph.py` — pure data, and
  `levellayout` already imports `levelgraph`, so no cycle;
  `levellayout` re-imports it from there.
- `generate()` derives from `layout_strategies` the family of
  **coverable side sets** and threads a side filter into both draws:
  - *grid zero's pseudo-exit* — the entrance side must leave the start
    grid's (eventual) side set coverable;
  - *spanning-tree growth* — an edge attaching a child on side X of
    parent P is admissible only if P's side set ∪ {X} stays coverable
    and the child's starting set {opposite(X)} is coverable.
  Filtering iterates ordered side lists (process determinism, spec
  0054). A straight chain is always admissible whenever any spine is
  listed, so constrained growth cannot dead-end short of `grid_count`.
- **The coverage pool is anchor-aware.** R-T5 filters arm strategies
  (`z`/`s`/`l`) out on anchored grids — every non-start grid continues
  its parent's corridor band, so only the **start grid** (built first,
  unanchored) can lay out an `l`. `coverable_sides` therefore takes the
  grid's anchor status: for non-start grids the pool drops `z`/`s`/`l`
  before classification. Without this, level 13 child grids drawn with
  perpendicular sides would pass the graph check yet still fall to
  `full_border` at layout — the exact mismatch this spec abolishes.
- Geometric consequence, intended: levels 11–12 grids form a **straight
  line** along the entrance axis; level 13 may **turn once, at the
  start grid** (entrance and exit perpendicular via `l`), children
  continuing straight; richer lists (14–20, `double_t` spine+stems in
  the anchored pool) are barely constrained in practice.
- `full_border` stays as the layout-time last resort (R-T5) for
  anchor-honouring failures — but side-mismatch fallbacks become
  structurally absent: a test asserts that on levels 11–13 every grid's
  required side set is coverable by a listed strategy.
- Single-grid level 11 is unaffected in distribution: its only required
  side is the entrance, and the two spines together cover all four
  sides, so the BL-41 uniform entrance draw is preserved.

### Performance

Generation cost grows with room count (per-room item BFS, per-gated-room
Sokoban solve). Today level 20 generates in ~3.6 s (12 rooms); at 40–60
rooms expect a multiple of that. Budget: **level 20 ≤ 12 s, whole Act 2
(levels 11–20 sequentially) ≤ 45 s** on this machine, measured by a
scratchpad timing script before/after. Generation is lazy per level
behind the loading screen (spec 0028), so only the per-level number is
user-visible. If the budget is blown, tuning (e.g. lowering the upper
bounds of the table) happens inside this spec, not silently later.

### Interactions

- **Spec 0058**: unchanged in design; its sweep gate (0 violations,
  TOTAL included) becomes reachable. The 0058 checklist item "capacity
  never limits real feature sets" is enforced by tests after this spec.
- **BL-17** (empty rooms, P3): more rooms ⇒ more rooms without items;
  explicitly out of scope here, stays in the backlog.
- **Goldens/hashes**: room-count draws shift every Act 2 stream again —
  re-record `act2_L11_walk` / `act2_L13_walk` once, review diffs; the
  spec-0054 cross-process determinism guard must stay green.

## Verification (tests written red-first after spec confirmation)

1. **Capacity/total for all sets** (extends `tests/test_enemy_room_size.py`):
   the `_SWEEP` parametrization grows from feature sets 0–5 to **0–9**
   (grid counts 7–10 with 1 seed each to bound runtime). Red today for
   levels 17–20 (TOTAL < 2 × G on known seeds).
2. **Feature-set bounds contract**: for every Act 2 set,
   `2 ≤ room_min / G` and `room_max / G ≤ 6`, `room_min ≥` the number of
   required rooms (distinct edge types + water count). Red today
   (levels 14–20 sit near 1 room per grid).
3. **Strategy contract**: exact lists — levels 11 and 12 are
   `['horizontal', 'vertical']`, level 13 is
   `['horizontal', 'vertical', 'l']`, levels 14–20 gain `l` and are
   otherwise unchanged. Red today.
4. **Coverable side sets**: for generated graphs of every Act 2 level,
   each grid's required side set (BORDER faces + entrance on the start
   grid) is coverable by a listed strategy **under that grid's anchor
   status** (non-start grids: pool minus `z`/`s`/`l`) — i.e. no grid is
   forced into `full_border` by side mismatch. Red today on trimmed
   levels (mixed-axis draws exist). A companion assertion checks
   levels 11–12 grids are collinear (the chain consequence).
5. **Sweep**: `scratchpad/sweep_enemy_awards.py` over ≥ 120 levels —
   0 violations of any kind.
6. **Timing**: scratchpad script generating levels 11–20, printing per-
   level wall time; budget as above.
7. Goldens re-recorded once; full `poe test` green.

## Done when:

- [ ] All ten feature sets pass the capacity/total tests (enemy total
      exactly 2 × G, every host a candidate room) — red before the
      table lands
- [ ] Feature-set bounds and strategy contracts green
- [ ] Coverable-side-set test green: no grid forced into full_border by
      side mismatch on any level; levels 11–12 grids collinear
- [ ] Sweep reports 0 violations (TOTAL included) across ≥ 120 levels
- [ ] Level-20 generation ≤ 12 s, Act 2 total ≤ 45 s, measured
- [ ] Goldens/hashes re-recorded once with reviewed diffs; `poe test`
      exits 0
- [ ] `kb/architecture.md` timings/room notes updated; BL-21, BL-22,
      BL-25 closed
- [ ] Daniel confirms in play: level 11 reads as an introduction, late
      levels are populated (not full-border wastelands), loading wait
      acceptable
