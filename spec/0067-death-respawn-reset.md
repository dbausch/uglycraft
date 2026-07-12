# 0067 — Death respawn: reset player and all enemies to starts; no crafting on the respawn tile (BL-50, BL-51)

## Status

- [ ] On any life loss, **every enemy** (in every visited room) returns to
      its original start tile — not just the player (BL-50)
- [ ] The caught enemy is reset to its start with the rest (its pre-death
      `_respawn_enemy` relocation applies only on a **shielded** hit, where no
      life is lost)
- [ ] `Room` captures `enemies_initial` at construction (parallel to
      `blocks_initial`); `World._reset_enemies()` restores from it, and
      `_lose_life` calls it alongside `_reset_blocks`
- [ ] Placing a crafted wall/block on the **respawn tile** (the start room's
      `player_start`) is rejected — Act 1 (`_place_wall`) and Act 2
      (`_act2_place`) both guarded (BL-51)
- [ ] **Decision (Act 2 respawn room):** whether `_lose_life` also returns the
      player to the **start room** (today it sets start-room coordinates but
      leaves `World.room` on the room the player died in) — see Decisions
- [ ] New tests red before the change, green after; `poe test` exits 0 with
      any affected goldens deliberately re-recorded
- [ ] Manual check: die mid-level → player and all enemies snap back to their
      starts; a crafted wall cannot be placed on the start tile (user
      acceptance)

## Problem

On death today (`World._lose_life`, world.py:681) only the **player** returns
to `player_start`; blocks reset via `_reset_blocks`. Enemies stay wherever
they wandered. Worse, `_on_caught` (world.py:670) relocates *the catching
enemy* to a random far tile via `_respawn_enemy` **before** losing the life —
so after a death the enemies are scattered, not reset. BL-50 wants a clean
slate: player **and all enemies** back to their level start positions.

Separately (BL-51), a player-crafted wall/block can be placed on the player's
own tile — including the `player_start` tile. A wall there would leave the
player standing on / trapped by a barrier on the next respawn. Placement on
the respawn tile must be forbidden.

The two are one topic: both concern the death→respawn state, and BL-51 keeps
the respawn tile that BL-50 sends the player back to walkable.

## Design

### BL-50 — reset all enemies on death

`_lose_life` is the single choke point for every life loss (enemy catch,
flame jet, …), so the reset lives there and covers all death causes.

**Capture initial positions** (parallel to `blocks_initial`). In
`Room.__init__` (rooms.py:15), add to `__slots__` and record:

```python
self.enemies_initial = tuple((e.col, e.row) for e in enemies)
```

The `enemies` list is stable across a level (same objects, same order — spec
0051 rooms persist by identity), so a positional `zip` restores each enemy.

