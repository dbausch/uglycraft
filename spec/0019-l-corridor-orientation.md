# L-Corridor and Z-Corridor Layout Gaps

## Status

- [ ] L-corridor orientation chosen to match required BORDER exit sides
- [ ] L-corridor empty quadrant filled by Zone T (one enlarged tip room from v-arm base to grid border)
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

The fix is to place one **enlarged tip room** (Zone T) that fills the entire
empty corner.

A tip room is a room whose door sits on the **short end-face** of the v-arm —
the face at the base of the arm, where the corridor would continue if the arm
went on.  Enlarging it means extending its floor sideways from the arm's base
all the way to the grid border, filling the whole corner area.

Zone T's door is from the **corridor** into T (through the gap row/col at the
arm's base).  It is NOT between Zone B/A (the zone adjacent to the v-arm's
side) and Zone T; those are in different row ranges and share no wall.

Zone C (the zone below the h-arm's far side) must **not** be extended into
Zone T's area — they connect to different corridor positions and must remain
separate rooms.

Concretely for `bl` (v-arm left col `jc`, junction row `jr`, arm widths 2):

Zone T: cols 1..`jc+1`, rows `jr+2`..`MAX_R`   (door at row `jr+1`, cols `jc`..`jc+1`)

If the area is too small for a 2×3 room, omit Zone T.

(If one arm is a dead end, a second tip exists at the arm's far end; place a
room there using the same enlarged-tip logic.)

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

## Fix B — fill L corner with Zone T

After zone packing, compute Zone T and place it as a new `PlacedNode`:

- Determine `jc` (v-arm left col) and `jr` (junction row, bottom of h-arm)
  from the corridor's `PlacedNode`.
- Zone T bounding box: cols 1..`jc+1`, rows `jr+2`..`MAX_R` (for `bl`; mirror
  for other orientations — see kb section 7 for all four cases).
- Take a spare room name (last room assigned to any zone), create a new
  `PlacedNode`, insert into `placed`.

Zone T's door is derived automatically by `derive_walls` — no special-casing
needed.  The door lands at cols `jc`..`jc+1` (the v-arm's base), facing the
h-arm corridor above.

Zone C is placed separately in the normal zone-packing pass.  Do not extend
Zone C left/right into Zone T's column range.

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
