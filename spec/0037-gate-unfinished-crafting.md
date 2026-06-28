# Spec 0037 — Gate unfinished crafting content behind constants (BL-26)

## Status

- [ ] G1 — Loose **rubble** (`MAT_ROCKS`) and **scrap-metal** (`MAT_METAL`)
      pickups are no longer placed in generated Act 2 levels, gated by a constant.
      No floor pickup of a gated material appears across many generated levels.
      (`MAT_CRYSTAL` is already never placed — confirm and leave as-is.)
- [ ] G2 — The crafting UI hides the four currently-unbuildable recipes
      (**Bell**, **Barricade**, **Portal Pair**, **Compass**) and the tools only
      they use (**Hammer**, **Chisel**, **Runestone**), plus the now-unobtainable
      **Scrap Metal** / **Forge Crystal** material rows — gated by a constant.
      Only **Stone Wall** and **Bridge** show; navigation/craft/select still work.
- [ ] G3 — Removing rubble drops does **not** break wall placement: rocks remain
      a usable material (Stone Wall recipe + quick-place) via a starting rock
      allowance, so the player can still place stone walls with no loose rubble on
      the floor.

## Background

UGLYCRAFT ships a crafting subsystem (`crafting.py`) whose data tables describe
more content than the game actually wires up. To present a clean "unfinished but
nice" build for user testing (BL-26), the half-built content should be hidden
without deleting the tables (so it can be finished later).

### Recipes — used vs unused (`crafting.py:74-81`)

```python
RECIPES = [
    (CRAFT_STONE_WALL,  {MAT_ROCKS: 3},                  None),          # USED
    (CRAFT_BRIDGE,      {MAT_PLANKS: 2},                 None),          # USED
    (CRAFT_BELL,        {MAT_METAL: 3},                  TOOL_HAMMER),   # unused
    (CRAFT_BARRICADE,   {MAT_ROCKS: 2, MAT_PLANKS: 1},   TOOL_CHISEL),   # unused
    (CRAFT_PORTAL_PAIR, {MAT_CRYSTAL: 2},                TOOL_RUNESTONE),# unused
    (CRAFT_COMPASS,     {MAT_METAL: 1, MAT_CRYSTAL: 1},  TOOL_RUNESTONE),# unused
]
```

- **Used:** `CRAFT_STONE_WALL` (Stone Wall, rocks→quick-place) and `CRAFT_BRIDGE`
  (Bridge, planks). Both require **no tool**. Bridge is consumed by
  `_try_auto_bridge` (`game.py:967-975`); Stone Wall by `_act2_place`
  (`game.py:863-880`).
- **Unused:** Bell, Barricade, Portal Pair, Compass. Each requires a tool, and
  **no tool is ever placed in any level** — `grep` for `add_tool` / `.tools`
  across `levelgraph.py`, `levels.py`, `levellayout.py` returns nothing. Tools are
  only ever *displayed* (`Inventory.tools` starts empty, `crafting.py:125`).
  Therefore these four recipes are **permanently uncraftable** today: `can_craft`
  short-circuits on the missing tool (`crafting.py:150-152`).

### Tools (`crafting.py:28-42`)

`TOOL_HAMMER`, `TOOL_CHISEL`, `TOOL_RUNESTONE` exist only as names/icons and are
used solely by the four unused recipes above. With no placement path they are
dead — the Tools panel (`game.py:1461-1475`) always renders them greyed out.

### Materials (`crafting.py:7-17`) and where pickups are placed

| Material | Display | Used by | Placed as loose pickup? |
|---|---|---|---|
| `MAT_ROCKS` | Rocks | **Stone Wall** (used), Barricade (unused) | **Yes** — `add_materials` |
| `MAT_PLANKS` | Planks | **Bridge** (used), Barricade (unused) | Yes — via `add_water_room` only |
| `MAT_METAL` | Scrap Metal | Bell, Compass (both unused) | **Yes** — `add_materials` |
| `MAT_CRYSTAL` | Forge Crystal | Portal Pair, Compass (both unused) | **No** — never in any `material_types` |

Loose-material distribution happens in the live builder path
`LevelGraphBuilder.add_materials` (`levelgraph.py:633-642`), called from the
feature-set build at `levelgraph.py:435`:

```python
def add_materials(self, mat_types, count) -> None:
    if not mat_types:
        return
    mats = [m for m in mat_types if m != 'planks']  # planks only via add_water_room
    if not mats:
        return
    all_nodes = list(self._graph.nodes.keys())
    for _ in range(count):
        t = self._rng.choice(all_nodes)
        self._graph.nodes[t].materials.append((self._rng.choice(mats),))
```

