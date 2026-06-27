# Room-Count-Driven Strategy Selection

## Status

- [ ] `_STRATEGY_MAX_ZONES` table defined alongside the other strategy constants
- [ ] `layout_graph` filters the strategy pool to `max_zones ≤ n_rooms` before selecting
- [ ] `_pick_strategy` passes the room count constraint into its selection
- [ ] No empty-zone layouts generated in the test suite (property test)

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

Simple 2-zone strategies (`horizontal`, `vertical`, `off_centre`) are
always eligible — one empty zone in a 2-zone layout is the irreducible
minimum and is acceptable.

| Strategy    | Max zones | Min rooms to select |
|-------------|-----------|---------------------|
| `horizontal`  | 2 | always eligible |
| `vertical`    | 2 | always eligible |
| `off_centre`  | 2 | always eligible |
| `t`           | 3 | ≥ 3             |
| `double_t`    | 4 | ≥ 4             |
| `z`           | 4 | ≥ 4             |
| `l`           | 4 | ≥ 4             |

The "max zones" figure is the structural maximum for each strategy (e.g.
`double_t` can produce two near-side sub-zones + two far-side sub-zones = 4).
In practice some sub-zones are suppressed by the minimum-size guard (`w ≥ 3`,
`h ≥ 2`), but worst-case is used for the filter to be conservative.

---

## Implementation

### 1. New constant table (`levellayout.py`)

Add alongside the existing `_COVERS_*` sets:

```python
_STRATEGY_MAX_ZONES = {
    'horizontal': 2,
    'vertical':   2,
    'off_centre': 2,
    't':          3,
    'double_t':   4,
    'z':          4,
    'l':          4,
}
_SIMPLE_STRATEGIES = frozenset({'horizontal', 'vertical', 'off_centre'})
```

### 2. Filter in `layout_graph`

After `regular_rooms` is computed, before `rng.choice`:

```python
available = strategies or STRATEGIES
# When a pool (>1 strategy) is offered, restrict to strategies whose
# zone count does not exceed the room count.  Always keep simple
# 2-zone strategies so there is always a valid choice.
if len(available) > 1:
    n_rooms = len(regular_rooms)
    filtered = [s for s in available
                if s in _SIMPLE_STRATEGIES
                or n_rooms >= _STRATEGY_MAX_ZONES.get(s, 2)]
    if filtered:
        available = filtered
strategy = rng.choice(available)
```

The `len(available) > 1` guard preserves explicit single-strategy overrides
(used in tests and the stitch fallback) without applying the room-count
filter — those callers have already made a deliberate choice.

### 3. Filter in `_pick_strategy`

`_pick_strategy` also narrows the pool before `rng.choice`.  It needs the
room count passed in:

```python
def _pick_strategy(exits, available, rng, n_rooms=0):
    ...
    choices = [s for s in available if s in compatible]
    # Narrow further by room count (same rule as layout_graph)
    room_filtered = [s for s in choices
                     if s in _SIMPLE_STRATEGIES
                     or n_rooms >= _STRATEGY_MAX_ZONES.get(s, 2)]
    if room_filtered:
        choices = room_filtered
    return rng.choice(choices) if choices else 'double_t'
```

In `_build_super_grid`, count rooms in the subgraph and pass the count:

```python
n_rooms = sum(1 for name, node in sub.nodes.items()
              if node.size != NodeSize.CORRIDOR)
chosen = [_pick_strategy(frozenset(exits), strategies, rng, n_rooms=n_rooms)]
```

---

## Verification

No automated test suite for Python/UGLYCRAFT — verify manually:

- Run `poe run --level 11` through `--level 14` several times.
- Confirm no large all-wall zones appear in double-T or Z/L corridor grids.
- Confirm the test suite still passes: `poe test`.

---

## Done when

- [ ] `poe test` passes (no regressions)
- [ ] Large all-wall zones no longer appear in generated levels (user confirmed)
