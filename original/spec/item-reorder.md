# Reorder and replace items

## Status

- [x] Item array updated with new characters, colors, and order
- [x] Item name resourcestrings updated
- [x] German translations updated
- [x] Game compiles (`poe build-original` exits 0)
- [x] All tests pass (`poe test-original` exits 0)
- [x] Manual check: items display correctly in-game and on item list screen

## Changes

| # | Old name | New name | Ch | Fg |
|---|---|---|---|---|
| 1 | Rope | Lamp | Φ U+03A6 | Yellow |
| 2 | Large Sparkling Diamond | Swords | ⚔ U+2694 | Yellow |
| 3 | Small Gems | Ruby | ▼ U+25BC | Red |
| 4 | Small Sparkling Diamond | Gems | ⁂ U+2042 | LightMagenta |
| 5 | Gold Bar | Diamond | ♦ U+2666 | LightCyan |
| 6 | Silver Bar | Silver Bar | ≡ U+2261 | LightGray |
| 7 | Well | Gold Bar | = U+003D | Yellow |
| 8 | Lamp | Necklace | 🝁 U+1F741 | LightGray |
| 9 | Large Gem | Flag | ⚑ U+2691 | LightGreen |
| 10 | Crown | Crown | ♛ U+265B | Yellow |

## Files to modify

- `original/UGLI_2_Core.inc` — `Items` array and `sItemName1`–`sItemName10`
- `original/translations/de.po` + `de.mo` — German item names
- `original/CHANGELOG.md`

## Done when

- [x] All 10 items match the table above (character, color, name) — `8de57ab`, `84d09a2`, `ab18dd0`, `f873ee4`, `d632cb2`
- [x] German translations match — `8de57ab`
- [x] Item list screen (pre-game) shows correct items — confirmed by user
- [x] Items display correctly during gameplay — confirmed by user
