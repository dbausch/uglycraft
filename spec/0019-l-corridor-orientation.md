# L-Corridor and Z-Corridor Layout Gaps

## Status

- [ ] L-corridor orientation chosen to match required BORDER exit sides
- [ ] L-corridor empty quadrant filled by enlarging one randomly chosen adjacent room
- [ ] Z-corridor bridge positioned so the side zone is always viable

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

The fix is to enlarge an **existing** corridor-adjacent room so its floor
extends into the corner.  There are up to two candidates:

**Candidate A — Zone B border room**
The zone that runs alongside the v-arm (Zone B) has a room at the boundary
nearest the corner.  Extending that room's bounding box towards the corner
does not change its challenge-graph edge to the corridor; the door remains at
the same shared wall with the corridor arm.

**Candidate B — Arm tip room**
The corridor's v-arm ends at a "tip" — its innermost row (or column) closest
to the corner, just short of the corner area.  A room placed immediately
beyond this tip and spanning the full width of both the tip and the corner
columns creates a large dead-end room, accessed through a single door at the
arm's tip face.  This room is a fresh PlacedNode that covers the tip area
(same column range as the v-arm) **plus** the corner (cols outside the arm,
same rows).  Its challenge-graph edge to the corridor is satisfied by the
shared wall at the arm tip.

Randomly select one of the available candidates (A, B, or both if both exist).
If neither candidate is available, leave the corner empty.

Concretely:

| Orientation | Corner area                        | Candidate A                         | Candidate B (tip room)                      |
|-------------|------------------------------------|--------------------------------------|----------------------------------------------|
| `bl`        | cols `MIN_C`–`cor_col-2`,          | bottommost Zone B room               | cols `MIN_C`–`cor_col+arm_w-1`,              |
|             | rows `cor_row+arm_h+1`–`MAX_R`     | extended to `MAX_R`                  | rows `cor_row+arm_h+1`–`MAX_R`               |
| `br`        | cols `cor_col+arm_w+1`–`MAX_C`,    | bottommost Zone B room               | cols `cor_col`–`MAX_C`,                      |
|             | rows `cor_row+arm_h+1`–`MAX_R`     | extended to `MAX_R`                  | rows `cor_row+arm_h+1`–`MAX_R`               |
| `tl`        | cols `MIN_C`–`cor_col-2`,          | topmost Zone B room                  | cols `MIN_C`–`cor_col+arm_w-1`,              |
|             | rows `MIN_R`–`cor_row-2`           | extended to `MIN_R`                  | rows `MIN_R`–`cor_row-2`                     |
| `tr`        | cols `cor_col+arm_w+1`–`MAX_C`,    | topmost Zone B room                  | cols `cor_col`–`MAX_C`,                      |
|             | rows `MIN_R`–`cor_row-2`           | extended to `MIN_R`                  | rows `MIN_R`–`cor_row-2`                     |

Candidate B is only placed if the corner area is large enough (≥ 3 wide or
≥ 3 tall depending on orientation, and ≥ 2 in the other dimension) **and**
a spare room is available (one can be "stolen" from the least-full zone).

---

## Problem C — Z-corridor empty side zone

`_layout_z` for `z_h`/`s_h` variants places the bridge at
`offset = rng.randint(3, max_off)`.  With `offset = 3` the side zone has
width `offset − 1 = 2`, which fails `side_ok` (`zsw >= 3`) and leaves the
side area empty.  A room in the main zone cannot cover it (the bridge corridor
separates them).  The side area abuts the corridor arms but is too narrow for
a room, resulting in wasted space that cannot be filled by enlarging any
adjacent room.

The fix is structural: choose the bridge position so the side zone always has
at least width 3 (or height 2 for `z_v`/`s_v`).

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

## Fix B — fill L corner by enlarging one adjacent room

After zone packing, build a list of candidate rooms (Zone B border room, tip
room) for the corner.  Use `rng.choice` to select one.  Implement as:

- Candidate A: look up the border Zone B room in `placed`, create a new
  `PlacedNode` with the same `col`/`w` but extended `row`/`h` to reach the
  corner, replace it in `placed`.
- Candidate B: take a spare room name (preferably the last room assigned to
  any zone), compute the tip-room bounding box, create a new `PlacedNode`
  for it, insert into `placed` (replacing any previous placement for that name).

The resulting room's connection to the corridor is found by `derive_walls` in
the normal way — no special-casing needed.

---

## Fix C — guarantee Z side zone is viable

For `z_h` and `s_h` variants, change:

```python
offset = rng.randint(3, max_off)
```

to:

```python
offset = rng.randint(4, max_off)
```

This ensures `side_width = offset − 1 ≥ 3`, so `side_ok` is always `True`
and the side zone always receives a room.

For `z_v` and `s_v`, `side_ok` requires height ≥ 2 and the current offset
range already guarantees this — no change needed.

---

## Files

- `levellayout.py` — `_layout_l`, `_layout_for_strategy`, `layout_graph`
- `levellayout.py` — `_build_super_grid`: compute and pass `required_exits`
- `levellayout.py` — `_layout_z`: adjust minimum offset for `z_h`/`s_h`

---

## Done when

- [ ] `poe test` passes
- [ ] L-corridor arms always at required border sides (user confirmed)
- [ ] No large empty corner in L-corridor layouts (user confirmed)
- [ ] Z-corridor side zone always contains a room (user confirmed)
