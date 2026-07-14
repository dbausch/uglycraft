# Spec 0079 — No block push (or explosion respawn) onto a collectable-item tile (BL-60)

Backlog: **BL-60 (P2)**. A push block must not come to rest on a tile that holds a
**collectable item** (rubble, metal, keys, award/treasure items, materials/planks
— anything in the cell **item layer**). Two paths can put it there today:

1. **Push** — `_try_push_block` accepts a target tile whenever it is unblocked and
   inside the block's own room floor; it does not consult the item layer.
2. **Explosion respawn** — `_block_respawn_tile` (spec 0076) draws a random free
   safe tile, again without excluding item-bearing tiles.

Either produces a block drawn on top of a pickup — an unintuitive interaction and
an overlapping-sprite mess. This spec refuses both. It is **strictly permissive of
existing solutions**: the player can always collect the item first, after which
the tile is free and the block can be pushed there — so **no push-puzzle
re-validation and no generator/levellayout change are needed**.
→ spec 0076 (respawn into the safe area), spec 0068 (push blocks), `cells.py`
item layer.

## Status checklist

- [x] **I1** — `_try_push_block` refuses the push when the target tile
  `(nc, nr)` carries a collectable (`self.cells.items(nc, nr)` non-empty),
  returning `False` so the existing failed-push path (`_register_bump`) runs —
  identical to how a push into a wall already fails (no move, a bump).
- [x] **I2** — `_block_respawn_tile` excludes item-bearing tiles from its
  candidate pool: a tile with `self.cells.items(tile)` non-empty is never chosen
  for an explosion respawn (added to the same filter that already drops blocked
  tiles, the player, and — as the primary path — plate tiles).
- [x] **I3** — No generator, `levellayout`, or puzzle-validation change: the
  constraint only ever *removes* a target that has a strictly-better
  collect-then-push alternative, so every existing solution survives.
- [x] **I4** — Verification: pygame-free `tests/test_world.py` (or
  `tests/test_exploding_blocks.py`) cases — a block cannot be pushed onto an item
  tile (push refused, block stays, a `'bumped'` is *not* emitted / a bump is), and
  a detonated block never respawns onto an item tile.
- [x] **I5** — Daniel confirms in-game: a block will not slide onto a pickup, and
  an exploded block never lands on one; collecting the item first then pushing
  still works.

## Background — confirmed facts

Established by reading the code (self-contained; do not re-derive):

### The item layer

`RoomCells` keeps a per-tile **item layer** separate from barriers/fixtures
(`cells.py:185`). `cells.items(c, r)` (`cells.py:237`) returns the tuple of
`Item(kind, payload)` at a tile — **empty** for a plain tile, non-empty exactly
when a collectable sits there. Items are parsed from three room-data lists into
this layer (`cells.py:400–402`): `treasures` → `Item('treasure', …)`,
`materials` → `Item('material', …)` (this covers rubble, metal, and planks — they
are material payloads), `keys` → `Item('key', …)`. `self.cells` is the current
room's cells (`world.py:195`), and a block always lives in the current room, so
`self.cells.items(nc, nr)` is the right query for both paths below. Collection
removes the item (`_collect_item`, `world.py:475`), after which the tile's item
layer is empty and the tile is a normal push/respawn target again.

### The push path

`_try_push_block(bc, br, dcol, drow)` (`world.py:546`):

```python
nc, nr = bc + dcol, br + drow
if not self.blocked(nc, nr) and (nc, nr) in self._room_floor(bc, br):
    block.col, block.row = nc, nr
    self._emit('bumped')
    self._light_doomed_fuses()
    return True
return False
```

The caller (`try_move`, `world.py:697`) runs `_register_bump(key, tc, tr)`
whenever `_try_push_block` returns `False` — so a refused push already has a
well-defined behaviour: the block does not move and a bump is registered, exactly
like pushing a block into a wall. Adding an item-layer term to the guard reuses
that path with no new code on the caller side.

### The explosion-respawn path

`_block_respawn_tile(b)` (`world.py:826`, spec 0076) builds its candidate pool
by filtering the room's safe tiles:

```python
player = (self.player.col, self.player.row)
own_room = self._room_floor(b.col, b.row)
plates = {pos for pos, _ in self.room.cells.fixtures_of_kind('plate')}
free = [t for t in self._safe_tiles
        if t in own_room and not self.blocked(*t) and t != player]
non_plate = sorted(t for t in free if t not in plates)
if non_plate:
    return random.choice(non_plate)            # normal path
if free:
    return random.choice(sorted(free))         # tiny room: plate last resort
return (b.col, b.row)                           # doomed-but-inert fallback
```

