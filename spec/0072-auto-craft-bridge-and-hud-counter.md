# Spec 0072 — Auto-craft bridges from planks + HUD BRIDGE counter (with a HUD element-list refactor)

Backlog: **BL-28 (P2)**. Two user-facing changes plus one engineering cleanup the
user explicitly asked for while handling BL-28:

1. **Auto-craft on water bump.** Bridges are already auto-*placed* when the player
   bumps a water tile holding a crafted bridge. Extend this so bumping water also
   auto-*crafts* the bridge from planks (2 planks) when no crafted bridge is held —
   one action, no crafting menu — mirroring the existing quick-place-wall path.
2. **HUD BRIDGE counter** left of the WALLS counter, shown only when the level
   contains planks, otherwise omitted and its space redistributed (the spec 0071
   key-strip conditional-visibility convention).
3. **HUD element-list refactor.** The current `_render_hud` builds a list of
   `(text, colour)` tuples and then splices the key-strip surface in by a hard-coded
   `imgs.insert(4, …)`. Adding a second conditional element (BRIDGE) on top of that
   magic index is fragile. Replace it with a single ordered list of already-rendered
   surfaces, built in display order with inline conditional inclusion — so both the
   key strip (0071) and the bridge counter route through one uniform mechanism.

## Status checklist

- [ ] **D1** — Bumping a water tile with no crafted bridge but ≥ 2 planks
  auto-crafts a bridge from the planks and places it in the same action (no menu);
  all existing bridge guards (one-per-water-room, far-side-open, no plate-adjacent
  landing) still hold. Implemented via a new `Inventory.can_quick_bridge()` /
  `quick_bridge()` pair mirroring `can_quick_place_wall()` / `quick_place_wall()`.
- [ ] **D2** — HUD shows a `BRIDGE N` counter immediately left of `WALLS`, present
  only when the level contains planks (`World._level_has_planks`); a level with no
  planks omits it and the even-spacing loop redistributes the space. Never reflows
  during play.
- [ ] **D3** — `_render_hud` refactored: one ordered list of `pygame.Surface`
  entries built in display order, conditional elements appended-or-skipped inline
  (no `imgs.insert(<magic index>)`). Key strip and bridge counter are each a helper
  returning a Surface or `None`. HUD output is pixel-identical to before for levels
  without planks (pure refactor for the existing elements).
- [ ] **D4** — Verification: headless assertions for the auto-craft path and the
  counter's per-level presence/width; screenshot goldens for a planks level (with
  the BRIDGE counter) re-recorded and reviewed; user confirmation in-game.

## Background — confirmed facts

Established by reading the code while writing this spec (self-contained; do not
re-derive):

### Bridge placement today (`world.py` `_try_auto_bridge`, lines 536–572)

Called from the movement/bump path (`world.py:242`). Current logic, in order:

1. `if not self.cells.is_water(col, row): return False`.
2. `water_room = self.cells.water_room(col, row) or (col, row)`; if that room is in
   `self._bridged_water_rooms`, `return False` — **one bridge per water room**
   (spec 0029 W2): once a room is reachable no further bridge to it can be built, so
   a bridge can never be wasted.
3. Reject if any pressure **plate** is orthogonally adjacent to the target tile —
   a solved puzzle (block parked on the plate) must not seal the new passage
   (spec 0049).
4. **`if not self.inventory.has_item(CRAFT_BRIDGE): return False`** ← the gate D1
   loosens.
5. Far-side-open check: the tile directly beyond the water (same direction as the
   player→water step) must be in-bounds and `not self.blocked(...)`.
6. On success: `inventory.use_item(CRAFT_BRIDGE)`, `cells.add_bridge((col,row))`,
   `_bridged_water_rooms.add(water_room)`, `_emit('bridge_built')`, `return True`.

### Crafting model (`crafting.py`)

- `RECIPES[1] = (CRAFT_BRIDGE, {MAT_PLANKS: 2}, None)` — a bridge costs **2 planks**,
  no tool. `MAT_PLANKS = 'planks'`.
- `can_craft(idx)` / `craft(idx)` operate by recipe index; `craft` consumes
  materials and increments `crafted[result]`.
