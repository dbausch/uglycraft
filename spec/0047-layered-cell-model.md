# Spec 0047 — Layered cell model: walls become barriers, passability becomes a query (refactor Stage 3, BL-35)

Stage 3 of the world-model refactor (→ `kb/world-model-review.md` §3
Stage 3, §5, §6.4): replace the boolean `walls` grid and the parallel
wall-ish structures with an authoritative **layered cell model** — a
terrain layer plus a fixture set per cell — and turn passability into a
**query** folded over the layers instead of a cached grid that every
mutator must remember to rebuild. Kills P1 (the grid erases *why* a tile
blocks) and P2 (full-rebuild invalidation). Migration runs under the
§6.4 **shadow-grid** protocol: the old grid stays alive as an assertion
until it has been silent through the full suite *and* a play session.
Zero behaviour change, proven by byte-identical spec-0044 goldens.

## Status

- [ ] T1 — `cells.py`: pygame-free cell model (`Terrain`, `Barrier`,
      `Bridge`, `RoomCells`) built once per room from the level dict
- [ ] T2 — Dual-write + shadow assertion: every mutation updates the cell
      model; the old `walls` grid is still rebuilt and compared cell-by-cell
      (`UGLYCRAFT_SHADOW=1`, always on in the test suite)
- [ ] T3 — All passability consumers flipped to the query: entities take a
      `blocked(c, r)` callable; `_bfs_from`, spawn/relocate scans,
      push/place/bridge/bump logic, `_verify_blocks`, `_respawn_enemy`
- [ ] T4 — Barrier-ish parallel structures die: `_level_walls`,
      `_placed_walls`, `_wall_hits`, `_room_doors`, `_room_gates`,
      `_water_tiles`, `_bridged_tiles` replaced by cell queries;
      `RoomState` snapshots `cells` instead of four wall-ish fields;
      `_update_pressure_plates` stops rebuilding anything
- [ ] T5 — Renderer reads barriers/terrain from cells (sprite from barrier
      kind, crack overlay from `hits`); facade updated
- [ ] T6 — Unit tests: `tests/test_cells.py` (red-first model tests) +
      `tests/test_world.py` extended through the query path; perf tripwire
      extended with an Act 2 hard-difficulty (BFS) case
- [ ] T7 — All spec-0044 goldens **byte-identical**, full suite green,
      shadow assertion silent across the suite
- [ ] T8 — Shadow gate: user plays with `UGLYCRAFT_SHADOW=1`; **then** the
      `walls` grid, `_build_walls`, `_build_walls_multiroom`, and the
      shadow code are deleted (separate commit, after that play session)
- [ ] T9 — Docs: kb review Stage 3 status, feature-inventory, BL-35 note

## Motivation

`walls[c][r] = True` conflates border, level wall, placed wall, closed
gate, locked door, pushable block, and unbridged water. Every consumer
reverse-engineers the cause by scanning parallel structures
(`_register_bump`'s precedence chain, `_render_field`'s per-frame
re-classification), and every mutator must remember to call
`_build_walls_multiroom()` — correctness by convention, once per call
site (P1/P2, the BL-13/BL-14 bug class). After Stage 3 a cell *knows*
what it contains, passability is derived, and there is no rebuild call
to forget because there is no cached grid.

## Design

### The model (T1) — new module `cells.py`

Pygame-free (covered automatically by the 0045 import-isolation test,
which asserts over everything `world` pulls in).

```python
class Terrain(Enum):
    FLOOR = auto()
    WATER = auto()          # water_room: node behind the WATER edge

@dataclass
class Barrier:              # cell-filling fixture
    kind: str               # 'border' | 'reinforced' | 'stone' | 'wooden'
                            #   | 'placed' | 'door' | 'gate'
    colour: str | None = None    # doors
    channel: str | None = None   # gates: the gate_id (R2 channel name)
    hits: int = 0                # bump damage (stone/wooden/placed)

@dataclass
class Bridge:               # cell-filling fixture over WATER terrain
    pass

class RoomCells:
    """One room's terrain + fixtures.  Sparse: only non-floor terrain and
    cells with fixtures are stored; everything else is bare floor."""
    terrain(c, r) -> Terrain
    water_room(c, r) -> node | None        # from water_tile_room
    barrier(c, r) -> Barrier | None
    bridge(c, r) -> bool
    add/remove fixture, damage(barrier)    # mutators
    barriers(kind=None) -> iterator        # renderer / logic index
    build_from_room_data(room_data) -> RoomCells   # THE one parser
```

