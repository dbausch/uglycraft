# Spec 0041 — Auto-craft a bridge on bumping water + HUD bridge counter (BL-28)

## Status

- [ ] A1 — Bumping a water tile auto-**crafts** a bridge from planks when none is
      held, then places it, in one action (no crafting menu). The existing
      one-bridge-per-water-room lock (spec 0029 W2) and far-side-open check are
      unchanged; planks are only consumed when a bridge is actually placed
- [ ] A2 — HUD shows a **BRIDGE** counter immediately to the **LEFT** of the
      existing **WALLS** counter, reporting how many bridges the player can place
      right now (bridges held + bridges craftable from planks)
- [ ] A3 — *(optional, secondary)* The crafting menu (TAB → `INVENTORY`) is gated
      behind a module constant so it can be hidden for the user-test build; ties
      in with BL-26's "hide unfinished content" constants

## Background

### Current auto-bridge behaviour (`game.py` `_try_auto_bridge`, lines 947–981)

Today a bridge is auto-**placed** on bumping water only if the player already
**holds** a crafted bridge. The relevant guards, in order:

```python
def _try_auto_bridge(self, col, row):
    if not self._is_multiroom:
        return False
    water = getattr(self, '_water_tiles', set())
    if (col, row) not in water:
        return False
    water_room = getattr(self, '_water_tile_room', {}).get((col, row), (col, row))
    if water_room in self._bridged_water_rooms:        # ← W2 lock (line 965)
        return False
    if not self.inventory.has_item(CRAFT_BRIDGE):      # ← held-only check (line 967)
        return False
    # far-side-open check (lines 969–974)
    pc, pr = self.player.col, self.player.row
    dc, dr = col - pc, row - pr
    far_c, far_r = col + dc, row + dr
    if (0 < far_c < COLS - 1 and 0 < far_r < ROWS - 1
            and not self.walls[far_c][far_r]):
        self.inventory.use_item(CRAFT_BRIDGE)          # ← consume (line 975)
        self._bridged_tiles.setdefault(self._current_room, set()).add((col, row))
        self._bridged_water_rooms.add(water_room)      # ← arm W2 lock (line 977)
        self._build_walls_multiroom()
        self.sounds.play('place_wall')
        return True
    return False
```

The **W2 one-bridge-per-water-room lock** is `self._bridged_water_rooms`
(initialised at `game.py:314`); `_water_tile_room` maps every water tile to the
single room behind its `WATER` edge (spec 0029 W4). Once a water room is bridged,
no further bridge to it can be built, so a bridge can never be wasted.

### The bridge recipe (`crafting.py`)

```python
CRAFT_BRIDGE = 'bridge'                                 # crafting.py:47
RECIPES = [
    (CRAFT_STONE_WALL,  {MAT_ROCKS: 3},   None),        # index 0
    (CRAFT_BRIDGE,      {MAT_PLANKS: 2},   None),        # index 1  ← bridge
    ...
]
```

The bridge recipe is **`RECIPES[1]`** — result `CRAFT_BRIDGE`, cost **2 planks**
(`MAT_PLANKS: 2`), **no tool**. Inventory helpers (`crafting.py:149–174`):

- `can_craft(recipe_idx)` — True if the materials (and tool, if any) suffice.
- `craft(recipe_idx)` — consumes the materials, increments `crafted[result]`.
- `has_item(craft_type)` — `crafted.get(craft_type, 0) > 0`.
- `use_item(craft_type)` — decrements `crafted[craft_type]` if > 0.

There is already a precedent for "auto-craft on place" for the **stone wall**:
`_act2_place` (`game.py:863–880`) uses a held wall, else `can_quick_place_wall()`
/ `quick_place_wall()` (`crafting.py:176–184`, 3 rocks). The bridge currently has
**no** equivalent auto-craft path — it must be crafted by hand in the menu first.

### The HUD counter render (`game.py` `_render_hud`, lines 1345–1396)

The HUD is a single evenly-spaced row of `elems`, each `(text, colour)`, rendered
with `font_hud` and laid out by computing a uniform `gap`. The **WALLS** element
is appended **last** (line 1386):

