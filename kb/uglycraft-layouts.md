# UGLYCRAFT Layout Strategies — Reference

## Grid and diagram notation

Full grid: 30 cols (0–29) × 16 rows (0–15).  Interior: cols 1–28, rows 1–14.

```
  #   solid wall — outer border, 1-tile gap between corridor and zone, unfilled area
  A B C …   room zone tile — rooms are packed here
  (space)   corridor floor tile
```

Row numbers run 0–15 down the left margin.  Each row is exactly 30 characters.

---

## Room shapes within zones

### Rect (default)
Plain rectangle.  Minimum 3 wide, 2 tall.

### L-pair (25 % chance when two consecutive rooms share an OPEN edge)
`_try_l_pair` / `_try_l_pair_vertical`, called from `_pack_band` /
`_pack_band_vertical`.  One room takes a full-row top plus a wider bottom
extension; the neighbour sits in the remaining top corner.  Both rooms
share one wall door.

### Corner-cut
`_l_shape_tiles` is defined at line 43 of `levellayout.py` but is never
called by any packing function.  Not currently used.

### Closet notch
`_nest_closets` carves a `(b_w+1) × (b_h+1)` notch from one corner of
the parent room and places the closet there.  Parent and closet share a
wall door.

---

## 1. Horizontal

**Example:** `arm_h = 2`, `cor_row = 7`

```
 0 ##############################
 1 #AAAAAAAAAAAAAAAAAAAAAAAAAAAA#
 2 #AAAAAAAAAAAAAAAAAAAAAAAAAAAA#
 3 #AAAAAAAAAAAAAAAAAAAAAAAAAAAA#
 4 #AAAAAAAAAAAAAAAAAAAAAAAAAAAA#
 5 #AAAAAAAAAAAAAAAAAAAAAAAAAAAA#
 6 ##############################
 7 #                            #
 8 #                            #
 9 ##############################
10 #BBBBBBBBBBBBBBBBBBBBBBBBBBBB#
11 #BBBBBBBBBBBBBBBBBBBBBBBBBBBB#
12 #BBBBBBBBBBBBBBBBBBBBBBBBBBBB#
13 #BBBBBBBBBBBBBBBBBBBBBBBBBBBB#
14 #BBBBBBBBBBBBBBBBBBBBBBBBBBBB#
15 ##############################
```

Zone A: cols 1–28, rows 1–(cor_row−2).
Zone B: cols 1–28, rows (cor_row+arm_h+1)–14.
Corridor: cols 1–28, rows cor_row–(cor_row+arm_h−1).
Gap rows: (cor_row−1) and (cor_row+arm_h).

**Exits:** left + right.  **Packing:** `_pack_band` for both zones.

---

## 2. Vertical

**Example:** `cor_w = 2`, `cor_col = 14`

```
 0 ##############################
 1 #AAAAAAAAAAAA#  #BBBBBBBBBBBB#
 2 #AAAAAAAAAAAA#  #BBBBBBBBBBBB#
 3 #AAAAAAAAAAAA#  #BBBBBBBBBBBB#
 4 #AAAAAAAAAAAA#  #BBBBBBBBBBBB#
 5 #AAAAAAAAAAAA#  #BBBBBBBBBBBB#
 6 #AAAAAAAAAAAA#  #BBBBBBBBBBBB#
 7 #AAAAAAAAAAAA#  #BBBBBBBBBBBB#
 8 #AAAAAAAAAAAA#  #BBBBBBBBBBBB#
 9 #AAAAAAAAAAAA#  #BBBBBBBBBBBB#
10 #AAAAAAAAAAAA#  #BBBBBBBBBBBB#
11 #AAAAAAAAAAAA#  #BBBBBBBBBBBB#
12 #AAAAAAAAAAAA#  #BBBBBBBBBBBB#
13 #AAAAAAAAAAAA#  #BBBBBBBBBBBB#
14 #AAAAAAAAAAAA#  #BBBBBBBBBBBB#
15 ##############################
```

Zone A: cols 1–12, rows 1–14.
Zone B: cols 17–28, rows 1–14.
Corridor: cols 14–15, rows 1–14.
Gap cols: 13 (between Zone A and corridor) and 16 (between corridor and Zone B).

**Exits:** top + bottom.  **Packing:** `_pack_band_vertical` for both zones.

---

## 3. Off-centre

