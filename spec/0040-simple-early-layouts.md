# Spec 0040 — Simpler corridor layouts for levels 11-13 (BL-22)

## Status

- [ ] L1 — The `layout_strategies` lists for `ACT2_FEATURE_SETS` indices 0-2
      (levels 11, 12, 13) contain only the simple strategies. The complex
      strategies `double_t`, `z` (which covers the `z/s` runtime variants), and
      `l` are removed; `horizontal`, `vertical`, `off_centre`, and `t` remain
- [ ] L2 — A pytest test (under `tests/`, run by `poe test`) asserts that across
      many seeds levels 11-13 only ever lay out with an allowed simple strategy
      (plus the `full_border` fallback); levels 14-20 are untouched

## Background

Act 2 levels (11-20) are generated from `ACT2_FEATURE_SETS` in `levels.py`
(`_act2_feature_sets`, `levels.py:195-342`). Each feature set carries a
`'layout_strategies'` list naming the corridor-layout strategies the generator
may pick from for that level. The first three sets (indices 0-2 → levels 11, 12,
13) are the player's introduction to procedurally-generated Act 2 levels and
should ease them in with simple corridor shapes.

The strategy names and their corridor shapes are defined in `levellayout.py`
(`STRATEGIES`, `levellayout.py:177`; dispatch at `levellayout.py:339-359`):

| Strategy | Corridor shape | Complexity |
|---|---|---|
| `horizontal` | Full-width horizontal band | simple |
| `vertical` | Full-height vertical band | simple |
| `off_centre` | Asymmetric horizontal band | simple |
| `t` | Horizontal band + 1 stem | simple |
| `double_t` | Horizontal band + 2 stems | **complex** |
| `z` | Two arms + connector (Z/S) | **complex** |
| `l` | L-shape (h-arm + v-arm) | **complex** |
| `full_border` | Rectangular frame | simple (fallback only) |

Note `z` is a single feature-set name that, at layout time, randomly expands to
one of the runtime variants `z_h`/`s_h`/`z_v`/`s_v` (`levellayout.py:672-677`).
Removing `z` therefore removes both the "z" and "s" strokes the backlog refers to
as `z/s`. `full_border` never appears in a feature-set list; it is injected only
by the generator's own fallback (see below).

**Current contents (exact), `levels.py`:**

```python
# Level 11 (index 0), levels.py:206
'layout_strategies': ['horizontal', 'vertical', 'double_t', 't', 'z', 'l'],
# Level 12 (index 1), levels.py:218
'layout_strategies': ['horizontal', 'vertical', 'double_t', 't', 'z'],
# Level 13 (index 2), levels.py:231
'layout_strategies': ['horizontal', 'vertical', 'off_centre', 'double_t', 't', 'z'],
```

So index 0 currently includes all three complex strategies (`double_t`, `z`,
`l`); indices 1 and 2 include `double_t` and `z`. None of the three currently
includes `l` except index 0.

## Resolution

Trim the complex strategies (`double_t`, `z`, `l`) from the `layout_strategies`
lists of indices 0-2, leaving only the simple ones in their existing order. This
is a `levels.py` data-only change (`_act2_feature_sets`); no `levellayout.py`
code changes.

**Resulting lists (exact):**

```python
# Level 11 (index 0)
'layout_strategies': ['horizontal', 'vertical', 't'],
# Level 12 (index 1)
'layout_strategies': ['horizontal', 'vertical', 't'],
# Level 13 (index 2)
'layout_strategies': ['horizontal', 'vertical', 'off_centre', 't'],
```

This is a pure removal: each remaining entry was already present in its list, and
no new strategy is added. `off_centre` is one of the allowed simple strategies
but is only introduced from level 13 onward in the current data, so levels 11-12
keep their existing `horizontal`/`vertical`/`t` set rather than gaining
`off_centre` (adding it would be out of scope for a "remove complex options"
change).

### Room-count validity (cross-check)

The generator filters strategies by zone capacity before choosing one, using
`_STRATEGY_MAX_ZONES` (`levellayout.py:185-194`):

```
horizontal 2, vertical 2, off_centre 2, t 3, double_t 4, z 4, l 4, full_border 1
```

