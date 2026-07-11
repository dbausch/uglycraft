# Spec 0056 — Grid entry tile shows the source exit type (BL-12)

Supersedes `spec/0039-entry-tile-exit-type.md`, which describes the same
defect but was written against the pre-refactor codebase (before specs
0044–0052): its `game.py` line references, the `_gate_open` set (replaced by
signal channels, spec 0050), and its direct room-dict rendering reads are all
stale. Spec 0052 (content registry, BL-38) explicitly deferred BL-12 as a
visual change needing its own spec — this is that spec, redesigned for the
layered-cell / Room-object / channel architecture.

## Status

- [x] B1 — Stitching records a `border_barriers` entry for every BORDER exit
      on **both** the exit-side and entry-side room dicts, guarded by the
      same surviving-prerequisite check that decides whether the barrier
      entity exists at all (degraded borders record `open`)
- [x] B2 — The border-exit render loop selects the tile sprite from the
      recorded barrier type via a pure sprite-key helper — locked door
      (open or closed, tracking the source door's true state) / gate (open
      or closed, tracking its channel) — and draws **nothing** for a plain
      open border (the punched gap in the border wall is the marker); the
      staircase blit is removed from this loop entirely
- [x] B3 — Automated tests green: unit tests for the sprite-key mapping,
      a stitch test asserting matching records on both room dicts, and the
      full suite (`poe test`) passes with the spec-0044 goldens unchanged
- [x] B4 — Manual visual check: each destination entry tile matches the
      source exit the player crossed — open, locked, and gated — confirmed
      by the user in play

## The defect

Multi-grid Act 2 levels stitch adjacent 30×16 grids along `BORDER` edges in
`_build_super_grid` (`levellayout.py`, edge loop starting ~line 2852). Each
BORDER edge carries in its `params`: an `exit_side` on grid A, the opposite
`entry_side` on grid B, and a barrier type `barrier ∈ {open, locked, gated}`
with `key_colour` / `gate_id` (decided at graph time by `_barrier_kw()` in
`levelgraph.py`).

At stitch time the wall is punched on **both** sides and an `exits` entry
(`'{side}_{pos}' → neighbour room key`) is added to **both** room dicts
(`levellayout.py` ~2882–2911). But the barrier **entity** is appended only to
the exit-side room dict, at the source border tile
(`_BORDER_TILE[exit_side](pos)`, i.e. col 0/29 or row 0/15):

- `barrier == 'locked'` and the key colour is in `surviving_key_colours`
  (levellayout.py:2914) → `room_a['locked_doors'].append((c, r, colour))`
- `barrier == 'gated'` and the gate id is in `surviving_gate_ids`
  (levellayout.py:2919) → `room_a['gates'].append((c, r, gate_id))`
- otherwise (open, or prerequisite dropped during layout) → nothing; the
  passage stays open (spec 0030 "barrier ↔ prerequisite coupling")

Grid B (the destination) gets only the punched wall and the `exits` entry —
no record of what kind of passage this is.

At runtime, `build_room_cells` (`cells.py`, spec 0047/0052) parses each room
dict once: the border ring becomes `Barrier('border')` cells **minus the exit
gaps**, and `locked_doors` / `gates` become `Barrier('door', colour=…)` /
`Barrier('gate', channel=gate_id)` cells — parse order makes the door/gate
win the border-exit tile on the **exit side**. On the **entry side** the exit
gap is simply an unbarriered hole in the border ring.

Rendering (`game.py`, `_render_field`, line 460):

- The border-exit loop (lines 504–512) blits `sp['staircase']` at **every**
  key of `self._current_room_data['exits']`, on either side, unconditionally.
- Later overlay passes draw the current room's cells: gates
  (`self.cells.barriers('gate')`, line 527 — open/closed from
  `self.channel(gate.channel)`), locked doors (`self.cells.barriers('door')`,
  line 568), and opened doors (`self._opened_doors`, line 573).

