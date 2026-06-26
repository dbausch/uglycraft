# Bug Fixes: Open Door Drawing and Water Planks Count

## Status

- [ ] Open doors drawn only in the room where they were opened
- [ ] Each water edge supplies exactly 2 planks on the player's side of the graph

---

## Bug 1 — Open doors appear on every grid

### Symptom

After unlocking a door in one room, an open-door sprite appears at the same tile
coordinates in every other room the player visits.

### Root cause

`self._opened_doors` stores `(col, row, door_color)` with no room key.  The render
loop at `game.py:1258` iterates all of `_opened_doors` without filtering by the
current room, so every room gets the sprite drawn at those coordinates.

Closed doors are correctly filtered (`self._room_doors.get(rk, [])` at line 1253);
opened doors are not.

### Fix

Store `(room_key, col, row, door_color)` in `_opened_doors` and filter by `rk` in the
render loop.

Files: `game.py`
- `_try_auto_open_door`: change `.add((col, row, door_color))` to
  `.add((room_key, col, row, door_color))`
- render loop: unpack four values; skip entries where `ok != rk`

---

## Bug 2 — Fewer planks than water edges

### Symptom

A level with N water edges may place fewer than 2N planks reachable to the player.

### Root cause

`LevelGraphBuilder.add_water_room()` picks the planks room from `self._reachable`,
which already includes water rooms added in earlier calls.  If a later water room's
planks land in an earlier water room (which is behind a water edge), the player cannot
retrieve them without already having planks — a circular dependency.

### Fix

In `add_water_room()`, pick only from rooms that are NOT themselves water rooms.
Add `self._water_rooms: set` to `__init__` (starts empty).  In `add_water_room()`,
compute `dry_candidates = [r for r in self._reachable if r not in self._water_rooms]`,
pick from there, then add the new room name to `self._water_rooms`.

Files: `levelgraph.py`
- `LevelGraphBuilder.__init__`: `self._water_rooms: set = set()`
- `LevelGraphBuilder.add_water_room`: restrict planks candidate pool to non-water rooms

---

## Verification (manual)

- Open a locked door in one room; confirm no open-door sprite in other rooms.
- Play a level that generates 2+ water edges; confirm 2 planks per water edge are
  collectable before crossing any stream.

## Done when:

- [ ] Open door sprite is absent from rooms where the door was not opened
- [ ] Level with N water edges places exactly 2N planks in freely-reachable rooms
