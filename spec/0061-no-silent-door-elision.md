# 0061 — No silent barrier elision; prerequisites free to roam

## Status

- [ ] Red tests: per-colour `#keys == #doors` on generated Act 2 levels;
      pinned level-13 case (6 keys, 2 doors pre-fix); cross-grid
      interior-gate plates occur (distribution test)
- [ ] Interior locked doors created unconditionally for every LOCKED edge
      between placed nodes; missing-key condition raises `LayoutError`
      (loud safety net) instead of degrading the door
- [ ] `add_gated_room` places its plate in any reachable eligible room
      (any grid), like keys; interior-gate elision moves to global scope
      (post-stitch, surviving plates across all grids)
- [ ] Detector sweep validated pre-fix (orphan keys found), 0 violations
      post-fix
- [ ] Goldens re-recorded once with reviewed diffs (the gated-plate pool
      change shifts graph streams; restored doors shift walks)
- [ ] `poe test` exits 0
- [ ] KB updated (R-K1 in `kb/requirements.md`; spec-0030 coupling and
      builder sections in `kb/architecture.md`); backlog entry closed
- [ ] User play-test confirmation: every key found has a door to open;
      locked rooms read as challenges again; remote plates for interior
      gates appear and work across grid transitions

## Problem

Play-testing level 13 (spec 0058/0060 acceptance) surfaced 5 keys but
only 3 doors. Diagnosis over eight generated level-13s: **6 of 8 seeds
have more keys than locked doors** (worst: 6 keys, 2 doors), with no
locked room ever dropped by the packer.

Cause: the barrier↔prerequisite coupling (spec 0030) is evaluated with
the wrong scope for interior doors. In each grid's `build_level_dict`,
a LOCKED edge's door is created only if its colour is in
`placed_key_colours` — derived from `all_keys` **of that grid alone**.
But key placement is deliberately cross-grid: `add_locked_room` puts
the key in any already-reachable room, which since spec 0030 includes
rooms on earlier grids (R-V3 design note — hunting keys across grids is
intended). A door on grid B whose key sits on grid A therefore looks
key-less from grid B and silently degrades to an open passage; the key
remains as an orphan.

Spec 0060 amplified the frequency (more rooms per grid ⇒ more LOCKED
edges ⇒ more cross-grid keys), but the bug predates it.

Secondary effect, also observed in play: the elided door strips the
room's visible challenge while its spec-0058 **challenge award stays**,
so formerly-locked rooms read as ordinary rooms with free awards —
a large part of the "awards sprinkled everywhere" impression.

**Interior gates share the flawed pattern without the bug** — their
per-grid check is currently correct only because `add_gated_room`
restricts the plate to the gate's own grid (`_puzzle_candidates`
returns current-grid rooms only, auto-adding one if needed). That
restriction predates spec 0050: with the old local `_gate_open` state a
cross-grid gate could not work at runtime. Since 0050, gate state is a
global channel table persisting across grid transitions — border gates
already run with remote plates routinely. Daniel's review (2026-07-11):
fold the liberation in — interior-gate plates may roam like keys,
matching the R-V3 philosophy that prerequisite-hunting is part of the
challenge.

Not affected:

- **Border doors and border gates** — `_build_super_grid` checks
  `surviving_key_colours` / `surviving_gate_ids` across **all** grids
  after stitching; correct scope already, including the spec-0056
  `border_barriers` degradation records.

## Design

### The key/plate asymmetry that shapes the fix

- **Keys are never lost.** Every LOCKED edge's key is placed atomically
  at graph time; layout never drops it (spec 0030 spill; K1
  `keys_dict == keys_graph`, test-locked). A key-less door is
  impossible short of a regression ⇒ doors get a **loud** net.
- **Plates can be lost.** A puzzle room dropped by the packer takes its
  plate with it — plates are deliberately not spilled (a plate needs
  its solvable Sokoban context; the gate is elided instead, spec 0032
  C7). A plate-less gate is therefore a **legitimate** rare outcome ⇒
  gates keep degrade-to-open, but at **global** scope.

### D1 — interior locked doors: unconditional, loud

In `build_level_dict`'s edge loop:

- Create the locked door for every LOCKED edge whose two nodes are
  placed (unplaced endpoints keep today's behaviour: no passage is
  converted; C7 spills the room's content).
- Replace the silent degradation with a loud check: the door's colour
  must appear among the **whole graph's** keys (`node.keys` over all of
  `graph.nodes` — the per-grid subgraph is not enough). On failure
  raise `LayoutError` → fresh-seed retry — "should be impossible"
  becomes "checked" (spec 0048 philosophy), never a silently reshaped
  level.
