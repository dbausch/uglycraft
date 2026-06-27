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

A corridor stroke with two turns.  The first arm starts at one border and
travels into the grid; at the first turn it bends onto a connector; at the
second turn it resumes the original direction and exits the *opposite* border
at a different position along it.  The shape is an S or Z: entering from one
side, exiting from the same axis but shifted.

Each turn is analogous to the L-corridor: two virtual tip extensions define
two zones.  With two turns there are **four zones in total — two on each side
of the stroke**.

The smallest example (arm_h = 1, arm_w = 1, 5 × 4 interior):

```
 0 #######
 1 #AAABB#
 2 #   BB#
 3 #CC   #
 4 #CCDDD#
 5 #######
```

Zone A: above first arm (same cols).  Zone B: right of connector, upper.
Zone C: left of connector, lower.  Zone D: below second arm (same cols).

---

### 6a. z_h — Z shape, horizontal arms

**Parameters:** `r_top`, `r_bot`, `c_break`, `arm_h`, `arm_w`

First arm:  cols 1..c_break+arm_w−1, rows r_top..r_top+arm_h−1.  Exits **LEFT**.
Connector:  cols c_break..c_break+arm_w−1, rows r_top..r_bot+arm_h−1.
Second arm: cols c_break..28, rows r_bot..r_bot+arm_h−1.  Exits **RIGHT**.

| Zone | Rows                        | Cols                  | Gap                       |
|------|-----------------------------|-----------------------|---------------------------|
| A    | 1 .. r_top−2                | 1 .. c_break+arm_w−1  | row r_top−1               |
| B    | 1 .. r_bot−2                | c_break+arm_w+1 .. 28 | col c_break+arm_w, row r_bot−1 |
| C    | r_top+arm_h+1 .. 14         | 1 .. c_break−2        | row r_top+arm_h, col c_break−1 |
| D    | r_bot+arm_h+1 .. 14         | c_break .. 28         | row r_bot+arm_h           |

**Example:** `r_top = 4`, `r_bot = 10`, `c_break = 12`, `arm_h = 2`, `arm_w = 2`

Zone A: rows 1–2,  cols 1–13.  Gap row 3.
Zone B: rows 1–8,  cols 15–28. Gap col 14, gap row 9.
Zone C: rows 7–14, cols 1–10.  Gap row 6, gap col 11.
Zone D: rows 13–14, cols 12–28. Gap row 12.

```
 0 ##############################
 1 #AAAAAAAAAAAAA#BBBBBBBBBBBBBB#
 2 #AAAAAAAAAAAAA#BBBBBBBBBBBBBB#
 3 ###############BBBBBBBBBBBBBB#
 4 #             #BBBBBBBBBBBBBB#
 5 #             #BBBBBBBBBBBBBB#
 6 ############  #BBBBBBBBBBBBBB#
 7 #CCCCCCCCCC#  #BBBBBBBBBBBBBB#
 8 #CCCCCCCCCC#  #BBBBBBBBBBBBBB#
 9 #CCCCCCCCCC#  ################
10 #CCCCCCCCCC#                 #
11 #CCCCCCCCCC#                 #
12 #CCCCCCCCCC###################
13 #CCCCCCCCCC#DDDDDDDDDDDDDDDDD#
14 #CCCCCCCCCC#DDDDDDDDDDDDDDDDD#
15 ##############################
```

**Exits:** LEFT (first arm) + RIGHT (second arm).

---

### 6b. s_h — S shape, horizontal arms  (left-right mirror of z_h)

**Parameters:** `r_top = 4`, `r_bot = 10`, `c_break = 17`, `arm_h = 2`, `arm_w = 2`

First arm:  cols c_break..28 = 17–28, rows 4–5.  Exits **RIGHT**.
Connector:  cols c_break..c_break+arm_w−1 = 17–18, rows 4–11.
Second arm: cols 1..c_break+arm_w−1 = 1–18, rows 10–11.  Exits **LEFT**.

Zone A: rows 1–2,  cols 17–28. Zone B: rows 1–8,  cols 1–15.
Zone C: rows 7–14, cols 20–28. Zone D: rows 13–14, cols 1–18.

