# Spec: Dialog/message box refactor — WaitKey + Dialog

## Status

- [x] `DrawInner` draws player, enemy, and current item after the wall/space loop
- [x] `ItemX := 0` sentinel set in `NewGame:` and in pickup handler before `LevelComplete`/`goto StartLevel`
- [x] `WaitKey: Integer` function added after `GetKey`
- [x] `YesKey` / `NoKey` typed set constants added to `const` section
- [x] `Dialog(Title, Prompt: String): Integer` function added after `WaitKey`
- [x] `LevelTransition` replaced with single `Dialog` call; centered (Y1 = 9)
- [x] `GameOver` replaced with `Dialog('G A M E  O V E R', '')`
- [x] `WinScreen` replaced with `Dialog` call; star animation removed
- [x] `AskPlayAgain` loops `Dialog` until `YesKey`/`NoKey`
- [x] `RemoveBlocks` loops `Dialog('B L Ö C K E   E N T F E R N E N', 'J / N')`; cost removed
- [x] `DrawBlocks` HUD label changed from `'STEINE'` to `'BLÖCKE'`
- [x] `ShowHelp`, `ShowStory`, `ShowItemDescriptions` exit via `WaitKey`
- [x] `HighScoreEntry` post-score and post-file pauses use `WaitKey`

---

## Motivation

Three problems with the current overlay and dialog code:

1. **Inconsistent key-reading**: dialogs use bare `GetKey`, plain `ReadLn`, or hand-rolled
   drain loops interchangeably. A stale buffered key can slip through.

2. **Ad-hoc box geometry**: each dialog hard-codes its own coordinates and border style —
   different widths, positions, border characters. None are reliably centered.

3. **LevelTransition off-center**: box top is at row 8; the math puts it at row 9 for a
   centered 3-row box in the 20-row field.

---

## Field geometry

- `FieldW = 80`, `FieldH = 20`; interior rows 2–19, cols 2–79.
- 3-row box: `Y1 = (20 − 3) div 2 + 1 = 9`, rows 9–11.
- 4-row total (box + unboxed prompt row): Y1 = 9, prompt at row 12.

---

## New constants (add to `const` section)

```pascal
YesKey : set of Byte = [Ord('J'), Ord('j')];
NoKey  : set of Byte = [Ord('N'), Ord('n')];
```

`WaitKey` / `Dialog` return an `Integer` key code; `in YesKey` / `in NoKey` works directly
since key codes are always in Byte range.

---

## DrawInner — entity drawing

`DrawInner` becomes the authoritative full interior repaint. After the existing wall/space
loop, add:

```pascal
if X >= 2 then
  Draw(X, Y, PlayerFg, FieldBg, '☺');
if EX >= 2 then
  Draw(EX, EY, EnemyFg, FieldBg, '☻');
if ItemX >= 2 then
  DrawItem;
```

**`ItemX := 0` sentinel** — "no item on field." Set in:
- `NewGame:` initialisation block (before `PrepareLevel`)
- Pickup handler, after `ItemNo := ItemNo + 1`, before `LevelComplete` / `goto StartLevel`

`X >= 2` / `EX >= 2` guards handle the startup case before the first `PrepareLevel`.

---

## WaitKey function (add after `GetKey`)

```pascal
function WaitKey: Integer;
var K: Char;
begin
  repeat
    K := GetKey;
  until not KeyPressed;
  WaitKey := Ord(K);
end;
```

First `GetKey` blocks until a key arrives; `until not KeyPressed` drains any further
buffered keys. Returns the integer code of the last key in the queue.

Used standalone by: `ShowHelp`, `ShowStory`, `ShowItemDescriptions`, `HighScoreEntry`.

---

## Dialog function (add after `WaitKey`, before `LevelTransition`)

```pascal
function Dialog(Title: String; Prompt: String): Integer;
```

Draws a centered box, calls `WaitKey`, calls `DrawInner` to restore the interior, returns
the key code.

