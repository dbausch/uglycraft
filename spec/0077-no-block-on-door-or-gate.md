# Spec 0077 — Unify opened doors into the cell model (delete `_opened_doors`)

Backlog: **BL-57 (P2)**. A tester found that pressing SPACE while standing on a
tile that holds a **door** or **gate** builds a `'placed'` block there anyway —
hidden under the later-drawn fixture, or (for an open gate) destroying the gate.

The minimal fix would be a placement predicate that special-cases both the cell
model *and* the parallel `self._opened_doors` set. That predicate is hacky for a
diagnosable reason: **opened doors leave the cell model** and live in a global
side-table only the renderer reads, so any consumer that asks "is there a
door/gate here?" must consult two representations. This is the P1/P3 pain the
world-model review flags (→ `kb/world-model-review.md` §2, §5).

This spec fixes the **root cause** instead: make an opened door behave like an
open gate — the fixture *stays* in the cell, only its passability changes
(`kb/world-model-review.md` §5's governing principle: *store identity and
structure, derive state by query*). `self._opened_doors` is then **deleted**,
and the BL-57 placement refusal collapses to a single authoritative lookup.

## Status checklist

- [ ] **D1** — `Barrier` gains an `opened: bool = False` field; `Barrier.blocks()`
  returns `not self.opened` for `kind == 'door'` (a closed door blocks, an opened
  door is passable — mirrors the gate's channel check).
- [ ] **D2** — `_try_auto_open_door` sets `barrier.opened = True` (keeping the
  barrier) instead of `cells.remove_barrier(...)` + `self._opened_doors.add(...)`.
- [ ] **D3** — `self._opened_doors` is removed entirely (world init line 349, the
  `_try_auto_open_door` write, and the `_WORLD_ATTRS` delegation in `game.py`). A
  new `World.door_opened(room_key, pos)` query reads the door barrier's `opened`
  from that room's live cells (`self._rooms`), returning `False` for an unbuilt
  room — reproducing the old set-membership semantics, including cross-room.
- [ ] **D4** — Rendering: the open-door draw folds into the existing
  `cells.barriers('door')` loop (`door_open_{o}` iff `door.opened`, else the closed
  `door_{colour}_{o}`); the separate `for … in self._opened_doors` render loop is
  deleted; `border_exit_sprite` reads `world.door_opened(home_room, tile)` instead
  of the `opened_doors` set argument.
- [ ] **D5** — `_place_block` refuses on any door/gate tile via a single predicate
  `b = cells.barrier(c, r); b is not None and b.kind in ('door', 'gate')` —
  covering the open gate, the entrance gate, and the opened door — emitting
  `'action_denied'` and spending no credit. The open-gate-destruction bug is fixed
  by the same guard (the gate barrier is no longer overwritten).
- [ ] **D6** — All other placement/door/gate behaviour is unchanged: credit gate,
  `blocked(c, r)` gate, respawn-tile gate, bare-floor placement, passability of an
  opened door, cross-room border-door rendering, door persistence across death
  (spec 0067), and door re-closing on level (re)start.
- [ ] **D7** — Verification: pygame-free `tests/test_world.py` asserts the refusal
  at an open-gate tile and an opened-door tile, that bare-floor placement still
  succeeds, and that `door_opened` persists across a death and resets on level
  start; the full suite is green and the goldens stay **byte-identical** (no
  re-record).
- [ ] **D8** — Daniel confirms in-game that a block can no longer be built on an
  open door/gate (denial sound fires, nothing is hidden, the gate is not
  destroyed) and that opened doors still render open on both sides of a border.

## Background — confirmed facts

Established by reading the code (self-contained; do not re-derive):

### The door/gate asymmetry (the root cause)

A **gate** that opens follows the cell model correctly: `_update_pressure_plates`
latches its channel high; the `'gate'` barrier **stays** in the cell and
`Barrier.blocks(channels)` returns `self.channel not in channels` = `False`
(`cells.py:137`). Passability is *derived* from a fixture that never leaves the
model.

A **door** that opens does the opposite. `_try_auto_open_door` (`world.py:574`):

```python
def _try_auto_open_door(self, col, row):
    barrier = self.cells.barrier(col, row)
    if barrier is None or barrier.kind != 'door':
        return False
    if not self.inventory.has_key(barrier.colour):
        return False
    self.inventory.use_key(barrier.colour)
    self.cells.remove_barrier((col, row))                     # ← fixture deleted
    self._opened_doors.add(                                   # ← copy stashed
        (self._current_room, col, row, barrier.colour))       #   in a global set
    self._emit('door_opened')
    return True
```

The authoritative fixture is **removed** and a positional copy is pushed into
`self._opened_doors` — a global set keyed `(room_key, col, row, colour)`
(`world.py:349` init, reset per level in `start_level`). Everything downstream
then needs the side-table: the renderer's open-door loop, `border_exit_sprite`,
and (in the naive BL-57 fix) the placement guard.

### Why a door/gate tile is reachable by SPACE at all

`_place_block` already guards `not self.blocked(c, r)`, so a *closed* door/gate is
safe. The problem is the tiles that are **passable yet still carry (or represent)
a door/gate fixture**:

- **Open gate** — barrier present, channel high, so passable. `set_barrier`
  (`cells.py:274`) **overwrites** the gate with `'placed'`; the gate overlay loop
  (`game.py:595`) no longer finds it → the gate silently disappears and the tile
  becomes a permanent block.
- **Level entrance gate** — a `'gate'` barrier on `ENTRANCE_CHANNEL`
  (`cells.py:378`). `_open_entrance` (`world.py:736`) latches the channel high (does
  **not** remove the barrier); once all awards are collected the tile is passable.
  A block placed there is drawn by the base pass, then the entrance sprite
  (`game.py:559`) blits **on top** → block hidden.
- **Opened door** — `_try_auto_open_door` removed the barrier, so the tile is
  barrier-free (passable); the open-door sprite is drawn from `_opened_doors`
  (`game.py:651`) **after** the base pass → a block placed there is hidden under it.

### Border doors — why `_opened_doors` is *global* (and still derivable)

A border passage's real door lives in **one** room only. Stitching
(`levellayout.py:3455`) appends the door to `room_a['locked_doors']` at
`barrier_tile = _BORDER_TILE[exit_side](pos)` (a border tile on room_a's side) and
writes a render record `('locked', colour, home=(gname_a, barrier_tile))` onto
**both** rooms' `border_barriers` (never a real barrier on room_b — that would
block the return transition, `levellayout.py:3471`).

`border_exit_sprite` (`game.py:67`) renders that border tile open/closed by
testing `(home_room, hc, hr, param) in opened_doors` — a **cross-room** lookup:
standing in room_b, it consults whether room_a's door is open. This is the only
reason the set embeds the room key.

It is fully derivable. A door can only be opened while the player is *in* its
room (bump → `_try_auto_open_door`), so an opened door implies its room was
entered and is present in `self._rooms` (`world.py:311`, lazily built by
`_enter_room`, `world.py:382`). The membership test becomes a query:

```python
def door_opened(self, room_key, pos):
    room = self._rooms.get(room_key)
    if room is None:
        return False                       # unbuilt room ⇒ never opened
    b = room.cells.barrier(*pos)
    return b is not None and b.kind == 'door' and b.opened
```

There is exactly one door per tile, so room + pos identifies it uniquely (the old
`colour`/`param` arm matches by construction).

### Lifecycle: death persists opened doors, level start re-closes them

- **Death** (`_lose_life`, `world.py:769`) does **not** rebuild `_rooms` and does
  **not** clear `_opened_doors`; it re-enters the start room and keeps channels and
  blocks. Opened doors therefore persist across death. The persistent `opened`
  flag on the (un-rebuilt) barrier reproduces this exactly.
- **Level (re)start** (`start_level`, `world.py:296`) sets `self._rooms = {}` and
  `self._opened_doors = set()`; every room is rebuilt fresh from its dict on next
  entry, so all doors are closed again. Rebuilt barriers default to
  `opened == False` → identical.

### Draw order (why the block vanishes today)

For one tile the renderer paints, in order: (1) base pass — the `'placed'` block
sprite; (2) later overlays — entrance / open-door sprite on top. The block is
painted first and covered (open gate is the inverse: the gate barrier is
overwritten, so the gate vanishes and the block shows). All cases are eliminated
by **refusing the placement** — rendering itself is not changed by this spec
except for the door open/closed source of truth (D4).

## D1 — Opened door stays a barrier

Add `opened` to the `Barrier` dataclass (`cells.py`), appended so positional
construction (`Barrier('door', colour=colour)`) is unaffected:

```python
@dataclass
class Barrier:
    kind: str
    colour: str = None
    channel: str = None
    hits: int = 0
    opened: bool = False        # doors: latched open by key (spec 0077)

    def blocks(self, channels=frozenset()):
        if self.kind == 'gate':
            return self.channel not in channels
        if self.kind == 'door':
            return not self.opened          # closed door blocks; opened passable
        return True
```

`cells.blocked` (`cells.py:219`) already calls `b.blocks(channels)`, so an opened
door reports `not blocked` — byte-identical passability to today's removed
barrier. No change to `BARRIER_BUMP` (a passable opened door is walked onto, never
bumped, so the `'key'` action is unreachable for it; `_try_auto_open_door` also
short-circuits — see D2).

## D2 — Open the door in place; delete `_opened_doors`

```python
def _try_auto_open_door(self, col, row):
    barrier = self.cells.barrier(col, row)
    if barrier is None or barrier.kind != 'door' or barrier.opened:
        return False                        # opened guard is defensive
    if not self.inventory.has_key(barrier.colour):
        return False
    self.inventory.use_key(barrier.colour)
    barrier.opened = True                    # keep the fixture; derive passability
    self._emit('door_opened')
    return True
```

Remove `self._opened_doors = set()` from `start_level` (`world.py:349`). Add the
`World.door_opened(room_key, pos)` query shown in Background. Remove
`'_opened_doors'` from `_WORLD_ATTRS` (`game.py:1249`).

## D3 / D4 — Rendering reads the barrier, not the set

`game.py` `_render_field`, the door overlays (`game.py:646–655`) collapse to one
loop:

```python
for (dc, dr), door in self.cells.barriers('door'):
    o = self._door_orient(dc, dr)
    dkey = f'door_open_{o}' if door.opened else f'door_{door.colour}_{o}'
    if dkey in sp:
        self.surf.blit(sp[dkey], (dc * TILE, dr * TILE))
# (the separate `for ok, dc, dr, _color in self._opened_doors:` loop is deleted)
```

`border_exit_sprite` (`game.py:67`) drops the `opened_doors` parameter and, for a
`'locked'` record, calls the world query:

```python
if kind == 'locked':
    home_room, (hc, hr) = home
    if world.door_opened(home_room, (hc, hr)):
        return f'door_open_{orient}'
    return f'door_{param}_{orient}'
```

The `_render_field` call site (`game.py:575`) passes `self.world` instead of
`self._opened_doors`. Net pixels are identical: a border door's own room still
draws it via *both* the `cells.barriers('door')` loop and the border-exit loop
(as today), now agreeing through one source of truth.

## D5 — Single placement predicate

```python
def _is_door_or_gate_tile(self, c, r):
    """A door or gate fixture lives on (c, r) — open or closed.  Building a
    'placed' block here would hide the block under the later-drawn fixture, or
    overwrite (destroy) the gate (spec 0077 / BL-57), so placement is refused.
    Opened doors are still barriers now (D1), so one lookup covers every case."""
    b = self.cells.barrier(c, r)
    return b is not None and b.kind in ('door', 'gate')

def _place_block(self):
    c, r = self.player.col, self.player.row
    if (self._block_credits > 0 and not self.blocked(c, r)
            and not self._is_respawn_tile(c, r)
            and not self._is_door_or_gate_tile(c, r)):
        self._block_credits -= 1
        self.cells.set_barrier((c, r), Barrier('placed'))
        self._emit('block_placed')
    else:
        self._emit('action_denied')   # no credit / blocked / respawn / door-gate
```

No new event or sound: the existing `'action_denied'` → `'denied'` wiring
(spec 0074) carries the feedback.

## D6 — Preserve existing behaviour

Unchanged: the credit gate, the `blocked(c, r)` gate, the respawn-tile gate
(spec 0067), successful placement on bare floor, opened-door passability,
cross-room border-door rendering, opened-door persistence across death, and
door re-closing on level (re)start. The only new refusal is "player standing on a
door/gate tile"; the only structural change is that opened doors now live in the
cell model instead of `_opened_doors`.

## D7 — Verification

pygame-free unit tests in `tests/test_world.py`, using the existing
`tests/act2_fixtures.py` fixtures (`gate_level`, `door_level`) and the `_fixture`
/ `_restore` helpers already used by the spec-0074 denial tests:

1. **Open gate refused** — `gate_level`, latch the gate channel high
   (`w._channels.add('g1')`) so `(15, 8)` is passable; give a block credit; stand
   the player on `(15, 8)`; `place()` emits exactly `['action_denied']`, spends no
   credit, and the gate barrier at `(15, 8)` is still `kind == 'gate'`.
2. **Opened door refused** — `door_level`, give the player the red key, bump the
   door at `(15, 8)` to open it; assert the door barrier is now present with
   `opened is True` and the tile is passable (`not w.blocked(15, 8)`); give a block
   credit; stand on `(15, 8)`; `place()` emits `['action_denied']`, spends no
   credit, and **no** `'placed'` barrier appears (the barrier is still the door).
3. **Bare floor still works** — on a plain floor tile with a credit, `place()`
   still emits `['block_placed']` and sets a `'placed'` barrier (guards the
   predicate against false positives).
4. **`door_opened` lifecycle** — after opening the door, `w.door_opened(room, (15,
   8))` is `True`; force a death (`w._lose_life()` with `lives > 1`) and assert it
   is still `True` (persistence, spec 0067); call `w.start_level(w.level)` and
   assert it is `False` (re-closed on level start).

Full suite stays green; goldens stay **byte-identical** — `'door_opened'` still
emits, open-door screenshots are pixel-identical, and no golden run places a block
on a door/gate.

## Out of scope

- **BL-58** — building a block on a *border passage* tile draws it with the
  border-wall sprite. Separate item, separate design question.
- Re-modelling doors as channel-driven (a door as a gate on a per-door latched
  channel). A boolean `opened` is the honest representation — doors open
  permanently by key match, not by a plate — and keeps the diff minimal.
- Allowing a block to *re-seal* an open gate/door (deliberately not a feature).
- Ray-cast / z-ordering changes to how any fixture is drawn.

## Done when:

- [ ] **D1** — `Barrier.opened` exists; `blocks()` returns `not opened` for doors;
  passability of an opened door is byte-identical to today.
- [ ] **D2** — `_try_auto_open_door` opens in place; `self._opened_doors` is gone
  from world init, the open path, and `_WORLD_ATTRS`.
- [ ] **D3** — `World.door_opened(room_key, pos)` reproduces the old cross-room
  set-membership, including `False` for an unbuilt room.
- [ ] **D4** — the open-door render folds into the `cells.barriers('door')` loop,
  the `_opened_doors` render loop is deleted, and `border_exit_sprite` reads the
  world query; rendered pixels are unchanged.
- [ ] **D5** — `_place_block` refuses on any door/gate tile via the single
  predicate, emitting `'action_denied'` and spending no credit; the open-gate is no
  longer destroyed.
- [ ] **D6** — every pre-existing placement/door/gate behaviour (D6 list) is
  unchanged.
- [ ] **D7** — the four `test_world.py` cases pass; full suite green; goldens
  byte-identical (no re-record).
- [ ] **D8** — Daniel confirms in-game (no block on an open door/gate; denial sound
  fires; nothing hidden; gate not destroyed; border doors render open both sides).