```
 0 ##############################
 1 #BBBBBBBBBBBBBBB#AAAAAAAAAAAA#
 2 #BBBBBBBBBBBBBBB#AAAAAAAAAAAA#
 3 #BBBBBBBBBBBBBBB##############
 4 #BBBBBBBBBBBBBBB#            #
 5 #BBBBBBBBBBBBBBB#            #
 6 #BBBBBBBBBBBBBBB#  ###########
 7 #BBBBBBBBBBBBBBB#  #CCCCCCCCC#
 8 #BBBBBBBBBBBBBBB#  #CCCCCCCCC#
 9 #################  #CCCCCCCCC#
10 #                  #CCCCCCCCC#
11 #                  #CCCCCCCCC#
12 ####################CCCCCCCCC#
13 #DDDDDDDDDDDDDDDDDD#CCCCCCCCC#
14 #DDDDDDDDDDDDDDDDDD#CCCCCCCCC#
15 ##############################
```

**Exits:** RIGHT (first arm) + LEFT (second arm).

---

### 6c. z_v — Z shape, vertical arms

**Parameters:** `c_top`, `c_bot`, `r_break`, `arm_w`, `arm_h`

First arm:  cols c_top..c_top+arm_w−1, rows 1..r_break+arm_h−1.  Exits **TOP**.
Connector:  rows r_break..r_break+arm_h−1, cols c_top..c_bot+arm_w−1.
Second arm: cols c_bot..c_bot+arm_w−1, rows r_break..14.  Exits **BOTTOM**.

| Zone | Rows                  | Cols                      | Gap                        |
|------|-----------------------|---------------------------|----------------------------|
| A    | 1 .. r_break−2        | 1 .. c_top−2              | row r_break−1, col c_top−1 |
| B    | 1 .. r_break−2        | c_top+arm_w+1 .. 28       | row r_break−1, col c_top+arm_w |
| C    | r_break+arm_h+1 .. 14 | 1 .. c_bot−2              | row r_break+arm_h, col c_bot−1 |
| D    | r_break .. 14         | c_bot+arm_w+1 .. 28       | col c_bot+arm_w            |

**Example:** `c_top = 5`, `c_bot = 22`, `r_break = 7`, `arm_w = 2`, `arm_h = 2`

Zone A: rows 1–5,  cols 1–3.  Zone B: rows 1–5,  cols 8–28.
Zone C: rows 10–14, cols 1–20. Zone D: rows 7–14, cols 25–28.

```
 0 ##############################
 1 #AAA#  #BBBBBBBBBBBBBBBBBBBBB#
 2 #AAA#  #BBBBBBBBBBBBBBBBBBBBB#
 3 #AAA#  #BBBBBBBBBBBBBBBBBBBBB#
 4 #AAA#  #BBBBBBBBBBBBBBBBBBBBB#
 5 #AAA#  #BBBBBBBBBBBBBBBBBBBBB#
 6 #####  #######################
 7 #####                   #DDDD#
 8 #####                   #DDDD#
 9 ######################  #DDDD#
10 #CCCCCCCCCCCCCCCCCCCC#  #DDDD#
11 #CCCCCCCCCCCCCCCCCCCC#  #DDDD#
12 #CCCCCCCCCCCCCCCCCCCC#  #DDDD#
13 #CCCCCCCCCCCCCCCCCCCC#  #DDDD#
14 #CCCCCCCCCCCCCCCCCCCC#  #DDDD#
15 ##############################
```

**Exits:** TOP (first arm) + BOTTOM (second arm).

---

### 6d. s_v — S shape, vertical arms  (left-right mirror of z_v)

**Parameters:** `c_top = 22`, `c_bot = 5`, `r_break = 7`, `arm_w = 2`, `arm_h = 2`

First arm exits **TOP** (near right side); second arm exits **BOTTOM** (near left side).

Zone A: rows 1–5,  cols 25–28. Zone B: rows 1–5,  cols 1–20.
Zone C: rows 10–14, cols 8–28. Zone D: rows 7–14, cols 1–3.

```
 0 ##############################
 1 #BBBBBBBBBBBBBBBBBBBB#  #AAAA#
 2 #BBBBBBBBBBBBBBBBBBBB#  #AAAA#
 3 #BBBBBBBBBBBBBBBBBBBB#  #AAAA#
 4 #BBBBBBBBBBBBBBBBBBBB#  #AAAA#
 5 #BBBBBBBBBBBBBBBBBBBB#  #AAAA#
 6 ######################  ######
 7 #DDD#                   ######
 8 #DDD#                   ######
 9 #DDD#  #######################
10 #DDD#  #CCCCCCCCCCCCCCCCCCCCC#
11 #DDD#  #CCCCCCCCCCCCCCCCCCCCC#
12 #DDD#  #CCCCCCCCCCCCCCCCCCCCC#
13 #DDD#  #CCCCCCCCCCCCCCCCCCCCC#
14 #DDD#  #CCCCCCCCCCCCCCCCCCCCC#
15 ##############################
```

