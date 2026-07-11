# Spec 0046 — Act 1 becomes a one-room Act 2 level (refactor Stage 2, BL-35)

Stage 2 of the world-model refactor (→ `kb/world-model-review.md` §3):
delete the `_is_multiroom` fork wholesale by wrapping Act 1 level dicts as
single-room multiroom levels at the `World.start_level` boundary. The two
genuinely different mechanics stop being a global code fork and become
**per-level rules** in the level dict. Zero behaviour change, proven by
the spec-0044 goldens staying byte-identical.

## Status

- [x] S1 — `_as_multiroom()` wrapper in `world.py`: Act 1 dicts are wrapped
      as `{'rooms': {None: …}, 'start_room': None, …}` on entry to
      `start_level`; the Act 1 setup branch in `start_level` is deleted
- [x] S2 — Per-level rules `spawn_mode` (`'sequential' | 'preplaced'`) and
      `crafting` (bool) replace the act fork for treasure logic and SPACE/TAB
- [x] S3 — All 22 `_is_multiroom` sites in `world.py` deleted; no call site
      chooses between `_build_walls` and `_build_walls_multiroom` any more
      (the `_build_walls` trap is structurally gone)
- [x] S4 — `game.py` re-keyed: TAB gate, HUD SEEK/LOOT, field-render
      branches, facade attribute list (`_is_multiroom` removed;
      `spawn_mode`, `crafting` added)
- [x] S5 — First fine-grained `World` unit tests (`tests/test_world.py`,
      pygame-free, red-first for the new rule attributes)
- [x] S6 — All spec-0044 goldens **byte-identical** (no re-record), full
      suite green
- [x] S7 — Docs: `kb/world-model-review.md` Stage 2 done,
      `kb/feature-inventory.md` §3.1 wall-builder note, backlog BL-35
      progress note

## Motivation

`if not self._is_multiroom: return` guards and forked logic appear in 22
places in `world.py` and 5 in `game.py`. Attributes like `_water_tiles`
and `_current_room_data` exist only on the multiroom path, which is the
bug class behind BL-33 (Act 1 render crash) and the `_build_walls` trap
(calling the base builder from Act 2 silently drops doors/gates/blocks —
`kb/world-model-review.md` P2/P4). After this stage there is exactly one
world representation; the only per-act differences are declared data.

## Design

### The wrapper (S1)

`World.start_level` normalises the dict it gets from `get_level` /
`regenerate_level`:

```python
def _as_multiroom(data):
    if 'rooms' in data:
        return data
    return {
        'rooms': {None: {'walls': data['walls'],
                         'enemy_starts': data['enemy_starts']}},
        'start_room': None,
        'player_start': data['player_start'],
        'spawn_mode': 'sequential',
        'crafting': False,
    }
```

- **The single room is keyed `None`**, not `'main'`: the 0044 golden
  traces record `_current_room` every tick, and Act 1 has always reported
  `None`. Keying the room `None` keeps every trace byte-identical.
  (Stage 5 turns rooms into objects and can revisit naming.)
- Only `walls` and `enemy_starts` go into the room dict — every other
  room key (`treasures`, `exits`, `water_tiles`, `tile_owner`, …) is read
  with `.get(…, default)` by `_enter_room` and friends, so the empty
  defaults do the right thing.
- `crown_pos` and `player_start` are read from the **unwrapped** dict via
  direct `get_level(self.level)` calls (`_spawn_treasure`, `_lose_life`);
  the wrapper is runtime-only, the authoring format in `levels.py` does
  not change.
- Act 1's difficulty/boss enemy selection collapses into `_enter_room`'s
  existing logic: Act 1 starts are all bare `(c, r)` tuples (= `chaser`),
  so EASY's `special + regular[:1]` equals the old `starts[:1]`, and the
  boss level has exactly one enemy start in `levels.py`, so HARD's
  "all starts" equals the old `starts[:1]` boss exception. No behaviour
  difference for the shipped data; the goldens (all 10 Act 1 levels EASY,
  1 and 5 HARD, boss screenshot) pin it.
- RNG order is unchanged: `_enter_room` consumes no randomness, and
  `_spawn_treasure` stays at its current position in `start_level`.

### Per-level rules (S2)

Two rule keys, read once in `start_level` onto `self`:

| Key | Act 1 (wrapper) | Act 2 (default when absent) | Governs |
|---|---|---|---|
| `spawn_mode` | `'sequential'` | `'preplaced'` | `_spawn_treasure` on level start, treasure-collection branch in `update` (spawn-next vs loot-count), boss relocation loop, HUD `SEEK` vs `LOOT` |
| `crafting` | `False` | `True` | `place()` dispatch (`_place_wall` credits vs `_act2_place` inventory), TAB inventory screen availability |

Generated Act 2 dicts and the 0044 fixtures carry neither key; the
defaults make them behave exactly as today. `levellayout.py` is not
touched.

