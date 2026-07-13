# Spec 0072 — Auto-craft bridges from planks + HUD BRIDGE counter (with an OO HBox HUD redesign)

Backlog: **BL-28 (P2)**. Two gameplay/HUD changes, one engineering redesign, and one
readability tweak the user asked for while handling BL-28:

1. **Auto-craft on water bump.** Bridges are already auto-*placed* when the player
   bumps a water tile holding a crafted bridge. Extend this so bumping water also
   auto-*crafts* the bridge from planks (2 planks) when no crafted bridge is held —
   one action, no crafting menu — mirroring the existing quick-place-wall path.
2. **HUD BRIDGE counter** left of the WALLS counter, shown only when the level
   contains planks, otherwise omitted and its space redistributed (the spec 0071
   key-strip conditional-visibility convention).
3. **HUD OO redesign (HBox).** The current `_render_hud` builds a list of
   `(text, colour)` tuples and then splices the key-strip surface in by a hard-coded
   `imgs.insert(4, …)`. Adding a second conditional element (BRIDGE) on top of that
   magic index is fragile. Redesign the HUD as a small GUI-toolkit-style **HBox**: a
   new `hud.py` module with a `HudElement` base (signals its own tight width), a
   reusable `LabelValue` element (the dominant `LABEL value` shape), an `IconStrip`
   element (the key strip), and an `HBox` that measures each element's tight width and
   evenly distributes the leftover space across the `n-1` gaps. Conditional elements
   are simply omitted from the element list — no `None` sentinel, no magic index.
4. **Subtle gap separators.** On top of the HBox, draw a faint 1 px medium-brightness
   rule vertically centred in each inter-element gap, so a right-justified value stays
   visually tied to its own label rather than drifting toward the next one.

## Status checklist

- [ ] **D1** — Bumping a water tile with no crafted bridge but ≥ 2 planks
  auto-crafts a bridge from the planks and places it in the same action (no menu);
  all existing bridge guards (one-per-water-room, far-side-open, no plate-adjacent
  landing) still hold. Implemented via a new `Inventory.can_quick_bridge()` /
  `quick_bridge()` pair mirroring `can_quick_place_wall()` / `quick_place_wall()`.
- [ ] **D2** — HUD shows a `BRIDGE N` counter immediately left of `WALLS`, present
  only when the level contains planks (`World._level_has_planks`); a level with no
  planks omits it and the HBox redistributes the space. `N` = buildable bridges
  (`planks // 2`, plus any crafted bridge); a trailing `.` marks an odd leftover
  plank (half a bridge banked), mirroring WALLS. Never reflows during play.
- [ ] **D3** — HUD redesigned as an OO HBox in a new `hud.py`: `HudElement` base
  (tight width), reusable `LabelValue`, `IconStrip` for the key strip, and an `HBox`
  that even-distributes leftover space across `n-1` gaps. Conditional elements are
  omitted from the list (no `None` sentinel, no `imgs.insert(<magic index>)`). HUD
  output is pixel-identical to before for levels without planks.
- [ ] **D4** — Subtle gap separators: the HBox draws a 1 px, medium-brightness
  horizontal line vertically centred in each of the `n-1` inter-element gaps (never
  in the outer margins), so right-justified values read against their own label. A
  deliberate visual change — existing HUD goldens are re-recorded here.
- [ ] **D5** — Verification: headless assertions for the auto-craft path and the
  counter's per-level presence/width; `hud.py` HBox/element/separator unit tests;
  HUD screenshot goldens re-recorded (separators + planks-level BRIDGE counter) and
  reviewed; user confirmation in-game.

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

**Counter value.** The number shown is the count of **buildable bridges** from what
the player is carrying — one bridge per two planks, plus any pre-crafted bridge:

```
buildable = inventory.crafted.get(CRAFT_BRIDGE, 0) + inventory.materials[MAT_PLANKS] // 2
half      = (inventory.materials[MAT_PLANKS] % 2) == 1   # one plank toward the next
```

A single leftover plank is "half a bridge banked", shown with a trailing `.` exactly
like the WALLS half-credit dot. Colour parallels WALLS: `LTGREEN` if
`buildable > 0`, `YELLOW` if `buildable == 0` but `half` is banked, else `GRAY`.
Rendered as `BRIDGE N.` (2-wide right-padded N + optional dot, matching the
`WALLS N.` field), so the field width is stable within the level. (Crafted bridges
are folded in only for completeness; with auto-craft they essentially never
accumulate, so in practice `N == planks // 2`.)

