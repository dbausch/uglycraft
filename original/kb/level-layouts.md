# UGLI 2 — Level Layouts

Field: 80 columns × 20 rows (1-indexed). Border: row 1, row 20, col 1, col 80 (always blocked). Interior: cols 2–79, rows 2–19.

All levels have inner border walls at cols 2 and 79 (rows 2–19), narrowing the playable interior to cols 3–78.

---

## Level 1 — Corridor

Inner border walls only (cols 2, 79). No other interior walls.

- Player: (76, 10), direction Left
- Enemy: (5, 10)

---

## Level 2 — Horizontal Double Wall

- Horizontal wall: cols 18–62, rows 10–11 (2 cells thick)
- Player: (76, 18) below the wall, direction Left
- Enemy: (5, 3) above the wall

---

## Level 3 — H-shape with Centre Gap

- Vertical walls: cols 20–22 rows 5–16; cols 58–60 rows 5–16 (3 cells thick)
- Horizontal wall: cols 20–60 rows 10–11 (2 cells thick), 3-cell gap at cols 39–41
- Net: two thick vertical legs joined by a double horizontal bar with a gap at centre
- Player: (51, 6) direction Left — upper right area
- Enemy: (28, 15) — lower left area

---

## Level 4 — Split Pillars + Crossbar

- Vertical pillars: cols 15–17 rows 4–8 and 13–17; cols 63–65 rows 4–8 and 13–17 (3 cells thick, 4-row gap at rows 9–12)
- Horizontal wall: cols 6–75 rows 10–11 (2 cells thick), 4-cell gap at cols 39–42
- Player: (59, 16) direction Left — lower right
- Enemy: (21, 5) — upper left

---

## Level 5 — Rectangular Frame with Side Gaps

- Vertical walls: cols 19–20 rows 4–17; cols 61–62 rows 4–17 (2 cells thick, 1-row gaps at rows 8 and 13)
- Horizontal walls: row 8 and row 13, cols 6–16 + 23–58 + 65–75 (gaps at cols 17–22 and 59–64 where verticals meet horizontals)
- Net: a frame with side passages through the gaps in the verticals
- Player: (73, 11) direction Left — right side
- Enemy: (8, 10) — left side

---

## Level 6 — Dense Pillar Labyrinth

- Primary pillars (2 cells thick): cols 10–11, 20–21, 30–31, 40–41, 50–51, 60–61, 70–71, rows 2–8 and 13–19 (4-row gap at rows 9–12)
- Secondary pillars (2 cells thick): cols 15–16, 25–26, 35–36, 45–46, 55–56, 65–66, rows 5–16
- Horizontal wall: cols 6–75 rows 10–11 (2 cells thick), rows 9 and 12 explicitly cleared; 2-cell gap at cols 40–41
- Net: dense interleaved pillars with a horizontal corridor and a narrow centre gap
- Player: (75, 5) direction Down — top-right
- Enemy: (6, 16) — bottom-left

---

## Level 7 — Three X-shapes with Corridor

Three sets of diagonal strokes (3 cells thick each), centred at roughly cols 16, 40, 64:

- Down-right strokes: I=0..11, K=(I div 6)*4 (jumps 4 cols across the horizontal wall). Blocks at cols 8+I+K, 32+I+K, 56+I+K (±1 for thickness)
- Down-left strokes: same I/K pattern. Blocks at cols 23−I−K, 47−I−K, 71−I−K (±1 for thickness)
- The strokes cross to form three X patterns above and below the corridor
- Horizontal wall: cols 6–75 rows 10–11 (2 cells thick), 2-cell gaps at cols 28–29 and 52–53
- Player: (76, 3) direction Down — top-right corner
- Enemy: (5, 18) — bottom-left corner

---

## Level 8 — Slalom (Alternating Walls)

- Top-anchored walls (rows 2–16, 2 cells thick): cols 10–11, 30–31, 50–51, 70–71
- Bottom-anchored walls (rows 5–19, 2 cells thick): cols 20–21, 40–41, 60–61
- Net: alternating walls with passable gaps — top-anchored walls have a gap at rows 17–19, bottom-anchored walls have a gap at rows 2–4. Creates a slalom course.
- Player: (75, 5) direction Down — top-right
- Enemy: (6, 5) — top-left

---

## Level 9 — "UGLI" String Art

Inner border walls (cols 2, 79) plus a string-art pattern spelling "UGLI" rendered from a 12×44 character template placed at offset (19, 5):

```
##        ##   ##########   ##            ##
##        ##  ##        ##  ##            ##
##        ##  ##        ##  ##            ##
##        ##  ##        ##  ##            ##
##        ##  ##        ##  ##            ##
##        ##  ##            ##            ##
##        ##  ##     #####  ##            ##
##        ##  ##        ##  ##            ##
##        ##  ##        ##  ##            ##
##        ##  ##        ##  ##            ##
##        ##  ##        ##  ##            ##
 ##########    ##########   ############  ##
```

- Player: (76, 10) direction Left
- Enemy: (5, 10)