`mat_types` comes from each feature set's `material_types`
(`levels.py:203,215,228,…`): level 11 is `[MAT_ROCKS, MAT_PLANKS]`; levels 12-20
are `[MAT_ROCKS, MAT_PLANKS, MAT_METAL]`. **No feature set lists `MAT_CRYSTAL`**,
so Forge Crystal is already never dropped. Planks are excluded here (placed
precisely for water crossings by `add_water_room`).

> Note: the older `_assign_items` (`levelgraph.py:688-802`) is dead code —
> its header reads "*formerly _assign_items — replaced by LevelGraphBuilder*".
> Gating only the live `add_materials` path is sufficient; `_assign_items` is not
> reached.

Placed materials flow to runtime as `(col, row, mat_type)` per room in the level
dict, are drawn as floor sprites (`game.py:1318-1319`), and are picked up into
`inv.materials` by `_collect_materials` (`game.py:536-547`).

### The caveat — `MAT_ROCKS` is also the **used** wall source

Stone-wall placement in Act 2 (`_act2_place`, `game.py:867-880`) either consumes
a pre-crafted Stone Wall **or** auto-crafts one from rocks via
`Inventory.can_quick_place_wall` / `quick_place_wall` (`crafting.py:176-187`),
which spend 3 `MAT_ROCKS`. The Stone Wall recipe itself is `{MAT_ROCKS: 3}`. So
simply suppressing rubble drops with no other rock source would leave the player
permanently at 0 rocks → **Stone Wall becomes uncraftable / unplaceable**,
breaking USED content. This must be resolved (G3), not ignored.

(The separate Act 1 wall-break credit system — `_place_credits`, `_place_wall` at
`game.py:855-861` — is independent of rocks and is out of scope here.)

## Resolution

Add gating constants to `constants.py` (it has no `MAT_*` import, so no circular
dependency with `crafting.py`, which imports `constants`). The visibility helpers
live in `crafting.py`; the drop suppression lives in `levelgraph.py`; the
allowance and menu rework live in `game.py`.

### New constants (`constants.py`, in the Act 2 block)

```python
# ── Unfinished-content gating for test builds (BL-26 / spec 0037) ─────────────
DROP_LOOSE_ROCKS  = False   # suppress rubble (MAT_ROCKS) floor pickups
DROP_LOOSE_METAL  = False   # suppress scrap-metal (MAT_METAL) floor pickups
SHOW_UNFINISHED_RECIPES = False  # show Bell/Barricade/Portal Pair/Compass + their tools
ACT2_STARTING_ROCKS = 9     # rocks granted at Act 2 start so Stone Wall stays usable
```

Setting any flag back to `True` (or raising `SHOW_UNFINISHED_RECIPES`) restores
the original behaviour, so nothing is deleted — only gated.

### G1 — suppress loose rubble and scrap-metal drops

Filter the disabled material types in the single live placement point,
`LevelGraphBuilder.add_materials` (`levelgraph.py:633-642`): after the existing
`planks` exclusion, also drop `MAT_ROCKS` when `not DROP_LOOSE_ROCKS` and
`MAT_METAL` when `not DROP_LOOSE_METAL`. If the resulting `mats` list is empty,
return without placing (the existing `if not mats: return` already handles this).
Forge Crystal needs no change (never listed). This stops the materials from ever
entering `node.materials`, so they never reach the level dict, the floor, or the
pickup path.

> Determinism note: filtering changes how many `self._rng.choice` calls fire, so
> generated levels differ from pre-gating seeds. Acceptable — this is a content
> gate, and Act 2 levels are regenerated per game anyway (`kb/architecture.md`,
> lazy Act 2 generation).

### G2 — hide unused recipes, tools, and dead material rows

Add pure helpers to `crafting.py` that preserve the **original `RECIPES` indices**
(the menu's `can_craft(idx)` / `craft(idx)` / `_inv_cursor` all index `RECIPES`
directly — `game.py:894-901`), so the gate is purely presentational:

```python
ENABLED_CRAFT_TYPES = {CRAFT_STONE_WALL, CRAFT_BRIDGE}

def visible_recipes():
    """[(orig_index, recipe), …] for recipes shown in the crafting UI."""
    if SHOW_UNFINISHED_RECIPES:
        return list(enumerate(RECIPES))
    return [(i, r) for i, r in enumerate(RECIPES) if r[0] in ENABLED_CRAFT_TYPES]

def visible_tools():
    """Tool types to show: those referenced by a visible recipe (empty when gated)."""
    return sorted({r[2] for _, r in visible_recipes() if r[2]})

def visible_materials():
    """Material types to show in the materials panel."""
    mats = [MAT_ROCKS, MAT_PLANKS]
    if DROP_LOOSE_METAL or SHOW_UNFINISHED_RECIPES:
        mats.append(MAT_METAL)
    if SHOW_UNFINISHED_RECIPES:
        mats.append(MAT_CRYSTAL)
    return mats
```

