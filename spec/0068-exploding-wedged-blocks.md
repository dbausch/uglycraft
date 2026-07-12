# 0068 — Doomed push-blocks explode and respawn; dead-square push allowed; on-death block reset removed (BL-37)

## Status

- [ ] Pushing a block is **no longer blocked by dead squares**: a block *may* be
      pushed onto a dead square — the consequence is that it now *ignites*
      (Daniel). The `_dead_squares` push guard in `_try_push_block` is removed
- [ ] A block **can never be pushed off its room's floor tiles** (Daniel):
      confinement to the block's own room (via `tile_owner`; Act 1 = the whole
      interior). This keeps a block in its puzzle
- [ ] Detection is a **static dead-square membership check** (Daniel): the
      safe/dead partition is fixed (single block, confined to its room,
      temporary obstacles ignored), so **no per-push recomputation** is needed —
      after a push, a block whose tile is in the room's precomputed dead-square
      set (dead *with respect to the plate*) is doomed and ignites
- [ ] Detection reuses the generator's precomputed `room.dead_squares`
      (reverse-reachability from all plates, permanent walls only —
      levellayout.py:1688/2916), exposed on `World` as `_dead_squares`
- [ ] A block **on a plate is never dead** (a plate is a reverse-flood target,
      never in the dead set) — the goal-state exclusion, for free
- [ ] **Floor tinting is reversed** (Daniel): the floor pattern now marks the
      **safe** tiles (a puzzle room's floor minus its dead squares), not the
      dead ones
- [ ] Fuse is **per-push, non-cancelling** (Decision 1): a lit fuse always
      detonates; it is not re-evaluated or cancelled
- [ ] Each exploding block **deducts `BLOCK_EXPLOSION_PENALTY` (500) points**
      (Daniel), floored at 0 — mirrors `LIFE_PENALTY`
- [ ] On detonation the block respawns at its **start tile** if free, else at
      the **nearest open tile** (Decision 4); it never materialises on the
      player or another block (enemies never share a push-puzzle room — R-P9)
- [ ] `World.update` gains a **block-fuse system** slotted explicitly into the
      pinned system order (spec 0052 G5); the contract note is updated
- [ ] Two new world events — `block_fuse_lit` and `block_exploded` — mapped to
      new SFX in `game.py`; the fuse and explosion are drawn (animated
      countdown on the tile, then a burst)
- [ ] The **on-death `_reset_blocks` path is removed** (Decision 6): dying no
      longer resets blocks or closes plate-gates; `_lose_life` keeps the spec
      0067 player + enemy reset. Gates self-correct via the per-tick latch; the
      open entrance persists because `_channels` is left untouched on death
- [ ] `_reset_blocks` and its four locking tests (`test_registry`,
      `test_rooms`, `test_dispatch`, `test_entrance_exit`) are removed or
      rewritten to the new behaviour; entrance-persists-across-death is re-pinned
- [ ] New tests red before the change, green after; `poe test` exits 0 with any
      affected goldens deliberately re-recorded
- [ ] Manual check: push a block onto a dead square → it counts down, deducts
      500, explodes, and respawns at its start; a block can't be pushed out of
      its room; the safe tiles are the tinted ones; die on a solved grid → the
      solved puzzle is preserved (user acceptance)

## Problem

Today a block pushed toward a tile from which the puzzle becomes unsolvable is
*prevented* from moving there (`_try_push_block` refuses dead squares), and a
genuinely wedged block just stays wedged. The only recovery is death, which
triggers `_reset_blocks` (world.py:708) — a blunt instrument that resets **all**
blocks and closes all plate-gates, wiping legitimately-solved puzzle progress
along with the mistake.

BL-37 makes the game **self-healing** and less fiddly: a block may be pushed
anywhere in its room (dead squares included); if that strands it, it visibly
reacts — an animated countdown, a 500-point penalty, an explosion — and
respawns at its start. With that in place, the on-death block reset becomes
redundant and actively harmful (it discards solved progress), so it is removed
in the same change.

## Decisions (resolved 2026-07-12)

1. **Fuse model — per-push, non-cancelling.** Detection runs right after a
   successful push; a lit fuse always detonates, not re-checked each tick.
2. **Push mechanics — allow dead squares, confine to the room (Daniel).**
   - Remove the `(nc, nr) not in self._dead_squares` guard in
     `_try_push_block` (world.py:479): a block may be pushed onto a dead square;
     it ignites as a consequence.
   - Add **room-floor confinement**: reject a push whose destination leaves the
     block's room floor (same `tile_owner`; Act 1 has no `tile_owner`, so the
     whole interior is one room and the existing interior-bounds check already
     confines).
