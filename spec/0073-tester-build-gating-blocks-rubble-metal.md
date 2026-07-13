# Spec 0073 — Tester-build gating: walls→blocks, rubble→block-credit, hide metal + inventory menu

Backlog: **BL-26 (P2)**, with the 2026-07-14 clarifications and Q1–Q3 answers. Goal: a
clean tester-facing build that exposes only finished, understandable mechanics. Six
deliverables:

1. **Rename the *user-built* wall to a BLOCK** everywhere (code included) — the
   placeable, its sprite, the HUD counter, the place-credit vocabulary, the
   events/sounds. The level's own **wall terrain** (`WALL_STONE` etc.) keeps its name.
   HUD counter labels also go plural for consistency: **BLOCKS** and **BRIDGES**.
2. **Blocks are earned as credits, not crafted** — mining a breakable wall *or*
   collecting rubble each banks half a block (2 → 1 block); SPACE spends a credit to
   place one. The 3-rocks Block recipe is **dropped**; rubble no longer enters the
   inventory (credit only — may change when the inventory is reactivated later).
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

- [ ] **D1** — The user-built wall is **BLOCK** throughout (code + UI + sound +
  sprite); level wall terrain untouched; HUD labels read **BLOCKS** and **BRIDGES**;
  suite green (event/sound/label goldens re-recorded).
- [ ] **D2** — Mining a breakable wall or collecting rubble each banks half a block
  (2 → 1), via one shared path; SPACE places a block from credits in both Acts; the
  3-rocks recipe is removed and rubble is credit-only (not stored in inventory).
- [ ] **D3** — Generated levels carry noticeably more rubble (block credits are
  earnable without relying on scarce breakable walls).
- [ ] **D4** — With `ENABLE_METAL = False`, generated levels contain no scrap metal;
  rubble and planks are unaffected.
- [ ] **D5** — With `ENABLE_INVENTORY_MENU = False`, the inventory / crafting overlay
  is completely disabled (TAB does nothing, nothing rendered); the internal `Inventory`
  (planks for auto-bridges, keys) still works.
- [ ] **D6** — Verification: updated/added tests pass, goldens re-recorded and
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
| `BREAKS_PER_CREDIT = 2` | `HALVES_PER_BLOCK = 2` |
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

## D2 — Blocks are earned as credits, not crafted (Q1)

**Earning.** Extract the credit-banking tail of `_break_wall` into a shared helper:

```python
def _earn_block_half(self):
    self._block_halves += 1
    if self._block_halves >= HALVES_PER_BLOCK:      # 2
        self._block_halves -= HALVES_PER_BLOCK
        self._block_credits += 1
        self._emit('credit_earned')
```

- `_break_wall` calls it after `_emit('wall_broken')` — mining a breakable wall = one
  half (unchanged behaviour).
- `_collect_materials`: when the material is `MAT_ROCKS`, call `_earn_block_half()`
  **instead of** `inventory.add_material` — one rubble = one half; still emit
  `'collected'` for the pickup chirp. Rubble does **not** enter the inventory (Q1:
  credit only for now; revisit when the inventory is reactivated).

So **2 rubble = 1 block** and **2 mined walls = 1 block**, mixed freely, shown by the
HUD `BLOCKS` counter and its spec-0072 lower-half-block half indicator (`_block_halves
> 0`).

**Placement.** Blocks are placed from credits in **both** Acts — drop the recipe path:

- Remove `RECIPES` entry `(CRAFT_BLOCK, {MAT_ROCKS: 3}, None)`, and the now-dead
  `Inventory.can_quick_place_block` / `quick_place_block`.
- `place()` calls `_place_block()` unconditionally (delete the `_act2_place` block
  branch; `_act2_place` handled only blocks, so it goes away — bridges are placed by
  bumping water, spec 0072, not via SPACE).
- Verify no code indexes `RECIPES` by a now-shifted position for the bridge (bridge
  crafting is material-direct via `quick_bridge`, but check `can_craft`/UI callers).

*(Note: the forge smashing a placed block routes through `_break_wall` and therefore
also banks a half-credit — a pre-existing quirk, left as-is; out of scope.)*

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
- The internal `Inventory` object is untouched — planks still fuel auto-bridges, keys
  still auto-open doors; only the **menu** is gone.

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
2. **Block credit** — a world unit test: collecting two rubble raises `_block_credits`
   by 1 with a `'credit_earned'` emit and leaves `inventory.materials['rocks'] == 0`;
   one rubble leaves a half (`_block_halves == 1`); a mined wall + a rubble = one
   credit; SPACE then places a block and decrements the credit.
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

## Resolved decisions (Q1–Q3, 2026-07-14)

- **Q1** — Rubble earns a half block **credit only** (not stored in inventory) for now;
  may change when the inventory is reactivated. The 3-rocks Block recipe is dropped;
  blocks are auto-earned from collecting rubble / smashing breakable walls.
- **Q2** — The whole inventory/crafting menu is disabled by a boolean constant
  (`ENABLE_INVENTORY_MENU = False`), not merely filtered.
- **Q3** — HUD labels are plural: **BLOCKS** and (for consistency) **BRIDGES**.

## Out of scope

- **BL-54** (metal-reinforced blocks vs the forge) — depends on metal being re-enabled.
- **BL-18** (4-plank bridges / wooden-door = half a bridge) — separate spec.
- Re-enabling the advanced economy; designing the eventual rocks/metal/crystal recipes.
- Changing `_break_wall` / `'wall_broken'` / the forge break mechanic (naming aside),
  including the forge-smashes-your-block-banks-a-half quirk.

## Done when:

- [ ] **D1** — user-built wall renamed to BLOCK across code/UI/sound/sprite; terrain
  walls untouched; HUD reads BLOCKS/BRIDGES; suite green; goldens re-recorded.
  *(commit: ____)*
- [ ] **D2** — shared `_earn_block_half` banks a half from mining *and* rubble
  (2 → 1 block); block placement is credit-based in both Acts; 3-rocks recipe +
  `quick_place_block` removed; rubble not stored; unit test green. *(commit: ____)*
- [ ] **D3** — rubble counts raised; generation test asserts the higher floor; Daniel
  confirms there is enough rubble in play. *(commit: ____)*
- [ ] **D4** — `ENABLE_METAL = False` removes scrap-metal drops (rubble/planks intact);
  generation test green. *(commit: ____)*
- [ ] **D5** — `ENABLE_INVENTORY_MENU = False` fully disables the crafting/inventory
  overlay (internal Inventory still works); headless test green. *(commit: ____)*
- [ ] **D6** — tests updated/added and green, goldens re-recorded and reviewed, Daniel
  confirms the tester build in-game. *(commit: ____)*
