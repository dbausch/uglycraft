# 0066 — Entrance opens on award completion; level ends by walking out through it (BL-43)

## Status

- [x] Collecting the **last** award no longer ends the level; instead it
      **opens** the entrance door, for every level 1–20 — the entrance is a
      gate barrier on a reserved channel; opening latches that channel high
      and emits a new `entrance_opened` event (`9076676`)
- [x] While open, the entrance border tile becomes **walkable** — exactly
      like a grid-exit gap — through the ordinary `cells.blocked(c, r,
      channels)` gate query, with **no** change to `world.blocked()` (`9076676`)
- [x] Act 1 enemies are **confined to the interior** (their `room_tiles` is
      the full interior tile set) so they can never occupy any border tile,
      the open entrance included; Act 2 enemies are already room-confined
      (`9076676`)
- [x] The level ends only on the **second** press — a bump against the
      screen edge while standing on the open entrance tile — mirroring the
      grid-change flow (`_try_room_transition`): `advance_level()`
      (level-up on 1–19, `game_over(won=True)` on 20) (`9076676`)
- [x] A dedicated **open-entrance sprite** (`draw_level_entrance_open` /
      `level_entrance_open`) renders while `world.entrance_open` is true; a
      distinct chime plays on `entrance_opened` — a distorted choir "ta-daa"
      fanfare (`9076676`, `87950fa`, `1ab2a77`)
- [x] The door stays open after death — `_reset_blocks` preserves the
      entrance channel (`self._channels & {ENTRANCE_CHANNEL}`); it is
      re-closed only when a fresh level starts (`start_level`) (`9076676`)
- [x] New tests red before the change, green after; `poe test` exits 0 with
      any affected goldens deliberately re-recorded (`9dd052d`, `9076676`)
- [x] Manual check: on Act 1 and Act 2 samples, collecting the last award
      opens the door (sprite + sound); the player then walks **onto** the
      door and a further press off the screen edge ends the level (user
      acceptance — 2026-07-12: sprite, item collection, sound, and walk-out
      all confirmed)

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

The open state lives in `self._channels` (empty at `start_level`, so the
entrance starts closed). Replace the two `advance_level()` calls at award
completion
with `self._open_entrance()`. The entrance is modelled as an **openable gate
barrier** driven by a reserved channel — the established openable-barrier
pattern (spec 0050) — so opening is just latching that channel high:

```python
ENTRANCE_CHANNEL = '__entrance__'      # reserved; never a plate/gate id

def _open_entrance(self):
    if ENTRANCE_CHANNEL in self._channels:
        return
    self._channels.add(ENTRANCE_CHANNEL)
    self._emit('entrance_opened')
```

- `world.py:789` (Act 1): `if self.item_no == 9: self._open_entrance()`
- `world.py:406` (Act 2): `if self._loot_collected >= self._loot_total:
  self._open_entrance()`

The channel membership **is** the open state — no separate `_entrance_open`
flag. Expose a read-only `world.entrance_open` property returning
`ENTRANCE_CHANNEL in self._channels` for the renderer.

**The entrance is a gate cell.** In the cell model, place the entrance as
`Barrier('gate', channel=ENTRANCE_CHANNEL)` at `room_data['entrance']` — a
new one-line entry in `CONTENT_PARSERS` (`cells.py:263`), consistent with the
"add a content kind = add one registry entry" philosophy. It overwrites the
`'border'` barrier the border loop laid at that tile. Closed (channel low) it
`blocks()` exactly like the border wall it replaces, and `BARRIER_BUMP['gate']
is None` keeps the bump inert; `is_border` still wins in the renderer so it
draws as `border_wall` under the closed-door sprite. Only the start room of
an Act 2 level carries `entrance`, so only it gets the gate.

Track the current room's entrance tile for the exit trigger: wherever
`_current_room_data` is (re)assigned — `start_level` (Act 1) and `_enter_room`
(Act 2) — refresh

```python
self._entrance_pos = self._current_room_data.get('entrance')   # or None
```

### Phase 2 — the open entrance is a walkable exit gap

A grid exit is walkable because the border loop leaves an **exit gap** (no
barrier) at that tile; the player walks onto it and a subsequent off-screen
press runs `_try_room_transition` (`world.py:566–570`). The open entrance
mirrors this precisely.

**Walkable when open — with no change to `blocked()`.** Passability already
flows through `cells.blocked(c, r, self._channels)` (`world.py:167`,
`cells.py:134`): a gate barrier `blocks()` iff its channel is **not** in
`channels`. Once `ENTRANCE_CHANNEL` is latched high, the entrance gate stops
blocking and the tile is walkable — through the exact same query every gate
and cross-grid door uses. No world-level tile exception, no cached collision
state; `world.blocked` is untouched.

