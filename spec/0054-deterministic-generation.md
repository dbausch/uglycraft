# 0054 — Deterministic level generation across processes (BL-40)

## Status

- [ ] `LevelGraphBuilder._reachable` iterates in insertion (reachability)
      order — no str-set iteration feeds an rng pool anywhere in generation
- [ ] Dead `_assign_items` (same buggy pattern, no callers) deleted
- [ ] Subprocess determinism test: level hashes identical across
      `PYTHONHASHSEED` values (red today for level 13)
- [ ] Golden `act2_L13_walk` re-recorded once; stable across processes after
- [ ] Full suite green

## Problem

BL-40: the same game seed produces different Act 2 level content in different
Python processes. Canonical-content sha256 of `get_level(13)` under
`set_game_seed(777)` differs across `PYTHONHASHSEED=0..3` (4 distinct
hashes); level 11 is stable (its feature set avoids the affected code paths).
Verified pre-existing before spec 0053 (stash-diff on ffdbf12). Consequences:

- `--level N` debugging and any cross-machine seed sharing are not
  reproducible.
- The golden `act2_L13_walk` passes/fails depending on the process hash
  seed — the suite is flaky.

## Root cause

`PYTHONHASHSEED` salts the hashes of **str** (and bytes) only — ints and
tuples of ints hash identically in every process. So iteration order over a
`set`/`frozenset` of *strings* varies per process, while sets of tile tuples
are process-stable. Wherever a str-set's iteration order feeds an
`rng.choice` pool, the same rng draw selects a different element per process.

Audit result — every live occurrence is in `LevelGraphBuilder`
(levelgraph.py), all iterating `self._reachable` (a `set[str]` of node
names) or a derived str-set:

| Site | Effect |
|---|---|
| `_room_candidates` (:510) — `[n for n in self._reachable …]` | key room (`add_locked_room`), closet parent (`add_closet_room`), gated-room fallback |
| `_pick` fallback (:536) — `list(self._reachable)` | any pick with empty candidates |
| `_current_grid_rooms` (:515, set comprehension) → `_puzzle_candidates` (:531) | plate+block room (`add_gated_room`, `start_next_grid`) |
| `add_water_room` (:610) — `dry = [r for r in self._reachable …]` | planks rooms |
| `start_next_grid` (:644) — `self._pick(list(self._reachable))` | border key room |

Also: module-level `_assign_items` (levelgraph.py:722) contains the same
pattern (`rng.choice(_freely_reachable())` over `list(set)`), but has **no
callers** — dead since the LevelGraphBuilder refactor.

Audited clean (no fix needed): content distribution (`add_treasures` /
`add_materials` / `add_enemies` / `add_flames`) iterates `graph.nodes`
dicts — insertion-ordered; `validate_playability` uses sets for membership
only (result order-free); `levellayout.py` str-set usages
(`required_exits`, `occupied_sides`, strategy `_COVERS_*`) are
membership-only, and its tile sets are int tuples (unsalted).

## Fix

1. **`self._reachable`: `set` → dict-as-ordered-set** (`{name: None}`).
   Iteration becomes insertion order — the order rooms became reachable —
   which is deterministic across processes; membership stays O(1). The
   `.add(name)` call sites become item assignments. This makes sites
   1, 2, 4, 5 of the table deterministic without touching their logic.
2. **`_current_grid_rooms`: return a list** built from
   `graph.neighbors(...)` (edge insertion order) instead of a set
   comprehension — fixes site 3. Callers only iterate/filter it.
3. `_water_rooms` stays a set: membership tests only.
4. **Delete dead `_assign_items`.**

The number and order of rng draws is unchanged — only the *ordering of the
pools* the draws index into. Under a fixed process this changes generated
content once (goldens shift); across processes the content becomes
invariant.

No geometric algorithm changes (ordering only) — geometry rule not
triggered.

## Golden-trace impact

`act2_L13_walk` must be re-recorded once (`UGLYCRAFT_REGOLD=1`); it then
stops flaking. `act2_L11_walk` is expected byte-identical — level 11 was
hash-invariant pre-fix (no affected pool executes on its path at seed 777) —
re-record only if the suite proves otherwise, and note why.

## Tests (red first)

New `tests/test_generation_determinism.py` plus a non-collected probe
`tests/_gen_hash.py` (runnable as `python -m tests._gen_hash <level> <seed>`,
prints a canonical-content sha256 of `levels.get_level(level)` — dicts and
collections recursively sorted so only real content differences count):

1. **Cross-hash-seed determinism** — run the probe in subprocesses with
   `PYTHONHASHSEED` 0, 1, 2 for level 13 / seed 777 (multi-grid, the known
   failing case) and level 11 / seed 777 (single-grid control); assert the
   three hashes per level are identical. Red today for level 13 (4 distinct
   hashes observed across seeds 0–3); level 11 already passes.
2. After the fix: verify the manual sweep (probe under `PYTHONHASHSEED=0..3`
   for levels 11 and 13) yields one hash per level, re-record
   `act2_L13_walk`, and run the full suite green — including
   `tests/test_entrance.py` (structural properties, unaffected) and 3×
   repeated `test_generated_level_13` in fresh processes to confirm the
   flake is gone.

## Done when:

- [ ] Subprocess determinism test red before the fix (level 13), green after
- [ ] Probe hashes identical across `PYTHONHASHSEED=0..3` for levels 11 & 13
- [ ] `_assign_items` deleted; no `list(<str-set>)` feeds an rng pool in
      levelgraph.py / levellayout.py
- [ ] `act2_L13_walk` re-recorded; `test_generated_level_13` passes 3×
      in fresh processes
- [ ] `poe test` exits 0
- [ ] BL-40 closed in `kb/backlog.md`; kb updated (`kb/findings.md` BL-40
      entry marked fixed; `kb/architecture.md` determinism note)