- Threading: per-grid builds see only their subgraph, so
  `_build_super_grid` computes the full graph's key colours once and
  passes them into `build_level_dict` (new parameter; `None` = derive
  from the given graph, which serves the single-grid path and manually
  built graphs).

### D2 — interior-gate plates roam; elision goes global

- **Graph phase:** `add_gated_room` draws its puzzle room from all
  reachable eligible rooms across every grid (eligibility unchanged:
  non-corridor, non-closet, no existing blocks/plates), exactly as
  `add_locked_room` draws key rooms. The auto-add-a-room path remains
  only for the no-eligible-room-anywhere case (start of generation).
  The plate node still carries the puzzle; `_build_subgraph` already
  copies plates into the plate room's own grid, whose build solves the
  Sokoban puzzle locally — the solver never needed the gate (border
  gates prove this daily).
- **Layout phase:** per-grid builds create interior gates
  **unconditionally** for GATED edges between placed nodes; the
  per-grid `placed_gate_ids` check is removed. After all grids are
  built and stitched, `_build_super_grid` removes every gate entity
  (interior ones now included) whose `gate_id` is not in the global
  `surviving_gate_ids` — same pass, same semantics as border gates:
  degrade to open when the plate genuinely did not survive. The
  single-grid path keeps its local check, which is already global
  there.
- **Runtime:** no changes — channels are global and persist across
  grids (spec 0050 + errata).

### RNG / golden impact

D1 adds no draws. D2 changes `add_gated_room`'s pool ⇒ the graph
stream shifts for every gated level; restored doors also change walk
traces. Re-record the Act 2 goldens once (`UGLYCRAFT_REGOLD=1`) and
review; the spec-0054 cross-process determinism guard must stay green
(the new pool iterates `_reachable`, already an ordered dict).

### New invariant (kb/requirements.md)

**R-K1** Barrier↔prerequisite pairing: on every generated level, for
every colour, `#keys == #locked doors` (interior + border); every gate
(interior + border) has a surviving plate of its `gate_id` somewhere in
the level, and gates whose plate did not survive do not exist (their
passage is open). Orphan keys exist only transiently in play.

## Verification (tests red-first after spec confirmation)

1. **Pairing property** (`tests/test_key_placement.py`): generated
   levels over the real Act 2 feature sets and the crowded fixtures —
   per colour, `#keys == #locked_doors` (interior + border tiles). Red
   today (6/8 level-13 seeds violate).
2. **Pinned case**: level-13 feature set, build seed 7 via the standard
   retry helper — 6 keys, 2 doors pre-fix; equal counts post-fix.
3. **Loud net**: a graph whose LOCKED edge has no key of its colour
   anywhere (manually stripped, as in the spec-0056 degraded-border
   test) → `build_level_dict` raises `LayoutError`.
4. **Plates roam** (distribution): over generated multi-grid gated
   levels, at least one interior gate's plate sits on a different grid
   than the gate (red today — structurally impossible). Companion
   guard: every gate present in the dict has a surviving plate of its
   id, and every GATED edge between placed nodes whose plate survived
   has its gate present (no over- or under-elision).
5. **Sweep**: scratchpad detector counting per-colour key/door
   mismatches and plate-less gates across ≥ 100 levels — validated
   pre-fix (orphan keys found), 0 violations post-fix.
6. Goldens re-recorded once; full `poe test` green.

## Done when:

- [ ] Pairing property and pinned case green (red before the fix)
- [ ] Loud-net test green: missing key ⇒ `LayoutError`, never a silent
      open passage
- [ ] Plates-roam distribution test green (cross-grid interior-gate
      plates exist); no over- or under-elision of gates
- [ ] Sweep: 0 violations across ≥ 100 generated levels (orphan keys
      confirmed pre-fix)
- [ ] Goldens re-recorded once with reviewed diffs
- [ ] `poe test` exits 0
- [ ] R-K1 in `kb/requirements.md`; `kb/architecture.md` spec-0030
      coupling + builder sections updated; backlog entry closed
- [ ] Daniel confirms in play (level 13+): key and door counts match,
      locked rooms read as challenges with their award behind the
      door, and a remote plate opens its interior gate across a grid
      transition
