# 0033 — Corridors continue across BORDER edges (BL-29)

## Status

- [x] **Stems unified to width 2–5** (was 3–5) so a stem can reproduce any narrow
      band — commit `0e8d284`. *Spines kept at 2–3 for now: widening them regresses
      the current closet nesting (being redesigned by another agent) and is not
      needed for band coverage — see "Spine widening deferred" below. Tracked as a
      follow-up backlog item.*
- [x] A child grid's corridor segment at the shared border face **reproduces the
      parent grid's corridor cross-section** (same rows/cols + width); arm
      strategies (z/s/l) and unhonourable bands are filtered out, `full_border` is
      the per-grid last resort — commit `a564670`
- [x] When the parent (source) grid is `full_border` (its frame covers the whole
      face), it **actively picks a varied exit band** within an attachable range
      and anchors the child to continue it — instead of always opening at grid
      centre — commit `4737109`; `test_full_border_exits_are_varied` green
- [x] The stitch chooses the border opening from **corridor** floor tiles only,
      on both endpoints — never room floor tiles — commit `a564670`
- [x] `full_border` is a per-grid last resort (not the old all-or-nothing
      whole-level rebuild) — commit `a564670`
- [x] Regression test: every BORDER opening's inner tile is corridor-owned on
      both endpoints — `tests/test_border_continuity.py`, green
- [x] Sanity: `full_border` usage across a multi-grid seed sweep stays low
      (< 30 %) — `test_full_border_usage_stays_low`, green
- [ ] User confirms a previously-unsolvable double-T entry is now solvable
      (manual play)

## Problem

A multi-grid Act 2 level was unsolvable. A `full_border` grid was exited at the
bottom; the adjacent **double-T** grid was entered at the top — but the opening
landed in the double-T's **top-right room**, not the top corridor stem. That room
was sealed by a gate whose pressure-plate puzzle sat in a *different* room of the
same grid. Entering the sealed room from outside, the player could not reach the
plate, so the gate never opened: hard soft-lock.

### Root cause (two coupled defects)

**Defect A — stitch picks any floor tile, not the corridor.**
`_build_super_grid` (`levellayout.py`) stitches each BORDER edge by intersecting
the floor rows/cols both grids reach at the shared border face, then opening the
wall at the middle shared position:

```python
rows_a = {r for (c, r) in room_a['tile_owner'] if c == col_a}
rows_b = {r for (c, r) in room_b['tile_owner'] if c == col_b}
shared = sorted(rows_a & rows_b)
pos = shared[len(shared) // 2]
```

`tile_owner` maps **every** floor tile to its node — corridor *and* rooms. When a
room reaches the border face (it legitimately can — see diagram), the middle
shared position can fall inside that room, punching the inter-grid opening into a
room instead of the corridor.

**Defect B — grids are laid out independently, so corridors don't align.**
Each grid is built with no knowledge of its neighbour, so the two corridors reach
the shared face at unrelated positions (grid A's spine at rows 7–8, grid B's at
rows 2–3). They coincide only ~67 % of the time. The corridors must be made to
**continue across the border by construction**, not merely overlap.

The architecture doc already *describes* the intended behaviour as "the
intersection of floor rows/cols that both **corridor** floor sets reach" — neither
the continuation nor the corridor restriction was actually implemented.

## Blast radius (measured)

Headless scan, 280 multi-grid builds over the crowded locked/water feature sets
(`scan_border.py`, `scan_fallback.py`, job tmp dir):

| Border side | openings on corridor | openings in a ROOM (mis-targeted) |
|-------------|---------------------:|----------------------------------:|
| left        | 156 | 112 |
| right       | 156 | 112 |
| top         | 192 | 100 |
| bottom      | 172 | 120 |

≈ **40 % of all BORDER openings land in a room, on every side** — not a double-T
corner case. Any corridor-based strategy whose room zones reach a border face is
exposed. Corridor positions coincide at the face only **67.5 %** of edges without
coordination, which is why independent layout + an all-or-nothing fallback would
collapse most multi-grid levels to `full_border`.

## Geometry

