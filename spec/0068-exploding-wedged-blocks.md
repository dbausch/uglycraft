# 0068 — Doomed push-blocks explode and respawn; per-plate safe tiles; on-death block reset removed (BL-37)

## Status

- [ ] Each **plate object owns its `safe_tiles`** (Daniel): the room-floor
      tiles from which a block can still be pushed to *that* plate, stored on the
      plate fixture — not in a position-keyed map beside it. The room's safe area
      is a property that unions over its plate objects. These tiles are
      **tinted**, and a block pushed **out of** the safe area is what *ignites*
- [ ] Pushing a block is **no longer blocked**: a block *may* be pushed onto a
      tile outside the safe area — the consequence is that it now *ignites*
      (Daniel). The old unsafe-tile push guard in `_try_push_block` (world.py:479)
      is removed
- [ ] A block **can never be pushed off its room's floor tiles** (Daniel):
      confinement to the block's own room (via `tile_owner`; Act 1 = the whole
      interior)
- [ ] Detection is a **static safe-set membership check** (Daniel): the safe
      set is fixed (single block, confined to its room, temporary obstacles
      ignored), so **no per-push recomputation** — after a push, a block whose
      tile is **not** in any plate's safe set is doomed and ignites
- [ ] Each plate's `safe_tiles` is computed once (at plate build) by
      reverse-reachability from the plate over permanent walls, restricted to its
      room floor — a pure `reverse_reachable(passable, target)` helper
- [ ] A block **on a plate is always safe** (a plate is the reverse-reachability
      seed, so it is in its own `safe_tiles`) — the goal-state exclusion, free
- [ ] Fuse is a **5-second, non-cancelling** countdown (Decision 1): the block
      **stays movable** during it but can never re-enter the safe area (proven
      below), so the fuse always runs to detonation
- [ ] The fused block **blends from its normal look to a red glow** over the 5 s
      (keyed on the remaining fuse), then plays a short **4-frame fiery blast**
      at detonation
- [ ] Each exploding block **deducts `BLOCK_EXPLOSION_PENALTY` (500) points**
      (Daniel), floored at 0 — mirrors `LIFE_PENALTY`
- [ ] On detonation the block respawns at its **start tile** if free, else at
      the **nearest open tile** (Decision 4); it never materialises on the
      player or another block (enemies never share a push-puzzle room — R-P9)
- [ ] `World.update` gains a **block-fuse system** slotted explicitly into the
      pinned system order (spec 0052 G5); the contract note is updated
- [ ] Two new world events — `block_fuse_lit` and `block_exploded` — mapped to
      new SFX in `game.py` (drive the glow start and the blast)
- [ ] The **on-death `_reset_blocks` path is removed** (Decision 6): dying no
      longer resets blocks or closes plate-gates; `_lose_life` keeps the spec
      0067 player + enemy reset. Gates self-correct via the per-tick latch; the
      open entrance persists because `_channels` is left untouched on death
- [ ] `_reset_blocks` and its four locking tests (`test_registry`,
      `test_rooms`, `test_dispatch`, `test_entrance_exit`) are removed or
      rewritten; entrance-persists-across-death is re-pinned
- [ ] New tests red before the change, green after; `poe test` exits 0 with any
      affected goldens deliberately re-recorded
- [ ] Manual check: push a block out of the tinted safe area → it counts down,
      deducts 500, explodes, and respawns at its start; a block can't be pushed
      out of its room; die on a solved grid → the solved puzzle is preserved
      (user acceptance)

## Problem

Today a block pushed toward a tile from which the puzzle becomes unsolvable is
*prevented* from moving there (`_try_push_block` refuses tiles outside the safe
area), and a genuinely stuck block just stays stuck. The only recovery is death,
which
triggers `_reset_blocks` (world.py:708) — a blunt instrument that resets **all**
blocks and closes all plate-gates, wiping legitimately-solved puzzle progress
along with the mistake.

