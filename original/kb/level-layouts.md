# UGLI 2 — Level Layouts

Field: 80 columns × 20 rows (1-indexed). Border: row 1, row 20, col 1, col 80 (always blocked). Interior: cols 2–79, rows 2–19.

All levels: enemy starts at (5, 10). Player start position and direction vary per level.

---

## Level 1 — Open Field

No interior walls.

- Player: (40, 10), direction Right

---

## Level 2 — Single Horizontal Wall

- Horizontal wall: cols 18–62, row 10 (45 cells)
- Player: (40, 5) above the wall, direction Right
- Enemy starts below the wall

---

## Level 3 — H-shape with Centre Gap

- Vertical walls: col 20 rows 5–15; col 60 rows 5–15
- Horizontal wall: cols 20–60 row 10, then cells (39,10),(40,10),(41,10) cleared
- Net: two vertical legs joined by a horizontal bar with a 3-cell gap at centre (cols 39–41)
- Player: (40, 9) direction Up — just above the gap

---

## Level 4 — Short Pillars + Crossbar with Centre Gap

- Vertical pillars: col 15 rows 4–8; col 65 rows 4–8; col 15 rows 12–16; col 65 rows 12–16
- Horizontal wall: cols 6–74 row 10, then (39,10),(40,10),(41,10) cleared (3-cell gap)
- Net: four corner posts with a full-width crossbar, 3-cell gap at centre
- Player: (40, 9), direction Right

---

## Level 5 — Rectangular Frame with Open Sides

- Vertical walls: col 20 rows 5–15; col 60 rows 5–15
- Horizontal walls: cols 22–58 row 7; cols 22–58 row 13
- Row 10 cols 20–60 explicitly cleared after placing verticals
- Net: a frame open left and right (verticals at cols 20/60, horizontal bars at rows 7/13), with a clear horizontal corridor at row 10
- Player: (40, 10) direction Up — in the centre corridor

---

## Level 6 — Labyrinth with Pillar Rows

Complex; columns placed in two interleaved sets:

- Set A: cols 10, 20, 30, 40, 50, 60, 70 — vertical pillars rows 2–8 and rows 12–19
- Set B: cols 15, 25, 35, 45, 55, 65 — vertical pillars rows 5–15
- Horizontal wall: cols 6–74 row 10 (overriding prior blocks); rows 9 and 11 cleared for same col range
- Then 5-cell centre gap at row 10: cols 38–42 cleared
- Net: a dense pillar labyrinth with a horizontal corridor at row 10 and a 5-cell gap at centre
- Player: (75, 5) direction Down — top-right open area

---

## Level 7 — Three X-shapes with Corridor

Two passes of diagonal lines, each placing three blocks per row:

- Pass 1 (down-right): at row I (3→17), blocks at cols (6+J, 34+J, 61+J) where J increments 0→14
- Pass 2 (down-left): at row I (3→17), blocks at cols (5+J, 33+J, 60+J) where J decrements 16→2
- The two passes cross, creating three X (diamond) shapes centred approximately at cols 14, 42, 70
- Rows 9–11 cleared entirely (cols 2–79) — open horizontal corridor
- Horizontal wall cols 6–74 row 10, then gaps: cols 26–28 and cols 54–56 cleared
- Net: three X-patterns above and below the corridor; row 10 crossbar with two 3-cell gaps
- Player: (75, 10) direction Right

---

## Level 8 — Alternating Tall Walls (Slalom)

- Top-anchored walls (rows 2–15): cols 10, 30, 50, 70
- Bottom-anchored walls (rows 5–19): cols 20, 40, 60
- Net: alternating walls that don't span the full height — passable gaps at top for bottom-anchored walls, at bottom for top-anchored walls. Creates a slalom course.
- Player: (75, 5) direction Down

---

## Level 9 — Four Chambers with Double Divider

- Double centre divider: col 39 rows 5–15; col 41 rows 5–15 (col 40 is open — a 1-cell corridor between the two walls)
- Side walls: col 20 rows 5–15; col 60 rows 5–15
- Upper horizontal arms: cols 21–38 row 5; cols 42–59 row 5
- Lower horizontal arms: cols 22–37 row 15; cols 43–58 row 15
- Net: four enclosed chambers (upper-left, upper-right, lower-left, lower-right) with a 1-cell centre corridor at col 40 (rows 5–15) accessible only from top/bottom
- Player: (40, 10) direction Right — standing in the narrow centre corridor between the divider walls