A strategy `s` is eligible only when `n_rooms >= _STRATEGY_MAX_ZONES[s]`
(`layout_graph`, `levellayout.py:328-334` for single-grid; `_pick_strategy`,
`levellayout.py:268-281` for the multi-grid path). `n_rooms` is the number of
**regular rooms in that grid's subgraph** (`regular_rooms`,
`levellayout.py:311-326`; per-grid count at `levellayout.py:2395-2396`) — for
multi-grid levels the level's total `room_count` is split across grids, so an
individual grid can have far fewer rooms than the level total.

Room counts for these levels: level 11 `(6, 8)` single grid; level 12 `(6, 8)`
over 2 grids; level 13 `(8, 10)` over 3 grids.

The trimmed lists remain valid:

- All retained strategies have a low zone requirement: `horizontal`, `vertical`,
  `off_centre` need `n_rooms >= 2`; `t` needs `n_rooms >= 3`.
- **Level 11** (single grid, 6-8 rooms): every retained strategy passes the
  `n_rooms` filter, so `['horizontal', 'vertical', 't']` is always non-empty.
- **Levels 12-13** (multi-grid): per-grid room counts can be small. If a grid
  has only 2 rooms, `t` is filtered out and a simple 2-zone band is used; if a
  grid has 1 room and **no** retained strategy passes the filter, the code's own
  `room_filtered or ['full_border']` fallback (`levellayout.py:271, 280, 333`)
  selects `full_border`. This is the same fallback that already exists today, so
  the trim cannot produce an empty strategy list or a crash.

### Exit-side compatibility (multi-grid, cross-check)

For multi-grid levels 12-13, `_pick_strategy` first intersects the available list
with the exit-coverage sets `_COVERS_LR` / `_COVERS_TB` / `_COVERS_ALL` /
`_COVERS_L` (`levellayout.py:180-183, 252-281`). The retained simple strategies
cover the common cases (`horizontal`/`off_centre`/`t` for left-right exits,
`vertical` for top-bottom exits). Exit configurations previously served only by a
complex strategy — e.g. a perpendicular two-exit grid that used to pick `l`, or a
3+ exit grid that used `double_t` — now find no compatible entry and fall back to
`full_border` (`levellayout.py:276`), a simple rectangular frame that reaches all
four borders. The level therefore stays solvable; the early-level "simple" intent
is preserved (a frame is simpler than a Z/L corridor, not more complex).

## Verification

This is a level-generator config change; verification is automated plus an
optional visual sanity check.

- **L2 — pytest (suite under `tests/`, run by `poe test`):**
  1. *Config assertion.* For `ACT2_FEATURE_SETS` indices 0-2, assert
     `set(layout_strategies) <= {'horizontal', 'vertical', 'off_centre', 't'}`
     and that none of `{'double_t', 'z', 'l'}` appears. Assert the exact lists
     above.
  2. *Generation sweep.* Across many seeds, generate levels 11-13 and assert the
     strategy actually used for each grid is in
     `{'horizontal', 'vertical', 'off_centre', 't', 'full_border'}`
     (`full_border` allowed because it is the generator's legitimate fallback;
     `double_t`/`z`/`l` must never occur). The chosen strategy is not currently
     recorded in the level dict, so the test instruments the dispatch — e.g.
     monkeypatch/spy on the `_layout_*` entry points (or `_pick_strategy` and the
     `rng.choice` in `layout_graph`) in `levellayout.py` to record every strategy
     name dispatched while generating these levels.
  3. *Untouched check.* Assert levels 14-20 (`ACT2_FEATURE_SETS` indices 3-9)
     still include the complex strategies (regression guard against an
     over-broad edit).
- **L1 — optional manual visual check (`poe run --level 11`, `--level 12`,
  `--level 13`):** play/observe each level and confirm the corridor shapes look
  like simple bands / single-stem T / rectangular frames, with no Z/S or L
  corridors.

## Done when:

- [ ] L1 — `ACT2_FEATURE_SETS` indices 0-2 carry exactly the trimmed lists
      (`['horizontal', 'vertical', 't']`, `['horizontal', 'vertical', 't']`,
      `['horizontal', 'vertical', 'off_centre', 't']`); `double_t`/`z`/`l` are
      gone from levels 11-13.
- [ ] L2 — pytest config + sweep test confirms levels 11-13 only lay out with the
      allowed simple strategies (or `full_border` fallback) across many seeds, and
      levels 14-20 are unchanged; `poe test` green.
