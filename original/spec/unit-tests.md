# Spec: Unit tests for UGLI_2

## Status

- ✗ `original/spec/unit-tests.md` — this spec committed
- ✗ `UGLI_2_Core.inc` extracted; `UGLI_2.pp` slimmed; `poe build-original` unchanged
- ✗ `UGLI_2_Test.pp` written; `poe test-original` poe task added
- ✗ `TStringTests` — 10 tests pass (UTF8Cols, Center, WordWrap, Justify)
- ✗ `TBufferTests` — 7 tests pass (BufPutCell, BufFill, BufDesaturate, BufFlush)
- ✗ `TLevelTests` — 5 tests pass (InitBorder, InitLevel1/2, start positions)
- ✗ `TDrawTests` — 5 tests pass (Draw ASCII/UTF-8, DrawHLine, DrawParagraph)
- ✗ `TGameLogicTests` — 8 tests pass (AwardPoints, IsPlayerCaught, IsItemPickedUp, GetItemName)

---

## Motivation

`UGLI_2.pp` is a single Pascal `program`. Its procedures cannot be imported by another
program via `uses`. The screen buffer (`BufFlushEnabled = false`) already suppresses terminal
output, but the main `begin…end.` block opens `TTY`, runs the intro, and starts the game loop,
making it impossible to test procedures in isolation without running the game.

The fix: extract all declarations and procedures into a shared include file
(`UGLI_2_Core.inc`). Both the game program and a new fpcunit test program include the same
file. The test program sets `BufFlushEnabled := false` before any drawing call, so no terminal
writes occur during tests.

---

## Approach: shared include file

`UGLI_2_Core.inc` contains everything between the `uses` clause and the `begin` of the main
block: all `type`/`const`/`var`/`resourcestring` declarations and all procedures.

`UGLI_2.pp` becomes:
```pascal
{$H+}
program UGLI_2;
uses CThreads, CRT, DOS, BaseUnix, SysUtils, gettext, UOSSound;
label NewGame, StartLevel, PlayAgain, OnGameOver, CleanUp;
{$I UGLI_2_Core.inc}
begin
  { ... unchanged main block ... }
end.
```

`UGLI_2_Test.pp` (new):
```pascal
{$H+}
program UGLI_2_Test;
uses CThreads, CRT, DOS, BaseUnix, SysUtils, gettext, UOSSound,
     fpcunit, testregistry, consoletestrunner;
{$I UGLI_2_Core.inc}
{ TStringTests, TBufferTests, TLevelTests, TDrawTests, TGameLogicTests }
var Runner: TTestRunner;
begin
  BufFlushEnabled := false;
  Runner := TTestRunner.Create(nil);
  Runner.Initialize;
  Runner.Run;
  Runner.Free;
end.
```

Because `BufFlushEnabled = false`, `BufFlush` exits without touching TTY. `TTY` (declared in
the include) is never opened or written. `UOSSound` falls back to silence when `libportaudio`
is unavailable.

---

## Test suite

### `TStringTests` — pure functions, no globals

| Test | Assertion |
|---|---|
| `TestUTF8Cols_Empty` | `UTF8Cols('') = 0` |
| `TestUTF8Cols_ASCII` | `UTF8Cols('abc') = 3` |
| `TestUTF8Cols_TwoByte` | `UTF8Cols('ö') = 1` |
| `TestUTF8Cols_ThreeByte` | `UTF8Cols('←') = 1` |
| `TestUTF8Cols_Mixed` | `UTF8Cols('Straße') = 6` |
| `TestCenter_Width` | `UTF8Cols(Center('AB')) = 80`; 'AB' appears at the correct position |
| `TestWordWrap_Short` | Single word ≤ Width → N=1, Lines[1]=word |
| `TestWordWrap_Wraps` | Long string with spaces → N>1, each line ≤ Width cols |
| `TestJustify_TwoWords` | `UTF8Cols(Justify('a b', 5)) = 5`; result = `'a   b'` |
| `TestJustify_OneWord` | Single word returned unchanged |

### `TBufferTests`

SetUp: `BufFlushEnabled := false; FillChar(Screen, SizeOf(Screen), 0); FillChar(Dirty, SizeOf(Dirty), 0)`

| Test | Assertion |
|---|---|
| `TestBufPutCell_Stores` | `BufPutCell(3,5,Red,Black,'A')` → `Screen[3,5].Ch='A'`, `.Fg=Red`, `.Bg=Black` |
| `TestBufPutCell_MarksDirty` | `Dirty[3,5] = true` after put |
| `TestBufPutCell_SkipsWhenSame` | Put, clear dirty, put same → `Dirty[3,5] = false` |
| `TestBufPutCell_IgnoresOOB` | `BufPutCell(0,0,0,0,'X')` and `BufPutCell(81,26,0,0,'X')` — no crash |
| `TestBufFill_AllCells` | After `BufFill(White,Black,' ')`: sampled cells correct; all dirty |
| `TestBufDesaturate_Gray` | After fill + desaturate: `.Fg=LightGray`, `.Bg=Black`, dirty |
| `TestBufFlush_ClearsDirty` | After fill then `BufFlush`: all `Dirty` false |

