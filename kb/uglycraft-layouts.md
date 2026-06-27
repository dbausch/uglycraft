# UGLYCRAFT Layout Strategies

Reference for all seven corridor-layout strategies used by Act 2
multi-grid levels.  Rows are 1–14 (MIN_R–MAX_R), cols are 1–28
(MIN_C–MAX_C), interior 28×14.

**Common symbols used in schematics:**

```
  #  corridor tile
  A B C D  room zones (rooms packed here)
  .  empty (corner gap — no corridor adjacent, no room placed)
  [1] [2]  corner-fill candidates (see L layouts)
```

---

## 1. Horizontal

Full-width horizontal spine.  Rooms packed in two horizontal bands above
and below.

**Parameters:**
- `arm_h = 2–3`  corridor height
- Spine positioned in middle third (rows ~5–9)
- Zone A (above) and Zone B (below) receive roughly equal rooms

**Exits:** left + right (spine tiles span cols 1–28)

```
col: 1─────────────────────────28
  1: AAAAAAAAAAAAAAAAAAAAAAAAAAA
  2: AAAAAAAAAAAAAAAAAAAAAAAAAAA   Zone A  (above)
  3: AAAAAAAAAAAAAAAAAAAAAAAAAAA
  4: AAAAAAAAAAAAAAAAAAAAAAAAAAA
  5: ───────────────────────────
  6: ###########################   Corridor (arm_h rows)
  7: ───────────────────────────
  8: BBBBBBBBBBBBBBBBBBBBBBBBBBB
  9: BBBBBBBBBBBBBBBBBBBBBBBBBBB   Zone B  (below)
 10: BBBBBBBBBBBBBBBBBBBBBBBBBBB
 11: BBBBBBBBBBBBBBBBBBBBBBBBBBB
 12: BBBBBBBBBBBBBBBBBBBBBBBBBBB
 13: BBBBBBBBBBBBBBBBBBBBBBBBBBB
 14: BBBBBBBBBBBBBBBBBBBBBBBBBBB
```

Rooms are stacked (L-pair / closet-corner shapes possible) within each band.

---

## 2. Vertical

Full-height vertical spine.  Rooms packed in two vertical bands left and
right.

**Parameters:**
- `cor_w = 2–3`  corridor width
- Spine positioned near horizontal centre (cols ~12–17)
- Zone A (left) and Zone B (right) each at least 5 cols wide

**Exits:** top + bottom (spine tiles span rows 1–14)

```
col: 1────────13 14 15──────────28
  1: AAAAAAAAAAA ## BBBBBBBBBBBBB
  2: AAAAAAAAAAA ## BBBBBBBBBBBBB
  3: AAAAAAAAAAA ## BBBBBBBBBBBBB   Zone A | Spine | Zone B
  4: AAAAAAAAAAA ## BBBBBBBBBBBBB
  5: AAAAAAAAAAA ## BBBBBBBBBBBBB
  6: AAAAAAAAAAA ## BBBBBBBBBBBBB
  7: AAAAAAAAAAA ## BBBBBBBBBBBBB
  8: AAAAAAAAAAA ## BBBBBBBBBBBBB
  9: AAAAAAAAAAA ## BBBBBBBBBBBBB
 10: AAAAAAAAAAA ## BBBBBBBBBBBBB
 11: AAAAAAAAAAA ## BBBBBBBBBBBBB
 12: AAAAAAAAAAA ## BBBBBBBBBBBBB
 13: AAAAAAAAAAA ## BBBBBBBBBBBBB
 14: AAAAAAAAAAA ## BBBBBBBBBBBBB
```

Rooms are stacked vertically (L-pair / closet-corner shapes possible).

---

## 3. Off-centre

Same topology as horizontal, but the spine is shifted so one band is
noticeably larger.  More rooms go in the larger band.

**Parameters:**
- `split ∈ [0.3, 0.7]` fraction above
- Minimum band height: 3 rows each side
- Rooms biased toward bigger band (2:1 ratio)

**Exits:** left + right

