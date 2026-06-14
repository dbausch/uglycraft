# UGLYCRAFT — Level Layouts

Grid: 30 × 16 (0-indexed). Border: col 0, col 29, row 0, row 15. Interior: cols 1–28, rows 1–14.

Helper functions used in `levels.py`:
- `_hwall(c1, c2, r)` — horizontal wall from col c1 to c2 at row r
- `_vwall(c, r1, r2)` — vertical wall at col c from row r1 to r2

---

## Level 1 — Open Field

No interior walls.

- Player: (15, 8)
- Enemies: [(2, 8)]

---

## Level 2 — Single Horizontal Wall

- `_hwall(6, 23, 7)` — 18 cells
- Player: (15, 3) above the wall
- Enemies: [(2, 8)] below

---

## Level 3 — H-shape with Centre Gap

- `_vwall(7, 3, 11)`, `_vwall(22, 3, 11)`
- `_hwall(7, 13, 7)`, `_hwall(16, 22, 7)` — 2-cell gap at cols 14–15
- Player: (15, 4)
- Enemies: [(2, 8)]

---

## Level 4 — Four Pillars + Crossbar (2 enemies)

- `_vwall(5, 2, 6)`, `_vwall(24, 2, 6)`, `_vwall(5, 9, 13)`, `_vwall(24, 9, 13)` — corner pillars
- `_hwall(2, 13, 8)`, `_hwall(16, 27, 8)` — crossbar, 2-cell gap at cols 14–15
- Player: (15, 4)
- Enemies: [(2, 4), (27, 11)]

---

## Level 5 — Cage with Open Bottom-Centre (2 enemies)

- `_vwall(7, 3, 12)`, `_vwall(22, 3, 12)`
- `_hwall(8, 21, 3)` — full top
- `_hwall(8, 12, 12)`, `_hwall(17, 21, 12)` — split bottom, gap at cols 13–16
- Net: cage open at lower centre
- Player: (15, 8) inside
- Enemies: [(27, 8), (2, 12)]

---

## Level 6 — Grid of Pillars (2 enemies)

- 10 upper pillars (rows 2–6) at cols 5, 7, 10, 12, 15, 17, 20, 22, 25, 27
- 10 lower pillars (rows 9–13) at same columns
- Net: two rows of 10 pillars each, checkerboard-like spacing
- Player: (28, 3) top-right
- Enemies: [(2, 8), (2, 13)]

---

## Level 7 — Three Sealed Vaults (3 enemies)

- Vault A (top-left): `_hwall(2, 10, 2)`, `_hwall(2, 10, 7)`, `_vwall(2, 2, 7)`, `_vwall(10, 2, 7)`
- Vault B (top-right): `_hwall(19, 27, 2)`, `_hwall(19, 27, 7)`, `_vwall(19, 2, 7)`, `_vwall(27, 2, 7)`
- Vault C (lower centre): `_hwall(9, 20, 9)`, `_hwall(9, 20, 13)`, `_vwall(9, 9, 13)`, `_vwall(20, 9, 13)`
- Player: (14, 1) in the corridor between A and B
- Enemies: [(2, 8), (27, 8), (14, 14)]

---

## Level 8 — Slalom (3 enemies)

- `_vwall(6, 1, 11)` — top-anchored; passable at bottom (rows 12–14)
- `_vwall(12, 4, 14)` — bottom-anchored; passable at top (rows 1–3)
- `_vwall(18, 1, 11)` — top-anchored
- `_vwall(24, 4, 14)` — bottom-anchored
- Player: (27, 3) top-right
- Enemies: [(2, 12), (13, 2), (23, 12)]

---

## Level 9 — Four Chambers (3 enemies)

- Double centre divider: `_vwall(14, 1, 5)`, `_vwall(14, 10, 14)`, `_vwall(15, 1, 5)`, `_vwall(15, 10, 14)` — col 14 and 15 blocked at rows 1–5 and 10–14, open at rows 6–9
- Left side: `_hwall(2, 12, 5)`, `_hwall(2, 12, 10)`, `_vwall(2, 5, 10)` (already border)
- Right side: `_hwall(17, 27, 5)`, `_hwall(17, 27, 10)`
- Net: four enclosed chambers with a 2-cell centre corridor (cols 14–15, rows 6–9) open only at top and bottom
- Player: (15, 8) — col 15 row 8 is open (walls at col 15 only block rows 1–5 and 10–14)
- Enemies: [(2, 8), (27, 8), (2, 13)]

---

## Level 10 — Concentric Vault Rings (Boss Level)

Three nested rectangular rings plus corner columns and scattered single blocks.

**Outer ring:** `_hwall(9, 20, 3)`, `_hwall(9, 20, 12)`, `_vwall(9, 3, 12)`, `_vwall(20, 3, 12)`

**Middle ring:** `_hwall(11, 18, 5)`, `_hwall(11, 18, 10)`, `_vwall(11, 5, 10)`, `_vwall(18, 5, 10)`

**Inner ring:** `_hwall(13, 16, 7)`, `_hwall(13, 16, 9)`, `_vwall(13, 7, 9)`, `_vwall(16, 7, 9)`

**Corner columns:** `_vwall(4, 1, 4)`, `_vwall(25, 1, 4)`, `_vwall(4, 10, 14)`, `_vwall(25, 10, 14)`

**Scattered single blocks:** (7,2),(22,2),(7,13),(22,13),(5,5),(24,5),(5,10),(24,10),(7,7),(22,7)

**Crown position (fixed):** (14, 8) — inside the inner ring (rows 7–9, cols 13–16)

**To reach the Crown:** break through one wall of each ring (9 bumps minimum, 3 per ring), earning 4 placement credits (9 breaks ÷ 2 = 4 credits, 1 break remaining toward next).

- Player: (2, 7) left side
- Boss: [(27, 7)] right side
