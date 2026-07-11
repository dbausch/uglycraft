# 0053 — Entrance / player-start anchoring via grid zero (BL-31)

## Status

- [x] Multi-grid graphs place grid zero at the super-grid origin `(0,0)`;
      the spanning tree never occupies it
- [x] Start grid sits at `delta(S)` with entrance side `opposite(S)`; its
      entrance side never carries a BORDER edge
- [x] Start-grid layout covers the entrance side; entrance placed there,
      player start on the corridor tile inside
- [x] `_pick_entrance` col-0 fallback deleted (replaced by a LayoutError guard)
- [x] Property tests: entrance side free of BORDER exits; entrance
      border-placed and adjacent to `player_start`; `player_start`
      corridor-owned
- [x] Golden trace `act2_L13_walk` re-baselined (multi-grid rng stream shifts)
- [x] Sweep re-run shows 0 adjacency violations (was 6/150)

## Problem

BL-31: the level entrance must sit next to a corridor tile, and that corridor
tile must be the player start — on a side of its own, not beside a locked or
gated border door.

`_pick_entrance` (levellayout.py:225) handles this correctly only when the
start grid has a border side free of BORDER exits. When every side the
corridor reaches is BORDER-occupied (e.g. a `horizontal` spine with exits
left and right), a fallback forces the entrance to `(0, row)` — typically
13–14 tiles from the player start, embedded beside an unrelated room.
Measured on 15 seeds × levels 11–20: **6 / 150 levels (4 %)**, all
multi-grid. The player start itself is corridor-owned in both paths
(0 violations).

The root cause is structural: nothing reserves a free side for the entrance,
so no local placement rule can fix it. The fix reserves one at graph
generation time.

## Design: grid zero

The outside of the dungeon is modelled as **grid zero** — the super-grid
origin `(0,0)`. For now it is empty, invisible, and non-reachable: no `Node`,
no `Edge`, nothing placed or rendered there, and the entrance border tile
stays solid wall (the entrance is a sprite, `game.py:499`). R-P3 / R-T4 /
playability validation are untouched because the room graph gains no members.

### At graph generation (`LevelGraph.generate`, multi-grid only)

1. Grid zero occupies `(0,0)` and draws its **pseudo-exit side**
   `S ∈ {left, top, bottom, right}` with the graph rng.
2. The start grid sits at the non-zero cell `delta(S)` — the spanning-tree
   root position — and its entrance side is `opposite(S)`, the face looking
   back at grid zero. The root corridor's `super_pos` is set to `delta(S)`
   explicitly (today the root implicitly keeps the default `(0,0)`).
3. `_spanning_tree` gains a `blocked` parameter (here `{(0,0)}`) checked on
   **every** Prim step: the frontier may approach the origin from any
   direction later in the growth, and every such proposal is skipped. No
   dungeon grid can ever occupy grid zero, and consequently **no BORDER edge
   can ever exist on the entrance side** (a BORDER edge on that face would
   require a grid at exactly `(0,0)`).
4. Record `graph.entrance_side` for the layout stage.

Consequence: the start grid has at most **3** BORDER exits. Trees of any grid
count still span — the infinite grid minus one cell stays connected.

### At layout (`_build_super_grid` / `build_level_dict`)

1. `required_sides[start corridor] += entrance_side` — strategy selection
   (`_pick_strategy`) must cover it, and R-S1 then guarantees the corridor
   reaches that side. With 3 BORDER exits + entrance this means all 4 sides →
   `full_border` (existing filter handles it).
2. `build_level_dict` receives `entrance_side` for the start grid and passes
   it to `_pick_entrance`, which places the entrance **deterministically on
   that side**: centre-most on-side corridor tile = `player_start`, border
   tile directly outside = `entrance`. No side scanning, no `occupied_sides`.
3. The col-0 fallback is **deleted**. If the corridor does not reach the
   entrance side (impossible per R-S1), raise `LayoutError` (fresh-seed
   retry) instead of silently misplacing the entrance.
4. Non-start grids keep the current scanning behaviour solely to derive the
   corridor enemy-distance reference tile (`player_pos` → `MIN_ENEMY_DIST`
   in `_place_items_in_room`); its result is never surfaced as an entrance.
   Unchanged, so enemy placement streams stay stable.

### Single-grid levels

Unchanged: with no BORDER edges nothing is occupied, so the existing main
path already yields an adjacent, corridor-owned pair on a free side, and the
fallback is unreachable. No rng draw is added for `grid_count == 1`, keeping
the `act2_L11_walk` golden stable.

