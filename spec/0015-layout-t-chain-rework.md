# Layout Rework: Generalised Corridor Layouts

## Status

- [ ] Generalised corridor function covering horizontal, T, double-T, cross
- [ ] T: spine in centre third; rooms above and below the bar; stem extends to border when tip empty
- [ ] Double-T: two stems, one on each side; 40 % chance stems align (cross-like), 60 % offset
- [ ] Cross (`_layout_cross` + `'cross'` key) removed; cross-like shapes emerge from double-T
- [ ] Z-shape: 4 variants (Z, S, rotated-Z, rotated-S); replaces chain

---

## Core insight: everything is a corridor + stems

All these layouts share one structure:

```
   ┌─────────────────────────────────────┐
   │  zone above the bar (may be split)  │
   ├─────────────────────────────────────┤
   │             C O R R I D O R        │  ← full-width band
   ├─────────────────────────────────────┤
   │  zone below the bar (may be split)  │
   └─────────────────────────────────────┘
```

A **stem** is a vertical extension of the corridor band that juts out
between two rooms on one side.  It splits that side's zone into a left
sub-zone, a right sub-zone, and a tip zone (≤1 room, directly at the
stem end).

```
   ┌──────────┬────────────────────────────┐
   │ z_top    │  ← one stem above the bar  │
   │          │      splits this side       │
   ├──────────┴──┬──────────────────────────┤
   │  C O R R   │   I D O R                │  ← full-width band
   ├─────────────┴───┬───────────────────────┤
   │  z_left         │  z_right              │  ← one stem below
   │            ┌────┘                       │
   │            │ z_bot tip (≤1 room)        │
   └────────────┴───────────────────────────┘
```

Specific layouts are configurations of this one model:

| Layout     | Stems | Notes                                               |
|------------|-------|-----------------------------------------------------|
| horizontal | 0     | 2 zones: above, below                               |
| vertical   | 0     | same, transposed                                    |
| T          | 1     | 4 zones: above, left, right, tip                    |
| double-T   | 2     | 6 zones: above-left, above-right, above-tip,        |
|            |       |           below-left, below-right, below-tip         |

---

## Generalised corridor function

A single `_layout_corridor` replaces `_layout_horizontal`, `_layout_vertical`,
and `_layout_t`.  It also generates double-T and cross.

### Parameters

```python
def _layout_corridor(
    corridor_name, room_names, rng,
    orientation='h',     # 'h' (horizontal) or 'v' (vertical)
    stems=(),            # sequence of stem specs: (side, col_frac, w_range)
    edge_map=None, node_sizes=None
):
```

| Parameter    | Meaning                                                        |
|--------------|----------------------------------------------------------------|
| `orientation`| `'h'` → spine is horizontal; `'v'` → transposed              |
| `stems`      | 0–2 specs; each: `(side, col_frac, w_range)`                  |
| `side`       | `'near'` (top for 'h') or `'far'` (bottom for 'h')            |
| `col_frac`   | float 0–1; stem centre as fraction of band width (chosen by rng if None) |
| `w_range`    | `(min_w, max_w)` for the stem width; defaults `(3, 5)`         |

### Spine placement

