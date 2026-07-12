# 0066 — Entrance opens on award completion; level ends by leaving through it (BL-43)

## Status

- [ ] Collecting the **last** award no longer ends the level; instead it
      **opens** the entrance door (a new `entrance_opened` event + a world
      `entrance_open` state flag), for every level 1–20
- [ ] The level ends only when the player **presses into the open entrance
      tile** from the adjacent inside tile (`advance_level()` — i.e. the
      existing level-up on levels 1–19, `game_over(won=True)` on level 20)
- [ ] The entrance stays a solid border barrier throughout: enemies never
      enter it and the player never stands on it — the exit is an
      intercepted bump, not a walkable tile (no change to `blocked()`)
- [ ] The door stays open after death (award state already persists); it is
      re-closed only when a fresh level starts
- [ ] `game.py` renders an **open**-door sprite while `world.entrance_open`
      is true (new `draw_level_entrance_open` / `level_entrance_open`
      sprite) and plays a distinct chime on `entrance_opened`
- [ ] `--dump-level` marks the entrance open/closed correctly is **not** in
      scope (dump renders handover state, entrance always closed at load)
- [ ] New tests red before the change, green after; `poe test` exits 0 with
      any affected goldens deliberately re-recorded
- [ ] Manual check: on a sample of Act 1 and Act 2 levels, collecting the
      last award opens the door (sprite + sound) and the level ends only
      when walking out through it (user acceptance)

## Problem

Today a level ends the **instant** the last award item is collected:

- **Act 1** (`spawn_mode == 'sequential'`), `world.py:789` —
  `if self.item_no == 9: self.advance_level()`.
- **Act 2** (`spawn_mode == 'preplaced'`), `world.py:406` —
  `if self._loot_collected >= self._loot_total: self.advance_level()`.

Since spec 0064 (BL-42) every level 1–20 has an **entrance door**: a solid
`'border'` barrier at a fixed per-level position, with the player start on
the interior floor tile directly inside it (Manhattan-adjacent). BL-43 turns
that door into the level exit:

> Collecting all awards shall **open** the entrance; the level ends only when
> the player **leaves through** it.

This realises the spec 0053 "Future extension": the opened entrance gives way
to grid zero (the outside). BL-43 only ends the level — the actual walk into
grid zero remains future work.

## Design

Two-phase completion replaces the one-phase instant advance.

### Phase 1 — award completion opens the door

Add a world flag `self._entrance_open` (bool), initialised **False** in
`start_level`. Replace the two `advance_level()` calls at award completion
with `self._open_entrance()`:

```python
def _open_entrance(self):
    if self._entrance_open:
        return
    self._entrance_open = True
    self._emit('entrance_opened')
```

- `world.py:789` (Act 1): `if self.item_no == 9: self._open_entrance()`
- `world.py:406` (Act 2): `if self._loot_collected >= self._loot_total:
  self._open_entrance()`

Expose a read-only view for the renderer: `world.entrance_open` property
(returns `self._entrance_open`).

### Phase 2 — leaving through the open entrance ends the level