So on the **exit side** the staircase is overdrawn by the real door/gate
sprite and grid A looks right. On the **entry side** there is nothing to
overdraw with — the tile shows a bare staircase regardless of whether the
player just walked through an open passage, a locked door, or a gate.
Looking back from grid B, the two sides of the same border never match.
(This is the "type information erased at the boundary" pain point P5 in
`kb/world-model-review.md`; the registry paper-test there reads: *"Stairs
(BL-12): no new mechanism — plumb the passage/edge type as data."*)

## Design

This is a **rendering** fix. Gameplay is untouched: the barrier entity, key
consumption, channel/gate logic, bump dispatch, and `find_exit` transitions
stay exactly as they are. The source barrier's *appearance* — including its
live open/closed state — is mirrored onto the entry tile.

**Design constraint (review, 2026-07-11): stairs are reserved for future
floor-to-floor travel. No entry/exit within the same floor may ever show the
staircase sprite.** All BORDER crossings are same-floor, so this spec does
not merely stop showing stairs on barrier tiles — it removes the staircase
blit from the border-exit loop altogether. An open border is rendered as
nothing: the punched gap in the border wall (plain floor) is the visual
marker. The `staircase` sprite itself stays in `sprites.py` for the future
inter-floor feature.

### B1 — record the barrier type on both room dicts at stitch time

The renderer has no access to graph edges, so the barrier type must travel on
the room dict, alongside `exits`. In `_build_super_grid`'s BORDER-edge loop,
where the barrier entity is placed (levellayout.py ~2912–2924), record on
**both** rooms, keyed by the same `exit_key_a` / `exit_key_b` already
computed:

```
room['border_barriers'][exit_key] = (kind, param, home)
```

one uniform 3-tuple per BORDER exit, with exactly three variants:

| Border state | Record |
|---|---|
| locked, key colour survived placement | `('locked', key_colour, (home_room_key, (hc, hr)))` |
| gated, gate id survived placement | `('gated', gate_id, None)` |
| open — including degraded barriers whose prerequisite dropped | `('open', None, None)` |

- The guard conditions are the **identical** `surviving_key_colours` /
  `surviving_gate_ids` checks that decide entity placement: a border that
  degraded to open must record `('open', None, None)` on both sides — never
  a phantom door the player could not have needed a key for.
- `home` (locked only) identifies where the one real door entity lives: the
  exit-side room key (`grid_name_map[edge.node_a]`) and its border tile
  (`_BORDER_TILE[exit_side](pos)`). This is precisely the tuple prefix that
  `World._try_auto_open_door` records into `_opened_doors`
  (`(room_key, col, row, colour)`, world.py:470), so the renderer can tell
  "opened" from "closed" on either side with one set lookup and no
  cross-room cell access. Gates need no home: gate state is the global
  channel table (`world.channel`, spec 0050), which already spans grids.
- Every stitched BORDER exit gets a record — `exits` keys and
  `border_barriers` keys are 1:1 on multi-grid rooms. Single-grid levels
  and Act 1 rooms have no `exits` and are unaffected.

**Deliberately not a cells entry.** `border_barriers` is room *metadata* like
`exits` / `tile_owner` / `dead_squares` — it must **not** become a
`CONTENT_PARSERS` entry (`cells.py`, spec 0052) and must **not** place a
mirror `Barrier` in the entry-side cells: a real door barrier there would
*block* (`Barrier.blocks()` is True for doors until removed), walling the
player in until they spend a second key, and the entry tile must stay
walkable for `find_exit` to trigger the return transition. A mirror gate
barrier would coincidentally behave (channels are global) but doors cannot,
so no runtime entity is mirrored — render-only, both kinds.

### B2 — select the sprite from the record at render time

In the border-exit loop (`game.py` 504–512), after `(sc, sr)` is computed
from the exit key, look up `self._current_room_data.get('border_barriers',
{}).get(exit_key)` and blit **at most one** sprite chosen by a **pure
helper** (module-level function taking the record, the orientation, the set
of open channels, and the opened-doors set; returning a sprite-key string,
or `None` for "draw nothing" — no pygame, unit-testable):

| Record | Condition | Sprite key |
|---|---|---|
| missing or `('open', None, None)` | — | `None` — nothing blitted; the tile shows the plain floor gap |
| `('locked', colour, home)` | `(home_room, hc, hr, colour)` in `self._opened_doors` | `door_open_{o}` |
| `('locked', colour, home)` | otherwise | `door_{colour}_{o}` |
| `('gated', gate_id, None)` | `self.channel(gate_id)` | `gate_open_{o}` |
| `('gated', gate_id, None)` | otherwise | `gate_closed_{o}` |

All sprites already exist in the sprite dict: `door_{colour}_{v|h}`
(sprites.py:1191–1192), `door_open_{v|h}` (1193–1194),
`gate_closed_{v|h}` / `gate_open_{v|h}` (1207–1210). The `staircase` sprite
(1195) is no longer referenced by this loop (reserved for inter-floor
travel).

**Orientation** `o` comes from the existing `self._door_orient(sc, sr)`
helper (game.py:112), the same one the door/gate overlay passes use. On a
border tile it resolves identically on both grids of an edge: left/right
border tiles (col 0 or 29) have floor beside them and border above/below →
`'h'`; top/bottom border tiles (row 0 or 15) have reinforced border tiles
left/right → `'v'`. So the entry sprite's orientation always matches the
source's.

**The unconditional staircase blit is deleted, not overdrawn.** On the exit
side the record-selected sprite is idempotent with the later overlay passes
(gate pass, door pass, opened-door pass), which repaint the very same sprite
at the same tile, because the record's state conditions coincide with the
entity state by construction (same channel, same `_opened_doors` entry). On
the entry side there is no overlay, so the record-selected sprite — or the
bare floor gap, for open borders — is what shows.

**State semantics** (why the two conditional rows are correct):

- *Locked, opened*: opening a door is permanent — `_try_auto_open_door`
  removes the barrier from the source cells and the `_opened_doors` entry
  survives death. Since BORDER edges form a spanning tree, a grid's single
  entry tile has always been crossed by the time the player can see it, so
  in practice the entry side shows `door_open` — the truthful mirror of what
  the source tile shows. The closed branch (`door_{colour}`) is the
  defensive complement and keeps the helper total (and matters if future
  features — saves, BL-43-style re-entry — ever show an uncrossed border).
- *Gated*: gate state is the channel, which is global and can go both ways —
  channels are cleared on life loss (`_reset_blocks`, world.py:658–660), so
  after a death both sides of a gated border consistently fall back to
  `gate_closed` until the plate is re-pressed. The entry tile mirrors this
  live, exactly like the source gate does.

The level-entrance sprite at the start grid (`game.py` 499–502,
`sp['level_entrance']`) is a different concern (the door to the outside /
grid zero, specs 0053/0055) and is not touched.

### Non-impact

- No rng draws are added or moved: the record is a deterministic dict write
  from values the stitch loop already holds. Generation streams are
  byte-identical apart from the new room-dict key; the process-determinism
  guard (`tests/test_generation_determinism.py`) compares hashes across
  subprocesses of the same code and is unaffected.
- No world behaviour changes: the spec-0044 golden traces record world
  events/state, not pixels, and must pass unchanged — no re-recording.
- `blocked`, bump dispatch, `find_exit`, key/plate logic: untouched.

## Verification

The project's pytest suite runs via `poe test`. Testable parts get tests
(written first, red, per the development workflow); the visual result is a
manual user-acceptance check.

1. **Unit tests — sprite-key helper** (no display needed; string in,
   string out; alongside the existing headless render tests in
   `tests/test_render.py` or a small new module):
   - missing record and `('open', None, None)` → `None` (nothing drawn —
     and in particular never `staircase`)
   - `('locked', 'red', home)` with the home tuple absent from the
     opened-doors set → `door_red_h` / `door_red_v` per orientation
   - same with the home tuple present → `door_open_h` / `door_open_v`
   - `('gated', gid, None)` with `gid` not in the open channels →
     `gate_closed_*`; with `gid` open → `gate_open_*`
2. **Stitch test — records on both sides** (with the existing stitching
   tests in `tests/test_border_continuity.py`, using the act2 fixtures or
   seeded generation): for every stitched multi-grid level checked, each
   room's `exits` keys and `border_barriers` keys are identical sets; the
   two records of one BORDER edge are equal on both rooms; a `locked` /
   `gated` record exists iff the matching entity was appended to the
   exit-side room's `locked_doors` / `gates` (and the record's `home` names
   exactly that room key and border tile); seeds covering all three barrier
   kinds are included, and a degraded-prerequisite case records `open`.
