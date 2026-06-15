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
{$I UGLI_2_BufFlush_Variants.inc}

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
{ Scenario helpers                                                    }
{ ------------------------------------------------------------------ }

procedure FillTestPattern;
{ Representative game screen: border, HUD, player, enemy, walls,
  and a row of item chars covering 1-byte, 2-byte, and 3-byte UTF-8. }
var Col, Row: Integer;
begin
  FillChar(Screen,  SizeOf(Screen),  0);
  FillChar(Dirty,   SizeOf(Dirty),   0);
  FillChar(Blocked, SizeOf(Blocked), 0);
  { Pre-fill every cell with a space so span-write variants never emit
    zero bytes for an undrawn cell and cause cursor-position drift. }
  for Col := 1 to ScreenW do
    for Row := 1 to ScreenH do
      begin
        Screen[Col, Row].Ch := ' ';
        Screen[Col, Row].Fg := FieldBg;
        Screen[Col, Row].Bg := FieldBg;
      end;
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
  TResult = record Avg, Best, Worst: Int64; end;

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
  R1, R2, R3, R4, R5: TResult;
end;

const NumScenarios = 3;
var
  Scenarios: array[1..NumScenarios] of TScenario;

procedure PrintResult(var F: Text; const VName: String; const R: TResult);
begin
  WriteLn(F, Format('  %-24s  avg=%5d  min=%5d  max=%5d  us',
    [VName, R.Avg, R.Best, R.Worst]));
end;

procedure PrintTimingResults(var F: Text);
var S: Integer;
begin
  WriteLn(F);
  WriteLn(F, 'UGLI_2_Bench  —  BufFlush variants  (', Reps, ' reps, times in microseconds)');
  WriteLn(F, '  TTY output goes to kernel buffer; Flush() blocks until buffer drained.');
  WriteLn(F);
  WriteLn(F, '  Variants:');
  WriteLn(F, '    V1   current: ESC[r;cH before every dirty cell; Write+Flush');
  WriteLn(F, '    V2   consec-skip: omit ESC[r;cH when cursor already adjacent');
  WriteLn(F, '    V3   row-span: one ESC[r;cH per row at first dirty col; write span');
  WriteLn(F, '    V2b  consec-skip + single fpWrite syscall');
  WriteLn(F, '    V3b  row-span + single fpWrite syscall');
  WriteLn(F);
  for S := 1 to NumScenarios do
    begin
      WriteLn(F, Scenarios[S].Name);
      PrintResult(F, 'V1  (per-cell, current)', Scenarios[S].R1);
      PrintResult(F, 'V2  (consec-skip)',        Scenarios[S].R2);
      PrintResult(F, 'V3  (row-span)',            Scenarios[S].R3);
      PrintResult(F, 'V2b (consec-skip+1write)', Scenarios[S].R4);
      PrintResult(F, 'V3b (row-span+1write)',     Scenarios[S].R5);
      WriteLn(F);
    end;
end;

{ Show a full-screen render of FlushProc; wait for Enter before continuing. }
procedure ShowVisual(FlushProc: TFlushProc; const VName, VDesc, Prompt: String);
begin
  Write(TTY, #27'[2J'#27'[H'); Flush(TTY);
  MarkAllDirty;
  FlushProc();
  { Reset SGR before caption so the last cell's colour doesn't bleed. }
  Write(TTY, #27'[0m'#27'[17;1H'#27'[0;97;40m');
  Write(TTY, ' Variant: ', VName, '  (', VDesc, ')                   ');
  Write(TTY, #27'[18;1H');
  Write(TTY, ' Row 14: | : * = (1-byte)  Γ Φ (2-byte)  ≡ ♦ ⌂ ☼ ☺ (3-byte)   ');
  Write(TTY, #27'[19;1H');
  Write(TTY, ' Verify: border intact, colours correct, chars at right columns. ');
  Write(TTY, #27'[20;1H');
  Write(TTY, ' ', Prompt, '                                                        ');
  Write(TTY, #27'[?25h');
  Flush(TTY);
  ReadLn;
  Write(TTY, #27'[?25l');
  Flush(TTY);
end;

{ ------------------------------------------------------------------ }
{ Main                                                               }
{ ------------------------------------------------------------------ }
var OutPath: String; OutFile: Text;
begin
  OutPath := '';
  if (ParamCount >= 2) and (ParamStr(1) = '--output') then
    OutPath := ParamStr(2);

  Assign(TTY, '/dev/tty');
  ReWrite(TTY);
  RawTTYFd := fpOpen('/dev/tty', O_WRONLY);
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
  Scenarios[1].R4 := RunBench(@BufFlushV2b);
  Scenarios[1].R5 := RunBench(@BufFlushV3b);

  { --- Scenario 2: border only ---------------------------------------- }
  Scenarios[2].Name := 'Border only (~197 dirty)';
  MarkBorderDirty; SaveDirtyState;
  Scenarios[2].R1 := RunBench(@BufFlush);
  Scenarios[2].R2 := RunBench(@BufFlushV2);
  Scenarios[2].R3 := RunBench(@BufFlushV3);
  Scenarios[2].R4 := RunBench(@BufFlushV2b);
  Scenarios[2].R5 := RunBench(@BufFlushV3b);

  { --- Scenario 3: sparse --------------------------------------------- }
  Scenarios[3].Name := 'Sparse (50 random dirty)';
  RandSeed := 42;
  MarkSparseDirty; SaveDirtyState;
  Scenarios[3].R1 := RunBench(@BufFlush);
  Scenarios[3].R2 := RunBench(@BufFlushV2);
  Scenarios[3].R3 := RunBench(@BufFlushV3);
  Scenarios[3].R4 := RunBench(@BufFlushV2b);
  Scenarios[3].R5 := RunBench(@BufFlushV3b);

  { --- Visual correctness test (one variant per screen) --------------- }
  ShowVisual(@BufFlush,    'V1',  'per-cell ESC[r;cH + Write/Flush',     'Press Enter to see V2...');
  ShowVisual(@BufFlushV2,  'V2',  'consec-skip: omit ESC[r;cH if adjacent', 'Press Enter to see V3...');
  ShowVisual(@BufFlushV3,  'V3',  'row-span: position once per row',      'Press Enter to see V2b...');
  ShowVisual(@BufFlushV2b, 'V2b', 'consec-skip + single fpWrite',         'Press Enter to see V3b...');
  ShowVisual(@BufFlushV3b, 'V3b', 'row-span + single fpWrite',            'Press Enter to close window and see timing.');

  { Exit alternate screen — main buffer reappears. }
  Write(TTY, #27'[?1049l'#27'[?25l');
  Flush(TTY);
  fpClose(RawTTYFd);
  Close(TTY);

  { Print timing results to stdout and, if --output given, to a file. }
  PrintTimingResults(Output);
  if OutPath <> '' then
    begin
      Assign(OutFile, OutPath);
      ReWrite(OutFile);
      PrintTimingResults(OutFile);
      Close(OutFile);
    end;
end.
