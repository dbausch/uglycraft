# Spec: Color system — Draw procedure + named color constants

## Status

- [x] Color constants added to `const` section
- [x] `WriteXY` renamed to `Draw`; `Fg`/`Bg` parameters added
- [x] `DrawHLine` updated with `Fg`/`Bg` parameters
- [x] All call sites updated: `TextColor`/`TextBackground` removed, colors passed inline
- [x] Local `const Fg/Bg` blocks added in procedures that repeat one color pair
- [x] `DrawLives`/`DrawBlocks` `LightRed` background bug fixed (`CounterBg = Red`)

---

## Motivation

`TextColor` and `TextBackground` are global side effects. Any `WriteXY` call silently
inherits whatever colors a prior call left set. This makes procedure ordering load-bearing
in non-obvious ways and makes call sites hard to read in isolation.

The fix: pass `Fg` (foreground) and `Bg` (background) as parameters to `Draw` (the renamed
`WriteXY`). Every write now declares its own colors. No write can inherit a stale color.

---

## Color constants (add to `const` section after the key-code constants)

```pascal
{ Foreground / background color roles }
WallFg    = Red;       { border and interior wall blocks █ }
PlayerFg  = Yellow;    { player smiley ☺ }
EnemyFg   = Brown;     { enemy smiley ☻ }
CounterFg = White;     { HUD counter text }
CounterBg = Red;       { background for all HUD counters (was LightRed for lives/blocks — bug) }
FieldBg   = Black;     { playing field background }
KeyHelpFg = LightCyan; { key-help bar text }
HelpFg    = Magenta;   { help-screen and story-screen text }
SplashFg  = White;     { level-transition splash text }
DialogFg  = White;     { modal dialog text (AskPlayAgain, RemoveBlocks) }
WinFg     = LightRed;  { win-screen text (with Blink) }
```

Items keep their existing literal color values per branch (no semantic constant needed — each
item is a distinct visual element, not a shared role).

---

## Draw procedure signature

```pascal
{ BEFORE }
procedure WriteXY(Col, Row: Integer; S: String);

{ AFTER }
procedure Draw(Col, Row, Fg, Bg: Integer; S: String);
```

At the start of `Draw`, set `TextColor(Fg); TextBackground(Bg);` before the write loop.
All other `TextColor`/`TextBackground` calls throughout the file are removed.

---

## DrawHLine signature

```pascal
{ BEFORE }
procedure DrawHLine(X1, X2, Y: Integer; Ch: String);

{ AFTER }
procedure DrawHLine(X1, X2, Y, Fg, Bg: Integer; Ch: String);
```

Passes `Fg`/`Bg` directly to `Draw`.

---

## Local Fg/Bg constants convention

Procedures that call `Draw` with the same color pair more than once define:

```pascal
const
  Fg = <role constant>;
  Bg = <role constant>;
```

Where only one dimension is shared (e.g. all draws share the same background, different
foregrounds), define only `Bg`. Example:

```pascal
procedure DrawScore;
const
  Fg = CounterFg;
  Bg = CounterBg;
var S: String;
begin
  Str(Score:5, S);
  Draw(3, 1, Fg, Bg, 'PUNKTE ' + S);
end;

procedure MoveRight(var X: Integer; var Y: Integer);
const
  Bg = FieldBg;
var OldX: Integer;
begin
  ...
  Draw(OldX, Y, Bg, Bg, ' ');
  Draw(X, Y, PlayerFg, Bg, '☺');
  Draw(BlockX, BlockY, WallFg, Bg, '█');
end;
```

---

## Affected procedures

All of the following lose their free-standing `TextColor`/`TextBackground` calls and gain
inline colors on every `Draw`/`DrawHLine` call:

`Draw` (was `WriteXY`), `DrawHLine`, `DrawBorder`, `DrawLevel` (was `WriteLevel`),
`DrawScore`, `DrawLives`, `DrawPauses`, `DrawBlocks`, `DrawKeys`, `DrawInner`,
`MoveDown`, `MoveLeft`, `MoveRight`, `MoveUp`, `EnemyMove`, `PlaceBlock`,
`DrawItem`, `LevelTransition`, `ShowHelp`, `ShowStory`, `GameOver`, `WinScreen`,
`AskPlayAgain`, `RemoveBlocks`.

Additionally: the stray `TextColor(2)` at the top of `DrawItem` is removed (it was
immediately overridden by every branch inside the procedure).

---

## Done when

- [x] `poe build-original` compiles with no errors or warnings
- [x] `poe run-original`: all screen elements display with the correct colors
- [x] HUD counters (score, lives, pauses, blocks, level) all show on a Red background
- [x] No `TextColor`/`TextBackground` calls remain that affect subsequent `Draw` calls (grep confirms: only the pair inside `Draw`, the pair inside `HighScoreEntry` for `WriteLn` prompts, and `TextBackground(FieldBg)` immediately before `ClrScr` calls are allowed)