Same structure as Horizontal but with a 30–70 % split so one band is taller.
More rooms assigned to the larger band.

**Example:** `cor_row = 10`

```
 0 ##############################
 1 #AAAAAAAAAAAAAAAAAAAAAAAAAAAA#
 2 #AAAAAAAAAAAAAAAAAAAAAAAAAAAA#
 3 #AAAAAAAAAAAAAAAAAAAAAAAAAAAA#
 4 #AAAAAAAAAAAAAAAAAAAAAAAAAAAA#
 5 #AAAAAAAAAAAAAAAAAAAAAAAAAAAA#
 6 #AAAAAAAAAAAAAAAAAAAAAAAAAAAA#
 7 #AAAAAAAAAAAAAAAAAAAAAAAAAAAA#
 8 #AAAAAAAAAAAAAAAAAAAAAAAAAAAA#
 9 ##############################
10 #                            #
11 #                            #
12 ##############################
13 #BBBBBBBBBBBBBBBBBBBBBBBBBBBB#
14 #BBBBBBBBBBBBBBBBBBBBBBBBBBBB#
15 ##############################
```

---

## 4. T-corridor

Full-width spine + one perpendicular stem reaching one border.  The stem
splits the far-side band into two sub-zones.

**Example:** `arm_h = 2`, `r_spine = 7`, stem side = far,
`c_stem = 13`, `stem_w = 3`

```
 0 ##############################
 1 #AAAAAAAAAAAAAAAAAAAAAAAAAAAA#
 2 #AAAAAAAAAAAAAAAAAAAAAAAAAAAA#
 3 #AAAAAAAAAAAAAAAAAAAAAAAAAAAA#
 4 #AAAAAAAAAAAAAAAAAAAAAAAAAAAA#
 5 #AAAAAAAAAAAAAAAAAAAAAAAAAAAA#
 6 ##############################
 7 #                            #
 8 #                            #
 9 #############   ##############
10 #BBBBBBBBBBB#   #CCCCCCCCCCCC#
11 #BBBBBBBBBBB#   #CCCCCCCCCCCC#
12 #BBBBBBBBBBB#   #CCCCCCCCCCCC#
13 #BBBBBBBBBBB#   #CCCCCCCCCCCC#
14 #BBBBBBBBBBB#   #CCCCCCCCCCCC#
15 ##############################
```

Spine: cols 1–28, rows 7–8.
Stem: cols 13–15, rows 9–14.
Zone A: cols 1–28, rows 1–5.
Zone B: cols 1–11, rows 10–14.
Zone C: cols 17–28, rows 10–14.
Gap row 6.  Gap at row 9 (cols outside 13–15).
Gap cols 12 and 16.

If stem is on the **near** side, Zone A (above spine) is split around the
near stem; Zone B (below spine) is full-width.

**Exits:** left + right (spine) + one of top/bottom (stem side).

---

## 5. Double-T

Full-width spine + two stems, one per side.

**Example:** `arm_h = 2`, `r_spine = 7`,
near stem `c_near = 9`, `w_near = 3`; far stem `c_far = 18`, `w_far = 3`

```
 0 ##############################
 1 #AAAAAAA#   #BBBBBBBBBBBBBBBB#
 2 #AAAAAAA#   #BBBBBBBBBBBBBBBB#
 3 #AAAAAAA#   #BBBBBBBBBBBBBBBB#
 4 #AAAAAAA#   #BBBBBBBBBBBBBBBB#
 5 #AAAAAAA#   #BBBBBBBBBBBBBBBB#
 6 #########   ##################
 7 #                            #
 8 #                            #
 9 ##################   #########
10 #CCCCCCCCCCCCCCCC#   #DDDDDDD#
11 #CCCCCCCCCCCCCCCC#   #DDDDDDD#
12 #CCCCCCCCCCCCCCCC#   #DDDDDDD#
13 #CCCCCCCCCCCCCCCC#   #DDDDDDD#
14 #CCCCCCCCCCCCCCCC#   #DDDDDDD#
15 ##############################
```

Near stem: cols 9–11, rows 1–6.  Far stem: cols 18–20, rows 9–14.
Zone A: cols 1–7, rows 1–5.   Zone B: cols 13–28, rows 1–5.
Zone C: cols 1–16, rows 10–14.  Zone D: cols 22–28, rows 10–14.

