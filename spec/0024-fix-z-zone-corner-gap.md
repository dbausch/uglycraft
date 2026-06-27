# Fix: Z/S Layout Leaves Unused Corner Zone

## Status

- [ ] Zone B extended to `MIN_R` when it holds exactly 1 room (z_h, s_h)
- [ ] Zone C extended to `MIN_R` when it holds exactly 1 room (z_v, s_v)

---

## Problem

Z-shape and S-shape corridor strategies leave one corner of the grid permanently
walled-off: a rectangular area adjacent to a zone that already exists, but not
covered by any zone definition. When a single room is placed in the neighbouring
zone, it fills that zone but the corner area above it remains solid wall.

The root cause is that Zone B (z_h / s_h) and Zone C (z_v / s_v) are defined to
start at the corridor arm row (`r_top` / `r_break`) rather than the top interior
row (`MIN_R`). The gap area above those zones is never offered to any room.

This is distinct from BL-02 (zones receiving 0 rooms): here all zones receive
rooms; the problem is that one zone is defined too small.

---

## ASCII diagram — z_h, before vs after

Concrete values: `arm_h=2, arm_w=2, r_top=5, r_bot=9, c_break=12`

```
Interior: cols 1–28, rows 1–14
Corridor: top arm  cols  1–13 rows 5–6
          connector cols 12–13 rows 5–10
          bottom arm cols 12–28 rows 9–10

     col: 0         1         2
           0123456789012345678901234567890
            |         |         |       |
BEFORE:
  row  1:  |.AAAAAAAAAAAAA..XXXXXXXXXXXXXX|  X = no zone (bug)
  row  2:  |.AAAAAAAAAAAAA..XXXXXXXXXXXXXX|
  row  3:  |.AAAAAAAAAAAAA..XXXXXXXXXXXXXX|
  row  4:  |..............WXXXXXXXXXXXXXX.|  W = wall
  row  5:  |.#############W.BBBBBBBBBBBBB.|  B = Zone B (current)
  row  6:  |.#############W.BBBBBBBBBBBBB.|
  row  7:  |.............##.BBBBBBBBBBBBB.|
  row  8:  |.CCCCCCCCCCC.##..............|
  row  9:  |.CCCCCCCCCCC.################.|
  row 10:  |.CCCCCCCCCCC.################.|
  row 11:  |.CCCCCCCCCCC.................| 
  row 12:  |.CCCCCCCCCCC.DDDDDDDDDDDDDDD.|
  row 13:  |.CCCCCCCCCCC.DDDDDDDDDDDDDDD.|
  row 14:  |.CCCCCCCCCCC.DDDDDDDDDDDDDDD.|

  Zone A: cols  1–13, rows  1–3  (w=13, h=3)
  Zone B: cols 15–28, rows  5–7  (w=14, h=3)  ← too high, misses rows 1–4
  Zone C: cols  1–10, rows  8–14 (w=10, h=7)
  Zone D: cols 12–28, rows 12–14 (w=17, h=3)
  Gap X:  cols 15–28, rows  1–4  (no zone)

AFTER (Zone B extended when 1 room assigned):
  row  1:  |.AAAAAAAAAAAAA..BBBBBBBBBBBBB.|  Zone B now fills rows 1–7
  row  2:  |.AAAAAAAAAAAAA..BBBBBBBBBBBBB.|
  row  3:  |.AAAAAAAAAAAAA..BBBBBBBBBBBBB.|
  row  4:  |..............W.BBBBBBBBBBBBB.|
  row  5:  |.#############W.BBBBBBBBBBBBB.|
  row  6:  |.#############W.BBBBBBBBBBBBB.|
  row  7:  |.............##.BBBBBBBBBBBBB.|
  ...unchanged below...

  Zone B: cols 15–28, rows  1–7  (w=14, h=7)
```

The single room in Zone B fills the full extended zone (rows 1–7).  
It still shares a boundary wall with the corridor at col 14, rows 5–7
(connector column c_break+arm_w−1=13 → wall at 14 → room at 15). ✓

---

## Why the condition is "exactly 1 room"

If Zone B holds 2+ rooms, `_pack_band_vertical` stacks them top-to-bottom. The
topmost room could occupy rows MIN_R..r_top−2, entirely above the corridor. It
would have no shared-boundary tile with the corridor, violating R-E1 and causing
`derive_walls` to raise.

With exactly 1 room the room spans the full extended zone (MIN_R to r_bot−2), so
it overlaps the connector row range (r_top..r_bot−2) and the shared boundary
exists at col c_break+arm_w, rows r_top..r_bot−2. ✓

---

## Affected variants and zone indices

All four Z/S variants have an analogous gap in a symmetric position. `valid` is
always `[A, B, C, D]` (all four zones always pass the `w≥3, h≥2` filter for the
random parameter ranges used):

| Variant | Gap location   | Zone to extend | Index in `valid` | Old row start | New row start | New height               |
|---------|----------------|----------------|-----------------|---------------|---------------|--------------------------|
| z_h     | top-right      | B              | 1               | `r_top`       | `MIN_R`       | `r_bot − MIN_R − 1`      |
| s_h     | top-left       | B              | 1               | `r_top`       | `MIN_R`       | `r_bot − MIN_R − 1`      |
| z_v     | top-right      | C              | 2               | `r_break`     | `MIN_R`       | `MAX_R − MIN_R + 1`      |
| s_v     | top-left       | C              | 2               | `r_break`     | `MIN_R`       | `MAX_R − MIN_R + 1`      |

---

## Implementation

In `_layout_z`, after computing `per_zone` and before calling packing functions,
add a post-distribution extension step:

```python
per_zone = [[] for _ in valid]
for i, name in enumerate(room_names):
    per_zone[i % len(valid)].append(name)

# Extend the gap zone when it receives exactly 1 room
if variant in ('z_h', 's_h'):
    if len(valid) > 1 and len(per_zone[1]) == 1:
        zc, _, zw, _, fn = valid[1]
        valid[1] = (zc, MIN_R, zw, r_bot - MIN_R - 1, fn)
else:  # z_v, s_v
    if len(valid) > 2 and len(per_zone[2]) == 1:
        zc, _, zw, _, fn = valid[2]
        valid[2] = (zc, MIN_R, zw, MAX_R - MIN_R + 1, fn)
```

No other files need changing.

---

## Verification

Manual — no automated test for visual layout:

- Run `poe run --level 11` through `--level 20` multiple times (levels randomise
  each run); look for Z/S-shape grids.
- Confirm the top-right (z_h) or top-left (s_h) corner area is now occupied by
  a room instead of solid wall.
- Confirm no regression: rooms still connect correctly to the corridor (no black
  screen / level-gen fallback to `full_border`).
- `poe test` must pass.

---

## Done when

- [ ] Z/S corner gap no longer appears when the relevant zone has 1 room
      (user confirmed).
- [ ] `poe test` passes.
