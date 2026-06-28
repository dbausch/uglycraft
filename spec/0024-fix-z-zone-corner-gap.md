# Fix: Z/S Layout Corner Gap

## Status

- [x] Zone B extended to `MIN_R` in z_h and s_h (unconditional)
- [x] z_h/s_h Zone B uses `_pack_band` (horizontal) with no room cap — all rooms connect via bottom arm
- [x] z_v/s_v Zone B extended to outer edge, packed vertically — fills top corner gap
- [x] z_v/s_v Zone C starts at `r_break` (not `MIN_R`), packed vertically, no room cap
- [x] z_v/s_v Zone D extended to outer edge, packed vertically
- [ ] `poe test` passes

---

## Problem

Z-shape and S-shape corridor strategies leave one corner of the grid permanently
walled-off: a rectangular area that is never offered to any zone.

The root cause is that Zone B (z_h / s_h) and Zone C (z_v / s_v) are defined to
start at the corridor arm row (`r_top` / `r_break`) rather than the top interior
row (`MIN_R`).  The area above those zones is never covered by any room.

---

## ASCII diagram — z_h, before vs after

Concrete values: `arm_h=2, arm_w=2, r_top=5, r_bot=9, c_break=12`  
Interior: cols 1–28, rows 1–14.  `#` = corridor floor, `.` = room zone floor.

```
     col: 0         1         2
           0123456789012345678901234567890
            |         |         |       |

BEFORE:
  row  1:  |.AAAAAAAAAAAAA.XXXXXXXXXXXXXX|  X = no zone (gap — bug)
  row  2:  |.AAAAAAAAAAAAA.XXXXXXXXXXXXXX|
  row  3:  |.AAAAAAAAAAAAA.XXXXXXXXXXXXXX|
  row  4:  |                             |
  row  5:  |.#############.BBBBBBBBBBBBB.|
  row  6:  |.#############.BBBBBBBBBBBBB.|
  row  7:  |.............##BBBBBBBBBBBBB.|
  row  8:  |.CCCCCCCCCCC.##..............|
  row  9:  |.CCCCCCCCCCC.################|
  row 10:  |.CCCCCCCCCCC.################|
  row 11:  |.CCCCCCCCCCC.................|
  row 12:  |.CCCCCCCCCCC.DDDDDDDDDDDDDDD|
  row 13:  |.CCCCCCCCCCC.DDDDDDDDDDDDDDD|
  row 14:  |.CCCCCCCCCCC.DDDDDDDDDDDDDDD|

  Zone A: cols  1–13, rows  1–3   (w=13, h=3)
  Zone B: cols 15–28, rows  5–7   (w=14, h=3)  ← starts at r_top=5; gap X rows 1–4
  Zone C: cols  1–10, rows  8–14  (w=10, h=7)
  Zone D: cols 12–28, rows 12–14  (w=17, h=3)
  Gap X:  cols 15–28, rows  1–4   (never covered)

AFTER (Zone B always extended to MIN_R, horizontal packing):
  row  1:  |.AAAAAAAAAAAAA.B1B1B1.B2B2B2|  (2 example rooms in Zone B)
  row  2:  |.AAAAAAAAAAAAA.B1B1B1.B2B2B2|
  row  3:  |.AAAAAAAAAAAAA.B1B1B1.B2B2B2|
  row  4:  |               B1B1B1.B2B2B2|
  row  5:  |.#############.B1B1B1.B2B2B2|
  row  6:  |.#############.B1B1B1.B2B2B2|
  row  7:  |.............##B1B1B1.B2B2B2|
  ...rows 8–14 unchanged...

  Zone B: cols 15–28, rows 1–7   (w=14, h=7, unlimited rooms, _pack_band)
```

All Zone B rooms span rows 1–7 and connect to the bottom arm via the shared
boundary at row 8 (cols 15–28 ⊆ bottom arm cols).  Multiple rooms side-by-side
all connect — no max_rooms restriction needed.

---

## Why z_h/s_h Zone B needs no room cap

Zone B (extended) sits above the bottom arm (rows `r_bot..r_bot+arm_h-1`, cols
`c_break..MAX_C`).  The bottom arm spans ALL cols from `c_break` to `MAX_C`,
which includes the full width of Zone B.

With `_pack_band` (horizontal packing), each room spans the full zone height
(rows `MIN_R..r_bot-2`) and is placed at some column slice within
`c_break+arm_w+1..MAX_C`.  Every such room has floor tiles immediately above the
wall row at `r_bot-1`, which is immediately above the bottom arm floor at `r_bot`.
Shared boundary at `(c, r_bot-1)` for c in room columns. ✓

