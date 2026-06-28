# Fix: Z/S Layout Corner Gap

## Status

- [x] Zone B extended to `MIN_R` in z_h and s_h (unconditional)
- [x] z_h/s_h Zone B uses `_pack_band` (horizontal) with no room cap — all rooms connect via bottom arm
- [x] z_v/s_v Zone B extended to outer edge, packed vertically — fills top corner gap
- [x] z_v/s_v Zone C starts at `r_break` (not `MIN_R`), packed vertically, no room cap
- [x] z_v/s_v Zone D extended to outer edge, packed vertically
- [x] `poe test` passes (1 pre-existing failure: BL-08, unrelated to this spec)

---

## Problem

Z-shape and S-shape corridor strategies leave one corner of the grid permanently
walled-off: a rectangular area that is never offered to any zone.

The root cause is that Zone B (z_h / s_h) and Zone C (z_v / s_v) are defined to
start at the corridor arm row (`r_top` / `r_break`) rather than the top interior
row (`MIN_R`).  The area above those zones is never covered by any room.

---

## ASCII diagram — z_h (complete, all zones)

Concrete values: `arm_h=2, arm_w=2, r_top=5, r_bot=9, c_break=12`  
Interior: cols 1–28, rows 1–14.  `#` = corridor.  First arm exits LEFT (cols 1–13);
connector vertical (cols 12–13, rows 5–10); second arm exits RIGHT (cols 12–28).

```
      col: 0         1         2
            0123456789012345678901234567890
row  0:  +------------------------------+
row  1:  |AAAAAAAAAAAAA.BBBBBBBBBBBBBB|   Zone B extended to MIN_R (fix)
row  2:  |AAAAAAAAAAAAA.BBBBBBBBBBBBBB|
row  3:  |AAAAAAAAAAAAA.BBBBBBBBBBBBBB|
row  4:  |..............BBBBBBBBBBBBBB|   wall row (A → first arm)
row  5:  |#############.BBBBBBBBBBBBBB|   first arm (exits LEFT)
row  6:  |#############.BBBBBBBBBBBBBB|
row  7:  |...........##.BBBBBBBBBBBBBB|   connector; last Zone B row
row  8:  |CCCCCCCCCC.##...............|   Zone C starts; wall row (B → second arm)
row  9:  |CCCCCCCCCC.#################|   second arm (exits RIGHT)
row 10:  |CCCCCCCCCC.#################|
row 11:  |CCCCCCCCCC..................|
row 12:  |CCCCCCCCCC.DDDDDDDDDDDDDDDDD|   Zone D starts
row 13:  |CCCCCCCCCC.DDDDDDDDDDDDDDDDD|
row 14:  |CCCCCCCCCC.DDDDDDDDDDDDDDDDD|
row 15:  +------------------------------+

Zone A: cols  1–13, rows  1– 3  _pack_band  (above first arm)
Zone B: cols 15–28, rows  1– 7  _pack_band  (extended to MIN_R; right of connector)
Zone C: cols  1–10, rows  8–14  _pack_band  (below first arm, left of connector)
Zone D: cols 12–28, rows 12–14  _pack_band  (below second arm)
```

All zones use `_pack_band` (horizontal packing, rooms span full zone height).
Connectivity:
- Zone A: bottom wall → first arm top (rows `r_top..r_top+arm_h-1`, full A col range). ✓
- Zone B: bottom wall → second arm top (rows `r_bot..r_bot+arm_h-1`, cols `c_break..MAX_C`
  which covers full Zone B col range). Multiple rooms — all connect. ✓
- Zone C: right wall (col `c_break-1`) → connector (col `c_break`,
  rows `r_top+arm_h+1..r_bot+arm_h-1`). Rooms span the full zone height so they always
  include connector rows. ✓
- Zone D: top wall → second arm bottom (rows `r_bot..r_bot+arm_h-1`, full D col range). ✓

No max_rooms cap needed on any zone.

---

## ASCII diagram — s_h (complete, all zones)

s_h is z_h reflected left-right.  First arm exits RIGHT (cols 12–28); second arm
exits LEFT (cols 1–13).

