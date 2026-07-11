# 0061 — Interior locked doors are never silently elided (key↔door 1:1)

## Status

- [ ] Red tests: per-colour `#keys == #doors` on generated Act 2 levels;
      pinned level-13 case (6 keys, 2 doors pre-fix)
- [ ] Interior locked doors created unconditionally for every LOCKED edge
      between placed nodes; missing-key condition raises `LayoutError`
      (loud safety net) instead of degrading the door
- [ ] Detector sweep validated pre-fix (orphan keys found), 0 violations
      post-fix
- [ ] Goldens re-checked; re-recorded once with reviewed diffs if the
      restored doors shift them
- [ ] `poe test` exits 0
- [ ] KB updated (R-K1 in `kb/requirements.md`; spec-0030 coupling section
      in `kb/architecture.md`); backlog entry closed
- [ ] User play-test confirmation: every key found has a door to open;
      locked rooms read as challenges again

## Problem

Play-testing level 13 (spec 0058/0060 acceptance) surfaced 5 keys but
only 3 doors. Diagnosis over eight generated level-13s: **6 of 8 seeds
have more keys than locked doors** (worst: 6 keys, 2 doors), with no
locked room ever dropped by the packer.

Cause: the barrier↔prerequisite coupling (spec 0030) is evaluated with
the wrong scope for interior doors. In each grid's `build_level_dict`,
a LOCKED edge's door is created only if its colour is in
`placed_key_colours` — derived from `all_keys` **of that grid alone**
(levellayout.py, "Gate/lock prerequisites that actually SURVIVED
placement"). But key placement is deliberately cross-grid:
`add_locked_room` puts the key in any already-reachable room, which
since spec 0030 includes rooms on earlier grids (R-V3 design note —
hunting keys across grids is intended). A door on grid B whose key sits
on grid A therefore looks key-less from grid B and silently degrades to
an open passage; the key remains as an orphan.

Spec 0060 amplified the frequency (more rooms per grid ⇒ more LOCKED
edges ⇒ more cross-grid keys), but the bug predates it.

Secondary effect, also observed in play: the elided door strips the
room's visible challenge while its spec-0058 **challenge award stays**,
so formerly-locked rooms read as ordinary rooms with free awards —
a large part of the "awards sprinkled everywhere" impression.

Not affected:

- **Border locked doors** — `_build_super_grid` checks
  `surviving_key_colours` across **all** grids after stitching; correct
  scope already.
- **Gates** — plates are guaranteed same-grid by construction
  (`_puzzle_candidates` returns current-grid rooms only), so the
  per-grid check is the right scope there.

## Design

The elision was a safety net against keys lost during layout. Since
spec 0030's spill, **keys are never lost** — invariant K1
(`keys_dict == keys_graph`) is test-locked, and every LOCKED edge's key
is placed atomically at graph time by `add_locked_room` /
`start_next_grid`. A key-less locked door is therefore impossible short
of a regression elsewhere, and the net's only remaining behaviour is
the misfire above.

Change, in `build_level_dict`'s edge loop (levellayout.py):

- Create the locked door **unconditionally** for every LOCKED edge whose
  two nodes are placed (unplaced endpoints keep today's behaviour: no
  passage is converted; the C7 spill moves the room's content).
- Replace the silent degradation with a **loud** check: the door's
  colour must appear among the **whole graph's** keys (`node.keys` over
  all of `graph.nodes` — the per-grid subgraph is not enough). If it
  fails, raise `LayoutError` → fresh-seed retry — "should be
  impossible" becomes "checked" (spec 0048 philosophy), never a
  silently reshaped level.

Threading: per-grid builds see only their subgraph, so the full graph's
key colours are computed once in `_build_super_grid` (and trivially in
the single-grid path) and passed to `build_level_dict` as
`global_key_colours`; `None` (manually built graphs calling
`build_level_dict` directly) means "derive from the given graph".

`placed_key_colours` (per-grid) keeps one remaining use — nothing: it
is removed; the border-door path in `_build_super_grid` keeps its own
`surviving_key_colours` (all grids, post-stitch), unchanged, including
the spec-0056 `border_barriers` degradation records for genuinely
missing border prerequisites (that machinery and its tests stay).

**No rng draws are added or removed** — doors are dict appends. Levels
where doors were previously elided regain them (blocked tiles change →
the level-13 golden walk may shift; re-record once and review: the only
acceptable difference is locked doors appearing where the graph always
demanded them).

### New invariant (kb/requirements.md)

**R-K1** Key↔door pairing: on every generated level, for every colour,
the number of keys equals the number of locked doors (interior +
border) of that colour, and every locked door has a reachable key
(K2/K3 as before). Orphan keys exist only transiently in play (after
the player opens a door with one of several same-colour keys).

## Verification (tests red-first after spec confirmation)

1. **Pairing property** (new, `tests/test_key_placement.py`): generated
   levels over the real Act 2 feature sets and the crowded fixtures —
   per colour, `#keys == #locked_doors` (interior + border tiles).
   Red today (6/8 level-13 seeds violate).
2. **Pinned case**: level-13 feature set, build seed 7 via the standard
   retry helper — 6 keys, 2 doors pre-fix; equal counts post-fix.
3. **Loud net**: unit test constructing a graph whose LOCKED edge has no
   key of its colour anywhere (manually stripped, as in the spec-0056
   degraded-border test) → `build_level_dict` raises `LayoutError`
   (no silent open passage).
4. **Sweep**: small detector (scratchpad) counting per-colour key/door
   mismatches across ≥ 100 levels — validated pre-fix (violations
   found), 0 post-fix.
5. Goldens per above; full `poe test` green.

## Done when:

- [ ] Pairing property and pinned case green (red before the fix)
- [ ] Loud-net test green: missing key ⇒ `LayoutError`, never a silent
      open passage
- [ ] Sweep: 0 orphan keys across ≥ 100 generated levels (violations
      confirmed pre-fix)
- [ ] Goldens byte-identical or re-recorded once with reviewed diffs
- [ ] `poe test` exits 0
- [ ] R-K1 in `kb/requirements.md`; `kb/architecture.md` spec-0030
      coupling section updated; backlog entry closed
- [ ] Daniel confirms in play (level 13+): key and door counts match,
      locked rooms read as challenges with their award behind the door