**Reset method** on `World`, mirroring `_reset_blocks` (visited rooms only —
an unvisited room's enemies never moved):

```python
def _reset_enemies(self):
    for room in self._rooms.values():
        for enemy, (c, r) in zip(room.enemies, room.enemies_initial):
            enemy.col, enemy.row = c, r
            enemy.reset_patrol()      # PatrolEnemy: back to its first leg; no-op otherwise
```

`PatrolEnemy` also carries a waypoint target/index; resetting position without
it would leave the patrol heading to a stale waypoint. Give `Enemy` a base
`reset_patrol()` no-op and `PatrolEnemy` an override that restores its initial
target, OR reset the index inline — decided in implementation, but the patrol
must resume from its start leg.

**Call it from `_lose_life`** (non-fatal branch):

```python
self.player.col, self.player.row = data['player_start']
self._reset_blocks()
self._reset_enemies()
```

**Drop the pre-death relocation.** `_on_caught` currently calls
`_respawn_enemy(enemy)` unconditionally. Move it into the shielded branch only
(where the player survives and the catcher must be shoved off the player);
on a real hit, `_reset_enemies` supersedes it:

```python
def _on_caught(self, enemy):
    if self.shield:
        self._respawn_enemy(enemy)     # survive: shove the catcher away
        self.shield = False
        self._shield_timer = 0
        self._emit('caught_shielded')
    else:
        self._emit('caught')
        self._lose_life()              # full reset handles every enemy
```

This also stops the life-loss path from drawing `_respawn_enemy`'s BFS/RNG
(which shifts the RNG stream) — goldens that catch-and-lose will re-record.

### BL-51 — no crafting on the respawn tile

The respawn tile is the start room's `player_start`. A small predicate:

```python
def _is_respawn_tile(self, c, r):
    return (self._current_room == self._level_data['start_room']
            and (c, r) == tuple(self._level_data['player_start']))
```

(Act 1 is the single room keyed `None` = `start_room`, so this matches there
too.) Guard both placement paths — reject silently, exactly as an
already-blocked tile does today (no barrier set, no credit/item consumed):

- `_place_wall` (Act 1): add `and not self._is_respawn_tile(c, r)` to the
  place condition.
- `_act2_place` (Act 2, `CRAFT_STONE_WALL` branch): same guard before
  `set_barrier`.

## Decisions

1. **Act 2 respawn room.** Today `_lose_life` sets `player.col/row` to the
   start room's `player_start` but does **not** switch `World.room` — so a
   death in a non-start grid leaves the player at start-grid *coordinates*
   inside the *wrong* room (a latent incoherence, independent of BL-50).
   *Recommendation:* on death, also `_enter_room(self._level_data['start_room'])`
   so the player genuinely respawns in the start room. This is a gameplay
   change (Act 2 death sends you back to grid 0) and re-records Act 2 death
   goldens — **confirm the direction before implementing.** If out of scope,
   BL-50 still resets enemy positions; only the player-room incoherence
   remains.
2. **Enemy-start tiles vs BL-51.** BL-51's letter is the *player* respawn
   tile. But with BL-50 an enemy also respawns onto its start tile, so a wall
   crafted there would collide with the returning enemy. *Default:* keep the
   guard to the player respawn tile only (per the backlog); widening it to
   enemy-start tiles is a possible follow-up, noted here so it isn't lost.

## Tests (world-level, pygame-free)

- **All enemies reset on death:** move every enemy off its start (set
  positions or drive updates), then a non-fatal `_lose_life`; assert each
  enemy is back at its `enemies_initial` position and the player at
  `player_start`.
- **Caught enemy resets, not relocated:** force a non-shielded catch; assert
  the catcher is at its start tile (not a random far tile) and a life was
  lost.
- **Shielded catch still relocates, no reset:** with a shield, a catch emits
  `caught_shielded`, loses no life, and relocates the catcher (enemies not
  reset to starts).
- **Multi-room reset:** an Act 2 fixture with enemies in two visited rooms;
  move both, die, assert both rooms' enemies reset (visited-rooms-only, like
  `_reset_blocks`).
- **No wall on the respawn tile (Act 1):** standing on `player_start` with a
  place credit, `place()` is rejected — no `placed` barrier, credit intact.
- **No wall on the respawn tile (Act 2):** `CRAFT_STONE_WALL` active on the
  start-room `player_start` is rejected — item not consumed; a control tile
  one step away still places.
- (If Decision 1 is accepted) **Act 2 death returns to start room:** die in a
  non-start room; assert `_current_room == start_room` and the player at
  `player_start`.

## Manual verification

- `poe run --level 1`: wander the enemies toward you, get caught → after the
  flash, every enemy is back at its start corner and you are at the entrance
  start; repeat to confirm it is consistent.
- Stand on the start tile and press SPACE (with a wall credit / crafted wall)
  → nothing is placed; step one tile away and it places normally.
- (If Decision 1 accepted) An Act 2 level: walk into a far grid, die there →
  respawn in the start grid at `player_start`.

## Done when:

- [ ] `Room.enemies_initial` captured at construction; `World._reset_enemies()`
      restores every visited room's enemies (position + patrol leg)
- [ ] `_lose_life` resets player, blocks, and all enemies; `_on_caught` only
      relocates the catcher on a shielded (no-life-lost) hit
- [ ] A crafted wall/block cannot be placed on the start room's `player_start`
      (Act 1 `_place_wall` and Act 2 `_act2_place`), rejected without consuming
      the credit/item
- [ ] Decision 1 (Act 2 respawn room) resolved and implemented per the user's
      choice
- [ ] New tests red first, then green; `poe test` exits 0 with any affected
      death goldens deliberately re-recorded
- [ ] User confirms in-game: death snaps player + all enemies back to starts,
      and no wall can be crafted on the start tile (manual acceptance)
