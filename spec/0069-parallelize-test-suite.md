# Spec 0069 — Parallelize the test suite (BL-47)

## Status

- [x] `pytest-xdist` added to `requirements.txt`; installed in `.venv` (ee606ef)
- [x] `poe test` runs `pytest tests/ -n auto` (parallel by default; `-v` dropped) (ee606ef)
- [x] FS-loop → `@pytest.mark.parametrize('fs', …)` hoist in the heavy sweep
      tests (coverage-preserving; identical build count) (9890e3c)
- [x] Discrete-`gc` hoist for the single 85 s outlier
      `test_no_item_on_player_start_or_entrance` (budget-preserving 30 → 6×5) (cc1cda8)
- [x] Full suite green under `-n auto` (823 tests pass — count grew from 802)
- [x] Wall-time measured: ~10:30 serial → ~4:57 parallel (≈2.1×), dual-core bound
- [ ] BL-47 closed; `kb/backlog.md` updated (see spec 0070 follow-up)

**Outcome note.** On this 2-physical-core machine the item-splits give **no**
measured wall gain over plain `-n auto` (pre-split 298 s vs post-split 296 s):
the suite is core-bound, not tail-idle-bound, so splitting only helps on ≥3–4
physical cores / CI (none here). Splits kept per user decision (coverage-neutral
FS-hoists future-proof; gc-hoist reduction accepted). The real further lever is
cutting generation cost — spec 0070.

## Motivation

BL-47: the suite runs 802 tests in ~10:30 serial. Tests are independent and
CPU-bound. `pytest-xdist -n auto` on this 4-core machine already gives a
measured **~2.2×** (10:30 → 4:49, all 802 pass — the suite is parallel-safe:
headless pygame drivers are set at import per-process, and the only test file
write is golden re-recording gated behind `UGLYCRAFT_REGOLD=1`).

The gap between the observed 4:49 and the ideal floor (total-work ÷ 4 ≈ 3 min)
is **end-of-run tail idle**: a handful of very long single test *items* cannot
be split across workers, so 1 worker grinds on an 85 s item while 3 sit idle.
Measured critical path (`--durations`, `-n auto`):

| Item | s | Shape | Split technique |
|---|---|---|---|
| `test_entrance::test_no_item_on_player_start_or_entrance` | 85.7 | `@given(seed, gc∈[1,6])`, 30 ex | discrete-`gc` hoist |
| `test_sokoban::test_pipeline_push_puzzles_never_fail_end_to_end` | 70.0 | pure `@given(seed)`, 100 ex | **leave whole** (below floor) |
| `test_act2_solvability::test_single_grid_levels_solvable` | 51.9 | inner `for fs in _CHEAP_SETS` | FS hoist |
| `test_border_continuity::test_border_barrier_records_on_both_sides` | 49.5 | inner `for fs in _REC_SETS` | FS hoist |
| `test_key_placement::test_no_softlocked_doors` | 35.8 | inner `for fs in _FEATURE_SETS` | FS hoist |
| `test_key_placement::test_key_door_pairing` | 35.4 | inner `for fs in (*_FEATURE_SETS, …)` | FS hoist |
| `test_key_placement::test_keys_never_dropped` | 31.6 | inner `for fs in _FEATURE_SETS` | FS hoist |

Breaking the top items into medium chunks lets xdist pack 4 workers evenly and
collapses the tail. Target: **~3× overall (≈ 3:00–3:30 wall)**, to be
confirmed by measurement — the spec commits to the technique, not a number.

## Technique 1 — parallel by default (option a, zero code)

- Add `pytest-xdist` to `requirements.txt`.
- `poe test`: `.venv/bin/python -m pytest tests/ -v` → `.venv/bin/python -m
  pytest tests/ -n auto`. `-v` is dropped because xdist interleaves per-worker
  output, making verbose names noise. A serial run is still available on demand
  with `poe test -- -n0`.

## Technique 2 — FS-loop hoist (coverage-preserving)

The heavy sweep tests share this shape:

```python
@given(st.integers(...))          # draws N seeds
@settings(max_examples=N)
def test_foo(seed):
    for fs in _SETS:              # inner loop → all in ONE pytest item
        _build(fs, seed); assert ...
```

Rewrite to hoist the feature-set loop into a parametrize:

```python
@pytest.mark.parametrize('fs', _SETS)
@given(st.integers(...))
@settings(max_examples=N)
def test_foo(fs, seed):
    _build(fs, seed); assert ...
```

