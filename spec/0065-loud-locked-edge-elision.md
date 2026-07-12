# 0065 — Loud LayoutError when a LOCKED edge loses its door; layout failure log (BL-46)

## Status

- [x] `build_level_dict`'s barrier loop raises `LayoutError` for a LOCKED
      edge with an unplaced endpoint (packer-dropped room / uncarved
      closet) instead of silently skipping the door
- [x] Same loud treatment for a LOCKED edge between placed nodes whose
      connection tile is not found (should-be-unreachable per R-E4)
- [x] Every `LayoutError` escaping the top-level `build_level_dict` call
      is appended to `uglycraft-layout.log`: timestamp, message, the
      failing grid's name, and — multi-grid — an ASCII canvas of the
      grids built so far with the failing grid annotated at its super
      position (absorbed per-strategy candidates never log)
- [x] `leveldump.render_rooms(...)`: public dict-level renderer (no
      `World`, no `get_level`) used by the log — the BL-48 enabler
- [x] Deterministic pinned regression test (FS_ALL, seed 584) green;
      `test_key_door_pairing` green including the persisted hypothesis
      example; log entry asserted for the pinned failure
- [x] Sweep: ≥ 300 builds across the key feature sets succeed (the retry
      absorbs the raise); Act 2 goldens byte-identical
- [x] `poe test` exits 0; R-K1 / R-P3 wording reconciled in
      `kb/requirements.md`; BL-46 closed

## Problem

BL-46 (investigated 2026-07-12): hypothesis found seed 584 (`FS_ALL`,
single grid, first build attempt) where the generated level has a cyan
key but no cyan door — an R-K1 violation. Root cause chain:

1. The graph has a LOCKED edge `corridor–room_5` (colour cyan); the cyan
   key was placed in `room_3` by `add_locked_room` (prerequisites roam,
   R-V3 design).
2. The zone packer **dropped `room_5`** at the overflow check; spec 0032
   C7 spilled its content, so the build succeeded.
3. The barrier loop in `build_level_dict` (levellayout.py ≈ 2925) hits
   `if edge.node_a not in placed or edge.node_b not in placed: continue`
   and silently creates no door. The key in `room_3` survives per K1 —
   an orphan key.

The direction is benign (orphan key, never a key-less door — no
soft-lock), but the invariant R-K1 (`#keys == #locked doors` per colour,
spec 0061) is violated, `test_key_door_pairing` re-fails deterministically
via the persisted `.hypothesis/` example, and the dropped room's spilled
challenge award becomes a free award — the exact "secondary effect" spec
0061 set out to remove.