The entrance is on the border and **stays a solid barrier**. The player can
only ever *press into* it from the single interior neighbour (the start
tile's side). We intercept that bump.

Track the current room's entrance tile: wherever `_current_room_data` is
(re)assigned — `start_level` for Act 1, `_enter_room` for Act 2 — refresh

```python
self._entrance_pos = self._current_room_data.get('entrance')   # or None
```

In the move method (`world.py:555–578`), the target tile of a failed step is
computed as `(tc, tr)` and, when in bounds and blocked, would push or bump.
**Before** `_try_push_block`, intercept the open entrance:

```python
if self.blocked(tc, tr):
    if self._entrance_open and (tc, tr) == self._entrance_pos:
        self.advance_level()        # level-up, or game_over(won=True) on L20
        return True
    if self._try_push_block(tc, tr, dcol, drow):
        ...
    self._register_bump(key, tc, tr)
```

`advance_level()` already handles the last-level case (`_end_game(won=True)`)
and emits `level_advanced` (mapped to the level-up fanfare in `game.py:192`).
No new completion event is required; the fanfare simply fires on **exit**
now instead of on last-pickup.

Every entrance tile is an in-bounds border tile (col 0/29 or row 0/15 — see
spec 0064 table), so the press always reaches the `self.blocked(tc, tr)`
branch and never the out-of-bounds `_try_room_transition` branch. In Act 2,
only the start room carries an `entrance` key, so `_entrance_pos` is `None`
in every other room and the exit can only be taken from the start grid —
exactly the "leave the way you came in" semantics.

### Geometry (press-into, not step-onto)

Level 1: entrance `(29, 7)`, start `(28, 7)` (spec 0064). Legend: `#` border
wall · `.` floor · `P` player · `E` closed entrance · `D` open entrance door.

**Closed — awards still outstanding (bump does nothing but sound):**

```
        col:  26  27  28  29
row 6          .   .   .   #
row 7          .   .   P   E     press → bump, E stays a wall
row 8          .   .   .   #
```

**Open — last award collected; press right from (28,7) → level ends:**

```
        col:  26  27  28  29
row 6          .   .   .   #
row 7          .   .   P → D     press right into D = advance_level()
row 8          .   .   .   #
```

The door tile is never occupied by the player or an enemy; the player exits
*through* it (the move that would step onto it is consumed as the exit). The
same shape holds for centre-top `(14,0)`/`(14,1)`, centre-bottom
`(14,15)`/`(14,14)`, and centre-left `(0,7)`/`(1,7)` — the sole interior
neighbour is always the player start's side.

### Death / reset semantics

The door **stays open** after death. Rationale: the door opens only once the
last award is already collected and removed, so award state cannot regress.
`_entrance_open` is therefore **not** touched by `_lose_life` / `_reset_blocks`
— only `start_level` clears it (to False) for the next level. After a death
the player respawns at `player_start` (the tile directly inside the open
door) and can immediately walk out.

`_entrance_pos` follows `_current_room_data`; confirm it is correct after an
Act 2 death (respawn returns to the start grid — see Verification).

## Rendering (`game.py`)

- New sprite `draw_level_entrance_open` (door ajar / open archway) registered
  as `'level_entrance_open'` in the sprite table (`sprites.py`).
- At the entrance blit (`game.py:537–540`), choose the sprite by state:

  ```python
  if 'entrance' in self._current_room_data:
      ec, er = self._current_room_data['entrance']
      key = 'level_entrance_open' if self.world.entrance_open else 'level_entrance'
      self.surf.blit(sp[key], (ec * TILE, er * TILE))
  ```

- Map the new `entrance_opened` event to a distinct chime in the event→sound
  table (`game.py` ~:192): a short "unlock" cue, reused or new SFX
  (`sounds.py`). It must be audibly different from the level-up fanfare so
  the two phases are distinguishable.

## Tests

World-level (pygame-free), in the existing suite:

- **Act 1 opens, does not advance:** drive a level to collect all 9 awards;
  assert an `entrance_opened` event fired, `world.entrance_open` is True,
  `world.level` is **unchanged**, and the player is still in the level.
- **Act 1 exits on press:** from the above state, position the player on the
  interior neighbour and press toward the entrance; assert `level_advanced`
  (or `game_over(won=True)` for level 10 wired as last) and the level
  advanced.
- **Closed entrance is inert:** before all awards are collected, pressing
  into the entrance registers a bump and does **not** advance.
- **Door persists across death:** open the entrance, then trigger a
  `_lose_life` that does not end the game; assert `world.entrance_open`
  stays True.
- **Act 2 opens then exits:** collect all preplaced loot (open), then press
  into the start-room entrance; assert advance. Confirm pressing into a
  non-start-room border does nothing (there is no `_entrance_pos` there).
- **Enemies never enter the open door:** with the entrance open, assert no
  enemy occupies `_entrance_pos` after an update (it stays blocked for them).

Goldens: the Act 1 sequential-completion trace and any screenshot golden
that renders a completed field change (fanfare now on exit, open-door
sprite). Re-record deliberately with `UGLYCRAFT_REGOLD=1` and eyeball the
diffs. Act 2 generation/runtime is otherwise unchanged.

## Manual verification

- `poe run --level 1`: collect all 9 awards → door sprite opens + chime, HUD
  unchanged, level does **not** advance; walk right into the door → level-up.
- `poe run --level 5` (centre-bottom entrance): same, pressing **down** into
  `(14,15)` from `(14,14)`.
- `poe run --level 10` (boss, entrance `(0,7)`): defeat/collect to open, then
  press **left** into `(0,7)` → **YOU WON!** (last level → `game_over(won=True)`).
- An Act 2 level (11–20): collect all loot in a far room, navigate back to the
  start grid, press into the entrance → advance. Confirm the door shows open
  once loot is complete even while standing in another grid on return.
- Die after opening the door (walk into an enemy): respawn inside, door still
  open, walk out.

## Done when:

- [ ] Last-award collection emits `entrance_opened`, sets `entrance_open`,
      and does **not** advance the level (both Act 1 and Act 2 paths)
- [ ] Pressing into the open entrance tile from its interior neighbour calls
      `advance_level()` (level-up on 1–19, win on 20); pressing while closed
      only bumps
- [ ] Entrance stays a border barrier for all actors; `blocked()` unchanged;
      no enemy ever occupies the entrance tile
- [ ] `entrance_open` survives death and is reset only by `start_level`
- [ ] `game.py` shows the open-door sprite while `entrance_open` and plays a
      distinct chime on `entrance_opened`
- [ ] New tests red first, then green; `poe test` exits 0 with affected Act 1
      goldens deliberately re-recorded and Act 2 traces byte-identical
- [ ] User confirms, on Act 1 and Act 2 samples, that the door opens on the
      last award and the level ends only by leaving through it (explicit
      message; manual acceptance)
