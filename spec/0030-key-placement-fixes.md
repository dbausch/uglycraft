# Spec 0030 — Key placement fixes

## Status

- [ ] K1 — Keys are never dropped during layout (spill to corridor, like spec
      0029 planks); placed **first** — after flames and push puzzles, before
      planks and all other items; `keys_dict == keys_graph` for every generated
      level
- [ ] K2 — A locked door / gate is placed **iff** its key / plate+block actually
      survived layout; otherwise the passage degrades to open. One guarded
      placement path shared by interior **and** border barriers; stitching only
      resolves the tile position, it never unconditionally invents a barrier
- [ ] K3 — Document that graph-side key reachability is sound (no fix needed);
      add a regression test that every locked door has a surviving, reachable key
- [ ] K4 — Property tests covering K1–K3 (no soft-locks across many seeds)

## Investigation summary (answers to the two questions)

**Q1 — Is key placement affected by dropping? YES, and it soft-locks the level.**
`_place_items_in_room` (`levellayout.py:1882-1886`) places keys with the same
`if p:` guard that dropped planks; when the key's room is full the key is silently
lost. Unlike planks, the consequence is a hard soft-lock: the locked-door
placement decides whether to place a door from `placed_key_colours`
(`levellayout.py:2165-2170`), which is computed from the **graph** `node.keys`
for placed nodes — **not** from surviving placed keys. So the door is placed even
though its key is gone, and every locked door uses a **distinct** colour
(`_next_color()`), so no other key opens it → permanently shut.

Border locked doors are worse: `_build_super_grid` appends them
**unconditionally** during stitching (`levellayout.py:2442-2453`) with no
key-survival check and no open-passage fallback at all.

**Q2 — Is key placement restricted to the reachable graph partition? YES (sound).**
`add_locked_room` (`levelgraph.py:533-544`) places the key in
`_room_candidates()` (reachable non-corridor rooms) and adds the locked room to
`_reachable` only *after*, so the key is never behind its own door. The
incremental construction makes every barrier's key live in an older room →
dependencies form a DAG (no key-behind-its-own-door cycle). `start_next_grid`
(`levelgraph.py:612-615`) does the same for BORDER locked edges, picking the key
room from the global `_reachable` set before the new corridor joins it.
`validate_playability` (`levelgraph.py:175-325`) then enforces full reachability,
opening LOCKED/BORDER edges only when a matching key is already reachable. Layout
connectivity mirrors graph reachability, so a reachable key in the graph is a
reachable key in the level. **No code change needed for Q2** (see K3).
Known caveat: BL-03 — in a branching super-grid a border key may land on a
different (still reachable) grid than expected; solvable but potentially
confusing. Out of scope here.

## Evidence (headless generation sweep)

Script: `scratchpad/repro_keys.py`. 135 key-bearing Act 2 levels (15 seeds × 10):

| Property | Result | Meaning |
|---|---|---|
| keys dropped in layout (`keys_dict < keys_graph`) | **58/135 (43%)**, 88 keys lost | keys silently dropped |
| **soft-lock** (a locked door with no key of its colour anywhere) | **58/135 (43%)**, 82 doors | level unsolvable for full completion |

Example (`seed0 idx5`): graph has 5 keys, only 3 survive → doors `purple` and
`cyan` are placed with no key on the floor.

## The defects and resolutions

### K1 — Keys dropped during layout (43% of key levels)

Same root cause as spec 0029 W1: `_place_items_in_room` drops collectibles when
the room is full, and keys are placed after treasures.

**Resolution:** keys are covered by spec 0029's **spill-to-corridor** mechanism —
when a key's room is full it spills to a free corridor tile (the corridor is the
reachability hub, so the key stays reachable), and `LayoutError` only if the
corridor is also full. Keys lead the collectible placement order — placed
**first**, after flames and push puzzles and **before** planks, treasures, and
other materials — so a key always wins a tile in its own room when possible. The
full canonical order is: **keys → planks → treasures (award items) → other
materials** (this supersedes BL-15's earlier "keys right after planks"). Target:
`keys_dict == keys_graph` always.

**Depends on spec 0029 W1 landing** (the spill machinery).

### K2 — Door/gate placed without its key; border barriers invented at stitch time

Two coupling bugs let a barrier exist without its prerequisite:

1. Interior: `placed_key_colours` / `placed_gate_ids` are derived from the
   **graph** (`node.keys` / `node.plates`) for placed nodes, not from the keys /
   plates+blocks that actually survived placement. A key dropped from a *placed*
   node still appears in `placed_key_colours`, so the door is placed (`2182-2191`)
   with no key. (When the key's whole *node* is unplaced the existing fallback
   already degrades to an open passage — that path is fine; only the
   placed-node-but-dropped-key path soft-locks.)
2. Border: stitching appends locked doors / gates **unconditionally**
   (`2442-2453`) — no guard, no fallback.

**Resolution — one guarded placement path; the barrier exists iff its
prerequisite is on the floor:**

- Derive door/gate placement from the **surviving** placements — `all_keys` for
  locked doors, `all_plates` + `all_blocks` for gates — not from the graph nodes.
  If the prerequisite did not survive, **degrade the passage to open** (the
  existing interior intent, now applied consistently).
- Apply the **same guarded routine to border barriers**: `_build_super_grid`
  computes only the stitch *position*, then hands the position-resolved BORDER
  edge to the shared placement logic, which places a door/gate only if its key /
  plate+block survived and otherwise leaves the (already-punched) border passage
  open. Stitching no longer invents barriers — addressing the "mutate after
  validation" danger (the BL-13 theme).

Note: the barrier *decision*, key colour, and key placement are already in the
graph (a `BORDER` edge's params) and validated by `validate_playability`. Only
the entity's *coordinate* is necessarily stitch-time (it depends on corridor
floor overlap). K2 keeps the decision in the graph and routes the coordinate
through the validated, prerequisite-aware path — it does not move geometry
earlier.

With K1 ensuring keys never drop, K2's degrade-to-open is a should-never-fire
safety net; together they make a soft-lock structurally impossible.

### K3 — Graph-side reachability is sound (no fix; add regression test)

No code change (see Q2). Add a regression test asserting the invariant so it
cannot silently regress: for every generated level, each locked door (interior
and border) has at least one surviving key of its colour, reachable from the
player start.

## Verification (K4)

Add pytest property tests that, across many seeds and all Act 2 feature sets,
assert for every generated level:

1. `keys_dict == keys_graph` — no key dropped (K1).
2. Every locked door (interior + border) has a surviving key of its colour
   somewhere in the level; every gate has a surviving plate **and** block (K2).
3. No locked door / gate is left with an absent prerequisite (no soft-lock); any
   barrier whose prerequisite is missing is an open passage instead (K2).
4. Each barrier's key/plate is reachable from the start without first crossing
   that barrier (K3).

## Done when:

- [ ] K1 — `keys_dict == keys_graph` for every generated level; keys spill to the
      corridor rather than dropping; keys placed first — before planks, treasures,
      and other materials (after flames and push puzzles).
- [ ] K2 — Locked doors and gates (interior and border) are placed only when
      their key / plate+block survived; otherwise the passage is open; border
      barriers go through the same guarded path as interior ones; stitching only
      resolves position. No soft-locks.
- [ ] K3 — Regression test confirms every locked door has a surviving, reachable
      key; graph-side reachability documented as sound.
- [ ] K4 — Property tests for K1–K3 pass (`poe test`).