**Placement & visibility.** The counter sits immediately **left of** `WALLS` (per
BL-28). It is added to the HBox element list **only when** `_level_has_planks` is
true; on a plankless level it is simply not constructed, and the HBox redistributes
the freed space across the remaining `n-1` gaps. Because `_level_has_planks` is fixed
per level, the counter's presence and field width are constant within a level, so the
HUD never reflows as planks/bridges are gained or spent.

## D3 — HUD OO redesign: an HBox of measured elements

Replace the tuple-list-plus-`imgs.insert` machinery with a small, testable,
GUI-toolkit-style layout in a **new module `hud.py`** (presentation/pygame-side,
parallel to `sprites.py`). The layout is a horizontal box: every element reports its
own tight width; the box lays them out left→right and distributes the leftover
horizontal space evenly across the `n-1` inter-element gaps — exactly the spacing the
current HUD computes, now expressed as objects.

### Classes (`hud.py`)

```python
class HudElement:
    """One HUD item. Owns a pre-rendered surface; reports its tight width."""
    def __init__(self, surface):
        self.surface = surface
    @property
    def width(self):
        return self.surface.get_width()
    def blit(self, target, x, top, row_h):
        # vertically centred by its own height within the HUD row
        cy = top + (row_h - self.surface.get_height()) // 2
        target.blit(self.surface, (round(x), cy))


class LabelValue(HudElement):
    """The dominant `LABEL value` element (single colour).

    Renders `f"{label} {value}"`, or just `label` when value is "". Value
    padding (fixed-width fields that must not reflow) stays the caller's job
    via format strings, exactly as today.
    """
    def __init__(self, font, label, value="", color=HUD_TEXT):
        text = f"{label} {value}" if value != "" else label
        super().__init__(font.render(text, True, color))


class IconStrip(HudElement):
    """A row of fixed-width icon slots (the key strip). Builds its own surface
    from (icon, lit) pairs; width == slots * slot_w."""
    def __init__(self, slots, slot_w, icon_h, ghost_alpha):
        ...   # existing _hud_key_strip body, producing one SRCALPHA surface


class HBox:
    """Lay elements out horizontally, distributing slack across the gaps."""
    def __init__(self, width, margin=10):
        self.width, self.margin = width, margin
    def blit(self, target, elements, top, row_h):
        tight = sum(e.width for e in elements)
        gap = (self.width - 2 * self.margin - tight) / max(len(elements) - 1, 1)
        x = float(self.margin)
        for e in elements:
            e.blit(target, x, top, row_h)
            x += e.width + gap
```

### `_render_hud` becomes element construction + one `HBox.blit`

```python
def _render_hud(self):
    hud_y = ROWS * TILE
    pygame.draw.rect(self.surf, HUD_BG, (0, hud_y, LOGICAL_W, STATUS_H))
    f = self.font_hud

    elements = [
        LabelValue(f, "SCORE", f"{self.score:>7}", HUD_TEXT),
        LabelValue(f, "LEVEL", f"{self.level:>2}", HUD_TEXT),
        LabelValue(f, "LIVES", f"{self.lives:>2}", HUD_LIFE),
    ]
    if self.spawn_mode == 'preplaced':
        elements.append(LabelValue(f, "LOOT", f"{self._loot_collected:>2}/{self._loot_total}", GOLD))
    else:
        elements.append(LabelValue(f, "SEEK:", f"{item_name:<{max_name}}", HUD_TEXT))

    if self._level_key_colours:                       # keys, after SEEK/LOOT (0071)
        elements.append(self._key_strip_element())
    if self.level == ACT1_BOSS_LEVEL:
        elements.append(LabelValue(f, "BOSS", "", MAGENTA))
    elif self.difficulty == HARD:
        elements.append(LabelValue(f, "HARD", "", RED))
    elements.append(LabelValue(f, "SHIELD", shield_val, shield_col))
    if self._level_has_planks:                        # BL-28, left of WALLS
        elements.append(LabelValue(f, "BRIDGE", f"{buildable:>2}{bridge_dot}", bridge_col))
    elements.append(LabelValue(f, "WALLS", f"{self._place_credits:>2}{walls_dot}", wall_color))

    HBox(LOGICAL_W, margin=10).blit(self.surf, elements, hud_y, STATUS_H)
```

Conditional elements (`IconStrip`, `BRIDGE`) are **omitted from the list** rather than
appended-as-`None` — the "conditional HUD element" idiom is simply *don't add it*. No
magic index, no sentinel.