Rework the crafting overlay (`game.py:_render_inventory`, 1418-1599):

- **Recipes** (`game.py:1507`): iterate `visible_recipes()`, using the returned
  original index `i` for `inv.can_craft(i)` and the active-item check, and the
  enumeration position for vertical layout (`y = ry + pos * ROW_H`).
- **Cursor** (`game.py:891-901`): make `_inv_cursor` a position into the **visible**
  list — clamp `K_DOWN` to `len(visible_recipes()) - 1`, and map the cursor
  position to the original recipe index for `can_craft` / `craft` /
  `active_item`. With gating on, the visible list is `[Stone Wall, Bridge]`.
- **Tools panel** (`game.py:1461-1475`): iterate `visible_tools()`. With gating on
  this is empty → omit the "Tools" header and panel entirely.
- **Materials panel** (`game.py:1441-1453`): iterate `visible_materials()` instead
  of all of `MATERIAL_NAMES`, so Scrap Metal and Forge Crystal rows disappear.

Used content (Stone Wall, Bridge, Rocks, Planks) stays fully visible and working.

### G3 — keep Stone Wall / quick-place working without rubble drops

Decision: **grant a per-game starting rock allowance** rather than dropping rubble
or reworking the quick-place source. This keeps the *used* rocks→Stone Wall path
exactly as designed (recipe, `can_quick_place_wall`, `_act2_place` all unchanged),
keeps the Rocks row meaningful in the materials panel (non-zero count), and simply
removes rubble from the floor.

Seed `Inventory.materials[MAT_ROCKS] = ACT2_STARTING_ROCKS` when the Act 2
inventory is created (`Inventory.__init__`, `crafting.py:118-128`, importing the
constant). `ACT2_STARTING_ROCKS = 9` yields three quick-placed stone walls
(3 rocks each) — enough for testing, matching the count of starting lives in feel.
No change to `quick_place_wall`, `can_quick_place_wall`, the Stone Wall recipe, or
`_act2_place`.

## Verification

**Automated (pytest, pure logic):**

1. **G1 drop suppression** — generate many Act 2 levels across multiple seeds and
   all feature sets; assert no room's `materials` list (and no level-dict material
   pickup) contains `MAT_ROCKS` or `MAT_METAL` while the flags are `False`, and
   that `MAT_CRYSTAL` never appears either. With the flags forced `True`, assert
   the materials *can* appear again (gate is reversible).
2. **G2 recipe/tool gate** — assert `visible_recipes()` returns exactly the
   Stone Wall and Bridge entries (with their original indices 0 and 1) and
   excludes Bell/Barricade/Portal Pair/Compass while `SHOW_UNFINISHED_RECIPES`
   is `False`; assert `visible_tools()` is empty and `visible_materials()`
   excludes `MAT_METAL`/`MAT_CRYSTAL`. With the flag `True`, all six recipes and
   three tools are returned.
3. **G3 allowance** — assert a freshly created `Inventory` has
   `materials[MAT_ROCKS] == ACT2_STARTING_ROCKS` and that
   `can_quick_place_wall()` is `True`, and that after `quick_place_wall()` three
   rocks are consumed.

**Manual (visual, user acceptance):** `poe run --level 11`, open the crafting
menu (Tab). Confirm: only **Stone Wall** and **Bridge** appear under Recipes; no
Tools panel; the Materials panel shows only Rocks and Planks; Rocks starts at a
non-zero count. Walk the level and confirm **no rubble or scrap-metal pickups** lie
on the floor. Stand on an open tile and place a stone wall (select Stone Wall,
Space) to confirm quick-place still works.

> Out of scope: disabling the crafting menu / "B" build action entirely is a
> separate idea tracked under **BL-28** — cross-reference only; this spec keeps the
> menu present and functional for the two used recipes.

## Done when:

- [ ] G1 — Loose `MAT_ROCKS` and `MAT_METAL` pickups never appear in generated
      levels while gated; `MAT_CRYSTAL` confirmed already absent; reversible by
      flag. Property test green. —
- [ ] G2 — Crafting UI shows only Stone Wall + Bridge (no Bell/Barricade/Portal
      Pair/Compass, no Tools panel, no Scrap Metal/Forge Crystal rows); navigation,
      craft, and select operate on the correct recipe indices; reversible by flag.
      Helper unit tests green; user-confirmed visual. —
- [ ] G3 — Stone Wall stays craftable and quick-placeable with no loose rubble on
      the floor via the starting rock allowance; allowance test green;
      user-confirmed a stone wall can still be placed. —
