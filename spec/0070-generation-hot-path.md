# Spec 0070 — Speed up the generation hot path (test-suite speed, BL-47 follow-up)

## Status

- [ ] OPT-1: `validate_layout` bounding-box prune (skip room pairs whose
      floor-boxes, expanded by 1, cannot intersect)
- [ ] OPT-2: `_place_puzzle` inner-loop hoist + inline `get_zone`
- [ ] Full suite green, unchanged (byte-identical generation output)
- [ ] Generation wall time re-profiled and recorded

## Motivation

Follow-up to spec 0069 (BL-47). The test suite is **core-bound** on this
2-physical-core machine — xdist gives ~2.1× and no more, and memoizing builds
is useless (measured 1–3% duplicate `(fs, seed)` builds). The only remaining
lever is **less total CPU work**: make generation itself faster. Since the
heavy sweep tests are generation-bound, a faster generator lowers the whole
suite's total work and therefore its parallel wall.

`cProfile` over 150 representative builds (6 sweep feature sets × 25 seeds,
`scratchpad`-style harness) = 29.4 s, dominated by two functions:

| Function | self | cumulative | ncalls | note |
|---|---|---|---|---|
| `_place_puzzle` (levellayout 1968) | 5.36 s | **17.4 s (59%)** | 79 | backward Sokoban BFS |
| `_comp_map` (2017, nested) | 5.13 s | 7.18 s | **1,559,507** | already memoized — calls are cache **hits** |
| `get_zone` (2043, nested) | 1.22 s | 8.5 s | **1,550,380** | thin wrapper over `_comp_map` |
| `validate_layout` (1509) | 3.74 s | 6.38 s | 250 | O(rooms²) × full-grid scan |

Both wins are **behaviour-preserving** — they change *how fast* the same output
is produced, never the output. That makes verification simple: generation must
stay byte-identical, which the existing golden tests
(`test_golden_act1`/`test_golden_act2`), the cross-process determinism test
(`test_generation_determinism`, `tests/_gen_hash.py`), and the full property
suite already enforce. Any behavioural drift turns them red.

## OPT-1 — `validate_layout` bounding-box prune

`validate_layout` loops over **every unordered pair** of placed nodes and, for
each pair, (a) scans all of A's floor tiles for direct adjacency to B, and (b)
scans the **entire** interior grid (`MIN_C..MAX_C` × `MIN_R..MAX_R` = 28×14) to
count shared-boundary passages. For a crowded level (40–60 rooms) that is
~1000–1800 pairs × 392 tiles → the 4.1 M generator-expression calls in the
profile. The vast majority of pairs are rooms nowhere near each other.

**Prune (lossless).** A shared-boundary passage tile, or a direct floor
adjacency, can exist between A and B only where A's floor bounding box **expanded
by 1** intersects B's floor bounding box expanded by 1:

```
A occupies cols [a.col, a.col+a.w), rows [a.row, a.row+a.h)   (floor within bbox)
A passage/adjacency influence: cols [a.col-1, a.col+a.w], rows [a.row-1, a.row+a.h]
```

If A's expanded box and B's expanded box do not overlap, the pair has **zero**
adjacent floor tiles and **zero** shared-boundary passages — so it contributes
no error and can be skipped before the grid scan. Concretely, skip the pair when

```
a.col + a.w < b.col - 1  or  b.col + b.w < a.col - 1  or
a.row + a.h < b.row - 1  or  b.row + b.w? ...  (row analogue)
```

(exact inequalities to be written against `PlacedNode.col/row/w/h`; corridors and
L-shapes use their true `floor_tiles` bounding box, computed once per node).

**Subtlety — the "no edge but passages exist" branch.** The current code also
flags a pair that has passages but *no* graph edge. A pruned (far-apart) pair
has no passages by construction, so pruning cannot hide that error. Pairs that
*do* have an edge but are somehow far apart would still be scanned (their boxes
overlap iff a passage is geometrically possible; a missing passage on an edge
that requires one is still caught because the boxes of an edge's two rooms must
be adjacent). Prune only decides *whether to scan*, never the verdict.

Optionally also restrict the passage tile scan to the overlap rectangle instead
of the whole grid — same result, less work — but the pair-level prune is the
main win and is done first.

## OPT-2 — `_place_puzzle` inner-loop hoist + inline `get_zone`

Inside the backward Sokoban BFS (levellayout ~2084–2119), each expanded state
`(curr_block, curr_zone)` runs a 4-direction loop that calls:

- `get_zone(old_block, curr_block)` → `_comp_map(curr_block).get(old_block)`
- `get_zone(push_from, old_block)` → `_comp_map(old_block).get(push_from)`

`curr_block` is **constant across all four directions**, so `_comp_map(curr_block)`
is fetched 4× per node needlessly, and every lookup pays a `get_zone` +
`_comp_map` Python call frame (≈ 3 M frames total). Hoist and inline:

```python
cm_curr = _comp_map(curr_block)          # once per BFS node, before the 4-dir loop
for dc, dr in _CARDINAL:
    ...
    if cm_curr.get(old_block) != curr_zone:      # was get_zone(old_block, curr_block)
        continue
    new_zone = _comp_map(old_block).get(push_from)  # was get_zone(push_from, old_block)
    ...
```

`get_zone` is defined as exactly `_comp_map(block_pos).get(player_pos)`, so both
substitutions are identities. `_comp_map` stays memoized (`comp_cache`); this
only removes redundant re-fetches and wrapper frames. `anchor_zones(old_block)`
is unchanged. Keep `get_zone` if any other caller remains; otherwise remove it.

## Non-goals

- No algorithm/output change. If any golden or determinism hash moves, the
  change is wrong and is reverted — not re-recorded.
- No change to `_comp_map`'s BFS, the Sokoban acceptance rules (spec 0063
  anchoring, R-P11), or `validate_layout`'s verdicts.
- No geometry change (no zone-boundary maths) — the geometry rule's ASCII-diagram
  gate does not apply; these are call-graph optimizations over unchanged tile sets.

## Verification

1. `poe test` green — same pass count, no golden/determinism regression.
2. Re-run the cProfile harness; record before/after wall and the new
   `_place_puzzle` / `validate_layout` / `_comp_map` figures.
3. Spot-check: `tests/_gen_hash.py` canonical hash for a fixed seed identical
   before and after (proves byte-identical output).

## Done when:

- [ ] OPT-1 implemented; `validate_layout` no longer scans far-apart pairs. — commit ____
- [ ] OPT-2 implemented; `_place_puzzle` hoists `cm_curr`, inlines `get_zone`. — commit ____
- [ ] `poe test` green, identical pass count; goldens/determinism unchanged. — commit ____
- [ ] Before/after profile recorded (harness in scratchpad or KB). — commit ____
