# 0076 — Exploded block respawns onto a random free tile inside the safe area (BL-55)

## Status

- [x] `_block_respawn_tile` no longer prefers the block's **home/start** tile.
      A detonated block respawns on a **random free tile inside the safe area of
      its own room**, so it can never reappear on an unsafe tile (a37fe3a)
- [x] Candidates are confined to the block's **own room** (`safe_tile_set` ∩
      `_room_floor(b)`, same `tile_owner`): a `Room` spans a whole grid whose
      `safe_tile_set` unions every plate, so an unconfined draw could teleport
      the block into a different, disconnected room and strand the puzzle — the
      reported cross-room bug
- [x] "Free" = not `blocked` (walls, unbridged water, another block) **and** not
      the player's tile — the block never materialises on the player or another
      block (enemies never share a push-puzzle room, R-P9) (a37fe3a)
- [x] **Plate tiles excluded from the normal candidate set**: a respawn never
      solves the puzzle for free. A plate tile is used **only as a last resort**
      when no non-plate safe tile is free (a very small room) (a37fe3a)
- [x] Degenerate fallback (should never fire in a one-block puzzle): if **no**
      safe tile is free at all, keep the block where it is rather than force it
      onto an unsafe tile — it stays put and re-explodes on the next push, never
      landing somewhere doomed (a37fe3a)
- [x] `spec 0068` test `test_detonate_deducts_500_and_respawns` updated: assert
      the respawn tile is inside `room.safe_tile_set`, free, and not the player's
      tile (no longer literally `(3, 2)`) (a37fe3a)
- [x] New world test: with the **home tile free**, detonate repeatedly and
      assert the block still lands only on safe/free tiles (proves home is no
      longer special-cased and unsafe tiles are never chosen) (a37fe3a)
- [x] New world test: **home tile occupied by the player**, detonate; assert the
      respawn tile is inside the safe area (the old nearest-open BFS could pick
      an unsafe neighbour — this is the reported bug); red before, green after
      (a37fe3a)
- [x] `poe test` exits 0; no golden affected (886 passed) (a37fe3a)
- [ ] Manual check: push a block out of the safe area, let it explode with the
      player standing on the block's start tile → it reappears on a tinted (safe)
      tile, never on a plain/unsafe tile (user acceptance)

## Problem

Spec 0068 (BL-37) respawns a detonated block at its **start tile** if free, else
the **nearest open tile** found by BFS from the start (`_block_respawn_tile`,
world.py:810). The BFS floods outward over *any* walkable tile and does **not**
restrict itself to the safe area. So when the start tile is occupied — most
commonly because the **player is standing on it** at detonation — the block can
respawn on a tile *outside* the safe area.

A block on an unsafe tile is a broken state: the puzzle is no longer solvable
from there, yet no fuse is lit (fuses only ignite on a *push*, and the respawn
sets `fuse = None`), so the block just sits there, doomed and inert, until the
player pushes it again. A tester reported exactly this: an exploded block landing
on an unsafe tile. (BL-55.)

The BFS also *prefers* the home tile, which is a second, milder wart: the fix
brief (Daniel) asks that an exploded block no longer return to its original home
at all, but pick a fresh random safe tile each time.

## Decision (Daniel, BL-55 fix hint)

