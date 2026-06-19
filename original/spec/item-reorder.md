# Reorder and replace items

## Status

- [ ] Item array updated with new characters, colors, and order
- [ ] Item name resourcestrings updated
- [ ] German translations updated
- [ ] Game compiles (`poe build-original` exits 0)
- [ ] All tests pass (`poe test-original` exits 0)
- [ ] Manual check: items display correctly in-game and on item list screen

## Changes

| # | Old name | New name | Ch | Fg |
|---|---|---|---|---|
| 1 | Rope | Lamp | Φ (keep) | Yellow (keep) |
| 2 | Large Sparkling Diamond | Swords | ⚔ U+2694 | Yellow |
| 3 | Small Gems | Small Ruby | ▼ U+25BC | LightRed |
| 4 | Small Sparkling Diamond | Small Gems | ⛬ U+26EC | LightMagenta |
| 5 | Gold Bar | Small Diamond | 🞙 U+1F799 | LightCyan |
| 6 | Silver Bar | Silver Bar | ≡ (keep) | LightGray (keep) |
| 7 | Well | Gold Bar | = (keep from old #5) | Yellow |
| 8 | Lamp | Necklace | 🝁 U+1F741 | LightGray |
| 9 | Large Gem | Flag | ⚑ U+2691 | LightGreen |
| 10 | Crown | Crown | 🜲 U+1F732 | Yellow |

## Files to modify

- `original/UGLI_2_Core.inc` — `Items` array and `sItemName1`–`sItemName10`
- `original/translations/de.po` + `de.mo` — German item names
- `original/CHANGELOG.md`

## Done when

- [ ] All 10 items match the table above (character, color, name)
- [ ] German translations match
- [ ] Item list screen (pre-game) shows correct items
- [ ] Items display correctly during gameplay
