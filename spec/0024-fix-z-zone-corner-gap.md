# Fix: Z/S Layout Corner Gap

## Status

- [ ] Zone B extended to `MIN_R` in z_h and s_h (unconditional)
- [ ] Zone C extended to `MIN_R` in z_v and s_v (unconditional)
- [ ] Extended zones carry `max_rooms=1`; distributor pops them before round-robin
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

AFTER (Zone B always extended to MIN_R, max_rooms=1):
  row  1:  |.AAAAAAAAAAAAA.BBBBBBBBBBBBB.|
  row  2:  |.AAAAAAAAAAAAA.BBBBBBBBBBBBB.|
  row  3:  |.AAAAAAAAAAAAA.BBBBBBBBBBBBB.|
  row  4:  |               BBBBBBBBBBBBB.|
  row  5:  |.#############.BBBBBBBBBBBBB.|
  row  6:  |.#############.BBBBBBBBBBBBB.|
  row  7:  |.............##BBBBBBBBBBBBB.|
  ...rows 8–14 unchanged...

  Zone B: cols 15–28, rows 1–7   (w=14, h=7, max_rooms=1)
```

The single room in Zone B spans rows 1–7 and is adjacent to the connector
(cols 12–13, rows 5–7).  Shared boundary wall at col 14, rows 5–7. ✓

---

## Why max_rooms=1 is required

If Zone B held 2 rooms stacked vertically (rows 1–7), the top room might occupy
rows 1–3 — entirely above the corridor.  It would have no floor tile adjacent to
any corridor tile, violating R-E1 / R-W3, and `derive_walls` would raise.

With 1 room the room spans the full zone height (rows 1–7), which includes the
connector-adjacent rows 5–7.  The shared boundary at col 14, rows 5–7 is
guaranteed regardless of corridor position.

---

## Affected variants

| Variant | Gap location | Zone to extend | Index | Old start | New start | New height           |
|---------|-------------|----------------|-------|-----------|-----------|----------------------|
| z_h     | top-right   | B              | 1     | `r_top`   | `MIN_R`   | `r_bot − MIN_R − 1`  |
| s_h     | top-left    | B              | 1     | `r_top`   | `MIN_R`   | `r_bot − MIN_R − 1`  |
| z_v     | top-right   | C              | 2     | `r_break` | `MIN_R`   | `MAX_R − MIN_R + 1`  |
| s_v     | top-left    | C              | 2     | `r_break` | `MIN_R`   | `MAX_R − MIN_R + 1`  |

---

## Implementation

### 1. Zone tuple format

Add a 6th element `max_rooms` to every zone tuple in `_layout_z`.  `None` means
unlimited; `1` means at most one room.  The existing packing functions (`_pack_band`,
`_pack_band_vertical`) receive only the first five elements and are unaffected.

```python
zones = [
    (col, row, w, h, fn, None),   # A — unlimited
    (col, row, w, h, fn, ???),    # B — None or 1 depending on variant
    (col, row, w, h, fn, ???),    # C — None or 1 depending on variant
    (col, row, w, h, fn, None),   # D — unlimited
]
```

### 2. Extended zone definitions per variant

**z_h** — Zone B (right of connector, index 1):

```python
# old:
(c_break + arm_w + 1, r_top,  MAX_C - c_break - arm_w, r_bot - r_top - 1,    _pack_band_vertical, None)
# new:
(c_break + arm_w + 1, MIN_R,  MAX_C - c_break - arm_w, r_bot - MIN_R - 1,    _pack_band_vertical, 1)
```

**s_h** — Zone B (left of connector, index 1):

```python
# old:
(MIN_C,                r_top,  c_break - 2,              r_bot - r_top - 1,    _pack_band_vertical, None)
# new:
(MIN_C,                MIN_R,  c_break - 2,              r_bot - MIN_R - 1,    _pack_band_vertical, 1)
```

**z_v** — Zone C (right of second arm, index 2):

```python
# old:
(c_right + arm_w + 1,  r_break, MAX_C - c_right - arm_w, MAX_R - r_break + 1, _pack_band_vertical, None)
# new:
(c_right + arm_w + 1,  MIN_R,   MAX_C - c_right - arm_w, MAX_R - MIN_R + 1,   _pack_band_vertical, 1)
```

**s_v** — Zone C (left of second arm, index 2):

```python
# old:
(MIN_C,                r_break, c_left - 2,               MAX_R - r_break + 1, _pack_band_vertical, None)
# new:
(MIN_C,                MIN_R,   c_left - 2,               MAX_R - MIN_R + 1,   _pack_band_vertical, 1)
```

### 3. Room distribution logic

Replace the flat round-robin in `_layout_z` with a two-pass approach:

```python
valid = [(c, r, w, h, fn, mx) for c, r, w, h, fn, mx in zones if w >= 3 and h >= 2]
rooms_copy = list(room_names)
rng.shuffle(rooms_copy)

per_zone = [[] for _ in valid]

# Pass 1: capped zones (max_rooms=1) get one room each, allocated first
for i, zone in enumerate(valid):
    if zone[5] == 1 and rooms_copy:
        per_zone[i] = [rooms_copy.pop()]

# Pass 2: remaining rooms go round-robin to uncapped zones
uncapped = [i for i, z in enumerate(valid) if z[5] != 1]
if uncapped:
    for k, name in enumerate(rooms_copy):
        per_zone[uncapped[k % len(uncapped)]].append(name)

for zone, rooms in zip(valid, per_zone):
    if rooms:
        col, row, w, h, fn, _ = zone
        fn(placed, rooms, col, row, w, h, rng, g)
```

The existing call sites that unpack zone tuples as 5-element sequences must be
updated to 6 elements wherever `_layout_z` builds or unpacks them.

---

## Verification

Manual — no automated test for visual layout:

- Run `poe run --level 11` through `--level 20` multiple times (levels randomise
  each run); look specifically for Z/S-shape grids.
- Confirm the corner area (top-right for z_h; top-left for s_h, z_v, s_v) is
  now occupied by a room instead of solid wall.
- Confirm rooms connect correctly (no black screen / fallback to `full_border`).
- `poe test` must pass.

---

## Done when

- [ ] Z/S corner gap no longer appears (user confirmed).
- [ ] `poe test` passes.
