# 0064 — Act 1 entrance doors at fixed per-level positions (BL-42)

## Status

- [ ] Every Act 1 level dict (1–10) carries an `entrance` key — the border
      tile nearest the level's previous `player_start` (table below)
- [ ] `player_start` moved to the interior floor tile adjacent to the
      entrance (levels 6 and 7 keep their start; it is already adjacent)
- [ ] `_as_multiroom` forwards `entrance` into the single-room dict so the
      existing sprite render path (game.py:538) draws it in Act 1
- [ ] New tests red before the data change, green after; `poe test` exits 0
      with all affected goldens deliberately re-recorded
- [ ] Manual check: entrance sprite visible and player start correct on
      levels 1–10 (user acceptance)

## Problem

BL-42: hand-authored Act 1 levels (1–10) have no entrance door; Act 2 levels
have had one since spec 0022 (border sprite + adjacent player start,
anchored by construction since spec 0053). Act 1 should match the same
visual convention, as groundwork for BL-43 (entrance opens after all awards
are collected; the level ends by leaving through it).

Refinement from Daniel: the entrance is **not** free-standing — it is placed
on the border tile *nearest to the current player start*, and the player
start then *moves along* to sit directly inside the entrance, exactly like
Act 2's entrance/start adjacency.

## Placement rule

For each level, with old start `(c, r)` on the 30×16 grid (border ring:
col 0, col 29, row 0, row 15):

1. Candidate entrance tiles are all border-ring tiles whose single interior
   neighbour is a **floor tile** (not in `walls`).
2. The entrance is the candidate with minimum **Manhattan distance** to the
   old `player_start`. (No ties occur in the ten levels; a tie-break rule is
   therefore not specified.)
3. The new `player_start` is the entrance's interior neighbour.

Generic relationship (bottom-side entrance shown):

```
row 14:   .  P  .      P = new player_start — interior floor tile
row 15:   ▓  E  ▓      E = entrance — border tile, stays solid wall
                       (sprite only, same semantics as Act 2 / spec 0053)
```

The entrance tile remains a solid border wall; the door is a sprite, and it
never opens in this spec. Opening + level-exit semantics are BL-43.

## Per-level positions

Applying the rule to the ten levels of `levels.py`:

| Level | old `player_start` | `entrance` | new `player_start` | side | dist |
|---|---|---|---|---|---|
| 1  | (15, 8) | (15, 15) | (15, 14) | bottom | 7 |
| 2  | (15, 3) | (15, 0)  | (15, 1)  | top    | 3 |
| 3  | (15, 4) | (15, 0)  | (15, 1)  | top    | 4 |
| 4  | (15, 4) | (15, 0)  | (15, 1)  | top    | 4 |
| 5  | (15, 8) | (15, 15) | (15, 14) | bottom | 7 |
| 6  | (28, 3) | (29, 3)  | (28, 3) — unchanged | right | 1 |
| 7  | (14, 1) | (14, 0)  | (14, 1) — unchanged | top   | 1 |
| 8  | (27, 3) | (29, 3)  | (28, 3)  | right  | 2 |
| 9  | (15, 8) | (16, 15) | (16, 14) | bottom | 8 |
| 10 | (2, 7)  | (0, 7)   | (1, 7)   | left   | 2 |

All new starts were checked against each level's wall set: every one is a
floor tile, and no enemy start coincides with or is adjacent to a new
player start.

### Level 5 — gameplay note (cage)

The cage (cols 7–22, top wall row 3, bottom wall row 12 with a gap at cols
13–16) contained the old start (15, 8) **inside**; the nearest border tile
is below the bottom gap, so the new start is **outside** the cage, directly
under its opening:

```
col:      12 13 14 15 16 17
row 11:    .  .  .  .  .  .      (cage interior above)
row 12:    #  .  .  .  .  #      bottom cage wall, gap at cols 13–16
row 13:    .  .  .  .  .  .
row 14:    .  .  .  P  .  .      P = new player_start (15, 14)
row 15:    ▓  ▓  ▓  E  ▓  ▓      E = entrance (15, 15)
```