Entry grid: double-T, horizontal spine at rows 7–8, one **top** (near) stem at
cols 13–15 reaching the top border-inner row. Top zones span rows 1–5, split by
the stem into a left room (cols 1–11) and a right room (cols 17–28). Interior is
cols 1–28, rows 1–14; row 0 / col 0 / col 29 / row 15 are always border wall.

Floor occupancy at the **inner-top row (row 1)** of the double-T grid — `L`=top-
left room, `C`=corridor stem, `R`=top-right room (gate-sealed), `#`=wall:

```
col:  0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 ... 28 29
row1: # L L L L L L L L L  L  L  #  C  C  C  #  R  R ...  R  #
                                   └ corridor ┘   └─ gate-sealed room ─┘
```

### BEFORE (buggy) — opening = middle of ALL entry-grid floor at row 1

```
shared cols = {1..11} ∪ {13,14,15} ∪ {17..28}     (≈ 26 columns)
pos = middle  ──►  col ~17  ──►  opens into R (sealed room)   ✗ unsolvable
```

### AFTER (fixed) — child corridor continues the parent band, opening = corridor

Parent (exit) grid's corridor reaches the shared face as a band, e.g. cols
`{13,14,15}`, width 3. The double-T (child) is laid out so its **top stem
reproduces that band exactly** — stem at cols 13–15, width 3:

```
shared cols (corridor only) = {13,14,15}
pos = middle = 14  ──►  opens into corridor stem C   ✓ solvable
```

The corridor tube runs straight through the border. The player walks down the
stem onto the spine, reaches every zone, solves the plate puzzle in the other
room, then opens the gate to `R` from inside.

## Definitions

**Corridor face band** of a placed grid at side *s*: the set of inner-line
positions whose tiles are corridor-owned — rows at `col 1`/`col COLS-2` for
left/right, cols at `row 1`/`row ROWS-2` for top/bottom. For every non-
`full_border` strategy this is a single contiguous run (a spine or one stem),
described by `(lo, width)`. For `full_border` the corridor covers the entire inner
line → treated as the sentinel **FREE** (covers any band).

**Unified segment model.** Today spines draw width 2–3 and stems draw 3–5, so a
band of width 2 can only be produced by a spine and a band of width 4–5 only by a
stem — a cross-type mismatch that forces fallback. This spec **unifies every spine
and stem (and z/s/l arm) to a single width/height range 2–5**, applied in *all*
levels (single- and multi-grid), and **widens each segment's position range** to
the full extent where the strategy's room zones still satisfy R-P4 (minimum
dims). Consequences:

- Any band width in 2–5 can be reproduced by a spine *or* a stem → strategy type
  no longer constrains width matching.
- A wider span of band positions is honorable, so most continuations fit without
  fallback.
- `full_border` keeps the **FREE** sentinel (frame covers the whole inner line).

This widens corridors and shrinks room zones somewhat; the greedy room→zone
assignment already caps and spills (R-P6, spec 0030) and `_generate_act2` retries
on `LayoutError`, so room placement stays sound — see "Invariants impact" below.

### Spine widening deferred (implementation note)

As built, **only stems are unified to 2–5; spines stay 2–3.** Widening spines to
2–5 was tried and regressed the corner-closet layouts: a wider corridor starves
the parent room's band, `_nest_closets` then fails the notch and the
`_place_closet_adjacent` fallback drops the closet into the corridor (direct
floor adjacency / multiple passages). Closets are being **redesigned by another
agent**, so spine widening is deferred to avoid colliding with that work.

It is also **not needed for continuation coverage**: left/right bands come only
from spines (so ≤ 3 anyway), and a wide (4–5) top/bottom band comes from a
**stem**, which a stem-capable child (t / double_t) reproduces. So every band a
parent can produce is reproducible by some child strategy today. Widening spines
to 2–5 (for extra strategy variety when matching) is a follow-up to land once the
closet redesign is in — tracked in the backlog.

## Fix

### Part 1 — Corridor continuation (deterministic)

