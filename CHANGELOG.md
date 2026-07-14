# CHANGELOG — UGLYCRAFT

Changes to **UGLYCRAFT**, the Python/pygame remake. The original 1996 DOS game
and its FPC/Linux port have their own changelog in
[`original/CHANGELOG.md`](original/CHANGELOG.md).

Versions are the repository's git tags. This changelog begins at **1.5**; the
history of releases 0.5–1.5 lives in the git tags. Spec references in
parentheses point at the design docs under [`spec/`](spec/).

---

## [Unreleased]

Everything below is the work since **1.5** — which shipped the complete Act 1
game and nothing more. The headline is **Act 2: ten procedurally generated
vault levels (11–20)**, together with the engine rebuild that made it possible.
None of this has been released yet.

### Added

#### Act 2 — "Beyond the Vault" (levels 11–20) (spec 0007)

- Procedurally generated **multi-room, multi-grid** levels: each level is a
  graph of rooms laid out onto one or more 30×16 grids joined by border
  passages, regenerated from a per-level seed.
- **Crafting & inventory** (`crafting.py`): materials, tools, recipes, and a TAB
  inventory/crafting screen. Active recipes are Stone Wall and Bridge; further
  content (Bell, Barricade, Portal Pair, Compass, extra tools/pickups) is
  designed and gated off behind constants (spec 0037).
- **Keys & locked doors**: seven key colours, auto-open on bump, with a HUD key
  display (specs 0038, 0071) and placement rules (spec 0030).
- **Pushable blocks, pressure plates, and channel-latched gates**: Sokoban-style
  push puzzles whose blocks latch gates open via a channel model (specs 0050,
  0052); plate/block placement is validated for solvability at generation time.
- **Water & bridges**: water is solid until bridged; bumping water auto-crafts a
  bridge from planks, one bridge per water room, with per-grid bridged state
  (specs 0009, 0027, 0029, 0041).
- **Flame jets**: rhythmic hazard tiles with a sweeping intensity cycle; the
  shield protects while active (spec 0009).
- **New enemies**: `PatrolEnemy` (waypoint patrols) and `ForgeOgre` (breaks
  placed walls, levels 16+).
- **Wall types**: reinforced (indestructible), stone, and wooden.

#### Level generator (`levelgraph.py`, `levellayout.py`)

- **Graph model & generation** — `Node`/`Edge`/`LevelGraph`, per-level feature
  sets, branching world graph (specs 0008, 0010, 0017).
- **Layout strategies** — horizontal / vertical / off-centre / t / double-t /
  z / s / l / full_border, zone assignment and packing, room-count-driven
  strategy selection (specs 0013, 0015, 0019, 0021, 0025, 0040), plus L-shaped
  rooms with arbitrary floor-tile sets (spec 0014).
- **Sokoban push-puzzle placement** — backward-BFS solver, dead-square analysis,
  and playability validation (spec 0011).
- **Playability validation** — every generated level is proven solvable,
  including plank-reachability for water challenges (spec 0029).
- **Multi-grid super-grid** — Wilson spanning tree over grids, BORDER edges, and
  corridor continuation stitched across grid borders (specs 0026, 0017, 0042).
- **Lazy per-level generation** — levels are generated on demand and cached, with
  a **loading screen and progress bar** (spec 0028).

#### Shared mechanics (all 20 levels)

- **Entrance-exit level completion** (spec 0066): collecting the last award now
  *opens the entrance* (a gate on a reserved channel); the level ends when the
  player walks out through the open door, instead of advancing on pickup. The
  door persists across death and plays a distinct "ta-daa" fanfare on opening.
- **Death respawn reset** (spec 0067): dying returns the player to the start
  room's spawn tile with the correct per-level reset scope.
- **Exploding wedged blocks** (spec 0068): a push block shoved out of its safe
  area lights a fuse and detonates (−500), then respawns on a random free tile
  inside its own room's safe area (spec 0076).
- **Action-denied sound** (spec 0074): a single feedback cue for every refused
  action (no credit, blocked tile, respawn tile, door/gate tile, border passage).
