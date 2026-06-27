# Layout Rework: T-shape and Chain

## Status

- [ ] T: spine floated off the grid border; rooms in a fourth zone above/below the bar
- [ ] T: stem extends to the border when the opposite zone is empty
- [ ] Chain: redesigned to eliminate stone-waste quadrants

---

## T-shape: two problems

### Problem 1 — Spine against the border

For `down`, the spine is at rows [1, arm_h] — against the top border.  No
room zone exists above it; that entire strip is stone.  Symmetric for the
other three orientations.

### Problem 2 — Stem stops mid-grid

When z3 (below the stem for `down`) receives no room — because the zone is
too small, or all rooms went to z1/z2 — the stem terminates at `r_stem_end`
and the column below it is stone all the way to the border.

---

## T-shape: proposed fixes

### Fix A — Float the spine

The spine shifts 2–4 tiles away from the border, opening a new room zone
(`z_near`) between the border and the spine.

For `down` (shown; other orientations are symmetric):

```
row 1  ──────────────────  ← grid border
       z_near (full width, 2-4 rows tall)
row 5  ══════════════════  ← spine (moved inward by 2-4 rows)
       │ stem │
       │ stem │
       ┴──────┴  ← or extends to border (Fix B)
```

| Zone   | Contents                        | Pack fn             |
|--------|---------------------------------|---------------------|
| z_near | rows [MIN_R, spine-2], full width | `_pack_band`      |
| z1     | left of stem, rows [spine+arm_h+1, MAX_R] | `_pack_band` |
| z2     | right of stem, same rows        | `_pack_band`        |
| z3     | below stem end                  | `_pack_band_vertical` |

Room distribution: z_near and z3 each get ≤1 room (tip zones with
single-wall adjacency); z1 and z2 split the rest round-robin.

**Parameters:**
```python
spine_inset = rng.randint(2, 4)          # rows between border and spine top
r_spine = MIN_R + spine_inset            # first row of spine
```

z_near connects to the spine via the wall row `r_spine - 1`, which is
adjacent to the spine's top edge (all full-width rooms in z_near share
that wall row). ✓

### Fix B — Stem extends to the border when z3 is empty

After zone packing: if no room landed in z3, extend the corridor's
`floor_tiles` from `r_stem_end + 1` to `MAX_R` at the stem columns.

The effect: the corridor fills the empty stone column.  No stone pillar,
no separate room — just continuous corridor floor reaching the border.

Implementation: after band packing check `placed` for any node that
occupies rows inside the z3 band.  If none, append stem extension tiles
to the corridor's `floor_tiles`.

---

## Chain: what it currently is

`_layout_chain` creates a compact rectangular hub (4–8 × 3–5 tiles)
centered on the grid and extends four narrow bands outward:

```
      [ROOM]
      [ROOM]
[RM] [HUB ] [RM]
      [ROOM]
      [ROOM]
```

Each band is restricted to the hub's width or height.  The four
corner quadrants (NW, NE, SW, SE) are completely stone.  With the hub
covering ~6 of 28 columns, each lateral band uses only 22 % of grid
width — the rest is waste.

---

## Chain: three options

### Option A — Widen the bands (minimal change)

Extend the four bands to the full available area:

- Above hub: full width `[MIN_C, MAX_C]`, rows `[MIN_R, hub_row-2]`
- Below hub: full width, rows `[hub_row+hub_h+1, MAX_R]`
- Left of hub: full height `[MIN_R, MAX_R]`, cols `[MIN_C, hub_col-2]`
- Right of hub: full height, cols `[hub_col+hub_w+1, MAX_C]`

**Problem:** rooms placed LEFT of the hub's column range in the "above"
or "below" band have no shared boundary with the hub — only the
hub's top/bottom edge is adjacent, and only in the hub's column range.
This breaks `validate_layout` for rooms placed outside hub columns.

Fix: restrict above/below bands to hub columns (current behavior) but
use `_pack_band_vertical` stacking multiple rooms there; use full-height
left/right bands.  Stone waste is reduced in corners but not eliminated.

### Option B — Full-cross hub (merge into cross)

The hub arms extend to the grid borders, making the corridor a true `+`
shape.  Rooms pack into 4 large corner zones — identical to the `cross`
strategy.  Chain and cross become the same thing; remove one.

### Option C — Z-corridor (new distinct shape)

The corridor forms a Z or S:

```
═══════════════════  ← top arm (full width)
                │
                │  ← bridge (short vertical on the right)
                │
═══════════════════  ← bottom arm (full width)
```

Three room zones:
- **Left strip**: left of bridge, between the two arms — large rectangle
- **Right strip**: right of bridge (above top arm and below bottom arm,
  split by the bridge) — two narrow bands
- (Optional) rooms above top arm / below bottom arm if arms are inset

The Z is visually distinct from cross, T, and L.  Both Z and S variants
(bridge on left or right) chosen randomly.

### Option D — Drop chain

Remove `chain` from `STRATEGIES`.  The problem it was designed to solve
(hub-style junction) is better served by `cross` or the reworked `t`.

---

## Open questions for refinement

1. **T z_near size**: should the spine inset be 2–4 rows (tight, room fits
   snugly above spine) or wider?  A larger inset means a taller z_near but
   a shorter area for z1/z2.

2. **T distribution**: z_near and z3 each get 1 room.  With only 4 total
   rooms, this leaves 2 rooms for z1 and z2 combined — each gets 1.  Is
   that acceptable, or should z_near sometimes get 0 rooms so z1/z2 get
   more variety?

3. **Chain direction**: Option A (reduce waste, keep hub), B (merge with
   cross), C (new Z shape), or D (drop it)?

---

## Done when

- [ ] `poe test` passes
- [ ] `poe run --level 12`: T-shape visible with rooms in all four zones,
  no large stone quadrant above/below the spine
- [ ] `poe run --level 12`: T stem touches the grid border (or a room
  occupies the stem-end zone)
- [ ] Chain (if kept): no stone-waste quadrants; visually distinct from cross
