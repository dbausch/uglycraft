# L-Corridor Orientation and Corner Gaps

## Status

- [ ] L-corridor orientation chosen to match required BORDER exit sides
- [ ] Empty quadrant minimised: only unavoidable inaccessible corner remains

---

## Problem A — wrong orientation

`_layout_l` picks one of `['bl', 'br', 'tl', 'tr']` at random.  Each
orientation exposes exits at a different pair of grid borders:

| Orientation | arm exits     |
|-------------|---------------|
| `bl`        | top + right   |
| `br`        | top + left    |
| `tl`        | bottom + right|
| `tr`        | bottom + left |

When `_pick_strategy` selects `'l'` for a corridor that needs, say,
`exits = {'left', 'top'}`, `_layout_l` might produce `'tl'` (bottom + right),
placing corridor floor tiles on the wrong borders.  The stitch then fails (or
the fallback to `z` always fires), and the intended L-shape is never used.

---

## Problem B — large empty quadrant

The L-shape always leaves one rectangular quadrant of the grid with no corridor
floor tiles adjacent to it.  Rooms cannot be placed there (no shared wall to
connect through), so the area is solid wall.  Depending on arm positions the
empty quadrant can be 4–6 tiles tall × 6–8 tiles wide — conspicuous empty space.

---

## Fix A — orient by required exits

`_layout_l` receives `edge_map` but not the required exit sides.  The call
chain is:

```
build_level_dict → layout_graph → _layout_for_strategy → _layout_l
```

Pass `required_exits: frozenset` through the call chain so `_layout_l` can
choose the orientation that places arms at the required borders:

```python
_EXIT_PAIR_TO_ORIENTATION = {
    frozenset({'top',    'right'}) : 'bl',
    frozenset({'top',    'left'})  : 'br',
    frozenset({'bottom', 'right'}) : 'tl',
    frozenset({'bottom', 'left'})  : 'tr',
}
```

If the required exits don't match any pair (no exits, or a non-perpendicular
pair), fall back to `rng.choice`.

---

## Fix B — minimise empty quadrant

Once the orientation is exit-driven, the empty quadrant is always the "inside
corner" of the L.  Make it small by placing the bend near the inside-corner
border: for `br` (exits top+left) the empty quadrant is bottom-right, so push
the bend toward the bottom-right (high `frac_r`, high `frac` for `br`).

Specifically, adjust `frac` and `frac_r` for each orientation so the empty
quadrant is ≤ 3 tiles in each dimension:

| Orientation | frac (h-arm col)   | frac_r (v-arm row) |
|-------------|--------------------|--------------------|
| `bl`        | keep 0.20–0.30     | keep 0.55–0.70     |
| `br`        | keep 0.70–0.80     | keep 0.55–0.70     |
| `tl`        | keep 0.20–0.30     | change to 0.30–0.45|
| `tr`        | keep 0.70–0.80     | change to 0.30–0.45|

(`tl`/`tr` previously used 0.55–0.70 which placed the h-arm too low, leaving
3–5 empty rows at the top of the grid.)

---

## Files

- `levellayout.py` — `_layout_for_strategy`, `layout_graph`, `_layout_l`
- `levellayout.py` — `_build_super_grid`: pass `required_exits` per corridor

---

## Done when

- [ ] `poe test` passes
- [ ] L-corridor arms are always at the required border sides (confirmed by
      running levels that trigger the `l` strategy)
- [ ] Empty corner area is visually small (user confirmed)
