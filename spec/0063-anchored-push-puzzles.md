# 0063 — Push puzzles anchored to the player's real entry (BL-45)

## Status

> **Confirmed working (accepted via validated sweep, 2026-07-12).** Red
> tests 18f1ccc, implementation b0e86bd, detector 3a57580+grid-wide fix,
> kb 9bd7b82, acceptance amendment 1e3f770. Sweep: 14 landing + 5
> entry-unsolvable in 120 pre-fix levels, 0 post-fix; goldens
> byte-identical; timing within budget (L20 worst 2.35 s); suite 667
> passed.

- [x] Red tests: pinned BL-45 reproduction (anchored solver rejects the
      2-high forced-push room; the unanchored one accepted it); no block
      start on a doorway landing tile (property over generated levels)
- [x] `_sokoban_bfs` starts from anchor zones only (no
      try-every-component); `_place_puzzle` accepts a block start only if
      its forward-start player zone contains the corridor anchor;
      `validate_push_puzzles` anchors at the plate room's doorways
- [x] Block starts excluded from doorway landing tiles (R-P7 mirror)
- [x] Detector sweep (anchored-solver replica + landing-tile check):
      violations found pre-fix or the pinned case stands as the red
      witness; 0 violations post-fix across ≥ 120 levels
- [x] Goldens re-recorded once with reviewed diffs (gated levels' pair
      pools shrink → rng streams shift); generation time re-measured
- [x] `poe test` exits 0
- [x] KB updated (R-P11 in `kb/requirements.md`; solver section in
      `kb/architecture.md`); BL-45 closed
- [x] Acceptance by validated sweep (statistical-sweep practice, Daniel
      2026-07-12): the defect is too rare (~19 hits / 120 levels
      pre-fix) for a play-test to verify its absence — the detector,
      validated against the pre-fix commit, stands in for it

## Problem

Play (Daniel, 2026-07-12, BL-45): an unsolvable level. A 2-row room
entered from the top; the block sits directly inside the entrance (on
its landing tile), the plate in the same top row further right:

```
Wall:                      #### #######
1st row of the room        #   B   P  #
2nd (last row of the room) #          #
Wall:                      ############

B = Moveable Block, P = Push Plate
```

