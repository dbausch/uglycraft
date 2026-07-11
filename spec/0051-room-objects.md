# Spec 0051 — Rooms as live objects, RoomState deleted (refactor Stage 5, BL-35)

Stage 5, the final stage of the world-model refactor (→
`kb/world-model-review.md` §3 Stage 5): a `Room` object owns everything
room-scoped, rooms persist **by identity** — `_enter_room` swaps a
pointer — and the two-idiom persistence (RoomState snapshot copying
*versus* per-room dicts keyed by room name) disappears entirely. Zero
behaviour change, byte-identical spec-0044 goldens.

## Status

- [x] R1 — `Room` class (in `rooms.py`): `key`, `data`, `cells`,
      `enemies`, `blocks`, `blocks_initial`, `plates`, `tile_owner`,
      `dead_squares`, `flame_jets`; built once by `Room.from_data`
      (difficulty-dependent enemy selection moves in, RNG-free);
      `RoomState`, `_save_room_state`, and the fresh/restore double
      branch are deleted
- [x] R2 — Rooms are created **lazily on first entry** and kept in
      `World._rooms`; `fresh = key not in self._rooms` — exactly the
      spec-0048 "first entry of a freshly generated room" semantics for
      `_verify_blocks`, for free
- [x] R3 — World's current-room views become read-only properties over
      `self.room`: `cells`, `enemies`, `_current_room` (= `room.key`,
      still `None` on Act 1 — the golden traces record it),
      `_current_room_data` (= `room.data`); the last per-room dicts
      (`_room_blocks`, `_room_blocks_initial`, `_room_plates`) die —
      consumers read `self.room.blocks` / `self.room.plates`
- [x] R4 — `_reset_blocks` iterates the *visited* rooms
      (`self._rooms.values()`); unvisited rooms need no reset — their
      blocks still sit at the initial positions in the level dict
- [x] R5 — Facade/tests updated (reads of `_room_blocks[rk]` become
      `world.room.blocks` / `world._rooms[rk].blocks`); goldens
      byte-identical; unit tests red-first for the Room API and the
      lazy/visited semantics
- [x] R6 — Docs: kb review Stage 5 done → **BL-35 completes**;
      feature-inventory; backlog close via agent

## Motivation

Rooms currently persist through two coexisting mechanisms: `RoomState`
snapshots hand-copied in both directions on every transition (`cells`,
`enemies`, `blocks`), and per-room dicts keyed by room name
(`_room_blocks`, `_room_plates`) that are *partially* mirrored into
those snapshots. `_enter_room` has a fresh/restore double branch, and
every new piece of room state must decide which idiom it joins — kb
review P3's worst residue. After Stage 5 there is exactly one answer:
it's a field on `Room`, and persistence is object identity.

## Design

### The Room object (R1, R2)

```python
class Room:                      # rooms.py, next to find_exit
    key, data                    # room dict (read-only source)
    cells                        # RoomCells (barriers/water/items/damage)
    enemies, blocks              # live lists (mutated in place)
    blocks_initial               # tuple of start positions (death reset)
    plates                       # [(c, r, channel), ...]
    tile_owner, dead_squares, flame_jets   # per-room constants from data

    @classmethod
    def from_data(cls, key, room_data, difficulty): ...
```

- `from_data` absorbs today's fresh branch verbatim: `build_room_cells`,
  the difficulty-dependent enemy selection (EASY: specials + one
  chaser; HARD: all + patrols), the flame-jet `'_tile_set'` precompute.
  It consumes no RNG, so creation order cannot shift any random draw.