**Exits:** all four.
**Options:** 40 % aligned stems (cross), 60 % offset (stems differ by ≥ 0.2 × INT_W).

---

## 6. Z-corridor  (four variants)

Two parallel arms joined by a bridge.  The bridge separates a large **main**
zone from a small **side** zone.

### 6a. z_h — horizontal arms, bridge near right

**Example:** `arm_th = 2`, `bridge_w = 3`, `offset = 5`
→ `c_bridge = 21`

Arms: rows 1–2 and 13–14 (full width).
Bridge: cols 21–23, rows 3–12 (rows MIN_R+arm_th through MAX_R−arm_th).
Zones: cols 1–19 (main) and cols 25–28 (side), rows 4–11.
Gap row 3 (except bridge cols).  Gap row 12 (except bridge cols).
Gap cols 20 and 24.

```
 0 ##############################
 1 #                            #
 2 #                            #
 3 #####################   ######
 4 #MMMMMMMMMMMMMMMMMMM#   #SSSS#
 5 #MMMMMMMMMMMMMMMMMMM#   #SSSS#
 6 #MMMMMMMMMMMMMMMMMMM#   #SSSS#
 7 #MMMMMMMMMMMMMMMMMMM#   #SSSS#
 8 #MMMMMMMMMMMMMMMMMMM#   #SSSS#
 9 #MMMMMMMMMMMMMMMMMMM#   #SSSS#
10 #MMMMMMMMMMMMMMMMMMM#   #SSSS#
11 #MMMMMMMMMMMMMMMMMMM#   #SSSS#
12 #####################   ######
13 #                            #
14 #                            #
15 ##############################
```

**Fix C (spec 0019):** current code uses `rng.randint(3, max_off)`, which
allows offset = 3 → side width = offset−1 = 2, failing `side_ok (≥ 3)`.
Change to `rng.randint(4, max_off)` so side width ≥ 3 always.

### 6b. s_h — horizontal arms, bridge near left

Mirror of z_h.  `c_bridge = MIN_C + offset`.  Main zone on right, side on
left.  Same Fix C applies.

### 6c. z_v — vertical arms, bridge near bottom

**Example:** `arm_th = 2`, `bridge_w = 3`, `r_bridge = 8`

Arms: cols 1–2 and 27–28 (full height).
Bridge: cols 3–26 (MIN_C+arm_th through MAX_C−arm_th), rows 8–10.
At bridge rows all 28 interior cols are corridor (arms + bridge overlap).
Zones: cols 4–25, rows 1–6 (main) and rows 12–14 (side).
Gap rows 7 and 11 (arms only, interior cols 3–26 are wall).
Gap cols 3 and 26.

```
 0 ##############################
 1 #  #MMMMMMMMMMMMMMMMMMMMMM#  #
 2 #  #MMMMMMMMMMMMMMMMMMMMMM#  #
 3 #  #MMMMMMMMMMMMMMMMMMMMMM#  #
 4 #  #MMMMMMMMMMMMMMMMMMMMMM#  #
 5 #  #MMMMMMMMMMMMMMMMMMMMMM#  #
 6 #  #MMMMMMMMMMMMMMMMMMMMMM#  #
 7 #  ########################  #
 8 #                            #
 9 #                            #
10 #                            #
11 #  ########################  #
12 #  #SSSSSSSSSSSSSSSSSSSSSS#  #
13 #  #SSSSSSSSSSSSSSSSSSSSSS#  #
14 #  #SSSSSSSSSSSSSSSSSSSSSS#  #
15 ##############################
```

### 6d. s_v — vertical arms, bridge near top

Mirror of z_v.  Main zone below bridge, side zone above.

**Exits (all Z variants):** all four — arms reach both horizontal or
vertical borders; bridge connects both arms.

---

## 7. L-corridor  (four orientations)

L-shaped corridor: one **v-arm** (vertical) + one **h-arm** (horizontal)
meeting at a junction.  The fourth quadrant has no corridor tiles.  Rooms
placed there would be unreachable — this quadrant is filled as a corner
extension (spec 0019 Fix B).

Orientation name = position of the junction corner within the grid:

| Name | v-arm exits | h-arm exits | junction at      |
|------|-------------|-------------|------------------|
| `bl` | top         | right       | bottom-left area |
| `br` | top         | left        | bottom-right     |
| `tl` | bottom      | right       | top-left         |
| `tr` | bottom      | left        | top-right        |

