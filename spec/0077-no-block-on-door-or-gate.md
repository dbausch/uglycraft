# Spec 0077 — No block placement on a door or gate tile

Backlog: **BL-57 (P2)**. A tester found that pressing SPACE while standing on a
tile that holds a **door** or **gate** builds a `'placed'` block there anyway.
The door/gate fixture is drawn *after* the base tile pass, so the block ends up
hidden underneath it (or the fixture is silently destroyed). Fix: **refuse the
placement** at those tiles and play the shared "action denied" SFX
(spec 0074 / BL-52), exactly as the other refused-placement cases already do.

## Status checklist

- [ ] **D1** — `_place_block` refuses when the player's tile holds a door or gate
  fixture (an open gate, the level entrance gate, or an opened door), emitting
  `'action_denied'` and spending no credit.
- [ ] **D2** — All existing placement/denial behaviour is unchanged (credit gate,
  blocked-tile gate, respawn-tile gate, successful placement on bare floor).
- [ ] **D3** — Verification: pygame-free `tests/test_world.py` asserts the refusal
  at an open-gate tile and an opened-door tile, and that a bare-floor placement
  still succeeds; full suite green, no golden re-record.
- [ ] **D4** — Daniel confirms in-game that a block can no longer be built on an
  open door/gate (denial sound fires, nothing is hidden).

## Background — confirmed facts

Established by reading the code (self-contained; do not re-derive):

### The one placement path (`world.py`)

`place()` (SPACE) → `_place_block()` is the **only** block-placement path after
spec 0073. Today (`world.py:715`):

```python
def _place_block(self):
    c, r = self.player.col, self.player.row
    if (self._block_credits > 0 and not self.blocked(c, r)
            and not self._is_respawn_tile(c, r)):
        self._block_credits -= 1
        self.cells.set_barrier((c, r), Barrier('placed'))
        self._emit('block_placed')
    else:
        self._emit('action_denied')   # no credit / blocked / respawn tile
```

`set_barrier` **overwrites** whatever barrier already occupies the cell
(`cells.py:274`: `self._barriers[pos] = barrier`), and there is one barrier per
cell.

### Why a door/gate tile can be reached at all

`_place_block` already guards `not self.blocked(c, r)`, so a *closed* door/gate is
safe — it blocks, so placement is refused. The problem is the tiles that are
**passable yet still carry a door/gate fixture**:

- **Open gate** — `Barrier.blocks(channels)` returns `self.channel not in channels`
  (`cells.py:137`); once the gate's channel is latched high the tile is passable,
  but the `'gate'` barrier is still there. `set_barrier` then **destroys** the gate
  (replaces it with `'placed'`); the gate overlay loop (`game.py:595`) no longer
  finds it, so the gate silently disappears and becomes a permanent block.
- **Level entrance gate** — a `'gate'` barrier on `ENTRANCE_CHANNEL`
  (`cells.py:378`). `_open_entrance` (`world.py:736`) latches the channel high
  (does **not** remove the barrier), so once all awards are collected the entrance
  tile is passable. A block placed there is drawn by the base pass, then the
  entrance sprite (`game.py:559`) is blitted **on top** → block hidden.
- **Opened door** — `_try_auto_open_door` (`world.py:574`) **removes** the door
  barrier and records `(room, col, row, colour)` in `self._opened_doors`. The tile
  is now barrier-free (passable), and the open-door sprite is drawn from
  `_opened_doors` (`game.py:651`) **after** the base pass → a block placed there is
  hidden under the open-door sprite.

### Draw order (why the block vanishes)

For one tile the renderer paints, in order: (1) base pass — the `'placed'` block
sprite; (2) later overlays — entrance sprite / open-door sprite drawn on top. The
block is painted first and covered. (Regular open gate is the exception: the gate
barrier is overwritten, so the gate vanishes and the block shows — still wrong,
just the other way round.) All cases are eliminated by refusing the placement.

## D1 — Refuse placement on a door/gate tile

Add a predicate to `world.py` (the pygame-free rules layer — no `cells.py` or
`game.py` change needed) that is true when the player's tile holds a door or gate
fixture in any state, and fold it into the `_place_block` guard:

```python
def _is_door_or_gate_tile(self, c, r):
    """A door or gate lives on (c, r) — open or closed.  Building a 'placed'
    block here would hide the block under the later-drawn fixture, or destroy
    the gate (spec 0077 / BL-57), so placement is refused."""
    b = self.cells.barrier(c, r)
    if b is not None and b.kind in ('door', 'gate'):
        return True                       # closed/open gate incl. the entrance
    # An opened door has its barrier removed but is still drawn from here.
    return any(rk == self._current_room and (dc, dr) == (c, r)
               for rk, dc, dr, _col in self._opened_doors)

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

The `b.kind == 'door'` arm is defensive (a passable door tile has no barrier, so
in practice the `_opened_doors` check catches doors and the `'gate'` arm catches
gates including the entrance). No new event or sound is introduced — the existing
`'action_denied'` → `'denied'` wiring (spec 0074) carries the feedback.

## D2 — Preserve existing behaviour

No change to: the credit gate, the `blocked(c, r)` gate, the respawn-tile gate
(spec 0067), successful placement on a bare floor tile, or any other refusal
site. The only new refusal is "player standing on a door/gate tile".

## D3 — Verification

pygame-free unit tests in `tests/test_world.py`, using the existing
`tests/act2_fixtures.py` fixtures (`gate_level`, `door_level`) and the `_fixture`
/ `_restore` helpers already used by the spec-0074 denial tests:

1. **Open gate refused** — `gate_level`, latch the gate channel high
   (`w._channels.add('g1')`) so `(15, 8)` is passable; give a block credit; stand
   the player on `(15, 8)`; `place()` emits exactly `['action_denied']`, spends no
   credit, and the gate barrier at `(15, 8)` is still `kind == 'gate'`.
2. **Opened door refused** — `door_level`, give the player the red key, bump the
   door at `(15, 8)` to open it (barrier removed, tile passable); give a block
   credit; stand on `(15, 8)`; `place()` emits `['action_denied']`, spends no
   credit, and no `'placed'` barrier appears at `(15, 8)`.
3. **Bare floor still works** — on a plain floor tile with a credit, `place()`
   still emits `['block_placed']` and sets a `'placed'` barrier (guards the
   predicate against false positives).

Full suite stays green; no golden re-record (golden runs take only successful
actions and never place a block on a door/gate).

## Out of scope

- **BL-58** — building a block on a *border passage* tile draws it with the
  border-wall sprite. Separate item, separate design question.
- Any change to how doors/gates are *drawn* (draw order, z-ordering). The fix is
  purely a placement rule; rendering is untouched.
- Allowing a block to *re-seal* an open gate/door (deliberately not a feature).

## Done when:

- [ ] **D1** — `_place_block` refuses on a door/gate tile via
  `_is_door_or_gate_tile`, emitting `'action_denied'` and spending no credit.
- [ ] **D2** — every pre-existing placement/denial behaviour is unchanged.
- [ ] **D3** — the three `test_world.py` cases pass; full suite green; no golden
  re-record.
- [ ] **D4** — Daniel confirms in-game (block can no longer be built on an open
  door/gate; denial sound fires; nothing hidden).
