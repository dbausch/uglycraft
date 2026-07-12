# Spec 0071 — Key display: drop the counter, add HUD key icons, fix the display bug

Backlog: **BL-27 (P2)**. Keys are unique — at most one of each colour per level —
so the inventory should not show a quantity counter next to a key. Also: show the
coloured key icons in the HUD status line (not only in the inventory view), and
investigate the display bug Daniel saw during play ("the key inventory sometimes
looked wrong").

## Status checklist

- [ ] **D1** — Inventory Keys section drops the `×N` counter; each held key is
  shown as `[icon] Name` only (no count column, no leftover gap).
- [ ] **D2** — Display-bug follow-up: confirm the key inventory now renders
  correctly (Daniel: the earlier "looked wrong" was most likely an artifact of a
  separate, already-resolved defect); record the resolution in `kb/findings.md`.
- [ ] **D3** — HUD status line shows the coloured icon of every key the player is
  currently holding, in a **fixed-width** key strip (no reflow of the rest of the
  HUD).
- [ ] **D4** — Verification: screenshot golden(s) for the inventory Keys section
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

Add a **fixed-width key strip** to the HUD showing `icon_key_{colour}` (20 px) for
every key the player currently holds (`count > 0`), left-aligned in `KEY_NAMES`
order.

**Fixed width, no reflow (decided).** The strip reserves a constant width sized to
the maximum number of distinct key colours — `len(KEY_COLORS) == 7` — so the rest
of the HUD never shifts as keys are picked up or used, matching the `SHIELD`
"always reserve, draw invisibly when inactive" convention. Held icons are drawn
left-aligned within the reserved strip; unused slots draw nothing (empty). The
strip width is a constant derived from `7 * (20 + gap_px)` — do **not** size it to
the per-level colour count (that would reflow between levels and defeats the point).

> A future backlog item adds a **bridge counter** to the HUD (to the left of the
> WALL counter). This spec does not add it, but the generalisation below — letting
> a HUD element be a pre-rendered surface at a fixed reserved width — is the same
> mechanism that item will reuse; keep it generic.

Geometry (28 px HUD row, icons 20 px, centred vertically at
`cy = hud_y + (STATUS_H - 20)//2 = 512 + 4`; 7 fixed slots, held icons
left-aligned):

```
 col: 0                                                              960
      +-----------------------------------------------------------------+
 512  | SCORE …  LEVEL …  LIVES …  SEEK …  [KEYS ▤▤▤····]  SHIELD …  WALLS … |
 540  +-----------------------------------------------------------------+
        KEYS strip = fixed 7-slot width; held icons left-aligned,
        remaining slots empty (·). Each ▤ = one 20px icon_key_<colour>.
```

Placement in the element list: insert the key strip **after** the `SEEK:`/`LOOT`
element and **before** the `BOSS`/`HARD`/`SHIELD`/`WALLS` status cluster — i.e. in
the "collectibles" region of the row (approved: keys next to LOOT).

Implementation: `_render_hud` currently builds `elems` as `(text, colour)` tuples,
then renders each to an image and places them with a computed even-spacing `gap`.
Generalise so an element may also be a pre-rendered fixed-width `pygame.Surface`
(the key strip: a 7-slot-wide transparent surface with held icons blitted
left-aligned), inserted into the image list at the chosen position; the existing
even-spacing loop then places it like any other element. Because its width is
constant regardless of how many keys are held, the surrounding elements never
move.

## D4 — Verification

No general automated gameplay suite, but the render path has **screenshot
goldens** (`tests/test_render.py`, `_shot(...)` + `assert_golden`) and a headless
`Harness`. Verify with:

1. **Inventory golden** — extend/adjust `test_shot_inventory` (or add a variant)
   over a fixture where the player holds ≥2 keys, so the golden captures the
   counter-free Keys section. Re-record with `UGLYCRAFT_REGOLD=1` and review the
   diff by eye (the `×1` must be gone, no gap).
2. **HUD golden** — add a screenshot golden of a playing frame where the player
   holds ≥2 keys, capturing the HUD key strip. Re-record and review.
3. **Headless assertion** — a small test that builds a `Game`, does
   `inventory.add_key('blue')`, renders the inventory, and asserts the render did
   not raise and (where cheaply checkable) that no `×` count glyph is emitted for
   keys. Keep it in the existing render-test module.
4. **Manual check** — Daniel plays a level with locked doors and confirms: keys in
   the inventory show no counter and read correctly; the HUD shows the held keys'
   coloured icons; picking up and using keys updates both views correctly.

Screenshot goldens are the deliberately fragile tier (spec 0044) — expect to
re-record them and review the pixel diff intentionally.

## Out of scope

- Changing consume-on-use key semantics (D2 hypothesis 3) — record only; file
  separately if wanted.
- Any change to Materials/Tools counters or the rest of the HUD elements.
- The `>7` locked-door colour-pool exhaustion generator edge (unrelated).

## Done when:

- [ ] **D1** — Inventory Keys section renders `[icon] Name` with no `×N` and no
  leftover column gap; Materials counters unchanged. *(commit: ____)*
- [ ] **D2** — `kb/findings.md` records the "key inventory looked wrong" report as
  resolved (artifact of an already-fixed defect; D1 removes the last cosmetic
  wart); key-rendering sanity checks pass. *(commit: ____)*
- [ ] **D3** — HUD status line shows `icon_key_{colour}` for every held key in a
  fixed 7-slot strip after LOOT; the rest of the HUD never shifts as keys change.
  *(commit: ____)*
- [ ] **D4** — Inventory + HUD screenshot goldens re-recorded and reviewed; the
  headless render assertion passes; Daniel confirms both views in-game. *(commit:
  ____)*