```
col: 1─────────────────────────28
  1: AAAAAAAAAAAAAAAAAAAAAAAAAAA
  2: AAAAAAAAAAAAAAAAAAAAAAAAAAA
  3: AAAAAAAAAAAAAAAAAAAAAAAAAAA   Zone A  (large, ~60-70%)
  4: AAAAAAAAAAAAAAAAAAAAAAAAAAA
  5: AAAAAAAAAAAAAAAAAAAAAAAAAAA
  6: AAAAAAAAAAAAAAAAAAAAAAAAAAA
  7: ###########################   Corridor (shifted high)
  8: ───────────────────────────
  9: BBBBBBBBBBBBBBBBBBBBBBBBBBB   Zone B  (small, ~30-40%)
 10: BBBBBBBBBBBBBBBBBBBBBBBBBBB
 11: BBBBBBBBBBBBBBBBBBBBBBBBBBB
 12: BBBBBBBBBBBBBBBBBBBBBBBBBBB
 13: BBBBBBBBBBBBBBBBBBBBBBBBBBB
 14: BBBBBBBBBBBBBBBBBBBBBBBBBBB
```

---

## 4. T-corridor

Full-width horizontal spine with one perpendicular stem reaching a border.
The stem divides the far-side zone into two sub-zones.

**Parameters:**
- `arm_h = 2–3`  spine height
- Spine in middle third (rows ~5–9)
- Stem: width 3–5, column fraction 25–75%
- Stem side: `'near'` (toward row 1) or `'far'` (toward row 14)

**Exits:** left + right + one T/B side (the stem side)

Example (stem on 'far' side, offset-right):

```
col: 1──────10 11 13───────────28
  1: AAAAAAAAAAAAAAAAAAAAAAAAAA    Zone A  (near side, full width)
  2: AAAAAAAAAAAAAAAAAAAAAAAAAA
  3: AAAAAAAAAAAAAAAAAAAAAAAAAA
  4: AAAAAAAAAAAAAAAAAAAAAAAAAA
  5: ##########################    Spine
  6: ##########################
  7: ──────────────────────────
  8: BBBBBBBBB ## CCCCCCCCCCCC     Zone B (far-left) | Stem | Zone C (far-right)
  9: BBBBBBBBB ## CCCCCCCCCCCC
 10: BBBBBBBBB ## CCCCCCCCCCCC
 11: BBBBBBBBB ## CCCCCCCCCCCC
 12: BBBBBBBBB ## CCCCCCCCCCCC
 13: BBBBBBBBB ## CCCCCCCCCCCC
 14: BBBBBBBBB ## CCCCCCCCCCCC     ← stem exits bottom border
```

Near-side stem omits Zone A entirely; far-side splits only the far band.

---

## 5. Double-T

Full-width horizontal spine with one stem on each side.  Both stems reach
their respective border, dividing both bands.  Two variants: aligned stems
(cross shape, 40% chance) or offset stems (60% chance).

**Parameters:**
- Same as T but two stems
- `frac_near` and `frac_far` each in [0.25, 0.75]; differ by ≥ 0.2 when offset

**Exits:** all four borders (spine covers left/right; stems cover top/bottom)

Example (offset stems):

```
col: 1──5 6 8──────────17 18 20─28
  1: AAAA ## BBBBBBBBBBB  ##  CCCC   near stem | Zones A+B+C (near side)
  2: AAAA ## BBBBBBBBBBB  ##  CCCC
  3: AAAA ## BBBBBBBBBBB  ##  CCCC
  4: AAAA ## BBBBBBBBBBB  ##  CCCC
  5: ##########################    Spine
  6: ##########################
  7: ──────────────────────────
  8: DDDDDDDD  ##  EEEEEEEEEEEE   far stem | Zones D+E (far side)
  9: DDDDDDDD  ##  EEEEEEEEEEEE
 10: DDDDDDDD  ##  EEEEEEEEEEEE
 11: DDDDDDDD  ##  EEEEEEEEEEEE
 12: DDDDDDDD  ##  EEEEEEEEEEEE
 13: DDDDDDDD  ##  EEEEEEEEEEEE
 14: DDDDDDDD  ##  EEEEEEEEEEEE
```

---

## 6. Z-corridor  (four variants)

Two parallel arms joined by an off-centre bridge.  The bridge divides the
space between the arms into a large main zone and a small side zone.

### 6a. z_h  (bridge right)

**Parameters:**
- `arm_th = 2–3`  arm thickness
- `bridge_w = 3–5`  bridge width
- `offset ≥ 4`  ← Fix C ensures side zone ≥ 3 cols wide
- `c_bridge = MAX_C − bridge_w − offset + 1`  (bridge near right edge)