The `free` comprehension already excludes blocked tiles and the player; this spec
adds an item-layer exclusion to the same comprehension so item tiles never enter
`free` (and therefore never `non_plate` either). The degenerate `(b.col, b.row)`
fallback is unchanged — if literally nothing is free it stays put.

## I1 — Refuse a push onto an item tile

Add the item-layer term to the push guard:

```python
def _try_push_block(self, bc, br, dcol, drow):
    block = self.room.block_at(bc, br)
    if block is None:
        return False
    nc, nr = bc + dcol, br + drow
    # Confined to the block's own room floor (spec 0068); additionally refused
    # onto a tile that holds a collectable — a block on a pickup is an
    # unintuitive, overlapping-sprite state (BL-60).  Collect the item first,
    # then the tile is free and the push succeeds — so every puzzle solution
    # survives.
    if (not self.blocked(nc, nr)
            and (nc, nr) in self._room_floor(bc, br)
            and not self.cells.items(nc, nr)):
        block.col, block.row = nc, nr
        self._emit('bumped')
        self._light_doomed_fuses()
        return True
    return False
```

A refused push falls through to the caller's `_register_bump` (`world.py:703`) —
no move, a bump registered — matching a push into a wall.

## I2 — Exclude item tiles from the respawn pool

Add the same term to the `free` comprehension in `_block_respawn_tile`:

```python
free = [t for t in self._safe_tiles
        if t in own_room and not self.blocked(*t) and t != player
        and not self.cells.items(*t)]
```

Everything downstream (`non_plate`, the plate-last-resort, the doomed-but-inert
fallback) is unchanged. An item tile is never a respawn target; if the only free
safe tiles all carry items (degenerate, effectively impossible in a one-block
puzzle room), the existing `(b.col, b.row)` fallback keeps the block put rather
than forcing it onto a pickup.

## I3 — No generator / puzzle-validation change

The constraint is **strictly permissive**: it only removes a target `(nc, nr)`
that carries an item, and in every such case *collect-then-push* reaches the same
tile (the item is collectable, and collecting frees the tile). No push-puzzle
becomes unsolvable, so `levellayout.py`'s Sokoban validation, the graph
generator, and the shipped level goldens are untouched. → `kb/requirements.md`
(push-puzzle solvability), spec 0076 (safe-area respawn).

## I4 — Verification

pygame-free tests, reusing the `tests/test_exploding_blocks.py` fixture style
(`_room`, `_world`, `_push`, `_kinds`) which already builds isolated push-puzzle
rooms with `pushable_blocks`, `pressure_plates`, and `tile_owner`, and can add a
`materials=[…]` / `treasures=[…]` entry to seed the item layer:

1. **Push onto an item tile refused** — a room with a block and a collectable
   material on the tile directly in the push direction. Push toward it: the block
   **does not move** (its position is unchanged), `_try_push_block` returned
   `False`, and no `'bumped'` for that block was emitted (the caller registered a
   bump instead). Then *collect* the item (walk the player over it / remove it)
   and push again: now the block **moves** onto the freed tile — proving the
   refusal is item-specific and collect-then-push still works.
2. **Detonated block never respawns onto an item tile** — a puzzle room whose
   safe area includes a tile seeded with a collectable; push the block out of the
   safe area, let it detonate, and assert the respawn tile has an **empty** item
   layer (`not w.cells.items(*pos)`) as well as being inside the safe area and
   free (the spec-0076 invariants still hold).

The existing `random.seed(seed)` in `_world` keeps `random.choice` deterministic;
assertion 2 checks the *invariant* (no item on the respawn tile), not a specific
tile, so it does not hard-code the seeded draw.

## Out of scope

- Changing what counts as a collectable, or the item layer's structure.
- Any change to push confinement, fuse/detonation timing, the safe-area
  mechanic, or the respawn algorithm beyond the one extra exclusion term.
- Blocks vs enemies / treasure-drop interactions (enemies never share a
  push-puzzle room — R-P9).

## Done when:

- [x] **I1** — `_try_push_block` refuses a push onto an item-bearing tile,
  falling through to the existing bump path. (a481076)
- [x] **I2** — `_block_respawn_tile` never selects an item-bearing tile; the
  spec-0076 fallbacks are otherwise unchanged. (a481076)
- [x] **I3** — no generator/levellayout/puzzle-validation change; goldens
  byte-identical. (a481076 — full suite 893 passed)
- [x] **I4** — the two verification cases (push-refused + collect-then-push
  succeeds; respawn never on an item tile) pass; the full suite stays green.
  (a481076)
- [x] **I5** — Daniel confirms in-game: a block won't slide onto a pickup, an
  exploded block never lands on one, and collect-then-push still works.
  (user-accepted 2026-07-15)
