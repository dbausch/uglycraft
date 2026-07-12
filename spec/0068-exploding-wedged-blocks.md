# 0068 — Doomed push-blocks explode and respawn; dead-square push allowed; on-death block reset removed (BL-37)

## Status

- [ ] Pushing a block is **no longer blocked by dead squares**: a block *may* be
      pushed onto a tile from which it can no longer reach a plate — the
      consequence is that it now *ignites* (Daniel). The `_dead_squares` push
      guard in `_try_push_block` is removed
- [ ] A block **can never be pushed off its room's floor tiles** (Daniel):
      confinement to the block's own room (via `tile_owner`; Act 1 = the whole
      interior). This keeps a block in its puzzle and limits interacting blocks
      to those assigned to the same room
- [ ] A block is *doomed* when, in the **current live configuration**, no
      player-performable push sequence can bring it onto **any** plate in its
      room; a doomed block lights an explosion fuse and, when the fuse expires,
      explodes and respawns at its start (BL-37)
- [ ] Detection is a **reverse-Sokoban flood from the plate** (Daniel): flood
      the room backward from (block-on-plate), tracking the player zone, to build
      the set of safe (block-pos, player-zone) states; the block is safe iff its
      current state is in that set, else doomed. Recomputed after every push
- [ ] A block **already on a plate is never doomed** (it is the flood's seed —
      the goal-state exclusion, for free)
- [ ] Detection uses the live `World.blocked` query (open gates, built bridges
      count) — never a private obstacle model (BL-13 bug class)
- [ ] Fuse is **per-push, non-cancelling** (Decision 1): a lit fuse always
      detonates; it is not re-evaluated or cancelled if the configuration later
      frees the block
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
      rewritten to the new behaviour; entrance-persists-across-death is
      re-pinned against the new mechanism
- [ ] New tests red before the change, green after; `poe test` exits 0 with any
      affected goldens deliberately re-recorded
- [ ] Manual check: push a block into a dead corner → it counts down, deducts
      500, explodes, and respawns at its start; a block can't be pushed out of
      its room; die on a solved grid → the solved puzzle is preserved (user
      acceptance)

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
   successful push; a lit fuse always detonates and is not re-checked each tick
   or cancelled if a later gate/bridge change would have freed the block. A doom
   created by a *non-push* event (e.g. a gate closing onto a lane) is not
   detected — accepted; dooms in practice come from pushes.
2. **Push mechanics — allow dead squares, confine to the room (Daniel).**
   - Remove the `(nc, nr) not in self._dead_squares` guard in
     `_try_push_block` (world.py:479): a block may be pushed onto a dead square;
     it ignites as a consequence.
   - Add a **room-floor confinement**: a push is rejected if the destination
     leaves the block's room floor (same `tile_owner`; Act 1 has no
     `tile_owner`, so the whole interior is one room and the existing
     interior-bounds check already confines). This limits interacting blocks to
     those in the same room.
   - The dead-square *floor visual* (game.py:528) is retained as a danger hint;
     revisit only if it reads wrong in play.
3. **Detection criterion — reverse-Sokoban flood from the plate (Daniel).** Do
   not forward-search from the current configuration (expensive). Flood the room
   **backward from the goal** (block on a plate), tracking the player zone so
   each reverse "pull" is player-performable, and collect all safe
   (block-pos, player-zone) states. A block is doomed iff its current state is
   **not** in the safe set. Target = **any** plate in the room (no block→plate
   pairing is stored, levellayout.py:2900; the generator's dead-square set
   already targets all plates, levellayout.py:2915). With one puzzle per room
   (the current reality) this is exact single-block Sokoban; if a room ever
   holds 2+ blocks, the others are treated as static obstacles in the flood
   (a conservative simplification — see Residual).
4. **Respawn when home is occupied — relocate to nearest open tile.** If the
   start tile is free at detonation it respawns there; otherwise the nearest
   open tile (BFS over unblocked tiles from the start), excluding the player's
   tile. (Rejected: hold the explosion pending until home clears.)
5. **Score penalty — 500 points per exploding block.** `BLOCK_EXPLOSION_PENALTY
   = 500` (mirrors `LIFE_PENALTY`), deducted per block at detonation, floored
   at 0.
6. **Remove the on-death `_reset_blocks` path.** Dying no longer resets blocks
   or closes plate-gates. The spec 0067 player + enemy reset stays. Gates
   recompute from live block occupancy via the per-tick `_latch_channels`; the
   open entrance survives because `_channels` is left untouched on death.

