# UGLYCRAFT — Feature Inventory

Hierarchical map of every implemented aspect of the Python game, with links to
the specs that exist for each. Written as groundwork for extending the
automated test suite beyond the level generator (which is already covered —
see §7).

Spec links are relative to this file (`../spec/…`). Aspects with no spec
predate the spec-first workflow; their reference documentation is the linked
`kb/` article.

→ Mechanics detail: `kb/uglycraft-mechanics.md` · Display: `kb/uglycraft-display.md`
· Sound: `kb/uglycraft-sound.md` · Generator: `kb/architecture.md` + `kb/requirements.md`

---

## 1. Application shell & presentation

- **1.1 Window, integer scaling, fullscreen** — `main.py` (`best_scale`,
  `present`, F11). No spec for the original implementation; the
  native-resolution rework (GamePi 800×480) is spec-committed but not yet
  implemented: [0043](../spec/0043-native-resolution.md).
- **1.2 Game state machine** — `game.py` (`TITLE`, `DIFFICULTY`,
  `LEVEL_INTRO`, `PLAYING`, `PAUSED`, `WIN`, `GAME_OVER`, `ENTER_SCORE`,
  `SHOW_SCORES`, `PLAY_AGAIN`, terminal `QUIT_GAME`; `STORY` exists but is
  unreachable). No spec; diagram in `kb/uglycraft-mechanics.md`.
  Since spec [0045](../spec/0045-world-extraction.md), `game.py` is
  presentation only: all gameplay rules live in the pygame-free `world.py`,
  connected by a typed event stream (→ `kb/world-model-review.md` Stage 1).
- **1.3 Rendering** — `sprites.py` (all sprites procedural via `pygame.draw`,
  no image files), boss 4-frame animation, title-screen bouncing ogres, red
  death flash, transition flash. No spec; `kb/uglycraft-display.md`.
- **1.4 HUD** — single status row (score, level, lives, SEEK, difficulty/BOSS
  tag, shield timer, wall credits) plus Act 2 additions. Specs:
  [0031](../spec/0031-overlay-box-overflow.md) (overlay message box),
  [0038](../spec/0038-key-inventory-display.md) (key display),
  [0041](../spec/0041-auto-craft-bridge.md) (bridge counter),
  [0043](../spec/0043-native-resolution.md) (font-fit rule, not implemented).
- **1.5 Loading screen with progress bar** — lazy Act 2 generation progress
  callback: [0028](../spec/0028-lazy-level-generation.md).
- **1.6 Title-screen history text** — `translations/history_en.txt`,
  `_load_history_text` + word wrap. No spec.

## 2. Act 1 core gameplay (`world.py`, `entities.py`)

- **2.1 Player movement & key repeat** — tile-grid movement, first-press
  immediate, 180 ms initial repeat delay, level-scaled repeat interval,
  per-key bump-consumed flag. No spec; `kb/uglycraft-mechanics.md`.
- **2.2 Speed scaling** — `factor = 1.07 ** (10 - level)`; boss fixed
  `BOSS_MOVE_MS = 82`. No spec.
- **2.3 Wall breaking & placement** — 3 bumps break a wall, 2 breaks earn one
  placement credit (carries across levels), crack sprites, credit refund for
  surviving placed walls on level advance. No spec (Space placement rework
  touched in [0001](../spec/0001-shield-rework.md)).
- **2.4 Scoring, lives, death** — per-item points, flat 500 death penalty,
  9 starting lives, +1 per level, final score `score * max(1, lives)`. No
  spec; `kb/uglycraft-mechanics.md` + `kb/findings.md` (Pascal differences).
- **2.5 Shield** — 250 pts, 10 s, consumed on catch, enemy respawn ≥ 8 tiles:
  [0001](../spec/0001-shield-rework.md).
- **2.6 Treasures & Crown** — item sequence per level, random spawn on open
  tiles, Crown fixed at level 10, boss relocates non-Crown items. No spec.
- **2.7 Enemy AI** — greedy chase (easy), BFS chase (hard), boss, wander,
  post-catch BFS respawn: [0002](../spec/0002-ogre-enemies.md) (ogre types and
  sprites); core chase logic has no spec.
- **2.8 Level progression** — advance/death/game-over bookkeeping, what
  carries over. No spec; `kb/uglycraft-mechanics.md`.
- **2.9 Hand-authored levels 1–10** — `levels.py` wall helpers; layouts
  documented in `kb/uglycraft-levels.md`. No spec.
- **2.10 High scores** — `hiscore.py` top-10 persistence to `uglycraft.hsc`,
  qualify check, name entry. No spec.

## 3. Act 2 gameplay (runtime side; umbrella spec [0007](../spec/0007-act2-beyond-the-vault.md))

