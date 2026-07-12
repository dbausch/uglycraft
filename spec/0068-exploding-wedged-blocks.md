# 0068 — Doomed push-blocks explode and respawn; on-death block reset removed (BL-37)

## Status

- [ ] A push-block is *doomed* when, in the **current live configuration**, no
      sequence of legal pushes can bring it onto **any** pressure plate; a
      doomed block lights an explosion fuse and, when the fuse expires, explodes
      and respawns at its start (BL-37)
- [ ] Detection is **true multi-block solvability**: other blocks may be pushed
      out of the way, so a block merely *obstructed by a movable block* is NOT
      doomed (Daniel); only a block that truly cannot reach a plate — including
      both members of a mutual jam where neither can move — ignites
- [ ] Allowed tiles are **recomputed after every successful push of any block**
      (a push can doom a different block than the one moved, and can doom two at
      once); every newly-doomed block that is not already fused ignites
- [ ] A block **already on a plate is never doomed** (it trivially reaches a
      plate — the goal-state exclusion, for free)
- [ ] Detection uses the live `World.blocked` query (respects bridged water and
      open gates at evaluation time), never a private obstacle model (BL-13
      bug class)
- [ ] Fuse is **per-push, non-cancelling** (Decision 1): a lit fuse always
      detonates; it is not re-evaluated or cancelled if the configuration later
      frees the block
- [ ] On detonation the block respawns at its **start tile** if free, else at
      the **nearest open tile** (Decision 3); it never materialises on the
      player or another block (enemies never share a push-puzzle room — R-P9)
- [ ] `World.update` gains a **block-fuse system** slotted explicitly into the
      pinned system order (spec 0052 G5); the contract note is updated
- [ ] Two new world events — `block_fuse_lit` and `block_exploded` — mapped to
      new SFX in `game.py`; the fuse and explosion are drawn (animated
      countdown on the tile, then a burst)
- [ ] The **on-death `_reset_blocks` path is removed** (Decision 4): dying no
      longer resets blocks or closes plate-gates; `_lose_life` keeps the spec
      0067 player + enemy reset. Gates self-correct via the per-tick latch; the
      open entrance persists because `_channels` is left untouched on death
- [ ] `_reset_blocks` and its four locking tests (`test_registry`,
      `test_rooms`, `test_dispatch`, `test_entrance_exit`) are removed or
      rewritten to the new behaviour; entrance-persists-across-death is
      re-pinned against the new mechanism
- [ ] New tests red before the change, green after; `poe test` exits 0 with any
      affected goldens deliberately re-recorded
- [ ] Manual check: mis-push a block into a true wedge → it counts down and
      explodes back to its start; jam two blocks so neither can move → both
      explode; obstruct a block with a *movable* one → nothing ignites; die on a
      solved grid → the solved puzzle is preserved (user acceptance)

## Problem

Today a block pushed onto a tile from which the puzzle becomes unsolvable simply
stays wedged. The only recovery is death, which triggers `_reset_blocks`
(world.py:708) — a blunt instrument that resets **all** blocks and closes all
plate-gates, wiping legitimately-solved puzzle progress along with the mistake.
The old `_verify_blocks` regeneration net (world.py:343) that used to catch
zero-push blocks now only runs on grid entry (spec 0048), so a mid-play
self-wedge has no in-game recovery at all.

BL-37 makes the game **self-healing** with respect to push puzzles: a doomed
block visibly reacts — an animated countdown, then an explosion — and respawns
at its start. With that in place, the on-death block reset becomes redundant and
actively harmful (it discards solved progress), so it is removed in the same
change.

## Decisions (resolved 2026-07-12)

1. **Fuse model — per-push, non-cancelling.** Detection runs right after a
   successful push; a lit fuse always detonates and is not re-checked each tick
   or cancelled if a later gate/bridge change would have freed the block. (The
   rejected alternative was a per-tick re-evaluated, cancel-if-freed fuse.)
   Consequence: a doom created by a *non-push* event — e.g. a gate closing onto
   a block's only lane — is not detected. Accepted as out of scope; dooms in
   practice are created by pushes.
2. **Detection criterion — true multi-block solvability (Daniel, refined).** A
   block is doomed iff, from the current live configuration, there is **no**
   sequence of legal pushes that lands it on any plate — where other blocks may
   themselves be pushed aside (a movable obstruction does **not** make a block
   doomed) and passability is the live `World.blocked` (open gates, built
   bridges count). Target = **any** plate in the room, because no block→plate
   pairing is stored (levellayout.py:2900 stores bare block positions) and the
   generator's own dead-square set already targets all plates
   (levellayout.py:2915). Recomputed after every push of every block.
   *Residual (accepted):* a joint deadlock where each block can individually
   reach some plate but not all simultaneously (tile contention) is not flagged.
   The criterion never ignites a block that could still be useful — the property
   Daniel asked for — at the cost of missing this rare joint case.
   (The rejected alternatives were local "zero push directions" and a
   "freeze all other blocks" dead-square test, both of which false-positive on a
   movable obstruction.)