Grids are built in BFS `corridor_order`, so each grid's spanning-tree **parent is
built before it** (BORDER edges form a tree — `_spanning_tree`). A non-start grid
has exactly one already-built BORDER neighbour: its parent. For child grid *B*
entered from side `eb` (= opposite of the parent's exit side `ea`):

1. Compute the parent's corridor face band on `ea`: `(lo, w)` or **FREE**.
2. **If FREE** (parent is `full_border`): build *B* with **no anchor** — its
   normal strategy and random corridor. The opening is placed at the centre of
   *B*'s own corridor face band on `eb` (corridor on both sides — the parent frame
   covers it).
3. **Else**: anchor *B* on side `eb` to `(lo, w)`. *B*'s corridor face segment on
   `eb` must occupy exactly positions `[lo, lo+w)`. Threaded as
   `corridor_anchor=(eb, lo, w)` through `build_level_dict → layout_graph → the
   chosen _layout_*`, which sets the position+width of the segment that reaches
   `eb` instead of drawing them randomly:

   | strategy | anchored side | segment set to the band (`w∈2–5`) |
   |----------|---------------|-------------------------|
   | horizontal / off_centre | left/right | spine `cor_h=w`, `cor_row=lo` |
   | vertical | top/bottom | spine `cor_w=w`, `cor_col=lo` |
   | t / double_t | left/right | spine rows = `[lo,lo+w)` |
   | t / double_t | top/bottom | the stem on `eb`: cols `[lo,lo+w)`, `stem_w=w` |
   | z·s_h | left/right | the arm reaching `eb`: rows `[lo,lo+w)` |
   | z·s_v | top/bottom | the arm reaching `eb`: cols `[lo,lo+w)` |
   | l | one lr + one tb | the arm reaching `eb` |
   | full_border | any | frame already covers it |

   With the unified 2–5 model, `w` is always in-range for the anchored segment, so
   matching never fails on width alone — only on whether position `lo` admits a
   valid layout for that strategy.

4. **Candidate filtering** (replaces independent strategy choice): build *B*'s
   strategy candidate set as those that (a) reach `eb` per `required_exits` and
   (b) admit a valid layout with the `eb`-segment fixed at `[lo, lo+w)` — i.e. the
   resulting room zones still satisfy R-P4. Incompatible strategies are filtered
   out. Pick among the survivors.
5. **Per-grid `full_border` fallback**: if the candidate set is empty (no strategy
   can place the segment at `[lo,lo+w)` without starving a required room zone),
   build *B* with `full_border`, whose frame covers every position and therefore
   continues any band. This is the only fallback and it is **per grid**, not
   whole-level. With the unified widths + widened positions this should be rare.

The start grid (i = 0) has no parent → built freely; its children continue it,
grandchildren continue children, etc.

### Part 2 — Corridor-only stitch

Restrict the stitch's candidate rows/cols to corridor-owned tiles on **both**
endpoints, via a `gname → corridor_node_name` map (`corridor_order` +
`grid_name_map`; the loop variable `corridor` is the corridor node's name and
`_build_subgraph` preserves it, so `tile_owner[corridor_tile]` equals it):

```python
rows_a = {r for (c, r) in room_a['tile_owner']
          if c == col_a and room_a['tile_owner'][(c, r)] == cor_a}
```

Part 1 makes the parent band ⊆ the child band (or one side FREE), so this
intersection is always non-empty and centred on the continued corridor; the
existing `ValueError("No shared floor …")` becomes a should-never-fire assertion.
`pos` is still the middle shared position. The single-tile opening (R-E1) and
barrier placement are unchanged. *(Open: whether to widen the opening to the full
band — deferred; 1-tile keeps R-E1.)*

## Invariants impact (`kb/requirements.md`, `kb/architecture.md`)

- **R-S1/R-S2/R-S3** (corridor reaches required sides; zones derived from corridor
  geometry) still hold — zones are recomputed from the actual chosen segment
  width/position, now from the unified 2–5 range and widened positions.
- **R-P4/R-P6** (room minimums, zone capacity) unchanged as rules, but wider
  corridors shrink zones, so `LayoutError` retries may rise slightly; the greedy
  assignment + spill (spec 0030) + `_generate_act2` retry absorb it.
- New invariant to record: **corridor continuity** — for a BORDER edge between two
  non-`full_border` grids, the two corridor face bands are identical
  (position + width). Add to `kb/requirements.md` (R-T/border section) and update
  the super-grid stitch description in `kb/architecture.md`.