- `has_item(t)` = `crafted.get(t,0) > 0`; `use_item(t)` decrements it.
- **Precedent — the wall path already does exactly this pattern.** For stone walls,
  `can_quick_place_wall()` returns `materials[MAT_ROCKS] >= 3`, and
  `quick_place_wall()` consumes 3 rocks (falling back to a pre-crafted
  `CRAFT_STONE_WALL` item if raw rocks are short). D1 adds the bridge analogue so the
  two auto-craft-and-place flows are symmetric rather than one-off.

### Planks in level data

Room dicts carry a `'materials'` list of `(col, row, mat_type)` tuples, where
`mat_type` is the material **string** (`'planks'`, etc.) — see
`levellayout.py:2224–2226` (`for (mat_type,) in plank_mats: materials.append((c, r,
mat_type))`) and `world.py:458` (`inventory.add_material(item.payload)`). Planks are
provisioned **only** by `add_water_room` (`levelgraph.py:699–707`, 2 planks in an
already-reachable dry room); `add_materials` explicitly excludes planks
(`levelgraph.py:757`). So "the level contains planks" ⇔ "the level has a water room
to bridge", which is exactly when a BRIDGE counter is meaningful.

### HUD rendering today (`game.py` `_render_hud`, lines 719–778)

Single row at `y = ROWS*TILE = 512`, height `STATUS_H = 28`. It builds `elems` as a
list of `(text, colour)` tuples in display order:

`SCORE` · `LEVEL` · `LIVES` · (`SEEK:`‹padded› **or** `LOOT c/t`) · [`BOSS`|`HARD`] ·
`SHIELD` · `WALLS`.

Then it renders each to `imgs`, and **splices the key strip in by index**:
`strip = self._hud_key_strip(); if strip is not None: imgs.insert(4, strip)`.
Finally it even-spaces `imgs` across `LOGICAL_W = 960` with `margin = 10` and a
computed `gap`, each image vertically centred by its own height
(`cy = hud_y + (STATUS_H - h)//2`).

- `WALLS N.` colour: `LTGREEN` if `_place_credits > 0`, `YELLOW` if
  `_breaks_toward_credit > 0` (partial credit mined), else `GRAY`; a trailing `.`
  marks partial progress. `SHIELD` is always present (drawn in `HUD_BG` — invisible —
  when inactive) so the layout never shifts.
- **The `imgs.insert(4, strip)` magic index is the fragility.** `4` happens to equal
  "after the four always-present leading elements (SCORE/LEVEL/LIVES/SEEK-or-LOOT)
  and before the optional BOSS/HARD cluster". Adding a second conditional element
  (BRIDGE) forces a second position that must account for whether the strip was
  inserted — brittle and order-coupled. D3 removes it.

### `_level_key_colours` precedent (`world.py:299–304`)

Computed once at level load as the union of key colours over
`data['rooms'][*]['keys']`, ordered by `KEY_NAMES`; exposed to `game.py` through the
`_WORLD_ATTRS` delegation tuple (`game.py:1228`), which turns each name into a
read-only `world.<name>` property on `Game`. `_level_has_planks` (D2) follows this
pattern exactly.

## D1 — Auto-craft-and-place a bridge from planks

Add to `Inventory` (`crafting.py`), directly mirroring the wall pair:

```python
def can_quick_bridge(self):
    """Enough planks (or a pre-crafted bridge) to build a bridge in one action."""
    return self.materials.get(MAT_PLANKS, 0) >= 2 or self.has_item(CRAFT_BRIDGE)

def quick_bridge(self):
    """Consume a bridge for placement: prefer raw planks, else a crafted bridge."""
    if self.materials.get(MAT_PLANKS, 0) >= 2:
        self.materials[MAT_PLANKS] -= 2
        return True
    if self.has_item(CRAFT_BRIDGE):
        return self.use_item(CRAFT_BRIDGE)
    return False
```

(Matches `can_quick_place_wall`/`quick_place_wall`, which prefer raw materials and
fall back to the crafted item.)

In `world.py` `_try_auto_bridge`, replace the two-step
`if not has_item(CRAFT_BRIDGE): return False` … `use_item(CRAFT_BRIDGE)` with the
quick-bridge pair, **keeping the guard order** so no plank is spent on a rejected
placement:

- Change the gate (step 4) to `if not self.inventory.can_quick_bridge(): return
  False`.
