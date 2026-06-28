# Spec 0035 — Push plates not adjacent to a room entrance (BL-19)

## Status

- [ ] P1 — A push-puzzle pressure plate is never placed **on** a room's entry
      tile, nor on a tile **cardinally adjacent** to it. The entry tile is found
      the same way the flame-jet code finds it: via `_find_connection_tile`
      between the room and each connected neighbour, then the room-floor tile
      cardinally adjacent to that connection wall tile
- [ ] P2 — The exclusion is a **soft** constraint inside `_place_puzzle`: if no
      solvable `(plate, block)` pair exists once the entry neighbourhood is
      removed from the plate candidate set, the room falls back to the
      unrestricted candidate set, so solvability is never reduced below today's
      guarantee (no new `ValueError`/regenerate failures introduced)
- [ ] P3 — Property test across many seeds × all Act 2 feature sets: no placed
      pressure plate is on or cardinally adjacent to its room's entry tile, and
      every affected level still passes `validate_push_puzzles`

## The defect

Push-puzzle placement chooses the pressure plate from the room's whole floor with
no awareness of where the player enters the room.

`_place_puzzle` (`levellayout.py:1664`) iterates plate candidates over the entire
room floor, skipping only tiles that are non-passable or already reserved:

```python
room_floor = placed[room_name].floor_tiles          # 1685
...
for P in sorted(room_floor):                         # 1729
    if P not in effective_pass or P in excluded:     # 1730  ← only these guards
        continue
    # ... backward Sokoban BFS from P ...
```

The caller (`build_level_dict`, `levellayout.py:2120-2132`) builds `excluded`
solely from prior puzzles' solution tiles:

```python
excluded = set()
prior_puzzles = []
for name, node in graph.nodes.items():
    if name not in placed or not node.plates:
        continue
    for (gate_id,) in node.plates:
        plate, block, sol = _place_puzzle(
            name, gate_id, placed, puzzle_passable, excluded, rng,
            prior_puzzles=prior_puzzles)
        ...
        excluded.update(sol)                          # 2130 — prior solutions only
```

Nothing keeps the plate away from the room's entrance. The **entry tile** is the
room-floor tile the player first steps onto when entering through the corridor
(or another room) — the floor tile cardinally adjacent to the converted
shared-boundary wall tile. Because `sorted(room_floor)` includes that tile and
its neighbours, the plate can land directly on it or one step away. The player
then walks in and is immediately standing on (or beside) the plate, which:

- trivialises the puzzle (no traversal needed to reach the goal), and
- cramps the push geometry — there is little room between the entrance and the
  plate for the block to be manoeuvred, so the intended Sokoban challenge
  collapses.

The flame-jet subsystem already solves the symmetric problem (R-F3: a jet must
not block the entry row/column). It computes the entry tile like this
(`levellayout.py:2026-2040`):

```python
entry_tile = None
for nb_name, _ in graph.neighbors(name):
    if nb_name not in placed:
        continue
    conn = _find_connection_tile(placed[name], placed[nb_name], walls)
    if conn:
        for dc2, dr2 in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            adj = (conn[0] + dc2, conn[1] + dr2)
            if adj in placed[name].floor_tiles:
                entry_tile = adj
                break
    if entry_tile:
        break
```

`_find_connection_tile(pa, pb, walls)` (`levellayout.py:1259`) returns the centre
shared-boundary wall tile between two rooms (the tile that becomes the passage).
The plate placement should reuse exactly this entry-tile derivation.

## Resolution

Exclude the room's entry-tile neighbourhood from the **plate candidate set** of
`_place_puzzle`, mirroring the flame-jet entry detection.

### 1. Compute the entry neighbourhood per puzzle room

In `build_level_dict`, just before the puzzle loop (`levellayout.py:2120`), for
each room `name` that has plates, derive the set of entry tiles and their cardinal
neighbours:

- For **every** placed neighbour `nb` of `name` (not just the first — a room may
  have more than one connection), call `_find_connection_tile(placed[name],
  placed[nb], orig_walls)`. Use **`orig_walls`** (the full reinforced-wall set
  built at `levellayout.py:2069`, already available at the puzzle loop), not the
  post-`derive_walls` `walls`. `derive_walls` *pops* the converted passage tile
  out of `walls` for OPEN/LOCKED/GATED/WATER edges (`levellayout.py:1211, 1224,
  1230`), so on a single-tile shared boundary `_find_connection_tile(..., walls)`
  would miss the real passage; the gate/lock/door placement already uses
  `orig_walls` for this reason (`levellayout.py:2093-2101, 2211`). (The flame
  block passes `walls` — the backlog's named "model" — but `orig_walls` is the
  reliable variant and the one to use here.)
