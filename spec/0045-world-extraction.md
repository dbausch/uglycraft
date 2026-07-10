# Spec 0045 — Extract `World` from `Game` (world-model refactor, Stage 1)

Stage 1 of the world-model refactor (→ `kb/world-model-review.md` §3):
move all world state and gameplay rules out of `game.py` into a new,
**pygame-free** `world.py`, connected to the presentation layer by a typed
event stream. Pure code motion plus the event seam — **zero behaviour
change**, proven by the spec-0044 goldens staying byte-identical.

## Status

- [ ] W1 — `world.py`: `World` class owning all gameplay state + rules;
      importing it must not import pygame
- [ ] W2 — Event stream: `World` emits typed events; `Game` drains them
      once per frame and maps them to sounds/music/flash/state changes,
      preserving today's exact ordering
- [ ] W3 — `Game` delegates: input handlers call `World` methods; per-frame
      `update(dt)` forwards to `world.update(dt)`; key-repeat scheduling
      stays in `Game`
- [ ] W4 — Rendering reads `World` state (draw-only; no game logic left in
      `_render_*`)
- [ ] W5 — All spec-0044 golden files **byte-identical** (traces and
      screenshots; `git diff --quiet tests/golden/`), full suite green
- [ ] W6 — Import-isolation test: `world` (and the modules it pulls in)
      never import pygame
- [ ] W7 — Docs: root `CLAUDE.md` architecture table, `kb/architecture.md`
      pointer, `kb/feature-inventory.md`, `kb/world-model-review.md`
      Stage 1 marked done

## Motivation

`Game` currently owns the pygame surface, fonts, sprites, sounds, input,
the menu state machine, **and** every rule of the game world. Rules cannot
be tested without constructing a `pygame.Surface`, and `sounds.play(...)`
calls are embedded inside world mutators. Splitting World (rules, no
pygame) from Game (presentation + input + state machine) is the enabling
step for every later stage: fine-grained unit tests get a real API to test
against, and stages 2–5 refactor `world.py` under both golden and unit
coverage.

## The split

### `World` owns (moves out of `Game`)

State: `level`, `score`, `lives`, `shield` + `_shield_timer`, `item_no`,
`treasure_item_no`, `treasure_pos`, `player`, `enemies`, `inventory`,
`move_ms`/`enemy_ms`, `walls` (collision grid), `_level_walls`,
`_placed_walls`, `_wall_hits`, `_breaks_toward_credit`, `_place_credits`,
`_bump_consumed`, the multiroom family (`_is_multiroom`, `_current_room`,
`_current_room_data`, `_room_states`, `_room_treasures`, `_room_materials`,
`_room_keys`, `_room_doors`, `_room_blocks`, `_room_blocks_initial`,
`_room_plates`, `_room_gates`, `_gate_open`, `_opened_doors`,
`_bridged_tiles`, `_bridged_water_rooms`, `_water_tiles`,
`_water_tile_room`, `_dead_squares`, `_flame_jets`, `_flame_timer`,
`_tile_owner`, `_loot_total`, `_loot_collected`), `_enemy_timer`,
`_move_timer`.

Logic: `_full_reset` (→ `World.__init__`), `_start_level`, `_enter_room`,
`_save_room_state`, `_build_walls` / `_build_walls_multiroom`,
`_bfs_from`, `_register_bump`, `_break_wall`, `_is_border`,
`_is_unbumpable`, `_try_move_key`'s world half (movement/push/bump given a
direction), `_place_wall`, `_act2_place`, `_buy_shield`, `_collect_loot`,
`_collect_materials`, `_collect_keys`, `_update_pressure_plates`,
`_try_push_block`, `_try_auto_open_door`, `_try_auto_bridge`,
`_spawn_treasure`, `_relocate_treasure`, `_advance_level`'s world half,
`_on_caught`, `_lose_life`, `_reset_blocks`, `_forge_ogre_attack`,
`_respawn_enemy`, `_verify_blocks`, `_tag_enemies_with_rooms`,
`_player_room`, the enemy/collision/flame/plate/pickup part of
`_update_playing`, and the end-game scoring (`final_score`).

