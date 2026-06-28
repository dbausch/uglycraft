# 0026 — Replace `_spanning_tree` with randomized Prim's algorithm

## Status

- [x] `_spanning_tree` replaced; `len(result) == n` always holds
- [x] All other spanning-tree invariants still pass (`poe test` green, 336 tests)
- [x] `branch_prob` retired from `_spanning_tree` and all call sites
- [x] Affected tests updated

---

## Problem

`_spanning_tree(n, branch_prob, rng)` in `levelgraph.py` is a biased random walk
that can trap itself. With `branch_prob=0.0`, only the current tip is extended.
The tip can be completely surrounded by previously-placed nodes, emptying the
frontier and causing early termination.

Confirmed failing case: `_spanning_tree(9, 0.0, Random(1007084))` returns 8 nodes
instead of 9. The failure is recorded in the Hypothesis database and replays on
every test run.

---

## Note on algorithm choice

Wilson's algorithm is designed for *finite* graphs. On an infinite 2D grid the
loop-erased random walk has unbounded expected return time (the grid is
null-recurrent): `n=2 seed=2` took 2 million+ steps and never terminated in
testing. Randomized Prim's was used instead — it grows the tree from the full
frontier and terminates in exactly n−1 successful steps with no pathological
cases.

## Algorithm: randomized Prim's

Wilson's algorithm is the standard way to generate a uniform random spanning tree.
It never gets trapped because it works on the full graph and erases loops instead
of getting stuck in them.

**State:**
- `tree` — set of `(col, row)` positions already in the tree; initially `{(0, 0)}`
- `result` — output list `[(parent_idx, exit_side, pos), …]`; initially `[(None, None, (0, 0))]`
- `index` — map from position to result index; initially `{(0, 0): 0}`

**Loop** while `len(tree) < n`:

1. Choose any start position `s` that is adjacent to a tree node and not yet in the
   tree. (One way: pick a random unvisited neighbour of a random tree node.)

2. Perform a loop-erased random walk from `s`:
   - Maintain the current walk as an ordered list and a `walk_index` dict mapping
     position → index-in-walk.
   - At each step pick a random neighbour (any of the four cardinal directions,
     including positions already in the walk or the tree).
   - If the neighbour is already in the current walk, erase the loop: truncate the
     walk list back to the first occurrence of that neighbour.
   - If the neighbour is in `tree`, stop — the loop-erased walk is now a simple
     path from `s` to the tree.

3. Add the path to the tree. The path ends at a tree node `t`; the nodes are
   `w[0], w[1], …, w[k-1]` (none yet in tree), with `w[k] = t` (already in tree).
   Add them in **reverse** order (nearest-to-tree first) so every parent appears in
   `result` before its children:
   - For `i = k-1` down to `0`:
     - parent position = `w[i+1]`, parent index = `index[w[i+1]]`
     - exit\_side = direction from `w[i+1]` to `w[i]`
     - append `(parent_idx, exit_side, w[i])` to `result`
     - record `index[w[i]] = len(result) - 1`
     - add `w[i]` to `tree`
     - stop early if `len(tree) == n`

**Output format:** unchanged — a list of length exactly `n` where entry `i` is
`(parent_idx, exit_side, (super_col, super_row))`, with `parent_idx=None` and
`exit_side=None` for the root (index 0). Parents always appear before children.

---

## `branch_prob` retirement

Wilson's algorithm produces a uniform random spanning tree; the branching topology
emerges naturally from the random walk and cannot be directly controlled by a
probability parameter.

`branch_prob` will be **retired**:

| Change | Detail |
|--------|--------|
| `_spanning_tree` signature | Drop `branch_prob` parameter |
| `levelgraph.py` call site | Remove `branch_prob = feature_set.get(…)` and the argument |
| `levels.py` feature sets | Remove all `'branch_prob': …` entries |
| `test_no_branching_at_zero_prob` | Remove — the path-only guarantee no longer applies |
| `test_invariants_hold_for_all_inputs` | Remove the `p` parameter from `@given` and the call |

**Design note:** levels 1–2 currently use `branch_prob=0.0` to guarantee a linear
chain of grids. With Wilson's, early levels will instead get naturally-branching
trees. For small grid counts (n=2, 3) no branching is possible anyway; for n=4+
some branching will occur. If strict chain topology is needed for specific levels,
a separate ticket should address it (e.g. a `topology='path'` flag implemented
via a path-specific algorithm distinct from Wilson's).

---

## Tests to add / update

| Test | Action |
|------|--------|
| `test_length_equals_n` (parametrised n=1..10) | Keep — must now pass for all seeds |
| `test_invariants_hold_for_all_inputs` (Hypothesis) | Remove `p` from `@given`; keep all other assertions; confirm the previously-failing seed no longer appears in the Hypothesis DB |
| `test_no_branching_at_zero_prob` | Remove |
| `test_branching_occurs_with_high_prob` | Remove (branch_prob gone) |

---

## Verification

- `poe test` passes with all spanning-tree invariant tests green.
- The Hypothesis database entry for `_spanning_tree(9, 0.0, Random(1007084))` no
  longer replays a failure.
- Manual play of several Act 2 levels confirms normal multi-grid structure.

---

## Done when

- [ ] `_spanning_tree(9, random.Random(1007084))` returns exactly 9 nodes.
  *(commit: )*
- [ ] `poe test` green with no spanning-tree failures.
  *(commit: )*
- [ ] No `branch_prob` references remain anywhere in the codebase.
  *(commit: )*
