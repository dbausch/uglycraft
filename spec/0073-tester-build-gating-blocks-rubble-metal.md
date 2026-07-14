# Spec 0073 — Tester-build gating: walls→blocks, rubble→block-credit, hide metal + inventory menu

Backlog: **BL-26 (P2)**, with the 2026-07-14 clarifications and Q1–Q3 answers. Goal: a
clean tester-facing build that exposes only finished, understandable mechanics. Six
deliverables:

1. **Rename the *user-built* wall to a BLOCK** everywhere (code included) — the
   placeable, its sprite, the HUD counter, the place-credit vocabulary, the
   events/sounds. The level's own **wall terrain** (`WALL_STONE` etc.) keeps its name.
   HUD counter labels also go plural for consistency: **BLOCKS** and **BRIDGES**.
2. **Blocks *and bridges* are earned as credits, not crafted** — mining a breakable
   wall or collecting rubble each banks half a **block** (2 → 1); collecting a pack of
   planks banks half a **bridge** (2 → 1). SPACE places a block from a block credit;
   bumping water places a bridge from a bridge credit. The 3-rocks Block recipe and the
   planks-based Bridge crafting (spec 0072) are **dropped**; rubble and planks no longer
   enter the inventory (credit only — may change when the inventory is reactivated).
3. **More rubble** — sprinkle noticeably more rubble through generated levels, since
   there are few breakable walls to mine, so rubble is the main way to earn block
   credits.
4. **Hide metal** — no scrap-metal drops in generated levels (rubble/planks stay).
5. **Disable the inventory / crafting menu entirely** — behind one boolean constant,
   set `False` for the tester build.
6. **Verification.**

All gating is behind **constants** so it can be flipped back on when the inventory /
metal economy is finished later (see BL-54, out of scope here).

## Status checklist

- [x] **D1** — The user-built wall is **BLOCK** throughout (code + UI + sound +
  sprite); level wall terrain untouched; HUD labels read **BLOCKS** and **BRIDGES**;
  suite green (event/sound/label goldens re-recorded).
- [x] **D2** — Block credits (mining a wall / collecting rubble, 2 → 1) and bridge
  credits (collecting a pack of planks, 2 → 1) via symmetric half-credit paths; SPACE
  places a block from a block credit, bumping water places a bridge from a bridge
  credit; the 3-rocks Block recipe and planks-based Bridge crafting are removed; rubble
  and planks are credit-only (not stored).
- [x] **D3** — Generated levels carry noticeably more rubble (block credits are
  earnable without relying on scarce breakable walls).
- [x] **D4** — With `ENABLE_METAL = False`, generated levels contain no scrap metal;
  rubble and planks are unaffected.
- [x] **D5** — With `ENABLE_INVENTORY_MENU = False`, the inventory / crafting overlay
  is completely disabled (TAB does nothing, nothing rendered); the internal `Inventory`
  (planks for auto-bridges, keys) still works.
- [x] **D6** — Verification: updated/added tests pass, goldens re-recorded and
  reviewed, and Daniel confirms the tester build in-game.

## Background — confirmed facts

Established by reading the code (self-contained; do not re-derive):

### The two kinds of "wall"

- **Level wall terrain** (NOT renamed): `WALL_STONE`, `WALL_WOODEN`,
  `WALL_REINFORCED` (`constants.py`), `WALL_HITS_TO_BREAK`, `WALL_BUMPS`,
  `BREAKS_PER_CREDIT`, the border wall, and `World._break_wall` / `'wall_broken'`
  (mining a breakable wall — also reused when the forge ogre smashes a placed block).
  These describe the dungeon, not the player's placeable.
- **User-built wall** (→ **BLOCK**): what the player places with SPACE. Today:
  - `crafting.py`: `CRAFT_STONE_WALL = 'stone_wall'`, `CRAFT_NAMES`/`CRAFT_ICONS`
    entries, `RECIPES[0] = (CRAFT_STONE_WALL, {MAT_ROCKS: 3}, None)`, `active_item`
    default, `can_quick_place_wall()` / `quick_place_wall()` (3 rocks, else a crafted
    item).
  - `world.py`: `_place_wall()` (spends `_place_credits`), the `_act2_place`
    `CRAFT_STONE_WALL` branch, event `'wall_placed'`, counters `_place_credits` /
    `_breaks_toward_credit`, `Barrier('placed')`.
  - `game.py`: HUD `WALLS` counter (`wall_val`/`wall_color`/`walls_half`, spec 0072),
    HUD `BRIDGE` label, `_EVENT_SOUNDS['wall_placed'] = 'place_wall'` (and
    `'bridge_built' = 'place_wall'`), `sp['placed_wall']`, help line
    `"place wall  (costs 1 credit)"`, `_WORLD_ATTRS`.
  - `sprites.py`: `placed_wall` sprite, `icon_stone_wall` icon.
  - `sounds.py`: `sfx_place_wall` under `'place_wall'`.
  - `entities.py`/`world.py`: forge ogre `wall_bump_power`, the "player-placed wall"
    damage path (`world.py` ~804–811, 963).

