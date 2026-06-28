# Spec 0032 — Closets (and other nodes) silently dropped in multi-grid layout (BL-23)

## Status

- [ ] N1 — `_build_subgraph` includes each grid's closets (with their edges and
      items); no closet is dropped in a multi-grid level
- [ ] N2 — No node is silently dropped: a built level contains every node of its
      graph, or raises `LayoutError` to regenerate (defense-in-depth; also covers
      the rare non-closet R-P4 case)
- [ ] N3 — Regression tests: placed nodes == graph nodes across feature sets
      (single- and multi-grid); closets survive in multi-grid
- [ ] N4 — Tests pass (`poe test`)

## Investigation

A diagnostic sweep (40 seeds × 10 real Act 2 feature sets = 400 levels,
`scratchpad/diag_drops.py`) found **434 / 6617 nodes dropped (6.6%)**:

| dropped node kind | count |
|---|---|
| **CLOSET** | **432** |
| HALL | 2 |

298 of the dropped nodes held content (treasures / materials / keys / plates).
A focused check (`closet_count=2`, varying grid count, 40 seeds each):

| grids | closets survived | closets dropped |
|---|---|---|
| 1 | 42 | **0** |
| 2 | 0 | **80** |
| 4 | 0 | **80** |

**Root cause (the 432).** Closets are nodes with no direct corridor edge — they
attach to a *room* (`add_closet_room`, edge room→closet). The single-grid path
`layout_graph` detects them (`closet_rooms`) and places them via `_nest_closets`
(which always succeeds — corner notch, else `_place_closet_adjacent`), so
single-grid drops 0. But the multi-grid path `_build_super_grid._build_subgraph`
(`levellayout.py:2293-2311`) copies **only the corridor's direct neighbours**
into each per-grid subgraph:

```python
for name, edge in graph.neighbors(corridor):
    if edge.edge_type == EdgeType.BORDER:
        continue
    node = sub.add_node(name, n.size)   # rooms only
    ...
```

A closet is a neighbour of a *room*, not the corridor, so it is never added to any
subgraph → never laid out → silently absent from `placed`/`tile_owner`. Every
closet in a level with ≥ 2 grids is therefore dropped.

**Secondary (the 2).** Two HALLs dropped via the simple-strategy band cap: a
`_pack_band` zone caps `n = (band_w+1)//3` and never iterates `room_names[n:]`,
and skips rooms with `w<2`/`h<2` (R-P4). This is over-capacity / too-small-zone
and is rare (2 / 6617) but is a genuine silent-drop path distinct from closets.

## Resolution

### N1 — copy each grid's closets into its subgraph (fixes the 432)

In `_build_subgraph`, after adding the corridor's room neighbours, also pull in any
node reachable from those rooms via non-BORDER, non-corridor edges (the closets —
and any closet-of-closet chain), adding each with its edge and a full item copy
(`treasures`, `materials`, `keys`, `blocks`, `plates`, `enemies`, `has_flames`),
exactly as room neighbours are copied. Then `layout_graph`'s existing closet
detection + `_nest_closets` place them within that grid. No geometry changes —
this is graph-copy completeness only.

### N2 — make silent node drops impossible (defense-in-depth, covers the 2)

After layout, assert that every node assigned to a grid is present in `placed`; if
any is missing, raise `LayoutError` so `_generate_act2_level` regenerates rather
than shipping a level with vanished content. This converts the residual R-P4
band-cap/too-small drops into a retry.

**Caveat (must resolve before enabling N2 unconditionally):** if a grid is ever
assigned more rooms than any compatible strategy can hold, N2 would regenerate
forever. The simple strategies silently cap today precisely because selection
filters on *min zones*, not *max capacity*. So N2 must be paired with bounding
room counts to layout capacity — which is exactly **BL-25** (scale room count with
grid count). Options: (a) land BL-25 first, then enable N2 globally; or (b) scope
N2 to "no **content-bearing** node is dropped" (raise only when a dropped node has
items), which is safe now and still prevents all content loss. Recommend (b) for
this spec, with (a) as the eventual stronger guarantee.

### N3/N4 — regression tests

- For single- and multi-grid feature sets (incl. the real Act 2 sets and a
  closet-bearing multi-grid set), assert **every graph node appears in some room's
  `tile_owner`** (placed == graph) — or, under N2 option (b), at least every
  content-bearing node.
- Specifically assert closets survive at grid counts 1..N.

## Verification

Re-run `scratchpad/diag_drops.py`: expect dropped closets → 0 and total drops → 0
(option a) or content-bearing drops → 0 (option b). New pytest cases enforce it.

## Done when:

- [ ] N1 — Closets are copied into per-grid subgraphs and placed; the focused
      check shows 0 closets dropped at all grid counts.
- [ ] N2 — No node (option a) / no content-bearing node (option b) is silently
      dropped; a level that cannot place one regenerates via `LayoutError`.
- [ ] N3 — Regression tests assert placed == graph (closets included) across
      single- and multi-grid feature sets.
- [ ] N4 — `poe test` green.