- Perform the far-side-open check (step 5) **before** consuming, exactly as now.
- On success, call `self.inventory.quick_bridge()` in place of
  `use_item(CRAFT_BRIDGE)`; everything else (`add_bridge`, `_bridged_water_rooms`,
  `_emit('bridge_built')`) is unchanged.

Add `MAT_PLANKS` to the `from crafting import …` line in `world.py`.

The one-bridge-per-water-room lock, the plate-adjacency guard, and the far-side
check are all unchanged — planks are consumed **only** on a placement that would
have succeeded with a crafted bridge.

## D2 — HUD BRIDGE counter

**Level-presence flag.** Add to `world.py`, in the same block that computes
`_level_key_colours`:

```python
self._level_has_planks = any(
    m[2] == MAT_PLANKS
    for rdata in data['rooms'].values()
    for m in rdata.get('materials', [])
)
```

Expose it by appending `'_level_has_planks'` to `_WORLD_ATTRS` in `game.py`.

**Counter value.** The number shown is the player's current **bridge capacity** —
crafted bridges plus whole bridges' worth of planks:

```
capacity = inventory.crafted.get(CRAFT_BRIDGE, 0) + inventory.materials[MAT_PLANKS] // 2
```

A single leftover plank (`planks % 2 == 1`) is "half a bridge banked", shown with a
trailing `.` exactly like the WALLS half-credit dot. Colour parallels WALLS:
`LTGREEN` if `capacity > 0`, `YELLOW` if `capacity == 0` but a half-plank is banked,
else `GRAY`. Rendered as `BRIDGE N` (2-wide right-padded N, matching the `WALLS N.`
field), so the field width is stable.

> **Decision needed (Q1):** capacity (`crafted + planks//2`, decrements as planks
> are spent — recommended, most informative) vs. a raw crafted-bridge count
> (`crafted[CRAFT_BRIDGE]`, which with auto-craft is almost always 0 and therefore
> near-useless). This spec assumes **capacity**; confirm before implementation.

**Placement & visibility.** Insert the counter immediately **left of** `WALLS` (per
BL-28). Present only when `_level_has_planks` is true; otherwise the helper returns
`None` and the element is skipped, letting the even-spacing loop redistribute the
space — the spec 0071 convention. Because `_level_has_planks` is fixed per level, the
counter's presence and field width are constant within a level, so the HUD never
reflows as planks/bridges are gained or spent.

## D3 — HUD element-list refactor (remove the magic-index splice)

Rebuild `_render_hud` so the element list is a single ordered sequence of
already-rendered `pygame.Surface`s, constructed top-to-bottom in display order with
conditional entries appended or skipped **in place** — no post-hoc index insertion.

Sketch:

```python
def _hud_text(self, txt, col):
    return self.font_hud.render(txt, True, col)

# in _render_hud, after computing colours/strings:
parts = [
    self._hud_text(f"SCORE {self.score:>7}", HUD_TEXT),
    self._hud_text(f"LEVEL {self.level:>2}",  HUD_TEXT),
    self._hud_text(f"LIVES {self.lives:>2}",  HUD_LIFE),
]
parts.append(self._hud_text(loot_txt, GOLD) if self.spawn_mode == 'preplaced'
             else self._hud_text(seek_txt, HUD_TEXT))
strip = self._hud_key_strip()
if strip is not None:
    parts.append(strip)                          # keys, after SEEK/LOOT (0071)
if self.level == ACT1_BOSS_LEVEL:
    parts.append(self._hud_text("BOSS", MAGENTA))
elif self.difficulty == HARD:
    parts.append(self._hud_text("HARD", RED))
parts.append(self._hud_text(shield_txt, shield_col))
bridge = self._hud_bridge_counter()              # BL-28, may be None
if bridge is not None:
    parts.append(bridge)                         # left of WALLS
parts.append(self._hud_text(walls_txt, wall_color))
# even-space `parts` (each already a Surface) exactly as today
```

`_hud_bridge_counter()` returns a rendered Surface or `None`, matching
`_hud_key_strip()`'s shape, so "conditional HUD element" has exactly one idiom in the
file: *a helper returning `Surface | None`, appended only when non-`None`.*

