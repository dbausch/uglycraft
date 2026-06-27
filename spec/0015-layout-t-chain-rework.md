# Layout Rework: T-shape and Z-shape (replaces chain)

## Status

- [ ] T: spine repositioned to the centre area; rooms above the spine as well as on both sides of the stem
- [ ] T: stem extends to the border when the tip zone is empty
- [ ] Z: new corridor layout replacing chain; 4 variants (Z, S, rotated-Z, rotated-S)

---

## T-shape: what makes it distinct

A T corridor is a **horizontal spine** plus a **vertical stem**.  When the
spine sits in the middle of the grid (same position `_layout_horizontal` uses)
rooms can appear both above the spine and on either side of the stem below it.
The stem is the only thing that makes T different from horizontal.

```
┌────────────────────────────┐
│  z_top  (above spine)      │
├────────────────────────────┤
│          SPINE             │  ← full-width horizontal arm,
├────────────┬───┬───────────┤     positioned like _layout_horizontal
│  z_left    │ S │  z_right  │
│            │ T │           │
│            │ E │           │
│            │ M │           │
│            └───┘           │  ← or continues to border
└────────────────────────────┘
```

The spine position is chosen the same way as in `_layout_horizontal`:
randomly in the centre third of the grid.  `_layout_t` is therefore a
strict superset of `_layout_horizontal` — it adds a stem and two extra
zones.

### Zone table (orientation: `down`)

| Zone    | Rows                         | Cols                       | Pack fn              |
|---------|------------------------------|----------------------------|----------------------|
| z_top   | [MIN_R, r_spine−2]           | [MIN_C, MAX_C]             | `_pack_band`         |
| z_left  | [r_spine+arm_h+1, MAX_R]     | [MIN_C, c_stem−2]          | `_pack_band`         |
| z_right | [r_spine+arm_h+1, MAX_R]     | [c_stem+arm_w+1, MAX_C]    | `_pack_band`         |
| z_bot   | tip: bottom of stem, ≤1 room | [c_stem, c_stem+arm_w−1]   | `_pack_band_vertical`|

z_top and z_bot each get **at most 1 room** (single-wall-adjacency tip
zones).  z_left and z_right split the remaining rooms round-robin.

### Spine placement

The spine row is chosen the same way `_layout_horizontal` picks its
corridor row: randomly within the centre third of the grid interior.
This guarantees z_top has enough height to hold at least one room.

### Stem placement

The stem column is chosen randomly within the spine, as today.

### Stem extension

After zone packing: if no room was placed in z_bot, extend the corridor's
`floor_tiles` from `r_stem_end + 1` to `MAX_R` at the stem columns.

Implementation: after band packing, test whether any key in `placed`
(other than the corridor) has its top row inside the z_bot band.  If not,
append the extension tiles to `placed[corridor_name]`.

### Other orientations

`up`, `right`, `left` are symmetric.  For `up` the spine is near the
bottom; z_top becomes z_bot and vice versa.  For `right`/`left` the
roles of rows and columns swap throughout.

---

## Z-shape: new corridor layout (replaces chain)

### Concept

The corridor forms a **Z** (or **S**, or their 90° rotations) shape: two
full-length arms connected by a short perpendicular bridge on one side.
The bridge splits the space between the arms into a large zone and a small
zone.

```
Horizontal Z               Horizontal S
═══════════════════        ═══════════════════
               │           │
               │           │
═══════════════════        ═══════════════════
(bridge on right)          (bridge on left)

Vertical Z                 Vertical S
║                          ║
║──────────────            ──────────────║
║                          ║
(bridge at bottom-right)   (bridge at top-left)
```

All four variants are valid; chosen randomly at generation time.

### Geometry (horizontal Z — bridge on right)

```
row r_top ── ══════════════════════════════ ← top arm (arm_h rows, full width)
                                     │
                                     │  ← bridge (arm_w cols)
                                     │
row r_bot ── ══════════════════════════════ ← bottom arm (arm_h rows, full width)
```

| Symbol     | Value                                                   |
|------------|---------------------------------------------------------|
| `r_top`    | `MIN_R` (top arm flush with top border)                 |
| `r_bot`    | `MAX_R − arm_h + 1` (bottom arm flush with bottom border)|
| `arm_h`    | `rng.randint(2, 3)`                                     |
| `c_bridge` | `MAX_C − arm_w + 1` for Z; `MIN_C` for S                |
| `arm_w`    | `rng.randint(3, 5)`                                     |

### Room zones (horizontal Z)

| Zone    | Rows                      | Cols                        | Pack fn              |
|---------|---------------------------|-----------------------------|----------------------|
| z_main  | [r_top+arm_h+1, r_bot−2]  | [MIN_C, c_bridge−2]         | `_pack_band`         |
| z_side  | [r_top+arm_h+1, r_bot−2]  | [c_bridge+arm_w+1, MAX_C]   | `_pack_band_vertical`|

z_main is the large zone (left of bridge for Z; right for S).
z_side is the narrow sliver on the other side of the bridge.

Arms are flush with the borders so no zones exist above or below them.

**Connectivity**: rooms in z_main connect to the top or bottom arm via
their top/bottom boundary row.  Rooms in z_side connect to the bridge via
their left/right boundary column.

**Room distribution**: z_main takes all rooms; z_side gets at most 1.

### Vertical Z/S (rotated variants)

Left and right arms run the full height at the left and right borders.
The bridge is a horizontal band.

| Symbol     | Value                                                   |
|------------|---------------------------------------------------------|
| `c_left`   | `MIN_C`; `c_right = MAX_C − arm_w + 1`                 |
| `arm_w`    | `rng.randint(2, 3)` (arm width)                         |
| `r_bridge` | `MAX_R − arm_h + 1` for rotated-Z; `MIN_R` for rotated-S|
| `arm_h`    | `rng.randint(3, 5)` (bridge height)                     |

Zones mirror the horizontal case: z_main above or below the bridge,
z_side on the other side.

### Strategy name and config

- New strategy key: `'z'`
- Add `'z'` to `VALID_STRATEGIES` in `levellayout.py`
- Remove `'chain'` from all `layout_strategies` lists in `levels.py`
- Add `'z'` to the same lists

---

## Open questions

1. **T z_top height**: with the spine in the centre third, z_top is
   approximately INT_H/3 − 2 rows ≈ 2–4 rows.  Is that reliably enough
   to fit one room, or should there be an explicit minimum height check
   before assigning a room to z_top?

2. **Z z_side**: z_side is as wide as the gap between the bridge and the
   border (arm_w = 3–5 cols wide).  Should z_side sometimes get 0 rooms
   (when the gap is too small for MIN_W) rather than always attempting to
   fill it?

---

## Done when

- [ ] `poe test` passes
- [ ] T `down`/`up`: rooms visible above the spine AND on both sides of the stem; stem reaches the border when z_bot is empty
- [ ] T `right`/`left`: same, symmetrically
- [ ] Z/S layout visible in game: large zone on one side of bridge, narrow zone on the other; no stone-waste quadrants
- [ ] All four Z variants (Z, S, rotated-Z, rotated-S) reachable in generation
- [ ] `'chain'` removed from all level configs; `'z'` added
