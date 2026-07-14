# CHANGELOG — UGLYCRAFT

Changes to **UGLYCRAFT**, the Python/pygame remake. The original 1996 DOS game
and its FPC/Linux port have their own changelog in
[`original/CHANGELOG.md`](original/CHANGELOG.md).

Versions are the repository's git tags. This changelog begins at **1.5**; the
history of releases 0.5–1.5 lives in the git tags. Spec references in
parentheses point at the design docs under [`spec/`](spec/).

---

## [Unreleased]

Everything below is the work since **1.5**, which shipped the complete Act 1
game and nothing more. The headline is **Act 2: ten procedurally generated
vault levels (11–20)** and the engine rebuild behind it.

Many of these areas were iterated on heavily — layout, placement rules, the
entrance mechanic and the push-block interactions each moved across a dozen or
more specs before they settled. Each note below describes the **settled**
result as it now stands, with the specs of the whole thread cited only as an
index rather than as separate deliverables.

### Act 2 & gameplay

- **Act 2 — "Beyond the Vault" (levels 11–20).** Procedurally generated
  multi-room, multi-grid vault levels, each regenerated from a per-level seed.
  (umbrella spec 0007.)

- **Level generator.** Settled pipeline: a room graph (`levelgraph.py`) with
  per-level feature sets is laid out (`levellayout.py`) onto one or more 30×16
  grids using a family of strategies (horizontal / vertical / off-centre / t /
  double-t / z / s / l / full_border) with zone packing and L-shaped rooms;
  several grids are joined by a Wilson spanning tree with corridors stitched
  across their borders (a single grid is handled as the degenerate "grid zero").
  Every level is proven solvable before it ships, and levels are generated lazily
  per seed behind a loading-screen progress bar. Placement of items, keys,
  plates, blocks and enemies converged on one set of rules — clearances, no empty
  rooms, nothing on the player-start tile, plates never at an entrance,
  room-size floors for enemies, no duplicate colour keys, and no silent dropping
  of locked/gated edges. Generation is deterministic and independent of process
  and hash seed. (specs 0008, 0010, 0013–0017, 0019, 0021, 0024–0026, 0028,
  0030, 0032–0036, 0040, 0042, 0049, 0054, 0055, 0057, 0058, 0060, 0061, 0065,
  0075.)

- **Crafting, inventory & credit economy.** Materials collected in the world bank
  toward block and bridge credits (two halves make a credit, carried across
  levels); a TAB inventory/crafting screen exposes the active recipes (Stone
  Wall, Bridge). Further content — Bell, Barricade, Portal Pair and Compass
  recipes, extra tools and pickups — is designed but gated off. (specs 0007,
  0037, 0073.)

- **Keys & locked doors.** Seven key colours shown in a HUD key strip; doors
  auto-open on bump and are modelled as **channel-latched barriers** (the open
  state is a latched channel, not a positional side-table). (specs 0007, 0030,
  0038, 0071, 0077.)

- **Push puzzles — blocks, pressure plates & gates.** Sokoban-style puzzles whose
  blocks latch gates open through a channel model; the generator only ships
  puzzles it can prove solvable. A block shoved out of its safe area lights a
  fuse and detonates (−500 pts), then respawns on a random free safe tile inside
  its own room. A block can never be placed on, pushed onto, or respawned onto a
  door, gate, border passage, or a tile holding a collectable. (specs 0011, 0035,
  0049, 0050, 0052, 0063, 0068, 0076, 0077, 0078, 0079.)

- **Water & bridges.** Water is solid until bridged; bumping it auto-crafts a
  bridge from planks — one bridge per water room, with per-grid bridged state —
  and the generator guarantees the planks are always reachable from the dry side.
  (specs 0009, 0012, 0027, 0029, 0041.)

- **Flame jets.** Rhythmic hazard tiles with a sweeping intensity cycle placed at
  the layout stage; the shield protects while they burn. (specs 0009, 0062.)

- **New enemies & wall types.** `PatrolEnemy` (waypoint patrols) and `ForgeOgre`
  (breaks placed walls, levels 16+). Walls come in three kinds: reinforced
  (indestructible), stone, and wooden. (spec 0007.)

- **Level entrance, grid entry & completion.** Settled across all 20 levels: the
  player starts next to the border at an entrance; grid-to-grid entry tiles
  reflect the source exit's type; collecting the last award **opens the
  entrance** gate, and walking out through it completes the level (replacing
  advance-on-pickup). The open door persists across death and plays a distinct
  "ta-daa" fanfare. Act 1 levels 1–10 gained hand-authored entrances and
  repositioned starts so the mechanic is uniform. Dying returns the player to the
  start room's spawn tile with the correct reset scope. (specs 0018, 0020, 0022,
  0039, 0053, 0056, 0064, 0066, 0067.)

- **Feedback & HUD.** A single **action-denied** sound covers every refused
  action (no credit, blocked tile, respawn tile, door/gate tile, border passage);
  the HUD gained the key strip and block/bridge credit counters, and the overlay
  message box now fits its text to the box. (specs 0031, 0038, 0041, 0059, 0071,
  0072, 0074.)

### Engine & tooling

- **Gameplay rules extracted into a pygame-free core.** All rules live in
  `world.py`, driven by a typed event stream; `game.py` is presentation only.
  Collision is a **query** over a layered terrain / barrier / fixture / item cell
  model (`cells.py`) — the cached walls grid and the old wall-builders are gone.
  Rooms are live objects that persist by identity; a content registry parses room
  data into cells; plates, gates, doors and the entrance all resolve through a
  global channel set; and every level (Act 1 included) is a multiroom level on
  one code path. (specs 0044–0048, 0050, 0051, 0052.)

- **Deterministic generation & tests.** Generation is reproducible regardless of
  process or hash seed (spec 0054). The suite gained a characterization harness
  with golden-master traces (spec 0044) plus a pygame-free world-model tier, runs
  in parallel (spec 0069), and generation was moved off the hot path (spec 0070);
  `--dump-level` renders any generated level as ASCII for inspection.

---

## [1.5] – 2026-06-21

Last release before this changelog. Shipped the complete **Act 1** game: ten
hand-authored levels, ogre chase AI (greedy on easy, BFS on hard) with a boss on
level 10, the shield power-up, scoring/lives/death, procedural sound effects and
per-level music, the title screen with the history of UGLI, and a persistent
top-10 high-score table. Version history for releases 0.5 through 1.5 is
recorded in the git tags.