**Constraint:** for any level **without** planks the produced `parts` list, and
therefore the rendered HUD, must be byte-for-byte identical to today's output — the
key strip stays at the same position (after SEEK/LOOT, before BOSS/HARD) and no new
element appears. This is a pure refactor for every existing element; only the
planks-level BRIDGE counter is new. The existing HUD screenshot goldens
(`test_shot_hud*`) must pass **without** re-recording for keyless/plankless levels.

## D4 — Verification

No general gameplay suite; use the headless `Harness` + screenshot goldens
(`tests/test_render.py`, spec 0044/0071 pattern).

1. **Auto-craft headless** — `test_auto_bridge_from_planks`: a world where the player
   holds 2 planks and no crafted bridge, standing next to a bridgeable water tile;
   bumping the water builds the bridge (`cells.is_bridge` at the tile), consumes the
   2 planks (`materials['planks'] == 0`), locks the water room, and emits
   `'bridge_built'`. A companion `test_auto_bridge_prefers_crafted`: with 1 crafted
   bridge **and** 2 planks, the crafted bridge is spent first (planks untouched).
   And `test_auto_bridge_insufficient`: 1 plank, no crafted bridge ⇒ no bridge, no
   plank spent, water room still unlocked.
2. **Guards intact** — reuse/extend existing bridge tests to confirm the
   one-per-water-room lock, plate-adjacency rejection, and far-side-open check still
   hold when the source is planks rather than a crafted item (no plank spent on a
   rejected placement).
3. **Counter headless** — `test_hud_bridge_counter_present_with_planks` (a planks
   level exposes `_level_has_planks is True` and `_hud_bridge_counter()` returns a
   Surface) and `test_hud_bridge_counter_absent_without_planks` (a plankless level ⇒
   `_level_has_planks is False`, helper returns `None`).
4. **Refactor safety** — the existing HUD goldens for keyless and keyed levels pass
   **unchanged** (proves D3 is behaviour-preserving for existing elements).
5. **HUD golden (new)** — `test_shot_hud_bridge`: a playing frame over a planks level
   showing the `BRIDGE N` counter left of `WALLS`. Re-record with
   `UGLYCRAFT_REGOLD=1` and review the diff by eye.
6. **Manual check** — Daniel plays a level with a water room and confirms: bumping
   water with only planks builds a bridge without opening the menu; the BRIDGE
   counter shows the right number, decrements on use, sits left of WALLS, and is
   absent on levels with no planks.

## Out of scope

- **BL-18** (4-plank bridges / mixed plank sources / single-plank item): this spec
  keeps the 2-plank recipe. If Q1/Q2 decisions imply provisioning changes, file
  against BL-18.
- The `>7` locked-door colour-pool edge (unrelated).
- Any change to the WALLS counter, SHIELD, or other HUD elements beyond the
  structural refactor.
- Auto-craft for anything other than bridges and the existing walls.

## Open questions

- **Q1** — BRIDGE counter value: **capacity** (`crafted + planks//2`, recommended)
  vs. raw crafted count. Spec assumes capacity.
- **Q2** — Should the BRIDGE counter carry the half-bridge `.` dot + YELLOW/partial
  colour parallel to WALLS, or stay a plain `LTGREEN/GRAY` count? Spec assumes the
  full WALLS-parallel treatment.

## Done when:

- [ ] **D1** — `Inventory.can_quick_bridge()`/`quick_bridge()` added; water-bump
  auto-crafts a bridge from 2 planks (menu-free) and prefers a crafted bridge when
  present; all bridge guards intact; no plank spent on a rejected placement.
  *(commit: ____)*
- [ ] **D2** — `World._level_has_planks` computed at load and delegated; `BRIDGE N`
  counter renders left of WALLS only on planks levels, omitted (space redistributed)
  otherwise; never reflows during play. *(commit: ____)*
- [ ] **D3** — `_render_hud` builds one ordered `Surface` list with inline
  conditional inclusion; the `imgs.insert(<magic index>)` splice is gone; HUD output
  is identical for plankless/keyless levels (existing goldens pass unchanged).
  *(commit: ____)*
- [ ] **D4** — Auto-craft + counter-presence headless assertions pass; existing HUD
  goldens pass unchanged; the new planks-level HUD golden is recorded and reviewed;
  Daniel confirms the behaviour in-game. *(commit: ____)*
