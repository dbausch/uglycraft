# Spec 0044 — Characterization harness for gameplay logic

Step 0 of the world-model refactor (→ `kb/world-model-review.md` §6): pin the
**current** behaviour of the runtime gameplay code (`game.py`, `entities.py`,
`crafting.py`, `rooms.py`) with golden-master tests *before* any refactoring
begins. No behaviour changes except the three named production edits (H1 clock
seam, H2 seed helper, H8 BL-33 fix).

## Status

- [x] H1 — Clock seam: all five `pygame.time.get_ticks()` call sites in
      `game.py` route through an overridable `Game.now()`
- [x] H2 — Determinism helpers: `levels.set_game_seed(seed)` + pytest fixture
      pinning the global `random`
- [x] H3 — Headless harness: fixtures + script driver (`tests/harness.py`)
- [x] H4 — Trace recorder: per-tick state + `sounds.play` event log, golden
      JSON files, explicit re-golden procedure
- [x] H5 — Golden traces: Act 1, levels 1–10
- [x] H6 — Golden traces: Act 2 mechanics (hand-written fixture levels) +
      two seeded generator levels
- [x] H7 — Golden screenshots (small set, pinned clock)
- [x] H8 — BL-33 fixed test-first: Act 1 render test red → guard → green
- [x] H9 — Performance tripwire (timed headless run)
- [x] H10 — Suite integration: everything runs under `poe test`;
      `kb/feature-inventory.md` §7 updated

## Motivation

The staged world-model refactor will touch nearly every line of `game.py`.
The generator already has a test suite (`tests/`, 12 files); the runtime
gameplay has none. Characterization tests recorded against the current code
through its **outermost seams only** (events in, state + sounds out) survive
all refactor stages unchanged and turn "did the refactor change anything?"
into an exact comparison. They are also, immediately, the missing gameplay
test suite.

## Determinism audit (basis for H1/H2)

Verified 2026-07-10:

- All gameplay randomness uses the **global `random` module**: enemy BFS
  tie-break (`entities.py:119`), wander (`entities.py:59`), treasure
  spawn/relocate (`game.py:645/659`), enemy respawn (`game.py:1020`), title
  ogres (`game.py:679-680`). `random.seed(k)` pins all of it.
- Act 2 level content derives from `levels._game_seed`. **Caution:**
  `Game._full_reset()` calls `levels.new_game_levels()`, which reseeds from
  `_rnd.Random().randint(...)` — OS entropy, *not* the global `random`
  module. Deterministic Act 2 tests must therefore set the seed **after**
  `_full_reset()` and before the first `get_level()` call for the level
  under test (level 1 will already be cached; that is fine).
- `pygame.time.get_ticks()` (wall clock) appears in `game.py` at five sites:
  gameplay — key-repeat registration (`_playing_event`, :797) and repeat
  check (`_update_playing`, :1063); render-only — boss animation frame
  (:1325), title ogre phase (:1621), name-entry cursor blink (:1790).
