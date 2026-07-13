# UGLYCRAFT — Game Mechanics Reference

*(Updated 2026-07-12 after the world-model refactor, specs 0045–0052:
rules live in `world.py` over the `cells.py` layered model; `game.py` is
presentation only.  The mechanics below are unchanged — the refactor was
behaviour-preserving — but state now lives on model objects, not on
scattered `Game` attributes.)*

## Speed Scaling Formula

`factor = 1.07 ** (10 - level)`. Applied at level start.

| Level | factor | player move_ms | enemy move_ms |
|---|---|---|---|
| 1 | 1.838 | 147 ms | 294 ms |
| 3 | 1.500 | 120 ms | 240 ms |
| 5 | 1.403 | 112 ms | 224 ms |
| 7 | 1.225 | 98 ms | 196 ms |
| 9 | 1.070 | 86 ms | 171 ms |
| 10 | — (fixed) | 80 ms (`BASE_MOVE_MS`) | 82 ms (`BOSS_MOVE_MS`) |

At level 10 the boss uses a fixed `BOSS_MOVE_MS = 82` — about 2.5% slower than the player's maximum key-repeat speed (80 ms), but only if the player holds a key without releasing.

## Key Repeat Mechanism

On `KEYDOWN`: registers `(now, now)` per key. Each update tick: movement fires immediately on first press. Key-repeat fires after `FIRST_REPEAT_MS = 180 ms` initial delay, then at `move_ms` intervals (level-scaled). A successful move clears `_bump_consumed` for that key; a wall bump sets it, preventing multiple bumps per keypress without releasing the key.

## Scoring

**Per item:** `TREASURE_POINTS = {1: 100, 2: 200, …, 9: 900, 10: 1000}`. Crown (item 10, level 10 only) gives 1000.

**Final score:** `score * max(1, lives)`. The `max(1, …)` means a game-over at 0 lives still multiplies by 1, not 0.

**Death penalty:** `score = max(0, score - LIFE_PENALTY)` where `LIFE_PENALTY = 500` (flat). Penalty applied before decrementing lives. `item_no` is NOT reset on death — the item sequence continues on the same level.

## Lives

- Start: `STARTING_LIVES = 9`
- Gain: +1 on each level advance
- Loss: caught without shield → `score -= 500 (min 0)`, `lives -= 1`
- Game over: `lives <= 0`
- No "buy a life" mechanic; the shield is the in-game purchase instead

## Shield System

- Cost: `SHIELD_COST_PTS = 250`, requires `score >= 250`, no shield already active
- Duration: `SHIELD_DURATION_MS = 10_000` ms (10 s), tracked in `_shield_timer`
- Effect when caught: shield consumed, no life lost, enemy respawned ≥ 8 tiles away. Sound: `caught_shield`. The enemy is always respawned on any catch (shield or not).
- Expiry: `shield_expire` sound plays; no refund
- HUD: shows `SHIELD XX` (seconds rounded up: `(_shield_timer + 999) // 1000`) when active; same 9-char field rendered invisible when inactive (maintains layout stability)

## Wall Breaking / Placement System

- `WALL_HITS_TO_BREAK = 3` bumps (by any direction key) destroys one inner wall
- `HALVES_PER_CREDIT = 2` walls destroyed earns 1 placement credit; counter (`_block_halves`) carries over between levels
- Wall state: bump damage lives on the wall's `Barrier.hits` (cells.py); a new level builds fresh barriers, so damage never carries over
- Bump consumed: once a key bumps a wall, that key must be released before registering another bump. A successful move clears the consumed flag. Border cells can never be bumped.
- Crack sprites: `crack1` at hit 1, `crack2` at hit 2, wall disappears at hit 3
- On level advance: one credit refunded per player-placed wall still standing in the current room (counted from the `placed` barriers in cells)
- Placed walls are visually distinct from level walls: blue fill `(30, 30, 80)` vs dark-red `(90, 22, 22)`

## Treasure / Item System

**`item_no` lifecycle:** reset to 0 at `World.start_level`; `_spawn_treasure` increments before spawning. Item sequence never resets on death, only on level advance.

**Crown:** `treasure_item_no = 10 if (item_no == 9 and level == ACT1_BOSS_LEVEL) else item_no` (the doc previously said `NUM_LEVELS`, which has been 20 since Act 2 — the code always meant level 10). On level 10, item 9 becomes the Crown at fixed position `(14, 8)` (inside the innermost vault ring). Crown is never relocated when boss walks over it.

**Spawn:** picks randomly from all open tiles excluding player and enemy positions. Fallback if no open tiles: `(1, 1)` (border — inaccessible in practice).

## Enemy AI

**Easy / levels 1–9:** `move_toward` — greedy:
```python
if abs(dx) >= abs(dy):   # NB: >= not > (Pascal uses >)
    try horizontal, else vertical
else:
    try vertical, else horizontal
```
The `occupied` set prevents two enemies landing on the same tile. Enemies process in list order; earlier enemies win contested tiles.

**Hard / levels 1–9:** `move_bfs` — BFS distance map from player; picks a random neighbour with minimum distance. Enemy cannot be permanently blocked; randomises among tied shortest paths.