### Block-credit + placement mechanic today (`world.py`)

`_break_wall` removes a barrier, emits `'wall_broken'`, then `_breaks_toward_credit +=
1`; at `BREAKS_PER_CREDIT` (**2**) it wraps → `_place_credits += 1` +
`'credit_earned'`. `place()` routes `if self.crafting: _act2_place() else:
_place_wall()`. `_place_wall()` spends one `_place_credits` → `Barrier('placed')` +
`'wall_placed'`. `_act2_place()` instead consumes a crafted `CRAFT_STONE_WALL` or
`quick_place_wall()` (3 rocks). Materials picked up in `_collect_materials` →
`inventory.add_material`.

### Bridges today (spec 0072 — being reworked here)

Bumping water auto-builds a bridge via `_try_auto_bridge`, which calls
`Inventory.quick_bridge()` (2 planks from inventory, else a crafted `CRAFT_BRIDGE`).
The HUD `BRIDGE` counter reads `crafted['bridge'] + planks//2` from the inventory,
shown only on plank-bearing levels (`_level_has_planks`). D2 replaces this
planks-in-inventory model with a **bridge credit** symmetric to blocks.

### Material distribution

`levels.py` Act 2 feature sets set `material_types` (level 1 `[ROCKS, PLANKS]`, levels
2–10 add `MAT_METAL`) and `material_count` ranging `(4,6)`→`(10,16)`
(`levels.py:212–337`). `levelgraph.add_materials(mat_types, count)` splits `count`
across `mat_types` **excluding planks** (planks come only from `add_water_room`). So
today the budget is split ~half rocks / half metal. **Crystal is never dropped.**
Gating metal therefore (a) needs only the metal removal and (b) already redirects the
whole budget to rubble — D3 raises the counts further on top of that.

## D1 — Rename the user-built wall to BLOCK; plural HUD labels

Mechanical rename of the **user-built** symbols only (leave the level-terrain set from
Background untouched):

| Today | New |
|---|---|
| `CRAFT_STONE_WALL = 'stone_wall'` | `CRAFT_BLOCK = 'block'` (name `'Block'`, icon `'icon_block'`) |
| `World._place_wall` | `_place_block` |
| event `'wall_placed'` | `'block_placed'` |
| `World._place_credits` | `_block_credits` |
| `World._breaks_toward_credit` | `_block_halves` |
| `BREAKS_PER_CREDIT = 2` | `HALVES_PER_CREDIT = 2` (shared by blocks & bridges) |
| sprite `placed_wall`, icon `icon_stone_wall` | `placed_block`, `icon_block` |
| sound `'place_wall'` / `sfx_place_wall` | `'place_block'` / `sfx_place_block` |
| forge `enemy.wall_bump_power` | `block_bump_power` |
| help text `"place wall …"` | `"place block …"` |
| HUD label `WALLS` | **`BLOCKS`** |
| HUD label `BRIDGE` (spec 0072) | **`BRIDGES`** |

