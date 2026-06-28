# Greedy zone assignment in `_layout_corridor`

## Status

- [x] `LayoutError` exception class defined in `levellayout.py`
- [x] `_next_room_tiles` helper computes tile count for the next room added to a zone
- [x] Greedy assignment replaces round-robin in `_layout_corridor` (lines 601–610)
- [x] Retry loop in `_generate_act2` catches `LayoutError` and retries with a fresh RNG

---

## Problem

`_layout_corridor` distributes rooms to zones round-robin by index.  When a stem
lands near a grid border the two sub-zones are wildly different in width — e.g.
Zone A width 3 and Zone B width 21.  Round-robin can assign 2 rooms to Zone A
even though its cap is 1.  `_pack_band` silently drops the second room, leaving
dead wall space and one fewer room placed than the graph specified.

This is wrong even when the total capacity across all zones is sufficient to hold
all rooms.

## Algorithm

Replace the round-robin block (lines 601–610) with a greedy picker.

### Helper: `_next_room_tiles(zw, zh, fn, k)`

Returns the tile count the next room would receive if it were added as the
`(k+1)`-th room to a zone with dimensions `zw × zh` using packer `fn`.
Returns 0 if the zone is already full (base width/height would fall below the
minimum of 2).

```
_pack_band zones:
    base = (zw - k) // (k + 1)
    return base * zh   if base >= 2   else 0

_pack_band_vertical zones:
    base = (zh - k) // (k + 1)
    return zw * base   if base >= 2   else 0
```

Derivation: with `k+1` rooms there are `k` inter-room gaps, so
`usable = dim - k` and `base = usable // (k+1)`.  This matches the formula
inside the packing functions exactly.

### Tie-breaking sort key (descending)

When two zones give equal tile counts, break ties in this priority order:

1. Zone area `zw × zh` — prefer larger zones (more room to grow)
2. `n_assigned` — prefer zones with fewer rooms already assigned
3. Random — a per-zone shuffle index computed once at the start of distribution

### Greedy loop

**Empty-zones-first rule:** while any valid zone has `n_assigned == 0`, the
candidate set is restricted to those empty zones.  Only once every zone has at
least one room does the unconstrained greedy apply.  This ensures every zone
receives at least one room before any zone receives a second.

```python
zone_rand = list(range(len(valid)))
rng.shuffle(zone_rand)

n_assigned = [0] * len(valid)
per_zone   = [[] for _ in valid]

for name in room_names:
    empty      = [i for i in range(len(valid)) if n_assigned[i] == 0]
    candidates = empty if empty else range(len(valid))

    best_i    = -1
    best_key  = (-1, -1, 0, -1)   # sentinel below any real key
    for i in candidates:
        zc, zr, zw, zh, fn = valid[i]
        t = _next_room_tiles(zw, zh, fn, n_assigned[i])
        if t <= 0:
            continue
        key = (t, zw * zh, -n_assigned[i], zone_rand[i])
        if key > best_key:
            best_key = key
            best_i   = i
    if best_i < 0:
        raise LayoutError(
            f"Cannot place all rooms: {len(room_names)} rooms,"
            f" total zone capacity exhausted"
        )
    per_zone[best_i].append(name)
    n_assigned[best_i] += 1
```

The packing calls that follow are unchanged.

## `LayoutError`

A new exception class in `levellayout.py`:

```python
class LayoutError(Exception):
    """Raised when a layout strategy cannot place all assigned rooms."""
```

It is not caught inside `levellayout.py`.  It propagates through
`layout_graph` → `build_level_dict` to the caller.

## Retry in `levels.py`

`_generate_act2` currently calls `LevelGraph.generate` and `build_level_dict`
once per feature set.  Wrap each level's generation in a `while True` loop that
retries with a fresh RNG on `LayoutError`.  Both `generate` and `build_level_dict`
must use the same fresh RNG for each attempt.

```python
from levellayout import build_level_dict, LayoutError

for i, features in enumerate(feature_sets):
    base_rng = _rnd.Random(seed + i)
    while True:
        rng = _rnd.Random(base_rng.randint(0, 2**31))
        graph = LevelGraph.generate(features, rng=rng)
        try:
            level_dict = build_level_dict(graph, rng=rng, ...)
            break
        except LayoutError:
            pass   # base_rng has advanced; next iteration gets a new seed
    levels.append(level_dict)
```

`LayoutError` is guaranteed to be rare: it can only occur when the graph
generator assigns more rooms to a grid than the chosen layout strategy's zones
can physically hold.  Because a valid solution always exists (smaller room
counts or wider zone splits always occur for some seed), the loop terminates.

## Tests

Add to the pytest suite.  No ad-hoc scripts.

### Unit: `_next_room_tiles`

- `_pack_band` zone `zw=3, zh=10, k=0` → `3 * 10 = 30`
- `_pack_band` zone `zw=3, zh=10, k=1` → `base = (3-1)//2 = 1 < 2` → `0`
- `_pack_band` zone `zw=7, zh=5, k=1`  → `base = (7-1)//2 = 3` → `3 * 5 = 15`
- `_pack_band_vertical` zone `zw=6, zh=4, k=0` → `6 * 4 = 24`
- `_pack_band_vertical` zone `zw=6, zh=4, k=1` → `base = (4-1)//2 = 1 < 2` → `0`

### Integration: no rooms silently dropped

Call `_layout_corridor` with a stem placed near the left border (e.g.
`col_frac=0.1`) so Zone A is ≤4 cols wide and Zone B is wide.  Assert that
`len(placed) - 1 == len(room_names)` (all rooms placed; −1 for the corridor
node itself).  Use a room count ≤ total capacity across zones.

### Integration: `LayoutError` on overflow

Call `_layout_corridor` with enough rooms to exceed total zone capacity.
Assert `LayoutError` is raised.

### Integration: empty zones filled before non-empty

With N rooms and N valid zones, every zone must receive exactly one room.
Without the empty-zones-first rule, greedy would stack multiple rooms in the
widest zone and leave the narrowest empty.

### Integration: greedy prefers wide zones

With two zones (narrow and wide) and a single room, assert the room lands in
the wide zone (gets more tiles there).

### Regression: existing `_layout_corridor` cases still pass

Run the full existing test suite (`poe test`); zero new failures.

---

## Done when

- [x] `_next_room_tiles` unit tests pass (confirmed by `poe test`) — c921ca8
- [x] No rooms are silently dropped when total zone capacity ≥ room count (test passes) — c921ca8
- [x] `LayoutError` is raised when room count > total zone capacity (test passes) — c921ca8
- [x] Greedy assignment puts a single room in the wider of two zones (test passes) — c921ca8
- [x] Empty zones receive a room before any zone gets a second (test passes) — ad25ef0
- [x] Retry loop in `_generate_act2` catches `LayoutError` and retries with a fresh RNG — c921ca8
- [x] Full test suite passes with zero regressions (`poe test`) — ad25ef0