**Boss (level 10):** single enemy. Hard → `move_bfs` at `BOSS_MOVE_MS = 82`. Easy → greedy at same speed. Animated: 4 frames (`boss_0`–`boss_3`) at `(pygame.time.get_ticks() // 120) % 4`.

**Enemy respawn after catch:** BFS-teleports to tile with distance ≥ 8 from player; falls back to ≥ 4 if no candidates; does nothing if still no candidates (enemy remains on player tile — will trigger another catch next tick).

**Act 1 enemy confinement (spec 0066):** Act 1 has no `tile_owner`, so
`_tag_enemies_with_rooms` gives every Act 1 enemy `room_tiles = INTERIOR_TILES`
(all non-border tiles) while leaving `room_name = None`. `room_name is None`
keeps them always-chasing (the `move_toward`/`move_bfs` branch), and
`room_tiles` bars them from every border tile — so no enemy can occupy the
open entrance. Invisible while the door is closed (the border already
`blocked()`), so Act 1 movement/goldens are byte-identical; it only bites the
one newly-passable border tile once the entrance opens. Act 2 enemies were
already room-confined (spec 0051/BL-34).

## Level Completion (entrance exit, spec 0066)

Collecting the **last** award no longer advances the level on pickup.
Instead it **opens the entrance**, and the level ends only when the player
**walks out** through it — a two-phase flow that mirrors an Act 2 grid
change.

- The entrance (a fixed per-level border tile, spec 0064) is a
  `Barrier('gate', channel=ENTRANCE_CHANNEL)` — placed by the `_parse_entrance`
  `CONTENT_PARSERS` entry in `cells.py`. `ENTRANCE_CHANNEL = '__entrance__'`
  (constants.py) is reserved: no plate emits it, so `_latch_channels`'
  targeted relatch never touches it.
- **Open:** the last award (`item_no == 9` in Act 1 sequential;
  `_loot_collected >= _loot_total` in Act 2 preplaced) calls
  `World._open_entrance()` → adds `ENTRANCE_CHANNEL` to `self._channels`,
  emits `entrance_opened`. Act 1 also clears `treasure_pos` so the final
  treasure sprite disappears. `world.entrance_open` = `ENTRANCE_CHANNEL in
  self._channels`.
- **Walkable:** passability flows through the ordinary `cells.blocked(c, r,
  channels)` gate query — `world.blocked` is unchanged. The open entrance is
  a walkable exit gap; the player steps onto it like any tile.
- **Leave:** standing on the open entrance, an **off-screen press** (the
  outward bump against the screen edge, in `try_move`'s off-grid branch)
  calls `advance_level()` — level-up on 1–19, `game_over(won=True)` on 20.
  One press only steps onto the door; the second press exits.
- **Persistence:** the door stays open across death — `_reset_blocks` now
  does `self._channels = self._channels & {ENTRANCE_CHANNEL}` (was `set()`),
  preserving the entrance while still closing plate gates. Only `start_level`
  (`_channels = set()`) re-closes it. This `_reset_blocks` accommodation is
  temporary: it is deleted with `_reset_blocks` when BL-37 (self-healing
  exploding blocks) lands.
- **Rendering:** `game.py` blits `level_entrance_open` vs `level_entrance` by
  `world.entrance_open`, and **excludes** the entrance channel from the
  generic gate overlay (else a portcullis would paint over the door). Sound:
  `entrance_opened` → a distorted choir "ta-daa" fanfare (`sfx_entrance_open`).
- **Future:** grid zero will become a per-level boss area; the exit will then
  become a real grid transition (swap `advance_level()` for a transition),
  which is why the exit is routed through the same off-screen branch.

## Level Progression

**On level advance (`World.advance_level`, now triggered by walking out —
spec 0066):**
- `lives += 1`
- `_block_credits += <count of 'placed' barriers in the current room>` — refund credits for remaining placed walls
- `_bump_consumed.clear()`; barriers (and their damage) are rebuilt fresh for the new level
- `_block_halves` NOT reset (partial progress carries over)
- Score carried over

**On death (not game over):**
- `score -= 500 (min 0)`, `lives -= 1`
- Player repositioned to `player_start`; enemy BFS-respawned ≥ 8 tiles away
- Level continues; walls (with their bump damage), `_block_credits`, and `item_no` all intact

## Game State Machine

```
TITLE
  Enter → DIFFICULTY
  H → SHOW_SCORES → TITLE
  Q → QUIT_GAME

DIFFICULTY
  E/1 → LEVEL_INTRO (easy, full_reset)
  H/2 → LEVEL_INTRO (hard, full_reset)
  ESC → TITLE

STORY  ← unreachable from normal UI (no transition in)

LEVEL_INTRO (2 s timer)
  any key or timer → PLAYING

PLAYING
  P → PAUSED
  ESC → PLAY_AGAIN
  [win] → WIN
  [game over] → GAME_OVER

PAUSED
  P → PLAYING

WIN / GAME_OVER
  any key → ENTER_SCORE (if qualifies) or SHOW_SCORES

ENTER_SCORE
  Enter → SHOW_SCORES

SHOW_SCORES
  any key → _scores_return_to (TITLE or PLAY_AGAIN)

PLAY_AGAIN
  Y/J → DIFFICULTY   N/ESC → TITLE
```

`QUIT_GAME` is a terminal state — main loop exits.
