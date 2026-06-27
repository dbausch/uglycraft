# L-Corridor and Z-Corridor Layout Gaps

## Status

- [ ] L-corridor orientation chosen to match required BORDER exit sides
- [ ] L-corridor empty quadrant filled by one enlarged tip room (standard or transposed strategy; single parametrised algorithm for all eight variants)
- [ ] Z-corridor `_layout_z` rewritten to produce the correct single-stroke Z/S shape

---

## Principle

The layout implements the challenge graph faithfully.  Every connection in
the world must correspond to a connection in the challenge graph, and every
connected area must be reachable via a challenge-graph path.  An area of floor
space with no corridor-adjacent room is waste; a room placed with no corridor
adjacency is unreachable.

BORDER edges connect corridors.  Rooms connect to the corridor.  The layout
algorithm chooses a strategy that fits the challenge graph's structure (exits
required, room count) and places rooms only where they can connect to the
corridor.

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
to it.  Currently no zone covers it.  Any room placed there would lack a
challenge-graph-valid connection to the corridor and be unreachable.

Two potential tip rooms exist at any junction: one at the **v-arm base** (the
arm end away from its exit border) and one at the **h-arm base**.  Exactly
one is enlarged to fill the entire corner; the other's tile range is absorbed
into the adjacent zone (no separate room for it).

There are eight variants (four exit pairs × two tip strategies); a single
parametrised algorithm handles all of them — see kb section 7.

---

## Problem C — Z-corridor wrong shape

The current `_layout_z` generates two full-width parallel arms (top and
bottom) connected by a narrow bridge.  This produces an H/π shape, not a Z.

A Z-corridor is a **single corridor stroke with two turns** — three segments:
1. A partial arm exiting at two adjacent borders (top-left for `z_h`)
2. A perpendicular connector segment
3. A partial arm exiting at the opposite two borders (bottom-right for `z_h`)

The bridge (connector) is narrow in one dimension (width = `arm_w`, typically
2–3 tiles) and long in the other.  The two room zones sit on opposite sides of
the connector — one in the top-right area, one in the bottom-left area.

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

A single parametrised algorithm covers all eight variants (four orientations ×
two tip strategies).  Rotate and swap row/col directions per orientation.

**Parameters derived from the corridor `PlacedNode` and orientation:**
- `corner_bbox` — bounding box of the zone that fills the corner
- `corner_gap` — the row or col index of the corridor-facing gap into the corner zone
- `gap_range` — the row or col range where that gap faces actual corridor floor

**Standard tip strategy** (v-arm base enlarged; `jc` near the v-arm exit border):

For `bl` (`jc` = v-arm left col, `jr` = h-arm top row, arm width 2):
- Corner zone: cols 1..`jc+1`, rows `jr+2`..`MAX_R`
- Door at gap row `jr+1`, cols `jc`..`jc+1`
- Zone B spans rows 1..`jr+1` absorbing the h-arm base tiles
- Zone C (placed separately) must not extend into the corner zone's col range

**Transposed tip strategy** (h-arm base enlarged; `jc` near the opposite border):

For `bl` transposed:
- Corner zone: cols 1..`jc-2`, rows 1..`MAX_R`
- Door at gap col `jc-1`, rows 1..`jr+1`
- Zone C spans cols `jc`..`MAX_C` absorbing the v-arm base tiles

**Corner room constraint (all eight variants):**
The corridor-facing gap covers only the junction edge, not the full corner
extent.  Any room packed entirely into the corner portion (past the junction
edge) has no corridor-adjacent face and is unreachable.  When packing rooms
into the corner zone, every room that covers the far portion must extend far
enough toward the junction to include at least one tile adjacent to the gap.

Door placement is derived automatically by `derive_walls`.  Mirror all
bounding boxes and gap positions for `br`, `tl`, `tr` (see kb section 7).

If the corner zone is too small for a 2×3 room, omit it.

---

## Fix C — rewrite `_layout_z` for correct Z/S shape

Replace the current parallel-arms-plus-bridge implementation with the
single-stroke Z/S design documented in `kb/uglycraft-layouts.md` section 6.

The shape has **four** room zones, two on each side of the stroke.  See
section 6 of the layouts KB for full diagrams and zone tables.

For `z_h` (exits LEFT + RIGHT):

```
first_arm  = cols MIN_C .. c_break+arm_w-1,  rows r_top .. r_top+arm_h-1
connector  = cols c_break .. c_break+arm_w-1, rows r_top .. r_bot+arm_h-1
second_arm = cols c_break .. MAX_C,           rows r_bot .. r_bot+arm_h-1
```

(First arm and connector overlap at junction rows; second arm and connector
overlap at junction rows.)

| Zone | Rows                    | Cols                    |
|------|-------------------------|-------------------------|
| A    | 1 .. r_top−2            | 1 .. c_break+arm_w−1    |
| B    | 1 .. r_bot−2            | c_break+arm_w+1 .. 28   |
| C    | r_top+arm_h+1 .. 14     | 1 .. c_break−2          |
| D    | r_bot+arm_h+1 .. 14     | c_break .. 28           |

At each turn, Zone A + Zone B (Turn 1) and Zone C + Zone D (Turn 2) are the
two virtual tip extensions — they fill the space the corridor would occupy if
it continued straight at that turn.  All four zones are placed unconditionally
(skip any with fewer than 3 cols × 2 rows of fillable area).

Choose `r_top`, `r_bot`, `c_break` so that all four zones have at least one
packable room.  Typical values with arm_h=2, arm_w=2 on the 30×16 grid:
`r_top ≈ 4`, `r_bot ≈ 10`, `c_break ≈ 8..22`.

When a zone has zero rows/cols (arm touching the corresponding border), omit
that zone.

Apply the same logic for `s_h`, `z_v`, `s_v` (mirrors/rotations).

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
