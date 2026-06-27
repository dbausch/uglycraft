# Room-Count-Driven Strategy Selection

## Status

- [x] `_STRATEGY_MAX_ZONES` table defined alongside the other strategy constants
- [x] `layout_graph` filters the strategy pool to `max_zones ≤ n_rooms` before selecting
- [x] `_pick_strategy` passes the room count constraint into its selection
- [x] No empty-zone layouts generated in the test suite (property test)
- [x] `'full_border'` added to `_STRATEGY_MAX_ZONES` (max_zones=1)
- [x] `full_border` is the fallback when `room_filtered` is empty
- [x] Erroneous `len(choices) > 1` guard removed from `_pick_strategy`
- [ ] `_SIMPLE_STRATEGIES` always-eligible carve-out removed from filter

---

## Problem

The layout strategy is chosen from a pool filtered only by required border
exits, without regard for how many rooms the corridor subgraph contains.
A `double_t` or `z` corridor creates up to four distinct room zones.  If the
subgraph has only two rooms, two zones are empty — large wall-filled areas
with no floor tiles and no passage into them.  The player can see these areas
but never enter them.

This violates the principle that the world is derived from the challenge graph:
the layout should reflect what the graph actually contains, not impose
structure that the graph cannot fill.

---

## Design rule

> Choose a corridor layout strategy whose maximum zone count does not exceed
> the number of rooms in the corridor's subgraph.

The filter is strict: a strategy is eligible only when
`n_rooms >= _STRATEGY_MAX_ZONES[strategy]`.  No carve-out for "simple"
strategies — a 1-room grid with a `vertical` corridor still leaves one zone
empty, which is unacceptable.  `full_border` (max_zones=1) serves as the
unconditional fallback, covering all exits by construction.

| Strategy      | Max zones | Min rooms to select |
|---------------|-----------|---------------------|
| `full_border` | 1         | ≥ 1 (fallback)      |
| `horizontal`  | 2         | ≥ 2                 |
| `vertical`    | 2         | ≥ 2                 |
| `off_centre`  | 2         | ≥ 2                 |
| `t`           | 3         | ≥ 3                 |
| `double_t`    | 4         | ≥ 4                 |
| `z`           | 4         | ≥ 4                 |
| `l`           | 4         | ≥ 4                 |

The "max zones" figure is the structural maximum for each strategy (e.g.
`double_t` can produce two near-side sub-zones + two far-side sub-zones = 4).
In practice some sub-zones are suppressed by the minimum-size guard (`w ≥ 3`,
`h ≥ 2`), but worst-case is used for the filter to be conservative.

---

## Implementation

### 1. New constant table (`levellayout.py`) — already done

```python
_STRATEGY_MAX_ZONES = {
    'horizontal': 2,
    'vertical':   2,
    'off_centre': 2,
    't':          3,
    'double_t':   4,
    'z':          4,
    'l':          4,
    'full_border': 1,   # perimeter frame; interior is one zone
}
_SIMPLE_STRATEGIES = frozenset({'horizontal', 'vertical', 'off_centre'})
```

`'full_border'` has `max_zones=1` because its corridor forms a rectangular
frame and the entire interior is a single room zone.  It covers all four
border sides by construction, so it is always exit-compatible.

### 2. Filter in `layout_graph` — update to remove `_SIMPLE_STRATEGIES` carve-out

After `regular_rooms` is computed, before `rng.choice`:

```python
available = strategies or STRATEGIES
if len(available) > 1:
    n_rooms = len(regular_rooms)
    filtered = [s for s in available
                if n_rooms >= _STRATEGY_MAX_ZONES.get(s, 2)]
    available = filtered if filtered else ['full_border']
strategy = rng.choice(available)
```

The `if s in _SIMPLE_STRATEGIES` arm is removed.  The filter is now a
strict zone-count check; `full_border` is the fallback when nothing passes.

The `len(available) > 1` guard preserves explicit single-strategy overrides
used in tests and the stitch-fallback path.

### 3. Filter in `_pick_strategy` — update to remove `_SIMPLE_STRATEGIES` carve-out

Same change: drop the `s in _SIMPLE_STRATEGIES` arm.

```python
def _pick_strategy(exits, available, rng, n_rooms=0):
    ...
    choices = [s for s in available if s in compatible]
    if not choices:
        return 'full_border'
    if n_rooms > 0:
        room_filtered = [s for s in choices
                         if n_rooms >= _STRATEGY_MAX_ZONES.get(s, 2)]
        choices = room_filtered if room_filtered else ['full_border']
    return rng.choice(choices)
```

The `else` branch (no exits required):

```python
else:
    choices = list(available) if available else ['full_border']
    if n_rooms > 0:
        room_filtered = [s for s in choices
                         if n_rooms >= _STRATEGY_MAX_ZONES.get(s, 2)]
        choices = room_filtered if room_filtered else ['full_border']
    return rng.choice(choices)
```

The `len(available) > 1` guard is **not** present in `_pick_strategy` —
that guard belongs only in `layout_graph`.

In `_build_super_grid`, count rooms in the subgraph and pass the count
(already done):

```python
n_rooms = sum(1 for name, node in sub.nodes.items()
              if node.size != NodeSize.CORRIDOR)
chosen = [_pick_strategy(frozenset(exits), strategies, rng, n_rooms=n_rooms)]
```

### 4. Effect on the observed failure (level 16, perpendicular 2-exit, 1 room)

For `exits = {'left', 'bottom'}`, `available = ['horizontal', 'vertical',
'off_centre', 'double_t', 't', 'z']`, `n_rooms = 1`:

- Exit filter: `compatible = _COVERS_L = {'l', 'double_t'}` → `choices = ['double_t']`
- Room filter: `room_filtered = []` (1 < 4 for `double_t`) → fallback to `['full_border']`
- Result: `'full_border'` chosen; the 1 room fills the full interior.

---

## Verification

No automated test suite for Python/UGLYCRAFT — verify manually:

- Run `poe run --level 11` through `--level 20` several times each.
- Confirm no large all-wall zones appear in any generated level.
- In particular: grids with 1–3 rooms and perpendicular or multi-sided exits
  should use a full-border corridor rather than double_t.
- Confirm the test suite still passes: `poe test`.

---

## Done when

- [ ] `poe test` passes (no regressions)
- [ ] Large all-wall zones no longer appear in generated levels (user confirmed)