**Behaviour-preserving constraint (D3 alone).** `LabelValue`'s `f"{label} {value}"`
reproduces every current string byte-for-byte (`"SCORE {score:>7}"`, the
`"SHIELD   "` invisible padding, the `"WALLS N."` dot, the label-only
`"BOSS"`/`"HARD"`), the element order is unchanged, and `HBox`'s gap math is the
current computation lifted verbatim. Therefore **at the end of D3** (before the D4
separators land) the rendered HUD for any keyless/plankless level is byte-for-byte
identical to today, and the existing HUD screenshot goldens (`test_shot_hud*`) pass
**without** re-recording. This is the checkpoint that proves the refactor is a pure
restructuring; the D4 separators are the first intentional pixel change. Land D3 and
D4 as **separate commits** so the behaviour-preserving refactor is verified on its own
before any visual change. The key strip moves into `IconStrip` but produces the same
surface at the same position.

Update the architecture table in `CLAUDE.md` (now 15 files) and `kb/uglycraft-display.md`
to describe the HBox model.

## D4 — Subtle gap separators

Right-justified numeric values (`SCORE   0`, `WALLS  3.`) can visually drift toward
the *next* label. Draw a faint vertical-centre rule in each gap so each value stays
anchored to its own label. The `HBox` owns gap geometry, so it draws them.

**Geometry** (HUD row `y ∈ [ROWS*TILE, ROWS*TILE+STATUS_H) = [512, 540)`; for the gap
between element `i` (right edge `Ri = x_i + w_i`) and element `i+1` (left edge
`Ri + G`, where `G` is the computed even gap)):

```
 element i                    gap = G px                    element i+1
 ┌──────────┐                                              ┌──────────┐
 │ SCORE   0│                                              │ LEVEL  1 │
 └──────────┘                                              └──────────┘
 x_i       Ri = x_i + w_i                                  L = Ri + G
            |<- inset ->|——————— line ———————|<- inset ->|
                       gx0                   gx1
 cy = 512 + STATUS_H//2 = 526          ← 1px line drawn here, colour HUD_SEP
 gx0 = Ri + inset ;  gx1 = Ri + G − inset
 drawn only when (gx1 − gx0) ≥ sep_min
```

**Parameters** (`HBox` constructor, with defaults): `sep_color = HUD_SEP`,
`sep_inset = 6`, `sep_thick = 1`, `sep_min = 4`. Separators are opt-in
(`sep_color=None` ⇒ none drawn); the HUD passes `HUD_SEP`. Only the `n-1`
inter-element gaps get a line — never the outer `margin` before the first element or
after the last.

**New constant** `HUD_SEP = (80, 80, 96)` in `constants.py` — medium brightness,
blue-grey to match the `HUD_BG = (16,16,24)` family. (Value confirmable at review.)

**`HBox.blit` gains the draw** (unchanged layout math; only the separator lines are
new):

```python
def blit(self, target, elements, top, row_h):
    tight = sum(e.width for e in elements)
    gap = (self.width - 2 * self.margin - tight) / max(len(elements) - 1, 1)
    cy = top + row_h // 2
    x = float(self.margin)
    for i, e in enumerate(elements):
        e.blit(target, x, top, row_h)
        x_end = x + e.width
        if self.sep_color is not None and i < len(elements) - 1:
            gx0 = x_end + self.sep_inset
            gx1 = x_end + gap - self.sep_inset
            if gx1 - gx0 >= self.sep_min:
                pygame.draw.line(target, self.sep_color,
                                 (round(gx0), cy), (round(gx1), cy), self.sep_thick)
        x = x_end + gap
```

This is a deliberate visual change to **every** HUD row (all levels), so the existing
HUD goldens are re-recorded in D4's commit (not D3's).

## D5 — Verification

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
3. **Counter presence** — `test_hud_bridge_present_with_planks` (a planks level
   exposes `_level_has_planks is True`, and the rendered HUD element list includes a
   `BRIDGE` element) and `test_hud_bridge_absent_without_planks` (a plankless level ⇒
   `_level_has_planks is False`, no `BRIDGE` element in the list).
4. **HBox / element unit tests (`tests/test_hud.py`, new — pure, no full Game)** —
   `hud.py` is unit-testable in isolation:
   - `LabelValue(font, "SCORE", "  1234").width` equals the width of the
     `font.render("SCORE   1234")` surface; a value-less `LabelValue(font, "BOSS")`
     renders just `"BOSS"`.
   - `HBox` places `n` elements with `x[0] == margin`, `x[-1] + last.width ==
     width - margin`, and equal gaps between consecutive elements (to ±1 px for
     rounding); the degenerate `n == 1` case centres/lefts without division by zero.
   - **Separators (D4):** with `sep_color` set, an `HBox` of `n` elements draws
     exactly `n-1` lines, each at `cy = top + row_h//2`, spanning
     `[Ri+inset, Ri+G-inset]`; with `sep_color=None`, zero lines. A too-narrow gap
     (`G - 2·inset < sep_min`) draws no line for that gap. Assert via a small
     off-screen surface and pixel probes at the expected midpoints (lit) and just
     inside the element edges (background).
