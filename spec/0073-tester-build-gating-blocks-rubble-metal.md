# Spec 0073 — Tester-build gating: walls→blocks, rubble→half-block, hide metal + advanced crafting

Backlog: **BL-26 (P2)**, with the 2026-07-14 clarifications. Goal: a clean
tester-facing build that exposes only finished, understandable mechanics.
Four changes plus verification:

1. **Rename the *user-built* wall to a BLOCK** everywhere (code included) — the
   craftable, the placed sprite, the HUD counter, the place-credit vocabulary, the
   events/sounds. The level's own **wall terrain** (`WALL_STONE` etc.) keeps its name.
2. **Rubble auto-earns half a block** — collecting one rubble banks half a block
   credit (2 rubble = 1 block), reusing the mined-wall credit path and the spec-0072
   lower-half-block HUD indicator.
3. **Hide metal** — no scrap-metal drops in generated levels (rubble stays).
4. **Hide the unfinished recipes/tools** — Bell, Barricade, Portal Pair, Compass and
   their tools (Hammer, Chisel, Runestone) disappear from the crafting UI.

All gating is behind **constants** so it can be flipped back on when the inventory /
metal economy is finished later (see BL-54, out of scope here).

## Status checklist

- [ ] **D1** — The user-built wall is called **BLOCK** throughout (code + UI + sound
  + sprite); level wall terrain is untouched; full suite green after the rename
  (event/sound/label goldens re-recorded).
- [ ] **D2** — Collecting rubble banks half a block credit (2 rubble = 1 block),
  shared with the mined-wall path; the HUD `BLOCK` counter and its half indicator
  update accordingly.
- [ ] **D3** — With `ENABLE_METAL = False`, generated levels contain no scrap metal;
  rubble and planks are unaffected.
- [ ] **D4** — With `ENABLE_ADVANCED_CRAFTING = False`, the crafting UI shows only the
  finished items; Bell/Barricade/Portal Pair/Compass and Hammer/Chisel/Runestone are
  hidden.
- [ ] **D5** — Verification: updated/added tests pass, goldens re-recorded and
  reviewed, and Daniel confirms the tester build in-game.

## Background — confirmed facts

Established by reading the code (self-contained; do not re-derive):

### The two kinds of "wall"

- **Level wall terrain** (NOT renamed): `WALL_STONE`, `WALL_WOODEN`,
  `WALL_REINFORCED` (`constants.py`), `WALL_HITS_TO_BREAK`, `WALL_BUMPS`,
  `BREAKS_PER_CREDIT`, the border wall, and `World._break_wall` /
  `'wall_broken'` (mining a level wall — also reused when the forge ogre breaks a
  placed block). These describe the dungeon, not the player's craftable.
- **User-built wall** (→ **BLOCK**): the thing the player places with SPACE. Today:
  - `crafting.py`: `CRAFT_STONE_WALL = 'stone_wall'`; `CRAFT_NAMES['stone_wall'] =
    'Stone Wall'`; `CRAFT_ICONS['stone_wall'] = 'icon_stone_wall'`;
    `RECIPES[0] = (CRAFT_STONE_WALL, {MAT_ROCKS: 3}, None)`; `active_item` default;
    `can_quick_place_wall()` / `quick_place_wall()` (3 rocks → a wall, else fall back
    to a crafted `CRAFT_STONE_WALL`).
  - `world.py`: `_place_wall()` (uses `_place_credits`), the `_act2_place`
    `CRAFT_STONE_WALL` branch, the `'wall_placed'` event, the counters
    `_place_credits` and `_breaks_toward_credit`, `Barrier('placed')` fixtures.
  - `game.py`: the HUD `WALLS` counter (`wall_val`/`wall_color`/`walls_half`, spec
    0072), `_EVENT_SOUNDS['wall_placed'] = 'place_wall'` (and
    `'bridge_built' = 'place_wall'`), `sp['placed_wall']`, the help line
    `"place wall  (costs 1 credit)"`, `_WORLD_ATTRS` (`_place_credits`,
    `_breaks_toward_credit`).
  - `sprites.py`: the `placed_wall` sprite and `icon_stone_wall` icon.
  - `sounds.py`: `sfx_place_wall` under the `'place_wall'` key.
  - `entities.py`/`world.py`: the forge ogre's `wall_bump_power` and the
    "player-placed wall" damage path (`world.py` ~804–811, 963).

### Block-credit mechanic today (`world.py`)

