# L-Corridor and Z-Corridor Layout Gaps

## Status

- [ ] L-corridor orientation chosen to match required BORDER exit sides
- [ ] L-corridor empty quadrant filled by enlarging one randomly chosen virtual tip room
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

The fix is to place (or enlarge) a room using a **virtual tip room**.  At the
junction, each arm has a virtual extension in the direction it would continue
if it went straight through.  These virtual extensions define small rooms that
can be enlarged into the empty corner by removing the wall separating them
from it.  For an L-corridor there are always **two** virtual tip rooms:

**Tip 1 — v-arm extension**
Where the v-arm would continue past the junction (in the opposite direction
from its border exit).  This defines a small room area just inside the empty
quadrant, separated from the h-arm corridor by one gap row.  Enlarge it
**toward the adjacent corner** by removing the gap wall between it and the
corner columns.

**Tip 2 — h-arm extension**
Where the h-arm would continue past the junction (away from its border exit).
This area is within Zone B's bounding box (nearest to the corner).  The
bottommost (or topmost, depending on orientation) Zone B room already occupies
this position.  Enlarge it **toward the corner** by removing the gap row/col
that separates it from the corner rows/cols.

(If one arm is a dead end rather than a border exit, a third virtual tip
exists at the arm's far end — the direction the arm faces but does not exit.
Each virtual tip can be enlarged into the adjacent empty area, potentially
spanning more than one empty corner.)

Both available tip rooms are always placed.  Tip 1 requires creating a
new `PlacedNode`; Tip 2 requires extending an existing `PlacedNode`.  If a
tip's area is too small for even a 2×2 room, omit that tip only.

Concretely for `bl` (junction col `jc`, junction row `jr`, arm widths 2):

| Tip | Room position before enlargement           | Enlarge direction         | Result                                 |
|-----|--------------------------------------------|---------------------------|----------------------------------------|
| 1   | cols `jc`–`jc+1`, rows `jr+2`–`MAX_R`     | left → add cols `1`–`jc-2`  | cols 1–`jc+1`, rows `jr+2`–`MAX_R`    |
| 2   | Zone B's bottommost room (cols 1–`jc-2`)   | down → extend to `MAX_R`  | cols 1–`jc-2`, rows `<orig top>`–`MAX_R` |

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

## Fix B — fill L corner by placing both tip rooms

After zone packing, identify the two virtual tip rooms and place both.
Implement as:

- **Tip 1** (v-arm extension): take a spare room name (preferably the last
  room assigned to any zone), compute the tip-room bounding box before
  enlargement, then extend it to fill the corner by adjusting `col`/`w`
  (or `row`/`h` depending on orientation), create a new `PlacedNode`, insert
  into `placed`.
- **Tip 2** (h-arm extension = Zone B border room): look up the border Zone B
  room in `placed`, create a new `PlacedNode` with extended `row`/`h` (or
  `col`/`w`) to reach the corner, replace it in `placed`.

The resulting room's connection to the corridor is found by `derive_walls` in
the normal way — no special-casing needed.

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
- [ ] Both L-corridor tip rooms placed, filling all corner-adjacent areas (user confirmed)
- [ ] Z-corridor is a single-stroke Z/S shape with two primary zones + optional C/D (user confirmed)
