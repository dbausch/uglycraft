# Spec 0071 — Key display: drop the counter, add HUD key icons, fix the display bug

Backlog: **BL-27 (P2)**. Keys are unique — at most one of each colour per level —
so the inventory should not show a quantity counter next to a key. Also: show the
coloured key icons in the HUD status line (not only in the inventory view), and
investigate the display bug Daniel saw during play ("the key inventory sometimes
looked wrong").

## Status checklist

- [x] **D1** — Inventory Keys section drops the `×N` counter; each held key is
  shown as `[icon] Name` only (no count column, no leftover gap).
- [x] **D2** — Display-bug follow-up: confirm the key inventory now renders
  correctly (Daniel: the earlier "looked wrong" was most likely an artifact of a
  separate, already-resolved defect); record the resolution in `kb/findings.md`.
- [x] **D3** — HUD status line shows a per-level key tracker: one slot per key
  colour present in the level, lit when held and ghosted (~15 %) when not; no strip
  (space redistributed) when the level has no keys; never reflows during play.
- [x] **D4** — Verification: screenshot golden(s) for the inventory Keys section
  and the HUD key strip; a headless assertion that a held key renders without a
  count; user confirmation in-game.

## Background — confirmed facts

Established by reading the code while writing this spec (self-contained; do not
re-derive):

- **Key model** (`crafting.py`): `Inventory.keys` is a `{colour: count}` dict.
  `add_key` increments, `use_key` decrements, `has_key` tests `> 0`. Colours are
  the seven strings `red, blue, green, yellow, cyan, purple, orange`
  (`KEY_COLORS` / `KEY_NAMES` in `constants.py`).
- **Keys are unique per colour.** `levelgraph.py:441` builds a *shuffled colour
  pool* and `pop()`s one colour per locked door — "ensures every locked door uses
  a distinct color." With at most one door per colour there is at most one key per
  colour, so `count` is always `1`. The `×N` counter therefore carries no
  information. (Only 7 colours exist; a level needing >7 locked doors is a
  separate generator constraint, out of scope here.)

  > **ERRATA (spec 0075 / BL-56):** this uniqueness only holds for levels with
  > ≤7 locked doors. The pool cycles, so a level with >7 locked doors repeats
  > colours (a colour can have up to 4 keys/doors — capped by
  > `MAX_KEYS_PER_COLOUR`). The HUD key tracker now draws a **stack** of that
  > many icons per colour (spec 0075 D2); see `kb/requirements.md` R-K2.
- **Keys are consumed on use.** `world.py:518` (`_try_auto_open_door`) calls
  `inventory.use_key(colour)` when the player bumps a matching locked door, so the
  key's count drops to 0 and it vanishes from the inventory list. This is a
  candidate explanation for "looked wrong" — see D2.
- **Inventory rendering** (`game.py` `_render_inventory`, the "Keys" block ~lines
  822–841): for each colour with `count > 0` it blits `icon_key_{colour}` at
  `panel_x`, then draws `×{count}` at `count_x` and the name at `name_x`. The
  `count_x`/`name_x` columns are shared with the Materials list.
- **HUD rendering** (`game.py` `_render_hud`, ~lines 685–736): a single row at
  `y = ROWS*TILE = 512`, height `STATUS_H = 28`. It is a list of text images
  (`SCORE`, `LEVEL`, `LIVES`, `SEEK:`/`LOOT`, optional `BOSS`/`HARD`, `SHIELD`,
  `WALLS`) evenly spaced across `LOGICAL_W = 960` by a computed `gap`. There is no
  key display today. The HUD deliberately avoids layout shift: `SEEK` is padded to
  the longest treasure name and `SHIELD` is always present (drawn in `HUD_BG` —
  invisible — when inactive).
- **Sprites available** (`sprites.py`): `icon_key_{colour}` (20 px icon, used by
  the inventory) and `key_{colour}` (32 px pickup) exist for all seven colours.
  A 20 px icon fits inside the 28 px HUD row (4 px vertical margin).

## D1 — Drop the key counter in the inventory

In the `_render_inventory` Keys block, stop drawing `×{count}`. Render each held
key as `[icon] Name`, aligned so there is no empty gap where the count column was.

- Remove the `txt = self.font_small.render(f"×{count}", ...)` blit for keys.
- Move the key name to sit right after the icon (use the icon-adjacent column, not
  `name_x`, so the row does not carry a hole). Keep the icon at `panel_x` and the
  name a few px to its right, matching the Tools block (Tools already draw
  `[icon] Name` with the name at `name_x` and no count — reuse that spacing for
  keys for visual consistency between the two icon-only lists).
- The colour of the name text stays `KEY_COLORS[colour]` (each key labelled in its
  own colour).
- Only colours with `count > 0` are listed (unchanged); the "Keys" header still
  only appears when at least one key is held (unchanged `any_keys` guard).

Materials keep their `×N` counter — this change is keys-only.

## D2 — Display-bug follow-up (believed already resolved)

BL-27 noted "during play the key inventory sometimes looked wrong." Daniel's
assessment (2026-07-12): the key inventory has looked correct in recent play, and
the earlier symptom was most likely an **artifact of a separate defect that has
since been fixed** — not a standalone bug in the key-rendering code.

This deliverable is therefore a light confirmation, not a bug hunt:

- Sanity-check the key-rendering path holds up: a used key (count 0) is filtered
  out and never lingers; `icon_key_{colour}` matches the label colour for all seven
  colours; the D1 re-spacing leaves no gap.
- Do **not** open a headless reproduction hunt for a bug we no longer believe
  exists. If any genuine defect surfaces incidentally while doing D1/D3, capture
  it; otherwise record the closure.

Deliverable: a one-paragraph note in `kb/findings.md` recording that the "key
inventory looked wrong" report is considered resolved (artifact of an
already-fixed defect), with D1 removing the last cosmetic wart (the redundant
`×1`). Note for the record: keys are **consumed on door-open** (`world.py:518`
`use_key`) so a carried key disappears once its door is opened — this is current,
intended behaviour and is explicitly out of scope here.

