# 0066 — Entrance opens on award completion; level ends by walking out through it (BL-43)

## Status

- [ ] Collecting the **last** award no longer ends the level; instead it
      **opens** the entrance door (a new `entrance_opened` event + a world
      `entrance_open` state flag), for every level 1–20
- [ ] While open, the entrance border tile becomes **walkable** — exactly
      like a grid-exit gap: the player can step onto it (`blocked()` returns
      False there), enemies stay confined out as they already are at exits
- [ ] The level ends only on the **second** press — a bump against the
      screen edge while standing on the open entrance tile — mirroring the
      grid-change flow (`_try_room_transition`): `advance_level()`
      (level-up on 1–19, `game_over(won=True)` on 20)
- [ ] A dedicated **open-entrance sprite** (`draw_level_entrance_open` /
      `level_entrance_open`) renders while `world.entrance_open` is true; a
      distinct chime plays on `entrance_opened`
- [ ] The door stays open after death (award state already persists); it is
      re-closed only when a fresh level starts (`start_level`)
- [ ] New tests red before the change, green after; `poe test` exits 0 with
      any affected goldens deliberately re-recorded
- [ ] Manual check: on Act 1 and Act 2 samples, collecting the last award
      opens the door (sprite + sound); the player then walks **onto** the
      door and a further press off the screen edge ends the level (user
      acceptance)

## Problem

Today a level ends the **instant** the last award item is collected:

- **Act 1** (`spawn_mode == 'sequential'`), `world.py:789` —
  `if self.item_no == 9: self.advance_level()`.
- **Act 2** (`spawn_mode == 'preplaced'`), `world.py:406` —
  `if self._loot_collected >= self._loot_total: self.advance_level()`.

Since spec 0064 (BL-42) every level 1–20 has an **entrance door**: a solid
`'border'` barrier at a fixed per-level position, with the player start on
the interior floor tile directly inside it (Manhattan-adjacent). BL-43 turns
that door into the level exit, and it must behave **exactly like a grid
change**: walk onto the opened tile, then a further press against the screen
edge (an off-screen bump) leaves.

This realises the spec 0053 "Future extension": the opened entrance gives way
to grid zero (the outside). BL-43 only ends the level — the actual walk into
grid zero remains future work.

## Design

Two-phase completion replaces the one-phase instant advance, reusing the
existing grid-transition mechanic so leaving the level feels identical to
leaving a grid.

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

Expose a read-only `world.entrance_open` property for the renderer.

Track the current room's entrance tile: wherever `_current_room_data` is
(re)assigned — `start_level` (Act 1) and `_enter_room` (Act 2) — refresh

```python
self._entrance_pos = self._current_room_data.get('entrance')   # or None
```

### Phase 2 — the open entrance is a walkable exit gap

A grid exit is walkable because the border loop leaves an **exit gap** (no
barrier) at that tile; the player walks onto it and a subsequent off-screen
press runs `_try_room_transition` (`world.py:566–570`). The open entrance
mirrors this precisely.

**Walkable when open.** Make the entrance tile query as passable while open,
by one live check in `blocked()` (`world.py:161`, alongside the existing
out-of-bounds and block checks — a query, never cached collision state):

```python
def blocked(self, c, r):
    if not (0 <= c < COLS and 0 <= r < ROWS):
        return True
    if self._entrance_open and (c, r) == self._entrance_pos:
        return False                      # open door = walkable exit gap
    if self.cells.blocked(c, r, self._channels):
        return True
    if self.room.block_at(c, r) is not None:
        return True
    return False
```

Because the field renderer keys off `self.blocked` (`game.py:507`), the open
tile automatically renders as floor (then the open-door sprite draws on top,
below) — no separate render special-case for walkability.

**Leave on the off-screen bump.** In the move method (`world.py:566–570`),
the off-screen branch currently always calls `_try_room_transition`. Prefer
the level-exit when the player stands on the open entrance:

```python
if not (0 <= tc < COLS and 0 <= tr < ROWS):
    if self._entrance_open and (self.player.col, self.player.row) == self._entrance_pos:
        self.advance_level()      # level-up 1–19, game_over(won=True) on 20
        return False
    self._try_room_transition()
    return False
```