**Exits:** top + bottom + left + right (arms are full-width; bridge spans full height)

```
col: 1────────────────c-1 c──c+bw 28
  1: ###########################   Top arm (full width, arm_th rows)
  2: ###########################
  3: ──────────────────────────
  4: MMMMMMMMMMMMMMMM ## SSSSSS   Main zone (large) | Bridge | Side zone (≥3)
  5: MMMMMMMMMMMMMMMM ## SSSSSS
  6: MMMMMMMMMMMMMMMM ## SSSSSS
  7: MMMMMMMMMMMMMMMM ## SSSSSS
  8: MMMMMMMMMMMMMMMM ## SSSSSS
  9: MMMMMMMMMMMMMMMM ## SSSSSS
 10: MMMMMMMMMMMMMMMM ## SSSSSS
 11: MMMMMMMMMMMMMMMM ## SSSSSS
 12: ──────────────────────────
 13: ###########################   Bottom arm (full width, arm_th rows)
 14: ###########################
```

Main zone uses `_pack_band`; side zone uses `_pack_band_vertical` (1 room only).

### 6b. s_h  (bridge left)

Mirror of z_h.  `c_bridge = MIN_C + offset`.
Main zone is on the **right** of bridge; side zone on the **left**.

### 6c. z_v  (bridge near bottom)

Transposed version of z_h.  Two full-height vertical arms at left and right;
horizontal bridge near bottom.

**Parameters:**
- `arm_th = 2–3`  arm thickness
- `bridge_w = 3–5`  bridge height (number of rows)
- `offset ≥ 3` (side height `offset−1 ≥ 2` already guaranteed)
- `r_bridge = MAX_R − bridge_w − offset + 1`

**Exits:** left + right + top + bottom

```
col: 1 2 3──────────────────26 27 28
  1: ## MMMMMMMMMMMMMMMMMMMM ##    Left arm | Main zone (above bridge) | Right arm
  2: ## MMMMMMMMMMMMMMMMMMMM ##
  3: ## MMMMMMMMMMMMMMMMMMMM ##
  4: ## MMMMMMMMMMMMMMMMMMMM ##
  5: ## MMMMMMMMMMMMMMMMMMMM ##
  6: ## MMMMMMMMMMMMMMMMMMMM ##
  7: ## MMMMMMMMMMMMMMMMMMMM ##
  8: ## MMMMMMMMMMMMMMMMMMMM ##
  9: ## #################### ##    Bridge (full inner width)
 10: ## #################### ##
 11: ## #################### ##
 12: ## SSSSSSSSSSSSSSSSSSSS ##    Side zone (≥2 rows)
 13: ## SSSSSSSSSSSSSSSSSSSS ##
 14: ## SSSSSSSSSSSSSSSSSSSS ##
```

### 6d. s_v  (bridge near top)

Mirror of z_v.  Bridge near top; main zone below.

---

## 7. L-corridor  (four orientations)

L-shaped corridor with a vertical arm (v-arm) and a horizontal arm (h-arm)
meeting at a junction.  One quadrant — opposite the junction corner — has
no corridor tiles and can only receive rooms via Fix B (corner fill).

**Parameters:**
- `arm_h = 2–3`  arm thickness (both arms same)
- `arm_w = 2–3`  arm width
- `cor_col`: v-arm column start; left-side: 20–30% of INT_W; right-side: 70–80%
- `cor_row`: h-arm row start; top-arm: 25–40%; bottom-arm: 55–70%

**Orientation → required exits map** (Fix A):

| Orientation | `required_exits`        | v-arm direction | h-arm direction |
|-------------|-------------------------|-----------------|-----------------|
| `bl`        | `{top, right}`          | upward (→ MIN_R) | rightward (→ MAX_C) |
| `br`        | `{top, left}`           | upward (→ MIN_R) | leftward (→ MIN_C)  |
| `tl`        | `{bottom, right}`       | downward (→ MAX_R) | rightward (→ MAX_C) |
| `tr`        | `{bottom, left}`        | downward (→ MAX_R) | leftward (→ MIN_C)  |

---

### 7a. bl  (exits: top + right)

v-arm goes up; h-arm goes right; junction at lower-left of v-arm.
Empty corner: **bottom-left** (`cols 1..cor_col-2, rows cor_row+arm_h+1..14`).