## D3 — Key icons in the HUD status line

Add a **per-level key-collection tracker** to the HUD: one 20 px slot for each key
colour that appears **in the current level**, drawn `icon_key_{colour}` **lit** when
the player holds that key and **ghosted** (~15 % opacity) when not.

**Scope of the slots — the level's key colours (decided, refined).** The strip
shows exactly the colours present in the level, not all seven. The colour set is
computed once at level load — `World._level_key_colours`, the union of key colours
across `data['rooms'][*]['keys']`, ordered by `KEY_NAMES` — and exposed to `game.py`
via the `_WORLD_ATTRS` delegation. Within a level this set is constant, so the
strip width is fixed and the rest of the HUD never reflows as keys are gained or
used; it only differs between levels.

**Ghosting, not empty slots (decided).** Every level-present colour always occupies
its fixed slot: a held key is drawn at full opacity, a not-yet-held key at ~15 %
opacity (`_KEY_GHOST_ALPHA = 38`, applied with
`icon.fill((255,255,255,38), special_flags=BLEND_RGBA_MULT)` on a copy — the icons
carry per-pixel alpha, so `set_alpha` would be ignored). This turns the reserved
space into a collect-tracker rather than an empty gap. Because keys are consumed on
door-open, a used key reverts from lit to ghosted — expected for a "currently held"
tracker.

**No keys ⇒ no strip (decided).** When the level has no keys at all
(`_level_key_colours == []` — e.g. every Act 1 level), `_hud_key_strip()` returns
`None` and the strip is **omitted**; the even-spacing loop then redistributes its
space across the remaining HUD elements. Since the emptiness is fixed per level,
this redistribution happens once per level.

> The same conditional-visibility convention applies to the upcoming HUD **bridge
> counter** (BL-28): show it only when the level contains planks, otherwise omit it
> and redistribute the space. Both reuse the mechanism below — a HUD element that
> may be a pre-rendered `pygame.Surface`, or absent — so keep it generic. (Filed as
> a note on BL-28.)

