# 0055 — Grid zero for single-grid levels: uniform entrance side (BL-41)

## Status

- [ ] `LevelGraph.generate` draws grid zero's pseudo-exit side for **every**
      generated graph (single-grid included); `entrance_side` is never None
      on generated graphs
- [ ] Single-grid `build_level_dict` honours `graph.entrance_side`:
      strategy coverage filter + deterministic entrance placement
- [ ] Entrance side uniformly distributed on level 11 (was 64 % left /
      30 % top / 6 % bottom / 0 % right over 200 seeds)
- [ ] Golden `act2_L11_walk` re-recorded once; `act2_L13_walk` byte-identical
- [ ] Full suite green

## Problem

Spec 0053 gave multi-grid levels a uniformly random entrance side via grid
zero, but left single-grid levels on the old scanning path: `_pick_entrance`
tries sides in the fixed order (left, top, bottom, right) and takes the
first one the corridor reaches. On a single-grid level nothing is occupied,
so any strategy whose corridor touches the left border yields a left
entrance, top only wins for vertical-ish corridors (and always beats
bottom, since a vertical spine reaches both), and right — scanned last —
can never win. Measured on level 11 over 200 seeds:

| side | share |
|---|---|
| left | 64 % |
| top | 30 % |
| bottom | 6 % |
| right | **0 %** |

Daniel's expectation (and the cleaner model): *every* level has an outside —
level 11 should have a grid zero too.

## Design

Extend spec 0053's grid zero to `grid_count == 1`:

### At graph generation (`LevelGraph.generate`)

The pseudo-exit draw becomes **unconditional**: grid zero occupies `(0,0)`,
draws `S` uniformly from the four sides, the (only) grid sits at `delta(S)`
(spanning-tree root; `_spanning_tree(1, …)` already returns just the root),
and `graph.entrance_side = opposite(S)`. Multi-grid behaviour and its rng
stream are unchanged — the same draw already happened there; single-grid
generation gains one leading `rng.choice`.

`entrance_side` is therefore set on every *generated* graph. Manually built
graphs (tests) keep the `None` default and the old scanning behaviour —
backward compatible.

### At layout (`build_level_dict`, single-grid path)

Mirror the multi-grid `_build_grid` flow:

1. Resolve `entrance_side = entrance_side or getattr(graph,
   'entrance_side', None)`.
2. When set, pre-pick the strategy with the existing
   `_pick_strategy(frozenset({entrance_side}), strategies, rng, n_rooms)`
   (n_rooms = non-corridor, non-closet nodes, as in `_build_grid`) and pass
   `required_exits={entrance_side}` into `layout_graph` — the strategy must
   cover the side, and R-S1 then guarantees the corridor reaches it. This
   respects the documented division of labour: `layout_graph` filters by
   room count only; **callers** pre-filter by exits.
3. `_pick_entrance` runs in its deterministic entrance-side mode (spec
   0053) — centre-most on-side corridor tile = `player_start`, border tile
   outside = `entrance`. The scanning mode remains only for manually built
   graphs and the non-start reference tile.

Level 11's strategy list (`horizontal, vertical, double_t, t, z, l`)
collectively covers all four sides, so every drawn side has compatible
strategies; the per-side draw is uniform, hence the entrance side
distribution becomes ~25 % per side (modulo LayoutError retries). The
strategy *mix* per side follows coverage (e.g. a drawn `top` selects among
vertical/z/l/double_t) — intended: the layout must face its entrance.

No geometric algorithm changes (selection and threading only) — geometry
rule not triggered.

## Golden-trace impact

Single-grid generation gains one leading rng draw → level 11's stream
shifts → `act2_L11_walk` re-recorded once (`UGLYCRAFT_REGOLD=1`).
Multi-grid streams are untouched: `act2_L13_walk` and the level-13
canonical hash must stay **byte-identical** (verified via the spec-0054
probe).

## Tests (red first)

Extend `tests/test_entrance.py`:

1. **Graph draw uniformity** — `LevelGraph.generate` with
   `grid_count = 1` over ~400 seeds: `entrance_side` is never None and each
   side's share is ≥ 15 % (uniform = 25 %). Red today (`entrance_side` is
   None for single-grid).
2. **Single-grid anchoring** — extend the existing level property test's
   grid-count range from 2–6 to **1–6**: entrance on
   `graph.entrance_side`, adjacent to `player_start`, corridor-owned. Red
   today for `gc = 1` (entrance side is None, never matches).
3. **Manual sweep** (not in suite): entrance-side distribution of real
   level 11 over 200 seeds ≈ uniform; spec-0054 probe shows level 13 hash
   unchanged and level 11 hash stable across `PYTHONHASHSEED=0..3`.
4. Re-record `act2_L11_walk`; full suite green, `act2_L13_walk` untouched.

## Done when:

- [ ] Generated single-grid graphs always carry `entrance_side`; draw
      uniform over 400 seeds (≥ 15 % per side)
- [ ] Single-grid levels place the entrance on `graph.entrance_side`,
      adjacent to the corridor-owned player start (property test, gc 1–6)
- [ ] Level 11 entrance-side sweep ≈ uniform (each side ≥ 15 % / 200 seeds)
- [ ] Level 13 canonical hash byte-identical pre/post; determinism tests
      green
- [ ] `act2_L11_walk` re-recorded; `act2_L13_walk` byte-identical;
      `poe test` exits 0
- [ ] kb updated (R-T6 covers single-grid; architecture entrance section);
      BL-41 closed in `kb/backlog.md`
