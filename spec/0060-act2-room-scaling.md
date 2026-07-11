# 0060 — Act 2 room scaling with grid count (BL-21 + BL-22 + BL-25)

## Status

- [ ] Red tests: enemy capacity/total (2 × G) extended to **all** ten
      feature sets; per-grid room-count bounds contract; strategy-trim
      contract for levels 11–13
- [ ] `room_count` rescaled per the table below (levels 11–20)
- [ ] Strategy lists trimmed for levels 11–13 (BL-22)
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

| Level | today | **new** |
|---|---|---|
| 11 | horizontal, vertical, double_t, t, z, l | **horizontal, vertical, t** |
| 12 | horizontal, vertical, double_t, t, z | **horizontal, vertical, t** |
| 13 | horizontal, vertical, off_centre, double_t, t, z | **horizontal, vertical, off_centre, t** |

Levels 14–20 keep their current lists. Room-count filtering
(`n_rooms ≥ _STRATEGY_MAX_ZONES`) already drops `t` (3 zones) on a
2-room level 11 draw, leaving the 2-zone spines — no new mechanism.
Between them `horizontal` (left+right) and `vertical` (top+bottom)
cover every entrance side, so the single-grid grid-zero pre-pick
(spec 0055) always finds a covering strategy.

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
3. **Strategy contract**: levels 11–13 contain none of `z`, `s`, `l`,
   `double_t`. Red today.
4. **Sweep**: `scratchpad/sweep_enemy_awards.py` over ≥ 120 levels —
   0 violations of any kind.
5. **Timing**: scratchpad script generating levels 11–20, printing per-
   level wall time; budget as above.
6. Goldens re-recorded once; full `poe test` green.

## Done when:

- [ ] All ten feature sets pass the capacity/total tests (enemy total
      exactly 2 × G, every host a candidate room) — red before the
      table lands
- [ ] Feature-set bounds and strategy contracts green
- [ ] Sweep reports 0 violations (TOTAL included) across ≥ 120 levels
- [ ] Level-20 generation ≤ 12 s, Act 2 total ≤ 45 s, measured
- [ ] Goldens/hashes re-recorded once with reviewed diffs; `poe test`
      exits 0
- [ ] `kb/architecture.md` timings/room notes updated; BL-21, BL-22,
      BL-25 closed
- [ ] Daniel confirms in play: level 11 reads as an introduction, late
      levels are populated (not full-border wastelands), loading wait
      acceptable
