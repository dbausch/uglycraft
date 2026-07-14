# Spec 0077 — Model an opened door as a channel-latched barrier (delete `_opened_doors`)

Backlog: **BL-57 (P2)**. A tester found that pressing SPACE while standing on a
tile that holds a **door** or **gate** builds a `'placed'` block there anyway —
hidden under the later-drawn fixture, or (for an open gate) destroying the gate.

The naïve fix — a placement predicate that scans both the cell model *and* the
parallel `self._opened_doors` set — is fragile because it reconstructs "is this
door open?" from a positional side-table that only the renderer maintains. The
root cause is a **door/gate asymmetry**: an open **gate** stays a `Barrier` and
derives its passability from a latched **channel**, whereas an opened **door**
*leaves* the cell model (barrier removed) and its open-state is copied into the
global `_opened_doors` set, keyed by `(room, col, row, colour)`.

This spec removes the asymmetry the honest way, following the level entrance —
which is already a `Barrier('gate', channel=ENTRANCE_CHANNEL)` opened by latching
a channel directly (no plate). **A door becomes a gate opened by a key bump:** it
keeps `colour` (for key matching) and gains a unique `channel` (its `door_id`,
minted at graph generation exactly like a gate's `gate_id`). Opening it latches
that channel high; `Barrier.blocks()` for doors and gates becomes the *same line*.
`self._opened_doors` is **deleted**, cross-room render becomes a global channel
query (identical to gated borders), and the BL-57 refusal collapses to one
authoritative lookup. → `kb/world-model-review.md` §5 (*store identity and
structure, derive state by query*); channels are §5 R2 / spec 0050.

## Status checklist

- [x] **D1** — Every LOCKED edge carries a unique `door_id` in its params, minted
  at graph generation by counters parallel to the gate counters (`door_counter`
  for interior via `add_locked_room`, `border_door_counter` for borders via
  `_barrier_kw`). Prefixes `door_` / `border_door_` are disjoint from `gate_` /
  `border_gate_` / `ENTRANCE_CHANNEL`.
- [x] **D2** — `levellayout.py` carries the `door_id` as data: both door-creation
  sites append `(*tile, colour, door_id)`; the border render record becomes
  `('locked', colour, door_id)` (dropping the positional `home`); the three
  `(c, r, colour)` 3-tuple unpack sites are widened to `(c, r, *_)`.
- [x] **D3** — `_parse_doors` sets `Barrier('door', colour=colour, channel=door_id)`
  (falling back to a position-derived channel for single-room hand-authored data);
  `Barrier.blocks()` unifies to `if self.channel is not None: return self.channel
  not in channels`.
- [x] **D4** — `_try_auto_open_door` opens by `self._channels.add(barrier.channel)`
  (the barrier stays); `self._opened_doors` is deleted (world init, the open path,
  the `_WORLD_ATTRS` delegation). No `door_opened(room, pos)` helper is needed —
  the channel set is the global truth.
- [x] **D5** — Rendering reads the channel, not the set: the door overlay loop
  draws `door_open_{o}` iff `self.channel(door.channel)` else `door_{colour}_{o}`;
  the separate `_opened_doors` render loop is deleted; `border_exit_sprite` drops
  its `opened_doors` parameter and renders its `'locked'` arm open iff
  `channel in open_channels` (structurally identical to its `'gated'` arm).
- [x] **D6** — `_place_block` refuses on any door/gate tile via one predicate
  `b = cells.barrier(c, r); b is not None and b.kind in ('door', 'gate')` — the
  open gate, the entrance gate, and the opened door are all present as barriers —
  emitting `'action_denied'` and spending no credit. The open-gate-destruction bug
  is fixed by the same guard (the gate barrier is no longer overwritten).
- [x] **D7** — All other placement/door/gate behaviour is unchanged: credit gate,
  `blocked(c, r)` gate, respawn-tile gate, bare-floor placement, opened-door
  passability, cross-room border-door rendering, door persistence across death
  (spec 0067), and door re-closing on level (re)start.
- [x] **D8** — Verification: pygame-free `tests/test_world.py` asserts the refusal
  at an open-gate tile and an opened-door tile, bare-floor success, and the door
  channel lifecycle (latched on open, persists across death, cleared on level
  start); `tests/test_render.py`'s `border_exit_sprite` cases are ported to the
  channel model; generator determinism + goldens stay green (goldens byte-identical
  — no run places a block on a door/gate; the door-open sprite is pixel-identical).
- [x] **D9** — Daniel confirms in-game (no block on an open door/gate; denial sound
  fires; nothing hidden; gate not destroyed; border doors render open both sides).

## Background — confirmed facts

Established by reading the code (self-contained; do not re-derive):

### The door/gate asymmetry (the root cause)

A **gate** that opens stays in the cell model: `_update_pressure_plates` latches
its channel high; the `'gate'` barrier remains and `Barrier.blocks(channels)`
returns `self.channel not in channels` = `False` (`cells.py:137`). Passability is
*derived* from a fixture that never leaves the model.

A **door** that opens does the opposite (`_try_auto_open_door`, `world.py:574`):

```python
self.inventory.use_key(barrier.colour)
self.cells.remove_barrier((col, row))                     # ← fixture deleted
self._opened_doors.add(                                   # ← copy stashed in a
    (self._current_room, col, row, barrier.colour))       #   global positional set
```

`self._opened_doors` is a global set keyed `(room_key, col, row, colour)`
(`world.py:349` init, reset per level in `start_level`). Everything downstream
then needs the side-table: the open-door render loop (`game.py:651`),
`border_exit_sprite` (`game.py:67`), and the naïve BL-57 placement guard.

### The precedent: the level entrance is already a directly-latched gate

`_parse_entrance` (`cells.py:378`) installs `Barrier('gate',
channel=ENTRANCE_CHANNEL)`; `_open_entrance` (`world.py:736`) opens it by
`self._channels.add(ENTRANCE_CHANNEL)` — a channel with **no plate emitter**,
latched by an event; `entrance_open` is `ENTRANCE_CHANNEL in self._channels`.
Gated **borders** already render cross-room through the channel set:
`border_exit_sprite`'s `'gated'` arm returns `'open' if param in open_channels`
(`game.py:84`) — no room lookup, no positional back-reference. Modelling a door
as a directly-latched gate is this exact, already-shipped pattern.

### Gates already mint unique channel ids at graph generation

In `LevelGraph.generate()` (`levelgraph.py`): interior gates get
`f'gate_{gate_counter[0]}'` (`_add_room`, line 483); border gates get
`f'border_gate_{border_counter[0]}'` (`_barrier_kw`, line 502). These counters are
level-wide (one graph per level, generation is a pure function of the seed), so
the ids are globally unique per level and travel as data in `edge.params`.
Interior gates already work cross-grid on a **global** channel set (spec 0050;
`kb/architecture.md` "Interior-gate plates roam like keys"). Doors currently carry
only `key_colour` — no unique id. This spec gives LOCKED edges a `door_id` minted
the same way.

### The channel set already has the exact door lifecycle

`start_level` (`world.py:347`) sets `self._channels = set()` → all door channels
low → **doors closed on level (re)start** (mirrors the old `_opened_doors =
set()`). `_lose_life` (`world.py:769`) leaves `_channels` untouched → **opened
doors persist across death** (mirrors keeping `_opened_doors`). The plate latch
relatches only *this room's plate gate_ids* (`world.py:544`: `self._channels =
(self._channels - local) | pressed`, `local` built from `plates`), so a latched
door channel — a different prefix, never a plate id — survives every tick, exactly
like the entrance channel. No new lifecycle code is needed.

### Why a door/gate tile is reachable by SPACE at all

`_place_block` already guards `not self.blocked(c, r)`, so a *closed* door/gate is
safe. The problem is passable tiles that still carry (or represent) a fixture:

- **Open gate** — barrier present, channel high, passable. `set_barrier`
  (`cells.py:274`) **overwrites** the gate with `'placed'`; the gate overlay loop
  (`game.py:595`) no longer finds it → the gate silently vanishes.
- **Level entrance gate** — passable once its channel is latched; a placed block is
  drawn by the base pass, then the entrance sprite (`game.py:559`) blits on top →
  block hidden.
- **Opened door** — barrier removed (today), so passable; the open-door sprite is
  drawn from `_opened_doors` (`game.py:651`) after the base pass → block hidden.

After this spec all three are barriers still present in the cell, so one predicate
(D6) covers them, and the open gate is no longer overwritten.

## D1 — Mint a `door_id` at graph generation (mirror the gate counters)

In `LevelGraph.generate()` (`levelgraph.py`), add `door_counter = [0]` beside
`gate_counter`/`border_counter` (line 467):

- **Interior doors** — `_add_room`'s LOCKED branch (line 476) threads a door id
  into `add_locked_room`:

  ```python
  elif et == EdgeType.LOCKED:
      colour = _next_color()
      if colour is None:
          b.add_open_room(size=size)
      else:
          b.add_locked_room(colour, door_id=f'door_{door_counter[0]}', size=size)
          door_counter[0] += 1
  ```

  `add_locked_room(self, colour, door_id=None, size=None, parent=None)` stores it:
  `self._graph.add_edge(..., EdgeType.LOCKED, key_colour=colour, door_id=door_id)`.

- **Border doors** — `_barrier_kw`'s locked branch (line 496) mints a
  `border_door_counter` id parallel to `border_gate`:

  ```python
  if barrier == 'locked':
      colour = _next_color()
      if colour is not None:
          did = f'border_door_{border_door_counter[0]}'
          border_door_counter[0] += 1
          return {'barrier': 'locked', 'key_colour': colour, 'door_id': did}
  ```

Prefixes keep the id namespaces disjoint (`door_`, `border_door_`, `gate_`,
`border_gate_`, `ENTRANCE_CHANNEL`), so no two channels ever collide.

## D2 — Carry the `door_id` as data (`levellayout.py`)

Both door-creation sites already hold the `edge`, so they read `door_id` from its
params and append it to the tuple:

- **Interior** (line 3039): `all_locked_doors.append((*conn, colour,
  edge.params['door_id']))`.
- **Border** (line 3457–3460): `doors.append((*barrier_tile, colour,
  edge.params['door_id']))` and the render record becomes
  `record = ('locked', colour, edge.params['door_id'])` — the positional `home`
  is no longer needed (its only reader was `border_exit_sprite`). Both border
  records (room_a and room_b) already receive the *same* `record` (line 3474), so
  both carry the same channel — cross-room agreement is structural.

Widen the three 3-tuple unpack sites that read `locked_doors` positionally to be
arity-tolerant: `levellayout.py:1668` and `2317` (`for c, r, *_ in …`), and
`tests/test_placement_rules.py:188,229` (`for c, r, *_ in …`). `_parse_plates`
(`cells.py:347`) already uses `*_`.

## D3 — Cells: door barrier carries the channel; `blocks()` unifies

`_parse_doors` (`cells.py:306`) reads the door id (explicit when generated; a
position-derived fallback keeps single-room hand-authored/test data working —
a single-room level's tiles are unique, so it can never collide):

```python
def _parse_doors(cells, room_data):
    for dc, dr, colour, *rest in room_data.get('locked_doors', []):
        channel = rest[0] if rest else f'door_{dc}_{dr}'
        cells.set_barrier((dc, dr), Barrier('door', colour=colour, channel=channel))
```

`Barrier.blocks()` (`cells.py:137`) becomes one branch for every channelled
barrier — gate, entrance, and now door:

```python
def blocks(self, channels=frozenset()):
    # A channelled barrier (gate or door) is open iff its channel is latched
    # high; everything else always blocks (spec 0077 unifies door↔gate).
    if self.channel is not None:
        return self.channel not in channels
    return True
```

Only gates and doors have a non-None channel (walls/placed/border/reinforced pass
`channel=None`), so the branch selects exactly them. `BARRIER_BUMP` is unchanged:
`'door' → 'key'` (a *closed* door opens by key on bump; an *open* door is passable
and never bumped) and `'gate' → None` — `kind` stays distinct for bump dispatch and
sprite selection; only `blocks()` and the open-state store are unified.

## D4 — Runtime: open by latching the channel; delete `_opened_doors`

```python
def _try_auto_open_door(self, col, row):
    barrier = self.cells.barrier(col, row)
    if barrier is None or barrier.kind != 'door':
        return False
    if self.channel(barrier.channel):
        return False                         # already open (defensive; bump can't reach it)
    if not self.inventory.has_key(barrier.colour):
        return False
    self.inventory.use_key(barrier.colour)
    self._channels.add(barrier.channel)      # latch high; the barrier stays
    self._emit('door_opened')
    return True
```

Delete `self._opened_doors = set()` from `start_level` (`world.py:349`) and
`'_opened_doors'` from `_WORLD_ATTRS` (`game.py:1249`). No `door_opened(room,
pos)` query is introduced — open-state is `channel in self._channels`, global by
construction, so cross-room rendering needs no room/position lookup.

## D5 — Rendering reads the channel, not the set

`_render_field`'s two door overlays (`game.py:646–655`) collapse to one loop:

```python
for (dc, dr), door in self.cells.barriers('door'):
    o = self._door_orient(dc, dr)
    dkey = f'door_open_{o}' if self.channel(door.channel) else f'door_{door.colour}_{o}'
    if dkey in sp:
        self.surf.blit(sp[dkey], (dc * TILE, dr * TILE))
# (the separate `for ok, dc, dr, _color in self._opened_doors:` loop is deleted)
```

`border_exit_sprite` (`game.py:67`) drops the `opened_doors` parameter; both barrier
arms now key off `open_channels`:

```python
def border_exit_sprite(record, orient, open_channels):
    if record is None:
        return None
    kind, param, extra = record
    if kind == 'locked':                     # param = colour, extra = door channel
        if extra in open_channels:
            return f'door_open_{orient}'
        return f'door_{param}_{orient}'
    if kind == 'gated':                      # param = gate channel
        state = 'open' if param in open_channels else 'closed'
        return f'gate_{state}_{orient}'
    return None
```

The `_render_field` call site (`game.py:575`) drops `self._opened_doors` from the
argument list. Net pixels are identical: a border door's own room still draws it
via both the `cells.barriers('door')` loop and the border-exit loop, now agreeing
through the one channel set.

## D6 — Single placement predicate

```python
def _is_door_or_gate_tile(self, c, r):
    """A door or gate fixture lives on (c, r) — open or closed.  Building a
    'placed' block here would hide the block under the later-drawn fixture, or
    overwrite (destroy) the gate (spec 0077 / BL-57), so placement is refused.
    Doors are barriers again now (D3), so one lookup covers every case."""
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

## D7 — Preserve existing behaviour

Unchanged: the credit gate, the `blocked(c, r)` gate, the respawn-tile gate
(spec 0067), successful placement on bare floor, opened-door passability
(byte-identical: a latched-channel door reports `not blocked`, exactly as the old
removed barrier did), cross-room border-door rendering, opened-door persistence
across death, and door re-closing on level (re)start (both ride `_channels`). The
only new refusal is "player standing on a door/gate tile"; the only structural
change is that opened doors now live in the cell model + channel set instead of
`_opened_doors`.

## D8 — Verification

pygame-free unit tests in `tests/test_world.py`, using the existing
`tests/act2_fixtures.py` fixtures (`gate_level`, `door_level`) and the `_fixture`
/ `_restore` helpers already used by the spec-0074 denial tests:

1. **Open gate refused** — `gate_level`, latch the gate channel high
   (`w._channels.add('g1')`) so `(15, 8)` is passable; give a block credit; stand
   the player on `(15, 8)`; `place()` emits exactly `['action_denied']`, spends no
   credit, and the gate barrier at `(15, 8)` is still `kind == 'gate'`.
2. **Opened door refused** — `door_level`, give the player the red key, bump the
   door at `(15, 8)` to open it; assert the door barrier is still present, its
   channel is latched (`w.channel(barrier.channel)` is `True`) and the tile is
   passable (`not w.blocked(15, 8)`); give a block credit; stand on `(15, 8)`;
   `place()` emits `['action_denied']`, spends no credit, and the barrier at
   `(15, 8)` is still `kind == 'door'` (no `'placed'`).
3. **Bare floor still works** — on a plain floor tile with a credit, `place()`
   still emits `['block_placed']` and sets a `'placed'` barrier (guards the
   predicate against false positives).
4. **Door channel lifecycle** — after opening, the door channel is in
   `w._channels`; force a death (`w._lose_life()` with `lives > 1`) and assert it is
   still latched (persistence, spec 0067); call `w.start_level(w.level)` and assert
   `w._channels` no longer holds it (re-closed on level start).

`tests/test_render.py`'s `border_exit_sprite` cases (lines 183–233) are ported to
the 3-arg signature and the channel model: a `'locked'` record now reads
`('locked', colour, channel)` and renders open iff `channel in open_channels`
(replacing the `home` / `opened_doors` set-membership cases). Generator
determinism (`test_generation_determinism`) and the golden traces/screenshots stay
green — the rng stream is unchanged (the counters mint deterministically in graph
order), `'door_opened'` still emits, the door-open sprite is pixel-identical, and
no golden run places a block on a door/gate, so **no re-record**.

## Out of scope

- **BL-58** — building a block on a *border passage* tile draws it with the
  border-wall sprite. Separate item, separate design question.
- Any change to how doors/gates are *drawn* (draw order, z-ordering) beyond the
  open/closed source of truth. The fix is a placement rule + the door open-state
  representation.
- Allowing a block to *re-seal* an open gate/door (deliberately not a feature).
- Traced wiring nets / ray-cast beams (`kb/world-model-review.md` §7). Doors join
  the *declared* channel mechanism only.

## Done when:

- [x] **D1** — every LOCKED edge has a unique `door_id` in params, minted by the
  new graph-gen counters; namespaces disjoint from gates/entrance. (`dd250d7`)
- [x] **D2** — `levellayout.py` stores the `door_id` in the door tuple and the
  border `'locked'` record; the 3-tuple unpack sites are widened. (`dd250d7`)
- [x] **D3** — a door barrier carries its channel; `Barrier.blocks()` is one branch
  for every channelled barrier; opened-door passability is byte-identical. (`dd250d7`)
- [x] **D4** — `_try_auto_open_door` latches the channel and keeps the barrier;
  `self._opened_doors` is gone from world init, the open path, and `_WORLD_ATTRS`.
  (`dd250d7`)
- [x] **D5** — the open-door render folds into the `cells.barriers('door')` loop,
  the `_opened_doors` render loop is deleted, and `border_exit_sprite` renders both
  barrier arms from `open_channels`; rendered pixels are unchanged. (`dd250d7`)
- [x] **D6** — `_place_block` refuses on any door/gate tile via the single
  predicate, emitting `'action_denied'` and spending no credit; the open gate is no
  longer destroyed. (`dd250d7`)
- [x] **D7** — every pre-existing placement/door/gate behaviour (D7 list) is
  unchanged. (`dd250d7`)
- [x] **D8** — the four `test_world.py` cases and the ported `test_render.py` cases
  pass; generator determinism + goldens stay green (byte-identical, no re-record).
  (`dd250d7`; the only reds are pre-existing load-sensitive Hypothesis
  `DeadlineExceeded` flakes — run-varying set, all green in isolation — filed BL-59.)
- [x] **D9** — Daniel confirms in-game (no block on an open door/gate; denial sound
  fires; nothing hidden; gate not destroyed; border doors render open both sides).
  (user-confirmed 2026-07-14)