`advance_level()` already handles the last-level win and emits
`level_advanced` (mapped to the level-up fanfare in `game.py:192`); the
fanfare now fires on the walk-out instead of on last-pickup. No new
completion event is needed.

Every entrance tile is an in-bounds border tile (col 0/29 or row 0/15 — spec
0064 table). From the interior neighbour the first press *steps onto* it (now
passable); standing on it, the only off-screen press is the outward one (the
other three neighbours are border walls or the interior), so the exit
direction is fixed by geometry. In Act 2 only the start room carries an
`entrance` key, so `_entrance_pos` is `None` in every other room — the level
can only be left from the start grid, the "leave the way you came in"
semantics.

### Geometry — step onto, then bump off (mirrors grid change)

Level 1: entrance `(29, 7)`, start `(28, 7)` (spec 0064). Legend: `#` border
wall · `.` floor · `P` player · `E` closed entrance · `D` open door · `×`
off-screen.

**Closed — awards outstanding; press right just bumps:**

```
        col:  26  27  28  29 | 30
row 6          .   .   .   #  |
row 7          .   .   P   E  |        press right → bump (E is a wall)
row 8          .   .   .   #  |
```

**Open, press 1 — step onto the door (a normal move):**

```
        col:  26  27  28  29 | 30
row 7          .   .   P → D  |        press right → step onto open door D
```

**Open, press 2 — bump the screen edge → level ends:**

```
        col:  26  27  28  29 | 30
row 7          .   .   .   P  |  ×     press right → off-screen → advance_level()
```

Identical shape for centre-top `(14,0)`/`(14,1)` (press up twice),
centre-bottom `(14,15)`/`(14,14)` (press down twice), centre-left
`(0,7)`/`(1,7)` (press left twice) — the sole interior neighbour is always
the player start's side, and the second press is always the off-screen one.

### Enemies at the open door

The open tile is passable via `blocked()`, so — exactly as with a grid-exit
gap — nothing in the model forbids an actor from standing on it. Act 2
enemies are room-confined (BFS/wander over `room_tiles`, spec 0051/BL-34) and
never leave their room, so they cannot reach the start-grid entrance anyway.
Act 1 has no confinement, so an enemy *may* occasionally wander onto the open
door; this matches grid-exit semantics (the gap tile is passable for all) and
cannot soft-lock the level — an enemy on the door cannot trigger completion
(only the player-move path does), enemies chase rather than camp, and after a
death the player respawns inside with the door still open. We accept this
parity; restricting the open door to the player alone is a possible follow-up
only if play-testing shows it matters.

### Rejected alternative — model the entrance as a gate channel

The entrance could be a `Barrier('gate', channel=…)` opened by adding its
channel to `self._channels` (the established openable-barrier pattern). Two
frictions make the dedicated flag cleaner: `_latch_channels` recomputes
`self._channels` wholesale from plate occupancy every tick
(`world.py:425`), so a persistent entrance channel would have to be re-ORed
in each pass; and the entrance is a per-level singleton tied to award
completion, not a plate/lever signal network. A single `_entrance_open` flag
queried live by `blocked()` is smaller and reads clearer, without caching
collision state.

### Death / reset semantics

The door **stays open** after death. It opens only once the last award is
collected and removed, so award state cannot regress. `_entrance_open` is
therefore **not** touched by `_lose_life` / `_reset_blocks` — only
`start_level` clears it (to False) for the next level. After a death the
player respawns at `player_start` (directly inside the open door) and can walk
straight out. Confirm `_entrance_pos` is still the start-grid entrance after
an Act 2 death (respawn returns to the start grid — see Verification).

## Rendering (`game.py`)

- New sprite `draw_level_entrance_open` (open archway / door swung inward,
  showing the outside through it) registered as `'level_entrance_open'` in
  the sprite table (`sprites.py`).
