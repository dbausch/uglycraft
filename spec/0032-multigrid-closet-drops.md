# Spec 0032 — Closet redesign: multi-grid inclusion + carved-from-room closets (BL-23)

## Status

- [ ] C1 — Generation: each room independently gets **at most one** closet with
      **~10%** probability (replaces `closet_count`)
- [ ] C2 — A closet is **carved from the room's own tiles** (never extends the
      room footprint), as one of three types: **back office**, **side office**,
      **corner toilet**
- [ ] C3 — Sizing: **offices ≈ 33%** of the room's tiles; **toilets ≈ 20%** and
      **near-square**; rounded to fit, respecting the 1-tile wall gap and a
      1-tile minimum toilet (2×2 footprint incl. its L-wall)
- [ ] C4 — The closet **type is chosen at layout** from the options actually
      buildable for the room's geometry (corridor-edge ≥ 3 tiles → any type;
      == 2 → back office only)
- [ ] C5 — The closet door connects to the **ROOM**, never the corridor; doors
      are cut **after** closets are defined
- [ ] C6 — Multi-grid: closets are copied into per-grid subgraphs (they are no
      longer omitted and dropped)
- [ ] C7 — Item spill **closet → room → corridor → `LayoutError`**; a closet
      that cannot be built spills its content to room/corridor; a closet push
      puzzle that cannot live in the room is **elided together with its gate**
- [ ] C8 — No content is silently dropped; `scratchpad/diag_drops.py` shows 0
      closet drops; regression tests assert it
- [ ] C9 — `poe test` green

## Investigation (why nodes were lost)

Diagnostic (40 seeds × 10 real Act 2 sets): **434 / 6617 nodes dropped; 432 are
CLOSETS** (298 held content). Focused check: multi-grid drops **100%** of
closets, single-grid **0%**. Root cause: `_build_super_grid._build_subgraph`
copies only the corridor's direct room neighbours; a closet attaches to a *room*,
so it is never copied into any subgraph → dropped (C6 fixes this). Attempting to
place them then exposed that the old `_nest_closets` notch geometry is fragile —
carving can delete the parent's connection tile, two closets collide, and the
`_place_closet_adjacent` fallback abuts other rooms. This spec **replaces** the
old notch/closet scheme with the carved-from-room design below.

## Design

Common setup for the diagrams: room floor cols 4–9 × rows 2–5, corridor along the
bottom (row 7); the room's **door edge** is its bottom (corridor-facing) edge.
`.` room floor · `k` closet floor · `#` wall · `+` cut door · `C` corridor.

### C1 — Generation

In `LevelGraph.generate` / the builder, drop `closet_count`. After the rooms are
added, **each room** rolls independently: with probability `_CLOSET_PROB ≈ 0.10`
add exactly one closet node attached to it (edge room→closet, OPEN). A room thus
has zero or one closet. The closet node still carries content (treasures /
materials / keys / plate+block) like any node.

### C2/C3/C5 — Three closet types (carved from the room)

**(a) Back office** — one wall **parallel** to the door edge; closet = the back
strip. Consumes depth (rows); the corridor edge stays fully free. **≈ 33%** of
room tiles (full width × depth ≈ H/3, ≥ 1, leaving the room a corridor-adjacent row).

```
      4 5 6 7 8 9
row2  k k k k k k     closet (back strip)
row3  # # + # # #     NEW wall ∥ door edge; + = closet↔ROOM door
row4  . . . . . .     room (front)
row5  . . . . . .
row6  # # # + # #     room↔corridor door — any of cols 4–9
row7  C C C C C C
```

**(b) Side office** — one wall **perpendicular** to the door edge; closet = a
full-depth side block. **≈ 33%** (depth × width ≈ W/3). Reduces the room's
corridor-door columns; the closet's corridor-facing tiles stay walled (no
corridor door for the closet).

```
      4 5 6 7 8 9
row2  k k # . . .
row3  k k # . . .     closet = side block (cols 4–5)
row4  k k + . . .     + = closet↔ROOM door
row5  k k # . . .
row6  # # # + # #     room↔corridor door — only cols 7–9
row7  C C C C C C
```

