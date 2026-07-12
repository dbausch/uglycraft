# 0064 — Act 1 entrance doors at fixed per-level positions (BL-42)

## Status

- [ ] Every Act 1 level dict (1–10) carries an `entrance` key — the border
      tile nearest the level's previous `player_start` (table below)
- [ ] `player_start` moved to the interior floor tile adjacent to the
      entrance (levels 6 and 7 keep their start; it is already adjacent)
- [ ] `_as_multiroom` forwards `entrance` into the single-room dict so the
      existing sprite render path (game.py:538) draws it in Act 1
- [ ] `--dump-level N [--seed S]` CLI option: headless ASCII export of any
      level 1–20 (new module `leveldump.py`, wired into `main.py`)
- [ ] New tests red before the change, green after; `poe test` exits 0
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

All positions below were machine-validated against each level's wall set:
every new start is an interior floor tile Manhattan-adjacent to its
entrance, and no enemy start coincides with a new player start.

### Level 5 — gameplay note (cage)

The old start (15, 8) was **inside** the cage; the nearest border tile is
below the cage's bottom-centre gap (cols 13–16, row 12), so the new start is
**outside** it, directly under the opening. This flips the level's
character: the player now starts on the same side as the enemies at (27, 8)
and (2, 12) and enters the cage through the gap, instead of starting
protected inside. Accepted as a consequence of the nearest-border rule;
flag at spec review if the top side (entrance (15, 0), dist 8) is preferred.

### Level 9 — nearest valid tile is off-axis

The centre divider (cols 14–15 walled at rows 1–5 and 10–14) blocks the
straight projections from the old start (15, 8): bottom (15, 15) and top
(15, 0) both have wall as their interior neighbour. The nearest *valid*
border tile is (16, 15) at Manhattan distance 8 — unique, since (14, 15)
and (15, 0) at distance 8 are blocked and everything else is ≥ 9. The start
lands in the lower-right chamber, which is open at col 16 row 10 (gap
between the divider and the row-10 wall) and at col 28 — not a trap.

## Full-grid diagrams

All ten levels at full 30×16, with the new entrance and start applied.
Generated from `levels.py` data (and machine-validated); these are also the
expected grid output of `--dump-level 1` … `--dump-level 10` (see below).

Legend: `#` wall (border + Act 1 stone) · `.` floor · `E` entrance ·
`P` player start · `e` enemy start · `C` crown.

### Level 1 — Open field

```
     000000000011111111112222222222
     012345678901234567890123456789
   0 ##############################
   1 #............................#
   2 #............................#
   3 #............................#
   4 #............................#
   5 #............................#
   6 #............................#
   7 #............................#
   8 #.e..........................#
   9 #............................#
  10 #............................#
  11 #............................#
  12 #............................#
  13 #............................#
  14 #..............P.............#
  15 ###############E##############
```

### Level 2 — Single horizontal wall

```
     000000000011111111112222222222
     012345678901234567890123456789
   0 ###############E##############
   1 #..............P.............#
   2 #............................#
   3 #............................#
   4 #............................#
   5 #............................#
   6 #............................#
   7 #.....##################.....#
   8 #.e..........................#
   9 #............................#
  10 #............................#
  11 #............................#
  12 #............................#
  13 #............................#
  14 #............................#
  15 ##############################
```

### Level 3 — H-shape

```
     000000000011111111112222222222
     012345678901234567890123456789
   0 ###############E##############
   1 #..............P.............#
   2 #............................#
   3 #......#..............#......#
   4 #......#..............#......#
   5 #......#..............#......#
   6 #......#..............#......#
   7 #......#######..#######......#
   8 #.e....#..............#......#
   9 #......#..............#......#
  10 #......#..............#......#
  11 #......#..............#......#
  12 #............................#
  13 #............................#
  14 #............................#
  15 ##############################
```

### Level 4 — Pillars + crossbar

```
     000000000011111111112222222222
     012345678901234567890123456789
   0 ###############E##############
   1 #..............P.............#
   2 #....#..................#....#
   3 #....#..................#....#
   4 #.e..#..................#....#
   5 #....#..................#....#
   6 #....#..................#....#
   7 #............................#
   8 #.############..############.#
   9 #....#..................#....#
  10 #....#..................#....#
  11 #....#..................#..e.#
  12 #....#..................#....#
  13 #....#..................#....#
  14 #............................#
  15 ##############################
```