No room in Zone B can be disconnected from the corridor regardless of horizontal
position, so `max_rooms=None` (unlimited) is correct.

---

## ASCII diagram — z_v, before vs after

Concrete values: `arm_h=2, arm_w=2, c_left=6, c_right=18, r_break=7`  
Interior: cols 1–28, rows 1–14.  `#` = corridor.  First arm exits TOP (cols 6–7);
connector horizontal (cols 6–19, rows 7–8); second arm exits BOTTOM (cols 18–19).

```
      col: 0         1         2
            0123456789012345678901234567890

BEFORE (Zone C extended to MIN_R, max_rooms=1):
  row  1:  |AAAA.##.BBBBBBBBBBB.CCCCCCCC|  C: rows 1–14, max_rooms=1
  row  5:  |AAAA.##.BBBBBBBBBBB.CCCCCCCC|  (one tall room or disconnected)
  row  7:  |AAAA.##############.CCCCCCCC|
  row 10:  |.....DDDDDDDDDDD.##.CCCCCCCC|

AFTER (B extended right, C starts at r_break, D extended left):
  row  0:  +------------------------------+
  row  1:  |AAAA.##.BBBBBBBBBBBBBBBBBBBB|  Zone B extends to right border
  row  2:  |AAAA.##.BBBBBBBBBBBBBBBBBBBB|
  row  3:  |AAAA.##.BBBBBBBBBBBBBBBBBBBB|
  row  4:  |AAAA.##.BBBBBBBBBBBBBBBBBBBB|
  row  5:  |AAAA.##.BBBBBBBBBBBBBBBBBBBB|
  row  6:  |AAAA.##......................|  wall row (B → connector)
  row  7:  |AAAA.##############.CCCCCCCC|  Zone C starts at r_break
  row  8:  |AAAA.##############.CCCCCCCC|
  row  9:  |.................##.CCCCCCCC|  wall row (connector → D)
  row 10:  |DDDDDDDDDDDDDDDD.##.CCCCCCCC|  Zone D extends to left border
  row 11:  |DDDDDDDDDDDDDDDD.##.CCCCCCCC|
  row 12:  |DDDDDDDDDDDDDDDD.##.CCCCCCCC|
  row 13:  |DDDDDDDDDDDDDDDD.##.CCCCCCCC|
  row 14:  |DDDDDDDDDDDDDDDD.##.CCCCCCCC|
  row 15:  +------------------------------+

  Zone A: cols  1– 4, rows  1– 8   _pack_band_vertical  (unchanged)
  Zone B: cols  9–28, rows  1– 5   _pack_band_vertical  (extended right to MAX_C)
  Zone C: cols 21–28, rows  7–14   _pack_band_vertical  (starts at r_break; no cap)
  Zone D: cols  1–16, rows 10–14   _pack_band_vertical  (extended left to MIN_C)
```

Connectivity:
- Zone B: left wall (col 8) → first arm (col 7, rows 1–8 ⊇ 1–5).  All rooms
  span the full zone width and connect regardless of vertical position. ✓
- Zone C: left wall (col 20) → second arm (col 19, rows 7–14).  Zone C rows are
  exactly 7–14, so every room reaches the arm range. ✓ No cap needed.
- Zone D: top wall (row 9) → connector (row 8, cols 6–19 ∩ 1–16 = 6–16). ✓

---

## ASCII diagram — s_v

s_v is z_v reflected left-right.  First arm exits TOP at the right col (18–19);
second arm exits BOTTOM at the left col (6–7).

```
      col: 0         1         2
            0123456789012345678901234567890

  row  0:  +------------------------------+
  row  1:  |BBBBBBBBBBBBBBBB.##.AAAAAAAA|  Zone B extends to left border
  row  2:  |BBBBBBBBBBBBBBBB.##.AAAAAAAA|
  row  3:  |BBBBBBBBBBBBBBBB.##.AAAAAAAA|
  row  4:  |BBBBBBBBBBBBBBBB.##.AAAAAAAA|
  row  5:  |BBBBBBBBBBBBBBBB.##.AAAAAAAA|
  row  6:  |..................##.AAAAAAAA|  wall row (B → connector)
  row  7:  |CCCC.##############.AAAAAAAA|  Zone C starts at r_break
  row  8:  |CCCC.##############.AAAAAAAA|
  row  9:  |CCCC.##......................|  wall row (connector → D)
  row 10:  |CCCC.##.DDDDDDDDDDDDDDDDDDDD|  Zone D extends to right border
  row 11:  |CCCC.##.DDDDDDDDDDDDDDDDDDDD|
  row 12:  |CCCC.##.DDDDDDDDDDDDDDDDDDDD|
  row 13:  |CCCC.##.DDDDDDDDDDDDDDDDDDDD|
  row 14:  |CCCC.##.DDDDDDDDDDDDDDDDDDDD|
  row 15:  +------------------------------+

  Zone A: cols 21–28, rows  1– 8   _pack_band_vertical  (unchanged)
  Zone B: cols  1–16, rows  1– 5   _pack_band_vertical  (extended left to MIN_C)
  Zone C: cols  1– 4, rows  7–14   _pack_band_vertical  (starts at r_break; no cap)
  Zone D: cols  9–28, rows 10–14   _pack_band_vertical  (extended right to MAX_C)
```

