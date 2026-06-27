# L-Corridor and Z-Corridor Layout Gaps

## Status

- [ ] L-corridor orientation chosen to match required BORDER exit sides
- [ ] L-corridor empty quadrant filled by one enlarged tip room (standard or transposed strategy; single parametrised algorithm for all eight variants)
- [ ] Z-corridor `_layout_z` rewritten to produce the correct single-stroke Z/S shape

---

## Problem A — L-corridor wrong orientation

`_layout_l` picks one of `['bl', 'br', 'tl', 'tr']` at random.  Each
orientation exposes exits at a different pair of grid borders:

| Orientation | corridor exits |
|-------------|----------------|
| `bl`        | top + right    |
| `br`        | top + left     |
| `tl`        | bottom + right |
| `tr`        | bottom + left  |

When `_pick_strategy` selects `'l'` for a corridor that requires, say,
`exits = {'left', 'top'}`, `_layout_l` might produce `'tl'` (bottom + right),
placing arms on the wrong borders.  The stitch falls back to `'z'` every time,
and the L-shape is never actually used.

---

## Problem B — L-corridor empty quadrant

The L-shape leaves one rectangular quadrant with no corridor floor adjacent
to it.  Currently no zone covers it, so rooms placed there would be unreachable.

Two potential tip rooms exist at any junction: one at the v-arm base and one
at the h-arm base.  Exactly one is enlarged to fill the corner; the other's
tile range is absorbed into the adjacent zone (no separate room for it).
Eight variants total: four exit pairs × two tip strategies.

---

## Problem C — Z-corridor wrong shape

The current `_layout_z` generates two full-width parallel arms (top and
bottom) connected by a narrow bridge.  This produces an H/π shape, not a Z.

A Z-corridor is a **single corridor stroke with two turns** — three segments:
1. A partial arm exiting at two adjacent borders (top-left for `z_h`)
2. A perpendicular connector segment (width = `arm_w`, typically 2–3 tiles)
3. A partial arm exiting at the opposite two borders (bottom-right for `z_h`)

The two room zones sit on opposite sides of the connector — one in the
top-right quadrant, one in the bottom-left quadrant.

---

## Fix A — orient L by required exits

Pass `required_exits: frozenset` from `_build_super_grid` through
`layout_graph` and `_layout_for_strategy` to `_layout_l`.  Map exit pair to
orientation:

```python
_EXIT_PAIR_TO_ORIENTATION = {
    frozenset({'top',    'right'}) : 'bl',
    frozenset({'top',    'left'})  : 'br',
    frozenset({'bottom', 'right'}) : 'tl',
    frozenset({'bottom', 'left'})  : 'tr',
}
```

If the required exits don't match any pair (0, 1, 3, or 4 exits), fall back to
`rng.choice`.

---

## Fix B — fill L corner with one enlarged tip room

One parametrised algorithm for all eight variants; rotate and swap row/col
directions per orientation.  Either tip strategy is valid — choose freely.

**Standard** (`jc` near v-arm exit border, `bl` example):
- Corner zone: cols 1..`jc+1`, rows `jr+2`..`MAX_R`;  door at gap row `jr+1`
- Zone B spans rows 1..`jr+1`, absorbing the h-arm base tile range
- Zone C is placed in the normal zone-packing pass; do not extend it into the
  corner zone's col range (different corridor-facing gap)

**Transposed** (`jc` near opposite border, `bl` example):
- Corner zone: cols 1..`jc-2`, rows 1..`MAX_R`;  door at gap col `jc-1`
- Zone C spans cols `jc`..`MAX_C`, absorbing the v-arm base tile range

**Corner room constraint:** the corridor-facing gap of the corner zone covers
only the junction edge rows/cols, not the full corner extent.  Rooms packed
into the far end of the corner zone must extend back to the junction edge;
otherwise they have no corridor-adjacent face and are unreachable.

Mirror all bounding boxes for `br`, `tl`, `tr` (see kb section 7 for diagrams).

If the corner zone is too small for a 2×3 room, omit it.

---

## Fix C — rewrite `_layout_z` for correct Z/S shape

Replace with the single-stroke Z/S design from `kb/uglycraft-layouts.md`
section 6.

For `z_h` (exits LEFT + RIGHT):

```
first_arm  = cols MIN_C .. c_break+arm_w-1,  rows r_top .. r_top+arm_h-1
connector  = cols c_break .. c_break+arm_w-1, rows r_top .. r_bot+arm_h-1
second_arm = cols c_break .. MAX_C,           rows r_bot .. r_bot+arm_h-1
```

| Zone | Rows                    | Cols                    |
|------|-------------------------|-------------------------|
| A    | 1 .. r_top−2            | 1 .. c_break+arm_w−1    |
| B    | 1 .. r_bot−2            | c_break+arm_w+1 .. 28   |
| C    | r_top+arm_h+1 .. 14     | 1 .. c_break−2          |
| D    | r_bot+arm_h+1 .. 14     | c_break .. 28           |

Skip zones with fewer than 3 cols × 2 rows.  Typical: `r_top ≈ 4`,
`r_bot ≈ 10`, `c_break ≈ 8..22`.  Apply the same logic for `s_h`, `z_v`, `s_v`.

---

## Files

- `levellayout.py` — `_layout_l`, `_layout_for_strategy`, `layout_graph`
- `levellayout.py` — `_build_super_grid`: compute and pass `required_exits`
- `levellayout.py` — `_layout_z`: complete rewrite

---

## Done when

- [ ] `poe test` passes
- [ ] L-corridor arms always at required border sides (user confirmed)
- [ ] L-corridor empty corner filled by one enlarged tip room for all eight variants; no unreachable corner rooms (user confirmed)
- [ ] Z-corridor is a single-stroke Z/S shape with two primary zones + optional C/D (user confirmed)
