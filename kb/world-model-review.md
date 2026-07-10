# World Model — Software Engineering Review

Design review of the runtime world representation (2026-07-10), motivated by
two goals: making gameplay logic **testable** and making it **cheap to add new
elements and interactions** (levers, machines, stairs, Act 2 boss — the §8
items in `kb/feature-inventory.md`).

→ Feature map: `kb/feature-inventory.md` · Mechanics: `kb/uglycraft-mechanics.md`
· Generator side: `kb/architecture.md`

---

## 1. What the world model is today

The "world" at runtime is spread across four representations:

1. **`Game.walls`** — a 30×16 boolean collision grid, rebuilt wholesale by
   `_build_walls()` / `_build_walls_multiroom()` after *every* mutation
   (door opened, gate toggled, block pushed, bridge built, wall broken/placed).
2. **~18 parallel structures on `Game`** — `_level_walls`, `_placed_walls`,
   `_wall_hits`, `_room_treasures`, `_room_materials`, `_room_keys`,
   `_room_doors`, `_room_blocks`, `_room_blocks_initial`, `_room_plates`,
   `_room_gates`, `_gate_open`, `_opened_doors`, `_bridged_tiles`,
   `_bridged_water_rooms`, `_water_tiles`, `_water_tile_room`,
   `_dead_squares`, `_flame_jets`, `_tile_owner`. Keying is inconsistent:
   some are `{room_key: list}`, some hold only the current room and are
   swapped on `_enter_room` (`_water_tiles`, `_flame_jets`, `_level_walls`),
   some are global sets embedding the room in the tuple
   (`_opened_doors = {(room_key, c, r, color)}`).
3. **`RoomState`** (`rooms.py`) — a second, *partial* snapshot type
   (9 fields), hand-copied field-by-field in both directions by
   `_save_room_state` / `_enter_room`. Plates, gates, bridges, water are
   **not** in it — they persist via the other idiom. Two persistence
   mechanisms coexist for one concept.
4. **The level dict** — untyped nested dicts from `build_level_dict` /
   `levels.py`, with two schema variants (Act 1: flat, `walls` may be a set;
   Act 2: `rooms` of dicts with ~14 keys). `parse_level_walls` papers over
   the set-vs-dict split. Element records are positional tuples of varying
   arity — enemy starts are `(c,r)` **or** `(c,r,etype)`, sniffed with
   `len(edata) >= 3`.

## 2. Pain points

### P1 — The boolean grid erases *why* a tile blocks

`walls[c][r] = True` conflates border, level wall, placed wall, closed gate,
locked door, pushable block, and unbridged water. Every consumer must
reverse-engineer the cause by scanning the parallel structures:
`_register_bump` re-checks border → door → bridge → reinforced →
`_is_unbumpable` (linear scans of doors/gates/blocks); `_render_field`
re-derives the same classification per frame.

This is the structural root of the **BL-13 class of bugs**: the Sokoban
solver, `validate_push_puzzles`, and the runtime each rebuild passability
from *different subsets* of the structures and disagree (water). Any future
element that blocks conditionally will re-create this bug class, once per
consumer that forgets it.

### P2 — Full-rebuild invalidation is a bug generator

Every mutator must remember to call `_build_walls_multiroom()` (never
`_build_walls()` — the known trap where Act 2 features vanish). Correctness
depends on N call sites each remembering; forgetting is invisible until a
collision goes wrong.

### P3 — Adding one element type costs ~10 touch points

A new interactive element (e.g. a lever) currently requires edits in:
level-dict schema (`levellayout.py`), the `_start_level` gathering loop,
both branches of `_enter_room` (fresh + restore), `RoomState.__slots__` +
`__init__` + `_save_room_state`, `_build_walls_multiroom` (if it blocks),
`_is_unbumpable` / `_register_bump` or the SPACE dispatch (if interactable),
`_update_playing` (if it ticks), `_render_field` (a new hand-written loop),
and `sprites.py`. This is the direct answer to "why is it hard to add
elements": behaviour is encoded as scattered if-chains and per-type loops,
not as a property of the element.

### P4 — Act 1 / Act 2 fork (`_is_multiroom`) in ~20 places

`if not self._is_multiroom: return` guards, forked treasure logic in
`_update_playing`, forked wall builders, forked `_lose_life`. Attributes
like `_water_tiles` and `_current_room_data` exist only on one path, so
other code defensively `getattr(self, '_water_tiles', set())` — or forgets
to: `_render_field` reads `self._current_room_data` unconditionally
(game.py:1230), which **crashes every Act 1 render** on current main
(regression in `04be23e`, post-v1.5; filed as a P1 backlog item). The fork
is exactly the kind of latent branch a conditional attribute model produces.

### P5 — Type information the generator had is erased at the boundary