- Headless operation works: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`,
  `pygame.init()`, `Game(pygame.Surface((960, 540)))` — verified in-session
  (this is how BL-33 was found).

## Deliverables

### H1 — Clock seam

`Game` gets a `now()` method (or attribute) returning
`pygame.time.get_ticks()` by default. All five call sites above use
`self.now()` instead of calling pygame directly — including the three
render-only sites, because golden screenshots (H7) need pinned animation
frames. Tests override with `game.now = lambda: fake_ms`. No other
behaviour change; with the default, the game is bit-identical to today.

### H2 — Determinism helpers

- `levels.set_game_seed(seed)` — sets `_game_seed` and clears `_act2_cache`
  (mirror of what `new_game_levels()` does, minus the entropy). Production
  code, test-only caller.
- pytest fixture `pin_rng` — `random.seed(fixed)` before each test.
- pytest session fixture: set SDL dummy drivers **before** `pygame.init()`,
  init once.

### H3 — Script driver (`tests/harness.py`)

- `make_game()` — headless `Game` factory (no `present` wired; the loading
  callback already no-ops when `present is None`).
- `start_level(game, n, difficulty)` — difficulty + `_full_reset()` +
  (for n > 1) `set_game_seed(...)` + `_start_level(n)` + state `PLAYING`.
- `run_script(game, script, dt=33)` — executes a step list. Each step is one
  tick: optionally inject synthesized `pygame.event.Event`s
  (KEYDOWN/KEYUP with a real `key`), then call `game.update(dt)`. The fake
  clock advances `dt` per tick and feeds `game.now`. Steps support holding
  keys across ticks so the key-repeat path (:797/:1063) is exercised.
- Scripts do **not** need to achieve game goals; they need to cover code
  paths. Where a mechanic is expensive to reach by play (shield needs
  250 points), the script may seed state directly (score, inventory
  contents) before running — the trace pins behaviour *from that state*.

### H4 — Trace recorder + goldens

- Recorder monkeypatches `game.sounds.play` (and `start_music`) to append
  `(tick, key)` to an event log — the SFX trigger map is a complete
  semantic event log (move/bump/break/collect/caught/level_up/…).
- Per-tick snapshot: `(state, level, score, lives, player col, player row,
  current_room)`. Snapshot + event log serialize to JSON under
  `tests/golden/`.
- Comparison is exact (`==`). Re-recording goldens only via explicit env
  var: `UGLYCRAFT_REGOLD=1 pytest ...` rewrites instead of asserting.
  Golden diffs must be reviewed and committed deliberately — a re-record is
  a statement that a behaviour change is intentional.

### H5 — Golden traces, Act 1 (levels 1–10)

Per level, scripted runs covering: movement + wall bump/break (3 hits,
credit at 2 breaks), wall placement, shield buy + expiry + caught-with-
shield, death (walk into enemy) and score penalty, treasure collection and
item sequence, level advance, boss level (relocation on item walk-over,
crown at fixed position). Both difficulties for at least one level (greedy
vs BFS enemies).

### H6 — Golden traces, Act 2 mechanics

Two layers:

1. **Hand-written fixture level dicts** (deterministic mini-levels, one per
   mechanic, injected by monkeypatching `levels.get_level` — same trick the
   runtime already tolerates): locked door + key (auto-open on bump),
   plate + block + gate (push, hold-open, reset on death), water + bridge
   auto-craft (one bridge per water room, opposite-floor rule), flame jet
   (phase timing, shield protection), room transition + state persistence
   (leave/return: walls, enemies, items restored), inventory crafting
   (stone wall recipe, quick-place), forge ogre attacking a placed wall,
   patrol enemy waypoint loop.
2. **Two seeded generator levels** (11 and 13 via `set_game_seed`) as
   integration traces — walk a fixed input sequence, record whatever
   happens. Deeper levels are excluded (level 20 generation ≈ 3.6 s).

### H7 — Golden screenshots

With `now` pinned: `render()` into the logical surface, hash
`pygame.image.tobytes(surf, 'RGB')` (SHA-256), compare against stored hex.
Small set: title, difficulty, one Act 1 field (level 3), boss level field,
one Act 2 fixture field (door+gate+water visible), inventory screen, HUD
row. Same `UGLYCRAFT_REGOLD` procedure.

**These are the fragile tests — adopted deliberately, on trial.** Any
intentional visual change invalidates them wholesale (that is what
`UGLYCRAFT_REGOLD=1` + reviewed re-record is for), and a hash mismatch
says only *that* pixels changed, not where. We try them out; if in
practice they cost more re-recording than they catch regressions, they
get dropped or reduced without touching H4–H6. Spec 0043 (native
resolution) would invalidate all of them, but 0043 is unscheduled /
possibly out of scope — noted, **not** a dependency or sequencing input;
traces (H4–H6) are resolution-independent regardless.

### H8 — BL-33 fix (test-first)

The Act 1 field screenshot/render test is **red today**: `_render_field`
(game.py:1230) reads `self._current_room_data`, only assigned in
`_enter_room` (Act 2 path) — every Act 1 render raises `AttributeError`
(regression from `04be23e`, post-v1.5, → `kb/backlog.md` BL-33). Fix:
guard the entrance-sprite block with `if self._is_multiroom:` (the
staircase block below it already is). Fix lands as its **own commit** after
the red test is committed, then the test goes green.

### H9 — Performance tripwire

One timed test: N ticks (≈2000) of an Act 1 level headless, assert wall
time under a generous threshold (order 5 s) to catch accidental
quadratic behaviour during the refactor. Marked `slow`-tolerant; threshold
errs far on the side of never flaking.

### H10 — Suite integration

All new tests live under `tests/` and run with the existing
`poe test` (`pytest tests/ -v`). Goldens are committed. After user
acceptance, update `kb/feature-inventory.md` §7 (coverage table) and the
checklist here.

## Non-goals

- **No refactoring.** `World` extraction is spec 0045 (Stage 1).
- No behaviour changes beyond H1 (identical by default), H2 (new helper),
  H8 (bug fix).
- No unit tests against `Game` internals (`_room_gates`,
  `_build_walls_multiroom`, …) — those structures are deleted in stages
  3–5; fine-grained unit tests are written against the `World` API from
  Stage 1 onward.
- No goldens for the sound *waveforms* or music content — only which sound
  keys fire when.

## Verification

This spec's deliverable is itself an automated suite; the gates are:

1. `poe test` exits 0 with the new tests included (except the deliberately
   red BL-33 test before its fix commit).
2. Golden files committed; a second full run reproduces them exactly
   (determinism proof).
3. Manual spot check by the user: `poe run` still plays identically
   (H1/H2/H8 touch production code).

## Done when:

- [x] H1 — all five `get_ticks` sites route through `Game.now()`; game
      plays identically (user-confirmed) (d672ad9)
- [x] H2 — `set_game_seed` + `pin_rng` fixture exist; same seed ⇒ same
      Act 2 level, twice in a row (5a16fa2, f157c52)
- [x] H3 — a scripted headless run of level 1 completes with no display (f157c52)
- [x] H4 — trace JSON written and exactly reproduced on a second run;
      `UGLYCRAFT_REGOLD=1` rewrites (f157c52, fa1155d)
- [x] H5 — Act 1 goldens for levels 1–10 committed and green (422c433, fa1155d, df1456f)
- [x] H6 — one fixture-level golden per Act 2 mechanic + seeded levels 11
      and 13 committed and green (a7fae25)
- [x] H7 — screenshot goldens committed and green (ee6b404)
- [x] H8 — BL-33 test committed red, fix committed separately, test green (0f3713b, ec6ffcd)
- [x] H9 — timed run present and green (e710d72)
- [x] H10 — `poe test` runs everything; `kb/feature-inventory.md` §7
      updated (1ee0937)
