# 0033 — BORDER openings must land on aligned corridor spines (BL-29)

## Status

- [ ] Child grids are laid out so their corridor reaches the shared border face
      at a position the already-built parent's corridor also reaches
      (coordinate-at-layout, guided retry)
- [ ] The stitch chooses the border opening from **corridor** floor tiles only,
      on both endpoints — never room floor tiles
- [ ] `full_border` is used only as a per-grid last resort when guided retry is
      exhausted (not the old all-or-nothing whole-level rebuild)
- [ ] Regression test: every BORDER opening's inner tile is corridor-owned on
      both endpoints
- [ ] Sanity: `full_border` usage across a multi-grid seed sweep stays low
      (strategy variety preserved)
- [ ] User confirms a previously-unsolvable double-T entry is now solvable

## Problem

A multi-grid Act 2 level was unsolvable. A `full_border` grid was exited at the
bottom; the adjacent **double-T** grid was entered at the top — but the opening
landed in the double-T's **top-right room**, not the top corridor stem. That room
was sealed by a gate whose pressure-plate puzzle sat in a *different* room of the
same grid. Entering the sealed room from outside, the player could not reach the
plate, so the gate never opened: hard soft-lock.

### Root cause (two coupled defects)

**Defect A — stitch picks any floor tile, not the corridor.**
`_build_super_grid` (`levellayout.py`) stitches each BORDER edge by intersecting
the floor rows/cols both grids reach at the shared border face, then opening the
wall at the middle shared position:

```python
rows_a = {r for (c, r) in room_a['tile_owner'] if c == col_a}
rows_b = {r for (c, r) in room_b['tile_owner'] if c == col_b}
shared = sorted(rows_a & rows_b)
pos = shared[len(shared) // 2]
```

`tile_owner` maps **every** floor tile to its node — corridor *and* rooms. So the
candidate set at the border-inner row/col includes room floor tiles. When a room
reaches the border face (it legitimately can — see diagram), the middle shared
position can fall inside that room, punching the inter-grid opening into a room
instead of the corridor spine. `_stitch_ok` (the pre-check that decides whether
to fall back) has the identical `tile_owner` scan, so it green-lights stitches
that then land in rooms.

**Defect B — grids are laid out independently, so corridors don't align.**
Even restricted to corridor tiles, the two grids' corridors reach the shared face
at *uncoordinated* positions (e.g. grid A's horizontal spine at rows 7–8, grid B's
at rows 2–3). They overlap only ~67% of the time (see "Blast radius"). Fixing
Defect A alone, with the existing **all-or-nothing** `full_border` fallback, would
rebuild *every* grid as a frame layout whenever *any* edge fails to align —
collapsing most multi-grid levels to `full_border` and destroying strategy
variety. The real fix must make the corridors **align by construction**.

The architecture doc already *describes* the intended behaviour as "the
intersection of floor rows/cols that both **corridor** floor sets reach" — neither
the alignment nor the corridor restriction was actually implemented.

## Blast radius (measured)

Headless scan, 280 multi-grid builds over the crowded locked/water feature sets
(`scan_border.py`, `scan_fallback.py` in the job tmp dir):

| Border side | openings on corridor | openings in a ROOM (mis-targeted) |
|-------------|---------------------:|----------------------------------:|
| left        | 156 | 112 |
| right       | 156 | 112 |
| top         | 192 | 100 |
| bottom      | 172 | 120 |

≈ **40 % of all BORDER openings land in a room, on every side** — not a double-T
corner case. Any corridor-based strategy whose room zones reach a border face
(horizontal, vertical, off_centre, t, double_t, z/s, l) is exposed; the double-T
was simply the case where the landed-in room was gate-sealed.

Corridor-only **alignment** rate per edge (would the corridors overlap at the
face without coordination): **67.5 %** — i.e. 32.5 % of edges would need help.
With the old all-or-nothing fallback this compounds: a 3-grid level (2 edges)
would fall back to full_border ≈ 54 % of the time. Hence coordinate-at-layout.

## Geometry

Entry grid: double-T, horizontal spine at rows 7–8, one **top** (near) stem at
cols 13–15 reaching the top border-inner row. Top zones span rows 1–5, split by
the stem into a left room (cols 1–11) and a right room (cols 17–28). Interior is
cols 1–28, rows 1–14; row 0 / col 0 / col 29 / row 15 are always border wall.