- At the entrance blit (`game.py:537–540`), pick the sprite by state:

  ```python
  if 'entrance' in self._current_room_data:
      ec, er = self._current_room_data['entrance']
      key = 'level_entrance_open' if self.world.entrance_open else 'level_entrance'
      self.surf.blit(sp[key], (ec * TILE, er * TILE))
  ```

  When open the underlying tile renders as floor (blocked False), so the open
  sprite is drawn over floor; the player sprite, drawn after the field,
  appears standing in the doorway.
- Map the new `entrance_opened` event to a distinct chime in the event→sound
  table (`game.py` ~:192): a short "unlock" cue (reused or new SFX in
  `sounds.py`), audibly different from the level-up fanfare so the two phases
  are distinguishable.

## Tests

World-level (pygame-free), in the existing suite:

- **Act 1 opens, does not advance:** drive a level to collect all 9 awards;
  assert an `entrance_opened` event fired, `world.entrance_open` is True,
  `world.level` is **unchanged**.
- **Open door is walkable:** with the entrance open, assert
  `world.blocked(*entrance_pos)` is False; from the interior neighbour, one
  press toward the entrance moves the player **onto** the entrance tile.
- **Second press (off-screen) advances:** standing on the open entrance,
  press outward (off-screen); assert `level_advanced` (or
  `game_over(won=True)` for the last level) and the level advanced.
- **Closed entrance is inert & solid:** before all awards are collected,
  `world.blocked(*entrance_pos)` is True and pressing into it bumps without
  moving or advancing.
- **One press is not enough:** immediately after opening, a single outward
  press from the interior neighbour steps onto the door but does **not**
  advance; only the next press does.
- **Door persists across death:** open the entrance, trigger a `_lose_life`
  that does not end the game; assert `world.entrance_open` stays True and the
  tile stays walkable.
- **Act 2 opens then exits:** collect all preplaced loot (open), walk onto
  the start-room entrance, press off-screen → advance. Confirm an off-screen
  press from a non-start-room border still only runs `_try_room_transition`
  (no `_entrance_pos` there).

Goldens: the Act 1 sequential-completion trace and any screenshot golden that
renders a completed field (fanfare now on walk-out, open-door sprite, and the
open tile now walkable). Re-record deliberately with `UGLYCRAFT_REGOLD=1` and
eyeball the diffs. Act 2 generation/runtime is otherwise unchanged.

## Manual verification

- `poe run --level 1`: collect all 9 awards → door sprite opens + chime, HUD
  unchanged, level does **not** advance; press right to step onto the door,
  press right again → off-screen → level-up.
- `poe run --level 5` (centre-bottom entrance): open, press **down** onto
  `(14,15)`, press **down** again → advance.
- `poe run --level 10` (boss, entrance `(0,7)`): open, press **left** onto
  `(0,7)`, press **left** again → **YOU WON!** (last level → win).
- An Act 2 level (11–20): collect all loot in a far room, navigate back to the
  start grid, step onto the entrance, press off-screen → advance. Confirm the
  door shows open once loot is complete even while standing in another grid.
- Die after opening the door: respawn inside, door still open and walkable,
  walk out.

## Done when:

- [ ] Last-award collection emits `entrance_opened`, sets `entrance_open`,
      and does **not** advance the level (both Act 1 and Act 2 paths)
- [ ] While open, the entrance tile is walkable (`blocked()` False there) and
      the player can step onto it; while closed it is solid and inert
- [ ] Standing on the open entrance, an off-screen press calls
      `advance_level()` (level-up 1–19, win on 20); one press alone (just
      stepping on) does not advance
- [ ] Enemies never leave via the entrance; no soft-lock from an enemy on the
      open door
- [ ] `entrance_open` survives death and is reset only by `start_level`
- [ ] `game.py` shows the open-door sprite while `entrance_open` and plays a
      distinct chime on `entrance_opened`
- [ ] New tests red first, then green; `poe test` exits 0 with affected Act 1
      goldens deliberately re-recorded and Act 2 traces byte-identical
- [ ] User confirms, on Act 1 and Act 2 samples, that the door opens on the
      last award and the level ends by walking onto it then bumping the screen
      edge (explicit message; manual acceptance)
