# 0028 — Lazy per-level Act 2 generation + startup burst fix (BL-11)

## Status

- [x] Act 2 levels are generated lazily, one level at a time, on first access — 8bed7e1
- [x] No Act 2 generation happens at `import levels` — 8bed7e1
- [x] `_full_reset` / new-game no longer regenerates all 10 Act 2 levels eagerly — 8bed7e1
- [x] A new game reshuffles Act 2 (fresh random levels), still without up-front cost — 8bed7e1
- [x] `--level N` debug launch generates only level N (lazily) — 8bed7e1
- [x] Main loop clamps `dt` so a long hitch never produces an enemy-movement burst — 8bed7e1 (code; no-burst pending user confirmation)
- [ ] A "Loading . . ." frame (white on black) is shown before/during any uncached Act 2 generation *(manual)*
- [ ] The loading dots fill to indicate generation progress *(manual)*
- [ ] Level music and enemy movement begin together when the level graphic first appears *(manual)*

## Problem (measured)

Launching `--level 11` shows a blank window for ~10–20 s with music playing,
then the graphic appears and all enemies move at frame-rate ("go crazy") for
1–2 s before settling to normal speed.

Measured costs (dummy SDL drivers, this machine):

| Step | Cost | When | Window state |
|---|---|---|---|
| `from levels import LEVELS` → `_generate_act2()` (`levels.py:356`) | ~9.8 s | `main.py:19`, before `pygame.init()` | no window yet |
| `Game(logical)` — sprites + sound synthesis + fonts | ~1.7 s | `main.py:66`, after window opens | blank |
| `game._full_reset()` → `regenerate_act2()` (`game.py:214-215`) | ~9.8 s | `main.py:74`, after window opens | blank |
| `game._start_level(11)` → `LEVELS[10]` (already built) | ~0 s | `main.py:75` | blank |

Per-level generation cost (isolated): **level 11 ≈ 20 ms** (1 grid),
**level 20 ≈ 3.6 s** (10 grids). Generating all ten ≈ 10.6 s.

### Root causes

1. **Double, eager generation.** All ten Act 2 levels are generated at import
   (`levels.py:356`) and then **thrown away and regenerated** by
   `regenerate_act2()` inside `_full_reset` (`game.py:215`). The import-time set
   is never played. Together this is ~20 s of work for a level that costs 20 ms.

2. **The first frame is never drawn until all that work finishes.** `set_mode`
   opens the window (`main.py:55`), but the main loop's first `render()`/
   `flip()` (`main.py:98`/`114`) only runs after `Game()` and `_full_reset()`
   return. Title music starts inside `Game()` (`_title_init` →
   `start_music('title')`, `game.py:89`→`635`), which is why music plays over a
   blank window.

3. **Un-clamped first `dt` → enemy burst.** The `clock` is created at
   `main.py:65`, before all the slow work. The first `clock.tick(FPS)`
   (`main.py:81`) therefore returns a `dt` of ~11 s. `update(dt)` does
   `self._enemy_timer += dt` (`game.py:1035`); the drain is an `if`, not a
   `while` (`game.py:1036`), so each frame subtracts one `enemy_ms` (~200 ms)
   but adds back only ~16 ms. The ~11 000 ms backlog bleeds out at ~184 ms/frame
   → ~60 frames (~1–2 s) of every-frame enemy movement. This is the literal
   BL-11 symptom.

## Design

### 1 — Lazy per-level generation (`levels.py`)

- Extract the ten Act 2 feature dicts out of `_generate_act2` into a module
  constant `ACT2_FEATURE_SETS` (order = level 11 … level 20).
- Add a per-game cache and seed:
  - `_act2_cache: dict[int, dict]` keyed by level number (11–20).
  - `_game_seed: int` — the base seed for the current game.