**Residual (accepted):** because the reverse flood treats any *other* same-room
blocks as static obstacles, a hypothetical multi-puzzle room could ignite a
block that a movable obstruction merely blocks. This does not occur in current
levels (one puzzle per room), and the exact single-block case is unaffected.

### Room invariant relied upon

**Enemies and push puzzles never share a room** (R-P9, `kb/requirements.md`:
`_distribute_enemies` excludes any node with `node.blocks or node.plates`,
levellayout.py:2525). So an exploding block's respawn need only avoid the
**player** and **other blocks** — never an enemy.

## Design

### A — Push mechanics (`_try_push_block`)

Replace the current destination test (in-bounds ∧ not blocked ∧ not a dead
square) with (in-bounds ∧ not blocked ∧ **within the block's room floor**):

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

`_room_floor(c, r)` returns the floor tiles owned by the same room as `(c, r)`:
`{t for t, o in self._tile_owner.items() if o == self._tile_owner.get((c, r))}`
when a `tile_owner` exists, else `INTERIOR_TILES` (Act 1). Cache per owner. The
`_dead_squares` guard is gone; the dead-square floor visual stays.

### B — Detection: reverse-Sokoban flood from the plate

A block is *safe* if the player can push it to a plate; *doomed* otherwise.
Compute the **safe set** once per push by flooding **backward** from the goal:

```
plates  = {(pc, pr) for pc, pr, _g in room.plates}
floor   = room floor tiles (block domain; other same-room blocks are static)
passable(player) = grid tiles that are not World.blocked and not a block

State  = (block_pos, player_zone)          # player_zone = normalized component
Seed   = for each plate p and each zone z the player can occupy next to a
         valid pull-from tile: (p, z)
Reverse step from (X, z): a forward push that ENDED at X came from the block
  at X−d with the player pushing from X−2d. So the predecessor state is
  (X−d, z'), valid when X−d ∈ floor, X−2d is player-passable, and the player
  in the successor zone z can have reached X (the post-push player tile).
Flood all predecessor states → SAFE.

doomed(b) = (b.pos, current_player_zone(b)) ∉ SAFE
```

- Reuses the player-zone normalization and `_player_reachable` from
  `_sokoban_bfs` (levellayout.py:1788), run in reverse; and
  `_compute_dead_squares` (levellayout.py:1688) as an optional prune. To keep
  the pygame-free runtime free of generation imports, lift these pure helpers
  into a shared module (e.g. `sokoban.py`) that both `levellayout` and `world`
  import. (Implementation detail; confirm during build.)
- Passability is the live `World.blocked` query (open gates, built bridges).
- A block on a plate now is a flood seed → always safe. Plate/goal-state
  exclusion falls out for free.
- Confinement (§A) bounds the block domain to one room, so the flood is small
  and runs only on a push.

**Ignite** the doomed set (skip already-fused blocks):

```python
def _light_doomed_fuses(self):
    for b in self._doomed_blocks():        # the reverse flood above
        if b.fuse is None:
            b.fuse = BLOCK_FUSE_MS
            self._emit('block_fuse_lit', b.col, b.row)
```

### Geometry (confirm before code — geometry rule)

`#` wall/blocked, `.` floor, `B` block, `T` plate. `d`-push legal iff the player
can stand on `pos − d` and `pos + d` is passable & in the room floor.

**(1) Corner wedge — DOOMED.** Pushed into a corner it cannot leave:

```
      c0 c1 c2 c3
  r0   #  #  #  #
  r1   #  B  .  #        T (plate) elsewhere in the room
  r2   #  .  .  #
  r3   #  #  #  #
```
Reverse flood from `T` can never pull a block *into* `(1,1)` (both perpendicular
pulls need a wall tile), so `(1,1)` is not in the safe set → `B` is **doomed**.
Under the old rule the push here was refused; now it is allowed and ignites.

**(2) Plate exclusion — SAFE.** A block on the plate is the flood seed:

```
      c0 c1 c2 c3
  r0   #  #  #  #
  r1   #  B  .  #        B(1,1) is on plate T=(1,1): seed of the reverse
  r2   #  .  .  #        flood -> always safe, never a fuse.
  r3   #  #  #  #
```

**(3) Confinement — push refused at the room edge.** `B` cannot be pushed off
its room floor (owner `A`) into the doorway/next room (owner `A2`):

```
      c0 c1 c2 c3 c4          owners:  c1,c2 = room A ; c3 = doorway/room A2
  r0   #  #  #  #  #
  r1   #  B  .  o  #          pushing B right past c2 is refused at the
  r2   #  #  #  #  #          A|A2 boundary (dest not in B's room floor)
```

**(4) Reachable → SAFE.** From a tile the reverse flood *does* reach (a
player-performable pull sequence exists back to the plate), the block is safe
and never ignites — this is the normal in-progress puzzle state.

*Multi-puzzle room (rare):* other same-room blocks are static obstacles in the
flood, so a genuine mutual jam (neither block pullable to a plate) ignites both;
a movable obstruction may also ignite (accepted Residual). Current levels have
one puzzle per room, where detection is exact.

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
blocked, so it never lands on another block). Enemies excluded by R-P9.

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

