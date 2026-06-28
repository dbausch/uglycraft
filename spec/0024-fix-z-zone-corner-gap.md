# Fix: Z/S Layout Corner Gap

## Status

- [x] Zone B extended to `MIN_R` in z_h and s_h (unconditional)
- [x] Zone C extended to `MIN_R` in z_v and s_v (unconditional)
- [x] z_h/s_h Zone B uses `_pack_band` (horizontal) with no room cap — all rooms connect via bottom arm
- [ ] z_v/s_v Zone C keeps `max_rooms=1` — only one room can reach the second arm's side wall
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

## Why z_v/s_v Zone C keeps max_rooms=1

Zone C (z_v / s_v) sits to the right / left of the second arm.  The second arm
spans only rows `r_break..MAX_R`.  Zone C is extended from `MIN_R` to `MAX_R`.

With vertical packing, a second room stacked above the first might occupy rows
`MIN_R..r_break-1` — entirely above the second arm's row range.  Its only
possible corridor adjacency is the side wall at `c_right+arm_w` (or `c_left-1`
for s_v), but that wall is only corridor-adjacent at rows `r_break..MAX_R`.
A room ending before `r_break` has no shared boundary → disconnected.

One room spanning the full zone height (`MIN_R..MAX_R`) always reaches the
arm rows and connects. ✓

---

## Affected variants

| Variant | Gap location | Zone to extend | Index | Packing fn          | max_rooms |
|---------|-------------|----------------|-------|---------------------|-----------|
| z_h     | top-right   | B (index 1)    |       | `_pack_band`        | `None`    |
| s_h     | top-left    | B (index 1)    |       | `_pack_band`        | `None`    |
| z_v     | top-right   | C (index 2)    |       | `_pack_band_vertical` | `1`     |
| s_v     | top-left    | C (index 2)    |       | `_pack_band_vertical` | `1`     |

---

## Implementation

### Zone tuple format

6 elements: `(col, row, w, h, fn, max_rooms)`.  `None` = unlimited; `1` = at
most one room.

### z_h Zone B (index 1)

```python
# was: _pack_band_vertical, 1
(c_break + arm_w + 1, MIN_R, MAX_C - c_break - arm_w, r_bot - MIN_R - 1,
 _pack_band, None)
```

### s_h Zone B (index 1)

```python
# was: _pack_band_vertical, 1
(MIN_C, MIN_R, c_break - 2, r_bot - MIN_R - 1,
 _pack_band, None)
```

### z_v Zone C (index 2) — unchanged

```python
(c_right + arm_w + 1, MIN_R, MAX_C - c_right - arm_w, MAX_R - MIN_R + 1,
 _pack_band_vertical, 1)
```

### s_v Zone C (index 2) — unchanged

```python
(MIN_C, MIN_R, c_left - 2, MAX_R - MIN_R + 1,
 _pack_band_vertical, 1)
```

### Room distribution in `_layout_z`

Two-pass: cap zones (`max_rooms=1`) get one room each first; remaining rooms
go round-robin to uncapped zones.

---

## Verification

Manual — no automated test for visual layout:

- Run `poe run --level 11` through `--level 20` multiple times; look for Z/S grids.
- Confirm corner area is occupied by a room (not solid wall).
- Confirm multiple rooms fit in Zone B for z_h/s_h grids.
- Confirm rooms connect correctly (no black screen / fallback to `full_border`).
- `poe test` must pass.

---

## Done when

- [ ] Z/S corner gap no longer appears (user confirmed).
- [ ] Multiple rooms are placed in z_h/s_h Zone B when graph has enough rooms.
- [ ] `poe test` passes.
