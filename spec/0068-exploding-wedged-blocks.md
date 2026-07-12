# 0068 — Wedged push-blocks explode and respawn; on-death block reset removed (BL-37)

## Status

- [ ] A push-block with **zero push directions** after a push is *wedged* and
      lights an explosion fuse; when the fuse expires the block explodes and
      respawns at its start (BL-37)
- [ ] **Mutually-wedged blocks ignite together**: the post-push scan lights a
      fuse on *every* block that currently has zero push directions, not only
      the block just pushed (Daniel: two adjacent blocks that jam each other)
- [ ] A block **resting on a pressure plate is never ignited** — parking a
      block on its plate is the puzzle's goal state, even if that tile has zero
      push directions
- [ ] Detection uses the live `World.blocked` query (respects bridged water and
      open gates at evaluation time), never a private obstacle model (BL-13
      bug class)
- [ ] Fuse is **per-push, non-cancelling** (Decision 1): a lit fuse always
      detonates; it is not re-evaluated or cancelled if the configuration later
      frees the block
- [ ] On detonation the block respawns at its **start tile** if free, else at
      the **nearest open tile** (Decision 2); it never materialises on the
      player or another block (enemies never share a push-puzzle room — R-P9)
- [ ] `World.update` gains a **block-fuse system** slotted explicitly into the
      pinned system order (spec 0052 G5); the contract note is updated
- [ ] Two new world events — `block_fuse_lit` and `block_exploded` — mapped to
      new SFX in `game.py`; the fuse and explosion are drawn (animated
      countdown on the tile, then a burst)
- [ ] The **on-death `_reset_blocks` path is removed** (Decision 3): dying no
      longer resets blocks or closes plate-gates; `_lose_life` keeps the spec
      0067 player + enemy reset. Gates self-correct via the per-tick latch; the
      open entrance persists because `_channels` is left untouched on death
- [ ] `_reset_blocks` and its four locking tests (`test_registry`,
      `test_rooms`, `test_dispatch`, `test_entrance_exit`) are removed or
      rewritten to the new behaviour; entrance-persists-across-death is
      re-pinned against the new mechanism
- [ ] New tests red before the change, green after; `poe test` exits 0 with any
      affected goldens deliberately re-recorded
- [ ] Manual check: mis-push a block into a wedge → it counts down and explodes
      back to its start; jam two blocks together → both explode; die on a solved
      grid → the solved puzzle is preserved (user acceptance)

## Problem

Today a block pushed onto a tile from which the puzzle becomes unsolvable simply
stays wedged. The only recovery is death, which triggers `_reset_blocks`
(world.py:708) — a blunt instrument that resets **all** blocks and closes all
plate-gates, wiping legitimately-solved puzzle progress along with the mistake.
The old `_verify_blocks` regeneration net (world.py:343) that used to catch
zero-push blocks now only runs on grid entry (spec 0048), so a mid-play
self-wedge has no in-game recovery at all.

BL-37 makes the game **self-healing** with respect to push puzzles: a wedged
block visibly reacts — an animated countdown, then an explosion — and respawns
at its start. With that in place, the on-death block reset becomes redundant and
actively harmful (it discards solved progress), so it is removed in the same
change.

## Decisions (resolved 2026-07-12)

1. **Fuse model — per-push, non-cancelling.** Detection runs once, right after a
   successful push. A lit fuse always detonates; it is not re-checked each tick
   and does not cancel if a later gate/bridge change would have freed the block.
   (The rejected alternative was a per-tick re-evaluated, cancel-if-freed fuse.)
   Consequence: a wedge created by a *non-push* event — e.g. a gate closing onto
   a block's only lane — is **not** detected. Accepted as out of scope; wedges
   in practice are created by pushes.
2. **Respawn when home is occupied — relocate to nearest open tile.** If the
   block's start tile is free at detonation, it respawns there; otherwise it
   takes the nearest open tile (BFS over unblocked tiles from the start),
   excluding the player's tile. Reuses the spirit of the 0067 enemy-respawn
   fallback. (The rejected alternative was to hold the explosion pending until
   home clears.)