Same as current `_layout_horizontal`: random row within the centre third
of the grid interior (rows MIN_R+INT_H//3 … MIN_R+2*INT_H//3 − arm_h).

### Zone derivation

For a horizontal corridor with one `'far'` stem (T-down):

```
z_near  = (MIN_C, MIN_R,          INT_W,  r_spine − MIN_R − 1)   full width
z_far_L = (MIN_C, r_spine+arm_h+1, c_stem − MIN_C − 1, MAX_R − r_spine − arm_h)
z_far_R = (c_stem+stem_w+1, r_spine+arm_h+1, ..., ...)
z_far_T = (c_stem, r_stem_end+2, stem_w, MAX_R − r_stem_end − 2)   tip zone
```

Room distribution: all rooms are distributed round-robin across the
left/right sub-zones only.  Tip zones receive no pre-allocated rooms.

### Stem extension to border (always applies)

After packing the side zones, check each stem's tip band.  If any room
placed in a side zone happens to reach to the tip band (its edge is
adjacent to the stem's end), a passage is carved there naturally — but
no room is forced into the tip.  If the tip band is empty, extend the
corridor's `floor_tiles` from the stem's end to the grid border.

This means tip rooms are **optional**: they appear only when the natural
zone packing happens to place a room flush against the stem end.
Practically this will be rare; the stem almost always extends to the
border.

### Deriving specific layouts

```python
# horizontal
_layout_corridor(name, rooms, rng, orientation='h', stems=())

# vertical
_layout_corridor(name, rooms, rng, orientation='v', stems=())

# T (random side)
_layout_corridor(name, rooms, rng, orientation='h',
                 stems=[('far', None, (3,5))])

# double-T — 40 % chance stems are aligned (cross-like), 60 % offset
frac_near = rng.uniform(0.25, 0.75)
if rng.random() < 0.4:
    frac_far = frac_near                      # aligned → cross-like
else:
    frac_far = rng.uniform(0.25, 0.75)        # offset → true double-T
_layout_corridor(name, rooms, rng, orientation='h',
                 stems=[('near', frac_near, (3,5)), ('far', frac_far, (3,5))])
```

---

## Z-shape: shifted corridor

### Insight

A Z is a straight corridor where one room on the south side has been made
tall enough to push the corridor segment above it upward.  The room on the
north side of that shifted segment is consequently squeezed: shorter in
height but wider.

```
before (straight corridor):

  ┌──room A──┬─────room B─────┐   ← north side
  ╠══════════╪════════════════╣   ← corridor band
  └──room C──┴─────room D─────┘   ← south side

after (room C grows tall, pushing corridor up on the right):

  ┌──room A──┐ ┌──room B (squeezed shorter, wider)──┐   ← north side
  ╠══════════╣ ╠════════════════════════════════════╣   ← shifted right
  │          ╠═╝                                        ← bridge
  └──room C──┘                                          ← tall south room
             └──room D──┘   ← remaining south room
```

The corridor itself forms a Z (or S, depending on which side the bridge
is on).

### Geometry (horizontal Z, bridge on right)

```
row r_low ──── ══════════════════════════ ← left arm (full width, arm_h rows)
                                    │
                                    │  ← bridge (arm_w cols, connects r_low to r_high)
                                    │
row r_high ─── ══════════════════════════ ← right arm (full width, arm_h rows)
```

Arms are flush with the top and bottom borders so the corridor fills the
full height.  The bridge column is chosen randomly in the right or left
quarter of the grid.

### Room zones

| Zone    | Area                                           | Pack fn              |
|---------|------------------------------------------------|----------------------|
| z_main  | between the arms, on the large side of bridge  | `_pack_band`         |
| z_side  | between the arms, on the narrow side of bridge | `_pack_band_vertical`|

z_main takes the majority of rooms.  z_side gets ≤1 room (it is as narrow
as `MAX_C − c_bridge − arm_w`, which may be too small for any room; skip
silently in that case).

### Four variants

| Variant    | Arms          | Bridge position |
|------------|---------------|-----------------|
| Z          | horizontal    | right           |
| S          | horizontal    | left            |
| rotated-Z  | vertical      | bottom          |
| rotated-S  | vertical      | top             |

Chosen randomly at generation time.

### Strategy name

Strategy key `'z'` replaces `'chain'` in `VALID_STRATEGIES` and all
`layout_strategies` lists in `levels.py`.

---

## Migration plan

1. Implement `_layout_corridor` replacing `_layout_horizontal`, `_layout_vertical`, `_layout_t`.
2. Add `_layout_z` as a new function.
3. Dispatch in `_layout_for_strategy`: `'horizontal'`→corridor(h,0 stems), `'vertical'`→corridor(v,0 stems), `'t'`→corridor(h,1 stem), `'double_t'`→corridor(h,2 stems with biased alignment), `'z'`→z-layout.
4. Add `'double_t'` to `VALID_STRATEGIES`.
5. Remove `'chain'` and `'cross'`; add `'z'` and `'double_t'`.
6. Update `levels.py` layout strategy lists accordingly.

---

## Open questions

1. **double-T in level configs**: tip zones are optional and stems extend
   to the border when empty, so double-T works at any room count.
   Proposed: add `'double_t'` to all levels that already include `'t'`
   (levels 11 onwards).

2. **cross removed**: `_layout_cross` and the `'cross'` strategy key are
   deleted.  Cross-like shapes emerge naturally from `'double_t'` at ~40 %
   probability (biased aligned-stem roll).  No separate strategy needed.

---

## Done when

- [ ] `poe test` passes
- [ ] horizontal/vertical unchanged in appearance after refactor
- [ ] T: rooms above spine, rooms on both sides of stem, stem extends to border when z_bot empty
- [ ] double-T: two stems visible; rooms fill side zones; empty stems extend to border
- [ ] double-T aligned (cross-like): two stems at same column; rooms in 4 side zones; both stems extend to border
- [ ] Z/S/rotated visible; large z_main zone, narrow z_side; no stone waste
- [ ] `'chain'` and `'cross'` removed; `'z'` and `'double_t'` added to level configs
