# 0053 — Entrance / player-start anchoring via reserved grid zero (BL-31)

## Status

- [ ] Graph generation reserves an entrance side on the start grid ("grid
      zero" super-grid cell blocked for the spanning tree)
- [ ] Start-grid layout must cover the entrance side; entrance placed there,
      player start on the corridor tile inside
- [ ] `_pick_entrance` col-0 fallback deleted (replaced by a LayoutError guard)
- [ ] Property tests: entrance side carries no BORDER exit; entrance is
      border-placed, adjacent to `player_start`; `player_start` corridor-owned
- [ ] Golden trace `act2_L13_walk` re-baselined (multi-grid rng stream shifts)
- [ ] Sweep re-run shows 0 adjacency violations (was 6/150)

## Problem

BL-31: the level entrance must be created next to a corridor tile, and that
corridor tile must be the player start.

`_pick_entrance` (levellayout.py:225) has two paths:

- **Main path** — already correct: walks sides in order (left, top, bottom,
  right), skips sides occupied by BORDER exits, and on the first side the
  corridor reaches picks the centre-most on-side corridor tile as
  `player_start` and the border tile directly outside as `entrance`.
- **Fallback** — fires when *every* side the corridor reaches is occupied by
  a BORDER exit (e.g. a `horizontal` spine with BORDER exits left and right,
  or a 4-exit start grid). It returns
  `(0, any_tile[1]), any_tile` with `any_tile` = topmost-leftmost corridor
  tile — the entrance lands on the left border regardless of where the player
  starts, typically 13–14 tiles away, embedded next to an unrelated room.

Measured incidence (15 seeds × levels 11–20 = 150 generated levels):

| Check | Violations |
|---|---|
| entrance cardinally adjacent to player_start | **6 / 150 (4 %)** |
| player_start corridor-owned | 0 |
| entrance collides with a border-exit tile | 0 |

All six failures were multi-grid start grids (3–8 grids) whose corridor's
reachable sides were all BORDER-occupied.

**Rejected approach (rev 1 of this spec):** keep the entrance on an occupied
side, anchored at the low end of the corridor's face band so it cannot collide
with the stitch opening. Rejected by Daniel: an always-open entrance door
sitting beside a locked/gated border door on the same face is unrealistic.
The entrance must live on a side that carries **no** BORDER exit at all —
which requires forcing the layout and the spanning-tree branching to keep one
side of the start grid free.

## Design: reserved entrance side ("grid zero")

Concept: the outside of the dungeon is modelled as a virtual pre-start grid
**zero** — a super-grid cell adjacent to the start grid that is *reserved,
empty, invisible, and non-reachable*. It exists only as a blocked cell in the
spanning tree plus a recorded side; no `Node`, no `Edge`, nothing is ever
placed, rendered, or reachable there (the entrance border tile stays solid
wall; the entrance is a sprite, `game.py:499`). R-P3/R-T4/playability
validation are untouched because the room graph gains no members.

### At graph generation (`LevelGraph.generate`, multi-grid only)

1. Grid zero **is the super-grid origin `(0,0)`** — the outside of the
   dungeon. Draw its pseudo-exit side `S` ∈ {left, top, bottom, right} with
   the graph rng.
2. The start grid sits at the non-zero cell `delta(S)` (the spanning-tree
   root position), and its entrance side is `opposite(S)` — the face looking
   back at grid zero. The root corridor's `super_pos` is set to `delta(S)`
   explicitly (today the root implicitly keeps the default `(0,0)`).
3. `_spanning_tree` gains a `blocked` parameter (here `{(0,0)}`) checked on
   **every** Prim step, not only the root's children: the frontier may
   approach the origin from any direction later in the growth, and every such
   proposal is skipped. No dungeon grid can ever occupy grid zero, and
   consequently **no BORDER edge can ever exist on the entrance side** (a
   BORDER edge on that face would require a grid at exactly `(0,0)`).
4. Record `graph.entrance_side` for the layout stage.

Consequence: the start grid has at most **3** BORDER exits (root branching
capped at 3). Trees of any grid count still span — the infinite grid minus
one cell stays connected.

### At layout (`_build_super_grid` / `build_level_dict`)

1. `required_sides[start corridor] += entrance_side` — strategy selection
   (`_pick_strategy`) must cover it and R-S1 then guarantees the corridor
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
   corridor enemy-distance reference tile (`player_pos` →
   `MIN_ENEMY_DIST` in `_place_items_in_room`); its result is never surfaced
   as an entrance. Unchanged, so enemy placement streams stay stable.

### Single-grid levels

Unchanged. With no BORDER edges nothing is occupied, so the existing main
path already yields an adjacent, corridor-owned pair on a free side, and the
fallback is unreachable. (Full uniformity — reserving an entrance side even
for `grid_count == 1` — was considered and dropped: it would constrain the
already-trimmed strategy lists of levels 11–13 for no observable gain, and
would invalidate the single-grid golden trace `act2_L11_walk` too.)

## Geometry

Super-grid view (grid zero at the origin; pseudo-exit side `S = bottom`
drawn, so the start grid sits at `(0,1)` with entrance side `top`):

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

Before (the bug this replaces): same layout, but left+right occupied and top
not required ⇒ a horizontal-spine start grid reaches no free side ⇒ fallback
puts `E` at `(0, 1)` — 14 tiles from `P`, beside a room, on a face that may
carry a locked border door.

Adjacency, corridor ownership, and "no barrier door on the entrance side" all
hold **by construction**: the entrance side has no BORDER edge, hence no
opening and no locked/gated border door anywhere on that face.

## Golden-trace impact

Drawing `entrance_side` (multi-grid only) prepends one rng draw and the
blocked cell changes spanning-tree growth: every multi-grid generation stream
shifts. `act2_L13_walk` (level 13, seed 777, 3 grids) must be re-baselined.
`act2_L11_walk` (single-grid) keeps its stream: no draw is added for
`grid_count == 1`.

## Tests (red first)

New `tests/test_entrance.py`:

1. **Graph property** (hypothesis over seeds, `grid_count` 3–8): generate,
   read `graph.entrance_side` and the start corridor's BORDER edge sides —
   the entrance side must not be among them, and no corridor node may sit at
   grid zero's cell. Red today (`entrance_side` does not exist — API pin).
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

- [ ] Multi-grid graphs reserve grid zero; start grid never has a BORDER
      edge on `graph.entrance_side`
- [ ] Start-grid entrance placed on the entrance side, player start on the
      adjacent corridor tile (both properties hold across the test sweep)
- [ ] `_pick_entrance` col-0 fallback removed; LayoutError guard in place
- [ ] New tests red before the fix, green after; `poe test` exits 0
- [ ] `act2_L13_walk` golden re-baselined; `act2_L11_walk` byte-identical
- [ ] Detector sweep shows 0/150 violations
- [ ] BL-31 closed in `kb/backlog.md`; kb updated (`kb/architecture.md`
      entrance selection; new invariant in `kb/requirements.md`)