Entering forces a push (the only way in is through B's tile), shoving B
into the bottom row, where it can never be pushed back up (no standing
row below) — the plate is unreachable. `_verify_blocks` stays blind
(the block keeps free left/right axes).

### Root cause: the solvers have no player anchor

All three solver layers in `levellayout.py` treat the player's starting
position as free, when in reality the player always arrives **from the
corridor, through a doorway**:

1. **`_sokoban_bfs`** tries *every* connected component as a player
   start (`for ps in player_candidates`) — including the room interior
   that is only reachable *through* the block. For the BL-45 room it
   finds the push-right chain from the interior component and reports
   solvable; the real player can never stand there.
2. **`_place_puzzle`'s backward BFS** explores `(block, player_zone)`
   states correctly but accepts every reached block start
   (`found[old_block] = new_state`) without checking that the required
   forward-start zone (`new_state`'s zone) is the one containing the
   corridor. The BL-45 pair was accepted exactly this way.
3. **`_puzzle_candidates`** (fast pre-filter) checks pusher tiles are
   passable, never reachable — harmless as an over-approximation, but
   nothing downstream corrected it.

Spec 0060's smaller rooms (2-high rooms are common now) made the shape
frequent enough to meet in play.

## Design

### D1 — anchored solvability (the fix)

A push puzzle counts as solvable only if a player starting **outside
the plate room** can execute it:

- `_sokoban_bfs(block_start, target, passable, dead_squares, anchors)`:
  the try-every-component loop is replaced by start zones derived from
  `anchors` — the normalized components of the given anchor tiles with
  the block in place. No anchor zone ⇒ unsolvable.
- `_place_puzzle`: a block start `B` is recorded only when the state's
  forward-start player zone equals `get_zone(anchor, B)`, where the
  anchor is any corridor floor tile of the grid (the corridor is in
  `passable` and is where the player always arrives; every doorway
  hangs off it). The backward BFS still explores all zones — the
  anchor only gates acceptance into `found`.
- `validate_push_puzzles` / `_can_push_block_to`: anchors are the plate
  room's doorway tiles (passage tiles adjacent to its floor — already
  part of the movement bounds). Any doorway may be the player's entry,
  so each is a valid anchor; none solvable ⇒ error, as before.

Dead-square computation stays anchor-free (a sound over-approximation).

### D2 — blocks never start on doorway landing tiles (R-P7 mirror)

Even when solvable, a block on a landing tile means the first entry is
a forced, surprising push. `_place_puzzle` gets `block_excluded`: the
same landing-tile set spec 0049 computes for plates
(`_plate_exclusions` — existing doorways/doors/gates/breakable
boundaries and buildable water flanks) now also excludes **block
starts** (solution paths may still cross those tiles; only the initial
position is barred). This alone would have prevented the observed
shape; D1 closes the whole class (e.g. blocks on articulation tiles of
carved L-shaped rooms).

### RNG / golden / performance impact

The pair pool per plate shrinks (anchored acceptance + landing-tile
exclusion), so `rng.choice(pairs)` draws differ: generation streams
shift for every gated level — re-record the affected Act 2 goldens once
(level 13 has gates; level 11 has none and must stay byte-identical).
Rejection may raise `LayoutError` retries slightly; re-run
`scratchpad/time_generation.py` and compare against the 0060 baseline
(level 20 worst 1.50 s, budget 12 s).

### New invariant (kb/requirements.md)

**R-P11** Every push puzzle is solvable by a player entering the plate
room from the corridor side (anchored player zone), and no pushable
block starts on a landing tile (R-P7's set). Enforced at placement
(`_place_puzzle`) and re-checked at validation
(`validate_push_puzzles`), both anchored.

## Verification (tests red-first after spec confirmation)

1. **Pinned BL-45 reproduction** (unit-level, synthetic tiles): build
   the diagram's room as a passable set + plate + block on the entrance
   landing tile; assert the anchored `_sokoban_bfs` (anchor = the
   doorway) returns False — red today, where the unanchored solver
   returns True. A second synthetic case that IS solvable from the
   doorway must stay True (no over-rejection).
2. **Landing-tile property**: over generated gated levels (the
   spec-0058 build cache), no `pushable_blocks` entry sits on a landing
   tile of its room. Red today (statistically).
3. **Anchored-validation property**: `validate_push_puzzles` (anchored)
   returns `[]` for every generated level — via the existing suite
   sweeps; the pre-fix detector replica must flag ≥ 1 generated level
   across a wide sweep, or failing that the pinned case is the red
   witness (the BL-45 shape occurred in production play).
4. **Sweep**: scratchpad detector (anchored re-validation +
   landing-tile check) over ≥ 120 levels — 0 violations post-fix.
5. Goldens re-recorded once (L11 byte-identical); timing re-measured;
   full `poe test` green.

## Done when:

- [x] Pinned reproduction red→green; solvable control case never
      rejected
- [x] No block start on a landing tile across generated levels
- [x] Anchored validation green suite-wide; detector sweep 0 violations
      across ≥ 120 levels
- [x] Goldens re-recorded once with reviewed diffs; L11 byte-identical;
      timing within the 0060 budget
- [x] `poe test` exits 0
- [x] R-P11 in `kb/requirements.md`; `kb/architecture.md` solver notes
      updated; BL-45 closed in `kb/backlog.md`
- [x] Accepted via the validated detector sweep (in lieu of a play-test
      — rare generative property, statistical-sweep practice): pre-fix
      14 landing + 5 entry-unsolvable in 120 levels, post-fix 0