### `Game` keeps

Window surface, fonts, sprites, `SoundManager`, `now()` clock seam, the
menu/state machine (`TITLE` … `PLAY_AGAIN`), all `handle_event` menu
branches, **key-repeat scheduling** (`_key_repeat`, `FIRST_REPEAT_MS`,
per-key timing — input hardware behaviour, not world rules), all
`_render_*` functions, title-ogre animation, the loading screen,
hiscore glue (`try_enter_score`), `_debug`.

### Interface sketch

```python
class World:
    def __init__(self, difficulty, progress=None)      # was _full_reset
    def start_level(self, n, progress=None)
    def try_move(self, dcol, drow, key_id) -> bool     # move/push/bump
    def key_released(self, key_id)                     # clears bump-consumed
    def place(self)                                    # SPACE (Act 1 + Act 2)
    def buy_shield(self)                               # ENTER
    def advance_level(self)                            # F10 / level complete
    def update(self, dt)                               # timers, enemies,
                                                       #   collisions, plates,
                                                       #   flames, pickups
    def drain_events(self) -> list                     # emitted since last call
```

`Game.handle_event` translates keys into these calls; `Game.update`
forwards `dt` and then drains + dispatches events. Rendering reads
`world.<attr>` directly (public read access is fine at this stage).
The harness keeps driving `Game` — traces must not notice the split.

### Events

`World` never touches `SoundManager`. Every current `sounds.play(key)` /
`start_music` / `stop_music` call site inside world logic becomes an
appended event; `Game` maps events back to the identical calls **in the
identical order** (the golden sound traces are the proof). Event kinds
(1:1 with today's triggers):

```
moved, bumped, wall_broken, credit_earned, wall_placed, collected,
shield_bought, shield_expired, caught, caught_shielded, life_lost,
level_advanced(n), game_over(won), boss_appeared, item_relocated,
music(key), music_stop, level_complete, flash(ms)
```

plus state-machine signals `Game` consumes: `level_advanced` →
`LEVEL_INTRO` + intro timer, `game_over(won)` → `WIN`/`GAME_OVER`.
Exact set may be adjusted during implementation as long as the mapping
reproduces today's sound/music order exactly.

### Facade for compatibility

`Game` keeps read-only delegating properties for the names the renderer
and the 0044 harness touch (`player`, `enemies`, `score`, `lives`,
`level`, `shield`, `state` stays native, `_current_room`, …), so
`tests/harness.py` snapshots keep working unchanged. Tests that *seed*
deep state (`h.game.score = …`, `_room_blocks`, `inventory`) may be
updated to reach through `h.game.world` — allowed test edits; **golden
files are not re-recorded**.

## Non-goals

- No data-model changes: the parallel per-room dicts move as they are
  (Stage 3 restructures them).
- No Act 1 / Act 2 unification (`_is_multiroom` moves untouched — Stage 2).
- No new unit-test suite yet — this spec only creates the API for it;
  fine-grained unit tests accumulate from Stage 2 onward.
- No behaviour fixes, however tempting; anything found goes to the backlog.

## Verification

1. `poe test` green — **with zero golden diffs**: `git status tests/golden/`
   clean, no `UGLYCRAFT_REGOLD` run anywhere in this stage. The unchanged
   goldens (traces *and* screenshots) are the definition of
   "behaviour-preserving".
2. New import-isolation test (W6): a subprocess imports `world` and
   asserts `'pygame' not in sys.modules`.
3. Manual gate: user plays (`poe run`) — menus, Act 1, Act 2, pause,
   inventory, death, game over.

## Done when:

- [ ] W1 — `world.py` exists, owns the state/logic listed above; `game.py`
      contains no gameplay rules
- [ ] W2 — event stream in place; sound/music calls only in `Game`
- [ ] W3 — input → `World` API; `Game.update` forwards and drains
- [ ] W4 — `_render_*` read-only against `World`
- [ ] W5 — full suite green with byte-identical goldens
- [ ] W6 — import-isolation test green
- [ ] W7 — docs updated (architecture table, kb links, Stage 1 ticked)