**Exits:** TOP (first arm) + BOTTOM (second arm).

**Note:** The current `_layout_z` code generates a different shape (two
full-width parallel arms + narrow bridge).  It must be rewritten to produce
the four-zone Z/S shape described here (spec 0019 Fix C).

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
Zone C: cols 9–28, rows 11–14.  Zone T (enlarged tip): cols 1–7, rows 11–14.

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
11 #TTTTTTT#CCCCCCCCCCCCCCCCCCCC#
12 #TTTTTTT#CCCCCCCCCCCCCCCCCCCC#
13 #TTTTTTT#CCCCCCCCCCCCCCCCCCCC#
14 #TTTTTTT#CCCCCCCCCCCCCCCCCCCC#
15 ##############################
```

Gap col 5 (between Zone B and v-arm).  Gap col 8 (between v-arm and Zones A/C/T).
Gap row 10 (between h-arm and Zones C/T).

**Zone T — enlarged v-arm tip (spec 0019 Fix B)**

A tip room is a room whose door sits on the **short end-face** of the arm —
the face the corridor would continue through if the arm went on.  An enlarged
tip room expands to fill the entire adjacent corner.

Zone T: cols 1–7, rows 11–14.  Door at gap row 10, cols 6–7 (the v-arm's base).
Zone T extends leftward from the v-arm base (cols 6–7) all the way to the
left border, filling the corner that Zone B leaves below the junction.

Zone C: cols 9–28, rows 11–14.  Door at gap row 10, cols 9–28.
Zone C must **not** be extended leftward into Zone T's area — their doors are
at different corridor positions and they must remain separate rooms.

When a stem is a dead end rather than a border exit, a third tip may exist
at the arm's far end — place a room there as well.

---

### 7b. br — exits: top + left

`cor_col = 22`, `cor_row = 8`

v-arm: cols 22–23, rows 1–9.   h-arm: cols 1–23, rows 8–9.
Zone A: cols 1–20, rows 1–6.   Zone B: cols 25–28, rows 1–9.
Zone C: cols 1–20, rows 11–14.  Zone T (enlarged tip): cols 22–28, rows 11–14.

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
11 #CCCCCCCCCCCCCCCCCCCC#TTTTTTT#
12 #CCCCCCCCCCCCCCCCCCCC#TTTTTTT#
13 #CCCCCCCCCCCCCCCCCCCC#TTTTTTT#
14 #CCCCCCCCCCCCCCCCCCCC#TTTTTTT#
15 ##############################
```

**Zone T:** cols 22–28, rows 11–14.  Door at gap row 10, cols 22–23.
Extends rightward from the v-arm base to the right border.
Zone C (cols 1–20) must not be extended into Zone T's area.

---

### 7c. tl — exits: bottom + right

`cor_col = 6`, `cor_row = 5`

v-arm: cols 6–7, rows 5–14.   h-arm: cols 6–28, rows 5–6.
Zone A: cols 9–28, rows 7–14.   Zone B: cols 1–4, rows 5–14.
Zone C: cols 9–28, rows 1–3.    Zone T (enlarged tip): cols 1–7, rows 1–3.

```
 0 ##############################
 1 #TTTTTTT#CCCCCCCCCCCCCCCCCCCC#
 2 #TTTTTTT#CCCCCCCCCCCCCCCCCCCC#
 3 #TTTTTTT#CCCCCCCCCCCCCCCCCCCC#
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

**Zone T:** cols 1–7, rows 1–3.  Door at gap row 4, cols 6–7 (v-arm's top end).
Extends leftward from the v-arm base to the left border.
Zone C (cols 9–28) must not be extended into Zone T's area.

---

### 7d. tr — exits: bottom + left

`cor_col = 22`, `cor_row = 5`

v-arm: cols 22–23, rows 5–14.   h-arm: cols 1–23, rows 5–6.
Zone A: cols 1–20, rows 7–14.   Zone B: cols 25–28, rows 5–14.
Zone C: cols 1–20, rows 1–3.    Zone T (enlarged tip): cols 22–28, rows 1–3.

```
 0 ##############################
 1 #CCCCCCCCCCCCCCCCCCCC#TTTTTTT#
 2 #CCCCCCCCCCCCCCCCCCCC#TTTTTTT#
 3 #CCCCCCCCCCCCCCCCCCCC#TTTTTTT#
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

**Zone T:** cols 22–28, rows 1–3.  Door at gap row 4, cols 22–23.
Extends rightward from the v-arm base to the right border.
Zone C (cols 1–20) must not be extended into Zone T's area.

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
