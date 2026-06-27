# Room Shapes

## Status

- [ ] L-shaped corridor (4 orientations), as a new layout strategy
- [ ] L-pair rooms: two adjacent rooms with complementary L-shapes sharing a boundary
- [ ] Corner closet: small room nested in the corner of a larger room
- [ ] Open-plan zones: deferred (requires connection model changes)

---

## Overview

The current packing system places rooms as rectangles with 1-tile wall gaps
between them.  This spec adds two kinds of non-rectangular geometry:

1. **L-shaped corridor** — the corridor node itself bends.  Four orientations;
   rooms are packed into three distinct zones around the L.

2. **Interpenetrating rooms** — two graph-adjacent rooms whose floor tiles
   partition a shared block instead of being separated by a gap.  Two
   sub-cases:
   - **L-pair**: two rooms of similar size, complementary L-shapes, placed
     side by side in a band.
   - **Corner closet**: a small room tucked into the notch carved from one
     corner of a larger room.

A third scenario (open-plan / no wall between two zones) requires changing
the single-passage connection model and is deferred.

---

## L-shaped corridor

### Shape

An L corridor has two rectangular arms joined at one corner:

```
   │ v-arm │
───┼───────┤ ← corner
   └───────────────────────┘
          h-arm
```

Four orientations (which corner the L "turns" in):

| Name    | h-arm   | v-arm   | Open quadrant |
|---------|---------|---------|---------------|
| `bl`    | bottom  | left    | bottom-right  |
| `br`    | bottom  | right   | bottom-left   |
| `tl`    | top     | left    | top-right     |
| `tr`    | top     | right   | top-left      |

### Room zones

With the corridor taking an L-shape, three zones remain for rooms:

- **Zone A**: along the h-arm on the side opposite the v-arm
  (e.g. for `bl`: above the h-arm, right of the v-arm).
- **Zone B**: along the v-arm on the side opposite the h-arm
  (e.g. for `bl`: left of the v-arm, above the h-arm row — the area
  "inside" the L that faces the open quadrant).
- **Zone C**: the open quadrant itself (neither arm covers it).

Rooms distributed round-robin across the three zones; each zone uses
`_pack_band` or `_pack_band_vertical` as appropriate.

### Parameters

```
arm_h  = rng.randint(2, 3)   # thickness of the h-arm
arm_w  = rng.randint(2, 3)   # thickness of the v-arm
# h-arm row: centre of grid vertically  (same formula as _layout_horizontal)
# v-arm col: 20-30% or 70-80% of grid width (shifted toward the chosen side)
```

### Implementation

New function `_layout_l(corridor_name, room_names, rng)`.  Orientation
chosen randomly from `['bl', 'br', 'tl', 'tr']`.

Add `'l'` to `STRATEGIES` and dispatch in `layout_graph`.

---

## L-pair rooms

### What it looks like

Two rooms placed together in the same band share a rectangular block (no
1-tile gap between them).  Their floor tiles partition the block like this
(`A` and `B` are different rooms, `|` marks the boundary wall tile):

```
AAABBB     ← top section: each room occupies its half-width
AAABBB
AAABBB
AAA|BBB    ← notch row: boundary wall tile
AAAAAAA    ← bottom section: room A extends full width
AAAAAAA
```

or (rotated — for a vertical band):

```
AAAAAA     ← left section: room A extends full height
AAAAAA
AAAAAA
AA|BBB     ← notch col: boundary wall tile
  BBBB
  BBBB
```

The two rooms share exactly one wall tile at their L-junction (used as
the connection tile for the OPEN edge between them).

### When to apply

In `_pack_band` (horizontal) and `_pack_band_vertical` (vertical), with
p ≈ 0.25, when at least two consecutive rooms both have sufficient size
(combined w ≥ 10 for h-band, combined h ≥ 8 for v-band).  Only applies
to OPEN-edge pairs (not locked/gated — those need clear single-tile doors).

### Implementation sketch

In `_pack_band` horizontal band, for rooms i and i+1:

```python
combined_w = w_i + w_j   # no gap between them
split_row  = band_row + rng.randint(band_h // 3, 2 * band_h // 3)

# Room i (L opens bottom-right):
a_tiles = ({(c, r) for c in range(col, col+combined_w)
                   for r in range(band_row, split_row)}
         | {(c, r) for c in range(col, col+w_i)
                   for r in range(split_row, band_row+band_h)})

# Room j (small rectangle in top-right + bottom-right):
b_tiles = {(c, r) for c in range(col+w_i+1, col+combined_w)
                  for r in range(split_row, band_row+band_h)}

placed[name_i] = PlacedNode(name_i, col, band_row, combined_w, band_h, floor_tiles=frozenset(a_tiles))
placed[name_j] = PlacedNode(name_j, col+w_i+1, split_row, w_j-1, band_h-split_row+band_row, floor_tiles=frozenset(b_tiles))
```

The connection tile between i and j is at `(col+w_i, split_row-1)` — the
single wall tile adjacent to both floor-tile sets.

### Constraint

The L-pair can only be generated for pairs where the graph has an OPEN
edge between the two rooms.  The packing loop must know the edge type;
`layout_graph` passes edge type info alongside room names.  If the graph
has no OPEN edge between rooms i and i+1, fall back to normal placement.

---

## Corner closet

### What it looks like

A large room has a rectangular notch cut from one corner.  A small room
(the closet) occupies that notch.  One shared wall tile is the connection
point — which may be a plain passage, a locked door, or a gate depending
on the graph edge type.  The closet is a full graph node and can contain
treasure, materials, or keys exactly like any other room.

```
LLLLLLLL
LLLLLLLL
LLLLLLLL
LLLL|CCC   ← boundary wall tile (passage / door / gate)
     CCC
     CCC
```

The large room (`L`) becomes an L-shape; the closet (`C`) is rectangular.

### Two access patterns

**From inside the large room** (edge: large_room → closet, any edge type):

```
CORRIDOR
──────────────────────────
L L L L L L L L
L L L L L L L L
L L L L | C C C   ← plain / locked / gated
         C C C
```

The closet sits in a corner that does NOT face the corridor.  The single
connection tile separates the L-area from the closet.  No direct corridor
access exists.

**From the corridor directly** (edge: corridor → closet, any edge type):

```
CORRIDOR
──────────────────────────
L L L L L L L L
L L L L L L L L
L L L   C C C
L L L   C C C     ← closet corner faces the corridor
    ────|────      ← boundary wall tile (passage / door / gate)
C O R R I D O R
```

The closet is placed in the corner of the large room that is adjacent to
the corridor's wall.  The wall tile on the existing large-room ↔ corridor
boundary (within the closet's column range) becomes the connection tile.
The large room's L-area has no edge to the closet — they share only a
physical wall on the notch sides.

### When to apply

Post-processing step `_nest_closets(placed, graph, rng)` after the
initial band packing.  Candidates: any graph-adjacent pair where room A
has w ≥ 8 and h ≥ 6, room B has w ≤ 5 and h ≤ 4.  All edge types
(OPEN, LOCKED, GATED) are eligible.

1. Determine access pattern from the graph edge direction:
   - **large_room → closet edge**: any corner of A; orient notch toward
     the L-interior.
   - **corridor → closet edge**: corner of A that is adjacent to the
     corridor's wall row/col.
2. Set notch size = (room_B.w, room_B.h) clamped to 30–45 % of each
   dimension of A.
3. Update room A's floor_tiles to remove the notch.
4. Reposition room B's PlacedNode into the notch position.
5. Compute the connection tile:
   - **large_room access**: single wall tile on the interior notch
     boundary between the L-area and the closet.
   - **corridor access**: wall tile on the existing corridor ↔ large-room
     boundary row/col, within the closet's column or row range.

This function runs before `derive_walls` so the wall map is built from
the updated floor_tiles.

---

## Open-plan zones (deferred)

Two graph-adjacent rooms with a multi-tile open boundary (no single wall
passage).  Requires changing `_find_connection_tile` to return `None` for
OPEN-edge pairs and letting the game handle free movement between adjacent
floor tiles.  Out of scope for this spec.

---

## Done when

- [ ] `poe test` passes
- [ ] `poe run --level 11`: L-corridor visible (bend clearly apparent)
- [ ] `poe run --level 13`: L-pair rooms visible (two rooms sharing a
  notched boundary)
- [ ] `poe run --level 15`: corner closet visible (small room in corner of
  large room)
- [ ] All new shapes are navigable (player can walk through all floor tiles)
- [ ] `_find_connection_tile` still finds exactly one passage per edge