### Future extension (out of scope, design must not preclude it)

Grid zero may later become a real place: the entrance door could open once a
condition is met — e.g. all loot collected — giving way to the outside, and
grid zero could host a per-level boss arena. The design keeps that path open:

- Grid zero has a fixed cell (`(0,0)`) and a recorded pseudo-exit side, so a
  future spec can generate a real grid there and stitch it like any other.
- The entrance sits at a border-face position exactly like a stitch opening,
  so upgrading it to a real transition is the existing mechanism: an
  `exits[f'{entrance_side}_{pos}']` entry pointing at a grid-zero room,
  plus a condition-gated barrier instead of solid wall.

Nothing in this spec may hard-code "the entrance is decorative" beyond the
current sprite rendering.

## Geometry

Super-grid view (pseudo-exit side `S = bottom` drawn, so the start grid sits
at `(0,1)` with entrance side `top`):

```
super-grid    (0,0)
             ┌──────┐
             │  Z   │   grid zero = the origin: never built, never reachable,
      ┌──────┼──────┼──────┐   no BORDER edge may cross this face
      │ g2   │ START│ g1   │
      │(-1,1)│ (0,1)│ (1,1)│   START's BORDER exits: left + right only
      └──────┴──────┴──────┘   top face carries the entrance exclusively
```

In-grid view of START (entrance side `top`, corridor stem band at cols
13–14; centre-most on-side tile for `(MIN_C+MAX_C)//2 = 14` is col 14):

```
col:    0 1 .......... 12 13 14 15 .......... 29
row 0:  # # .......... #  #  E  # ........... #    E = entrance (14, 0)
row 1:  # . . room ... #  c  P  # ... room ... #    P = player start (14, 1)
                          ↑  ↑ corridor stem tiles (c)
        Manhattan distance E↔P = 1; border tile E stays solid wall (sprite only)
```

Adjacency, corridor ownership, and "no barrier door on the entrance side" all
hold **by construction**: the entrance side has no BORDER edge, hence no
opening and no locked/gated border door anywhere on that face.

## Golden-trace impact

Drawing the pseudo-exit side (multi-grid only) prepends one rng draw, and the
blocked origin changes spanning-tree growth: every multi-grid generation
stream shifts. `act2_L13_walk` (level 13, seed 777, 3 grids) must be
re-baselined. `act2_L11_walk` (single-grid) keeps its stream.

## Tests (red first)

New `tests/test_entrance.py`:

1. **Graph property** (hypothesis over seeds, `grid_count` 3–8): generate,
   read `graph.entrance_side` and the start corridor's BORDER edge sides —
   the entrance side must not be among them, and no corridor node may sit at
   `(0,0)`. Red today (`entrance_side` does not exist — API pin).
2. **Level property** (same builds, retry helper style from
   `test_border_continuity.py`), for the start grid:
   - `entrance` on the border ring, Manhattan distance 1 to `player_start`,
   - `tile_owner[player_start]` is the corridor node,
   - no key in `rooms[start]['exits']` names the entrance side, and no
     locked door / gate sits on any border tile of the entrance side.
   Red today at ~4 % incidence; pin at least one failing seed from the sweep
   (e.g. seed 4 / level 13 shape) as a deterministic regression case.
3. **Sweep** — re-run the BL-31 detector (15 seeds × levels 11–20): 0
   violations on all three checks (pre-fix: 6 adjacency violations).
4. `poe test` green, including re-baselined `act2_L13_walk`.

## Done when:

- [x] Multi-grid graphs reserve grid zero at `(0,0)`; the start grid sits at
      `delta(S)` and never has a BORDER edge on `graph.entrance_side`
      (a8e5997; confirmed by Daniel 2026-07-12)
- [x] Start-grid entrance placed on the entrance side, player start on the
      adjacent corridor tile (both properties hold across the test sweep)
      (a8e5997)
- [x] `_pick_entrance` col-0 fallback removed; LayoutError guard in place
      (a8e5997)
- [x] New tests red before the fix, green after; `poe test` exits 0
      (ffdbf12 red, a8e5997 green; suite 531 passed — `act2_L13_walk`
      per-process flake is pre-existing BL-40, not introduced here)
- [x] `act2_L13_walk` golden re-baselined; `act2_L11_walk` byte-identical
      (a8e5997)
- [x] Detector sweep shows 0/150 violations (was 6/150)
- [x] BL-31 closed in `kb/backlog.md`; kb updated (`kb/architecture.md`
      entrance selection + grid zero; R-T6 in `kb/requirements.md`)
      (9c3c185 + closure commit)