- **3.1 Multi-room / multi-grid runtime** — live `Room` objects
  (`rooms.py`, persist by identity since spec
  [0051](../spec/0051-room-objects.md); `RoomState` is gone),
  `_enter_room` pointer swap, exit detection.
  Since spec [0046](../spec/0046-act1-as-one-room-act2.md) *every* level is
  a multiroom level (Act 1 is wrapped as one room keyed `None`), and since
  spec [0047](../spec/0047-layered-cell-model.md) collision is a **query**
  (`World.blocked` over the `cells.py` layered model) — the walls grid and
  both `_build_walls*` builders are gone, so the historical wrong-builder
  trap has no code left to occur in. Specs:
  [0007](../spec/0007-act2-beyond-the-vault.md),
  [0027](../spec/0027-bridge-state-per-grid.md) (per-grid bridge state).
- **3.2 Wall types** — reinforced (indestructible), stone, wooden:
  [0007](../spec/0007-act2-beyond-the-vault.md),
  [0023](../spec/0023-fix-reinforced-walls-indestructible.md).
- **3.3 Materials, crafting, inventory UI** — `crafting.py` (materials,
  tools, recipes, `Inventory`), TAB screen: [0007](../spec/0007-act2-beyond-the-vault.md);
  unfinished content gated behind constants:
  [0037](../spec/0037-gate-unfinished-crafting.md). Active recipes: Stone
  Wall, Bridge.
- **3.4 Keys & locked doors** — 7 key colours, auto-open on bump, HUD key
  display: [0007](../spec/0007-act2-beyond-the-vault.md),
  [0038](../spec/0038-key-inventory-display.md); placement side
  [0030](../spec/0030-key-placement-fixes.md).
- **3.5 Pushable blocks, pressure plates, gates** — `Block` occupants +
  plate fixtures + channel latch (`_try_push_block`, `_latch_channels`,
  specs [0050](../spec/0050-behaviour-dispatch-channels.md)/
  [0052](../spec/0052-content-registry.md)); the `_verify_blocks` net is a
  fresh-entry-only last resort since [0048](../spec/0048-solver-passability-unification.md)
  (BL-14 fixed — water-caused stuck blocks no longer generate):
  [0007](../spec/0007-act2-beyond-the-vault.md),
  [0011](../spec/0011-push-puzzle-placement.md),
  [0035](../spec/0035-plate-not-at-entrance.md).
- **3.6 Water & bridges** — water solid until bridged, auto-craft bridge on
  bump, one bridge per water room, per-grid bridged tiles:
  [0009](../spec/0009-phase3-hazards.md),
  [0012](../spec/0012-bug-open-door-draw-and-planks-count.md),
  [0029](../spec/0029-water-challenge-fixes.md),
  [0041](../spec/0041-auto-craft-bridge.md),
  [0027](../spec/0027-bridge-state-per-grid.md).
- **3.7 Flame jets** — rhythmic intensity (`_flame_tile_intensity`), shield
  protects: [0009](../spec/0009-phase3-hazards.md).
- **3.8 Act 2 enemies** — `PatrolEnemy` (waypoints), `ForgeOgre` (breaks
  placed walls, levels 16+): [0007](../spec/0007-act2-beyond-the-vault.md).
- **3.9 Level entrance & grid entry** — border-adjacent player start,
  entrance sprite, entry tile reflects source exit type:
  [0022](../spec/0022-level-entrance.md),
  [0018](../spec/0018-player-spawn-wall.md),
  [0020](../spec/0020-enemy-at-grid-entry.md),
  [0039](../spec/0039-entry-tile-exit-type.md).

## 4. Level generation (`levelgraph.py`, `levellayout.py`, `levels.py`)

- **4.1 Graph model & generation** — `Node`/`Edge`/`LevelGraph`,
  `LevelGraphBuilder`, feature sets per level:
  [0008](../spec/0008-level-graph-system.md),
  [0010](../spec/0010-level-gen-refactor.md),
  [0017](../spec/0017-large-levels.md) (world graph, branching).
- **4.2 Playability validation** — `validate_playability` incl. WATER
  plank-reachability gate: [0029](../spec/0029-water-challenge-fixes.md);
  model-boundary analysis in `kb/architecture.md` (BL-13).
- **4.3 Layout strategies** — horizontal/vertical/off-centre/t/double-t/
  z/s/l/full_border, zones, packing:
  [0013](../spec/0013-level-layout-expansion.md),
  [0015](../spec/0015-layout-t-chain-rework.md),
  [0019](../spec/0019-l-corridor-orientation.md),
  [0024](../spec/0024-fix-z-zone-corner-gap.md),
  [0025](../spec/0025-greedy-zone-assignment.md),
  [0021](../spec/0021-room-count-driven-strategy.md),
  [0040](../spec/0040-simple-early-layouts.md).
- **4.4 Room shapes** — L-shaped rooms, `floor_tiles` sets:
  [0014](../spec/0014-room-shapes.md).
- **4.5 Level density & room content** —
  [0016](../spec/0016-level-density.md),
  [0034](../spec/0034-no-empty-rooms.md).
- **4.6 Push-puzzle placement (Sokoban solver)** — backward BFS,
  `validate_push_puzzles`, dead-square analysis:
  [0011](../spec/0011-push-puzzle-placement.md).
