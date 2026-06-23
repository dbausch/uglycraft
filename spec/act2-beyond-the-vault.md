# Act 2: Beyond the Vault

## Status

- [ ] Room transitions (2-3 rooms per level, border openings, state persistence)
- [ ] Level architecture (reinforced / stone / wooden walls)
- [ ] Pre-placed treasures with LOOT x/y HUD
- [ ] Materials system (rocks, planks, scrap metal, forge crystals)
- [ ] Tools system (hammer, chisel, runestone - found, permanent, unlock recipes)
- [ ] Inventory / crafting screen (TAB, pauses game)
- [ ] Recipes (stone wall, bridge, bell, reinforced barricade, portal pair, compass)
- [ ] SPACE dispatch (place item / use key on door / toggle switch)
- [ ] Shield protects against flame jets
- [ ] Locked doors + colour-coded keys
- [ ] Pushable blocks (indestructible, player-only)
- [ ] Pressure plates + gates
- [ ] Water streams (visible carry to drain)
- [ ] Flame jets (rhythmic on/off, blocked by walls/blocks)
- [ ] Switches: levers (toggle) and buttons (momentary, 3s)
- [ ] Machines: gate, drawbridge, flame valve, conveyor belt, piston
- [ ] Patrol guard enemy (fixed path, predictable)
- [ ] Forge ogre enemy (chaser, breaks placed walls in 2 bumps)
- [ ] Levels 11-20 designed and playable
- [ ] Act 2 boss: The Forge Master (level 20)
- [ ] Level randomization (seeded variation per playthrough)

---

## Overview

After defeating the first boss and claiming the Crown on level 10, the player
discovers passages to the **Ogre Forge** - an underground complex where ogres
are manufactured. Act 2 spans levels 11-20 with exploration, environmental
puzzles, crafting from found materials, machines, and a second boss.

Levels 1-10 remain exactly as they are. All new mechanics activate only in
Act 2.

---

## Design Principles

1. **No attacking enemies.** The core identity is evasion, obstacle-building,
   and puzzling. No turrets, no offensive items, no combat gadgets.
2. **No projectiles.** Environmental hazards (flame jets, water streams) replace
   ranged threats. They are rhythmic and predictable - pattern-based, not
   reaction-based.
3. **Resources from exploration.** Materials are found at fixed positions in
   rooms (chests, rubble, debris), not dropped by breaking walls.
4. **Materials relate to products.** Rocks → stone structures. Planks → wooden
   structures. Metal → mechanical devices. Crystals → magical items.
5. **Crafting is deliberate.** The inventory screen (TAB) pauses the game.
   Crafting is a puzzle decision, not a real-time stress moment.
6. **Permanent architecture.** Reinforced (indestructible) interior walls form
   corridors, chambers, and pillars. Rooms feel like built spaces, not arenas.
7. **Simple controls.** SPACE = action (place/use). TAB = inventory. ENTER =
   shield. Arrow keys = move. Minimal additions to Act 1's scheme.

---

## Room Transitions

Each Act 2 level consists of 2-3 rooms, each a full 30x16 grid. Rooms are
connected by **openings** in the border wall (1-3 tiles wide). When the player
walks into an opening, the game transitions to the connected room with a brief
visual flash (0.3s). The player appears at the corresponding opening on the
other side.

**State preservation:** Each room retains its own state when the player leaves:
broken walls, placed items, enemy positions, switch states, collected
materials/treasures. Re-entering a room restores it exactly as left.

**Enemies stay put.** Enemies do not follow between rooms. Each room has its
own set of enemies.

**Locked exits.** Some openings are blocked by locked doors. The player must
find the matching key and use it (SPACE with key selected) to open the exit.

**Level data format:**
```python
{
    'rooms': {
        'main':  { 'walls': ..., 'exits': {'right_7': 'forge'}, ... },
        'forge': { 'walls': ..., 'exits': {'left_7': 'main'}, ... },
    },
    'start_room': 'main',
    'player_start': (2, 7),
}
```

Levels 1-10 have no `rooms` key. The engine falls through to existing
single-room behaviour.

---

## Level Architecture

Three wall types in Act 2:

| Type | Bumps to break | Visual | Purpose |
|------|---------------|--------|---------|
| **Reinforced** | indestructible | Dark stone, riveted | Permanent structure: corridors, pillars, doorframes |
| **Stone** | 3 | Brick (existing Act 1 style) | Sealed passages, breakable shortcuts |
| **Wooden** | 2 | Brown planks | Crate barriers, easier to clear |

Reinforced walls form the architectural skeleton of each room. Breakable walls
are the exception - blocking specific shortcuts, hiding side passages, or
sealing treasure alcoves.