```
col: 1──cor_col──cor_col+arm_w────28
  1: .... #### AAAAAAAAAAAAAAAAAAA    v-arm (##) | Zone A (above h-arm, right of v-arm)
  2: .... #### AAAAAAAAAAAAAAAAAAA
  3: .... #### AAAAAAAAAAAAAAAAAAA
  4: .... #### ─────────────────── ← h-arm starts
  5: BBBB #### ###################   Zone B (left of v-arm) | junction | h-arm (###)
  6: BBBB #### ###################
  7: BBBB ─────────────────────── ← h-arm ends
  8: [12] ....  CCCCCCCCCCCCCCCCCC   [corner] | Zone C (below h-arm, right of v-arm)
  9: [12] ....  CCCCCCCCCCCCCCCCCC
 10: [12] ....  CCCCCCCCCCCCCCCCCC
 11: [12] ....  CCCCCCCCCCCCCCCCCC
 12: [12] ....  CCCCCCCCCCCCCCCCCC
 13: [12] ....  CCCCCCCCCCCCCCCCCC
 14: [12] ....  CCCCCCCCCCCCCCCCCC
```

**Corner fill candidates (randomly chosen):**

`[1]` Candidate A — extend Zone B's **bottommost** room downward to row 14:
```
  7: BBBB ─────────────────────── ← h-arm ends
  8: B[1] ....  CCCCCCCCCCCCCCCCCC   Zone B room extends down (same cols, to MAX_R)
  9: B[1] ....  CCCCCCCCCCCCCCCCCC
 ...
 14: B[1] ....  CCCCCCCCCCCCCCCCCC
```
Room's door remains at the shared wall with the v-arm; floor grows into corner.

`[2]` Candidate B — tip room below v-arm, spanning corner + v-arm columns:
```
  7: ──── ─────────────────────── ← h-arm ends  (v-arm ends too)
  8: [2][2][2][2]  CCCCCCCCCCCCCCCC  Tip room (cols 1..cor_col+arm_w-1)
  9: [2][2][2][2]  CCCCCCCCCCCCCCCC
 ...
 14: [2][2][2][2]  CCCCCCCCCCCCCCCC
```
Room door at bottom face of v-arm (row cor_row+arm_h, cols cor_col..cor_col+arm_w-1).
One room is "stolen" from Zone B or C to place here.

---

### 7b. br  (exits: top + left)

v-arm goes up; h-arm goes left; junction at lower-right of v-arm.
Empty corner: **bottom-right** (`cols cor_col+arm_w+1..28, rows cor_row+arm_h+1..14`).

```
col: 1───────────────cor_col──────28
  1: AAAAAAAAAAAAAAAA #### ........    Zone A | v-arm | (top-right, empty)
  2: AAAAAAAAAAAAAAAA #### ........
  3: AAAAAAAAAAAAAAAA #### ........
  4: ─────────────────────────────  ← h-arm starts
  5: ##################### #### BBBB   h-arm | junction | Zone B (right of v-arm)
  6: ##################### #### BBBB
  7: ──────────────────────────────  ← h-arm ends
  8: CCCCCCCCCCCCCCCC .... [12][12]  Zone C | (corner) | corner fill [1][2]
  9:   ...
 14: CCCCCCCCCCCCCCCC .... [12][12]
```

`[1]` Extend Zone B's bottommost room downward (same cols, to row 14).
`[2]` Tip room cols `cor_col..28`, rows `cor_row+arm_h+1..14` (spans v-arm + corner).

---

### 7c. tl  (exits: bottom + right)

v-arm goes down; h-arm goes right; junction at upper-left of v-arm.
Empty corner: **top-left** (`cols 1..cor_col-2, rows 1..cor_row-2`).

```
col: 1──cor_col──cor_col+arm_w────28
  1: [12] .... CCCCCCCCCCCCCCCCCC   [corner fill] | Zone C (above h-arm, right of v-arm)
  2: [12] .... CCCCCCCCCCCCCCCCCC
  3: [12] .... CCCCCCCCCCCCCCCCCC
  4: [12] ─────────────────────── ← h-arm starts (row cor_row)
  5: BBBB #### ###################   Zone B (left of v-arm) | junction | h-arm
  6: BBBB #### ###################
  7: BBBB ─────────────────────── ← h-arm ends
  8: BBBB #### AAAAAAAAAAAAAAAAAAA   Zone B continues | v-arm | Zone A (below h-arm, right)
  9: BBBB #### AAAAAAAAAAAAAAAAAAA
 10: BBBB #### AAAAAAAAAAAAAAAAAAA
 11: BBBB #### AAAAAAAAAAAAAAAAAAA
 12: BBBB #### AAAAAAAAAAAAAAAAAAA
 13: BBBB #### AAAAAAAAAAAAAAAAAAA
 14: BBBB #### AAAAAAAAAAAAAAAAAAA
```