3. **Remove the on-death `_reset_blocks` path.** Dying no longer resets blocks
   or closes plate-gates. The spec 0067 player + enemy reset stays. Gates
   recompute from live block occupancy via the per-tick `_latch_channels`; the
   open entrance survives because `_channels` is left untouched on death (the
   old `_reset_blocks` ENTRANCE-preservation hack is no longer needed).

### Room invariant relied upon

**Enemies and push puzzles never share a room** (R-P9, `kb/requirements.md`:
`_distribute_enemies` excludes any node with `node.blocks or node.plates`,
levellayout.py:2525). So an exploding block's respawn need only avoid the
**player** and **other blocks** — never an enemy. → see `kb/requirements.md`
R-P9.

## Design

### A — Detection (per-push, reuse the push-direction primitive)

`World.blocked` already counts a block as an obstacle (world.py:175), so the
existing per-block push-direction computation in `_verify_blocks`
(world.py:343–355) already sees a neighbouring block as a blocked side — mutual
wedges fall out for free. Factor that inner computation into a predicate and
reuse it:

```python
def _push_dirs(self, bc, br):
    """Number of axes along which the block at (bc, br) can be pushed:
    both the player-stands-here tile and the destination must be open."""
    n = 0
    for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        pf = (bc - dc, br - dr)          # where the player must stand
        pt = (bc + dc, br + dr)          # where the block would go
        if (0 < pf[0] < COLS - 1 and 0 < pf[1] < ROWS - 1
                and not self.blocked(*pf)
                and 0 < pt[0] < COLS - 1 and 0 < pt[1] < ROWS - 1
                and not self.blocked(*pt)):
            n += 1
    return n
```

`_verify_blocks` is refactored to call `_push_dirs` (behaviour identical, so its
goldens/sweeps stay green).

**Ignite scan**, hooked at the single successful-push site — inside
`_try_push_block`, after the block has moved and before it returns `True`:

```python
def _light_wedged_fuses(self):
    plate_tiles = {(pc, pr) for pc, pr, _g in self.room.plates}
    for b in self.room.blocks:
        if b.fuse is not None:                  # already lit — never re-light
            continue
        if (b.col, b.row) in plate_tiles:       # on a plate = goal state
            continue
        if self._push_dirs(b.col, b.row) == 0:  # wedged
            b.fuse = BLOCK_FUSE_MS
            self._emit('block_fuse_lit', b.col, b.row)
```

Scanning **all** blocks (not just the pushed one) is what makes a mutual pair
ignite together: the push that jams them leaves *both* at zero push directions.

### Geometry (confirm before code — geometry rule)

`#` wall/blocked, `.` open floor, `A`/`B` blocks. A block is pushable along an
axis iff **both** the opposite tiles (player-stands + destination) are open;
zero pushable axes = wedged.

**Single-block corner wedge** — one block shoved into a corner, no partner:

```
      c0 c1 c2 c3
  r0   #  #  #  #
  r1   #  B  .  #
  r2   #  .  .  #
  r3   #  #  #  #
```
`B(1,1)`: horiz left `(0,1)=#` blocked; vert up `(1,0)=#` blocked → **0 push
dirs → wedged**. Lights a fuse; explodes; respawns at its start tile.

**Mutual wedge** — two blocks that jam each other against a wall; removing
either would free the other:

```
      c0 c1 c2 c3 c4 c5
  r0   #  #  #  #  #  #
  r1   #  .  A  B  .  #
  r2   #  .  .  .  .  #
  r3   #  #  #  #  #  #
```
`A(2,1)`: horiz left `(1,1)=.` open but right `(3,1)=B` blocked → not pushable;
vert up `(2,0)=#` blocked → not pushable → **0 dirs**. `B(3,1)`: horiz left
`(2,1)=A` blocked, vert up `(3,0)=#` blocked → **0 dirs**. Both wedged. (Remove
`B` and `A`'s row would be `# . A . . #` → `A` pushable again — confirming they
are *mutually* wedged, so both must ignite.) The post-push full scan lights
fuses on **both**.