Spec 0061 D1 deliberately preserved this path ("unplaced endpoints keep
today's behaviour") because its 8-seed diagnosis contained no dropped
locked rooms; the case is real but rare: a detector sweep found
**0 / 720** affected builds (300 FS_LOCKED + 300 FS_ALL + 60
FS_CROWDED_LOCKED + 60 real level-13 sets).

Underneath sits an invariant tension: **K1 (keys are never lost) and
R-K1 (per-colour pairing) cannot both hold on a level that dropped a
locked room.** One must yield — and per the 0048/0061 philosophy the
answer is: such a level must not exist.

## Design

### D1 — the loud raise

Make the residual case loud, in `levellayout.py`'s barrier loop
(`build_level_dict`, the "Locked doors, gates, and water tiles from
edges" section, ≈ line 2924):

```python
for edge in graph.edges:
    if edge.node_a not in placed or edge.node_b not in placed:
        if edge.edge_type == EdgeType.LOCKED:
            raise LayoutError(
                f"LOCKED edge {edge.node_a}--{edge.node_b} "
                f"({edge.params['key_colour']}) has an unplaced endpoint "
                f"— door would be elided, key orphaned (BL-46)")
        continue
    ...
    conn = _find_connection_tile(pa, pb, orig_walls)
    if conn is None:
        if edge.edge_type == EdgeType.LOCKED:
            raise LayoutError(
                f"LOCKED edge {edge.node_a}--{edge.node_b} "
                f"({edge.params['key_colour']}) has no connection tile "
                f"(R-E4 should have raised) — BL-46 loud net")
        continue
```

`LayoutError` feeds the standard fresh-seed retry everywhere this
function is called (`_generate_act2_level`, `_build_super_grid` per-grid
builds, the tests' `_build_retry`); at < 0.2 % incidence the retry cost
is negligible.

Scope decisions:

- **GATED edges keep degrade-to-open**, both for unplaced endpoints and
  at global surviving-plate scope — plates can legitimately be lost
  (spec 0061 D2); an orphan plate is harmless. Out of scope here.
- **WATER edges unchanged** (tiles already collected by `derive_walls`).
- **BORDER-locked doors unchanged** — they are handled in
  `_build_super_grid` against global surviving keys (correct scope since
  spec 0056/0061).
- The earlier `puzzle_passable` edge loop (≈ 2744) shares the silent
  pattern but only derives a tile set; it stays as-is — a doomed build
  dies at the barrier loop anyway, and one authoritative raise site
  beats two redundant ones.
- An **uncarvable closet on a LOCKED edge** (R-T3 skip path) is also
  caught by the same check, deliberately: retry rather than orphan the
  key.

### D2 — every escaping LayoutError writes a diagnostic log entry

Today a `LayoutError` is silently absorbed by the fresh-seed retry —
the failure that triggered a retry is unrecoverable after the fact.
Every `LayoutError` that **escapes the top-level `build_level_dict`
call** (i.e. aborts one whole build attempt) is appended to a log file
before propagating, so retries leave a diagnostic trail:

```
== LayoutError 2026-07-12T14:33:07 ==
grid: grid_2 (3 of 5 built)
message: no strategy placed grid 'room_7'

grid_a @ (2, 1)   exits: ...
grid_1 @ (1, 1)   exits: ...
grid_2 @ (1, 0)   <-- FAILED: no strategy placed grid 'room_7'

<2D canvas of the grids built so far; at grid_2's super position a
 30×16 placeholder box of '!' with 'FAILED' centred>
```

Mechanics:

- **Log file**: `uglycraft-layout.log` in the working directory (same
  convention as `uglycraft.hsc`), plain text, append. Path in a module
  variable `levellayout.LAYOUT_LOG_PATH` so tests redirect it; entries
  are ≤ ~6 KB, the file may be deleted freely, no rotation.
- **What logs**: only failures of a whole build attempt. `_build_grid`'s
  per-strategy candidates (`except (LayoutError, ValueError): continue`)
  are routine iteration, not failures — the recursive per-grid
  `build_level_dict` calls pass an internal `_log=False`, so absorbed
  candidates never log. When no candidate works, the escaping
  `"no strategy placed grid"` raise logs exactly once.
- **Context attachment**: `_build_super_grid` wraps its grid-building
  loop; on `LayoutError` it attaches `failing_grid` (grid name),
  `rooms_so_far` (the completed grids' room dicts), and their super
  positions (from the corridors' `super_pos` — the stitch exits do not
  exist yet at this point, so positions are passed explicitly, never
  BFS-derived) to the exception and re-raises. The single-grid body
  attaches `failing_grid='main'` and no rooms (no "so far" exists —
  the room dict only assembles at the end of the build; the entry then
  carries grid name + message only, stated limitation).
- **Rendering**: a new public `leveldump.render_rooms(rooms, positions,
  failed=(name, msg))` — the dict-level renderer slice of BL-48(a):
  renders room dicts via `Room.from_data` (HARD, so all authored
  enemies show; no `World`, no `get_level`), places blocks at the given
  super positions on the 2D canvas, marks the failing grid's index line
  with `<-- FAILED: <msg>` and draws a `!`-bordered placeholder block
  with `FAILED` centred at its super position. `leveldump` is imported
  by `levellayout` only inside the logging helper (no import cycle:
  `leveldump`'s module-level imports are `cells`/`rooms`/`entities`/
  `constants`).
- The game/runtime is untouched: logging happens inside levellayout,
  headless-safe, and only on failures.

### Invariant reconciliation (kb/requirements.md)

- **R-K1** stands as written — after this fix it is actually guaranteed,
  with the new raise listed as the enforcement for the dropped-room case.
- **R-P3** ("Every node in the graph appears in the `placed` dict.
  Unplaced nodes are a bug") is contradicted by the legitimate packer
  drop + C7 spill path. Reword: nodes may be dropped by the packer with
  their content spilled (C7), **except** that no LOCKED edge may lose an
  endpoint — that raises (this spec).

### RNG / golden impact

No rng draws are added or removed; behaviour changes only for builds
that previously produced an orphan key (0/720 in the sweep), which now
retry with the next sub-seed. The Act 2 golden seeds build cleanly
today, so `act2_*` goldens (and everything else) stay **byte-identical**.

## Tests (red first)

In `tests/test_key_placement.py` (R-K1 section):

1. **Pinned regression**: `_build_retry(FS_ALL, 584)` must yield
   per-colour `#keys == #doors` (red today: cyan orphan key). Pinned
   explicitly so the regression does not depend on the local
   `.hypothesis/` database.
2. `test_key_door_pairing` itself goes green (the persisted seed-584
   example replays automatically on this machine).
3. **No retry storm**: reuse the sweep shape — the existing hypothesis
   sweeps (`test_keys_never_dropped`, 100 examples × 3 feature sets)
   already prove builds keep succeeding through `_build_retry`; no new
   test needed, but the full suite must stay green with no new
   `LayoutError` leaking out of retry loops.

New `tests/test_layout_log.py` (D2):

4. **Renderer unit**: `leveldump.render_rooms` over two hand-written
   room dicts at explicit super positions with `failed=('grid_2', msg)`
   — canvas blocks at the right offsets, the index line carries
   `<-- FAILED`, the placeholder block of `!` sits at the failing
   grid's position. Red today (function does not exist).
5. **Log integration**: with `levellayout.LAYOUT_LOG_PATH` pointed at a
   tmp file, the pinned seed-584 first attempt (post-D1 it raises)
   appends an entry containing the timestamp header, `grid: main`, and
   the BL-46 LOCKED-edge message. Red today (no log is written).
6. **No spam**: build a healthy multi-grid level (e.g. the level-13 set,
   seed 777) with the log redirected — per-strategy candidate failures
   inside `_build_grid` must leave the log **empty** if the build
   succeeds on the first attempt, or contain only whole-attempt
   entries otherwise.
7. Suite hygiene: an autouse conftest fixture redirects
   `LAYOUT_LOG_PATH` into `tmp_path` for the whole suite so tests never
   pollute the working directory.

## Done when:

- [x] Pinned seed-584 regression red before the fix, green after
      (c393fcc)
- [x] `test_key_door_pairing` green (including the persisted example)
      (c393fcc)
- [x] Escaping LayoutErrors append a log entry (grid name, message,
      annotated canvas of grids built so far); absorbed per-strategy
      candidates never log (c393fcc; multi-grid entry verified by a
      forced mid-loop failure on the level-13 set)
- [x] `leveldump.render_rooms` exists as the public dict-level renderer
      (BL-48(a) enabler) (c393fcc)
- [x] Full `poe test` exits 0 (727 passed); Act 2 goldens byte-identical
      (c393fcc)
- [x] `kb/requirements.md` R-K1 enforcement note + R-P3 rewording
      committed (32a2c7d)
- [x] BL-46 closed in `kb/backlog.md` (backlog agent); BL-48 updated
      (enabler landed) (fb5eeb1)

Note (implementation, c393fcc): the spec assumed the K1 hypothesis
sweeps built through `_build_retry`; `test_keys_never_dropped` /
`test_no_softlocked_doors` actually built retry-less, so their `_build`
helper now retries like `_generate_act2` — a retry-less build fails on
seeds production simply retries.