### Level 5 — Cage

```
     000000000011111111112222222222
     012345678901234567890123456789
   0 ##############################
   1 #............................#
   2 #............................#
   3 #......################......#
   4 #......#..............#......#
   5 #......#..............#......#
   6 #......#..............#......#
   7 #......#..............#......#
   8 #......#..............#....e.#
   9 #......#..............#......#
  10 #......#..............#......#
  11 #......#..............#......#
  12 #.e....######....######......#
  13 #............................#
  14 #..............P.............#
  15 ###############E##############
```

### Level 6 — Grid of pillars

```
     000000000011111111112222222222
     012345678901234567890123456789
   0 ##############################
   1 #............................#
   2 #.#.#..#.#..######..#.#..#.#.#
   3 #.#.#..#.#..........#.#..#.#PE
   4 #.#.#..#.#..######..#.#..#.#.#
   5 #.#.#..#.#..........#.#..#.#.#
   6 #.#.#..#.#..######..#.#..#.#.#
   7 #............................#
   8 #.e..........................#
   9 #.#.#..#.#..######..#.#..#.#.#
  10 #.#.#..#.#..........#.#..#.#.#
  11 #.#.#..#.#..######..#.#..#.#.#
  12 #.#.#..#.#..........#.#..#.#.#
  13 #.#e#..#.#..######..#.#..#.#.#
  14 #............................#
  15 ##############################
```

### Level 7 — Three sealed vaults

```
     000000000011111111112222222222
     012345678901234567890123456789
   0 ##############E###############
   1 #.............P..............#
   2 #.#########........#########.#
   3 #.#.......#........#.......#.#
   4 #.#.......#........#.......#.#
   5 #.#.......#........#.......#.#
   6 #.#.......#........#.......#.#
   7 #.#########........#########.#
   8 #.e........................e.#
   9 #........############........#
  10 #........#..........#........#
  11 #........#..........#........#
  12 #........#..........#........#
  13 #........############........#
  14 #.............e..............#
  15 ##############################
```

### Level 8 — Slalom

```
     000000000011111111112222222222
     012345678901234567890123456789
   0 ##############################
   1 #.....#...........#..........#
   2 #.....#......e....#..........#
   3 #.....#...........#.........PE
   4 #.....#.....#.....#.....#....#
   5 #.....#.....#.....#.....#....#
   6 #.....#.....#.....#.....#....#
   7 #.....#.....#.....#.....#....#
   8 #.....#.....#.....#.....#....#
   9 #.....#.....#.....#.....#....#
  10 #.....#.....#.....#.....#....#
  11 #.....#.....#.....#.....#....#
  12 #.e.........#..........e#....#
  13 #...........#...........#....#
  14 #...........#...........#....#
  15 ##############################
```

### Level 9 — Four chambers

```
     000000000011111111112222222222
     012345678901234567890123456789
   0 ##############################
   1 #.............##.............#
   2 #.............##.............#
   3 #.............##.............#
   4 #.............##.............#
   5 #.###########.##.###########.#
   6 #............................#
   7 #............................#
   8 #.e........................e.#
   9 #............................#
  10 #.###########.##.###########.#
  11 #.............##.............#
  12 #.............##.............#
  13 #.e...........##.............#
  14 #.............##P............#
  15 ################E#############
```

### Level 10 — Boss: concentric rings

```
     000000000011111111112222222222
     012345678901234567890123456789
   0 ##############################
   1 #...#....................#...#
   2 #...#..#.############.#..#...#
   3 #...#....#..........#....#...#
   4 #...#....#.########.#....#...#
   5 #....#...#.#......#.#...#....#
   6 #........#.#.####.#.#........#
   7 EP.....#.#.#.#C.#.#.#.#....e.#
   8 #........#.#.####.#.#........#
   9 #........#.#......#.#........#
  10 #...###..#.########.#..###...#
  11 #...#....#..........#....#...#
  12 #...#....############....#...#
  13 #...#..#.....#.....#..#..#...#
  14 #...#.....#.....#........#...#
  15 ##############################
```

## `--dump-level` CLI — reusable ASCII level export

The diagrams above should never have to be hand-drawn again. A new module
**`leveldump.py`** (pygame-free — imports only `levels`, `cells`,
`constants`) provides:

```python
def dump_level(level_num, seed=None) -> str
```