**Plate exclusion** — a block parked on its plate `P` is the goal state and is
never ignited even at zero push dirs:

```
      c0 c1 c2 c3
  r0   #  #  #  #
  r1   #  B  .  #      B(1,1) sits on plate at (1,1): 0 push dirs, but
  r2   #  .  .  #      on a plate -> NOT wedged, no fuse.
  r3   #  #  #  #
```

### B — Fuse state + constant

`Block` (entities.py) is an `Entity` with no `__slots__`, so add per-instance
state in `__init__` (or lazily): `self.fuse = None` (None = inert; an int =
remaining ms). New constant in `constants.py`:

```python
BLOCK_FUSE_MS = 1500   # wedged-block explosion countdown (tunable at acceptance)
```

### C — Update tick system (pinned order)

A new system in `World.update` decrements every block's fuse and detonates at
zero. It **moves blocks** (respawn), which changes passability and plate
occupancy, so it must run **before** the `_latch_channels` plate pass so gate
state reflects the same tick's detonations, and after enemy movement / collision
(irrelevant here — no enemies in puzzle rooms, but the slot must be fixed for
determinism):

```
transition gate → shield timer → input phase → enemy movement →
treasure/loot → player-enemy collision → flame damage →
  ►► block-fuse system ◄◄  → channel latch (plates) → material pickup → key pickup
```

Update the SYSTEM ORDER CONTRACT docstring (world.py:832) to insert the
block-fuse system at this position.

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

### D — Detonation (respawn + events)

```python
def _detonate_block(self, b):
    home = self.room.blocks_initial[self.room.blocks.index(b)]
    self._emit('block_exploded', b.col, b.row)   # burst at the OLD position
    b.col, b.row = self._block_respawn_tile(home)
    b.fuse = None
```

`blocks_initial` is captured per room at construction (rooms.py:24) and is
positionally aligned with `room.blocks`. `_block_respawn_tile(home)` returns
`home` if it is open and not the player's tile, else the nearest open non-player
tile by BFS from `home` (blocks count as blocked, so it never lands on another
block). Enemies are excluded by the room invariant, not by an explicit check.

### E — Remove the on-death block reset (Decision 3)

- In `_lose_life` (world.py:705) delete the `self._reset_blocks()` call. The
  player + enemy reset (spec 0067) stays; `_channels` is left untouched so the
  open entrance persists and plate-gates recompute next tick via
  `_latch_channels`.
- Delete the now-unused `_reset_blocks` method (world.py:708) and the
  `ENTRANCE_CHANNEL` preservation comment.
- **Test fallout** (these lock the deleted behaviour):
  - `tests/test_dispatch.py::test_reset_blocks_closes_gates_immediately` —
    remove (gate-closing-on-death is deleted).
  - `tests/test_rooms.py::test_reset_blocks_covers_visited_only_and_unvisited_stay_initial`
    — remove.
  - `tests/test_registry.py` (line ~130 uses `_reset_blocks` as a helper) —
    rewrite to not call the removed method.
  - `tests/test_entrance_exit.py` — the entrance-persists-across-death
    assertion must stay green; update its rationale to the new mechanism
    (`_channels` untouched on death) and re-pin it.

### F — Rendering & sound

- **Sound** (`sounds.py`): add `sfx_block_fuse` (a short rising tick/beep) and
  `sfx_block_explode` (a noise burst); register both in the SFX dict.
- **Event map** (`game.py` `_EVENT_SOUNDS`, line 178): `'block_fuse_lit' →
  'block_fuse'`, `'block_exploded' → 'block_explode'`.