---

## Treasures in Act 2

In Act 1, treasures spawn randomly one at a time in a 1→9 cycle.

In Act 2, **all treasures are pre-placed** at fixed positions defined in the
level data. Any treasure type, any quantity. A room might contain a heap of 5
gold ingots, a single emerald in a hidden alcove, or no treasures at all.

**Completion condition:** collect ALL pre-placed treasures across all rooms in
the level. The HUD shows `LOOT 7/12` (collected / total) instead of the Act 1
`SEEK: Diamond` indicator.

Scoring per item is unchanged (Coin = 100, Diamond = 200, ... Crown = 1000).

---

## Materials

Found at fixed positions in rooms. Walk over a pickup to collect it into
inventory.

| Material | Found as | Visual |
|----------|----------|--------|
| **Rocks** | Rubble piles, cave-ins, quarry debris | Grey heap |
| **Planks** | Broken crates, timber stores, scaffolding | Brown stack |
| **Scrap Metal** | Workshop floors, broken machines, anvil scraps | Silver pieces |
| **Forge Crystal** | Power nodes, glowing alcoves (rare) | Glowing blue gem |

Materials are NOT dropped by breaking walls. Breaking walls in Act 2 is still
possible (stone/wooden walls) but yields nothing - it is a tactical action, not
a resource action.

---

## Tools

Found at fixed positions, often in hard-to-reach places or behind locked doors.
Once collected, a tool stays in inventory permanently and is **not consumed** by
recipes. It simply unlocks the ability to craft certain items.

| Tool | Found in | Unlocks |
|------|----------|---------|
| **Hammer** | Level 15 "The Forge Floor" | Bell recipe |
| **Chisel** | Level 16 "The Workshop" | Reinforced Barricade recipe |
| **Runestone** | Level 17 "The Crystal Chamber" | Portal Pair, Compass recipes |

---

## Inventory and Crafting (TAB)

Pressing TAB pauses the game and opens an overlay with:

- **Materials**: collected items with counts (Rocks: 5, Planks: 3, ...)
- **Tools**: found tools (permanent, shown as icons)
- **Keys**: collected keys (colour-coded)
- **Recipes**: list of all combinations. Available recipes are highlighted;
  unavailable ones are greyed with a note (e.g. "need Hammer" or "need 2 more
  Rocks"). Select a recipe and press ENTER to craft it.
- **Crafted items / active selection**: crafted items ready to place. Select
  one to make it the **active item** - what SPACE will place or use.

Arrow keys navigate. ENTER crafts. ESC closes the inventory.

### Recipes

| Ingredients | Tool required | Product | Real-world logic |
|-------------|---------------|---------|------------------|
| 3 Rocks | -- | **Stone Wall** | Stack rocks to block a path |
| 2 Planks | -- | **Bridge** | Lay planks across water |
| 3 Scrap Metal | Hammer | **Bell** | Hammer scraps into a noisy lure device |
| 2 Rocks + 1 Plank | Chisel | **Reinforced Barricade** | Shaped stone + wood frame (5 bumps to break) |
| 2 Forge Crystals | Runestone | **Portal Pair** | Forge's own magical technology |
| 1 Scrap Metal + 1 Forge Crystal | Runestone | **Compass** | Points toward nearest key (single use, consumed) |

Each material maps to its domain: rocks → stone structures, planks → wooden
structures, metal → mechanical devices, crystals → magical items. Cross-material
recipes (barricade, compass) yield hybrid items.

---

## Controls

| Key | Context | Action |
|-----|---------|--------|
| **SPACE** | Open floor tile | Place the active item from inventory |
| **SPACE** | Adjacent to locked door | Use selected key on it |
| **SPACE** | On/adjacent to switch | Toggle lever / press button |
| **TAB** | Any time during play | Open inventory / crafting (pauses game) |
| **ENTER** | During play | Activate shield (250 pts; also protects vs flames) |
| **Arrows** | During play | Move player |
| **Arrows** | In inventory | Navigate |
| **ENTER** | In inventory | Craft selected recipe |
| **ESC** | In inventory | Close |

**Act 1 (levels 1-10):** completely unchanged. SPACE places wall via credits.
TAB does nothing. ENTER = shield. No inventory, no materials.

**Act 2 default active item:** Stone Wall (if player has ≥3 rocks). Player must
open TAB to select a different item.

---

## Environmental Elements

### Locked Doors + Keys

Colour-coded doors (red, blue, green) placed in wall openings (interior or
border). Keys are found at fixed positions in rooms. To open a door: select the
matching key as the active item in inventory (TAB), walk adjacent to the door,
press SPACE. The door opens permanently and the key is consumed.

### Pushable Blocks

Heavy grey stone blocks occupying one tile. **Indestructible** - cannot be
broken by any entity (player, chaser, Forge Ogre, boss). The player pushes a
block 1 tile by walking into it, provided the tile behind the block (in the
push direction) is empty floor. Enemies cannot push blocks.

Uses: hold down pressure plates, push into water (permanent stepping stone),
block enemy paths, block flame jet sources, redirect patrol guard routes.

### Pressure Plates + Gates

A pressure plate is a floor tile. When any entity or pushable block is on it,
a linked gate (elsewhere in the room) opens. When the plate is vacated, the
gate closes. Pushable blocks hold plates permanently.

Gates are visually distinct (portcullis grate). When closed, they act as
indestructible walls. When open, they are passable floor.

### Water Streams

Tiles with flowing water in a defined direction. If the player steps onto a
water tile, they are **carried visibly, tile by tile**, in the flow direction
until reaching the stream's end - a narrow drain grate or a point where the
water flows under a wall. The player ends up at the drain tile.

Not lethal (no life lost). Creates one-way movement hazards. Cross with a
Bridge (crafted from 2 planks) placed on any water tile, or push a block into
the stream (permanent stepping stone at that tile).

Enemies that step on water are also carried to the drain.

### Flame Jets

A set of tiles connected to a source. The source cycles on/off on a fixed
rhythm (e.g. 2 seconds on, 2 seconds off). When active, flame sprites fill the
tiles. Contact with active flames = catch (life lost, same as enemy contact).

**Shield protects against flames.** While shield is active (10 seconds),
walking through flames is safe. This gives the shield a new strategic role.

Flame sources can be permanently blocked by placing a stone wall or pushing a
block onto the source tile. They can also be controlled by switches (flame
valve machine).

---

## Machines and Switches

### Switches

- **Lever**: toggle. SPACE flips between on and off. Stays in its state until
  toggled again. Visual: lever on wall, clearly up or down.
- **Button**: momentary. SPACE activates it for 3 seconds, then it resets.
  Visual: round plate on wall, glows while active.

### Machines

Each machine is linked to one or more switches (defined in level data).

| Machine | Effect when active | Visual |
|---------|--------------------|--------|
| **Gate** | Reinforced wall section opens (passable floor) | Portcullis grate |
| **Drawbridge** | Bridge extends over water tiles | Wooden platform |
| **Flame Valve** | Shuts off a flame jet (overrides its rhythm) | Valve wheel on pipe |
| **Conveyor Belt** | Row of tiles pushes entities 1 tile per tick in a direction | Animated arrows on floor |
| **Piston** | Pushes a pushable block 1 tile in a fixed direction | Mechanical arm |

Machine states persist when leaving and re-entering a room.

Multiple switches can control the same machine (AND/OR logic for puzzles).
A single switch can control multiple machines.

---

## Enemy Types

### Existing (Act 1, unchanged)

- **Chaser**: BFS pathfinding (HARD) or greedy (EASY)
- **Boss**: level 10, BFS on both difficulties

### New (Act 2)

| Type | Behaviour | Visual |
|------|-----------|--------|
| **Patrol Guard** | Walks a fixed back-and-forth path between waypoints. Does not chase the player. Predictable - the player times movement around it. | Ogre with lantern overlay |
| **Forge Ogre** | Chaser (BFS). Breaks player-placed walls (stone wall, barricade) in 2 bumps instead of 3. Cannot break reinforced walls or pushable blocks. | Ogre with anvil helmet |

### Act 2 Boss: The Forge Master (Level 20)

- Speed: 78ms (faster than player's 80ms base)
- AI: BFS chaser on both difficulties
- Immune to bells (decoys don't work on it)
- Breaks player-placed walls in 1 bump
- Cannot break reinforced walls or pushable blocks
- Defeat condition: collect the **Sceptre** (fixed position, behind locked
  doors requiring keys scattered across the level's rooms) while surviving.
  Pure evasion + puzzle-solving.

---

## Speed Curve

Act 2 uses a gentler speed curve than Act 1:

```
Act 1: factor = 1.07 ^ (10 - level)    [levels 1-9; level 10 fixed]
Act 2: factor = 1.05 ^ (20 - level)    [levels 11-19; level 20 fixed]
```

| Level | Player ms | Enemy ms |
|-------|-----------|----------|
| 11 | ~120 | ~240 |
| 15 | ~97 | ~195 |
| 19 | ~84 | ~168 |
| 20 | 80 (fixed) | 78 (boss, fixed) |

---

## Level Roadmap

| Level | Rooms | Introduces | Theme |
|-------|-------|-----------|-------|
| 11 | 2 | Room transitions, reinforced walls, rocks, pre-placed treasures, patrol guards | "The Passage" |
| 12 | 2 | Locked doors + keys, inventory/crafting (TAB) | "The Gatehouse" |
| 13 | 2 | Pushable blocks, pressure plates + gates | "The Mechanism" |
| 14 | 2 | Water streams, planks, bridge crafting | "The Waterworks" |
| 15 | 3 | Levers, machine gates, flame jets + shield, hammer tool, bell | "The Forge Floor" |
| 16 | 2 | Conveyor belts, buttons, drawbridges, forge ogre, chisel, barricade | "The Workshop" |
| 17 | 3 | Forge crystals, runestone tool, portal pair, piston | "The Crystal Chamber" |
| 18 | 3 | Compass, all mechanics, multi-key + multi-switch puzzle | "The Labyrinth" |
| 19 | 3 | Heavy enemies + all hazards combined | "The Gauntlet" |
| 20 | 3 | Act 2 Boss: The Forge Master | "The Heart of the Forge" |

One new mechanic per level. Each level teaches one concept before combining.

---

## Level Randomization

Each playthrough generates different room layouts procedurally. A hidden seed
(auto-generated from the system clock at game start) drives a seeded RNG
(`random.Random(seed)`) so generation is deterministic for a given seed.

### Generation approach: layered constrained procedural generation

Each Act 2 level has a **level template** that defines high-level structure:
room count, connectivity (which rooms link where), which mechanics are active,
difficulty parameters (enemy count, hazard density, resource scarcity), and
which puzzle type(s) to use. The template is fixed per level; the layouts
within it are generated.

#### Layer 1 — Skeleton (reinforced walls)

Generate the permanent architecture using **BSP (Binary Space Partition)**:

1. Start with the full 30x16 interior (cols 1-28, rows 1-14)
2. Recursively subdivide into 3-5 chambers by placing reinforced wall
   partitions (horizontal or vertical)
3. Cut doorways (1-2 tiles wide) in each partition to connect chambers
4. Place room exits at border positions defined by the connectivity template
5. Enforce minimum chamber size (5x4 tiles) and corridor width (1-2 tiles)

Result: a unique arrangement of corridors and chambers every playthrough,
all connected and navigable.

#### Layer 2 — Puzzle templates

Rather than generating puzzle logic from scratch, instantiate **puzzle
templates** — hand-designed micro-layouts that guarantee their own internal
solvability. Each template is parameterized (size, orientation, position)
and slotted into a chamber that fits.

Example puzzle templates:

| Template | Elements | Internal guarantee |
|----------|----------|--------------------|
| "Key behind water" | Water stream, key on far side, plank supply nearby | Key reachable if player bridges the water |
| "Plate and block" | Gate, pressure plate behind wall gap, pushable block | Gate opens when block is pushed onto plate |
| "Timed sprint" | Button, drawbridge over water, corridor of correct length | Drawbridge stays open long enough to cross at current speed |
| "Flame corridor" | Flame jets across corridor, shield or wall supply nearby | Passable with shield or by blocking the source |
| "Lever trade-off" | Lever opens gate A but activates flame jets at B | Both paths viable with different resource costs |

Templates specify relative positions of their elements. The generator places
them into chambers, adjusting coordinates to fit. A chamber can hold one
puzzle template or be left empty (just architecture + enemies).

#### Layer 3 — Hazards

Place environmental hazards in remaining open areas:

- **Water streams**: pick a direction, lay tiles, end at a wall/drain.
  Must not bisect the only path to a required element.
- **Flame jets**: pick a source tile and direction. Verify the corridor is
  passable during the off-cycle.
- **Breakable walls** (stone/wooden): fill non-critical doorways and
  alcove entrances.

Each hazard has placement rules (e.g. water needs a drain point, flames
need a clear line, breakable walls must not seal off the only path).

#### Layer 4 — Population

Place items and enemies in open floor tiles:

- **Treasures**: distribute the level's treasure list across rooms, one
  per open tile, prioritising chambers and dead ends
- **Materials**: distribute based on which recipes the level uses, placed
  in reasonable locations (rocks near rubble, planks near broken structures)
- **Tools**: placed at the fixed position defined by the level template
  (tools are too important to randomize freely)
- **Enemies**: place at valid positions away from the player start, ensuring
  BFS distance ≥ 5 tiles

#### Layer 5 — Validation

After generation, run a BFS flood-fill from the player start:

1. Verify every treasure is reachable (considering breakable walls, keys,
   switches — simulate the puzzle solutions)
2. Verify every exit is reachable
3. Verify the level is completable (all puzzles solvable in sequence)

If validation fails, increment the seed and regenerate. With well-constrained
templates and placement rules, failures should be rare (<5% of attempts).

### What varies vs. what is fixed

| Varies per playthrough | Fixed per level |
|------------------------|-----------------|
| Reinforced wall layout (BSP partition) | Room count and connectivity |
| Chamber shapes and corridor positions | Which mechanics are active |
| Treasure positions | Treasure types and quantities |
| Material positions | Material types and quantities |
| Enemy start positions | Enemy types and counts |
| Breakable wall placement | Tool positions (critical items) |
| Hazard positions (within rules) | Puzzle template selection |
| Patrol guard waypoints | Switch → machine wiring logic |

### New file: `levelgen.py`

The procedural generator lives in a new file. It takes a level template and
a seed, returns a fully populated level dict (same format as hand-designed
levels in `levels.py`). The game calls the generator at level start for Act 2
levels instead of reading from a static list.

`levels.py` still contains the 10 Act 1 levels (static) and the 10 Act 2
level templates (parameters for the generator).

---

## File Impact

| File | Change |
|------|--------|
| **New: `crafting.py`** | Material types, tool types, inventory state, recipe definitions, craftable item behaviours |
| **New: `rooms.py`** | RoomState (persist/restore), RoomCluster (multi-room management), transitions |
| **New: `levelgen.py`** | Procedural room generator: BSP skeleton, puzzle template instantiation, hazard/population placement, validation |
| **`levels.py`** | 10 Act 1 levels (static, unchanged) + 10 Act 2 level templates (parameters for `levelgen.py`) |
| **`game.py`** | Room transitions, TAB inventory overlay, SPACE context dispatch, water carry animation, flame/shield interaction, switch/machine tick, conveyor movement, LOOT HUD, pushable block physics |
| **`entities.py`** | PatrolEnemy (waypoint path), ForgeOgre (faster wall-break), pushable block collision |
| **`sprites.py`** | ~20 new procedural sprites |
| **`sounds.py`** | ~12 new SFX, 10 new music tracks |
| **`constants.py`** | Material/tool/recipe definitions, machine types, Act 2 speed curve, new colours |

## Implementation Phases

Each phase produces a playable milestone:

1. **Room transitions + foundation** — multi-room engine, reinforced walls,
   pre-placed treasures (LOOT HUD), inventory screen, SPACE dispatch.
   Levels 11-12.
2. **Environmental puzzles** — pushable blocks, pressure plates, gates, locked
   doors + keys. Levels 13-14.
3. **Hazards + crafting** — water streams (carry animation), flame jets +
   shield interaction, bridges, tools, bell. Levels 15-16.
4. **Machines + advanced crafting** — levers, buttons, gates, conveyors,
   drawbridges, pistons, portals, forge ogres. Levels 17-18.
5. **Endgame + randomization** — all mechanics combined, Act 2 boss, level
   randomization. Levels 19-20.

---

## Done when

- [ ] Levels 1-10 are byte-identical and play identically to current
- [ ] Room transitions work: state persists across visits, enemies stay put
- [ ] All three wall types render correctly and break at the right thresholds
- [ ] Pre-placed treasures show LOOT x/y in HUD; level completes when all collected
- [ ] Materials collectible from fixed positions; inventory shows correct counts
- [ ] Tools persist in inventory and unlock recipes
- [ ] TAB opens inventory; recipes craft correctly; active item selectable
- [ ] SPACE places active item on floor, uses key on door, toggles switches
- [ ] ENTER activates shield; shield protects against flames
- [ ] Locked doors open with matching key (consumed)
- [ ] Pushable blocks: player pushes, enemies can't; indestructible by all
- [ ] Pressure plates + gates: block holds plate; vacating closes gate
- [ ] Water streams carry player visibly to drain; bridges and blocks cross them
- [ ] Flame jets cycle on/off; shield protects; wall/block on source blocks them
- [ ] Levers toggle, buttons are momentary (3s)
- [ ] All 5 machine types function correctly when linked to switches
- [ ] Patrol guards follow waypoint paths; forge ogres break walls faster
- [ ] Act 2 boss (level 20) is faster, immune to bells, breaks walls in 1 bump
- [ ] Sceptre collectible to win Act 2
- [ ] All 10 Act 2 levels designed and playable on EASY and HARD
- [ ] Level randomization provides per-playthrough variation while staying solvable