Floor occupancy at the **inner-top row (row 1)** of the double-T grid — `L`=top-
left room, `C`=corridor stem, `R`=top-right room (gate-sealed), `#`=wall:

```
col:  0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 ... 28 29
row1: # L L L L L L L L L  L  L  #  C  C  C  #  R  R ...  R  #
                                   └ corridor ┘   └─ gate-sealed room ─┘
```

### BEFORE (buggy) — opening = middle of ALL entry-grid floor at row 1

```
shared cols = {1..11} ∪ {13,14,15} ∪ {17..28}     (≈ 26 columns)
pos = middle  ──►  col ~17  ──►  opens into R (sealed room)   ✗ unsolvable
```

### AFTER (fixed) — corridors aligned + opening = corridor only

```
parent grid forced double-T's corridor to reach row-1 at a col the parent reaches;
shared cols (corridor only) = {13,14,15}
pos = middle = 14  ──►  opens into corridor stem C   ✓
```
The player walks down the stem onto the spine, reaches every zone, solves the
plate puzzle in the other room, then opens the gate to `R` from the inside.

## Fix

### Part 1 — Coordinate at layout (guided retry)

Grids are already built in BFS `corridor_order`, so each grid's spanning-tree
**parent is built before it** (BORDER edges form a tree — `_spanning_tree`). When
laying out grid *i* (i > 0):

1. Gather its constraint from already-built BORDER neighbours (exactly one — the
   parent — for a tree): the parent's corridor reaches the shared face at a set
   of positions `targets` (rows for a left/right face, cols for top/bottom).
   Grids are the same size, so positions share one coordinate axis.
2. Build grid *i* with its chosen strategy. **Accept** iff its corridor reaches
   the entry-side inner tile at a position in `targets`. Otherwise rebuild with a
   fresh RNG draw (re-randomising spine/stem placement) up to `K` tries
   (`K ≈ 30`).
3. If all `K` tries miss, build grid *i* with `full_border` (whose frame corridor
   reaches every face position, so it always aligns). This is now a **per-grid**
   last resort, not a whole-level rebuild.

A helper computes a grid's corridor face positions:
`corridor_face(room, side, corridor_name)` → `{pos : tile_owner[inner_tile]==corridor_name}`.

The start grid (i = 0) has no built neighbour → built freely; its children align
to it, grandchildren to children, etc.

### Part 2 — Corridor-only stitch

In the stitch loop (and the residual `_stitch_ok`, if kept), restrict the
candidate rows/cols to corridor-owned tiles on **both** endpoints, using a
`gname → corridor_node_name` map (`corridor_order` + `grid_name_map`; the loop
variable `corridor` is the corridor node's name and `_build_subgraph` preserves
it, so `tile_owner[corridor_tile]` equals it):

```python
rows_a = {r for (c, r) in room_a['tile_owner']
          if c == col_a and room_a['tile_owner'][(c, r)] == cor_a}
```

Part 1 guarantees this intersection is non-empty for every edge, so the existing
`ValueError("No shared floor …")` becomes a should-never-fire assertion. `pos` is
still the middle shared position; wall popping, exit-key recording, and barrier
placement are unchanged.

## Verification

1. **Regression test** (`tests/test_act2_solvability.py` or a focused new test):
   build multi-grid levels; for every grid's `exits`, parse `side_pos`, compute
   the inner tile, and assert `tile_owner[inner_tile]` is a corridor name (graph
   nodes with `NodeSize.CORRIDOR`). Must hold for both endpoints of every BORDER
   edge. Red before the fix (~40 % violations), green after.
2. **Variety sanity**: over a multi-grid seed sweep, assert the share of grids
   laid out as `full_border` stays low (coordinate-at-layout should keep it well
   under the old all-or-nothing collapse). Threshold set from a measured baseline.
3. `poe test` passes (no regression in existing super-grid / solvability tests).
4. **User acceptance**: the double-T entry case is solvable in actual play.

## Done when

- [ ] Child grids align their corridor to the parent's at the shared face;
      `full_border` is a per-grid last resort only (commit ____).
- [ ] Stitch + `_stitch_ok` pick the opening from corridor floor tiles only,
      both endpoints (commit ____).
- [ ] Regression test asserts every BORDER opening inner tile is corridor-owned
      on both endpoints; red before, green after (commit ____).
- [ ] `full_border`-usage sanity check passes over the seed sweep (commit ____).
- [ ] `poe test` passes (commit ____).
- [ ] User confirms the double-T entry case is now solvable (manual play).