Because the field renderer keys off `self.blocked` (`game.py:507`), the open
tile automatically renders as floor (then the open-door sprite draws on top,
below) — no separate render special-case for walkability.

**Leave on the off-screen bump.** In the move method (`world.py:566–570`),
the off-screen branch currently always calls `_try_room_transition`. Prefer
the level-exit when the player stands on the open entrance:

```python
if not (0 <= tc < COLS and 0 <= tr < ROWS):
    if self.entrance_open and (self.player.col, self.player.row) == self._entrance_pos:
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

### Keeping enemies off the open door — Act 1 confinement

The open tile is passable via `blocked()`, so — exactly as with a grid-exit
gap — nothing in `blocked()` forbids an actor from standing on it. Act 2
enemies are room-confined (BFS/wander/respawn restricted to `room_tiles`,
spec 0051/BL-34) and never leave their room, so they cannot reach the
start-grid entrance. Act 1 enemies have no room today (`room_tiles is None`,
because the Act 1 room dict carries no `tile_owner`, so
`_tag_enemies_with_rooms` early-returns), so an unconfined enemy *could* step
onto the open door.

Fix: **attach every Act 1 enemy to the single interior room.** Define the
interior tile set once —

```python
INTERIOR_TILES = frozenset((c, r) for c in range(1, COLS - 1)
                                   for r in range(1, ROWS - 1))