`[1]` Extend Zone B's **topmost** room upward to row 1 (same cols, to MIN_R).
`[2]` Tip room cols `1..cor_col+arm_w-1`, rows `1..cor_row-2` (above v-arm top face).

---

### 7d. tr  (exits: bottom + left)

v-arm goes down; h-arm goes left; junction at upper-right of v-arm.
Empty corner: **top-right** (`cols cor_col+arm_w+1..28, rows 1..cor_row-2`).

```
col: 1───────────────cor_col──────28
  1: CCCCCCCCCCCCCCCC .... [12][12]  Zone C (above h-arm, left of v-arm) | [corner fill]
  2: CCCCCCCCCCCCCCCC .... [12][12]
  3: CCCCCCCCCCCCCCCC .... [12][12]
  4: ─────────────────────────────  ← h-arm starts
  5: ##################### #### BBBB   h-arm | junction | Zone B (right of v-arm)
  6: ##################### #### BBBB
  7: ──────────────────────────────  ← h-arm ends
  8: AAAAAAAAAAAAAAAA #### BBBBBBBB  Zone A (below h-arm, left) | v-arm | Zone B
  9:   ...
 14: AAAAAAAAAAAAAAAA #### BBBBBBBB
```

`[1]` Extend Zone B's topmost room upward (same cols, to row 1).
`[2]` Tip room cols `cor_col..28`, rows `1..cor_row-2` (above v-arm top face).

---

## Zone packing functions

| Function              | Packs rooms along | Used in                                   |
|-----------------------|-------------------|-------------------------------------------|
| `_pack_band`          | Horizontal        | Horizontal, off-centre, T/double-T, z/s   |
| `_pack_band_vertical` | Vertical          | Vertical, Z side zones, L Zone B          |

Both functions may place rooms as plain rectangles, **L-pair rooms** (two
rooms sharing one wall, one of which is L-shaped), or **corner-closet** rooms.

---

## Strategy selection — `_pick_strategy`

Selects a strategy compatible with the required border exits:

| Requirement              | Eligible strategies                              |
|--------------------------|--------------------------------------------------|
| Only L + R exits         | horizontal, off_centre, t, double_t, z (not vertical, not l) |
| Only T + B exits         | vertical, double_t, z (not horizontal, off_centre)            |
| Perpendicular pair (L+T etc.) | l, double_t, z                              |
| 3 or 4 exits             | double_t, z only                                |
| 0 or 1 exit              | any strategy                                     |

Fallback order: preferred list → double_t → z (z always works for any direction).

---

## Corner-fill implementation notes (Fix B for L-layouts)

After zone packing, build a candidate list:

1. **Candidate A**: find the border Zone B room (topmost or bottommost
   depending on orientation).  Create a new `PlacedNode` with the same
   `col`/`w` but `row`/`h` extended to reach `MIN_R` or `MAX_R`.  Replace in
   `placed`.

2. **Candidate B**: steal one spare room name (last in a zone's list, or the
   last room assigned to any zone).  Compute the tip-room bounding box
   (v-arm columns + corner columns × corner rows).  Create a new `PlacedNode`
   for it.  Insert into `placed` (replacing previous placement).

   Candidate B is only added to the list if the corner area is large enough:
   - width ≥ 3 (cols from `MIN_C` or `cor_col`) AND height ≥ 2 (rows in corner)
   - At least one room can be "stolen" (zone list has > 1 item)

Use `rng.choice(candidates)` to pick.  If candidates is empty, leave corner
as solid wall.

---

## Z-layout bridge constraint (Fix C)

For `z_h` and `s_h`: change minimum offset from 3 → **4** so that
`side_width = offset − 1 ≥ 3` (satisfies `side_ok`).  The side zone always
receives exactly one room.

For `z_v` and `s_v`: minimum side height is 2; offset ≥ 3 already guarantees
this (unchanged).