`build_level_dict` flattens `EdgeType` into side effects (a hole in the
wall, a door tuple, a water list). The runtime no longer knows what kind of
passage anything is — which is why the staircase sprite is drawn at
*ordinary* border exits (`kb/findings.md` bug): rendering keys on "is an
exit" because "is a staircase" no longer exists at runtime. Implementing
real STAIRS, or any new edge type, will fight this erasure again.

### P6 — Stringly-typed seams, parsed repeatedly

Exit keys `'left_7'` are built and `rsplit('_', 1)`-parsed in three places
(`find_exit`, `_build_walls_multiroom`, `_render_field`). Sprite keys are
composed by f-string and silently skipped when absent (`if dkey in sp:`) —
a typo renders nothing rather than failing. Enemy types are bare strings.

### P7 — The world is trapped inside `Game`

`Game` owns the pygame surface, fonts, sprites, sounds, input, state
machine, *and* all world state and rules. Testing `_try_push_block` or the
plate/gate logic requires constructing a `Game` with a real
`pygame.Surface` and a `SoundManager`. `sounds.play(...)` calls are
embedded inside world mutators, so rules and presentation are inseparable.
This is the single biggest obstacle to the gameplay test suite.

## 3. Refactoring direction (staged, each stage shippable)

### Stage 1 — Extract `World` from `Game`  ← do this first

New module (e.g. `world.py`): a `World` class owning player position,
enemies, rooms, inventory, and all world mutation rules — **no pygame
import**. `Game` keeps the state machine, input translation, rendering,
sound. Instead of calling `sounds.play` inline, `World` appends typed
events (`WallBroken`, `DoorOpened`, `PlayerCaught`, `LevelComplete`, …) to
an event list; `Game` drains it and maps events → sounds/flash/music.

Payoff: `World.from_level_dict(get_level(n))` is constructible in a plain
pytest; tests drive `world.step(direction)` and assert on state + events.
The event list doubles as the natural test observation point. **All later
stages then happen under test coverage.**

### Stage 2 — Act 1 becomes a one-room Act 2 level

Wrap Act 1 dicts as `{'rooms': {'main': …}, 'start_room': 'main'}` and
delete the `_is_multiroom` fork wholesale. The only genuinely different
mechanic — sequential random treasure spawning vs pre-placed loot — becomes
a per-level rule (`spawn_mode: 'sequential' | 'preplaced'`), not a global
code fork. Kills P4 (and the class of bugs behind the Act 1 render crash).

### Stage 3 — Authoritative tile map

Replace the parallel dicts with one map per room:
`tiles: dict[(c,r), Tile]` where `Tile` carries `kind` + params (wall type,
hit count, door colour, gate id, water room, plate gate id, …). Items
(treasures/materials/keys) live in an `items: dict[(c,r), Item]` layer;
enemies stay an entity list. Passability becomes a *query*
(`tile.blocks(world_state)`) instead of a cached boolean grid — no rebuild
calls to forget (P1, P2). Critically, the generator's Sokoban solver and
`validate_push_puzzles` consume the **same** passability function, closing
the BL-13 model-mismatch class structurally instead of patching water in.

### Stage 4 — Behaviour dispatch table

Register tile kinds in a table:
`TILE_KINDS[kind] = TileSpec(blocks, on_bump, on_enter, pushable, sprite)`.
`_register_bump`'s if-chain, the `_collect_*` sequence, the push special
case, and `_render_field`'s per-type loops collapse into generic dispatch.
Adding a lever = one `TileSpec` + one sprite function + generator placement
(P3 drops from ~10 touch points to ~3). Keep the passage/edge type in the
room data (fixes the stairs-sprite fallthrough as a side effect, P5).

### Stage 5 — `Room` as a live object

A `Room` dataclass owns its tiles/items/enemies. Rooms persist by identity
— `_enter_room` swaps the active room pointer; `RoomState`,
`_save_room_state`, and the fresh/restore double branch are deleted. The
asymmetric two-idiom persistence (P3's worst part) disappears.

### Level dict stays — as a serialization format only

The dict is a fine generator/hand-authoring boundary. Parse it **once**
into typed objects (`World.from_level_dict`); the stringly schema (P6) then
lives in exactly one parser, and tuple-arity sniffing is replaced by
dataclasses at the boundary.

## 4. Ordering rationale

Stage 1 before everything: it is small (mostly moving code + introducing
events), it unlocks the gameplay test suite this review was motivated by,
and every subsequent stage is a behaviour-preserving refactor that wants
tests watching it. Stages 2–5 are then independent commits, roughly in
order of pain relieved per effort. Stage 3 is the load-bearing one — it is
what makes "more elements and interactions" cheap and what unifies the
solver/runtime world view.