5. **Refactor checkpoint (D3, before D4)** — at the end of D3 the existing HUD
   goldens for keyless and keyed levels pass **unchanged** (proves the refactor is
   behaviour-preserving). This is asserted at the D3 commit; the D4 commit then
   re-records them.
6. **HUD goldens (D4 + counter)** — re-record all `test_shot_hud*` goldens once the
   separators land, plus a new `test_shot_hud_bridge` (a playing frame over a planks
   level showing the `BRIDGE N.` counter left of `WALLS`). Re-record with
   `UGLYCRAFT_REGOLD=1` and review every diff by eye: confirm the faint gap lines
   appear in each inter-element gap and nowhere else, and the BRIDGE counter reads
   correctly.
7. **Manual check** — Daniel plays a level with a water room and confirms: bumping
   water with only planks builds a bridge without opening the menu; the BRIDGE
   counter shows the right number, decrements on use, sits left of WALLS, and is
   absent on levels with no planks; and the gap separators subtly divide the HUD
   without looking noisy.

## Out of scope

- **BL-18** (4-plank bridges / mixed plank sources / single-plank item): this spec
  keeps the 2-plank recipe.
- The `>7` locked-door colour-pool edge (unrelated).
- Any change to the WALLS counter, SHIELD, or other HUD elements beyond expressing
  them as `LabelValue` in the HBox (behaviour unchanged).
- Auto-craft for anything other than bridges and the existing walls.
- A general layout engine: the HBox does horizontal even-gap distribution only — no
  VBox, alignment modes, min/max sizing, or nesting. Add those only if a later HUD
  need demands them.

## Resolved decisions

- **Counter value** — buildable bridges (`planks // 2`, plus any crafted bridge),
  with a trailing `.` for one leftover plank; colour parallels WALLS
  (LTGREEN / YELLOW-half / GRAY). Confirmed by Daniel 2026-07-13.
- **HUD engineering** — object-oriented HBox in a new `hud.py`: `HudElement` reports
  its tight width, `HBox` distributes slack across the `n-1` gaps, `LabelValue` is the
  reusable `label:value` element. Confirmed by Daniel 2026-07-13.
- **Gap separators** — a faint 1 px medium-brightness horizontal rule, vertically
  centred in each inter-element gap, to anchor right-justified values to their labels.
  Requested by Daniel 2026-07-13; geometry/params to confirm at spec review.

## Done when:

- [ ] **D1** — `Inventory.can_quick_bridge()`/`quick_bridge()` added; water-bump
  auto-crafts a bridge from 2 planks (menu-free), spending raw planks first and
  falling back to a crafted bridge (mirroring `quick_place_wall`); all bridge guards
  intact; no plank spent on a rejected placement. *(commit: ____)*
- [ ] **D2** — `World._level_has_planks` computed at load and delegated; `BRIDGE N.`
  counter (= `planks//2` buildable, `.` for an odd plank) renders left of WALLS only
  on planks levels, omitted (space redistributed) otherwise; never reflows during
  play. *(commit: ____)*
- [ ] **D3** — HUD redesigned as an OO HBox in `hud.py` (`HudElement`/`LabelValue`/
  `IconStrip`/`HBox`); `_render_hud` builds an element list + one `HBox.blit`; the
  `imgs.insert(<magic index>)` splice is gone; HUD output byte-identical for
  plankless/keyless levels (existing goldens pass unchanged **at this commit**);
  `hud.py` unit tests pass. *(commit: ____)*
- [ ] **D4** — `HBox` draws a 1 px `HUD_SEP` line vertically centred in each of the
  `n-1` inter-element gaps (opt-in via `sep_color`, none in the outer margins, none
  in gaps narrower than `sep_min`); `HUD_SEP` added to `constants.py`; separator unit
  tests pass; HUD goldens re-recorded and reviewed. *(commit: ____)*
- [ ] **D5** — Auto-craft + counter-presence headless assertions, `hud.py` HBox/
  element/separator unit tests, and the guard tests all pass; HUD goldens re-recorded
  (separators + planks-level BRIDGE counter) and reviewed; Daniel confirms the
  behaviour in-game. *(commit: ____)*