Connectivity (s_v):
- Zone B: right wall (col 17) → first arm (col 18, rows 1–8 ⊇ 1–5). ✓
- Zone C: right wall (col 5) → second arm (col 6, rows 7–14). ✓
- Zone D: left wall (col 8) → second arm (col 7, rows 7–14 ⊇ 10–14);
  also top wall (row 9) → connector at cols 9–19. ✓

---

## Affected variants

| Variant | Gap location | Fix                                                        |
|---------|--------------|------------------------------------------------------------|
| z_h     | top-right    | Zone B extended to `MIN_R`, `_pack_band`, no cap          |
| s_h     | top-left     | Zone B extended to `MIN_R`, `_pack_band`, no cap          |
| z_v     | top-right    | Zone B extended to `MAX_C`, `_pack_band_vertical`, no cap; Zone C starts at `r_break`; Zone D extended to `MIN_C` |
| s_v     | top-left     | Zone B extended to `MIN_C`, `_pack_band_vertical`, no cap; Zone C starts at `r_break`; Zone D extended to `MAX_C` |

---

## Implementation

### Zone tuple format

6 elements: `(col, row, w, h, fn, max_rooms)`.  `None` = unlimited.

### z_h Zone B (index 1) — already done

```python
(c_break + arm_w + 1, MIN_R, MAX_C - c_break - arm_w, r_bot - MIN_R - 1,
 _pack_band, None)
```

### s_h Zone B (index 1) — already done

```python
(MIN_C, MIN_R, c_break - 2, r_bot - MIN_R - 1,
 _pack_band, None)
```

### z_v zones (indices 0–3)

```python
# A: left of first arm (vertical band) — unchanged
(MIN_C,              MIN_R,    c_left - 2,            r_break + arm_h - 1,
 _pack_band_vertical, None),
# B: above connector — extended right to MAX_C
(c_left + arm_w + 1, MIN_R,    MAX_C - c_left - arm_w, r_break - 2,
 _pack_band_vertical, None),
# C: right of second arm — starts at r_break (not MIN_R), no cap
(c_right + arm_w + 1, r_break, MAX_C - c_right - arm_w, MAX_R - r_break + 1,
 _pack_band_vertical, None),
# D: below connector — extended left to MIN_C
(MIN_C,              r_break + arm_h + 1, c_right - 2, MAX_R - r_break - arm_h,
 _pack_band_vertical, None),
```

### s_v zones (indices 0–3)

```python
# A: right of first arm (vertical band) — unchanged
(c_right + arm_w + 1, MIN_R,  MAX_C - c_right - arm_w, r_break + arm_h - 1,
 _pack_band_vertical, None),
# B: above connector — extended left to MIN_C
(MIN_C,              MIN_R,   c_right - 2,              r_break - 2,
 _pack_band_vertical, None),
# C: left of second arm — starts at r_break (not MIN_R), no cap
(MIN_C,              r_break, c_left - 2,               MAX_R - r_break + 1,
 _pack_band_vertical, None),
# D: below connector — extended right to MAX_C
(c_left + arm_w + 1, r_break + arm_h + 1, MAX_C - c_left - arm_w, MAX_R - r_break - arm_h,
 _pack_band_vertical, None),
```

---

## Verification

Manual — no automated test for visual layout:

- Run `poe run --level 11` through `--level 20` multiple times; look for Z/S grids.
- Confirm corner area is occupied by a room (not solid wall).
- Confirm multiple rooms fit in z_h/s_h Zone B.
- Confirm multiple rooms fit in z_v/s_v Zone B and Zone C.
- Confirm rooms connect correctly (no black screen / fallback to `full_border`).
- `poe test` must pass.

---

## Done when

- [ ] Z/S corner gap no longer appears (user confirmed).
- [ ] Multiple rooms are placed in z_h/s_h Zone B when graph has enough rooms.
- [ ] Multiple rooms are placed in z_v/s_v Zone B and Zone C when graph has enough rooms.
- [ ] `poe test` passes.