- `get_level(level_num) -> dict`:
  - Act 1 (`level_num <= _ACT1_COUNT`): return `LEVELS[level_num - 1]`.
  - Act 2: return `_act2_cache[level_num]` if present; otherwise generate the
    single level from `ACT2_FEATURE_SETS[level_num - _ACT1_COUNT - 1]` using a
    seed **derived deterministically** from `_game_seed` and the Act 2 index
    (`_rnd.Random(_game_seed + index)` — same scheme as the current loop), cache
    it, and return it. Generation reuses the existing retry-on-`LayoutError`
    loop unchanged.
- `new_game_levels()` (replaces `regenerate_act2`): pick a fresh random
  `_game_seed` and clear `_act2_cache`. **Generates nothing.** Each new game
  thus gets fresh random Act 2 levels, but pays only for the levels actually
  visited.
- `TOTAL_LEVELS = _ACT1_COUNT + len(ACT2_FEATURE_SETS)` (= 20). Export it.
- Remove the eager `LEVELS.extend(_generate_act2())` at module top level.
  `LEVELS` holds only the 10 Act 1 dicts after import.
- Initialise `_game_seed` once at import (so `get_level` works even if
  `new_game_levels` was never called, e.g. tests) without generating anything.

**Determinism note:** deriving each level's seed from a single `_game_seed`
means level N is identical whether reached by play or by `--level N`, within one
process. Each process launch (and each `new_game_levels()`) picks a new random
`_game_seed`, so relaunching `--level 11` still yields a fresh level — matching
today's behaviour.

### 2 — Wire game.py and main.py to the accessor

- `game.py:35` `NUM_LEVELS = len(LEVELS)` → `NUM_LEVELS = TOTAL_LEVELS`
  (import from `levels`).
- Replace direct `LEVELS[...]` reads that index the *current/target* level with
  `get_level(...)`:
  - `game.py:236` `data = LEVELS[level_num - 1]` → `get_level(level_num)`
  - `game.py:603` `data = LEVELS[self.level - 1]` → `get_level(self.level)`
  - `game.py:901` `data = LEVELS[self.level - 1]` → `get_level(self.level)`
- Replace `regenerate_act2()` calls with `new_game_levels()`:
  - `game.py:214-215` (in `_full_reset`)
  - `game.py:404-405` (new-game / play-again path)
- `main.py:70` `min(args.level, len(LEVELS))` → `min(args.level, TOTAL_LEVELS)`.

### 3 — Clamp `dt` (the burst fix)

- Add `MAX_DT_MS` to `constants.py` (proposed **100 ms**).
- `main.py:81`: `dt = min(clock.tick(FPS), MAX_DT_MS)`.

This bounds the time injected into `_enemy_timer` on *any* frame, so neither the
startup work nor a mid-game lazy generation of a heavy level (16/18/20) can
produce a movement burst. The existing reset of `_enemy_timer`/`_move_timer` to
0 in `_start_level` (`game.py:317-318`) remains as belt-and-suspenders.

### 4 — Loading frame with progress dots

Goal: the player sees a progress indicator during generation instead of a
frozen/blank window, and the level's first real frame (with music + enemy
motion) appears *after* generation, together.

**Appearance.** Centred white text on a black background:

```
Loading . . . . . . . . . .
```

The word `Loading` is always shown. The dot field is **10 slots wide** (so the
text never shifts); dots **fill left-to-right to indicate progress** as
generation proceeds. The 10-slot width is fixed regardless of how many work
units a given level has — `filled = round(10 * done / total)`.

**Progress source.** Generation reports progress as it builds:

- Multi-grid levels: the work unit is **one grid**. `_build_super_grid` builds
  grids sequentially; `total = grid_count`, `done` increments after each grid is
  laid out. (Level 20 → 10 grids → one dot per grid; the 10-slot field then maps
  1:1.)
- Single-grid levels (11–13 etc.): `total = 1`; the field jumps 0 → 10 when the
  single build completes. At ~20 ms this flashes imperceptibly.