- **4.7 Item / key / enemy placement** — priority order, corridor spill,
  barrier↔prerequisite coupling, closet carving:
  [0030](../spec/0030-key-placement-fixes.md),
  [0032](../spec/0032-multigrid-closet-drops.md),
  [0033](../spec/0033-no-item-on-player-start.md),
  [0035](../spec/0035-plate-not-at-entrance.md),
  [0036](../spec/0036-enemy-room-size-floor.md).
- **4.8 Multi-grid super-grid** — spanning tree
  ([0026](../spec/0026-wilson-spanning-tree.md)), BORDER edges, corridor
  continuation across borders ([0042](../spec/0042-border-corridor-stitch.md)),
  stitching, border barriers: [0017](../spec/0017-large-levels.md).
- **4.9 Lazy per-level generation** — `get_level` cache, per-level seed,
  `regenerate_level`: [0028](../spec/0028-lazy-level-generation.md).

## 5. Sound & music (`sounds.py`)

- **5.1 SFX** — 14 procedural effects, FM synthesis + physical impact + tanh
  saturation: [0003](../spec/0003-sounds.md),
  [0004](../spec/0004-sfx-redesign.md).
- **5.2 Music** — 10 level tracks + title + win, 8-bar 8-voice loops,
  per-level themes, channel-0 dedup: [0005](../spec/0005-music-themes.md).
- **5.3 Graceful degradation** — silent no-op if numpy/mixer unavailable.
  No spec.

## 6. Packaging, build, deploy (not gameplay — out of test-suite scope)

- poe tasks: Linux/Windows builds, itch.io deploy, AUR release + git
  packages: [0006](../spec/0006-arch-packaging.md); tables in root
  `CLAUDE.md`.

## 7. Automated test coverage

`poe test` runs `pytest tests/ -v` — two tiers since spec 0044:

**Generator unit tests** (§4):

| Test file | Covers |
|---|---|
| `tests/test_graph_building.py` | 4.1 graph generation |
| `tests/test_world_graph.py` | 4.8 spanning tree / world graph |
| `tests/test_layout.py` | 4.3 layout strategies, wall derivation |
| `tests/test_room_shapes.py` | 4.4 room shapes |
| `tests/test_sokoban.py` | 4.6 push-puzzle solver |
| `tests/test_placement_rules.py` | 4.7 placement rules (0033/0034/0035/0036) |
| `tests/test_key_placement.py` | 4.7 key placement (0030) |
| `tests/test_node_drops.py` | 4.7 closet/node drops (0032) |
| `tests/test_water_challenge.py` | 4.2/3.6 water solvability (0029) |
| `tests/test_act2_solvability.py` | 4.2 end-to-end solvability |
| `tests/test_border_continuity.py` | 4.8 border stitching (0042) |
| `tests/test_lazy_levels.py` | 4.9 lazy generation (0028) |

**Gameplay characterization** (§§1–3; golden-master traces via
`tests/harness.py`, spec [0044](../spec/0044-characterization-harness.md) —
re-record only with `UGLYCRAFT_REGOLD=1`):

| Test file | Covers |
|---|---|
| `tests/test_harness.py` | harness self-tests, seed/trace determinism |
| `tests/test_golden_act1.py` | §2: walks L1–10, wall break/place, shield, death/penalty, shielded catch, game over, advance, pause |
| `tests/test_golden_act2.py` | §3: door/key, plate/block/gate + reset, water/planks/craft/bridge, flames + shield, grid transition persistence, forge ogre, patrol; seeded L11/L13 walks |
| `tests/test_render.py` | §1.3/1.4: render smoke (BL-33) + golden screenshots (fragile tier, on trial) |
| `tests/test_perf.py` | throughput tripwire (2000 ticks < 5 s) |

Still without automated coverage: `hiscore.py` (file I/O deliberately kept
out of tests), sound *content* (`sounds.py` waveforms — only trigger keys
are traced), and the menu flows outside the traced states. Root-level
`test_levelgraph.py` remains an older unittest suite not collected by
`poe test`.

Root-level `test_levelgraph.py` is an older unittest-style suite covering the
graph/layout basics; it is **not** run by `poe test` (which only collects
`tests/`).

## 8. Designed but not implemented (for completeness)

From [0007](../spec/0007-act2-beyond-the-vault.md) /
[0009](../spec/0009-phase3-hazards.md), still absent from the code:

- Switches (levers, buttons) and machines (drawbridge, flame valve, conveyor
  belt, piston).
- Player carried by water flow (water is simply solid until bridged).
- `STAIRS` edge type (enum exists; no generation or runtime support — a
  sprite-fallthrough bug draws stairs at some passages, see `kb/findings.md`).
- Act 2 boss (Forge Master, level 20).
- Gated crafting content: Bell / Barricade / Portal Pair / Compass recipes,
  Hammer / Chisel / Runestone tools, Scrap Metal / Forge Crystal pickups
  ([0037](../spec/0037-gate-unfinished-crafting.md)).
- `STORY` game state (renderer exists, no transition in).
