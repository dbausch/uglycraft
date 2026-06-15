{$mode objfpc}{$H+}
{ BufFlush performance benchmark.
  Three variants are timed across three dirty-cell scenarios, then a
  visual correctness check is shown (1-byte, 2-byte, 3-byte UTF-8 chars
  side by side, various colours) before printing timing results.

  Build and run with:  poe bench-original
}
program UGLI_2_Bench;

uses CThreads, DOS, BaseUnix, Unix, SysUtils, termio, gettext, UOSSound;

const
  User    = 'Public Domain';
  Version = '2.3';
  Release = '0042';
  FieldW  = 80;
  FieldH  = 20;
  ScreenW = FieldW;
  ScreenH = 25;
  KeyRight = 77;  KeyLeft  = 75;  KeyDown  = 80;  KeyUp    = 72;
  KeyPause = 112; KeySlower = 79; KeyFaster = 71;
  KeyEscape = 27; KeySpace  = 32;
  KeyF1 = 59; KeyF2 = 60; KeyF3 = 61; KeyF4 = 62; KeyF5 = 63;
  HighScoreFileName = 'UGLI.HSC';
  License = 'Released under the terms of the GNU GPLv3';
  Black        = 0;  Blue         = 1;  Green        = 2;  Cyan         = 3;
  Red          = 4;  Magenta      = 5;  Brown        = 6;  LightGray    = 7;
  DarkGray     = 8;  LightBlue    = 9;  LightGreen   = 10; LightCyan    = 11;
  LightRed     = 12; LightMagenta = 13; Yellow       = 14; White        = 15;
  Blink        = $80;
  WallFg    = Red;      PlayerFg  = Yellow;  EnemyFg   = Brown;
  CounterFg = White;    CounterBg = Red;     FieldBg   = Black;
  KeyHelpFg = LightCyan; HelpFg  = Magenta;  SplashFg  = White;
  DialogFg  = White;   WinFg     = LightRed;
  ItemDescFg = Black;  ItemDescBg = LightGray;
  ItemCount  = 10;

{$I UGLI_2_Core.inc}

{ ------------------------------------------------------------------ }
{ Timing                                                             }
{ ------------------------------------------------------------------ }

function MicroNow: Int64;
var TV: TimeVal;
begin
  fpGetTimeOfDay(@TV, nil);
  MicroNow := Int64(TV.tv_sec) * 1000000 + TV.tv_usec;
end;