BL-37 makes the game **self-healing** and less fiddly: a block may be pushed
anywhere in its room; if that pushes it out of the safe area, it visibly
reacts — an animated countdown, a 500-point penalty, an explosion — and respawns
at its start. With that in place, the on-death block reset becomes redundant and
actively harmful (it discards solved progress), so it is removed in the same
change.

## Decisions (resolved 2026-07-12)

1. **Fuse model — 5 s, per-push, non-cancelling.** Detection runs right after a
   successful push; the fuse (`BLOCK_FUSE_MS = 5000`) always runs to detonation
   and is not re-checked each tick. The block **remains movable** while it burns.
   *Why that is safe (invariant):* the safe area is exactly the tiles from which
   a block can be pushed to the plate; if a block is already outside it, every
   tile one push away is also outside it (otherwise the current tile would reach
   the plate too). So a fused block can only move among unsafe tiles — it can
   never be pushed back into the safe area, and cancelling would be pointless.
2. **Push mechanics — allow leaving the safe area, confine to the room (Daniel).**
   - Remove the guard that refused pushes outside the safe area
     (`_try_push_block`, world.py:479): a block may be pushed anywhere in its
     room, including out of the safe area; it ignites as a consequence.
   - Add **room-floor confinement**: reject a push whose destination leaves the
     block's room floor (same `tile_owner`; Act 1's interior is one room and the
     existing interior-bounds check already confines).
