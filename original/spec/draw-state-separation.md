# Spec: Draw/state separation — InitBorder, PrepareLevel, Redraw, LevelTransition

## Status

- [x] `InitBorder` procedure added; called from `Init` once at program start
- [x] `DrawBorder` purely visual — no `Blocked` assignments; includes HUD counter calls
- [x] `WriteLevel` renamed to `DrawLevel`
- [x] `DrawInner` removed from `InitLevel`
- [x] `Redraw` simplified: `ClrScr` + `DrawBorder` + `DrawKeys` + `DrawInner`
- [x] `DrawFrame` renamed to `PrepareLevel`; order fixed: `InitLevel` before `Redraw`
- [x] `LevelTransition` drops redundant `InitLevel` call; adds `DrawInner` to clear splash
- [x] Redundant `DrawInner` after `Redraw` in help/story handlers removed
- [x] Redundant `DrawInner` after `PrepareLevel` in `PlayerCaught` removed
- [x] `RemoveBlocks` clears interior `Blocked` only (border cells are permanent)

---

## Motivation

Three violations of separation of concerns:

1. `InitLevel` calls `DrawInner` — state setup triggers rendering.
2. `DrawFrame` calls `Redraw` (which runs `DrawInner` with stale walls) *then* `InitLevel`
   (which sets walls and runs `DrawInner` again) — two draws, first one stale.
3. Border `Blocked` cells are set by `DrawBorder` (a rendering procedure) and cleared by
   `DrawFrame`'s reset loop on every level start, even though they never change.

Clean rule: **state procedures do not draw; drawing procedures do not touch state.**

---

## Procedure responsibilities after this change

| Procedure | Responsibility |
|---|---|
| `Init` | One-time setup. Calls `InitBorder` to set permanent border `Blocked` cells. |
| `InitBorder` | **New.** Set border `Blocked` to `true` — once, never reset. |
| `InitLevel(L)` | **Pure state**: interior wall `Blocked` flags, `X`, `Y`, `Key`, `EX`, `EY`, `Direction`. No drawing. |
| `DrawBorder` | Visual only: draw `█` border + call all HUD counter procedures. No `Blocked` assignments. |
| `DrawInner` | Visual only: draw interior cells from `Blocked`. |
| `Redraw` | Full visual repaint: `ClrScr` + `DrawBorder` + `DrawKeys` + `DrawInner`. No state changes. |
| `PrepareLevel` | Level reset: clear **interior** `Blocked` → `InitLevel(Level)` → `Redraw`. |
| `LevelTransition` | Show splash, wait for key, capture optional direction change, `DrawInner` to clear splash. No `InitLevel` call. |

---

## InitBorder (new procedure — add before DrawBorder)

```pascal
procedure InitBorder;
var I: Integer;
begin
  for I := 1 to FieldW do
    begin
      Blocked[I, 1] := true;
      Blocked[I, FieldH] := true;
    end;
  for I := 2 to FieldH - 1 do
    begin
      Blocked[1, I] := true;
      Blocked[FieldW, I] := true;
    end;
end;
```

Add `InitBorder;` at the end of `Init`.

---

## DrawBorder

No `Blocked` assignments. Draws border visually and delegates to HUD counter procedures:

```pascal
procedure DrawBorder;
const
  Fg = WallFg;
  Bg = FieldBg;
var I: Integer;
begin
  for I := 1 to FieldW do
    begin
      Draw(I, 1, Fg, Bg, '█');
      Draw(I, FieldH, Fg, Bg, '█');
    end;
  for I := 2 to FieldH - 1 do
    begin
      Draw(1, I, Fg, Bg, '█');
      Draw(FieldW, I, Fg, Bg, '█');
    end;
  DrawLevel;
  DrawScore;
  DrawLives;
  DrawPauses;
  DrawBlocks;
end;
```

---

## InitLevel — remove DrawInner

```pascal
procedure InitLevel(L: Integer);
begin
  case L of
    1: InitLevel1;
    ...
    9: InitLevel9;
  end;
  Direction := Key;
  { DrawInner removed }
end;
```

---

## Redraw — simplified

```pascal
procedure Redraw;
begin
  ClrScr;
  DrawBorder;   { border + HUD counters }
  DrawKeys;
  DrawInner;
end;
```

Note: `DrawBorder` is called before `DrawInner`. Inside `DrawBorder`, the border `█`
characters are drawn; border `Blocked` flags were set once by `InitBorder` and never
change. `DrawInner` iterates only interior cells (2..79, 2..19) so it does not conflict
with the border.

---

## PrepareLevel (renamed from DrawFrame)

Clear interior `Blocked` only (border cells are permanent). Call `InitLevel` first so
walls are in `Blocked` before `Redraw` → `DrawInner` reads them.

```pascal
procedure PrepareLevel;
var I, J: Integer;
begin
  for I := 2 to FieldW - 1 do
    for J := 2 to FieldH - 1 do
      Blocked[I, J] := false;
  InitLevel(Level);
  Redraw;
end;
```

---

## LevelTransition — no InitLevel, add DrawInner

The state was already set by the `PrepareLevel` call that precedes `LevelTransition` at
every call site. The splash overwrites interior cells visually; `DrawInner` restores them.

```pascal
procedure LevelTransition;
const
  Fg = SplashFg;
  Bg = FieldBg;
var UserDir: Char;
begin
  UserDir := #0;
  repeat
    DrawHLine(27, 53, 8, Fg, Bg, '█');
    Draw(27, 9, Fg, Bg, '█');
    Str(Level, S);
    Draw(28, 9, Fg, Bg, ' L E V E L   ' + S + '           ');
    Draw(53, 9, Fg, Bg, '█');
    DrawHLine(27, 53, 10, Fg, Bg, '█');
    Draw(27, 11, Fg, Bg, ' T A S T E   D R Ü C K E N ');
    Delay(1000);
  until KeyPressed;
  Key := GetKey;
  if Key in [Chr(KeyRight), Chr(KeyLeft), Chr(KeyUp), Chr(KeyDown)] then
    UserDir := Key;
  if UserDir <> #0 then Direction := UserDir;
  DrawInner;
  Delay(1000);
end;
```

---

## Cascading removals

- `PlayerCaught`: remove trailing `DrawInner;` — `PrepareLevel` → `Redraw` already includes it.
- `HandleInput` (F1/F2 handlers): remove trailing `DrawInner;` after `Redraw;` — same reason.
- `RemoveBlocks`: change clear loop bounds from `1..FieldW / 1..FieldH` to `2..FieldW-1 / 2..FieldH-1`.

---

## Done when

- [x] `poe build-original` compiles with no errors or warnings
- [x] `poe run-original`: level walls appear correctly after the level-transition splash is dismissed
- [x] Help (F1) and story (F2) screens return to the correct game state without position or wall reset
- [x] After `RemoveBlocks` (F5), the border is intact and level walls are correctly restored
- [x] No `Blocked` assignments remain in `DrawBorder` (grep confirms)
- [x] `InitLevel` contains no `Draw` or `DrawInner` calls (grep confirms)
