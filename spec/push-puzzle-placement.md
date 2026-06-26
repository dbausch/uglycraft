# Push Puzzle Placement Redesign

## Status

- [ ] `_puzzle_candidates(plate, room_floor, passable, excluded)` — reverse BFS
- [ ] `_puzzle_solution_tiles(block, plate, candidates)` — shortest-path reconstruction
- [ ] `_place_puzzle(room_name, gate_id, placed, passable, excluded, rng)` — atomic placement
- [ ] `build_level_dict()` places puzzles atomically before other items
- [ ] `_place_items_in_room()` no longer places plates or blocks
- [ ] Pass-2 block placement loop removed
- [ ] Multi-puzzle exclusion: second puzzle cannot overlap first puzzle's solution tiles
- [ ] `validate_push_puzzles()` always passes (sanity check, never a corrective mechanism)

---

## Problem

The two-pass approach (plates placed in pass 1 among other items, blocks placed in a
separate pass 2 via a 1-push heuristic) is structurally wrong. Plates are chosen blindly
from whatever tiles happen to be free, then pass 2 reverse-engineers a block position from
that blind plate. When no 1-push candidate exists the code falls back to a non-dead square,
which is necessary but not sufficient for solvability.

---

## What Is Strictly Required

A push puzzle needs exactly one input: the **passable tile set** at puzzle-solving time:

```
passable = all_interior_tiles − walls − gate_tiles − lock_tiles
```

Everything else (treasures, materials, enemies, keys) is irrelevant to block movement.
This set is fully available immediately after `derive_walls()`.

---

## Algorithm

### Once before all puzzles

After `derive_walls()`:
- Collect gate tile and lock tile positions via `_find_connection_tile` on graph edges.
- Compute `puzzle_passable = all_interior − walls − gate_tiles − lock_tiles`.
- Initialise `excluded = set()`.

### For each puzzle (gate_id, room_name)

**B1 — `_puzzle_candidates(plate, room_floor, passable, excluded)`**

Reverse BFS from `plate` through `passable`, restricted to `room_floor`, skipping
`excluded`. Returns dict `{pos: (parent_pos, push_dir)}`.

For each step from a frontier tile T, look for tile S = T − D such that:
- S ∈ room_floor, S ∈ passable, S ∉ excluded, S not yet in valid or invalid
- Player position R = T − 2D ∈ passable → S is valid (add to dict + queue)
- R ∉ passable → S is invalid (mark and skip future)

Seeding: same rule applied from plate to each adjacent tile.

**B2 — choose (plate, block) pair**

Collect all `(P, B)` pairs where `P ∈ room_floor ∩ passable − excluded` and
`B ∈ candidates(P)`. Pick a random pair.

**B3 — `_puzzle_solution_tiles(block, plate, candidates)`**

Trace back from `block` through `candidates` parent pointers to `plate`. For each push
step (block_from → block_to with push direction D, player at block_from − D), collect:

```
solution_tiles = {block_from, player_at} for each push step
solution_tiles.add(plate)   # block's final resting position
```

**B4 — update state**

```
excluded.update(solution_tiles)
puzzle_passable -= {plate}   # next puzzle: plate is occupied (block resting on it)
all_plates.append((*plate, gate_id))
all_blocks.append(block)
global_used.update({plate, block})
```

---

## Files Changed

| File | Change |
|------|--------|
| `levellayout.py` | Add `_puzzle_candidates`, `_puzzle_solution_tiles`, `_place_puzzle`; restructure `build_level_dict` to call `_place_puzzle` first; remove pass-2 block loop; remove blocks/plates from `_place_items_in_room` |

---

## Done When

- [ ] `poe test` passes 46/46 across multiple runs and multiple `PYTHONHASHSEED` values.
- [ ] Block is never at `plate ± D` exclusively; blocks appear at varied distances.
- [ ] A level with two gated rooms places each puzzle such that neither interferes with the other's solution path (manual check via `poe run --level 13`).
