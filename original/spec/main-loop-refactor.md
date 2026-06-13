# Spec: Main loop refactor — eliminate bootstrap hack, real pickup event

## Status

- ✓ `EX`/`EY` added to each `InitLevel1`–`InitLevel9`
- ✓ `AwardPoints` formula changed to `ItemNo * 100` (called before increment)
- ✓ Label `NextItem` renamed to `StartLevel`; label declaration updated
- ✓ `NewGame:` initializes all variables directly for Level 1
- ✓ `LevelComplete` procedure extracted
- ✓ `IsPlayerCaught` / `IsItemPickedUp` helper functions added
- ✓ Pickup logic inlined at `if IsItemPickedUp` with correct award-before-increment order
- ✓ `DrawLevel` renamed from `WriteLevel`

---

## Motivation

The current `NewGame:` label uses a bootstrap hack: it sets `Level := 0; ItemNo := 9;` and
falls through to `NextItem:`, which increments both and triggers the level-advance branch
to set up Level 1 as if a transition had just occurred.

Three cascading hacks result:
- `AwardPoints` is called at the top of `NextItem` *after* the increment, so the formula
  uses `(ItemNo - 1) * 100` to "undo" the extra step — making rope worth 0 pts instead of 100.
- `Score := 0` is needed to cancel the 900 fake points awarded during bootstrap.
- `Lives := Lives + 1` is guarded by `if Level > 1` to skip the fake first transition.

The fix: make the three key events real.

---

## EX/EY per InitLevel (change: each level owns its enemy start)

Add `EX := 5; EY := 10;` at the end of every `InitLevel1`–`InitLevel9`. All levels
currently use the same position; the point is that each level owns its initialization.

```pascal
procedure InitLevel1;
begin
  X := 40;
  Y := 10;
  Key := Chr(KeyRight);
  EX := 5;
  EY := 10;
end;
{ same two lines added to InitLevel2..9 }
```

Remove all `EX := 5; EY := 10;` assignments from the main block.

---

## AwardPoints formula (behavior change: rope = 100 pts, not 0)

Called **before** `ItemNo := ItemNo + 1` at the pickup site:

```pascal
procedure AwardPoints;
begin
  Score := Score + ItemNo * 100;  { rope(1)=100, diamond(2)=200, ..., big_gem(9)=900 }
  DrawScore;
end;
```

Points per level-clear: 4500 (100+200+…+900). This matches the item value table.

---

## Helper functions (add before HandleInput)

```pascal
function IsPlayerCaught: Boolean;
begin
  IsPlayerCaught := (X = EX) and (Y = EY);
end;

function IsItemPickedUp: Boolean;
begin
  IsItemPickedUp := (ItemX = X) and (ItemY = Y);
end;
```

---

## LevelComplete procedure (add after PlayerCaught)

Increment `Lives` **before** calling `PrepareLevel` so `Redraw` displays the correct count:

```pascal
procedure LevelComplete;
begin
  Lives := Lives + 1;
  ItemNo := 1;
  BlockX := 1;
  BlockY := 1;
  PrepareLevel;      { calls InitLevel(Level) → InitLevelN sets EX, EY, X, Y, Direction }
  LevelTransition;
end;
```

---

## Main block — before and after

### Before

```pascal
NewGame:
  Level := 0;
  ItemNo := 9;
  Lives := 10;
NextItem:
  EnemyTick := 0;
  ItemNo := ItemNo + 1;
  AwardPoints;
  if ItemNo = 10 then
    begin
      ItemNo := 1;
      Level := Level + 1;
      BlockX := 1;
      BlockY := 1;
      if Level = 1 then Score := 0;
      EX := 5;
      EY := 10;
      if Level = 10 then
        begin
          WinScreen;
          goto PlayAgain;
        end;
      DrawFrame;
      if Level > 1 then Lives := Lives + 1;
      DrawLives;
      LevelTransition;
    end;
  RandomPos;
  repeat
    Delay(MoveDelay);
    DrawItem;
    TextColor(4);
    HandleInput;
    ...
    if (X = EX) and (Y = EY) then
      begin
        PlayerCaught;
        if Lives = 0 then goto OnGameOver;
      end;
    if (ItemX = X) and (ItemY = Y) then
      begin
        SoundPickup;
        goto NextItem;
      end;
  until KeyCode = KeyEscape;
```

### After

```pascal
NewGame:
  Level := 1;
  Score := 0;
  Lives := 10;
  ItemNo := 1;
  BlockX := 1;
  BlockY := 1;
  PrepareLevel;    { → InitLevel(1) → InitLevel1: sets X, Y, Direction, EX, EY }
  LevelTransition;
StartLevel:
  EnemyTick := 0;
  RandomPos;
  repeat
    Delay(MoveDelay);
    DrawItem;
    HandleInput;
    if KeyCode = KeyEscape then goto CleanUp;
    if KeyCode = KeyF4 then goto NewGame;
    if KeyCode = KeyF5 then RemoveBlocks;
    EnemyMove;
    if IsPlayerCaught then
      begin
        PlayerCaught;
        if Lives = 0 then goto OnGameOver;
      end;
    if IsItemPickedUp then
      begin
        SoundPickup;
        AwardPoints;          { award for current ItemNo before increment }
        ItemNo := ItemNo + 1;
        if ItemNo = 10 then
          begin
            Level := Level + 1;
            if Level = 10 then
              begin
                WinScreen;
                goto PlayAgain;
              end;
            LevelComplete;
          end;
        goto StartLevel;
      end;
  until KeyCode = KeyEscape;
```

---

## What is removed

| Removed | Reason |
|---|---|
| `Level := 0; ItemNo := 9;` | Bootstrap hack — replaced by direct Level=1, ItemNo=1 initialization |
| `NextItem:` label | Replaced by `StartLevel:` — the true "begin playing an item" point |
| `AwardPoints;` at top of `NextItem` | Moved to pickup site, called before increment |
| `if Level = 1 then Score := 0;` | Score initialized to 0 in `NewGame:` |
| `EX := 5; EY := 10;` in main block | Moved into each `InitLevelN` |
| `if Level > 1 then Lives := Lives + 1; DrawLives;` | `LevelComplete` increments before `PrepareLevel`; `Redraw` handles display |
| `goto NextItem` in pickup block | Replaced by inline award + `goto StartLevel` |
| `TextColor(4);` before `HandleInput` | Floating call — affected only space characters, not visible glyphs |

---

## Done when

- ✓ `poe build-original` compiles with no errors or warnings
- ✓ `poe run-original`:
  - Level 1 splash appears immediately after the intro screens (no fake Level 0)
  - Lives counter shows 10 at the Level 1 splash
  - Collecting rope awards 100 points
  - Each subsequent item awards the correct amount (200, 300, …, 900)
  - Level clear: lives counter increments **before** the next level splash appears
  - F4 restarts cleanly at Level 1 with Score=0 and Lives=10
  - Levels 1–9 complete and lead to the win screen