```

— and in `_tag_enemies_with_rooms` (`world.py:346`), when `self._tile_owner`
is empty (the Act 1 single-room case), assign `enemy.room_tiles =
INTERIOR_TILES` to every enemy instead of returning early. Leave
`enemy.room_name = None`: the chase/wander branch (`world.py:756`) keys
always-chase off `room_name is None`, so Act 1 enemies keep chasing exactly
as today, while `room_tiles` now confines them to the interior in
`wander` / `move_toward` / `move_bfs` (`entities.py:57,74,112`) and in
`_respawn_enemy` (`world.py:684`).

The confinement is invisible while the door is closed: every border tile is
already `blocked()`, so `room_tiles = INTERIOR_TILES` removes no candidate an
enemy could have taken — Act 1 enemy movement (and its goldens) stays
byte-identical. It only bites once the door opens, precisely excluding the
one newly-passable border tile. No enemy can ever occupy the entrance, so the
open door cannot be blocked or camped.

### Future direction — grid zero becomes a real transition

Grid zero (the outside) is planned to become a per-level boss area (or
similar) rather than "the level just ends." When that lands, leaving through
the entrance becomes a **real grid transition** into grid zero, not a
level-up. This spec therefore deliberately routes the exit through the same
off-screen branch as `_try_room_transition`: the future change is swapping
the `advance_level()` call for a transition into grid zero, leaving the
walk-onto-then-bump-off feel untouched. For now, leaving simply ends the
level (`advance_level()`).

### Why a channel, not a `blocked()` flag

An earlier draft modelled the open state as a world `_entrance_open` flag
with a special-case in `world.blocked()` (`return False` at `_entrance_pos`
when open). The channel model is preferred because it keeps **all**
passability inside the one canonical query, `cells.blocked(c, r, channels)`
(spec 0047/0048/0050), instead of adding a tile exception in the hottest
world-level predicate; it reuses the state the engine already carries for
"what is open" (`self._channels`); and game.py already selects open/closed
border-door sprites off `self.world._channels` (`game.py:554`), so the
entrance sprite follows the same path. The two frictions that first steered
me to the flag turned out to be non-issues:

- `_latch_channels` does **not** recompute `self._channels` wholesale. It is
  a *targeted* relatch — `self._channels = (self._channels - local) | pressed`
  (`world.py:447`), where `local` is only this room's plate gate-ids. A
  channel no plate emits (like `ENTRANCE_CHANNEL`) is never subtracted and
  survives every pass untouched — the mechanism is built for exactly this
  (the comment cites cross-grid gates held high from another room).
- "A singleton, not a network" is no obstacle: a 1-emitter → 1-gate channel
  is a valid degenerate case of the same abstraction.

### Death / reset semantics

The door **stays open** after death. It opens only once the last award is
collected and removed, so award state cannot regress. The only place that
wipes channels wholesale is `_reset_blocks` (`world.py:662`,
`self._channels = set()`, called from `_lose_life`), which would wrongly
close the entrance on death. Change it to preserve the entrance channel while
still closing plate-held gates:

```python
# was: self._channels = set()
self._channels = self._channels & {ENTRANCE_CHANNEL}
```

`start_level` still sets `_channels = set()` (`world.py:270`), so a fresh
level always starts with the entrance closed. After a death the player
respawns at `player_start` (directly inside the open door) and can walk
straight out. Confirm `_entrance_pos` is still the start-grid entrance after
an Act 2 death (respawn returns to the start grid — see Verification).

**This `_reset_blocks` accommodation is temporary.** It exists only because
today death wipes all channels wholesale to reset plate-held gates. When
BL-37 (exploding push-blocks → a self-healing level) lands, the
reset-blocks-on-death path goes away entirely — the spec supersedes
`_reset_blocks` — and with it the wholesale channel wipe. At that point
nothing closes channels on death, so the entrance channel persists on its
own: this `self._channels & {ENTRANCE_CHANNEL}` line is **deleted together
with `_reset_blocks`**, not migrated. Until BL-37, the one-line preservation
keeps the door open across death.

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

- **Entrance is a gate cell:** at level load the entrance tile holds a
  `Barrier('gate', channel=ENTRANCE_CHANNEL)`; `ENTRANCE_CHANNEL` is not in
  `world._channels` and `world.entrance_open` is False.
- **Act 1 opens, does not advance:** drive a level to collect all 9 awards;
  assert an `entrance_opened` event fired, `ENTRANCE_CHANNEL in world._channels`
  (i.e. `world.entrance_open` is True), and `world.level` is **unchanged**.
- **Open door is walkable via the gate query:** with the entrance open,
  assert `world.blocked(*entrance_pos)` is False and
  `world.cells.blocked(*entrance_pos, world._channels)` is False; from the
  interior neighbour, one press toward the entrance moves the player **onto**
  the entrance tile.
- **Second press (off-screen) advances:** standing on the open entrance,
  press outward (off-screen); assert `level_advanced` (or
  `game_over(won=True)` for the last level) and the level advanced.
- **Closed entrance is inert & solid:** before all awards are collected,
  `world.blocked(*entrance_pos)` is True and pressing into it bumps without
  moving or advancing.
- **One press is not enough:** immediately after opening, a single outward
  press from the interior neighbour steps onto the door but does **not**
  advance; only the next press does.
- **Door persists across death:** open the entrance, then trigger a
  `_lose_life` that does not end the game (which runs `_reset_blocks`); assert
  `ENTRANCE_CHANNEL` survives in `world._channels`, `world.entrance_open`
  stays True, and the tile stays walkable — while any plate-held gate channel
  is correctly cleared.
- **Act 2 opens then exits:** collect all preplaced loot (open), walk onto
  the start-room entrance, press off-screen → advance. Confirm an off-screen
  press from a non-start-room border still only runs `_try_room_transition`
  (no `_entrance_pos` there).
- **Act 1 enemies are interior-confined:** after `start_level`, every Act 1
  enemy has `room_tiles == INTERIOR_TILES` and `room_name is None`; drive
  many ticks with the entrance open and assert no enemy ever occupies any
  border tile (the open entrance included).

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

- [x] The entrance loads as a `Barrier('gate', channel=ENTRANCE_CHANNEL)`;
      last-award collection latches that channel high, emits `entrance_opened`,
      and does **not** advance the level (both Act 1 and Act 2 paths) (`9076676`)
- [x] While open, the entrance tile is walkable through the ordinary
      `cells.blocked(c, r, channels)` gate query (`world.blocked` unchanged)
      and the player can step onto it; while closed it is solid and inert
      (`9076676`)
- [x] Standing on the open entrance, an off-screen press calls
      `advance_level()` (level-up 1–19, win on 20); one press alone (just
      stepping on) does not advance (`9076676`)
- [x] Act 1 enemies carry `room_tiles == INTERIOR_TILES` (`room_name` still
      None) and never occupy any border tile, the open entrance included;
      Act 1 enemy goldens stayed byte-identical (`9076676`)
- [x] `ENTRANCE_CHANNEL` survives death (`_reset_blocks` preserves it) and is
      cleared only by `start_level`; plate gates still close on death (`9076676`)
- [x] `game.py` shows the open-door sprite while `entrance_open` and plays a
      distinct chime on `entrance_opened` — the entrance gate is excluded from
      the generic gate overlay so a door, not a portcullis, renders (`9076676`)
- [x] New tests red first, then green; `poe test` exits 0. Act 1 goldens
      stayed byte-identical; the two Act 2 goldens that reached the last loot
      (`act2_door`, `act2_water`) were deliberately re-recorded — they now open
      the entrance instead of advancing (`9dd052d`, `9076676`)
- [x] User confirms, on Act 1 and Act 2 samples, that the door opens on the
      last award and the level ends by walking onto it then bumping the screen
      edge (explicit message; manual acceptance — 2026-07-12)