```python
walls_dot = '.' if self._breaks_toward_credit > 0 else ' '
elems = [
    (f"SCORE {self.score:>7}", HUD_TEXT),
    (f"LEVEL {self.level:>2}",  HUD_TEXT),
    (f"LIVES {self.lives:>2}",  HUD_LIFE),
]
if self._is_multiroom:
    elems.append((f"LOOT {self._loot_collected:>2}/{self._loot_total}", GOLD))
else:
    elems.append((f"SEEK: {item_name:<{max_name}}", HUD_TEXT))
...
elems.append((shield_txt, shield_col))
elems.append((f"WALLS {self._place_credits:>2}{walls_dot}", wall_color))   # last
```

Wall colour logic (lines 1349–1354): `LTGREEN` if `_place_credits > 0`, `YELLOW`
if mid-progress, else `GRAY`. There is currently **no bridge element**.

### The crafting menu (`game.py`)

Opened with **TAB** while in `PLAYING` multiroom (`game.py:789–792`):
`self.state = INVENTORY`, music paused. Handled by `_inventory_event`
(`game.py:883+`) and rendered from `RECIPES` (`game.py:1507+`). BL-26 already
calls for gating unfinished recipes/tools behind constants; with bridges
auto-crafted on bump and stone walls quick-placed, the menu becomes unnecessary
for the user-test build.

## Resolution

### A1 — Auto-craft then place on bump

In `_try_auto_bridge`, **before** the held-bridge check, attempt an auto-craft so
that holding raw planks is sufficient. Replace the single `has_item` guard with an
ensure-a-bridge-is-available step that does **not** yet consume anything:

```python
BRIDGE_RECIPE_IDX = 1   # RECIPES index of CRAFT_BRIDGE (define near imports / in crafting.py)

# ... after the W2 lock check, before the far-side check:
if not self.inventory.has_item(CRAFT_BRIDGE):
    if not self.inventory.can_craft(BRIDGE_RECIPE_IDX):   # < 2 planks and none held
        return False
    self.inventory.craft(BRIDGE_RECIPE_IDX)               # consumes 2 planks → crafted bridge
# now a crafted bridge is guaranteed to be held; fall through to the
# UNCHANGED far-side-open check, which then use_item()s it and arms the W2 lock.
```

Key properties:

- **Order is preserved:** the W2 `_bridged_water_rooms` lock and the
  far-side-open check come exactly as today. The auto-craft is inserted only on
  the `not has_item` branch, replacing the old unconditional `return False`.
- **No waste:** planks are consumed by `craft()` only after the W2 lock and the
  water-tile checks have passed, and the resulting bridge is consumed by the
  existing `use_item(CRAFT_BRIDGE)` only when the far-side is open and the bridge
  is actually placed. If the far-side check fails, the just-crafted bridge stays
  in inventory (held) for a later bump — consistent with current held-bridge
  behaviour. (Crafting just-in-time before a failing far-side check would leave
  the player holding a bridge they didn't ask for; this is acceptable and matches
  how a hand-crafted held bridge already behaves. If undesired, the far-side
  check may be hoisted above the craft — note this as an implementation choice,
  not a scope change.)
- Reference the bridge recipe by a named index constant (e.g. `BRIDGE_RECIPE_IDX
  = 1`, ideally exported from `crafting.py` next to `RECIPES`) rather than a bare
  literal, mirroring how `CRAFT_BRIDGE` is already imported.

Net effect: bumping water with **only planks** (≥ 2) and no crafted bridge now
crafts and places a bridge in one action, with no menu step.

### A2 — HUD BRIDGE counter, left of WALLS

Add a **BRIDGE** element to `elems` **immediately before** the WALLS append
(`game.py:1386`), so it renders to the left of WALLS in the evenly-spaced row:

```python
bridges_held      = self.inventory.crafted.get(CRAFT_BRIDGE, 0)
bridges_craftable = self.inventory.materials.get(MAT_PLANKS, 0) // 2   # 2 planks each
bridges_available = bridges_held + bridges_craftable
bridge_color = LTGREEN if bridges_available > 0 else GRAY
elems.append((f"BRIDGE {bridges_available:>2}", bridge_color))   # BEFORE WALLS
elems.append((f"WALLS {self._place_credits:>2}{walls_dot}", wall_color))
```

- The counter reports **bridges the player can place right now** = bridges already
  crafted **plus** bridges craftable from current planks (`planks // 2`). This is
  the number that matters at a water tile after A1, since either source now
  yields a placement.
- Fixed-width 2-digit field (`:>2`) and `LTGREEN`/`GRAY` colouring mirror the
  WALLS element so the row stays visually consistent; layout is auto-spaced by the
  existing `gap` computation, so no manual positioning is needed.