- On a `LayoutError` retry, progress resets to 0 for the new attempt.

**Mechanism (synchronous, no threads).**

- `build_level_dict` / `_build_super_grid` accept an optional
  `progress=callable` parameter, invoked as `progress(done, total)` after each
  grid (and once at start with `(0, total)`). `get_level(n, progress=...)`
  forwards it.
- `Game.draw_loading(done, total)` renders the screen above to `self.surf`.
- Factor the scale-blit-flip from `main.py:100-114` into a small `present()`
  helper so a frame can be drawn outside the main loop.
- The progress callback passed into generation does: `draw_loading(done,total)`
  → `present()` → pump `pygame.event.get()` (so the OS does not flag the window
  "not responding" during a multi-second grid build).
- Before any `_start_level(n)` that may trigger Act 2 generation
  (`n >= ACT2_START_LEVEL` and `n` not cached), paint the initial
  `draw_loading(0, total)` frame, then run generation with the callback. Entry
  points:
  - **Debug path** (`main.py`): before `game._start_level(level)`.
  - **In-game** (`game.py:_advance_level`, before `_start_level` at `879`):
    generation runs *before* the `LEVEL_INTRO` state is entered, so the loading
    frame must be shown here.

The loading frame keeps whatever music is currently playing (title or previous
level). `_start_level` still calls `start_music(level_num)` at its end, so level
music begins exactly when the level is ready — together with the first PLAYING
frame and clean (reset, clamped) enemy timers.

## Tests (`tests/test_lazy_levels.py`, new)

Run with `poe test`.

- `import levels` performs **no** Act 2 generation: `len(LEVELS) == _ACT1_COUNT`
  and `_act2_cache == {}` immediately after import.
- `TOTAL_LEVELS == 20`.
- `get_level(n)` for Act 1 returns the exact `LEVELS[n-1]` object.
- `get_level(11)` returns a dict with the expected level keys and is **cached**:
  a second call returns the same object; the cache contains only key 11
  (laziness — accessing 11 does not generate 12–20).
- Determinism: with `_game_seed` fixed, clearing the cache and re-fetching
  `get_level(11)` yields an equal level structure.
- `new_game_levels()` empties `_act2_cache` and changes `_game_seed`.

`dt` clamp and loading frame are verified manually (see below) — they live in
`main.py` / rendering and are not covered by the pytest suite.

## Manual verification

1. `poe run --level 11` (easy): graphic appears within a fraction of a second;
   enemies move at normal speed immediately (no 1–2 s burst); level music starts
   as the graphic appears.
2. `poe run --level 20`: the "Loading . . ." frame shows with dots filling one
   per grid as generation proceeds, then the level appears with no enemy burst.
3. Normal play from the title into Act 2 (level 10 → 11): transition is smooth;
   heavy levels show the loading frame; no burst on arrival.
4. Start a new game twice and reach level 11 each time: the layout differs
   (fresh seed per game).

## Done when

- [x] `import levels` generates no Act 2 levels; `_act2_cache` empty, `LEVELS` has 10 entries — *(test)* 8bed7e1
- [x] `get_level()` generates Act 2 levels lazily and caches them; only accessed levels are built — *(test)* 8bed7e1
- [x] `new_game_levels()` reshuffles (new seed, cleared cache) with no up-front generation — *(test)* 8bed7e1
- [x] `--level N` clamps to `TOTAL_LEVELS` and generates only level N — *(smoke-verified)* 8bed7e1
- [ ] `--level 11` shows the graphic near-instantly with no enemy burst — *(manual / user acceptance)*
- [ ] Heavy Act 2 levels (16/18/20) show the "Loading . . ." frame with dots filling per grid instead of a frozen window — *(manual / user acceptance)*
- [ ] Level music and enemy movement begin together with the level graphic — *(manual / user acceptance)*
- [x] `poe test` green — 8bed7e1 (344 passed)