- **Act 1 fixed entrance doors** (spec 0064): hand-authored entrance and
  repositioned player/enemy starts for levels 1–10, so the completion mechanic
  applies uniformly across all 20 levels.

#### Tooling & tests

- **Characterization harness + golden-master traces** (spec 0044): deterministic
  end-to-end traces of gameplay, re-recorded only with `UGLYCRAFT_REGOLD=1`.
- **World-model unit tests**: a pygame-free tier accumulated through the refactor
  (specs 0045–0052) for fine-grained failure localisation.
- **Parallelized test suite** (spec 0069) and a **generation hot-path
  optimisation** (spec 0070).
- **`--dump-level` ASCII export** for inspecting generated layouts.

### Changed

#### Engine architecture

- **World extraction** (spec 0045): all gameplay rules moved into a **pygame-free
  `world.py`**; `game.py` is now presentation only, driven by a typed event
  stream. The observable event sequence is byte-identical to the pre-split code.
- **Layered cell model** (spec 0047): collision is now a **query** over a layered
  terrain/barrier/fixture/item model (`cells.py`); the cached walls grid and both
  `_build_walls*` builders are gone.
- **Solver / passability unification** (spec 0048): the generator's solver and the
  runtime share one passability definition; the block-regeneration net is a
  fresh-entry-only last resort.
- **Live Room objects** (spec 0051): rooms persist by identity (`rooms.py`); the
  old `RoomState` snapshot model is gone.
- **Content registry** (spec 0052): a single parser table turns room data into
  cell fixtures/occupants.
- **Behaviour dispatch via channels** (spec 0050): plates, gates, doors, and the
  level entrance all resolve their open state through a global channel set.
- **Deterministic, process-independent generation** (spec 0054): generation no
  longer depends on set-iteration order or `PYTHONHASHSEED`.
- **Act 1 as one room** (spec 0046): every level is now a multiroom level; Act 1
  is wrapped as a single room, so one code path serves both acts.

#### Gameplay & presentation

- Act 1 level completion switched from pickup-advance to the entrance-exit walk
  (spec 0066); Act 1 enemies are confined to interior tiles so they never step on
  the open entrance.
- HUD gained an Act 2 key-inventory strip and a bridge/block credit counter
  (specs 0038, 0041, 0071, 0072); the overlay message box grew a fit-to-text
  layout (specs 0031, 0059).
- Doors are modelled as channel-latched barriers rather than a positional
  side-table (spec 0077).

### Fixed

- Reinforced walls are now genuinely indestructible (spec 0023).
- z-strategy zone corner gap closed (spec 0024); L-corridor orientation
  corrected (spec 0019).
- Player spawn no longer lands on/next to a wall (spec 0018); grid-entry tile now
  reflects the source exit type (specs 0039, 0056); entrance/player-start
  anchoring across grids (spec 0053).
- Generator content quality: no empty rooms (spec 0034); items/keys never on the
  player-start tile (specs 0033, 0057); pressure plates never at an entrance and
  with placement clearance (specs 0035, 0049); enemies respect a room-size floor
  and award placement (specs 0036, 0058); Act 2 room scaling (spec 0060);
  duplicate colour keys resolved (spec 0075).
- Doors on locked/gated edges are never silently elided (specs 0061, 0065).
- Push-block interactions: a block never respawns onto an unsafe tile
  (spec 0076), and is never placed on / pushed onto / respawned onto a door, gate,
  border passage, or collectable-item tile (specs 0077, 0078, 0079).
- Single-grid levels handled as "grid zero" without multi-grid stitching
  (spec 0055).

---

## [1.5] – 2026-06-21

Last release before this changelog. Shipped the complete **Act 1** game: ten
hand-authored levels, ogre chase AI (greedy on easy, BFS on hard) with a boss on
level 10, the shield power-up, scoring/lives/death, procedural sound effects and
per-level music, the title screen with the history of UGLI, and a persistent
top-10 high-score table. Version history for releases 0.5 through 1.5 is
recorded in the git tags.
