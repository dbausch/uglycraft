# Spec 0039 — Grid entry tile reflects the source exit type (BL-12)

> **SUPERSEDED by spec/0056-grid-entry-tile-type.md.** Written before the
> world-model refactor (specs 0044–0052); its game.py line references, the
> `_gate_open` set, and the render-read mechanisms are stale. Do not implement
> from this file.

## Status

- [ ] T1 — Each multi-grid BORDER tile records its barrier type (open / locked /
      gated, plus key colour / gate id) on **both** the exit-side and entry-side
      room dicts at stitch time, guarded by the same surviving-prerequisite check
      that decides whether the barrier exists at all
- [ ] T2 — The border-exit render loop picks the sprite from the recorded barrier
      type — locked door / gate — instead of unconditionally drawing stairs; stairs
      remain the fallback only for a plain open border
- [ ] T3 — The destination-grid entry tile now matches the source exit the player
      crossed (locked door / gate / open passage), confirmed by manual visual check
      at a boundary of each barrier type

## The defect

Multi-grid Act 2 levels stitch adjacent 30×16 grids along `BORDER` edges in
`_build_super_grid` (`levellayout.py:2447-2508`). Each BORDER edge has an
`exit_side` on grid A and the opposite `entry_side` on grid B, and a barrier type
in its params (`barrier` ∈ {`open`, `locked`, `gated`}, plus `key_colour` /
`gate_id` — see `kb/architecture.md`, "Barrier type" and the data-flow summary).

At stitch time the wall is punched on **both** sides and an `exits` entry is added
to **both** room dicts (`levellayout.py:2469-2494`):

```python
room_a['walls'].pop((col_a, pos), None)   # exit side
room_b['walls'].pop((col_b, pos), None)   # entry side
...
exits_a[exit_key_a] = gname_b
exits_b[exit_key_b] = gname_a
```

But the barrier **entity** (locked door / gate) is appended only to the exit-side
room (`room_a`), at the source border tile (`levellayout.py:2496-2508`):

```python
barrier_tile = _BORDER_TILE[exit_side](pos)
barrier = edge.params.get('barrier', 'open')
if barrier == 'locked' and edge.params['key_colour'] in surviving_key_colours:
    room_a['locked_doors'].append((*barrier_tile, colour))
elif barrier == 'gated' and edge.params['gate_id'] in surviving_gate_ids:
    room_a['gates'].append((*barrier_tile, gate_id))
# else: barrier prerequisite absent — leave the border passage open
```

Grid B (the destination) gets only the punched wall and the `exits` entry — no
barrier record.

At render time (`game.py:1234-1243`) every border exit, on **either** side, is
drawn as a generic staircase:

```python
if self._is_multiroom:
    for exit_key in self._current_room_data.get('exits', {}):
        side, pos_str = exit_key.rsplit('_', 1)
        pos = int(pos_str)
        if side == 'right':    sc, sr = COLS - 1, pos
        ...
        self.surf.blit(sp['staircase'], (sc * TILE, sr * TILE))   # always stairs
```

On the **exit** side the staircase is later overdrawn by the actual door/gate
entity in the overlay pass (`game.py:1263-1266` gates, `1304-1308` locked doors),
so grid A shows the barrier correctly. On the **entry** side there is no barrier
record, so the destination tile shows a bare staircase regardless of what the
player crossed. Looking back from grid B at a locked door or gate, the player sees
stairs — the two sides do not match.

## Resolution

This is a **rendering** fix (no gameplay change): mirror the source barrier's
*appearance* onto the entry tile. The barrier entity stays only on grid A; the
key/plate logic, `_is_unbumpable`, and door-opening are untouched.

### T1 — record the barrier type on both sides at stitch time

The render loop has no access to the graph edges, so the barrier type must travel
on the room dict alongside `exits`. In `_build_super_grid`, where the BORDER edge
is stitched (`levellayout.py:2489-2508`), add a parallel `border_barriers` map to
**both** rooms, keyed by the same `exit_key` / `entry_key` already computed:

```python
# ('open', None) | ('locked', colour) | ('gated', gate_id)
if barrier == 'locked' and edge.params['key_colour'] in surviving_key_colours:
    info = ('locked', edge.params['key_colour'])
elif barrier == 'gated' and edge.params['gate_id'] in surviving_gate_ids:
    info = ('gated', edge.params['gate_id'])
else:
    info = ('open', None)
room_a.setdefault('border_barriers', {})[exit_key_a]  = info
room_b.setdefault('border_barriers', {})[exit_key_b] = info
```