- **Barrier policies** (mirroring the generator's `EdgeType`, P5):
  `border`/`reinforced` never open; `stone` breaks after 3 bumps,
  `wooden` after 2, `placed` is player-installed (forge ogre breaks in
  2); `door(colour)` opens by key match on bump; `gate(channel)` blocks
  iff its channel is low. Border cells become explicit `border`
  barriers created by `build_from_room_data` (minus exit openings).
- **Breaking a wall = removing a fixture**; the floor beneath was always
  there. Placing a wall = installing a `placed` barrier. Bump damage
  lives on the barrier (`hits`), not in a side table.
- **Blocks stay where they are** (per-room `_room_blocks` lists): they
  are occupants (they move), and folding them into entities is a later
  stage. The passability query consults the list.
- **Plates, items, flame jets, dead squares stay as-is**: they never
  blocked movement, so they are outside this stage's scope (Stage 4
  moves behaviour into a dispatch table).
- **Gate state stays stored** in `_gate_open`, mutated only by
  `_update_pressure_plates` and `_reset_blocks`, exactly as today; a
  gate barrier blocks iff `channel not in world._gate_open`. Deriving
  pressed-ness at query time (kb review R1/R2) is **deferred to Stage
  4**, deliberately: derived gate state would change *when* a gate
  opening becomes visible to collisions (mid-enemy-loop instead of at
  the plate pass at the end of the tick) — a real behaviour change this
  behaviour-preserving stage must not make. What *does* die now is the
  wall rebuild after every plate change: passability reads `_gate_open`
  live, and since its mutation points are unchanged, every consumer
  sees exactly the state it saw before.

### The query (T3)

```python
# World
def blocked(self, c, r) -> bool:
    """True iff (c, r) cannot be walked on: out of bounds, a blocking
    barrier, unbridged water, or a pushable block."""
```

folded as: bounds → barrier present and blocking (gate consults
`_gate_open`) → terrain WATER without Bridge → block at (c, r).
This is the single replacement for every `self.walls[c][r]` read:

| Consumer | Change |
|---|---|
| `Player.try_move`, `Enemy.wander/move_toward/move_patrol` | signature: `walls` grid → `blocked(c, r)` callable (`move_bfs` takes none today — unchanged) |
| `_bfs_from` | query |
| `_spawn_treasure`, `_relocate_treasure` open-tile scans | query |
| `_verify_blocks`, `_try_push_block` push-target checks | query |
| `_place_wall`, `_act2_place` "am I on open floor" | query |
| `_try_auto_bridge` far-side check | query |
| `_respawn_enemy` fallback scan | query |
| `_register_bump` | precedence preserved (see below) |

`_register_bump` keeps today's exact precedence, re-pointed at the
model: door barrier → auto-open (key match); WATER terrain → auto-bridge
attempt; `border`/`reinforced` barrier → inert; gate barrier / block /
still-unbridged water → inert (`_is_unbumpable` is **deleted** — the
cell answers directly); breakable barrier → `hits += 1`, break at the
policy threshold (`WALL_BUMPS`). The if-chain itself survives until
Stage 4 turns it into `barrier.on_bump` dispatch; this stage only
changes where it looks, not what it decides — the golden sound traces
pin the order.

### Structures that die (T4)

| Old | Becomes |
|---|---|
| `_level_walls` {(c,r): wall_type} | `stone`/`wooden`/`reinforced` barriers |
| `_placed_walls` set | `placed` barriers |
| `_wall_hits` {(c,r): n} | `Barrier.hits` |
| `_room_doors` {rk: [(c,r,colour)]} | `door` barriers (per-room cells) |
| `_room_gates` {rk: {gid: (c,r)}} | `gate` barriers (channel=gid) |
| `_water_tiles` / `_water_tile_room` | WATER terrain (+ `water_room` attr) |
| `_bridged_tiles` {rk: set} | `Bridge` fixtures (persist via cells) |
| `walls` grid + `_build_walls` + `_build_walls_multiroom` | `blocked()` query (grid survives only as the T2 shadow until T8) |