3. **Detection — static dead-square membership, no recomputation (Daniel).**
   For a single block, confined to its room, with temporary obstacles (other
   blocks, doors, gates, breakable walls, unbridged water) ignored, the set of
   dead tiles *with respect to the plate* is **fixed**. So detection does not
   re-flood per push: after a push, a block is doomed iff its tile is in the
   room's precomputed dead-square set. Reuse the generator's
   `room.dead_squares` (reverse-reachability from all plates over permanent
   walls, levellayout.py:1688; stored at 2916, surfaced by `World._dead_squares`,
   world.py:215). Target = any plate (no block→plate pairing is stored,
   levellayout.py:2900; the dead-square set already targets all plates).
4. **Respawn when home is occupied — relocate to nearest open tile.** If the
   start tile is free at detonation it respawns there; otherwise the nearest
   open tile (BFS over unblocked tiles from the start), excluding the player's
   tile.
5. **Score penalty — 500 points per exploding block.** `BLOCK_EXPLOSION_PENALTY
   = 500` (mirrors `LIFE_PENALTY`), deducted per block at detonation, floored
   at 0.
6. **Remove the on-death `_reset_blocks` path.** Dying no longer resets blocks
   or closes plate-gates. The spec 0067 player + enemy reset stays. Gates
   recompute via the per-tick `_latch_channels`; the open entrance survives
   because `_channels` is left untouched on death.
7. **Reverse the floor tinting (Daniel).** The floor pattern marks the **safe**
   tiles — a puzzle room's floor minus its dead squares — instead of the dead
   ones. Non-puzzle rooms (no plate) get plain floor.

**Residuals (accepted):** the static dead-square set ignores (a) player
reachability and (b) temporary obstacles, so it *under-detects* — a block
stranded by a not-yet-built bridge or a player-access quirk on a nominally
"alive" tile is not ignited. And in a hypothetical multi-puzzle room the set
ignores the other block. None of these occur with the current one-puzzle-per-room
levels; the common case is exact and cheap.

### Room invariant relied upon

**Enemies and push puzzles never share a room** (R-P9, `kb/requirements.md`;
`_distribute_enemies` excludes any node with `node.blocks or node.plates`,
levellayout.py:2525). So an exploding block's respawn need only avoid the
**player** and **other blocks** — never an enemy.

## Design

### A — Push mechanics (`_try_push_block`)