- **Fuse animation** (`game.py` block draw loop, line 582): when `b.fuse` is not
  None, overlay a countdown cue on the tile (e.g. pulse toward red / a shrinking
  ring keyed on `b.fuse / BLOCK_FUSE_MS`).
- **Explosion** (`game.py`): on a `block_exploded` event, spawn a brief burst
  animation at the emitted position (a short-lived particle/flash drawn from
  `sprites.py`; timer-driven like the existing screen flash).

## Tests (world-level, pygame-free unless noted)

- **Single wedge ignites & explodes:** push a block into a corner (0 push
  dirs); assert `b.fuse` is set; advance `update` past `BLOCK_FUSE_MS`; assert a
  `block_exploded` event fired and the block is back at its start tile.
- **Mutual wedge — both ignite:** arrange the two-block config above; the push
  that jams them lights a fuse on **both**; both explode and return to their
  starts.
- **Block on a plate never ignites:** a block parked on its plate with 0 push
  dirs after a push has `fuse is None` — no `block_fuse_lit`, gate stays open.
- **Bridged/gated lane counts as open:** a block whose only push lane crosses a
  now-open gate (channel high) is **not** wedged — detection uses live
  `World.blocked`.
- **Fuse is non-cancelling:** light a fuse, then (artificially) open a gate that
  would free the block; the fuse still detonates (Decision 1).
- **Respawn relocates when home blocked:** occupy the block's start tile (place
  a wall / park another block), detonate; assert it lands on the nearest open
  tile, never on the player or another block.
- **On death, blocks are NOT reset:** solve a puzzle (park a block on its
  plate), move another block, then a non-fatal `_lose_life`; assert blocks stay
  where they are (the solved plate block still on the plate, its gate still
  open) and only the player + enemies reset (spec 0067 untouched).
- **Entrance persists across death (new mechanism):** open the entrance, die;
  assert `ENTRANCE_CHANNEL` still latched and the entrance still open — via
  `_channels` untouched, not `_reset_blocks`.
- **System order:** the block-fuse system runs before `_latch_channels` — a
  detonation that moves a block off a plate closes its gate the same tick.

## Manual verification

- `poe run` an Act 2 level with a push puzzle: deliberately push a block into a
  wall corner → it flashes a countdown, explodes, and reappears at its start.
- Jam two blocks against each other so neither can move → both count down and
  explode together.
- Park a block on its plate (solve the puzzle) → no countdown starts; the gate
  stays open.
- Solve a puzzle, then die on that grid → the solved puzzle is preserved (block
  still on the plate, gate still open); player and enemies reset as before.
- Open the entrance (collect all awards), then die → the entrance is still open
  on respawn.

## Done when:

- [ ] `World._push_dirs` factored out; `_verify_blocks` reuses it with identical
      behaviour (its goldens/sweeps stay green)
- [ ] A successful push lights a fuse (`BLOCK_FUSE_MS`) on every zero-push block
      that is not on a plate; `block_fuse_lit` emitted per block
- [ ] Mutually-wedged blocks all ignite from the one push that jams them
- [ ] `_tick_block_fuses` decrements fuses in `update` at the pinned slot (before
      `_latch_channels`); at zero the block emits `block_exploded` and respawns
      at its start, else the nearest open non-player tile
- [ ] On-death `_reset_blocks` call and method removed; `_lose_life` keeps the
      0067 player + enemy reset; gates self-correct via the latch; the open
      entrance persists (`_channels` untouched on death)
- [ ] The four `_reset_blocks`-locking tests are removed/rewritten;
      entrance-persists-across-death re-pinned against the new mechanism
- [ ] `block_fuse_lit` / `block_exploded` mapped to new SFX; fuse countdown and
      explosion are drawn
- [ ] New tests red first, then green; `poe test` exits 0 with any affected
      goldens deliberately re-recorded
- [ ] User confirms in-game: wedged blocks (single and mutual) explode back to
      their starts; plate-parked blocks never ignite; dying preserves solved
      puzzle progress (manual acceptance)
