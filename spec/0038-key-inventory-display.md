# Spec 0038 — Key inventory display: no counter, fix display bug (BL-27)

## Status

- [ ] D1 — Keys in the inventory/crafting screen are rendered **without** a
      `×N` quantity counter (keys are unique tokens — at most one of each colour
      matters). Materials, tools, and crafted recipes keep their counters; only
      the keys list changes.
- [ ] D2 — The suspected "key inventory looked wrong" display bug is identified
      and fixed. The concrete cause found from code reading is **counter
      inflation across levels** (the inventory — and therefore `keys` — is never
      reset between levels, so the same colour can show `×2`, `×3`…); removing
      the counter (D1) eliminates the visible symptom. Confirm by code review +
      manual play that no **other** display defect remains (wrong colour, stale
      entry, or a key shown when absent / absent when held); if the user
      observed a different symptom, reproduce it first, then fix.

## The defect

### Where the key counter is drawn

`_render_inventory` (`game.py:1417`) draws the inventory/crafting overlay. The
"Keys" section (`game.py:1477-1496`) lists each held key with a `×N` counter,
exactly mirroring the Materials section:

```python
# ── Keys (below tools) ───────────────────────────────────────────
any_keys = any(v > 0 for v in inv.keys.values())
if any_keys:
    panel_y += 8
    header = self.font_small.render("Keys", True, GRAY)
    self.surf.blit(header, (panel_x, panel_y))
    panel_y += 22
    for key_color, name in KEY_NAMES.items():
        count = inv.keys.get(key_color, 0)
        if count <= 0:
            continue
        icon_key = f'icon_key_{key_color}'
        if icon_key in sp:
            self.surf.blit(sp[icon_key], (panel_x, panel_y))
        col = KEY_COLORS.get(key_color, WHITE)
        txt = self.font_small.render(f"×{count}", True, col)   # <-- counter
        self.surf.blit(txt, (count_x, panel_y + 2))
        nm = self.font_small.render(name, True, col)
        self.surf.blit(nm, (name_x, panel_y + 2))
        panel_y += ROW
```

`count_x` / `name_x` are the columns defined in the Materials block
(`game.py:1434-1435`); the keys list reuses them so the layout matches.

### Why keys should not have a counter

A key is a **unique unlock token**, not a stackable resource. The level
generator hands out **at most one key of each colour** — every locked
door/edge gets a *distinct* colour via `_next_color()` drawn from
`KEY_COLORS.keys()` (`levelgraph.py:358-394`), and spec **0030** made key
placement reliable (each surviving locked door has exactly one surviving key of
its colour; → see `spec/0030-key-placement-fixes.md`). So per level a key is a
yes/no possession; a `×1` next to it is meaningless clutter.

### The concrete display bug: counter inflation across levels

`Inventory()` is constructed **once per game**, in `_full_reset`
(`game.py:260`). `_start_level` (`game.py:264`) and `_advance_level`
(`game.py:905-913`, which just calls `_start_level`) **never reset
`self.inventory`** — so materials, tools, crafted items **and `inventory.keys`**
persist across all 10 levels.

`add_key` (`crafting.py:137-138`) increments the colour's count on every
pickup:

```python
def add_key(self, key_color):
    self.keys[key_color] = self.keys.get(key_color, 0) + 1
```

`use_key` (`crafting.py:140-144`) decrements it when a matching door is opened
(`game.py:617-618`). A key that is **not** consumed before the level ends
(e.g. its door was reached by another route, or the run advances with the key
still held) carries over. The next Act 2 level re-uses colours from the front of
`KEY_COLORS.keys()`, so collecting, say, a red key again yields
`self.keys['red'] == 2`, and the inventory shows `Red Key ×2` for a token that
is conceptually unique. This is the most likely source of "during play the key
inventory sometimes looked wrong." Because the colour comes from a *graph*
decision that spec 0030 made sound, a wrong display here is a **UI bug, not a
generation bug**.

### What is *not* broken (checked from code reading)

The show/hide logic is correct and need not change:

- The "Keys" header and the per-key row are gated on `count > 0`
  (`game.py:1478`, `1486`), so a fully-spent key (count 0, entry still present
  in the dict) is **not** displayed — no stale row.
- The loop iterates `KEY_NAMES.items()`, and every colour the generator can
  emit (`KEY_COLORS.keys()`) is present in `KEY_NAMES` and `KEY_COLORS` and has
  an `icon_key_<colour>` sprite (`sprites.py:1211`, `crafting.py:94-112`), so no
  held key is ever silently dropped from the list and the colour/name/icon
  mapping is consistent.

If manual play reveals a symptom outside these (e.g. a wrong colour swatch or a
key that visibly fails to appear), D2 covers reproducing and fixing it; from the
code alone the counter is the only defect found.

## Resolution

### D1 — render keys without a count

In the Keys section of `_render_inventory` (`game.py:1484-1496`), drop the
`×{count}` text entirely. Keep the icon, the colour-tinted name, and the
`count > 0` guard (so spent/absent keys still don't render). Concretely, remove
the two lines that build and blit the `txt = self.font_small.render(f"×{count}"…)`
counter; render only the icon at `panel_x` and the name at `name_x` (the
name may move left to `count_x` or stay at `name_x` — keep it aligned with the
Tools list, which already renders a name with no counter at `name_x`,
`game.py:1473-1474`). Materials, tools, and recipe counters are untouched.

### D2 — the display bug

Removing the counter (D1) removes the visible `×2`/`×3` symptom of cross-level
accumulation, which is the concrete bug found. The underlying persistence of
`inventory.keys` across levels is **out of scope** for this display-only item
(whether keys *should* carry between levels is a gameplay question — file
separately if desired); D2's obligation is that the **rendered** key list is
correct: one row per currently-held colour, right icon, right name, no count.

If, on the manual verification run, the user reports a different display
symptom (wrong colour, a held key missing, or a key shown when none is held),
reproduce it on a known seed/level first, then fix it as part of D2 and document
the cause here. From code reading no such second defect exists.

## Verification

- **D1 / D2 — manual visual check (user acceptance).** Run a debug Act 2 level
  that contains a locked door + key:

  ```
  poe run --level 11
  ```

  Walk onto the key pickup to collect it, open the inventory/crafting screen
  (the `TAB` key — the binding that sets `self.state = INVENTORY`,
  `game.py:789-790`),
  and confirm the "Keys" section shows the collected key with its icon and
  colour-tinted name and **no `×N` counter**. Spend it on the matching door and
  reopen the inventory: the key row disappears (no stale entry). Spot-check that
  Materials, Tools, and Recipes still show their counters unchanged. (Try a
  couple of generator seeds / levels if the first has no key-bearing room.)

- **D1 — optional automated guard (only if a pure helper is extracted).** The
  current rendering is display-coupled (blits to a surface) and not unit-testable
  without a display. A unit test is warranted **only** if the key-row text is
  factored into a pure formatter (e.g. `_key_inventory_line(name) -> str`); such
  a helper can then be asserted to contain the colour name and **not** contain
  `×`. No display is required for that. If no helper is extracted, D1/D2 rest on
  the manual check above.

## Done when:

- [ ] D1 — The inventory/crafting Keys list renders each held key with icon and
      name only, no `×N` counter; materials/tools/recipes counters unchanged.
- [ ] D2 — The suspected display bug is resolved: the rendered key list is
      correct (one row per held colour, right icon/name, no count, no stale row);
      the cross-level counter-inflation cause is documented and its symptom gone,
      and no other display defect remains (user-confirmed).