- **Sound** (`sounds.py`): add `sfx_block_fuse` (short rising tick) and
  `sfx_block_explode` (noise burst); register both.
- **Event map** (`game.py` `_EVENT_SOUNDS`, line 178): `'block_fuse_lit' →
  'block_fuse'`, `'block_exploded' → 'block_explode'`.
- **Fuse animation** (`game.py` block draw loop, line 582): when `b.fuse` is not
  None, overlay a countdown cue keyed on `b.fuse / BLOCK_FUSE_MS`.
- **Explosion** (`game.py`): on `block_exploded`, spawn a brief timer-driven
  burst at the emitted position (drawn from `sprites.py`, like the screen flash).

## Tests (world-level, pygame-free unless noted)

- **Dead-square push now allowed + ignites:** push a block into a corner it
  cannot leave (previously refused); assert the push *succeeds*, `b.fuse` is
  set, and `block_fuse_lit` fired.
- **Confinement:** attempt to push a block off its room floor (toward a doorway
  / another owner); assert the push is refused and the block does not move.
- **Explode + penalty + respawn:** advance `update` past `BLOCK_FUSE_MS`; assert
  `block_exploded` fired, `score` dropped by 500 (floored at 0), and the block
  is back at its start.
- **Block on a plate never ignites:** a block parked on its plate is never
  fused; its gate stays open.
- **Reachable stays safe:** from a tile the reverse flood reaches, a push does
  not ignite the block (normal in-progress state).
- **Bridged/gated lane counts as open:** a block whose only route to the plate
  crosses a now-open gate is safe — detection uses live `World.blocked`.
- **Fuse is non-cancelling:** light a fuse, then (artificially) make the block
  solvable again; it still detonates (Decision 1).
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
- *(if a multi-puzzle fixture is available)* **Mutual jam ignites both:** two
  blocks jammed so neither can be pulled to a plate → both fuse.

## Manual verification

- `poe run` an Act 2 push-puzzle level: push a block into a dead corner → it
  flashes a countdown, the score drops 500, it explodes and reappears at its
  start.
- Try to push a block through a doorway out of its room → it won't move past the
  room edge.
- Park a block on its plate (solve the puzzle) → no countdown; the gate stays
  open.
- Solve a puzzle, then die on that grid → the solved puzzle is preserved (block
  still on the plate, gate still open); player and enemies reset as before.
- Open the entrance (collect all awards), then die → the entrance is still open.

## Done when:

- [ ] `_try_push_block` drops the dead-square guard and adds room-floor
      confinement; a block may be pushed onto a dead square but never off its
      room
- [ ] `World._doomed_blocks` builds the safe set by a reverse-Sokoban flood from
      the room's plate(s) with player-zone tracking, over live `World.blocked`
      passability; a block whose current state is outside the set is doomed
      (block on a plate is a seed → always safe); pure helpers lifted to a shared
      module so the runtime imports no generation code
- [ ] A successful push ignites every newly-doomed block (`BLOCK_FUSE_MS` fuse,
      `block_fuse_lit` per block)
- [ ] `_tick_block_fuses` decrements fuses at the pinned slot (before
      `_latch_channels`); at zero the block deducts `BLOCK_EXPLOSION_PENALTY`,
      emits `block_exploded`, and respawns at its start else the nearest open
      non-player tile
- [ ] On-death `_reset_blocks` call and method removed; `_lose_life` keeps the
      0067 player + enemy reset; gates self-correct via the latch; the open
      entrance persists (`_channels` untouched)
- [ ] The four `_reset_blocks`-locking tests removed/rewritten;
      entrance-persists-across-death re-pinned against the new mechanism
- [ ] `block_fuse_lit` / `block_exploded` mapped to new SFX; fuse countdown and
      explosion are drawn
- [ ] New tests red first, then green; `poe test` exits 0 with any affected
      goldens deliberately re-recorded
- [ ] User confirms in-game: a stranded block counts down, costs 500, explodes,
      and respawns; blocks can't be pushed out of their room; plate-parked
      blocks never ignite; dying preserves solved puzzle progress (manual
      acceptance)