3. **Representation — `safe_tiles` on each plate object (Daniel).** The data
   lives **on the plate fixture** as `plate.safe_tiles`: the room-floor tiles
   from which a block can be pushed to that plate (reverse-reachability over
   permanent walls, restricted to that plate's room). No position-keyed map
   beside the plates. The room's safe area is a **property** unioning over its
   plate objects. Because the block is single, confined, and temporary obstacles
   are ignored, each `safe_tiles` is **fixed** — computed once when the plate is
   built, never recomputed per push. Detection: a block is doomed iff its tile
   is **not** in the room's safe area (it can reach no plate). Target = any plate
   (no block→plate pairing is stored, levellayout.py:2900).
4. **Respawn when home is occupied — relocate to nearest open tile.** If the
   start tile is free at detonation it respawns there; otherwise the nearest
   open tile (BFS from the start, excluding the player's tile).
5. **Score penalty — 500 points per exploding block.** `BLOCK_EXPLOSION_PENALTY
   = 500` (mirrors `LIFE_PENALTY`), deducted per block at detonation, floored
   at 0.
6. **Remove the on-death `_reset_blocks` path.** Dying no longer resets blocks
   or closes plate-gates. The spec 0067 player + enemy reset stays. Gates
   recompute via the per-tick `_latch_channels`; the open entrance survives
   because `_channels` is left untouched on death.
7. **Tinting = the safe set.** The floor pattern marks the union safe area (only
   room tiles). Non-puzzle rooms (no plate) get plain floor.

**Residuals (accepted):** the safe set ignores (a) player reachability and
(b) temporary obstacles, so detection *under*-detects — a block stranded by a
not-yet-built bridge or a player-access quirk on a nominally-safe tile is not
ignited. And in a hypothetical multi-puzzle room the sets ignore the other
block. None occur with the current one-puzzle-per-room levels; the common case
is exact and cheap. Detection never *falsely* ignites a block still inside the
safe set.

### Room invariant relied upon

**Enemies and push puzzles never share a room** (R-P9, `kb/requirements.md`;
`_distribute_enemies` excludes any node with `node.blocks or node.plates`,
levellayout.py:2525). So an exploding block's respawn need only avoid the
**player** and **other blocks** — never an enemy.

## Design

### A — Representation: `safe_tiles` on the plate object

A plate is a `Fixture` object (cells.py:87, `kind='plate'`, `payload=channel`).
Give the plate its own `safe_tiles: frozenset` and compute it **when the plate
is built** — no external map, no position key. The pure helper:

```python
def reverse_reachable(passable, target):
    """Tiles from which a block can be pushed to `target` (reverse-BFS:
    a block at Q could have been pushed from Q−d with the player at Q−2d,
    when both are passable)."""
    reach, q = {target}, deque([target])
    while q:
        bx, by = q.popleft()
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            origin, stood = (bx - dc, by - dr), (bx - 2*dc, by - 2*dr)
            if origin in passable and stood in passable and origin not in reach:
                reach.add(origin); q.append(origin)
    return frozenset(reach)
```

Populate at room build (in `build_room_cells` / a post-pass on `RoomCells`,
which knows the room's permanent walls and floor): for each plate fixture,
`plate.safe_tiles = reverse_reachable(perm_passable, plate_pos) & room_floor`.
`perm_passable` = interior tiles minus permanent (reinforced) walls;
`room_floor` = tiles owned by the plate's room. This lives on the object, so it
serializes nowhere and never appears in a room-data key or a golden dump.

`Room` exposes the union as a computed property:

```python
@property
def safe_tile_set(self):
    return frozenset().union(
        *(f.safe_tiles for _, f in self.cells.fixtures_of_kind('plate')))
```

`World._safe_tiles → self.room.safe_tile_set`. (If a typed home reads better
than a field on the generic `Fixture`, a dedicated `Plate` fixture is a fine
alternative — the point is the set lives on the plate, not in a keyed map.)

### B — Push mechanics + detection (`_try_push_block`)

Destination test becomes (in-bounds ∧ not blocked ∧ **within the block's room
floor**); then the doom check fires:

```python
nc, nr = bc + dcol, br + drow
if (not self.blocked(nc, nr)
        and (nc, nr) in self._room_floor(bc, br)):   # confinement (Decision 2)
    block.col, block.row = nc, nr
    self._emit('bumped')
    self._light_doomed_fuses()                        # detection (Decision 3)
    return True
return False

def _light_doomed_fuses(self):
    safe = self._safe_tiles                            # room.safe_tile_set
    for b in self.room.blocks:
        if b.fuse is None and (b.col, b.row) not in safe:
            b.fuse = BLOCK_FUSE_MS
            self._emit('block_fuse_lit', b.col, b.row)
```

`_room_floor(c, r)` = floor tiles sharing `(c, r)`'s `tile_owner` (else
`INTERIOR_TILES` on Act 1); cache per owner. A block *on a plate* is in that
plate's safe set (the flood seed), so it is always safe.

### Geometry (confirm before code — geometry rule)

Legend (same for every diagram): `#` = permanent wall; `T` = the plate (the
goal — always safe, it is the reverse-reachability seed); `S` = **safe** floor
tile (a block here can still be pushed to the plate → **tinted**); `x` =
**unsafe** floor tile (a block here can never reach the plate → pushing a block
onto it lights the fuse). The **room** is every `T`/`S`/`x` tile; the **safe
area** is `T` + `S`. Every map below is *computed* by reverse-reachability
(`origin = Q−d`, player `stood = Q−2d`, both passable), not eyeballed.

A push along `d` needs the player able to stand behind the block (at `pos−d`)
and the destination `pos+d` passable — so a tile is safe only if a *chain* of
such pushes reaches `T`.

**(1) Rectangular room, plate in a corner.** The safe area is the upper-left
block; the far column and far row are unsafe (no room to stand behind the block
to push it back toward `T`):

```
     c0 c1 c2 c3 c4 c5
  r0  #  #  #  #  #  #
  r1  #  T  S  S  x  #
  r2  #  S  S  S  x  #
  r3  #  x  x  x  x  #
  r4  #  #  #  #  #  #
```

**(2) Plate in open space has a *small* safe area.** With `T` mid-room and walls
on all four sides, the block can only be pushed onto `T` along the one row where
the player can stand behind it — so only three tiles are safe:

```
     c0 c1 c2 c3 c4 c5 c6
  r0  #  #  #  #  #  #  #
  r1  #  x  x  x  x  x  #
  r2  #  x  S  T  S  x  #
  r3  #  x  x  x  x  x  #
  r4  #  #  #  #  #  #  #
```

**(3) Non-rectangular / maze room (a spur wall).** The safe area threads around
the interior wall; the tint shows the viable corridor:

```
     c0 c1 c2 c3 c4 c5 c6
  r0  #  #  #  #  #  #  #
  r1  #  T  S  S  S  x  #
  r2  #  S  #  #  #  x  #
  r3  #  x  x  x  x  x  #
  r4  #  #  #  #  #  #  #
```

**(4) Confinement — refused at the room boundary (ownership, not walls).** Two
rooms in one grid: room `a` (owner A) and room `b` (owner B), joined by a
doorway `D`. The block `O` may be pushed among `a` tiles, but a push whose
destination is `D` or a `b` tile is refused — it can never leave its room:

```
     c0 c1 c2 c3 c4 c5 c6      A = room-a floor, B = room-b floor,
  r0  #  #  #  #  #  #  #      D = doorway (owner B), O = the block (in room A)
  r1  #  a  a  a  #  b  #
  r2  #  a  O  a  D  b  #      pushing O onto D (owner B) is refused
  r3  #  a  a  a  #  b  #
  r4  #  #  #  #  #  #  #
```

**Maze note (for the planned maze).** The safe area *is* exactly the set of
block positions from which the puzzle is still solvable, so the intended
solution path is always fully safe. Sokoban pushing needs clearance *behind* the
block, so geometry matters:

- **1-wide winding corridors collapse the safe area toward nothing** (the player
  can't get behind the block at a bend) — such a maze would ignite a block
  almost anywhere and isn't even solvable. Avoid.
- **2–3-tile-wide floor with a few turns keeps most of the room safe** — e.g. a
  2-wide L keeps 11 of 16 floor tiles safe (only the dead corners are unsafe):

```
     c0 c1 c2 c3 c4 c5 c6
  r0  #  #  #  #  #  #  #
  r1  #  T  S  S  S  x  #
  r2  #  x  S  S  S  x  #
  r3  #  #  #  S  S  #  #
  r4  #  #  #  S  S  #  #
  r5  #  #  #  x  x  #  #
  r6  #  #  #  #  #  #  #
```

Generation's existing solvability guarantee (block start + solution stay
reverse-reachable) keeps any maze in the solvable class; the tint reveals the
viable region to the player.

### C — Fuse state + constants

`Block` (entities.py) is an `Entity` with no `__slots__`; add `self.fuse = None`
(None = inert; int = remaining ms). New constants in `constants.py`:

```python
BLOCK_FUSE_MS = 5000           # 5 s red-glow countdown before a doomed block blasts
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

- **Floor tint = safe area** (`game.py`, line 528): tint `self._safe_tiles` (the
  room's safe area) instead of the old unsafe-tile tint. Render the pattern
  sprite on those tiles, plain floor elsewhere. Rename the tint sprite key to
  `safe_floor`.
- **Sound** (`sounds.py`): add `sfx_block_fuse` (short rising tick) and
  `sfx_block_explode` (noise burst); register both.
- **Event map** (`game.py` `_EVENT_SOUNDS`, line 178): `'block_fuse_lit' →
  'block_fuse'`, `'block_exploded' → 'block_explode'`.
- **Red-glow blend** (`game.py` block draw loop, line 582; `sprites.py`): when
  `b.fuse` is not None, draw the block blended from its normal appearance toward
  a **red glow** by `glow = 1 − b.fuse / BLOCK_FUSE_MS` (0 at ignition → 1 at
  detonation). Either pre-render the glow sprite and alpha-blit it over the base
  at `glow`, or tint procedurally in `sprites.py`.
- **4-frame blast** (`sprites.py` + `game.py`): add a **4-frame fiery
  explosion** sprite sequence. On `block_exploded`, start a timer-driven overlay
  at the emitted position that steps through the 4 frames once (≈exploding over
  a few hundred ms), then clears. Runs like the existing screen-flash timer;
  purely presentational, driven by the world event.

## Tests (world-level, pygame-free unless noted)

- **Plate owns its safe tiles:** each plate fixture exposes `plate.safe_tiles`
  containing the plate tile and excluding an unreachable corner;
  `room.safe_tile_set` is the union over the room's plate objects.
- **Leaving the safe set ignites:** push a block onto a tile not in
  `safe_tile_set` (previously refused); assert the push *succeeds*, `b.fuse` is
  set, and `block_fuse_lit` fired.
- **Confinement:** attempt to push a block off its room floor; assert the push
  is refused and the block does not move.
- **Explode + penalty + respawn:** advance `update` past `BLOCK_FUSE_MS`; assert
  `block_exploded` fired, `score` dropped by 500 (floored at 0), block back at
  its start.
- **Block on a plate never ignites:** a block on its plate is in the safe set →
  never fused; its gate stays open.
- **Inside the safe set stays safe:** push a block onto a safe tile; assert it
  is not fused.
- **Fused block stays movable but can't re-enter safe area:** after a block is
  fused, push it again; assert the push succeeds, the fuse is unchanged (not
  re-lit, not cancelled), and its new tile is still outside `safe_tile_set`.
- **Respawn relocates when home blocked:** occupy the start tile, detonate;
  assert nearest open tile, never on the player or another block.
- **On death, blocks are NOT reset:** solve a puzzle, move another block,
  non-fatal `_lose_life`; assert blocks stay put and only player + enemies reset.
- **Entrance persists across death (new mechanism):** open the entrance, die;
  assert `ENTRANCE_CHANNEL` still latched via `_channels` untouched.
- **System order:** the block-fuse system runs before `_latch_channels`.
- **Safe-tile tint (rendering):** the tinted set equals `room.safe_tile_set`; a
  non-puzzle grid tints nothing.

## Manual verification

- `poe run` an Act 2 push-puzzle level: push a block out of the tinted safe area
  → over ~5 s it glows red, then blasts (4-frame animation), the score drops
  500, and it reappears at its start.
- Try to push a block through a doorway out of its room → it won't move past the
  room edge.
- Observe the floor tint: the **safe** placement tiles are patterned.
- Park a block on its plate (solve the puzzle) → no countdown; the gate stays
  open.
- Solve a puzzle, then die on that grid → the solved puzzle is preserved; player
  and enemies reset as before.
- Open the entrance (collect all awards), then die → the entrance is still open.

## Done when:

- [ ] Each plate fixture owns `plate.safe_tiles` (reverse-reachable room tiles),
      computed once at build; `Room.safe_tile_set` (a property over the plate
      objects) and `World._safe_tiles` surface the union — no position-keyed map
- [ ] `_try_push_block` drops the old unsafe-tile guard and adds room-floor
      confinement; a block may leave the safe area but never its room
- [ ] `_light_doomed_fuses` ignites any block whose tile is not in
      `safe_tile_set` (no per-push recomputation); a block on a plate is always
      safe
- [ ] `_tick_block_fuses` decrements fuses at the pinned slot (before
      `_latch_channels`); at zero the block deducts `BLOCK_EXPLOSION_PENALTY`,
      emits `block_exploded`, and respawns at its start else the nearest open
      non-player tile
- [ ] Floor tinting marks `room.safe_tile_set` (the safe area)
- [ ] On-death `_reset_blocks` call and method removed; `_lose_life` keeps the
      0067 player + enemy reset; gates self-correct via the latch; the open
      entrance persists (`_channels` untouched)
- [ ] The four `_reset_blocks`-locking tests removed/rewritten;
      entrance-persists-across-death re-pinned
- [ ] `block_fuse_lit` / `block_exploded` mapped to new SFX; the fused block
      blends toward a red glow over the 5 s and plays a 4-frame fiery blast at
      detonation; the block stays pushable while burning
- [ ] New tests red first, then green; `poe test` exits 0 with any affected
      goldens deliberately re-recorded
- [ ] User confirms in-game: a block pushed out of the safe area counts down,
      costs 500, explodes, and respawns; blocks can't be pushed out of their
      room; safe tiles are the tinted ones; dying preserves solved puzzle
      progress (manual acceptance)