### Fork deletion (S3)

Every `if (not) self._is_multiroom` in `world.py` goes:

- **Guards that become no-ops** (collections now always exist, empty for
  Act 1) — deleted outright: `_is_unbumpable`, `_verify_blocks`,
  `_try_room_transition`, `_collect_materials`, `_collect_keys`,
  `_update_pressure_plates`, `_try_push_block`, `_try_auto_open_door`,
  `_try_auto_bridge`, `_reset_blocks`, the `try_move` off-grid branch,
  `_lose_life` (`_reset_blocks()` runs unconditionally; for Act 1 it
  clears nothing and rebuilds an identical wall grid), `update`'s
  `player_room` computation (Act 1 `_tile_owner` is `{}` → `None`, same
  as today) and flame-jet gate (`self._flame_jets` is `[]` for Act 1).
- **Wall-builder choices** (`_break_wall`, `_place_wall`, `_act2_place`)
  — always call `_build_walls_multiroom()`. For a wrapped Act 1 room
  (no exits/doors/blocks/water/gates) it computes exactly what
  `_build_walls()` computes. `_build_walls` survives only as the first
  phase *inside* `_build_walls_multiroom`; no call site can pick the
  wrong builder any more.
- **Mechanic forks** (`start_level` setup, `update` treasure branch,
  boss relocation, `place()`) — re-keyed on `spawn_mode` / `crafting`
  as per S2.

`self._is_multiroom` itself is deleted from `World`.

### Presentation re-keying (S4)

- `_playing_event` TAB gate: `self._is_multiroom` → `self.crafting`.
- `_render_hud`: LOOT vs SEEK on `spawn_mode == 'preplaced'`.
- `_render_field`: the entrance/staircase/overlay blocks lose their
  `_is_multiroom` gates and run unconditionally (`rk = self._current_room`
  hoisted; all collections exist and are empty for Act 1, `'entrance' in
  self._current_room_data` alone gates the entrance sprite). The treasure
  code renders **both** the room-treasure list (empty in Act 1) and
  `treasure_pos` (always `None` in Act 2) — no branch needed.
- Facade: `_is_multiroom` leaves `_WORLD_ATTRS`; `spawn_mode` and
  `crafting` join it.

### First World unit tests (S5)

`tests/test_world.py` — pygame-free (no harness, no `Game`): construct
`World('easy')` directly and assert against state + drained events.
Red-first where the API is new:

- wrapped Act 1: `_current_room is None`, `spawn_mode == 'sequential'`,
  `crafting is False`, `_room_treasures == {None: []}` (red until S1/S2)
- generated/fixture dict: `spawn_mode == 'preplaced'`, `crafting is True`
  (red until S2)
- behaviour smoke through the unified path (green before and after,
  locking the seam): bump-to-break emits `bumped/bumped/wall_broken`;
  `place()` in Act 1 consumes a credit and emits `wall_placed`;
  `buy_shield` respects the score threshold
- the import-isolation test (0045 W6) keeps covering the new code

## Non-goals

- No data-model changes beyond the two rule keys (Stage 3 restructures
  the parallel dicts).
- No `RoomState` changes (Stage 5).
- No generator changes; `levels.py` authoring format unchanged.
- No behaviour fixes; findings go to the backlog.

## Verification

1. `poe test` green with **zero golden diffs** (`git status tests/golden/`
   clean; no `UGLYCRAFT_REGOLD` anywhere in this stage). The traces record
   `_current_room` per tick — the `None` room key is what keeps them
   byte-identical.
2. New `tests/test_world.py` red-first for the rule attributes, then green.
3. Manual gate: user plays (`poe run`) — Act 1 walk/break/place/shield/
   death/boss, Act 2 door/gate/water/flames, pause, inventory.

## Done when:

- [x] S1 — wrapper in place, Act 1 setup branch deleted from `start_level`
      (aa9b050)
- [x] S2 — `spawn_mode` / `crafting` rules drive treasure and SPACE/TAB logic
      (aa9b050)
- [x] S3 — `grep -c _is_multiroom world.py` is 0; single wall-builder call site
      (aa9b050)
- [x] S4 — `game.py` re-keyed; facade updated (aa9b050)
- [x] S5 — `tests/test_world.py` in place (red-first attrs, then green)
      (aa9b050)
- [x] S6 — full suite green, goldens byte-identical (aa9b050 — 468 passed,
      `tests/golden/` untouched)
- [x] S7 — docs + BL-35 note updated (986d0f8, 492f35d)

User acceptance 2026-07-11: played the build — playable; the one glitch
found (grid exit landing in a "different level") was reproduced headlessly,
confirmed identical on pre-refactor commit 6fc59a7 (the `_verify_blocks`
regeneration net + stale-entry-teleport, NOT a 0045/0046 regression), and
filed as BL-36 (P1). Acceptance confirmed with that finding on record.
