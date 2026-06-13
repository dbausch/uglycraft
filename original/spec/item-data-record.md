# Spec: TItemData record — item definitions + ShowItemDescriptions rewrite

## Status

- ✓ `TItemData` record type declared (`Ch`, `Name`, `Fg` fields)
- ✓ `ItemDescFg`, `ItemDescBg`, `ItemCount` constants added
- ✓ `Items : array[1..ItemCount] of TItemData` typed constant defined
- ✓ `DrawItem` rewritten to use `Items` array
- ✓ `ShowItemDescriptions` rewritten to use `Draw`; layout per spec below

---

## Motivation

`DrawItem` hard-codes character, color, and description strings in three separate
places (the procedure itself, and the old `ShowItemDescriptions`). Defining the
item data once as a typed constant eliminates the duplication and makes adding or
editing items a single-point change.

---

## New constants (add to `const` section)

```pascal
ItemDescFg = Black;    { foreground for item-descriptions screen }
ItemDescBg = LightGray; { background for item-descriptions screen }
ItemCount  = 10;
```

---

## New type (add to `type` section, after `TDirection`)

```pascal
TItemData = record
  Ch:   String[4];    { UTF-8 encoded character (max 3 bytes) }
  Name: String[40];   { German treasure name }
  Fg:   Integer;      { foreground color used during gameplay }
end;
```

---

## New typed constant (new `const` block, between `type` and `var`)

```pascal
const
  Items : array[1..ItemCount] of TItemData = (
    (Ch: '|'; Name: 'Seil';                      Fg: Brown),
    (Ch: '☼'; Name: 'grosser glänzender Diamant'; Fg: LightBlue),
    (Ch: ':'; Name: 'kleine Edelsteine';           Fg: LightRed),
    (Ch: '*'; Name: 'kleiner glänzender Diamant';  Fg: LightBlue),
    (Ch: '='; Name: 'Goldbarren';                  Fg: Yellow),
    (Ch: '≡'; Name: 'Silberbarren';                Fg: LightGray),
    (Ch: 'Γ'; Name: 'Brunnen';                     Fg: Cyan),
    (Ch: 'Φ'; Name: 'Lampe';                       Fg: Yellow),
    (Ch: '♦'; Name: 'grosser Edelstein';           Fg: LightGreen),
    (Ch: '⌂'; Name: 'Krone';                       Fg: Yellow)
  );
```

Index 9 = big gem (used on levels 1–8); index 10 = crown (used on level 9 only).

---

## `DrawItem` rewrite

```pascal
procedure DrawItem;
var Idx: Integer;
begin
  Idx := ItemNo;
  if (ItemNo = 9) and (Level = 9) then Idx := 10;
  Draw(ItemX, ItemY, Items[Idx].Fg, FieldBg, Items[Idx].Ch);
end;
```

Replaces the 10-branch if-chain (including the double-draw hack for the crown).

---

## `ShowItemDescriptions` rewrite

All `WriteLn` / `GotoXY` calls replaced with `Draw`. Local `const Fg = ItemDescFg;
Bg = ItemDescBg;` — items are drawn in `Fg`/`Bg` regardless of their gameplay color.

### Screen layout (25 rows, 80 cols)

```
Row  2: headline 1                  — Center('L I S T E   D E R   E I N Z U S A M M E L N D E N   S C H Ä T Z E')
Row  3: (empty)
Rows 4–13: item list                — 10 items, block-centered (longest line sets left margin)
Row 14: (empty)
Row 15: (empty)                     — two consecutive empty lines after the list
Row 16: headline 2                  — Center('S P I E L A N L E I T U N G')
Row 17: (empty)
Rows 18–21: description text        — 4-space left margin (Draw col 5), wraps before col 77
Row 24: key prompt                  — Center('T A S T E   D R Ü C K E N')
```

### Item list centering

Compute `MaxW` at runtime:
```pascal
MaxW := 0;
for I := 1 to ItemCount do
  begin
    ItemW := UTF8Cols(Items[I].Ch) + 2 + UTF8Cols(Items[I].Name);
    if ItemW > MaxW then MaxW := ItemW;
  end;
Col := (FieldW - MaxW) div 2 + 1;
```

Each item drawn as `Items[I].Ch + '  ' + Items[I].Name` at `(Col, 3 + I)`.

The two longest lines are items 2 and 4 ("☼  grosser glänzender Diamant" and
"*  kleiner glänzender Diamant"), both 29 display columns → `Col = 26`.

### Description text (4-space left margin, wraps at 72 display cols)

```
Row 18: 'Du drückst jetzt eine Taste, dann drückst du eine der Richtungstasten'
Row 19: 'danach musst du mit den Richtungstasten die oben gezeigten Dinge'
Row 20: 'einsammeln. (Die Krone kommt ganz zum Schluss.) Während des Spiels kann'
Row 21: 'man mit <F1> die anderen Tasten die zum bedienen des Spiels nachlesen.'
```

---

## Files changed

`original/UGLI_2.pp` only.

---

## Done when

- ✓ `poe build-original` compiles with no errors or warnings (11e86d5)
- ✓ `poe run-original` (11e86d5, 14ea528; confirmed by user):
  - Item-descriptions screen uses Draw throughout (no WriteLn/GotoXY)
  - Headline 1 centered on row 2, headline 2 centered on row 16
  - Item list centered as a block; two empty lines before second headline
  - Description text starts at col 5, wraps within 72 cols
  - All items drawn in black on gray (not their gameplay colors)
  - "T A S T E   D R Ü C K E N" on row 24
  - After screen exits, game field restores correctly
  - In-game items still use their correct characters and colors
  - Crown (⌂, Yellow) appears on level 9; big gem (♦, LightGreen) on other levels
  - Typo "Edelsteiene" fixed to "Edelsteine"