**Why this preserves (indeed improves) coverage at identical cost.** Before, one
item runs N examples, each building `len(_SETS)` levels from the *same* seed →
`N × len(_SETS)` builds, feature sets correlated on shared seeds. After, each of
the `len(_SETS)` items runs N examples with its own independently-drawn seeds →
`N × len(_SETS)` builds — same count, but feature sets now explore *independent*
seed samples (strictly more of the space). `max_examples` is unchanged. Each
`(test, fs)` is a separate pytest item that xdist distributes.

Apply to (exact list — module-level FS tuples already exist in each file):

- `tests/test_key_placement.py`: `test_keys_never_dropped`,
  `test_no_softlocked_doors`, `test_graph_keys_reachable`,
  `test_key_door_pairing` (its set is `(*_FEATURE_SETS,
  _levels.ACT2_FEATURE_SETS[2])` — parametrize over that exact tuple).
- `tests/test_border_continuity.py`: `test_border_openings_land_on_corridor`,
  `test_corridors_continue_across_border` (over `_SETS`),
  `test_border_barrier_records_on_both_sides` (over `_REC_SETS`).
- `tests/test_act2_solvability.py`: `test_single_grid_levels_solvable`
  (over `_CHEAP_SETS`), `test_crowded_multigrid_levels_solvable`
  (over `_CROWDED_SETS`).

`_build(fs, seed)` in each file already takes `fs` first, so the loop body moves
out unchanged. Existing pinned/regression (non-`@given`) tests are untouched.

## Technique 3 — discrete-`gc` hoist (budget-preserving), one test only

`test_entrance::test_no_item_on_player_start_or_entrance` is the single 85 s
outlier and has no FS loop — it draws `gc = st.integers(1, 6)` jointly with
`seed`, 30 examples. Hoist the small discrete dimension and divide the budget:

```python
@pytest.mark.parametrize('gc', range(1, 7))
@given(st.integers(0, 2**32 - 1))
@settings(max_examples=5, deadline=None)     # 6 × 5 = 30, unchanged total
def test_no_item_on_player_start_or_entrance(gc, seed):
    _g, lv = _build(seed, gc); _assert_start_tiles_item_free(lv)
```

Total builds stay at 30; the `gc` distribution becomes exactly uniform (6×5)
instead of randomly ~5-per-value. **Tradeoff (the one real one in this spec):**
per-item hypothesis exploration drops from 30 to 5 examples, so shrinking works
within a 5-example budget per `gc`. Acceptable for this simple
"no item on start/entrance tile" invariant; total sample count is identical.
Only this one test is hoisted this way — the smaller `gc` tests
(`test_grid_zero_reserved`, `test_entrance_anchored_to_player_start`) are left
alone.

## Non-goals

- **Seed-sharding** pure-`@given(seed)` items (e.g. `test_pipeline_push_puzzles`
  70 s, `test_full_pipeline_no_value_error`, `test_plates_never_on_landing_tiles`,
  `test_invariant_s_one_push_position_is_solvable` 500 ex). These are below the
  total-work ÷ 4 floor, so they pack as single chunks without gating the wall.
  Sharding would change hypothesis's per-shard database/shrinking semantics —
  out of scope; left as a possible BL follow-up if a future core-count needs it.
- **Reducing any `max_examples`** beyond the budget-neutral `gc` redistribution
  above. No safety net is weakened.
- **Hypothesis profile** (BL-47 option b) and **shared memoized build fixture**
  (option c). Left in the backlog.

## Verification

1. `poe test` (now `-n auto`) exits 0 with all tests passing.
2. Record wall time and compare against the 10:30 serial baseline; note the
   post-split `--durations` tail to confirm the top items shrank.
3. Argue budget invariance per changed test (build count unchanged for FS
   hoists; 30 total unchanged for the `gc` hoist).

## Done when:

- [x] `pytest-xdist` in `requirements.txt`, installed. — ee606ef
- [x] `poe test` uses `-n auto`, `-v` dropped, serial fallback documented. — ee606ef
- [x] FS-loop hoist applied to the 9 listed tests; each `(test, fs)` is a
      distinct item; per-test build count unchanged. — 9890e3c
- [x] `gc` hoist applied to `test_no_item_on_player_start_or_entrance`
      (6×5 = 30). — cc1cda8
- [x] Full suite green under `-n auto` (823 passed; count grew from 802). — ee606ef+
- [x] Wall time measured and recorded (~2.1×, dual-core bound); `--durations`
      confirms the top items are split (85 s outlier → 6 items). — this commit
- [ ] BL-47 closed in `kb/backlog.md`. — commit ____