```
      col: 0         1         2
            0123456789012345678901234567890
row  0:  +------------------------------+
row  1:  |BBBBBBBBBB.AAAAAAAAAAAAAAAAA|   Zone B extended to MIN_R (fix)
row  2:  |BBBBBBBBBB.AAAAAAAAAAAAAAAAA|
row  3:  |BBBBBBBBBB.AAAAAAAAAAAAAAAAA|
row  4:  |BBBBBBBBBB..................|   wall row (A ends; only B remains)
row  5:  |BBBBBBBBBB.#################|   first arm (exits RIGHT)
row  6:  |BBBBBBBBBB.#################|
row  7:  |BBBBBBBBBB.##...............|   connector; last Zone B row
row  8:  |...........##.CCCCCCCCCCCCCC|   Zone C starts; wall row (B → second arm)
row  9:  |#############.CCCCCCCCCCCCCC|   second arm (exits LEFT)
row 10:  |#############.CCCCCCCCCCCCCC|
row 11:  |..............CCCCCCCCCCCCCC|
row 12:  |DDDDDDDDDDDDD.CCCCCCCCCCCCCC|   Zone D starts
row 13:  |DDDDDDDDDDDDD.CCCCCCCCCCCCCC|
row 14:  |DDDDDDDDDDDDD.CCCCCCCCCCCCCC|
row 15:  +------------------------------+

Zone A: cols 12–28, rows  1– 3  _pack_band  (above first arm)
Zone B: cols  1–10, rows  1– 7  _pack_band  (extended to MIN_R; left of connector)
Zone C: cols 15–28, rows  8–14  _pack_band  (below first arm, right of connector)
Zone D: cols  1–13, rows 12–14  _pack_band  (below second arm)
```

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

## Zone packing summary

All four zones in every variant use a single packing function throughout, with no room cap.

| Variant | Packing fn           | Zone B fix                          |
|---------|----------------------|-------------------------------------|
| z_h     | `_pack_band`         | extended to `MIN_R` (right of connector) |
| s_h     | `_pack_band`         | extended to `MIN_R` (left of connector)  |
| z_v     | `_pack_band_vertical`| extended to `MAX_C`; Zone C starts at `r_break`; Zone D extended to `MIN_C` |
| s_v     | `_pack_band_vertical`| extended to `MIN_C`; Zone C starts at `r_break`; Zone D extended to `MAX_C` |

---

## Implementation

### Zone tuple format

6 elements: `(col, row, w, h, fn, max_rooms)`.  `None` = unlimited.

### z_h zones (all four) — already implemented

```python
# A: above first arm
(MIN_C,           MIN_R,              c_break + arm_w - 1, r_top - 2,
 _pack_band, None),
# B: right of connector — extended to MIN_R
(c_break + arm_w + 1, MIN_R,          MAX_C - c_break - arm_w, r_bot - MIN_R - 1,
 _pack_band, None),
# C: below first arm, left of connector
(MIN_C,           r_top + arm_h + 1,  c_break - 2,          MAX_R - r_top - arm_h,
 _pack_band, None),
# D: below second arm
(c_break,         r_bot + arm_h + 1,  MAX_C - c_break + 1,  MAX_R - r_bot - arm_h,
 _pack_band, None),
```

### s_h zones (all four) — already implemented

```python
# A: above first arm
(c_break,         MIN_R,              MAX_C - c_break + 1,  r_top - 2,
 _pack_band, None),
# B: left of connector — extended to MIN_R
(MIN_C,           MIN_R,              c_break - 2,           r_bot - MIN_R - 1,
 _pack_band, None),
# C: below first arm, right of connector
(c_break + arm_w + 1, r_top + arm_h + 1, MAX_C - c_break - arm_w, MAX_R - r_top - arm_h,
 _pack_band, None),
# D: below second arm
(MIN_C,           r_bot + arm_h + 1,  c_break + arm_w - 1,  MAX_R - r_bot - arm_h,
 _pack_band, None),
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

- [x] Z/S corner gap no longer appears (user confirmed — addefc7, 94e5777, b115ed1, 9f12ba6).
- [x] Multiple rooms are placed in z_h/s_h Zone B when graph has enough rooms (user confirmed).
- [x] Multiple rooms are placed in z_v/s_v Zone B and Zone C when graph has enough rooms (user confirmed).
- [x] `poe test` passes (1 pre-existing failure: BL-08, unrelated to this spec).
