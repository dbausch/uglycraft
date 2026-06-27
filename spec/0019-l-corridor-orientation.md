# L-Corridor Orientation and Corner Gaps

## Status

- [ ] L-corridor orientation chosen to match required BORDER exit sides
- [ ] Empty quadrant filled: adjacent Zone B extended to cover it

---

## Problem A — wrong orientation

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

## Problem B — large empty quadrant

The L-shape leaves one rectangular quadrant with no corridor floor tiles
adjacent to it.  Currently no zone covers that area, so it is solid wall.
Depending on arm position the quadrant can be 4–6 tiles tall × 5–7 tiles wide
— conspicuous wasted space.

---

## Fix A — orient by required exits

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

If the required exits don't match any pair, fall back to `rng.choice`.

---

## Fix B — extend Zone B into the empty quadrant

The empty quadrant is always on the "inside corner" of the L — the side
opposite to where both arms extend.  The zone that is **adjacent** to the
empty quadrant (Zone B, a vertical band alongside the v-arm) currently starts
at the h-arm row.  Extending Zone B to start at `MIN_R` (instead of `cor_row`)
allows rooms packed into it to cover the full height including the empty corner.

The rooms in the extended part (above the h-arm) share a wall with the v-arm
at col `cor_col ± 1`, in the rows where the v-arm exists.  `derive_walls` finds
that connection tile and punches a door there.  The room's floor extends into
the former empty corner and the player can explore it through that door.

Concretely, for each orientation, extend Zone B's `band_row` to `MIN_R` (or
`band_end` to `MAX_R`) so it spans the full height or width of that strip:

| Orientation | Zone B before         | Zone B after (extended)         |
|-------------|-----------------------|---------------------------------|
| `bl`        | rows `MIN_R` → `cor_row+arm_h-1`  | rows `MIN_R` → `MAX_R`  |
| `br`        | rows `MIN_R` → `cor_row+arm_h-1`  | rows `MIN_R` → `MAX_R`  |
| `tl`        | rows `cor_row` → `MAX_R`          | rows `MIN_R` → `MAX_R`  |
| `tr`        | rows `cor_row` → `MAX_R`          | rows `MIN_R` → `MAX_R`  |

(For `bl`/`br` the extension is downward; for `tl`/`tr` upward.)

---

## Files

- `levellayout.py` — `_layout_l`, `_layout_for_strategy`, `layout_graph`
- `levellayout.py` — `_build_super_grid`: compute and pass `required_exits`

---

## Done when

- [ ] `poe test` passes
- [ ] L-corridor arms are always at the required border sides (confirmed by
      inspecting levels that trigger the `l` strategy)
- [ ] No large empty corner visible in the L-corridor layout (user confirmed)
