# UGLYCRAFT — Level Layouts

Grid: 30 × 16 (0-indexed). Border: col 0, col 29, row 0, row 15. Interior: cols 1–28, rows 1–14.

Since spec 0064 (BL-42) every Act 1 level has an entrance door on the
border with the player start directly inside it, and enemies border-adjacent
(centre row 7 / centre col 14; corners at (1, 1) / (28, 1) / (1, 14) /
(28, 14)).  `main.py --dump-level N [--seed S]` prints any level 1-20 as
loaded (ASCII, spec 0064) — use it instead of reading positions off this
file when the live state matters.

Helper functions used in `levels.py`:
- `_hwall(c1, c2, r)` — horizontal wall from col c1 to c2 at row r
- `_vwall(c, r1, r2)` — vertical wall at col c from row r1 to r2

---

## Level 1 — Open Field

No interior walls.

- Entrance: (29, 7) centre right
- Player: (28, 7) inside the entrance
- Enemies: [(1, 7)] centre left

---

## Level 2 — Single Horizontal Wall

- `_hwall(6, 23, 7)` — 18 cells
- Entrance: (14, 0) centre top
- Player: (14, 1) above the wall
- Enemies: [(14, 14)] centre bottom

---

## Level 3 — H-shape with Centre Gap

- `_vwall(7, 3, 11)`, `_vwall(22, 3, 11)`
- `_hwall(7, 13, 7)`, `_hwall(16, 22, 7)` — 2-cell gap at cols 14–15
- Entrance: (29, 7) centre right
- Player: (28, 7) inside the entrance
- Enemies: [(1, 7)] centre left

---

## Level 4 — Four Pillars + Crossbar (2 enemies)

- `_vwall(5, 2, 6)`, `_vwall(24, 2, 6)`, `_vwall(5, 9, 13)`, `_vwall(24, 9, 13)` — corner pillars
- `_hwall(2, 13, 8)`, `_hwall(16, 27, 8)` — crossbar, 2-cell gap at cols 14–15
- Entrance: (14, 0) centre top
- Player: (14, 1) inside the entrance
- Enemies: [(1, 14), (28, 14)] bottom corners

---

## Level 5 — Cage with Open Bottom-Centre (2 enemies)

- `_vwall(7, 3, 12)`, `_vwall(22, 3, 12)`
- `_hwall(8, 21, 3)` — full top
- `_hwall(8, 12, 12)`, `_hwall(17, 21, 12)` — split bottom, gap at cols 13–16
- Net: cage open at lower centre
- Entrance: (14, 15) centre bottom
- Player: (14, 14) outside the cage, below its opening
- Enemies: [(1, 1), (28, 1)] top corners

---

## Level 6 — Grid of Pillars + Centre Bars (2 enemies)

- 8 outer pillars (rows 2–6) at cols 2, 4, 7, 9, 20, 22, 25, 27
- 8 lower outer pillars (rows 9–13) at same columns
- 6 horizontal bars in centre: `_hwall(12, 17, r)` at rows 2, 4, 6 (upper) and 9, 11, 13 (lower)
- Net: pillars flanking a centre corridor of horizontal bars, open gap at rows 7–8
- Entrance: (29, 7) centre right
- Player: (28, 7) inside the entrance
- Enemies: [(1, 1), (1, 14)] left corners

---

## Level 7 — Three Sealed Vaults (3 enemies)

- Vault A (top-left): `_hwall(2, 10, 2)`, `_hwall(2, 10, 7)`, `_vwall(2, 2, 7)`, `_vwall(10, 2, 7)`
- Vault B (top-right): `_hwall(19, 27, 2)`, `_hwall(19, 27, 7)`, `_vwall(19, 2, 7)`, `_vwall(27, 2, 7)`
- Vault C (lower centre): `_hwall(9, 20, 9)`, `_hwall(9, 20, 13)`, `_vwall(9, 9, 13)`, `_vwall(20, 9, 13)`
- Entrance: (14, 0) centre top
- Player: (14, 1) in the corridor between A and B
- Enemies: [(1, 7), (28, 7), (14, 14)] centre left/right (wall pockets) + centre bottom

---

## Level 8 — Slalom (3 enemies)

- `_vwall(6, 1, 11)` — top-anchored; passable at bottom (rows 12–14)
- `_vwall(12, 4, 14)` — bottom-anchored; passable at top (rows 1–3)
- `_vwall(18, 1, 11)` — top-anchored
- `_vwall(24, 4, 14)` — bottom-anchored
- Entrance: (29, 7) centre right
- Player: (28, 7) inside the entrance
- Enemies: [(1, 7), (14, 1), (14, 14)] centre left/top/bottom

---

## Level 9 — Four Chambers (3 enemies)

- Double centre divider: `_vwall(14, 1, 5)`, `_vwall(14, 10, 14)`, `_vwall(15, 1, 5)`, `_vwall(15, 10, 14)` — col 14 and 15 blocked at rows 1–5 and 10–14, open at rows 6–9
- Left side: `_hwall(2, 12, 5)`, `_hwall(2, 12, 10)`, `_vwall(2, 5, 10)` (already border)
- Right side: `_hwall(17, 27, 5)`, `_hwall(17, 27, 10)`
- Net: four enclosed chambers with a 2-cell centre corridor (cols 14–15, rows 6–9) open only at top and bottom
- Entrance: (29, 7) centre right
- Player: (28, 7) inside the entrance
- Enemies: [(1, 1), (1, 7), (1, 14)] left column: corner / centre / corner

---

## Level 10 — Concentric Vault Rings (Boss Level)

Three nested rectangular rings plus corner columns and scattered single blocks.

**Outer ring:** `_hwall(9, 20, 2)`, `_hwall(9, 20, 12)`, `_vwall(9, 2, 12)`, `_vwall(20, 2, 12)`

**Middle ring:** `_hwall(11, 18, 4)`, `_hwall(11, 18, 10)`, `_vwall(11, 4, 10)`, `_vwall(18, 4, 10)`

**Inner ring:** `_hwall(13, 16, 6)`, `_hwall(13, 16, 8)`, `_vwall(13, 6, 8)`, `_vwall(16, 6, 8)`

**Corner columns:** `_vwall(4, 1, 4)`, `_vwall(25, 1, 4)`, `_vwall(4, 10, 14)`, `_vwall(25, 10, 14)`

**Scattered single blocks:** (7,2),(22,2),(7,13),(22,13),(5,5),(24,5),(5,10),(6,10),(23,10),(24,10),(7,7),(22,7),(10,14),(13,13),(16,14),(19,13)

**Crown position (fixed):** (14, 7) — inside the inner ring (rows 6–8, cols 13–16)

**To reach the Crown:** break through one wall of each ring (9 bumps minimum, 3 per ring), earning 4 placement credits (9 breaks ÷ 2 = 4 credits, 1 break remaining toward next).

- Entrance: (0, 7) centre left
- Player: (1, 7) inside the entrance
- Boss: [(28, 7)] centre right