{ ------------------------------------------------------------------ }
{ V2: skip ESC[r;cH when cursor is already at the next cell         }
{ ------------------------------------------------------------------ }

procedure BufFlushV2;
const AnsiClr: array[0..7] of Byte = (0, 4, 2, 6, 1, 5, 3, 7);
var Col, Row, LastFg, LastBg, FgCode, BgCode, LastCol, LastRow: Integer;
begin
  if not BufFlushEnabled then
    begin
      for Col := 1 to ScreenW do
        for Row := 1 to ScreenH do
          Dirty[Col, Row] := false;
      Exit;
    end;
  Write(TTY, #27'[?7l');
  LastFg := -1; LastBg := -1; LastCol := -1; LastRow := -1;
  for Row := 1 to ScreenH do
    for Col := 1 to ScreenW do
      if Dirty[Col, Row] then
        begin
          if (Screen[Col, Row].Fg <> LastFg) or (Screen[Col, Row].Bg <> LastBg) then
            begin
              if Screen[Col, Row].Fg < 8 then
                FgCode := 30 + AnsiClr[Screen[Col, Row].Fg]
              else
                FgCode := 90 + AnsiClr[Screen[Col, Row].Fg - 8];
              BgCode := 40 + AnsiClr[Screen[Col, Row].Bg and 7];
              Write(TTY, #27'[0;', FgCode, ';', BgCode, 'm');
              LastFg := Screen[Col, Row].Fg;
              LastBg := Screen[Col, Row].Bg;
            end;
          if (Col <> LastCol + 1) or (Row <> LastRow) then
            Write(TTY, #27'[', Row, ';', Col, 'H');
          Write(TTY, Screen[Col, Row].Ch);
          LastCol := Col;
          LastRow := Row;
          Dirty[Col, Row] := false;
        end;
  Write(TTY, #27'[?7h');
  Flush(TTY);
end;

{ ------------------------------------------------------------------ }
{ V3: per row, position once at first dirty cell, write span        }
{ Clean cells inside the span are still correct — Screen always     }
{ holds the current display state.                                   }
{ ------------------------------------------------------------------ }

procedure BufFlushV3;
const AnsiClr: array[0..7] of Byte = (0, 4, 2, 6, 1, 5, 3, 7);
var Col, Row, LastFg, LastBg, FgCode, BgCode, First, Last: Integer;
begin
  if not BufFlushEnabled then
    begin
      for Col := 1 to ScreenW do
        for Row := 1 to ScreenH do
          Dirty[Col, Row] := false;
      Exit;
    end;
  Write(TTY, #27'[?7l');
  LastFg := -1; LastBg := -1;
  for Row := 1 to ScreenH do
    begin
      First := 0; Last := 0;
      for Col := 1 to ScreenW do
        if Dirty[Col, Row] then
          begin
            if First = 0 then First := Col;
            Last := Col;
          end;
      if First = 0 then Continue;
      Write(TTY, #27'[', Row, ';', First, 'H');
      for Col := First to Last do
        begin
          if (Screen[Col, Row].Fg <> LastFg) or (Screen[Col, Row].Bg <> LastBg) then
            begin
              if Screen[Col, Row].Fg < 8 then
                FgCode := 30 + AnsiClr[Screen[Col, Row].Fg]
              else
                FgCode := 90 + AnsiClr[Screen[Col, Row].Fg - 8];
              BgCode := 40 + AnsiClr[Screen[Col, Row].Bg and 7];
              Write(TTY, #27'[0;', FgCode, ';', BgCode, 'm');
              LastFg := Screen[Col, Row].Fg;
              LastBg := Screen[Col, Row].Bg;
            end;
          Write(TTY, Screen[Col, Row].Ch);
          Dirty[Col, Row] := false;
        end;
    end;
  Write(TTY, #27'[?7h');
  Flush(TTY);
end;

{ ------------------------------------------------------------------ }
{ Scenario helpers                                                    }
{ ------------------------------------------------------------------ }

procedure FillTestPattern;
{ Representative game screen: border, HUD, player, enemy, walls,
  and a row of item chars covering 1-byte, 2-byte, and 3-byte UTF-8. }
var Col: Integer;
begin
  FillChar(Screen,  SizeOf(Screen),  0);
  FillChar(Dirty,   SizeOf(Dirty),   0);
  FillChar(Blocked, SizeOf(Blocked), 0);
  Level := 3; Score := 12345; Lives := 7; ItemNo := 3;
  PausesRemaining := 18; BlocksRemaining := 1980;
  InitBorder;
  DrawBorder;
  { Player and enemy }
  Draw(40, 10, PlayerFg,   FieldBg, '☺');
  Draw(10,  8, EnemyFg,    FieldBg, '☻');
  { A horizontal wall segment }
  for Col := 15 to 25 do Draw(Col, 7, WallFg, FieldBg, '█');
  { Item characters — 1-byte ASCII }
  Draw(4, 14, Brown,      FieldBg, '|');
  Draw(5, 14, LightRed,   FieldBg, ':');
  Draw(6, 14, LightBlue,  FieldBg, '*');
  Draw(7, 14, Yellow,     FieldBg, '=');
  { 2-byte UTF-8 (U+03xx Latin/Greek) }
  Draw(9, 14, Cyan,       FieldBg, 'Γ');   { U+0393 }
  Draw(10, 14, Yellow,    FieldBg, 'Φ');   { U+03A6 }
  { 3-byte UTF-8 (U+2xxx, U+263x) }
  Draw(12, 14, LightGray, FieldBg, '≡');  { U+2261 }
  Draw(13, 14, LightGreen,FieldBg, '♦');  { U+2666 }
  Draw(14, 14, Yellow,    FieldBg, '⌂');  { U+2302 }
  Draw(15, 14, LightBlue, FieldBg, '☼');  { U+263C }
  Draw(16, 14, Yellow,    FieldBg, '☺');  { U+263A }
end;

var
  SavedDirty: array[1..ScreenW, 1..ScreenH] of Boolean;

procedure SaveDirtyState;
begin
  SavedDirty := Dirty;
end;

procedure RestoreDirtyState;
begin
  Dirty := SavedDirty;
end;

procedure MarkAllDirty;
var Col, Row: Integer;
begin
  for Col := 1 to ScreenW do
    for Row := 1 to ScreenH do
      Dirty[Col, Row] := true;
end;

procedure MarkBorderDirty;
var Col, Row: Integer;
begin
  FillChar(Dirty, SizeOf(Dirty), 0);
  for Col := 1 to ScreenW do
    begin Dirty[Col, 1] := true; Dirty[Col, FieldH] := true; end;
  for Row := 2 to FieldH - 1 do
    begin Dirty[1, Row] := true; Dirty[FieldW, Row] := true; end;
end;

procedure MarkSparseDirty;
{ 50 random cells — models a single HUD element update. }
var Index: Integer;
begin
  FillChar(Dirty, SizeOf(Dirty), 0);
  for Index := 1 to 50 do
    Dirty[Random(ScreenW) + 1, Random(ScreenH) + 1] := true;
end;

{ ------------------------------------------------------------------ }
{ Benchmark runner                                                    }
{ ------------------------------------------------------------------ }

const Warmup = 5; Reps = 30;

type
  TFlushProc = procedure;
  TResult    = record Avg, Best, Worst: Int64; end;

function RunBench(FlushProc: TFlushProc): TResult;
var Index: Integer; T0, T1, Total: Int64;
begin
  for Index := 1 to Warmup do begin RestoreDirtyState; FlushProc; end;
  Total := 0; Result.Best := High(Int64); Result.Worst := 0;
  for Index := 1 to Reps do
    begin
      RestoreDirtyState;
      T0 := MicroNow;
      FlushProc;
      T1 := MicroNow;
      Inc(Total, T1 - T0);
      if T1 - T0 < Result.Best  then Result.Best  := T1 - T0;
      if T1 - T0 > Result.Worst then Result.Worst := T1 - T0;
    end;
  Result.Avg := Total div Reps;
end;

{ Results storage — printed after exiting alternate screen. }
type TScenario = record
  Name: String[40];
  R1, R2, R3: TResult;
end;

const NumScenarios = 3;
var
  Scenarios: array[1..NumScenarios] of TScenario;
  BenchS: Integer;  { loop variable for printing results }

procedure PrintResult(const VName: String; const R: TResult);
begin
  WriteLn(Format('  %-24s  avg=%5d  min=%5d  max=%5d  us',
    [VName, R.Avg, R.Best, R.Worst]));
end;

{ ------------------------------------------------------------------ }
{ Main                                                               }
{ ------------------------------------------------------------------ }
begin
  Assign(TTY, '/dev/tty');
  ReWrite(TTY);
  BufFlushEnabled := true;

  { Enter alternate screen — renders don't touch the main scrollback. }
  Write(TTY, #27'[?1049h'#27'[?25l'#27'[2J'#27'[H');
  Flush(TTY);

  FillTestPattern;

  { --- Scenario 1: full screen ---------------------------------------- }
  Scenarios[1].Name := 'Full screen (2000 dirty)';
  MarkAllDirty; SaveDirtyState;
  Scenarios[1].R1 := RunBench(@BufFlush);
  Scenarios[1].R2 := RunBench(@BufFlushV2);
  Scenarios[1].R3 := RunBench(@BufFlushV3);

  { --- Scenario 2: border only ---------------------------------------- }
  Scenarios[2].Name := 'Border only (~197 dirty)';
  MarkBorderDirty; SaveDirtyState;
  Scenarios[2].R1 := RunBench(@BufFlush);
  Scenarios[2].R2 := RunBench(@BufFlushV2);
  Scenarios[2].R3 := RunBench(@BufFlushV3);

  { --- Scenario 3: sparse --------------------------------------------- }
  Scenarios[3].Name := 'Sparse (50 random dirty)';
  RandSeed := 42;
  MarkSparseDirty; SaveDirtyState;
  Scenarios[3].R1 := RunBench(@BufFlush);
  Scenarios[3].R2 := RunBench(@BufFlushV2);
  Scenarios[3].R3 := RunBench(@BufFlushV3);

  { --- Visual correctness test ---------------------------------------- }
  { Final clean render using V3 — user checks the display before we exit. }
  Write(TTY, #27'[2J'#27'[H'); Flush(TTY);
  MarkAllDirty;
  BufFlushV3;
  { Caption at row 17 (safe below item row at 14) }
  Write(TTY, #27'[17;1H'#27'[0;97;40m');
  Write(TTY, ' Row 14: | : * = (1-byte)  Γ Φ (2-byte)  ≡ ♦ ⌂ ☼ ☺ (3-byte)   ');
  Write(TTY, #27'[18;1H');
  Write(TTY, ' Verify: border intact, colours correct, chars at right columns. ');
  Write(TTY, #27'[19;1H');
  Write(TTY, ' Press Enter to exit benchmark and see timing results.           ');
  Write(TTY, #27'[?25h');
  Flush(TTY);
  ReadLn;

  { Exit alternate screen — main buffer reappears. }
  Write(TTY, #27'[?1049l'#27'[?25l');
  Flush(TTY);
  Close(TTY);

  { Print timing results to stdout (now on main screen / scrollback). }
  WriteLn;
  WriteLn('UGLI_2_Bench  —  BufFlush variants  (', Reps, ' reps, times in microseconds)');
  WriteLn('  TTY output goes to kernel buffer; Flush() blocks until buffer drained.');
  WriteLn;
  WriteLn('  Variants:');
  WriteLn('    V1  current: ESC[r;cH before every dirty cell');
  WriteLn('    V2  consec-skip: omit ESC[r;cH when cursor already adjacent');
  WriteLn('    V3  row-span: one ESC[r;cH per row at first dirty col; write span');
  WriteLn;
  for BenchS := 1 to NumScenarios do
    begin
      WriteLn(Scenarios[BenchS].Name);
      PrintResult('V1 (per-cell, current)', Scenarios[BenchS].R1);
      PrintResult('V2 (consec-skip)',        Scenarios[BenchS].R2);
      PrintResult('V3 (row-span)',            Scenarios[BenchS].R3);
      WriteLn;
    end;
end.