**Deliberately kept:** `_break_wall` and `'wall_broken'` (generic "a barrier was
broken"), the `WALL_*` terrain constants, `WALL_BUMPS`, and `Barrier('placed')`'s
internal kind string `'placed'` (only its *sprite key* is renamed).

`can_quick_place_wall`/`quick_place_wall` and the `_act2_place` block branch are not
renamed but **removed** (see D2). Update `_WORLD_ATTRS`, the KB
(`uglycraft-display.md`, `uglycraft-mechanics.md`, `uglycraft-sound.md`), and every
test referencing a renamed symbol/event/sound/label; event-trace and screenshot
goldens are re-recorded (D6).

## D2 — Blocks and bridges are earned as credits, not crafted (Q1, Q4)

Both resources follow one pattern: collecting the material (or mining a wall) banks a
**half credit**; two halves make one credit; building spends a credit. Nothing goes
through the inventory.

**Earning — a shared half-credit path.** Generalise the credit-banking tail of
`_break_wall` (two thin wrappers over one helper, or a small `_earn_half(halves,
credits)`):

```python
def _earn_block_half(self):   # mined wall / rubble
    self._block_halves += 1
    if self._block_halves >= HALVES_PER_CREDIT:     # 2
        self._block_halves -= HALVES_PER_CREDIT
        self._block_credits += 1
        self._emit('credit_earned')

def _earn_bridge_half(self):  # a pack of planks
    ... same, on _bridge_halves / _bridge_credits ...
```

- **Blocks** — `_break_wall` banks a block half after `_emit('wall_broken')` (mining a
  breakable wall, unchanged); `_collect_materials` banks a block half when the material
  is `MAT_ROCKS`. Counters `_block_credits` / `_block_halves` (the renamed
  `_place_credits` / `_breaks_toward_credit`).
- **Bridges** — `_collect_materials` banks a bridge half when the material is
  `MAT_PLANKS`. New counters `_bridge_credits` / `_bridge_halves`.

In both cases still `_emit('collected')` for the pickup chirp; the material does **not**
enter the inventory (Q1/Q4). So **2 rubble = 1 block**, **2 mined walls = 1 block**, and
**2 planks = 1 bridge**, mixed freely.

**HUD.** `BLOCKS` shows `_block_credits`; `BRIDGES` shows `_bridge_credits` (still only
on plank-bearing levels via `_level_has_planks`). Each uses the spec-0072 lower-half
indicator, driven by `_block_halves > 0` / `_bridge_halves > 0`. Both bridge counters
join `_WORLD_ATTRS`. This replaces spec 0072's `planks//2`-from-inventory computation
(and drops the `CRAFT_BRIDGE` / `MAT_PLANKS` imports the HUD used).

**Placement — credit-based, drop the recipes.**

- **Block**: `place()` calls `_place_block()` unconditionally (spends one
  `_block_credits`). Delete the `_act2_place` block branch (it handled only blocks, so
  `_act2_place` goes away). Remove the `RECIPES` `CRAFT_BLOCK` entry and the dead
  `Inventory.can_quick_place_block` / `quick_place_block`.
- **Bridge**: `_try_auto_bridge` spends one `_bridge_credits` instead of
  `quick_bridge()` — the gate becomes `if self._bridge_credits <= 0: return False`, and
  on success `self._bridge_credits -= 1`. **All existing guards are unchanged**
  (one-per-water-room lock, far-side-open, plate-adjacency). Remove the dead
  `Inventory.can_quick_bridge` / `quick_bridge`, the `RECIPES` `CRAFT_BRIDGE` entry, and
  the `crafted['bridge']` fallback.
- After both removals `RECIPES` holds only the dormant advanced recipes (behind the
  disabled menu, D5); verify nothing indexes `RECIPES` by a now-shifted position and
  that the `CRAFT_BLOCK` / `CRAFT_BRIDGE` constants are no longer referenced.

*(Note: the forge smashing a placed block routes through `_break_wall` and therefore
also banks a block half — a pre-existing quirk, left as-is; out of scope.)*

## D3 — More rubble

Raise rubble availability so block credits are earnable without relying on the few
breakable walls. Two levers, both in `levels.py` / the metal gate:

- Gating metal (D4) already sends the entire `material_count` budget to rubble.
- On top of that, **increase `material_count`** across the Act 2 feature sets
  (proposal: roughly +50–100 %, e.g. level 1 `(4,6)`→`(8,10)`, mid `(6,10)`→`(12,18)`,
  late `(10,16)`→`(18,26)`) so a level yields enough rubble for a useful number of
  blocks. Exact values are **playtest-tuned** (a D6 manual check) — the numbers above
  are a starting point, not final.

Keep planks provisioning (water rooms) unchanged.

## D4 — Hide metal

Add `ENABLE_METAL = False` to `constants.py`. In `levels.py`, filter the feature-set
`material_types` through it (drop `MAT_METAL` when disabled), so flipping the flag
restores the level-2+ metal drops verbatim. No scrap metal is placed; rubble and planks
are unchanged. (Crystal is already never dropped.)

## D5 — Disable the inventory / crafting menu (Q2)

Add `ENABLE_INVENTORY_MENU = False` to `constants.py`. When `False`:

- The TAB handler in `game.py` does not open the inventory/crafting overlay, and
  `_render_inventory` is not invoked (no crafting UI at all).
- The internal `Inventory` object is untouched but now effectively tracks only **keys**
  (rubble → block credits and planks → bridge credits bypass it, D2; metal is gated);
  keys still auto-open doors. Only the **menu** is gone.

This subsumes hiding the unfinished recipes/tools: with the menu off, Bell / Barricade
/ Portal Pair / Compass and Hammer / Chisel / Runestone are simply never shown. Their
`RECIPES`/`TOOL_*` definitions remain in `crafting.py` (dormant) for when the economy
is finished.

## D6 — Verification

pytest suite (event traces, goldens, world unit tests). The rename is broad:

1. **Rename safety** — `grep` proves no `stone_wall` / `place_wall` / `WALLS` /
   `_place_credits` / `quick_place_wall` references remain outside the intentionally
   kept set; `poe test` passes. Event-trace goldens (`'wall_placed'→'block_placed'`)
   and HUD screenshot goldens (`WALLS→BLOCKS`, `BRIDGE→BRIDGES`) are re-recorded and
   reviewed.
2. **Block & bridge credits** — world unit tests: collecting two rubble raises
   `_block_credits` by 1 with a `'credit_earned'` emit and leaves
   `inventory.materials['rocks'] == 0`; one rubble leaves a half (`_block_halves == 1`);
   a mined wall + a rubble = one credit; SPACE then places a block and decrements it.
   Symmetrically, collecting two planks raises `_bridge_credits` by 1 (planks not
   stored); bumping water spends one bridge credit and builds the bridge, with the
   spec-0072 guards intact. The spec-0072 bridge tests
   (`test_auto_bridge_*`) are reworked from the planks-in-inventory model to credits.
3. **More rubble** — a generation test: a seed sweep yields materially more rubble per
   level than before the change (assert a per-level rubble floor).
4. **Metal gate** — with `ENABLE_METAL = False`, no generated room lists a `metal`
   material across a seed sweep; flipping the flag restores it.
5. **Inventory-menu gate** — a headless test: with `ENABLE_INVENTORY_MENU = False`,
   pressing TAB does not enter the inventory state and no crafting overlay renders.
6. **Manual check** — Daniel plays the tester build and confirms: the HUD reads
   `BLOCKS` / `BRIDGES`; mining walls and collecting rubble both fill BLOCKS (half at a
   time) and there is *enough* rubble; SPACE places a block; no scrap metal appears;
   TAB opens nothing.

## Resolved decisions (Q1–Q4, 2026-07-14)

- **Q1** — Rubble earns a half block **credit only** (not stored in inventory) for now;
  may change when the inventory is reactivated. The 3-rocks Block recipe is dropped;
  blocks are auto-earned from collecting rubble / smashing breakable walls.
- **Q2** — The whole inventory/crafting menu is disabled by a boolean constant
  (`ENABLE_INVENTORY_MENU = False`), not merely filtered.
- **Q3** — HUD labels are plural: **BLOCKS** and (for consistency) **BRIDGES**.
- **Q4** — Planks are handled exactly like rubble: a pack of planks earns half a
  **bridge** credit (2 → 1), planks are not stored in the inventory, and the
  planks-based Bridge crafting from spec 0072 is dropped in favour of bridge credits.

## Out of scope

- **BL-54** (metal-reinforced blocks vs the forge) — depends on metal being re-enabled.
- **BL-18** (4-plank bridges / wooden-door = half a bridge) — separate spec; note it
  will re-tune the plank↔bridge ratio, which this spec fixes at 2 planks = 1 bridge.
- Re-enabling the advanced economy; designing the eventual rocks/metal/crystal recipes.
- Changing `_break_wall` / `'wall_broken'` / the forge break mechanic (naming aside),
  including the forge-smashes-your-block-banks-a-half quirk.

## Done when:

- [x] **D1** — user-built wall renamed to BLOCK across code/UI/sound/sprite; terrain
  walls untouched; HUD reads BLOCKS/BRIDGES; suite green; goldens re-recorded.
  *(commit: f01b3a1; confirmed in-game 2026-07-14)*
- [x] **D2** — block half from mining *and* rubble, bridge half from planks (2 → 1
  each); block placed by SPACE and bridge by water-bump, both from credits; 3-rocks
  Block recipe + `quick_place_block` and planks-based Bridge crafting (`quick_bridge`,
  `CRAFT_BRIDGE`) removed; rubble/planks not stored; unit tests green. *(commit: c634c31;
  confirmed in-game 2026-07-14)*
- [x] **D3** — rubble counts raised; generation test asserts the higher floor; Daniel
  confirms there is enough rubble in play. *(commit: 6d0b22d; confirmed in-game
  2026-07-14)*
- [x] **D4** — `ENABLE_METAL = False` removes scrap-metal drops (rubble/planks intact);
  generation test green. *(commit: ad6fb76; confirmed in-game 2026-07-14)*
- [x] **D5** — `ENABLE_INVENTORY_MENU = False` fully disables the crafting/inventory
  overlay (internal Inventory still works); headless test green. *(commit: d21a967;
  confirmed in-game 2026-07-14)*
- [x] **D6** — tests updated/added and green (full suite 853), goldens re-recorded and
  reviewed, Daniel confirms the tester build in-game. *(commit: d21a967; confirmed
  in-game 2026-07-14)*