Geometry (28 px HUD row, icons 20 px; each element centred vertically by its own
height, `cy = hud_y + (STATUS_H - img.height)//2`; N = number of key colours in the
level, slot = 23 px):

```
 col: 0                                                              960
      +-----------------------------------------------------------------+
 512  | SCORE …  LEVEL …  LIVES …  SEEK …  [🔑🔑▨▨]  SHIELD …  WALLS … |
 540  +-----------------------------------------------------------------+
        KEYS strip = N slots (N = level's key colours); 🔑 lit = held,
        ▨ ghosted (~15%) = not held. No keys in the level ⇒ strip omitted,
        space redistributed. Each slot = one 23px icon_key_<colour>.
```

Placement in the element list: insert the key strip **after** the `SEEK:`/`LOOT`
element and **before** the `BOSS`/`HARD`/`SHIELD`/`WALLS` status cluster — i.e. in
the "collectibles" region of the row (approved: keys next to LOOT).

Implementation: `_render_hud` builds `elems` as `(text, colour)` tuples, renders
each to an image, and places them with a computed even-spacing `gap`. Generalise so
an element may also be a pre-rendered `pygame.Surface` (the key strip): build the
strip via `_hud_key_strip()` and `imgs.insert(4, strip)` only when it is non-`None`.
Each element is now centred by its own height so the 20 px strip and the shorter
text share a centre line. Because the strip's width is fixed for the level, the
surrounding elements never move during play.

## D4 — Verification

No general automated gameplay suite, but the render path has **screenshot
goldens** (`tests/test_render.py`, `_shot(...)` + `assert_golden`) and a headless
`Harness`. Verify with:

1. **Inventory golden** — `test_shot_inventory` holds three keys (red/cyan/orange,
   also seeded into the fixture's `keys`) so the golden captures the counter-free
   Keys section. Re-record with `UGLYCRAFT_REGOLD=1` and review the diff by eye (the
   `×1` must be gone, no gap).
2. **HUD golden** — `test_shot_hud_keys`: a playing frame over a level with four key
   colours (red/green/purple/cyan) where the player holds two, so the golden
   captures both lit and ghosted slots. Re-record and review.
3. **Headless assertions** (non-fragile, alongside the goldens):
   - `test_hud_key_strip_per_level_fixed_width` — strip width `== _KEY_SLOT × N`
     (N = level's key colours) and constant across 0/1/all held (no reflow).
   - `test_hud_key_strip_absent_without_keys` — a keyless level yields
     `_level_key_colours == []` and `_hud_key_strip() is None` (strip omitted).
4. **Manual check** — Daniel plays a level with locked doors and confirms: keys in
   the inventory show no counter and read correctly; the HUD tracker shows the
   level's key colours (lit when held, ghosted when not); picking up and using keys
   updates both views correctly; keyless levels show no strip.

Screenshot goldens are the deliberately fragile tier (spec 0044) — expect to
re-record them and review the pixel diff intentionally.

## Out of scope

- Changing consume-on-use key semantics (D2 hypothesis 3) — record only; file
  separately if wanted.
- Any change to Materials/Tools counters or the rest of the HUD elements.
- The `>7` locked-door colour-pool exhaustion generator edge (unrelated).

## Done when:

- [x] **D1** — Inventory Keys section renders `[icon] Name` with no `×N` and no
  leftover column gap; Materials counters unchanged. *(commit: 041e394)*
- [x] **D2** — `kb/findings.md` records the "key inventory looked wrong" report as
  resolved (artifact of an already-fixed defect; D1 removes the last cosmetic
  wart); key-rendering sanity checks pass. *(commit: 041e394)*
- [x] **D3** — HUD tracker shows one slot per key colour in the level (after LOOT),
  lit when held and ghosted (~15 %) when not; omitted with space redistributed when
  the level has no keys; never reflows during play. *(commit: 041e394, 6ef8709)*
- [x] **D4** — Inventory + HUD screenshot goldens re-recorded and reviewed; the two
  headless strip assertions pass; Daniel confirms both views in-game. *(commit:
  041e394, 6ef8709)*