`_break_wall(col,row)` removes a barrier, emits `'wall_broken'`, then
`_breaks_toward_credit += 1`; when it reaches `BREAKS_PER_CREDIT` (**2**) it wraps and
`_place_credits += 1` with a `'credit_earned'` emit. `place()` → `_place_wall()`
(Act 1 / `crafting=False`) spends one `_place_credits` to drop a `Barrier('placed')`
and emits `'wall_placed'`. In Act 2 `_act2_place()` instead consumes a crafted item or
`quick_place_wall()` (3 rocks). Materials are picked up in `_collect_materials()` →
`inventory.add_material(payload)`.

### Material distribution

`levels.py` Act 2 feature sets list `material_types`: level 1 uses
`[MAT_ROCKS, MAT_PLANKS]`, levels 2–10 use `[MAT_ROCKS, MAT_PLANKS, MAT_METAL]`
(`levels.py:212–331`). `levelgraph.add_materials` drops those (planks excluded — planks
come only from `add_water_room`). **Crystal is never dropped**, so Portal Pair/Compass
are already un-craftable; gating metal is the only material change needed.

## D1 — Rename the user-built wall to BLOCK

Mechanical rename of the **user-built** symbols only (leave the level-terrain set from
Background untouched). Proposed table:

| Today | New |
|---|---|
| `CRAFT_STONE_WALL = 'stone_wall'` | `CRAFT_BLOCK = 'block'` |
| `CRAFT_NAMES[…] = 'Stone Wall'` | `'Block'` |
| `CRAFT_ICONS[…] = 'icon_stone_wall'` | `'icon_block'` |
| `Inventory.can_quick_place_wall` / `quick_place_wall` | `can_quick_place_block` / `quick_place_block` |
| `World._place_wall` | `_place_block` |
| event `'wall_placed'` | `'block_placed'` |
| `World._place_credits` | `_block_credits` |
| `World._breaks_toward_credit` | `_block_halves` |
| `BREAKS_PER_CREDIT = 2` | `HALVES_PER_BLOCK = 2` |
| sprite `placed_wall`, icon `icon_stone_wall` | `placed_block`, `icon_block` |
| sound key `'place_wall'` / `sfx_place_wall` | `'place_block'` / `sfx_place_block` |
| HUD label `WALLS` | `BLOCK` |
| forge `enemy.wall_bump_power` | `block_bump_power` |
| help text `"place wall …"` | `"place block …"` |