### `TLevelTests`

SetUp: `BufFlushEnabled := false; FillChar(Blocked, SizeOf(Blocked), 0)`

| Test | Assertion |
|---|---|
| `TestInitBorder_Corners` | `Blocked[1,1]`, `Blocked[80,1]`, `Blocked[1,20]`, `Blocked[80,20]` all true |
| `TestInitBorder_Interior` | `Blocked[40,10] = false` |
| `TestInitLevel1_NoWalls` | After `InitLevel1`: no interior cell blocked; `StartX=40`, `StartY=10` |
| `TestInitLevel2_Wall` | After `InitBorder + InitLevel2`: `Blocked[18,10]` and `Blocked[62,10]` true |
| `TestInitLevel1to9_StartPos` | Each `InitLevelN` sets `StartX/StartY` inside `[2..79, 2..19]` |

### `TDrawTests`

SetUp: `BufFlushEnabled := false; FillChar(Screen, SizeOf(Screen), 0); FillChar(Dirty, SizeOf(Dirty), 0)`

| Test | Assertion |
|---|---|
| `TestDraw_ASCII` | `Draw(5,3,White,Black,'Hi')` → `Screen[5,3].Ch='H'`, `Screen[6,3].Ch='i'` |
| `TestDraw_ThreeByte` | `Draw(1,1,Red,Black,'←')` → `Screen[1,1].Ch='←'` |
| `TestDrawHLine_Range` | `DrawHLine(2,6,4,White,Black,'─')` → cols 2–6, row 4 all have `Ch='─'`; col 1 unchanged |
| `TestDrawParagraph_Count` | `DrawParagraph('word',1,1,72,White,Black)` returns 1 |
| `TestDrawParagraph_Wraps` | Long string → return value > 1 |

### `TGameLogicTests`

SetUp: `BufFlushEnabled := false; Score := 0; ItemNo := 1; X := 5; Y := 5; EX := 10; EY := 10; ItemX := 20; ItemY := 15`

| Test | Assertion |
|---|---|
| `TestAwardPoints_Item1` | `ItemNo:=1; AwardPoints` → `Score = 100` |
| `TestAwardPoints_Item5` | `ItemNo:=5; AwardPoints` → `Score = 500` |
| `TestIsPlayerCaught_True` | `EX:=X; EY:=Y` → `IsPlayerCaught = true` |
| `TestIsPlayerCaught_False` | `EX<>X` → `IsPlayerCaught = false` |
| `TestIsItemPickedUp_True` | `ItemX:=X; ItemY:=Y` → `IsItemPickedUp = true` |
| `TestIsItemPickedUp_False` | `ItemX<>X` → `IsItemPickedUp = false` |
| `TestGetItemName_Rope` | `GetItemName(1) = 'Rope'` (English default, no translation loaded) |
| `TestGetItemName_Crown` | `GetItemName(10) = 'Crown'` |

---

## Build

```
cd original && fpc -Fuuos UGLI_2_Test.pp -o UGLI_2_Test && ./UGLI_2_Test
```

fpcunit is in FPC's standard search path on Arch Linux (`fcl-fpcunit` package). Add
`-Fu/usr/lib/fpc/3.2.2/units/x86_64-linux/fcl-fpcunit` if the compiler cannot find it.

`pyproject.toml` poe task:

```toml
[tool.poe.tasks.test-original]
help  = "Build and run UGLI_2 unit tests"
shell = "cd original && fpc -Fuuos UGLI_2_Test.pp -o UGLI_2_Test && ./UGLI_2_Test"
```

---

## Commit order

1. `original/spec/unit-tests.md` — this spec
2. Extract `UGLI_2_Core.inc`; slim `UGLI_2.pp`; verify `poe build-original` unchanged
3. `original/UGLI_2_Test.pp` + `poe test-original` task; all tests pass

---

## Done when

- ✗ `poe build-original` succeeds with the slimmed `UGLI_2.pp` + include — _commit 2_
- ✗ `poe test-original` compiles and exits 0 — _commit 3_
- ✗ All 5 test case classes run — _commit 3_
- ✗ All 35 individual tests pass — _commit 3_
- ✗ `BufFlushEnabled := false` prevents terminal writes during the test run — _commit 3_