This flips the level's character: the player now starts outside the cage —
on the same side as the enemies at (27, 8) and (2, 12) — and enters it
through the gap, instead of starting protected inside. Accepted as a
consequence of the nearest-border rule; flag at spec review if the top side
(entrance (15, 0), dist 8) is preferred instead.

### Level 9 — nearest valid tile is off-axis

The centre divider (cols 14–15 walled at rows 1–5 and 10–14) blocks the
straight projections from the old start (15, 8): bottom (15, 15) and top
(15, 0) both have wall as their interior neighbour. The nearest *valid*
border tile is (16, 15) at Manhattan distance 8 (unique — (14, 15) and
(15, 0) at distance 8 are blocked, everything else is ≥ 9):

```
col:      13 14 15 16 17
row  9:    .  .  .  .  .      centre corridor (rows 6–9) open
row 10:    .  #  #  .  #      hwall(17, 27, 10) starts at col 17
row 11:    .  #  #  .  .
row 12:    .  #  #  .  .      cols 14–15: vwall rows 10–14
row 13:    .  #  #  .  .
row 14:    .  #  #  P  .      P = new player_start (16, 14)
row 15:    ▓  ▓  ▓  E  ▓      E = entrance (16, 15)
```

The start lands in the lower-right chamber, which is open at col 16 row 10
(gap between the divider and hwall(17, 27, 10)) and at col 28 — not a trap.

## Implementation

1. **`levels.py`** — each of the ten Act 1 dicts gains
   `'entrance': (col, row)` and its `player_start` updated per the table
   (levels 6 and 7 keep their start value).
2. **`world.py` `_as_multiroom`** — forward the key into the single room
   dict: `'entrance': data['entrance']` (all Act 1 dicts will have it).
   Without this the renderer never sees it — the wrapper currently copies
   only `walls` and `enemy_starts`.
3. **No render change** — game.py:538 already draws `sp['level_entrance']`
   for any current room whose data has `entrance`; Act 2 behaviour is
   untouched (its room dicts already carry the key, spec 0022/0053).

Item/award placement already avoids `player_start` (specs 0033/0057) by
reading the effective value, so the moved starts need no further handling.

## Tests (red first)

New `tests/test_act1_entrance.py`, over `levels.LEVELS`:

1. **Presence + pin**: every Act 1 dict has `entrance` equal to the exact
   tuple in the table above (data pin — red today, key absent).
2. **Invariants**: `entrance` lies on the border ring; Manhattan distance
   to `player_start` is exactly 1; `player_start` is interior (cols 1–28,
   rows 1–14) and not in `walls`; no enemy start equals `player_start`.
3. **Forwarding**: `_as_multiroom(LEVELS[i])['rooms'][None]['entrance']`
   equals the level's entrance (red today — key not forwarded).

### Golden-trace impact

Moving `player_start` shifts every Act 1 characterization trace, and the
entrance sprite + moved player change Act 1 screenshot goldens:

- All `tests/golden/act1_*.json` traces re-recorded with
  `UGLYCRAFT_REGOLD=1`. Scripted walks that navigate relative to the old
  start (e.g. `test_wall_break_and_place` walks from (15, 3) to the row-7
  wall — now starting at (15, 1)) get their hold counts adjusted so they
  still exercise the same mechanics (same bump/break/credit assertions).
- Screenshot goldens `shot_act1_field`, `shot_boss_field`, and any
  `shot_overlay_*` that render an Act 1 field behind the overlay are
  re-recorded (entrance sprite now visible, player elsewhere).
- `act2_*` traces and goldens must stay **byte-identical** — nothing in the
  Act 2 path changes.

## Manual verification

- `poe run --level N` for N = 1..10: entrance sprite on the border at the
  table position, player spawning directly inside it.
- Level 5: confirm the outside-the-cage start plays acceptably.
- Level 10 (boss): entrance at (0, 7) visible, start (1, 7), boss behaviour
  unchanged.

## Done when:

- [ ] All ten Act 1 dicts carry the table's `entrance` + `player_start`
- [ ] `_as_multiroom` forwards `entrance`; sprite renders in Act 1
- [ ] New tests red first, then green; `poe test` exits 0 with Act 1
      goldens deliberately re-recorded and Act 2 goldens byte-identical
- [ ] User confirms entrance sprites + moved starts on levels 1–10
      (explicit message; manual acceptance)