The barrier type is read from `edge.params` (the same source the existing entity
placement uses), and it is guarded by the **identical** surviving-prerequisite
check: a border that degraded to open (key/plate dropped — see spec 0030 K2 and
`kb/architecture.md` "Barrier ↔ prerequisite coupling") records `('open', None)`
and must not show a phantom door. This keeps the entry-tile appearance consistent
with the actual passable/blocked state.

`border_barriers` rides on the room dict, so it is available at render time as
`self._current_room_data.get('border_barriers', {})` with no new instance plumbing
(mirrors how `exits` is read — `game.py:1236`, `_current_room_data` set at
`game.py:363`).

### T2 — pick the sprite from the barrier type at render

In the border-exit loop (`game.py:1234-1243`), once `(sc, sr)` is computed, look
up `border_barriers.get(exit_key)` and choose **one** sprite for the tile:

| Recorded barrier | Sprite blitted at the border tile |
|------------------|-----------------------------------|
| `('locked', colour)` | `door_{colour}_{o}` (closed locked door) |
| `('gated', gate_id)` | `gate_open_{o}` if `gate_id in self._gate_open` else `gate_closed_{o}` |
| `('open', None)` / missing | `staircase` (existing fallback) |

Orientation `o` comes from the existing `self._door_orient(sc, sr)` helper
(`game.py:172-184`), exactly as the exit-side door/gate overlay computes it — a
right/left border tile resolves to the same orientation on both grids (border
neighbours are reinforced), so the entry sprite matches the source. The matching
sprites already exist in the sprite dict: `door_{colour}_{v|h}`
(`sprites.py:1191-1192`), `gate_closed_{v|h}` / `gate_open_{v|h}`
(`sprites.py:1207-1210`).

Drawing the barrier sprite **instead of** the staircase (not under it) avoids a
double draw; on the exit side the overlay door/gate pass still paints over the same
tile (idempotent — same sprite/position, and an *opened* door on grid A is shown
via `_opened_doors`, `game.py:1309-1313`, on top). Stairs remain the visual marker
for a plain open border, which has no dedicated "open doorway" border sprite.

`_gate_open` is a global set of open gate ids (`game.py:297, 1265`), so the entry
tile mirrors the gate's current open/closed state even though the gate **entity**
lives only on grid A.

The level-entrance sprite at the start grid (`game.py:1229-1232`,
`draw_level_entrance`) is a separate concern (the outside-world entrance) and is
unaffected.

## Verification

Primarily a **manual visual check** (user acceptance) — this is a rendering
mirror with no automatable display assertion.

1. Generate Act 2 levels until a multi-grid boundary of each barrier type appears
   and walk through it, then look back from the destination grid:
   - `poe run --level 13` (and higher multi-grid Act 2 levels, e.g. 15, 18, 20)
     to reach grids stitched with **open**, **locked**, and **gated** borders.
   - Open border → entry tile shows stairs (unchanged).
   - Locked border → after opening the door on the source side and crossing, the
     destination entry tile shows the **same-colour locked door** (not stairs).
   - Gated border → after opening the gate and crossing, the destination entry
     tile shows the **gate** in its current open/closed state (not stairs).
   Confirm the entry tile matches the exit the player just crossed (T3).

2. **Optional automated guard (T2):** if a pure tile-selection helper is extracted
   — e.g. `_border_tile_sprite_key(barrier_info, orient, open_gate_ids)` returning
   the sprite key string — unit-test the mapping (`('locked', 'red')` → `door_red_*`,
   `('gated', gid)` open vs closed, `('open', None)` → `staircase`) without a
   display, using only the string result. No pygame surface is required.

## Done when:

- [ ] T1 — Stitching records `border_barriers[exit_key] = (type, prereq)` on both
      the exit-side and entry-side room dicts, guarded by the surviving-prerequisite
      check (degraded-to-open borders record `('open', None)`).
- [ ] T2 — The border-exit render loop selects locked-door / gate / staircase from
      the recorded barrier type instead of unconditionally drawing stairs; the
      tile-selection mapping is correct (helper unit-test green if extracted).
- [ ] T3 — Visual check confirms each destination entry tile matches the source
      exit type the player crossed — open, locked, and gated (user-confirmed).
