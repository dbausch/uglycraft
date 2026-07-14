# 0076 — Exploded block respawns onto a random free tile inside the safe area (BL-55)

## Status

- [ ] `_block_respawn_tile` no longer prefers the block's **home/start** tile.
      A detonated block respawns on a **random free tile inside the room's safe
      area** (`room.safe_tile_set`), so it can never reappear on an unsafe tile
- [ ] "Free" = not `blocked` (walls, unbridged water, another block) **and** not
      the player's tile — the block never materialises on the player or another
      block (enemies never share a push-puzzle room, R-P9)
- [ ] Degenerate fallback (should never fire in a one-block puzzle): if **no**
      safe tile is free, keep the block where it is rather than force it onto an
      unsafe tile — it stays put and re-explodes on the next push, never landing
      somewhere doomed
- [ ] `spec 0068` test `test_detonate_deducts_500_and_respawns` updated: assert
      the respawn tile is inside `room.safe_tile_set`, free, and not the player's
      tile (no longer literally `(3, 2)`)
- [ ] New world test: with the **home tile free**, detonate repeatedly and
      assert the block still lands only on safe/free tiles (proves home is no
      longer special-cased and unsafe tiles are never chosen)
- [ ] New world test: **home tile occupied by the player**, detonate; assert the
      respawn tile is inside the safe area (the old nearest-open BFS could pick
      an unsafe neighbour — this is the reported bug)
- [ ] `poe test` exits 0; any affected golden deliberately re-recorded and the
      diff reviewed
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

- **Which safe area?** The room's union `safe_tile_set` (= `World._safe_tiles`) —
  the same set that `_light_doomed_fuses` uses to decide doom. This keeps
  respawn and doom detection on one definition: a block is safe iff it is in the
  union, so respawning into the union guarantees the block is *not* immediately
  doomed. (Blocks are not paired to individual plates in the model — spec 0068
  §"Room invariant" / levellayout.py — so "its own plate's safe tiles" is not
  available anyway.)
- **The plate tile is eligible.** It is inside the safe area, and a block landing
  on it simply solves that puzzle. This is harmless (the fuse already cost the
  player 500 points and 5 s, and the tile is one of several chosen at random —
  not an exploit) and keeps the rule "the whole safe area" literal.
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
    """A random free tile inside the room's safe area (spec 0076 / BL-55).
    Free = not blocked (walls / water / another block) and not the player's
    tile.  Falls back to the block's current tile only if the safe area has no
    free tile (degenerate; never happens with one block per puzzle room)."""
    player = (self.player.col, self.player.row)
    candidates = sorted(
        t for t in self._safe_tiles
        if not self.blocked(*t) and t != player)
    if candidates:
        return random.choice(candidates)
    return (b.col, b.row)                            # doomed-but-inert fallback
```

Note `self.blocked(*t)` treats the *currently detonating* block `b` as blocked at
its present (unsafe) tile — that tile is outside the safe area, so it is not a
candidate anyway; no self-exclusion special-case is needed. Other blocks on safe
tiles are correctly excluded.

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
- **New behaviour:** candidates = safe ∧ free ∧ not `P`
  = `{(2,2), (4,2), (2,3), (3,3), (4,3)}` — every one an `S`/`T` tile. A random
  pick always lands the block back inside the safe area. ✔

(When home *is* free, home is just one of the candidates, no longer preferred —
the block may land on any free safe tile.)

## Tests (world-level, pygame-free)

Update / add in `tests/test_exploding_blocks.py`:

- **`test_detonate_deducts_500_and_respawns` (update):** keep the −500 / event
  assertions; replace `block_positions() == [(3, 2)]` with: the single block
  position is `in w.room.safe_tile_set`, `not w.blocked(*pos)`, and
  `!= (player.col, player.row)`.
- **`test_respawn_lands_in_safe_area_home_free` (new):** player parked off the
  safe area; detonate; assert respawn tile ∈ safe area and free. (Home free —
  proves home isn't special and unsafe tiles are never chosen.)
- **`test_respawn_avoids_unsafe_when_home_blocked` (new):** player on the block's
  home tile (3,2) (the reported bug); detonate; assert respawn tile ∈ safe area,
  free, and ≠ player — i.e. never an `x` tile.

The existing `random.seed(seed)` in `_world` makes `random.choice` deterministic
per test, but the assertions check the *invariant* (inside safe area, free), not
a specific tile, so they don't hard-code the seeded draw.

## Manual verification

- `poe run` an Act 2 push-puzzle level. Stand the player on the block's start
  tile, push the block out of the tinted safe area, and wait for the blast → the
  block reappears on a **tinted** tile, never on plain floor.
- Repeat a few times → it lands on different safe tiles (random), not always its
  original home.

## Done when:

- [ ] `_block_respawn_tile` returns a random free tile inside `room.safe_tile_set`
      (sorted candidates → `random.choice`), never preferring home, never an
      unsafe tile; degenerate fallback keeps the block on its current tile
- [ ] "Free" excludes blocked tiles and the player's tile; the block never lands
      on the player or another block
- [ ] `test_detonate_deducts_500_and_respawns` updated to assert the safe-area
      invariant; two new tests cover home-free and home-blocked (the reported
      bug), red before the change and green after
- [ ] `poe test` exits 0; any affected golden re-recorded and reviewed
- [ ] User confirms in-game: an exploded block always reappears on a tinted
      (safe) tile, including when the player stands on its start tile (manual
      acceptance)