**(c) Corner toilet** — a near-square block in a corner, enclosed by an **L of
two wall segments sharing the corner cell**, then one arm cut as the door.
**≈ 20%**, near-square (e.g. 6×4 room → ~5 tiles → 2×2). Minimum 1 tile → 2×2
footprint (toilet + 3-tile L-wall, one of which becomes the door). At a
corridor-facing corner it costs one door column; at a back corner it does not
affect the door.

```
      4 5 6 7 8 9
row2  . . . . . .
row3  . . . . . .     room
row4  . . . . # #     L-wall: corner (8,4) + arm (9,4)
row5  . . . . + k     arm (8,5) cut as closet↔ROOM door; toilet = (9,5)
row6  # # # + # #     room↔corridor door — cols 4–7
row7  C C C C C C
```

In all three, the dividing tiles are wall by construction (interior non-floor →
wall in `derive_walls`), so the room↔closet edge yields **exactly one** door, cut
into the **room** (C5), and the closet shares **zero** passages with the corridor
(R-E3). Doors are cut by `derive_walls` after the closet floor sets are fixed.

### C4 — Buildable-option selection (at layout)

Let `E` = the count of room floor tiles along the corridor-facing edge.
- `E ≥ 3` → all three types are normally buildable; pick one (random among the
  buildable set, honouring the C3 sizing).
- `E == 2` → only **back office** (it consumes depth, not corridor-edge width).
- A type is buildable only if its carve leaves the room (i) with ≥ 1 corridor-edge
  tile for its own door, (ii) connected, and (iii) each part ≥ its minimum. If no
  type is buildable, the closet is treated as "cannot be built" (see C7).

### C6 — Multi-grid inclusion

In `_build_subgraph`, after adding the corridor's room neighbours, BFS over
non-BORDER, non-corridor edges from those rooms to also add their closets (with
the room↔closet edge and a full item copy). Then per-grid layout carves them.

### C7 — Item placement and fallbacks

- **Spill order for a closet's items:** closet tiles → its room → the corridor →
  `LayoutError` (mirrors the room→corridor spill from spec 0029/0030, with the
  closet as the innermost level).
- **Closet that cannot be built** (no buildable type, C4): the closet contributes
  no floor; its items spill to the room, then the corridor. We want this to be
  rare — log/measure it (diagnostic) to understand when it happens.
- **A closet push puzzle** (plate+block intended for the closet) that cannot be
  placed in the closet is first retried in the **room**; if it cannot be solvable
  there either, the puzzle is **elided together with its gate** (the gated edge
  becomes an open passage, plate+block removed) — consistent with spec 0030's
  "barrier exists only if its prerequisite is on the floor".
- No content-bearing node is silently dropped: if content cannot be placed
  anywhere (closet→room→corridor all full), raise `LayoutError` to regenerate.

## Verification

- `scratchpad/diag_drops.py`: dropped closets → 0; content drops → 0.
- pytest (`tests/test_node_drops.py`): closets survive at grid counts 1..N; no
  content-bearing node dropped across single- and multi-grid feature sets;
  closet doors connect to the room (closet shares 0 passages with the corridor);
  every built level still passes `validate_layout` / `validate_push_puzzles` (via
  successful `build_level_dict`).

## Done when:

- [ ] C1 — One closet per room at ~10%; `closet_count` removed.
- [ ] C2/C3 — Closets carved from room tiles as back/side office (~33%) or corner
      toilet (~20%, near-square); never extend the footprint.
- [ ] C4 — Type picked from buildable options; `E==2` → back office only.
- [ ] C5 — Closet door connects to the room; closet shares 0 corridor passages.
- [ ] C6 — Closets present in multi-grid levels (0 dropped at all grid counts).
- [ ] C7 — Spill closet→room→corridor→`LayoutError`; unbuildable closet/puzzle
      handled (puzzle elided with its gate); no content silently dropped.
- [ ] C8/C9 — Regression tests + `diag_drops` confirm 0 closet/content drops;
      `poe test` green.