## Full_border active exit position

**Problem.** An opening lands at grid centre only when the shared corridor band is
the full inner line — a **full_border ↔ full_border** edge (both corridors cover
every position → `pos = middle`). full_border↔non-full already follows the
non-full grid's narrow band. With full_border chosen fairly often (per-grid
fallback; more so until spine widening lands), many crossings cluster at centre,
making the continuation hard to see.

**Fix.** A full_border grid is no longer a passive **FREE** parent. When a child's
spanning-tree parent is `full_border`, the parent **actively chooses a varied exit
band** `(lo, w)` on the shared side, the child is anchored to continue it, and the
chosen position is recorded so the stitch uses it even when the child is also
`full_border` (otherwise that edge would re-centre).

Before / after — grid A (`full_border`) exits right into grid B; shared face =
A col 28 / B col 1; band = rows (interior rows 1–14):

```
BEFORE  (full↔full → centre)            AFTER (A picks band rows 4–5, w=2)
 row : A28  A29│B0  B1                    row : A28  A29│B0  B1
  1  :  ▓    #  │ #   ▓                     1  :  ▓    #  │ #   ▓
  4  :  ▓    #  │ #   ▓                     4  :  ▓    ▷══▷    ▓   ← opening rows 4–5
  7  :  ▓   ▷══▷    ▓     ← always row 7    5  :  ▓    ▷══▷    ▓     (B continues here)
 14  :  ▓    #  │ #   ▓                    14  :  ▓    #  │ #   ▓
```

**Attachable ranges** (so a non-full child can honour the band):
- left/right band (rows): `w = randint(2,3)`, `lo = randint(4, 12-w)` (rows ~4–10)
  — horizontal/off_centre/t/double_t spine fits with ≥2 room-rows each side.
- top/bottom band (cols): `w = randint(2,3)`, `lo = randint(7, 23-w)` (cols ~7–21)
  — guarantees the simplest top/bottom strategy (`vertical`, needs ≥5 cols each
  side) attaches; stems attach there too.

If the child's strategy still can't honour the band, the existing per-grid
candidate loop / `full_border` fallback covers it.

**Scope.** Contained to `_build_super_grid`: the anchor computation (full_border
parent → varied band instead of `None`) plus a per-edge recorded position the
stitch prefers. No strategy-function changes.

## Verification

1. **Regression test** (`tests/test_act2_solvability.py` or focused new test):
   build multi-grid levels; for every grid's `exits`, parse `side_pos`, compute
   the inner tile, assert `tile_owner[inner_tile]` is a corridor name (graph nodes
   with `NodeSize.CORRIDOR`), for both endpoints of every BORDER edge. Red before
   (~40 % violations), green after.
2. **Continuation test**: for each BORDER edge where neither grid is
   `full_border`, assert the two corridor face bands are identical (same position
   set), i.e. the corridor truly continues.
3. **Variety sanity**: over a seed sweep, assert the share of grids laid out as
   `full_border` stays low (threshold from a measured baseline).
4. `poe test` passes (no regression in existing super-grid / solvability tests).
5. **User acceptance**: the double-T entry case is solvable in actual play.

## Done when

- [x] Stems unified to width 2–5 (commit `0e8d284`). *Spines deferred — see
      "Spine widening deferred"; backlog follow-up filed.*
- [x] Child grids reproduce the parent's corridor band (position + width) at the
      shared face; FREE when parent is `full_border` (commit `a564670`).
- [x] `corridor_anchor` threaded through `build_level_dict → layout_graph → the
      spine/stem strategies`; arm strategies (z/s/l) filtered when anchored
      (commit `a564670`).
- [x] Stitch picks the opening from corridor floor tiles only, both endpoints;
      `full_border` fallback is per-grid (commit `a564670`).
- [x] Regression test (corridor-owned opening) red before (`3b65ef7`), green
      after (`a564670`).
- [x] Continuation test (parent band == child band) passes (`a564670`).
- [x] `full_border`-usage sanity check passes over the seed sweep (`a564670`).
- [x] `poe test` passes — full suite 387 passed (`a564670`).
- [ ] User confirms the double-T entry case is solvable (manual play).