Kept as-is: `_room_blocks` (+ `_room_blocks_initial`), `_gate_open`,
`_bridged_water_rooms` (a *rule* about rooms, not a tile property),
`_opened_doors` (render-only history), `_room_plates`, `_dead_squares`,
`_flame_jets`, `_tile_owner`, and all item lists.

`RoomState` shrinks: `level_walls`/`placed_walls`/`wall_hits`/`doors`
are replaced by one `cells` field (barriers carry their own damage and
door state); `enemies`/`treasures`/`materials`/`keys`/`blocks` stay.
`_enter_room` restores or builds `self.cells` (one `RoomCells` per
room, swapped on entry like the structures it replaces — rooms as live
objects is Stage 5).

### Renderer (T5)

`_render_field` classification becomes a read of the model: barrier
kind → sprite (`border_wall`, `wall`, `wall_wooden`, `wall_reinforced`,
`placed_wall`, door/gate sprites), `hits` → crack overlay, WATER
terrain + Bridge → water/bridge sprites. `_door_orient`'s reinforced
check reads barriers. Blit **order must stay exactly as today** — the
golden screenshots pin it. Facade: dead attributes leave
`_WORLD_ATTRS`; `cells` joins it. The two `tests/test_golden_act2.py`
assertions on `_placed_walls` are updated to cell queries (allowed test
edits; goldens untouched).

### Shadow-grid migration (T2, T8 — kb review §6.4)

Parallel change, never a flag-day:

1. **Dual-write**: mutators update the cell model *and* still trigger
   the old grid rebuild.
2. **Assert**: after every mutation and every room entry, when
   `UGLYCRAFT_SHADOW=1` (exported unconditionally by
   `tests/conftest.py`; available to `poe run` for the play gate),
   compare all 30×16 cells: `walls[c][r] == blocked(c, r)` — with
   occupant blocks factored out on both sides consistently.
   Any divergence raises immediately with the cell and both answers.
3. **Flip consumers** (T3) one group per commit under the assertion.
4. **Delete** (T8) the grid, the builders, and the shadow code — only
   after the assertion has been silent through the full suite **and**
   the user's play session. The deletion is its own commit so the
   entire migration remains bisectable.

### Tests (T6)

- `tests/test_cells.py`, red-first: `build_from_room_data` on a fixture
  room (barrier kinds, door colour, gate channel, water terrain, border
  with exit gaps); break/place/damage mutators; `blocked()` truth table
  incl. gate-open toggling and bridged water.
- `tests/test_world.py` additions: door open / gate cross / bridge /
  push driven through `World` with events asserted (these exist in
  golden form; the unit versions localise failures).
- Perf: `test_perf.py` gains an Act 2 hard-difficulty case (BFS floods
  the grid through the query every enemy tick — the plausible
  regression) with the same generous 5 s bound.

## Non-goals

- No behaviour dispatch table, no derived plate/channel state, no
  `hazard_at` field queries (Stage 4).
- No `Room` objects, no `RoomState` deletion, no global positions
  (Stage 5).
- Blocks stay lists; items/plates/flames/dead squares stay as they are.
- The generator (`levelgraph.py`/`levellayout.py`) is untouched; making
  the Sokoban solver consume this same passability query (the
  structural BL-14 fix) is the follow-up spec after this stage proves
  the query — noted in BL-14/BL-36.
- No behaviour fixes (BL-36 stays open; `_verify_blocks` keeps its
  semantics, only its reads change).

## Verification

1. `poe test` green with **zero golden diffs** and the shadow assertion
   active for the whole suite; no `UGLYCRAFT_REGOLD`.
2. `tests/test_cells.py` red-first, then green.
3. Manual gate, two steps: user plays with `UGLYCRAFT_SHADOW=1`
   (a divergence crashes loudly — silence is the sign-off for T8);
   after T8's deletion commit, a short normal play check.

## Done when:

- [ ] T1 — `cells.py` model in place, one parser from room data
- [ ] T2 — dual-write + shadow assertion on in the suite
- [ ] T3 — every `walls[c][r]` consumer reads `blocked()` / the model
- [ ] T4 — parallel wall structures deleted; `RoomState` carries `cells`
- [ ] T5 — renderer reads the model; facade updated
- [ ] T6 — new unit tests red→green; Act 2 perf case added
- [ ] T7 — suite green, goldens byte-identical, shadow silent
- [ ] T8 — user shadow-play done; grid + builders + shadow code deleted
- [ ] T9 — docs updated