- BRIDGE is only meaningful in Act 2; gate its append behind `self._is_multiroom`
  (the same flag already used for the LOOT element) so Act 1 is unaffected.

### A3 — *(optional, secondary)* Gate the crafting menu behind a constant

Introduce a module-level boolean constant, e.g. `CRAFTING_MENU_ENABLED` in
`constants.py` (or alongside BL-26's hide-unfinished-content constants), default
`True` for now. Check it at the **single** open site (`game.py:789`):

```python
elif k == pygame.K_TAB and self._is_multiroom and CRAFTING_MENU_ENABLED:
    self.state = INVENTORY
    ...
```

When `False`, TAB no longer opens `INVENTORY`; the player relies entirely on
auto-place (walls via `_act2_place` quick-place, bridges via A1) and the new
BRIDGE/WALLS HUD counters. This is **secondary** to A1/A2 and should land as its
own commit; it dovetails with BL-26 (which gates unused recipes/tools and loose
material drops) — the constant belongs with that family rather than being a
one-off here.

## Verification

### A1 — automated (pytest, no display)

The material/inventory accounting of "auto-craft then place" is pure `Inventory`
logic and needs no pygame display. Add a unit test that mirrors the
`_try_auto_bridge` craft-then-use sequence on an `Inventory`:

- Start with `materials[MAT_PLANKS] = 2`, no crafted bridge. Assert
  `not has_item(CRAFT_BRIDGE)`, `can_craft(BRIDGE_RECIPE_IDX)` is True; run
  `craft(BRIDGE_RECIPE_IDX)` then `use_item(CRAFT_BRIDGE)`; assert planks now `0`
  and `crafted[CRAFT_BRIDGE] == 0` (the bridge was placed).
- With only **1** plank and no bridge, assert `can_craft(BRIDGE_RECIPE_IDX)` is
  False (so `_try_auto_bridge` returns without consuming anything).
- With a bridge already held **and** 2 planks, assert the path consumes the held
  bridge and leaves planks untouched (no double-crafting).

For the **W2 one-bridge-per-water-room lock** and far-side check, exercise
`_try_auto_bridge` itself headlessly by constructing a `Game` under the dummy
video driver (`SDL_VIDEODRIVER=dummy`) on a small water level: call
`_try_auto_bridge` twice on the same water room — the second call must return
`False` and consume no planks (lock still holds). If instantiating `Game`
headlessly proves impractical, the lock is covered by the existing spec 0029 W2
machinery and may instead be confirmed by the manual run below.

Command: `poe test` (runs `pytest tests/ -v`). New tests live in the existing
suite (e.g. extend `tests/test_water_challenge.py`).

### A2 / A1 — manual visual check (`poe run`, user acceptance)

- Launch an Act 2 water level: `poe run --level 11` (any multiroom level with a
  WATER edge; pick one with planks reachable). Confirm the HUD shows **BRIDGE NN**
  immediately to the left of **WALLS NN**, with the count = held bridges + planks
  // 2, updating as planks are picked up and bridges placed.
- Pick up ≥ 2 planks **without** crafting a bridge, then bump a water tile with
  open floor on the far side: a bridge appears in one action (no menu), planks
  decrease by 2, the BRIDGE counter drops accordingly, and `place_wall` sound
  plays.
- Bump the same water room again: nothing happens (W2 lock), no planks consumed.

### A3 — manual check (`poe run`)

With `CRAFTING_MENU_ENABLED = False`, confirm TAB no longer opens the crafting
screen and bridges/walls can still be placed entirely via auto-craft, guided by
the HUD counters. With it `True`, the menu opens as before.

## Done when:

- [ ] A1 — Bumping water with only planks (≥ 2) and no held bridge auto-crafts and
      places a bridge in one action; planks consumed only on actual placement; W2
      one-bridge-per-water-room lock and far-side-open check unchanged; pytest for
      the craft-then-place accounting and the per-room lock passes. —
- [ ] A2 — HUD shows a BRIDGE counter to the left of WALLS reporting bridges held +
      craftable; updates correctly (user-confirmed via `poe run`). —
- [ ] A3 — *(optional)* Crafting menu gated behind a constant; TAB suppressed when
      disabled, bridges/walls still placeable via auto-craft (user-confirmed). —