**Deliberately kept:** `_break_wall` and `'wall_broken'` (generic "a barrier was
broken" — fires for both mining level walls and the forge smashing a placed block),
`WALL_*` terrain constants, `WALL_BUMPS`, and `Barrier('placed')`'s internal kind
string `'placed'` (only the *sprite key* it maps to is renamed).

Update `_WORLD_ATTRS` delegation, the KB (`kb/uglycraft-display.md`,
`kb/uglycraft-mechanics.md`, `kb/uglycraft-sound.md`), and every test that references
a renamed symbol/event/sound/label. Event-trace and screenshot goldens that mention
`wall_placed` / the `WALLS` label are re-recorded (see D5).

## D2 — Rubble earns half a block

Extract the credit-banking tail of `_break_wall` into a shared helper and call it from
rubble pickup too:

```python
def _earn_block_half(self):
    self._block_halves += 1
    if self._block_halves >= HALVES_PER_BLOCK:      # 2
        self._block_halves -= HALVES_PER_BLOCK
        self._block_credits += 1
        self._emit('credit_earned')
```

- `_break_wall` calls it after `_emit('wall_broken')` (unchanged behaviour: a mined
  wall is one half).
- `_collect_materials`: when the collected material is `MAT_ROCKS`, call
  `_earn_block_half()` (one rubble = one half) instead of adding it to
  `inventory.materials`. Still `_emit('collected')` for the pickup chirp; the
  `'credit_earned'` fires on every second rubble.

So **2 rubble = 1 block** and **2 mined walls = 1 block**, both shown by the HUD
`BLOCK` counter and its lower-half-block half indicator (spec 0072, driven by
`_block_halves > 0`). Picking up rubble is now always useful, independent of the
crafting menu.

> **Open question Q1** — does rubble *also* keep accumulating in
> `inventory.materials['rocks']` (for a future rocks-based recipe), or go straight to
> a half-credit only (recommended, since the 3-rocks `Block` recipe is redundant once
> rubble → credit)? This spec assumes **credit only** in the gated build.

## D3 — Hide metal

Add `ENABLE_METAL = False` to `constants.py`. In `levels.py`, filter the feature-set
`material_types` through it (drop `MAT_METAL` when disabled) — a single helper or a
comprehension at the point of use, so flipping the flag restores the level-2+ metal
drops verbatim. No scrap metal is placed; rubble and planks are unchanged. (Crystal is
already never dropped.)

## D4 — Hide the unfinished recipes and tools

Add `ENABLE_ADVANCED_CRAFTING = False` to `constants.py`. In `game.py`'s crafting
overlay (the `for … enumerate(RECIPES)` loop ~884 and the tools row), render only the
**visible** set when the flag is off: keep the finished items (Block, Bridge) and hide
Bell / Barricade / Portal Pair / Compass and the tools Hammer / Chisel / Runestone.
Recipe *indices* used by `craft()` must stay valid — filter for **display** only, do
not reorder `RECIPES`. Keys and materials sections are unchanged.

> **Open question Q2** — with rubble→credit (D2) and auto-craft bridges (spec 0072),
> the `Block` and `Bridge` recipes are effectively automatic; should the crafting
> overlay still list them, or is it now vestigial enough to hide entirely in the
> tester build? This spec keeps Block + Bridge visible; confirm.

## D5 — Verification

There is a pytest suite (event traces, goldens, world unit tests). The rename is
broad, so:

1. **Rename safety** — `grep` proves no `stone_wall` / `place_wall` / `WALLS` /
   `_place_credits` / `quick_place_wall` references remain outside the intentionally
   kept set; `poe test` passes with the renamed symbols. Event-trace goldens
   (`'wall_placed'→'block_placed'`) and the HUD screenshot goldens (`WALLS→BLOCK`) are
   re-recorded and reviewed.
2. **Rubble credit** — a world unit test: collecting two rubble raises `_block_credits`
   by 1 with a `'credit_earned'` emit and leaves `inventory.materials['rocks'] == 0`;
   one rubble leaves a half (`_block_halves == 1`, no credit). Mining still works
   alongside (a wall + a rubble = one credit).
3. **Metal gate** — a generation test: with `ENABLE_METAL = False`, no generated room
   lists a `metal` material across a seed sweep; flipping the flag restores it.
4. **Crafting UI gate** — a render/headless test: the crafting overlay lists no
   hidden recipe/tool with `ENABLE_ADVANCED_CRAFTING = False`.
5. **Manual check** — Daniel plays the tester build and confirms: the HUD reads
   `BLOCK`; mining walls and collecting rubble both fill it (half at a time); SPACE
   places a block; no scrap metal appears; the crafting screen shows only finished
   content.

## Out of scope

- **BL-54** (metal-reinforced blocks vs the forge) — depends on metal being re-enabled;
  separate spec.
- **BL-18** (4-plank bridges / wooden-door = half a bridge) — separate spec.
- Re-enabling the advanced economy; designing the eventual rocks/metal/crystal recipes.
- Changing `_break_wall` / `'wall_broken'` / the forge's break mechanic (naming aside).

## Open questions

- **Q1** — rubble → credit-only vs. also into inventory (spec assumes credit-only).
- **Q2** — keep Block/Bridge in the crafting overlay or hide the now-automatic menu
  entirely (spec keeps them).
- **Q3** — HUD label `BLOCK` vs `BLOCKS` (spec uses `BLOCK`, matching the singular
  `BRIDGE`/`SHIELD`).

## Done when:

- [ ] **D1** — user-built wall renamed to BLOCK across code/UI/sound/sprite; terrain
  walls untouched; suite green; event + label goldens re-recorded. *(commit: ____)*
- [ ] **D2** — rubble banks half a block via the shared `_earn_block_half` path
  (2 rubble = 1 block); HUD counter/half indicator update; unit test green.
  *(commit: ____)*
- [ ] **D3** — `ENABLE_METAL = False` removes scrap-metal drops (rubble/planks
  intact); generation test green. *(commit: ____)*
- [ ] **D4** — `ENABLE_ADVANCED_CRAFTING = False` hides Bell/Barricade/Portal
  Pair/Compass + Hammer/Chisel/Runestone from the crafting UI; recipe indices intact.
  *(commit: ____)*
- [ ] **D5** — tests updated/added and green, goldens re-recorded and reviewed, Daniel
  confirms the tester build in-game. *(commit: ____)*