3. **Respawn when home is occupied — relocate to nearest open tile.** If the
   block's start tile is free at detonation it respawns there; otherwise the
   nearest open tile (BFS over unblocked tiles from the start), excluding the
   player's tile. (Rejected: hold the explosion pending until home clears.)
4. **Remove the on-death `_reset_blocks` path.** Dying no longer resets blocks
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

### A — Detection: runtime multi-block solvability

Detection answers, for each block, "can this block still reach a plate?" in the
**current** configuration, letting every block move (classic multi-block
Sokoban reachability), not the cheap local test. It runs after every successful
push, at the single push site — inside `_try_push_block`, after the block has
moved and before it returns `True`.

**One reachable-configuration BFS per push.** From the current room state, flood
the space of reachable multi-block configurations; a block is doomed iff it is
never on a plate in any reachable configuration.

```
state      = (sorted tuple of block positions, player-zone representative)
transition = one legal push of one block:
               • player can reach the push-from side (the zone touches it),
               • the destination tile is passable under the LIVE query
                 (World.blocked: walls, closed gates, unbridged water) and
                 not occupied by another block,
             then re-normalize the player zone around the moved block.
plates     = {(pc, pr) for pc, pr, _g in room.plates}

visited = BFS(all reachable states from the current state)
for each block b (by index):
    if no visited state has b's position ∈ plates:   # b can never reach a plate
        b is DOOMED
```

- Passability is the live `World.blocked` query — open gates and built bridges
  are traversable at evaluation time; never a private obstacle model (BL-13).
- A block already on a plate is on a plate in the *current* (hence reachable)
  state → not doomed. Plate/goal-state exclusion falls out for free.
- Reuse: `_compute_dead_squares` (permanent-wall dead squares,
  levellayout.py:1688) as a pruning filter, and the player-zone normalization
  from `_sokoban_bfs` (levellayout.py:1788). To avoid a `world → levellayout`
  dependency that drags generation code into the pygame-free runtime, lift the
  needed pure helpers (`_compute_dead_squares`, `_normalize_player`,
  `_player_reachable`) into a small shared module (e.g. `sokoban.py`) that both
  import. (Implementation detail; confirm during build.)
- Rooms are small and this runs only on a push (never per frame).

**Ignite** the doomed set (skip blocks that already carry a fuse):

```python
def _light_doomed_fuses(self):
    doomed = self._doomed_blocks()          # the BFS above
    for b in doomed:
        if b.fuse is None:
            b.fuse = BLOCK_FUSE_MS
            self._emit('block_fuse_lit', b.col, b.row)
```

### Geometry (confirm before code — geometry rule)

`#` wall/blocked, `.` open floor, `A`/`B` blocks, `T` plate (target). A push of
a block in direction `d` is legal when the player can stand on the near side
(`pos − d`, reachable) and the far side (`pos + d`, the destination) is passable
and unoccupied.

**(1) Single-block corner wedge — DOOMED.** One block, no partner:

```
      c0 c1 c2 c3
  r0   #  #  #  #
  r1   #  B  .  #
  r2   #  .  .  #
  r3   #  #  #  #
```
`B(1,1)` can only be pushed right (player at `(0,1)`=# — impossible) or down
(player at `(1,0)`=# — impossible); left/up destinations are walls. `B` cannot
move at all, so it never reaches a plate → **doomed** → ignites.

**(2) Mutual wedge — BOTH DOOMED.** Two blocks jam each other against a wall;
neither can move, so neither can free the other:

```
      c0 c1 c2 c3 c4 c5
  r0   #  #  #  #  #  #
  r1   #  .  A  B  .  #
  r2   #  .  .  .  .  #
  r3   #  #  #  #  #  #
```
`A(2,1)`: up `(2,0)=#`; down needs player at `(2,0)=#`; left needs player at
`(3,1)=B` (occupied); right destination `(3,1)=B` (occupied). `A` cannot move.
By symmetry `B(3,1)` cannot move. Neither reaches a plate under *any* push order
→ **both doomed** → both ignite from the one push that jams them.

**(3) Movable obstruction — NOT DOOMED.** `A` is blocked by `B`, but `B` can be
shoved aside, so `A` can still reach the plate `T`:

```
      c0 c1 c2 c3 c4 c5
  r0   #  #  #  #  #  #
  r1   #  .  .  .  .  #
  r2   #  A  B  .  T  #
  r3   #  .  .  .  .  #
  r4   #  #  #  #  #  #
```
`A(1,2)`, `B(2,2)`, plate `T(4,2)`. `B` can be pushed **up**: player stands at
`(2,3)` (south, reachable), `B` moves `(2,2) → (2,1)` (open). Now `A`'s right is
clear and `A` can be pushed right along row 2 toward `T`. The BFS reaches a
state with `A` on `T`, so `A` is **not doomed** — nothing ignites. (This is the
case the local "zero push directions" / freeze-others tests get wrong.)

**(4) Plate exclusion — NOT DOOMED.** A block sitting on a plate is already on a
target in the current state → not doomed, even if it cannot move:

```
      c0 c1 c2 c3
  r0   #  #  #  #
  r1   #  B  .  #      B(1,1) sits on plate T=(1,1): already on a plate
  r2   #  .  .  #      -> not doomed, no fuse.
  r3   #  #  #  #
```

### B — Fuse state + constant

`Block` (entities.py) is an `Entity` with no `__slots__`, so add per-instance
state in `__init__`: `self.fuse = None` (None = inert; an int = remaining ms).
New constant in `constants.py`:

```python
BLOCK_FUSE_MS = 1500   # doomed-block explosion countdown (tunable at acceptance)
```

### C — Update tick system (pinned order)

A new system in `World.update` decrements every block's fuse and detonates at
zero. It **moves blocks** (respawn), which changes passability and plate
occupancy, so it runs **before** the `_latch_channels` plate pass (gate state
reflects the same tick's detonations):

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

`blocks_initial` is captured per room at construction (rooms.py:24), positionally
aligned with `room.blocks`. `_block_respawn_tile(home)` returns `home` if it is
open and not the player's tile, else the nearest open non-player tile by BFS
from `home` (blocks count as blocked, so it never lands on another block).
Enemies are excluded by the room invariant, not by an explicit check.

### E — Remove the on-death block reset (Decision 4)

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

- **Single wedge ignites & explodes:** push a block into a corner it cannot
  leave; assert `b.fuse` is set and a `block_fuse_lit` fired; advance `update`
  past `BLOCK_FUSE_MS`; assert a `block_exploded` fired and the block is back at
  its start.
- **Mutual wedge — both ignite:** arrange config (2) above; the push that jams
  them lights a fuse on **both**; both explode and return to their starts.
- **Movable obstruction — nothing ignites:** arrange config (3); after the push,
  assert **no** block is fused (the obstructing block can be shoved aside, so
  the puzzle stays solvable).
- **Block on a plate never ignites:** a block parked on its plate (config 4) is
  never fused, even if immovable; its gate stays open.
- **Bridged/gated lane counts as open:** a block whose only route to a plate
  crosses a now-open gate (channel high) is not doomed — detection uses live
  `World.blocked`.
- **Fuse is non-cancelling:** light a fuse, then (artificially) open a gate that
  would make the block solvable again; the fuse still detonates (Decision 1).
- **Respawn relocates when home blocked:** occupy the block's start tile (place
  a wall / park another block), detonate; assert it lands on the nearest open
  tile, never on the player or another block.
- **On death, blocks are NOT reset:** solve a puzzle (park a block on its
  plate), move another block, then a non-fatal `_lose_life`; assert blocks stay
  where they are (solved plate block still on the plate, its gate still open)
  and only the player + enemies reset (spec 0067 untouched).
- **Entrance persists across death (new mechanism):** open the entrance, die;
  assert `ENTRANCE_CHANNEL` still latched and the entrance still open — via
  `_channels` untouched, not `_reset_blocks`.
- **System order:** the block-fuse system runs before `_latch_channels` — a
  detonation that moves a block off a plate closes its gate the same tick.

## Manual verification

- `poe run` an Act 2 level with a push puzzle: push a block into a wall corner
  it can't leave → it flashes a countdown, explodes, and reappears at its start.
- Jam two blocks so neither can move → both count down and explode together.
- Obstruct a block with another block that can still be shoved aside → nothing
  ignites; solve the puzzle normally.
- Park a block on its plate (solve the puzzle) → no countdown starts; the gate
  stays open.
- Solve a puzzle, then die on that grid → the solved puzzle is preserved (block
  still on the plate, gate still open); player and enemies reset as before.
- Open the entrance (collect all awards), then die → the entrance is still open
  on respawn.

## Done when:

- [ ] `World._doomed_blocks` runs a multi-block reachability BFS from the live
      configuration and returns every block that cannot reach any plate (other
      blocks free to move; live `World.blocked` passability); pure helpers lifted
      to a shared module to keep the runtime free of generation imports
- [ ] A successful push ignites every newly-doomed block (`BLOCK_FUSE_MS` fuse,
      `block_fuse_lit` per block); a block obstructed only by a movable block is
      not ignited; a block on a plate is never ignited
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
- [ ] User confirms in-game: single and mutual wedges explode back to their
      starts; a movable obstruction never ignites; plate-parked blocks never
      ignite; dying preserves solved puzzle progress (manual acceptance)