Change the respawn algorithm so a detonated block **respawns to a completely
random free tile within the safe area**, no longer preferring or returning to its
home tile. The chosen tile must be free (not blocked, not the player's tile) and
inside `room.safe_tile_set`.

- **Which safe area?** The safe tiles of the block's **own room**, i.e.
  `safe_tile_set` intersected with the block's own room floor
  (`World._room_floor(b)`, same `tile_owner`). A `Room` object spans a whole
  grid of several disconnected rooms, and `safe_tile_set` (= `World._safe_tiles`)
  unions **every** plate across them; drawing from the raw union lets a block
  teleport into an unrelated, disconnected room and strand its puzzle — the
  reported cross-room bug (Daniel). Confining the draw to the block's own room
  floor keeps it where it belongs. This still respects doom detection: a block
  is confined to its own room floor when pushed (`_try_push_block`), so its
  own-room safe tiles are exactly the tiles from which its puzzle stays solvable.
  (Blocks are not paired to individual plates — spec 0068 §"Room invariant" —
  but each plate's `safe_tiles` lie entirely within its own room floor, so the
  own-room intersection picks out just the block's own plate's safe tiles.)
- **The plate tile is a last resort, not a normal target (Daniel).** A block
  landing on its plate solves the puzzle, so we don't want an explosion to hand
  that out casually. Exclude every plate tile from the primary candidate set;
  fall back to including plate tiles only when no *non-plate* safe tile is free —
  which can happen in a very small room where the plate is the only free safe
  tile.
- **Randomness source.** Reuse the module-level `random` already used for
  treasure/enemy respawn (world.py:648, 923); pick with `random.choice` over the
  **sorted** candidate list so set-iteration order never feeds the draw
  (process-determinism rule, kb/architecture.md "Process determinism" / BL-40).
- **Degenerate fallback.** If no safe tile is free (all occupied by the player /
  other blocks — cannot happen with one block per puzzle room, but guard it):
  leave the block on its current tile. It is doomed-but-inert exactly as before
  the push; the next push re-ignites it. We never force it onto an unsafe tile.

## Design

`_detonate_block` is unchanged except that it no longer passes `home` as a
preference — it asks for a random safe tile. `_block_respawn_tile(home)` is
replaced by `_block_respawn_tile(b)` (or keeps the `home` name but ignores it for
the primary path):

```python
def _detonate_block(self, b):
    self.score = max(0, self.score - BLOCK_EXPLOSION_PENALTY)
    self._emit('block_exploded', b.col, b.row)     # burst at the OLD position
    b.col, b.row = self._block_respawn_tile(b)
    b.fuse = None

def _block_respawn_tile(self, b):
    """A random free tile inside the safe area of the block's OWN room, avoiding
    plate tiles unless nothing else is free (spec 0076 / BL-55).  Free = not
    blocked (walls / water / another block) and not the player's tile.  Falls
    back to the block's current tile only if its room's safe area has no free
    tile at all (degenerate; never happens with one block per puzzle room)."""
    player = (self.player.col, self.player.row)
    own_room = self._room_floor(b.col, b.row)       # same tile_owner as the block
    plates = {pos for pos, _ in self.room.cells.fixtures_of_kind('plate')}
    free = [t for t in self._safe_tiles
            if t in own_room and not self.blocked(*t) and t != player]
    non_plate = sorted(t for t in free if t not in plates)
    if non_plate:
        return random.choice(non_plate)             # normal path
    if free:
        return random.choice(sorted(free))          # tiny room: plate last resort
    return (b.col, b.row)                            # doomed-but-inert fallback
```

`own_room = self._room_floor(b.col, b.row)` is the set of floor tiles sharing the
block's `tile_owner`; intersecting the grid-wide `safe_tile_set` with it keeps the
respawn inside the block's own room (the cross-room fix). `self.blocked(*t)`
treats the *currently detonating* block `b` as blocked at its present (unsafe)
tile — outside the safe set anyway, so no self-exclusion special-case is needed.
Other blocks on safe tiles are correctly excluded. Plate positions come from
`room.cells.fixtures_of_kind('plate')` (the same source as `plate.safe_tiles`).

`self._safe_tiles` is `room.safe_tile_set` (spec 0068), the union of every
plate's `safe_tiles`. For a non-puzzle room it is empty, but a block only exists
where a plate does, and a block on a plate never fuses, so detonation only ever
runs in a room whose safe set is non-empty.

### Geometry (confirm before code — geometry rule)

Fixture `_puzzle_level` (tests/test_exploding_blocks.py), spec 0068 diagram (1):
a 4×3 room, plate `T` at (2,2), block start at (3,2). Legend: `T` plate (safe),
`S` safe floor, `x` unsafe floor, `P` the player.

Safe area = `{(2,2), (3,2), (4,2), (2,3), (3,3), (4,3)}`.

**Reported bug — player on the block's start tile.** The block has been pushed to
the unsafe far column (5,2) and fused; the player stands on the block's home
(3,2). At detonation:

```
     c2 c3 c4 c5
  r2  T  P  S  b        b = fused block at (5,2), about to explode
  r3  S  S  S  x
  r4  x  x  x  x
```

- **Old behaviour:** home (3,2) is occupied by `P`, so the BFS floods from (3,2)
  to the nearest open tile — which can be an **`x`** tile → block respawns unsafe.
- **New behaviour:** non-plate candidates = safe ∧ free ∧ not `P` ∧ not a plate
  = `{(4,2), (2,3), (3,3), (4,3)}` — every one an `S` tile (the plate `T` at
  (2,2) is excluded). A random pick always lands the block on a safe, non-plate
  tile. ✔ The plate `(2,2)` would only be chosen if those four were all
  occupied — impossible in this fixture, but the last-resort path for a room so
  small that the plate is the only free safe tile.

(When home *is* free, home is just one of the non-plate candidates, no longer
preferred — the block may land on any free non-plate safe tile.)

## Tests (world-level, pygame-free)

Update / add in `tests/test_exploding_blocks.py`:

- **`test_detonate_deducts_500_and_respawns` (update):** keep the −500 / event
  assertions; replace `block_positions() == [(3, 2)]` with: the single block
  position is `in w.room.safe_tile_set`, `not w.blocked(*pos)`,
  `!= (player.col, player.row)`, and **not the plate tile** `(2, 2)`.
- **`test_respawn_lands_in_safe_area_home_free` (new):** player parked off the
  safe area; detonate; assert respawn tile ∈ safe area, free, and **not the
  plate**. (Home free — proves home isn't special and unsafe/plate tiles are
  never chosen on the normal path.)
- **`test_respawn_avoids_unsafe_when_home_blocked` (new):** player on the block's
  home tile (3,2) (the reported bug); detonate; assert respawn tile ∈ safe area,
  free, ≠ player, and ≠ the plate — i.e. never an `x` tile and not a free win.
- **`test_respawn_uses_plate_only_as_last_resort` (new):** a minimal fixture
  whose safe area is just the plate `T` plus one `S` tile; occupy the lone `S`
  (place a second block there, or stand the player on it) so the only free safe
  tile is the plate; detonate and assert the block lands **on the plate** —
  proving the plate is used when, and only when, nothing else is free.
- **`test_respawn_stays_in_the_blocks_own_room` (new):** a grid (one `Room`)
  holding two walled-apart puzzle rooms A and B; `safe_tile_set` spans both.
  Detonate a block in room A (with A's lone non-plate safe tile occupied so a
  raw-union draw would pick a room-B tile); assert the block respawns inside
  room A and never in room B. Red before the cross-room fix (respawned to a
  room-B tile), green after.

The existing `random.seed(seed)` in `_world` makes `random.choice` deterministic
per test, but the first three assertions check the *invariant* (inside safe area,
free, not plate), not a specific tile, so they don't hard-code the seeded draw.

## Manual verification

- `poe run` an Act 2 push-puzzle level. Stand the player on the block's start
  tile, push the block out of the tinted safe area, and wait for the blast → the
  block reappears on a **tinted** tile, never on plain floor.
- Repeat a few times → it lands on different safe tiles (random), not always its
  original home.

## Done when:

- [x] `_block_respawn_tile` returns a random free **non-plate** tile inside the
      safe area of the block's **own room** (`safe_tile_set` ∩ `_room_floor(b)`;
      sorted candidates → `random.choice`), never preferring home, never an
      unsafe tile, never a different room; a plate tile is used only when no
      non-plate safe tile is free; degenerate fallback keeps the block put
      (a37fe3a, cross-room fix pending commit)
- [x] "Free" excludes blocked tiles and the player's tile; the block never lands
      on the player or another block (a37fe3a)
- [x] `test_detonate_deducts_500_and_respawns` updated to assert the safe-area /
      non-plate invariant; four new tests cover home-free, home-blocked (the
      reported bug), plate-only-as-last-resort, and the cross-room case — red
      before, green after (a37fe3a + cross-room fix)
- [x] `poe test` exits 0; no golden affected (886 passed) (a37fe3a)
- [ ] User confirms in-game: an exploded block always reappears on a tinted
      (safe) tile, including when the player stands on its start tile (manual
      acceptance)
