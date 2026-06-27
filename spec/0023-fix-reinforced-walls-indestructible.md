# Fix: Reinforced Walls Are Indestructible

## Status

- [ ] `_register_bump` returns early for `WALL_REINFORCED` (no hits registered, no break)

---

## Bug

`game.py:_register_bump` looks up `wall_type` from `_level_walls` but has no
guard for `WALL_REINFORCED`. The fallback in:

```python
hits_needed = WALL_BUMPS.get(wall_type, WALL_HITS_TO_BREAK)
```

returns 3 for any type absent from `WALL_BUMPS`, including `WALL_REINFORCED`.
Result: reinforced walls break after 3 bumps — identical to stone walls.

---

## Fix

Add a single early-return guard immediately after `wall_type` is read
(`game.py` line 182), before `_bump_consumed` is updated:

```python
wall_type = self._level_walls.get((col, row))
if wall_type == WALL_REINFORCED:
    return  # indestructible — bumping has no effect
if self._is_unbumpable(col, row):
    return
```

No other files need changing.

---

## Verification

Manual — no automated test for this path:

- Run `poe run --level 11` (first Act 2 level, which places reinforced walls).
- Walk into a reinforced wall repeatedly; confirm it never breaks.
- Walk into a stone wall; confirm it still breaks after 3 bumps.
- Walk into a wooden wall; confirm it still breaks after 2 bumps.

---

## Done when

- [ ] Reinforced walls cannot be destroyed by player bumping (user confirmed).