Replace the destination test (in-bounds ∧ not blocked ∧ **not a dead square**)
with (in-bounds ∧ not blocked ∧ **within the block's room floor**), then run the
doom check:

```python
nc, nr = bc + dcol, br + drow
if (not self.blocked(nc, nr)
        and (nc, nr) in self._room_floor(bc, br)):   # confinement (Decision 2)
    block.col, block.row = nc, nr
    self._emit('bumped')
    self._light_doomed_fuses()                        # detection (Decision 3)
    return True
return False
```

`_room_floor(c, r)` = floor tiles sharing `(c, r)`'s `tile_owner`
(`{t for t, o in self._tile_owner.items() if o == self._tile_owner.get((c, r))}`)
when a `tile_owner` exists, else `INTERIOR_TILES` (Act 1). Cache per owner.

### B — Detection: static dead-square membership

No runtime Sokoban. The safe/dead partition is the generator's precomputed set,
already on the room:

```python
def _light_doomed_fuses(self):
    dead = self._dead_squares            # room.dead_squares (world.py:215)
    for b in self.room.blocks:
        if b.fuse is None and (b.col, b.row) in dead:
            b.fuse = BLOCK_FUSE_MS
            self._emit('block_fuse_lit', b.col, b.row)
```

- `room.dead_squares` = tiles from which a block can never be pushed to any
  plate (reverse-reachability over permanent walls). A block *on a plate* is a
  reverse-flood target, so it is never in the set → never ignites (goal-state
  exclusion, free).
- Scanning all room blocks (not just the pushed one) costs nothing and covers a
  hypothetical multi-block room.

### Geometry (confirm before code — geometry rule)

`#` wall, `.` floor, `B` block, `T` plate. `room.dead_squares` = floor tiles the
block can never be pulled back from the plate to reach.

**(1) Corner is a dead square — pushing there now IGNITES.** Reverse-pull from
`T` cannot reach `(1,1)` (both perpendicular pulls need a wall tile behind), so
`(1,1) ∈ dead_squares`:

```
      c0 c1 c2 c3
  r0   #  #  #  #
  r1   #  d  .  #        d = dead square (in dead_squares); T elsewhere
  r2   #  .  .  #        old rule refused the push here; new rule allows it
  r3   #  #  #  #        and the block ignites on arrival
```

**(2) Plate tile is never dead — SAFE.** A block on `T` is on a reverse-flood
target:

```
      c0 c1 c2 c3
  r0   #  #  #  #
  r1   #  B  .  #        B(1,1) on plate T=(1,1): not in dead_squares -> safe
  r2   #  .  .  #
  r3   #  #  #  #
```

**(3) Confinement — push refused at the room edge.** `B` (owner `A`) cannot be
pushed into the doorway / next room (owner `A2`):

```
      c0 c1 c2 c3 c4        owners: c1,c2 = room A ; c3 = doorway/room A2
  r0   #  #  #  #  #
  r1   #  B  .  o  #        pushing B right past c2 is refused (dest not in
  r2   #  #  #  #  #        B's room floor)
```

**(4) Tinting reversed — safe tiles are the tinted ones.** In a puzzle room, the
floor pattern marks `room_floor − dead_squares` (the safe placement region);
dead squares and non-puzzle floor render plain.

### C — Fuse state + constants

`Block` (entities.py) is an `Entity` with no `__slots__`; add `self.fuse = None`
(None = inert; int = remaining ms). New constants in `constants.py`:

```python
BLOCK_FUSE_MS = 1500           # doomed-block explosion countdown (tunable)
BLOCK_EXPLOSION_PENALTY = 500  # points lost per exploding block (cf. LIFE_PENALTY)
```

### D — Update tick system (pinned order)

A new system in `World.update` decrements every block's fuse and detonates at
zero. It moves blocks (respawn), changing passability and plate occupancy, so it
runs **before** the `_latch_channels` plate pass:

```
transition gate → shield timer → input phase → enemy movement →
treasure/loot → player-enemy collision → flame damage →
  ►► block-fuse system ◄◄  → channel latch (plates) → material pickup → key pickup
```

Update the SYSTEM ORDER CONTRACT docstring (world.py:832) accordingly.

```python
def _tick_block_fuses(self, dt):
    for b in self.room.blocks:
        if b.fuse is None:
            continue
        b.fuse -= dt
        if b.fuse <= 0:
            b.fuse = None
            self._detonate_block(b)
```

### E — Detonation (respawn + penalty + events)

```python
def _detonate_block(self, b):
    home = self.room.blocks_initial[self.room.blocks.index(b)]
    self.score = max(0, self.score - BLOCK_EXPLOSION_PENALTY)   # Decision 5
    self._emit('block_exploded', b.col, b.row)                  # burst at OLD pos
    b.col, b.row = self._block_respawn_tile(home)               # Decision 4
    b.fuse = None
```

`blocks_initial` (rooms.py:24) is positionally aligned with `room.blocks`.
`_block_respawn_tile(home)` returns `home` if open and not the player's tile,
else the nearest open non-player tile by BFS from `home` (blocks count as
blocked, so it never lands on another block).

### F — Remove the on-death block reset (Decision 6)

- In `_lose_life` (world.py:705) delete the `self._reset_blocks()` call. The
  player + enemy reset (spec 0067) stays; `_channels` is left untouched so the
  open entrance persists and plate-gates recompute next tick via
  `_latch_channels`.
- Delete the unused `_reset_blocks` method (world.py:708) and its
  `ENTRANCE_CHANNEL` preservation comment.
- **Test fallout** (these lock the deleted behaviour):
  - `tests/test_dispatch.py::test_reset_blocks_closes_gates_immediately` — remove.
  - `tests/test_rooms.py::test_reset_blocks_covers_visited_only_and_unvisited_stay_initial` — remove.
  - `tests/test_registry.py` (~line 130 uses `_reset_blocks`) — rewrite to not
    call the removed method.
  - `tests/test_entrance_exit.py` — keep the entrance-persists-across-death
    assertion green; update its rationale to the new mechanism (`_channels`
    untouched) and re-pin.

### G — Rendering & sound

- **Floor tint reversal** (`game.py`, line 528): replace the dead-square tint
  with a **safe-tile** tint. Build `safe_tiles = { floor tiles whose owning room
  has a plate } − dead_squares` (Act 1: interior floor − dead_squares when the
  level has a plate); render the pattern sprite on `safe_tiles`, plain floor
  elsewhere. Rename the sprite key `dead_floor → safe_floor` for clarity.
- **Sound** (`sounds.py`): add `sfx_block_fuse` (short rising tick) and
  `sfx_block_explode` (noise burst); register both.
- **Event map** (`game.py` `_EVENT_SOUNDS`, line 178): `'block_fuse_lit' →
  'block_fuse'`, `'block_exploded' → 'block_explode'`.
- **Fuse animation** (`game.py` block draw loop, line 582): when `b.fuse` is not
  None, overlay a countdown cue keyed on `b.fuse / BLOCK_FUSE_MS`.
- **Explosion** (`game.py`): on `block_exploded`, spawn a brief timer-driven
  burst at the emitted position (drawn from `sprites.py`, like the screen flash).

## Tests (world-level, pygame-free unless noted)

- **Dead-square push now allowed + ignites:** push a block onto a tile in
  `room.dead_squares` (previously refused); assert the push *succeeds*, `b.fuse`
  is set, and `block_fuse_lit` fired.
- **Confinement:** attempt to push a block off its room floor (toward a doorway
  / another owner); assert the push is refused and the block does not move.
- **Explode + penalty + respawn:** advance `update` past `BLOCK_FUSE_MS`; assert
  `block_exploded` fired, `score` dropped by 500 (floored at 0), and the block
  is back at its start.
- **Block on a plate never ignites:** a block parked on its plate is never in
  `dead_squares` → never fused; its gate stays open.
- **Safe tile stays safe:** push a block onto a non-dead room tile; assert it is
  not fused.
- **Respawn relocates when home blocked:** occupy the start tile (wall / another
  block), detonate; assert it lands on the nearest open tile, never on the
  player or another block.
- **On death, blocks are NOT reset:** solve a puzzle (block on plate), move
  another block, non-fatal `_lose_life`; assert blocks stay put (plate block
  still on the plate, gate still open) and only player + enemies reset.
- **Entrance persists across death (new mechanism):** open the entrance, die;
  assert `ENTRANCE_CHANNEL` still latched via `_channels` untouched.
- **System order:** the block-fuse system runs before `_latch_channels` — a
  detonation moving a block off a plate closes its gate the same tick.
- **Safe-tile tint (rendering):** in a puzzle room the tinted set equals
  `room_floor − dead_squares`; a non-puzzle grid tints nothing.

## Manual verification

- `poe run` an Act 2 push-puzzle level: push a block onto a dead square → it
  flashes a countdown, the score drops 500, it explodes and reappears at its
  start.
- Try to push a block through a doorway out of its room → it won't move past the
  room edge.
- Observe the floor tint: the **safe** placement tiles are patterned, dead
  squares are plain.
- Park a block on its plate (solve the puzzle) → no countdown; the gate stays
  open.
- Solve a puzzle, then die on that grid → the solved puzzle is preserved (block
  still on the plate, gate still open); player and enemies reset as before.
- Open the entrance (collect all awards), then die → the entrance is still open.

## Done when:

- [ ] `_try_push_block` drops the dead-square guard and adds room-floor
      confinement; a block may be pushed onto a dead square but never off its
      room
- [ ] `_light_doomed_fuses` ignites any block whose tile is in the room's
      precomputed `dead_squares` (no per-push recomputation); a block on a plate
      is never in the set
- [ ] `_tick_block_fuses` decrements fuses at the pinned slot (before
      `_latch_channels`); at zero the block deducts `BLOCK_EXPLOSION_PENALTY`,
      emits `block_exploded`, and respawns at its start else the nearest open
      non-player tile
- [ ] Floor tinting marks the safe tiles (`room_floor − dead_squares` in puzzle
      rooms), not the dead ones
- [ ] On-death `_reset_blocks` call and method removed; `_lose_life` keeps the
      0067 player + enemy reset; gates self-correct via the latch; the open
      entrance persists (`_channels` untouched)
- [ ] The four `_reset_blocks`-locking tests removed/rewritten;
      entrance-persists-across-death re-pinned
- [ ] `block_fuse_lit` / `block_exploded` mapped to new SFX; fuse countdown and
      explosion are drawn
- [ ] New tests red first, then green; `poe test` exits 0 with any affected
      goldens deliberately re-recorded
- [ ] User confirms in-game: a block on a dead square counts down, costs 500,
      explodes, and respawns; blocks can't be pushed out of their room; safe
      tiles are the tinted ones; dying preserves solved puzzle progress (manual
      acceptance)