- `World._rooms: dict[key, Room]`, populated on first entry. Lazy
  creation makes `fresh` (spec 0048's `_verify_blocks` gate) fall out of
  `key not in self._rooms`. Unvisited rooms have no live state — which
  is today's behaviour, since their enemies/blocks exist only as data
  until first entry.
- `_enter_room(key)` becomes: get-or-create, `self.room = room`,
  re-tag enemies (idempotent, as today runs on every entry), reset
  `_flame_timer` (today's per-entry reset — it stays on `World`),
  clear `_bump_consumed`, `_verify_blocks()` if fresh. No copying in
  either direction; `_try_room_transition` drops the save call.

### Current-room views (R3)

`self.cells`, `self.enemies`, `self._current_room`,
`self._current_room_data` become read-only properties over `self.room`
— every existing reader (world internals, the Game facade chain,
harness snapshots) keeps working verbatim, including in-place mutation
through them (`enemies.clear()` in tests mutates the room's list).
`World.__init__` seeds `self.room` with an empty placeholder so
`blocked()` is queryable before the first level loads, as the empty
`RoomCells()` did.

Trace compatibility: the harness records `_current_room` per tick;
`room.key` is `None` for wrapped Act 1 (spec 0046) and the room name
for Act 2 — byte-identical goldens.

The start_level gather loop shrinks to `_loot_total` counting (a sum
over the room dicts); `_room_blocks`, `_room_blocks_initial`, and
`_room_plates` are deleted along with their facade entries.

### Death reset scope (R4)

`_reset_blocks` today resets **all** rooms' blocks from
`_room_blocks_initial` (gathered eagerly at level start). With lazy
rooms it iterates only `self._rooms.values()` — equivalent, because an
unvisited room's blocks were never moved: its eventual `from_data` puts
them at the same initial positions the eager gather recorded. The
channel clear stays as is.

### Tests (R5, red first)

- `Room.from_data` unit tests: field population, enemy selection per
  difficulty, `blocks_initial` snapshot (red: class missing).
- Lazy semantics: entering a room twice yields the *same object*
  (`world._rooms[k] is world.room`); wedged-block re-entry lock and the
  0048 regeneration tests keep passing unchanged (fresh = first entry).
- Reset scope: blocks moved in a visited room reset on death; an
  unvisited room, entered after a death, still gets its initial blocks.
- The existing broad locks (test_dispatch.py persistence, cross-grid
  channels, gate/plate timing) and all goldens carry over untouched —
  they were written against observable state for exactly this stage.

## Non-goals

- No global `(grid, col, row)` positions, no multi-floor `z` (kb R4 —
  future work, nothing currently needs it).
- `_opened_doors` (render-only history), `_bridged_water_rooms` (a rule
  about rooms, not room state), `_channels`, and loot counters stay on
  `World`.
- Blocks stay position tuples in `Room.blocks` (occupant entities are
  future work, e.g. BL-37's exploding blocks may motivate them).
- Level dict stays the serialization format (parsed once per room by
  `from_data`).

## Verification

1. `poe test` green with **zero golden diffs**; no `UGLYCRAFT_REGOLD`.
2. Red-first unit tests as above; the spec-0044/0048/0050 behaviour
   locks (transitions, persistence, regeneration, channels) are the
   main net.
3. Manual gate: user plays an Act 2 level with room transitions —
   break a wall / collect items / push a block in one room, leave,
   return; die with progress spread over several rooms.

## Done when:

- [x] R1 — `Room` + `from_data`; RoomState/save/restore deleted (42b4e8f)
- [x] R2 — lazy `_rooms` map; fresh = first entry (42b4e8f)
- [x] R3 — current-room properties; last per-room dicts deleted (42b4e8f;
      `parse_level_walls` moved rooms.py → cells.py to break the import
      cycle Room's cells dependency would create)
- [x] R4 — death reset over visited rooms (42b4e8f)
- [x] R5 — tests red→green; goldens byte-identical (42b4e8f — 522 passed)
- [x] R6 — docs (33be01c); BL-35 closed via backlog agent

User acceptance 2026-07-12: played room transitions, cross-room
persistence, and death with progress over several rooms — "all good".
This completes all five stages of kb/world-model-review.md §3.