All four examples use `arm_w = 2`, `arm_h = 2`.

---

### 7a. bl — exits: top + right

`cor_col = 6`, `cor_row = 8`

v-arm: cols 6–7, rows 1–9.   h-arm: cols 6–28, rows 8–9.
Zone A: cols 9–28, rows 1–6.   Zone B: cols 1–4, rows 1–9.
Zone C: cols 9–28, rows 11–14.  Empty corner: cols 1–4, rows 11–14.

```
 0 ##############################
 1 #BBBB#  #AAAAAAAAAAAAAAAAAAAA#
 2 #BBBB#  #AAAAAAAAAAAAAAAAAAAA#
 3 #BBBB#  #AAAAAAAAAAAAAAAAAAAA#
 4 #BBBB#  #AAAAAAAAAAAAAAAAAAAA#
 5 #BBBB#  #AAAAAAAAAAAAAAAAAAAA#
 6 #BBBB#  #AAAAAAAAAAAAAAAAAAAA#
 7 #BBBB#  ######################
 8 #BBBB#                       #
 9 #BBBB#                       #
10 ##############################
11 #########CCCCCCCCCCCCCCCCCCCC#
12 #########CCCCCCCCCCCCCCCCCCCC#
13 #########CCCCCCCCCCCCCCCCCCCC#
14 #########CCCCCCCCCCCCCCCCCCCC#
15 ##############################
```

Gap col 5 (v-arm left wall), gap col 8 (v-arm right wall, rows 1–9 and
col 8 wall rows 11–14), gap row 10 (h-arm bottom wall).

**Corner fill — spec 0019 Fix B, randomly choose one candidate:**

Candidate A — extend Zone B's bottommost room into the corner (cols 1–4,
rows extend to 14):

```
10 ##############################
11 #BBBB####CCCCCCCCCCCCCCCCCCCC#
12 #BBBB####CCCCCCCCCCCCCCCCCCCC#
13 #BBBB####CCCCCCCCCCCCCCCCCCCC#
14 #BBBB####CCCCCCCCCCCCCCCCCCCC#
```

Candidate B — tip room T spanning v-arm cols + corner cols (cols 1–7,
rows 11–14); accessed through a door at the h-arm's bottom face (row 10):

```
10 ##############################
11 #TTTTTTT#CCCCCCCCCCCCCCCCCCCC#
12 #TTTTTTT#CCCCCCCCCCCCCCCCCCCC#
13 #TTTTTTT#CCCCCCCCCCCCCCCCCCCC#
14 #TTTTTTT#CCCCCCCCCCCCCCCCCCCC#
```

---

### 7b. br — exits: top + left

`cor_col = 22`, `cor_row = 8`

v-arm: cols 22–23, rows 1–9.   h-arm: cols 1–23, rows 8–9.
Zone A: cols 1–20, rows 1–6.   Zone B: cols 25–28, rows 1–9.
Zone C: cols 1–20, rows 11–14.  Empty corner: cols 25–28, rows 11–14.

```
 0 ##############################
 1 #AAAAAAAAAAAAAAAAAAAA#  #BBBB#
 2 #AAAAAAAAAAAAAAAAAAAA#  #BBBB#
 3 #AAAAAAAAAAAAAAAAAAAA#  #BBBB#
 4 #AAAAAAAAAAAAAAAAAAAA#  #BBBB#
 5 #AAAAAAAAAAAAAAAAAAAA#  #BBBB#
 6 #AAAAAAAAAAAAAAAAAAAA#  #BBBB#
 7 ######################  #BBBB#
 8 #                       #BBBB#
 9 #                       #BBBB#
10 ##############################
11 #CCCCCCCCCCCCCCCCCCCC#########
12 #CCCCCCCCCCCCCCCCCCCC#########
13 #CCCCCCCCCCCCCCCCCCCC#########
14 #CCCCCCCCCCCCCCCCCCCC#########
15 ##############################
```

**Corner fill candidates:** Candidate A extends Zone B into cols 25–28, rows
11–14.  Candidate B places tip room cols 22–28, rows 11–14.

---

### 7c. tl — exits: bottom + right

`cor_col = 6`, `cor_row = 5`

v-arm: cols 6–7, rows 5–14.   h-arm: cols 6–28, rows 5–6.
Zone A: cols 9–28, rows 7–14.   Zone B: cols 1–4, rows 5–14.
Zone C: cols 9–28, rows 1–3.    Empty corner: cols 1–4, rows 1–3.