and `main.py` gains:

```
--dump-level N     print an ASCII rendering of level N (1–20) and exit
--seed S           pin the Act 2 base seed (only meaningful with --dump-level)
```

The dump path runs before any window is created (headless; usable over SSH
and in tests).

### Behaviour

- **Act 1 (1–10)**: normalise via `world._as_multiroom` and render the
  single room — output matches the diagrams above (one header line per
  room is prepended, see format).
- **Act 2 (11–20)**: generate the level via `levels.get_level` — with
  `--seed S` pinned through `levels.set_game_seed(S)` first, otherwise the
  process's fresh random seed — and render **every room** of the level
  dict: start room first, remaining rooms in sorted key order. Each room
  is preceded by a header line naming its key and its `exits` mapping.
  With a fixed seed the output is deterministic (spec 0054).
- Grid format per room: the two column-ruler lines, then 16 rows, each
  `'  %2d '` row number + 30 symbol characters — exactly the diagram
  format above.

### Symbol table

One character per cell; markers over items over fixtures over barriers
over terrain (later wins the cell listed first here):

| Symbol | Meaning | Source |
|---|---|---|
| `.` | floor | terrain |
| `~` | water (unbridged) | terrain |
| `=` | bridge over water | fixture |
| `#` | border wall **and** stone wall | barrier `border` / `stone` |
| `R` | reinforced wall (indestructible) | barrier `reinforced` |
| `w` | wooden wall (breakable) | barrier `wooden` |
| `D` | locked door (colour not encoded) | barrier `door` |
| `G` | gate | barrier `gate` |
| `X` | exit gap on the border (inter-grid staircase) | `exits` keys |
| `_` | pressure plate | fixture `plate` |
| `!` | flame nozzle | fixture `flame_nozzle` |
| `*` | treasure | item |
| `m` | material | item |
| `k` | key (colour not encoded) | item |
| `O` | pushable block | occupant |
| `e` | enemy start (chaser) | occupant |
| `p` | patrol enemy start | occupant |
| `F` | forge ogre start | occupant |
| `C` | crown | `crown_pos` |
| `E` | level entrance | `entrance` |
| `P` | player start (start room only) | `player_start` |

`border` and `stone` share `#` deliberately: stone is the default wall and
Act 1 diagrams stay maximally readable; the rarer Act 2 kinds get their own
letters. Colours/channels (doors, keys, gates, plates) are not encoded —
the dump is a geometry tool, not a full state dump.

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
4. **`leveldump.py`** — `dump_level` as specified; **`main.py`** —
   `--dump-level` / `--seed` arguments, print-and-exit before pygame
   window setup.

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

New `tests/test_leveldump.py`:

4. **Act 1 shape**: for levels 1–10, `dump_level(n)` renders one room —
   grid lines are 16 rows × 30 symbols; exactly one `E` and one `P`; the
   border ring is `#` except at `E`.
5. **Act 1 pin**: `dump_level(2)`'s grid equals the Level 2 diagram in
   this spec verbatim (rulers + rows).
6. **Act 2**: with a pinned seed, `dump_level(13, seed=…)` returns one
   grid per room in the level dict, start room first with exactly one `E`
   and one `P`; calling twice with the same seed gives identical output.

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
  Act 2 generation or runtime path changes (`--dump-level` only reads).

## Manual verification

- `poe run --level N` for N = 1..10: entrance sprite on the border at the
  table position, player spawning directly inside it.
- Level 5: confirm the outside-the-cage start plays acceptably.
- Level 10 (boss): entrance at (0, 7) visible, start (1, 7), boss behaviour
  unchanged.
- `.venv/bin/python main.py --dump-level 5` reproduces the Level 5 diagram;
  `--dump-level 13 --seed 777` prints all rooms of a generated level 13.

## Done when:

- [ ] All ten Act 1 dicts carry the table's `entrance` + `player_start`
- [ ] `_as_multiroom` forwards `entrance`; sprite renders in Act 1
- [ ] `--dump-level N [--seed S]` prints the ASCII export for any level
      1–20 and exits without opening a window
- [ ] New tests red first, then green; `poe test` exits 0 with Act 1
      goldens deliberately re-recorded and Act 2 goldens byte-identical
- [ ] User confirms entrance sprites + moved starts on levels 1–10
      (explicit message; manual acceptance)