- Colors: `DialogFg` / `FieldBg` throughout
- `Prompt = ''` → 3-row box only
- `Prompt ≠ ''` → 3-row box + unboxed prompt row below; 4 rows total

**Geometry:**
```
W  = max(UTF8Cols(Title), UTF8Cols(Prompt)) + 4
if W < 27 then W := 27
X1 = (FieldW − W) div 2 + 1
X2 = X1 + W − 1
BoxH = 3  { or 4 if Prompt ≠ '' }
Y1 = (FieldH − BoxH) div 2 + 1
```

**Visual structure:**
```
Y1:   ████████████████████████████
Y1+1: █   TITLE (centered)        █
Y1+2: ████████████████████████████
Y1+3:     Prompt (centered)            ← only if Prompt ≠ ''
```

Text is centered within interior width `(W − 2)` using `UTF8Cols` from `DANISOFT`.
`DrawHLine` for solid border rows; `Draw` for content and prompt rows.

End sequence:
```pascal
Dialog := WaitKey;
DrawInner;
```

---

## Affected procedures

### LevelTransition

Old: `repeat draw 6 calls; Delay(1000); until KeyPressed; GetKey; direction; DrawInner`

New:
```pascal
Str(Level, S);
KeyCode := Dialog('L E V E L   ' + S, 'T A S T E   D R Ü C K E N');
if KeyCode in [KeyRight, KeyLeft, KeyUp, KeyDown] then
  Direction := Chr(KeyCode);
Delay(1000);
```

### GameOver

```pascal
SoundGameOver;
Dialog('G A M E  O V E R', '');
```

Return value discarded.

### WinScreen

```pascal
Dialog('G E W O N N E N', 'T A S T E   D R Ü C K E N');
SoundWon;
HighScoreEntry;
ClrScr;
```

Star animation (`TextAttr := Random(255); Write('*'); …`) removed entirely.

### AskPlayAgain

```pascal
var Code: Integer;
repeat
  Code := Dialog('N O C H M A L  S P I E L E N', 'J / N');
until (Code in YesKey) or (Code in NoKey);
AskPlayAgain := Code in YesKey;
```

### RemoveBlocks

```pascal
var Code: Integer;
repeat
  Code := Dialog('B L Ö C K E   E N T F E R N E N', 'J / N');
until (Code in YesKey) or (Code in NoKey);
if Code in YesKey then
  begin { clear blocks, InitLevel, DrawBorder } end;
DrawInner;   { second DrawInner: shows updated block state }
```

No point cost deducted (20-pt deduction removed).

### DrawBlocks

```pascal
Draw(68, 20, Fg, Bg, 'BLÖCKE ' + S);   { was 'STEINE' }
```

### ShowHelp / ShowStory / ShowItemDescriptions

`Key := GetKey` / `ReadLn` → `WaitKey` (return value discarded).

### HighScoreEntry

Two bare `ReadLn` pauses (after displaying score, after displaying file) → `WaitKey`
(discard). `ReadLn(FirstName)` / `ReadLn(LastName)` text-input calls unchanged.

---

## Done when

- [x] `poe build-original` compiles with no errors or warnings (d81242f)
- [x] `poe run-original` (d81242f, confirmed by user):
  - Level splash vertically centered (rows 9–11, not 8–10)
  - GAME OVER, Play Again, and RemoveBlocks dialogs all use `█` border style and are centered
  - WinScreen: splash centered; star animation gone; `SoundWon` plays then high-score entry follows
  - F1/F2 help/story screens: player, enemy, and item sprites visible immediately on return
  - No ghost item visible in LevelTransition after collecting the 9th item
  - AskPlayAgain/RemoveBlocks: box stays visible until J or N is pressed
  - RemoveBlocks: no point cost deducted
  - Item descriptions screen exits on any key (no ReadLn hang)
  - High-score entry: name text input still works; confirmations exit on any key
  - No dialog box residue visible after any dialog closes
