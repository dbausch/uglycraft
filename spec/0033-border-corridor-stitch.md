# 0033 — BORDER openings must land on the corridor spine (BL-29)

## Status

- [ ] `_build_super_grid` stitch chooses the border opening from **corridor**
      floor tiles only, never arbitrary room floor tiles
- [ ] `_stitch_ok` uses the same corridor-only candidate set, so its verdict
      matches what the real stitch can do
- [ ] Regression test: every BORDER opening's inner tile is owned by the entry
      grid's corridor node
- [ ] User confirms a previously-unsolvable double-T entry now opens onto the
      corridor and is solvable

## Problem

A multi-grid Act 2 level was unsolvable. A `full_border` grid was exited at the
bottom; the adjacent **double-T** grid was entered at the top — but the opening
landed in the double-T's **top-right room**, not the top corridor stem. That
room was locked by a gate whose pressure-plate puzzle sat in a *different* room
of the same grid. Entering the locked room from outside, the player could not
reach the plate, so the gate never opened: hard soft-lock.

### Root cause

`_build_super_grid` (`levellayout.py`) stitches each BORDER edge by intersecting
the floor rows/cols both grids reach at the shared border face, then opening the
wall at the middle shared position:

```python
rows_a = {r for (c, r) in room_a['tile_owner'] if c == col_a}
rows_b = {r for (c, r) in room_b['tile_owner'] if c == col_b}
shared = sorted(rows_a & rows_b)
pos = shared[len(shared) // 2]
```

`tile_owner` maps **every** floor tile to its node — corridor *and* rooms. So
the candidate set at the border-inner row/col includes room floor tiles. When a
room reaches the border face (it legitimately can — see diagram), the middle
shared position can fall inside that room, punching the inter-grid opening into a
room instead of the corridor spine. `_stitch_ok` (the pre-check that decides
whether to fall back to `full_border`) has the identical `tile_owner` scan, so it
green-lights stitches that then land in rooms.

The architecture doc already *describes* the intended behaviour as "the
intersection of floor rows/cols that both **corridor** floor sets reach" — the
code never actually restricted to the corridor. This spec makes code match doc.

## Geometry

Entry grid: double-T, horizontal spine at rows 7–8, one **top** (near) stem at
cols 13–15 reaching the top border-inner row. Top zones span rows 1–5, split by
the stem into a left room (cols 1–11) and a right room (cols 17–28). Interior is
cols 1–28, rows 1–14; row 0 / col 0 / col 29 / row 15 are always border wall.

Floor occupancy at the **inner-top row (row 1)** of the entry (double-T) grid —
`L`=top-left room, `C`=corridor stem, `R`=top-right room (gate-locked), `#`=wall:

```
col:  0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 ... 28 29
row1: # L L L L L L L L L  L  L  #  C  C  C  #  R  R ...  R  #
                                   └ corridor ┘   └─ gate-locked room ─┘
```

The exit grid (full_border, above) reaches its inner-bottom row (row 14) across
essentially all columns, so the shared-column set is governed by the entry grid.

### BEFORE (buggy) — candidate columns = all entry-grid floor at row 1

```
shared cols = {1..11} ∪ {13,14,15} ∪ {17..28}     (≈ 26 columns)
pos = middle of that set  ──►  lands at col ~17  ──►  opens into R
```
Opening at `(17,0)` ↔ entry tile `(17,1)` = top-right room `R`. The player drops
into a gate-locked room with no in-room access to its plate. **Unsolvable.**

### AFTER (fixed) — candidate columns = corridor floor at row 1 only

```
shared cols = {13,14,15}        (the top stem)
pos = middle = 14  ──►  opens into the corridor stem `C`
```
Opening at `(14,0)` ↔ entry tile `(14,1)` = corridor. The player walks down the
stem onto the spine, reaches every zone, solves the plate puzzle in the other
room, then opens the gate to `R` from the inside. **Solvable.**

If the two corridors share **no** column/row at the face (e.g. the stem column
does not overlap the exit grid's corridor columns), `_stitch_ok` now returns
False and both grids are rebuilt with `full_border`, whose corridor frame reaches
every border column/row — so a corridor-to-corridor opening is always found. The
fallback already existed; restricting to corridor tiles simply routes more of the
hard cases through it instead of silently opening into a room.

## Fix

In `_build_super_grid`:

1. Build a `gname → corridor_node_name` map from `corridor_order` +
   `grid_name_map` (the loop variable `corridor` *is* the corridor node's name,
   and `_build_subgraph` preserves it, so `tile_owner[corridor_tile]` equals it).
2. In **both** `_stitch_ok` and the real stitch loop, filter the row/col
   candidate sets to tiles whose `tile_owner` value is that grid's corridor name:

   ```python
   rows_a = {r for (c, r) in room_a['tile_owner']
             if c == col_a and room_a['tile_owner'][(c, r)] == cor_a}
   ```

   (and symmetrically for `rows_b` / `cols_a` / `cols_b`).

No other behaviour changes: the chosen `pos` is still the middle shared position,
wall popping and exit-key recording are unchanged, the `full_border` fallback is
unchanged.

## Verification

Add a regression test to `tests/test_act2_solvability.py` (or a focused new
test): for a multi-grid build, find the corridor node names (graph nodes with
`NodeSize.CORRIDOR`), then for every grid's `exits`, parse `side_pos`, compute the
inner tile (`col 1` / `COLS-2` / `row 1` / `ROWS-2` per side), and assert
`tile_owner[inner_tile]` is a corridor name. This must hold for both endpoints of
every BORDER edge. Confirm the test is **red** before the fix and **green** after.

Run the full suite (`poe test`) to confirm no regression in existing super-grid /
solvability tests.

## Done when

- [ ] Stitch and `_stitch_ok` both pick the opening from corridor floor tiles
      only (commit ____).
- [ ] New regression test asserts every BORDER opening inner tile is
      corridor-owned; red before, green after (commit ____).
- [ ] `poe test` passes (commit ____).
- [ ] User confirms the double-T entry case is now solvable (manual play).