3. **Full suite**: `poe test` exits 0; the spec-0044 goldens pass without
   re-recording.
4. **Manual visual check** (user acceptance, B4): `poe run --level 13` (and
   higher multi-grid levels, e.g. 15/18/20) until a border of each kind is
   found; cross it and look back at the entry tile:
   - open border → a plain floor gap in the border wall, **no stairs on
     either side**;
   - locked border → the just-opened door is shown **open** on the entry
     tile (not stairs, not a closed door demanding a second key);
   - gated border → the gate, mirroring its live state — open while the
     block holds the plate, and **closed on both sides after dying** (life
     loss clears channels), re-opening when the plate is pressed again.

## Done when:

- [x] B1 — `_build_super_grid` records
      `border_barriers[exit_key] = (kind, param, home)` on **both** room
      dicts of every BORDER edge, guarded by the surviving-prerequisite
      checks; degraded borders record `('open', None, None)`; `exits` and
      `border_barriers` keys are 1:1. (stitch test of Verification 2 green)
      — tests bc3e723, implementation b62f370
- [x] B2 — The border-exit render loop draws the record-selected sprite via
      the pure sprite-key helper — nothing (plain floor gap) for open
      borders, the staircase sprite never appearing on any same-floor
      entry/exit; locked doors track the source door's opened state through
      `_opened_doors` via the record's `home`; gates track their channel.
      (helper unit tests of Verification 1 green)
      — tests bc3e723, implementation b62f370
- [x] B3 — Full `poe test` suite green, spec-0044 goldens unchanged (no
      re-recording). — 542 passed at b62f370
- [x] B4 — Manual check per Verification 4: the user has explicitly
      confirmed in play that entry tiles match the crossed exit for all
      three barrier kinds (open / locked / gated), including the
      gate-closes-on-death mirror. — confirmed by Daniel 2026-07-11