- For each connection tile `conn`, the entry tile(s) are the room-floor tiles
  cardinally adjacent to `conn`: `{(conn[0]+dc, conn[1]+dr) for dc,dr in
  CARDINAL} ∩ placed[name].floor_tiles`.
- The **plate-avoid set** for the room is the union, over every entry tile `e`,
  of `{e}` itself plus its four cardinal neighbours that lie in the room floor:
  `{e} ∪ ({(e[0]+dc, e[1]+dr)} ∩ room_floor)`. (Off-floor neighbours are walls
  and are not plate candidates anyway, so intersecting with `room_floor` is just
  tidiness.)

The entry tile itself is **not** currently excluded by any existing mechanism, so
it must be included in this avoid set (the plate could land exactly on the
entrance today).

### 2. Apply the exclusion to the plate candidate loop only

Pass the room's avoid set into `_place_puzzle` as a new argument (e.g.
`plate_avoid`, default empty `frozenset()`). Restrict **only the plate selection**:

```python
for P in sorted(room_floor):
    if P not in effective_pass or P in excluded or P in plate_avoid:
        continue
```

Do **not** add `plate_avoid` to the existing `excluded` set: `excluded` is also
consulted for **block** positions and solution tiles in the backward BFS
(`old_block in excluded`, `levellayout.py:1761`). Keeping the avoid set on the
*plate* only means the block and the solution path may still legitimately pass
through the entrance area — only the goal (plate) is moved away from the door. The
constraint is purely about where the plate lands.

### 3. Keep solvability — soft fallback (interaction with the Sokoban solver)

`_place_puzzle` raises `ValueError` when no solvable pair exists
(`levellayout.py:1799-1801`), and `validate_push_puzzles` failure raises
`ValueError` (`levellayout.py:2266`). Crucially, `_generate_act2_level`
(`levels.py:367-374`) only catches **`LayoutError`**, not `ValueError` — so a
puzzle that becomes unsolvable does **not** trigger a fresh-seed retry; it
propagates and crashes. The exclusion therefore must never turn a solvable room
into an unsolvable one.

Make the plate exclusion a **soft preference** inside `_place_puzzle`:

1. Build `pairs` as today, but skipping plate candidates in `plate_avoid`.
2. If `pairs` is empty **and** `plate_avoid` was non-empty, rebuild `pairs`
   ignoring `plate_avoid` (the original unrestricted behaviour).
3. Only if `pairs` is still empty does `_place_puzzle` raise `ValueError` — i.e.
   exactly the same failure condition as today.

This guarantees the change can only *narrow* plate choice when a solvable
non-entrance plate exists, and otherwise degrades gracefully to the current
behaviour. No new failure modes, and the downstream `validate_push_puzzles`
re-check (`levellayout.py:2264-2266`) is unaffected because every returned pair is
still a fully solved Sokoban configuration.

(Rooms small enough that *every* solvable plate is adjacent to the entrance — e.g.
a 2×2 puzzle room — fall back and keep their plate where it is. This is rare and
acceptable; the alternative would be to drop the puzzle, which is worse.)

## Verification

Level-generator logic test (pytest, suite under `tests/`, run with `poe test`).
Add to a new `tests/test_plate_placement.py` (or extend
`tests/test_placement_rules.py`, which already documents R-F3 entry-tile rules and
imports `build_level_dict` + the conftest feature-set fixtures).

For seeds across a wide range, and for each gate-bearing feature set
(`FS_GATED`, `FS_ALL` from `tests/conftest.py`):

1. Generate the graph and `level = build_level_dict(graph, rng=...)`.
2. For every room dict in `level['rooms']`, for every plate in the room's plate
   list:
   - Recompute the room's entry tiles independently from the placed nodes /
     connection tiles (the same `_find_connection_tile` over the full wall set +
     cardinal-adjacent floor logic), and assert **no plate** equals an entry tile
     or is cardinally adjacent to one.
3. Assert `validate_push_puzzles(room, tile_owner)` returns `[]` for every
   generated level (affected levels remain solvable) — reusing the existing
   solvability harness in `tests/test_act2_solvability.py` / `tests/test_sokoban.py`.

Use `hypothesis` (`@given(st.integers(...))`, `@settings(max_examples=...)`) as
the surrounding tests do, with a deadline generous enough for multi-grid
generation.

## Done when:

- [ ] P1 — No push-puzzle plate is placed on, or cardinally adjacent to, its
      room's entry tile; entry tile derived via `_find_connection_tile` exactly
      as the flame-jet code does. —
- [ ] P2 — The exclusion is soft: rooms with no non-entrance solvable plate fall
      back to the unrestricted candidate set; no new generation failures and
      `validate_push_puzzles` still passes for every level. —
- [ ] P3 — Property test across many seeds × all gate-bearing Act 2 feature sets
      asserts the no-plate-at-entrance invariant and per-level solvability
      (`poe test`). —