```
 0 ##############################
 1 #########CCCCCCCCCCCCCCCCCCCC#
 2 #########CCCCCCCCCCCCCCCCCCCC#
 3 #########CCCCCCCCCCCCCCCCCCCC#
 4 ##############################
 5 #BBBB#                       #
 6 #BBBB#                       #
 7 #BBBB#  #AAAAAAAAAAAAAAAAAAAA#
 8 #BBBB#  #AAAAAAAAAAAAAAAAAAAA#
 9 #BBBB#  #AAAAAAAAAAAAAAAAAAAA#
10 #BBBB#  #AAAAAAAAAAAAAAAAAAAA#
11 #BBBB#  #AAAAAAAAAAAAAAAAAAAA#
12 #BBBB#  #AAAAAAAAAAAAAAAAAAAA#
13 #BBBB#  #AAAAAAAAAAAAAAAAAAAA#
14 #BBBB#  #AAAAAAAAAAAAAAAAAAAA#
15 ##############################
```

**Corner fill candidates:** Candidate A extends Zone B's topmost room into
cols 1–4, rows 1–3.  Candidate B places tip room cols 1–7, rows 1–3.

---

### 7d. tr — exits: bottom + left

`cor_col = 22`, `cor_row = 5`

v-arm: cols 22–23, rows 5–14.   h-arm: cols 1–23, rows 5–6.
Zone A: cols 1–20, rows 7–14.   Zone B: cols 25–28, rows 5–14.
Zone C: cols 1–20, rows 1–3.    Empty corner: cols 25–28, rows 1–3.

```
 0 ##############################
 1 #CCCCCCCCCCCCCCCCCCCC#########
 2 #CCCCCCCCCCCCCCCCCCCC#########
 3 #CCCCCCCCCCCCCCCCCCCC#########
 4 ##############################
 5 #                       #BBBB#
 6 #                       #BBBB#
 7 #AAAAAAAAAAAAAAAAAAAA#  #BBBB#
 8 #AAAAAAAAAAAAAAAAAAAA#  #BBBB#
 9 #AAAAAAAAAAAAAAAAAAAA#  #BBBB#
10 #AAAAAAAAAAAAAAAAAAAA#  #BBBB#
11 #AAAAAAAAAAAAAAAAAAAA#  #BBBB#
12 #AAAAAAAAAAAAAAAAAAAA#  #BBBB#
13 #AAAAAAAAAAAAAAAAAAAA#  #BBBB#
14 #AAAAAAAAAAAAAAAAAAAA#  #BBBB#
15 ##############################
```

**Corner fill candidates:** Candidate A extends Zone B's topmost room into
cols 25–28, rows 1–3.  Candidate B places tip room cols 22–28, rows 1–3.

---

## Strategy selection

| Required exits       | Must use                        | Cannot use                      |
|----------------------|---------------------------------|---------------------------------|
| `{left, right}`      | horizontal, off_centre, t, double_t, z | vertical             |
| `{top, bottom}`      | vertical, t, double_t, z        | horizontal, off_centre          |
| perpendicular pair   | l, double_t, z                  | horizontal, vertical, off_centre |
| 3 or 4 exits         | double_t, z                     | everything else                 |

L-corridor orientation is chosen to match the required exit pair (Fix A,
spec 0019).  If no required exits: random orientation.

---

## Parameter ranges

| Parameter         | Range                    | Layout         |
|-------------------|--------------------------|----------------|
| arm_h / cor_h     | 2–3                      | all            |
| cor_w             | 2–3                      | vertical       |
| arm_w             | 2–3                      | L              |
| cor_col (bl/tl)   | 20–30 % of INT_W         | L              |
| cor_col (br/tr)   | 70–80 % of INT_W         | L              |
| cor_row (bl/br)   | 55–70 % of INT_H         | L              |
| cor_row (tl/tr)   | 25–40 % of INT_H         | L              |
| bridge_w          | 3–5                      | Z              |
| offset (z_h/s_h)  | **≥ 4** after Fix C      | Z horizontal   |
| offset (z_v/s_v)  | 3–5                      | Z vertical     |
| stem_w            | 3–5                      | T, double-T    |
| stem fraction     | 25–75 % of INT_W         | T, double-T    |
