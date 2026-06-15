{$mode objfpc}{$H+}
program UGLI_2_Test;

uses CThreads, DOS, BaseUnix, SysUtils, termio, gettext, UOSSound,
     fpcunit, testregistry, consoletestrunner;

const
  User = 'Public Domain';
  Version = '2.3';
  Release = '0042';
  FieldW = 80;
  FieldH = 20;
  ScreenW = FieldW;
  ScreenH = 25;
  KeyRight = 77;
  KeyLeft = 75;
  KeyDown = 80;
  KeyUp = 72;
  KeyPause = 112;
  KeySlower = 79;
  KeyFaster = 71;
  KeyEscape = 27;
  KeySpace = 32;
  KeyF1 = 59;
  KeyF2 = 60;
  KeyF3 = 61;
  KeyF4 = 62;
  KeyF5 = 63;
  KeyF6 = 64;
  HighScoreFileName = 'UGLI.HSC';
  License = 'Released under the terms of the GNU GPLv3';
  Black        = 0;
  Blue         = 1;
  Green        = 2;
  Cyan         = 3;
  Red          = 4;
  Magenta      = 5;
  Brown        = 6;
  LightGray    = 7;
  DarkGray     = 8;
  LightBlue    = 9;
  LightGreen   = 10;
  LightCyan    = 11;
  LightRed     = 12;
  LightMagenta = 13;
  Yellow       = 14;
  White        = 15;
  Blink        = $80;
  WallFg    = Red;
  PlayerFg  = Yellow;
  EnemyFg   = Brown;
  CounterFg = White;
  CounterBg = Red;
  FieldBg   = Black;
  KeyHelpFg = LightCyan;
  HelpFg    = Magenta;
  SplashFg  = White;
  DialogFg  = White;
  WinFg      = LightRed;
  ItemDescFg = Black;
  ItemDescBg = LightGray;
  ItemCount  = 10;

{$I UGLI_2_Core.inc}
{$I UGLI_2_BufFlush_Variants.inc}

{ ------------------------------------------------------------------ }
{ Key queue — inject predetermined keystrokes into WaitKey-based     }
{ procedures without opening a real TTY.                             }
{ ------------------------------------------------------------------ }
const KeyQueueSize = 32;

var
  KeyQueue  : array[0..KeyQueueSize - 1] of Integer;
  KeyQueueH : Integer = 0;
  KeyQueueT : Integer = 0;
  KeyCapture: TScreenBuffer;  { screen buffer snapped at WaitKey time }

procedure ClearKeyQueue;
begin
  KeyQueueH := 0;
  KeyQueueT := 0;
end;

procedure EnqueueKey(K: Integer);
begin
  KeyQueue[KeyQueueT] := K;
  KeyQueueT := (KeyQueueT + 1) mod KeyQueueSize;
end;

{ Dequeue the next key; 'N' (exits any Yes/No loop) when queue empty. }
function DequeueKey: Integer;
begin
  if KeyQueueH <> KeyQueueT then
    begin
      DequeueKey := KeyQueue[KeyQueueH];
      KeyQueueH  := (KeyQueueH + 1) mod KeyQueueSize;
    end
  else
    DequeueKey := Ord('N');
end;

{ Like DequeueKey but also snapshots Screen into KeyCapture first. }
function CapturingDequeueKey: Integer;
begin
  BufCopy(KeyCapture);
  CapturingDequeueKey := DequeueKey;
end;

{ Shared setup for any test class that needs KeyProviderFunc. }
procedure KeyTestSetUp;
begin
  BufFlushEnabled    := false;
  FillChar(Screen,  SizeOf(Screen),  0);
  FillChar(Dirty,   SizeOf(Dirty),   0);
  FillChar(Blocked, SizeOf(Blocked), 0);
  InitBorder;
  Level            := 1;
  Score            := 0;
  Lives            := 3;
  ItemNo           := 1;
  MoveDelay        := 100;
  PausesRemaining  := 20;
  BlocksRemaining  := 2000;
  X := 40; Y := 10;
  EX := 5;  EY := 10;
  ItemX := 0; ItemY := 0;  { 0 → DrawInner skips item sprite }
  BlockX := 1; BlockY := 1;
  EnemyTick        := 0;
  Direction        := DirRight;
  { Build YesKey / NoKey from the English defaults; Init is not called. }
  YesKey := [Ord('Y'), Ord('y')];
  NoKey  := [Ord('N'), Ord('n')];
  ClearKeyQueue;
  KeyProviderFunc := @DequeueKey;
end;

procedure KeyTestTearDown;
begin
  KeyProviderFunc := nil;
  ClearKeyQueue;
end;

{ ------------------------------------------------------------------ }
{ TStringTests — pure functions, no global state needed              }
{ ------------------------------------------------------------------ }

type
  TStringTests = class(TTestCase)
  published
    procedure TestUTF8Cols_Empty;
    procedure TestUTF8Cols_ASCII;
    procedure TestUTF8Cols_TwoByte;
    procedure TestUTF8Cols_ThreeByte;
    procedure TestUTF8Cols_Mixed;
    procedure TestCenter_LeadingSpaces;
    procedure TestCenter_OddLength;
    procedure TestWordWrap_Short;
    procedure TestWordWrap_Wraps;
    procedure TestWordWrap_Empty;
    procedure TestWordWrap_LeadingSpaces;
    procedure TestWordWrap_SingleLongWord;
    procedure TestJustify_TwoWords;
    procedure TestJustify_OneWord;
    procedure TestJustify_ThreeWords;
    procedure TestJustify_AlreadyWide;
  end;

procedure TStringTests.TestUTF8Cols_Empty;
begin
  AssertEquals(0, UTF8Cols(''));
end;

procedure TStringTests.TestUTF8Cols_ASCII;
begin
  AssertEquals(3, UTF8Cols('abc'));
end;

procedure TStringTests.TestUTF8Cols_TwoByte;
begin
  AssertEquals(1, UTF8Cols('ö'));
end;

procedure TStringTests.TestUTF8Cols_ThreeByte;
begin
  AssertEquals(1, UTF8Cols('←'));
end;

procedure TStringTests.TestUTF8Cols_Mixed;
begin
  AssertEquals(6, UTF8Cols('Straße'));
end;

procedure TStringTests.TestCenter_LeadingSpaces;
var R: String;
begin
  R := Center('AB');
  { Center: Blanks = 39 - (2 div 2) = 38 leading spaces }
  AssertEquals(38, Pos('A', R) - 1);
  AssertEquals(40, UTF8Cols(R));
end;

procedure TStringTests.TestCenter_OddLength;
var R: String;
begin
  { 3-char string: Blanks = 39 - (3 div 2) = 39 - 1 = 38 }
  R := Center('ABC');
  AssertEquals(38, Pos('A', R) - 1);
end;

procedure TStringTests.TestWordWrap_Short;
var Lines: array[0..11] of String; N: Integer;
begin
  WordWrap('hello', 72, Lines, N);
  AssertEquals(1, N);
  AssertEquals('hello', Lines[0]);
end;

procedure TStringTests.TestWordWrap_Wraps;
var Lines: array[0..11] of String; N, I: Integer;
begin
  WordWrap('aaa bbb ccc', 5, Lines, N);
  AssertTrue('N > 1', N > 1);
  for I := 0 to N - 1 do
    AssertTrue('line width', UTF8Cols(Lines[I]) <= 5);
end;

procedure TStringTests.TestWordWrap_Empty;
var Lines: array[0..11] of String; N: Integer;
begin
  WordWrap('', 72, Lines, N);
  AssertEquals(0, N);
end;

procedure TStringTests.TestWordWrap_LeadingSpaces;
var Lines: array[0..11] of String; N: Integer;
begin
  { Leading spaces are consumed before the first word. }
  WordWrap('  hello', 72, Lines, N);
  AssertEquals(1, N);
  AssertEquals('hello', Lines[0]);
end;

procedure TStringTests.TestWordWrap_SingleLongWord;
var Lines: array[0..11] of String; N: Integer;
begin
  { A word longer than Width is force-split at Width columns. }
  WordWrap('hello', 3, Lines, N);
  AssertEquals(2, N);
  AssertEquals('hel', Lines[0]);
  AssertEquals('lo', Lines[1]);
end;

procedure TStringTests.TestJustify_TwoWords;
var R: String;
begin
  R := Justify('a b', 5);
  AssertEquals(5, UTF8Cols(R));
  AssertEquals('a   b', R);
end;

procedure TStringTests.TestJustify_OneWord;
begin
  AssertEquals('hello', Justify('hello', 5));
end;

procedure TStringTests.TestJustify_ThreeWords;
var R: String;
begin
  { "a b c" to width 10: Extra=5, Gaps=2.
    Gap 0 gets Base=2 + remainder 1 + minimum 1 = 4 spaces.
    Gap 1 gets Base=2 + 0 + 1 = 3 spaces. }
  R := Justify('a b c', 10);
  AssertEquals(10, UTF8Cols(R));
  AssertEquals('a    b   c', R);
end;

procedure TStringTests.TestJustify_AlreadyWide;
begin
  { Extra=0: only the mandatory single space between words is added. }
  AssertEquals('a b', Justify('a b', 3));
end;

{ ------------------------------------------------------------------ }
{ TBufferTests — off-screen buffer operations                        }
{ ------------------------------------------------------------------ }

type
  TBufferTests = class(TTestCase)
  protected
    procedure SetUp; override;
  published
    procedure TestBufPutCell_Stores;
    procedure TestBufPutCell_MarksDirty;
    procedure TestBufPutCell_SkipsWhenSame;
    procedure TestBufPutCell_IgnoresOOB;
    procedure TestBufPutCell_Boundary;
    procedure TestBufFill_AllCells;
    procedure TestBufDesaturate_Gray;
    procedure TestBufFlush_ClearsDirty;
    procedure TestBufCopy;
  end;

procedure TBufferTests.SetUp;
begin
  BufFlushEnabled := false;
  FillChar(Screen, SizeOf(Screen), 0);
  FillChar(Dirty, SizeOf(Dirty), 0);
end;

procedure TBufferTests.TestBufPutCell_Stores;
begin
  BufPutCell(3, 5, Red, Black, 'A');
  AssertEquals('A', Screen[3, 5].Ch);
  AssertEquals(Red, Integer(Screen[3, 5].Fg));
  AssertEquals(Black, Integer(Screen[3, 5].Bg));
end;

procedure TBufferTests.TestBufPutCell_MarksDirty;
begin
  BufPutCell(3, 5, Red, Black, 'A');
  AssertTrue(Dirty[3, 5]);
end;

procedure TBufferTests.TestBufPutCell_SkipsWhenSame;
begin
  BufPutCell(3, 5, Red, Black, 'A');
  Dirty[3, 5] := false;
  BufPutCell(3, 5, Red, Black, 'A');
  AssertFalse(Dirty[3, 5]);
end;

procedure TBufferTests.TestBufPutCell_IgnoresOOB;
begin
  BufPutCell(0, 0, 0, 0, 'X');
  BufPutCell(81, 26, 0, 0, 'X');
  AssertTrue(true);
end;

procedure TBufferTests.TestBufPutCell_Boundary;
begin
  { Col=ScreenW and Row=ScreenH are the last valid cells, not OOB. }
  BufPutCell(ScreenW, ScreenH, Green, Black, 'Z');
  AssertEquals('Z', Screen[ScreenW, ScreenH].Ch);
  AssertTrue(Dirty[ScreenW, ScreenH]);
end;

procedure TBufferTests.TestBufFill_AllCells;
begin
  BufFill(White, Black, ' ');
  AssertEquals(' ', Screen[1, 1].Ch);
  AssertEquals(White, Integer(Screen[1, 1].Fg));
  AssertEquals(' ', Screen[40, 13].Ch);
  AssertTrue(Dirty[1, 1]);
  AssertTrue(Dirty[80, 25]);
end;

procedure TBufferTests.TestBufDesaturate_Gray;
begin
  { Black bg: Fg dims, Bg stays Black }
  BufFill(Red, Black, 'X');
  BufDesaturate;
  AssertEquals(LightGray, Integer(Screen[4, 7].Fg));
  AssertEquals(Black, Integer(Screen[4, 7].Bg));
  { Non-black bg: Bg becomes LightGray; White Fg stays White }
  BufFill(White, Red, 'X');
  BufDesaturate;
  AssertEquals(White, Integer(Screen[4, 7].Fg));
  AssertEquals(LightGray, Integer(Screen[4, 7].Bg));
  AssertTrue(Dirty[4, 7]);
end;

procedure TBufferTests.TestBufFlush_ClearsDirty;
var Col, Row: Integer; AnyDirty: Boolean;
begin
  BufFill(White, Black, ' ');
  BufFlush;
  AnyDirty := false;
  for Col := 1 to ScreenW do
    for Row := 1 to ScreenH do
      if Dirty[Col, Row] then AnyDirty := true;
  AssertFalse(AnyDirty);
end;

procedure TBufferTests.TestBufCopy;
var Dst: TScreenBuffer;
begin
  BufFill(Red, Blue, 'Q');
  BufCopy(Dst);
  AssertEquals('Q', Dst[1, 1].Ch);
  AssertEquals(Red, Integer(Dst[1, 1].Fg));
  AssertEquals(Blue, Integer(Dst[40, 12].Bg));
  AssertEquals('Q', Dst[ScreenW, ScreenH].Ch);
end;

{ ------------------------------------------------------------------ }
{ TLevelTests — Blocked map and level initialisation                 }
{ ------------------------------------------------------------------ }

type
  TLevelTests = class(TTestCase)
  protected
    procedure SetUp; override;
  published
    procedure TestInitBorder_Corners;
    procedure TestInitBorder_Interior;
    procedure TestInitLevel1_NoWalls;
    procedure TestInitLevel2_Wall;
    procedure TestInitLevel3_CentreGap;
    procedure TestInitLevel4_EnemyStartNotBlocked;
    procedure TestInitLevel4_WallBounds;
    procedure TestInitLevel5_Row10Clear;
    procedure TestInitLevel9_DividerWalls;
    procedure TestInitLevel9_CentreCorridor;
    procedure TestInitLevel1to9_StartPos;
    procedure TestInitLevel1to9_EnemyStartNotBlocked;
  end;

procedure TLevelTests.SetUp;
begin
  BufFlushEnabled := false;
  FillChar(Blocked, SizeOf(Blocked), 0);
  FillChar(Screen, SizeOf(Screen), 0);
  FillChar(Dirty, SizeOf(Dirty), 0);
end;

procedure TLevelTests.TestInitBorder_Corners;
begin
  InitBorder;
  AssertTrue(Blocked[1, 1]);
  AssertTrue(Blocked[80, 1]);
  AssertTrue(Blocked[1, 20]);
  AssertTrue(Blocked[80, 20]);
end;

procedure TLevelTests.TestInitBorder_Interior;
begin
  InitBorder;
  AssertFalse(Blocked[40, 10]);
end;

procedure TLevelTests.TestInitLevel1_NoWalls;
var I, J: Integer;
begin
  InitLevel1;
  AssertEquals(40, StartX);
  AssertEquals(10, StartY);
  for I := 2 to FieldW - 1 do
    for J := 2 to FieldH - 1 do
      AssertFalse('blocked at ' + IntToStr(I) + ',' + IntToStr(J), Blocked[I, J]);
end;

procedure TLevelTests.TestInitLevel2_Wall;
begin
  InitBorder;
  InitLevel2;
  AssertTrue(Blocked[18, 10]);
  AssertTrue(Blocked[62, 10]);
  AssertFalse(Blocked[17, 10]);
  AssertFalse(Blocked[63, 10]);
end;

procedure TLevelTests.TestInitLevel3_CentreGap;
begin
  InitBorder;
  InitLevel3;
  { Horizontal bar at row 10 has a 3-cell gap explicitly cleared. }
  AssertFalse('gap at 39,10', Blocked[39, 10]);
  AssertFalse('gap at 40,10', Blocked[40, 10]);
  AssertFalse('gap at 41,10', Blocked[41, 10]);
  { Cells outside the gap are blocked. }
  AssertTrue('wall at 38,10', Blocked[38, 10]);
  AssertTrue('wall at 42,10', Blocked[42, 10]);
end;

procedure TLevelTests.TestInitLevel4_EnemyStartNotBlocked;
begin
  InitBorder;
  InitLevel4;
  { Regression: wall was formerly columns 5-75, which blocked the enemy
    start position at (5, 10). The wall now starts at column 6. }
  AssertFalse('enemy start col 5 must be open', Blocked[5, 10]);
end;

procedure TLevelTests.TestInitLevel4_WallBounds;
begin
  InitBorder;
  InitLevel4;
  AssertTrue('wall starts at col 6', Blocked[6, 10]);
  AssertTrue('wall ends at col 74', Blocked[74, 10]);
  AssertFalse('col 5 open', Blocked[5, 10]);
  AssertFalse('col 75 open', Blocked[75, 10]);
  { Centre gap cleared. }
  AssertFalse('gap at 39,10', Blocked[39, 10]);
  AssertFalse('gap at 40,10', Blocked[40, 10]);
  AssertFalse('gap at 41,10', Blocked[41, 10]);
end;

procedure TLevelTests.TestInitLevel5_Row10Clear;
begin
  InitBorder;
  InitLevel5;
  { Vertical walls at cols 20 and 60 span rows 5-15 (including row 10),
    but InitLevel5 explicitly clears the entire row 10 from col 20 to 60. }
  AssertFalse('col 20 row 10 must be clear', Blocked[20, 10]);
  AssertFalse('col 60 row 10 must be clear', Blocked[60, 10]);
  AssertFalse('col 40 row 10 must be clear', Blocked[40, 10]);
  { Row 10 outside the cleared range stays unblocked (never set). }
  AssertFalse('col 5 row 10', Blocked[5, 10]);
end;

procedure TLevelTests.TestInitLevel9_DividerWalls;
begin
  InitBorder;
  InitLevel9;
  { Double centre divider at cols 39 and 41, rows 5-15. Row 10 is in that range. }
  AssertTrue('divider col 39 row 10', Blocked[39, 10]);
  AssertTrue('divider col 41 row 10', Blocked[41, 10]);
end;

procedure TLevelTests.TestInitLevel9_CentreCorridor;
begin
  InitBorder;
  InitLevel9;
  { Col 40 is the open corridor between the two divider walls. }
  AssertFalse('centre corridor at col 40', Blocked[40, 10]);
  { Player starts at (40, 10) — must not be blocked. }
  AssertFalse('player start not blocked', Blocked[StartX, StartY]);
end;

procedure TLevelTests.TestInitLevel1to9_StartPos;
var L: Integer;
begin
  for L := 1 to 9 do
    begin
      FillChar(Blocked, SizeOf(Blocked), 0);
      InitLevel(L);
      AssertTrue('StartX in range (level ' + IntToStr(L) + ')',
                 (StartX >= 2) and (StartX <= FieldW - 1));
      AssertTrue('StartY in range (level ' + IntToStr(L) + ')',
                 (StartY >= 2) and (StartY <= FieldH - 1));
    end;
end;

procedure TLevelTests.TestInitLevel1to9_EnemyStartNotBlocked;
var L: Integer;
begin
  { Regression for level 4: enemy start (5, 10) was inside the wall when
    the wall ran from col 5 to 75. Verify all levels keep the enemy start open. }
  for L := 1 to 9 do
    begin
      FillChar(Blocked, SizeOf(Blocked), 0);
      InitBorder;
      InitLevel(L);
      AssertFalse('enemy start blocked at level ' + IntToStr(L),
                  Blocked[StartEX, StartEY]);
    end;
end;

{ ------------------------------------------------------------------ }
{ TDrawTests — Draw, DrawHLine, DrawParagraph, DrawItemName          }
{ ------------------------------------------------------------------ }

type
  TDrawTests = class(TTestCase)
  protected
    procedure SetUp; override;
  published
    procedure TestDraw_ASCII;
    procedure TestDraw_ThreeByte;
    procedure TestDrawHLine_Range;
    procedure TestDrawParagraph_Count;
    procedure TestDrawParagraph_Wraps;
    procedure TestGetItemName_AllNonEmpty;
    procedure TestDrawItemName_ZoneWidth;
    procedure TestDrawItemName_RopeCentred;
    procedure TestDrawItemName_CrownOnLevel9;
  end;

procedure TDrawTests.SetUp;
begin
  BufFlushEnabled := false;
  FillChar(Screen, SizeOf(Screen), 0);
  FillChar(Dirty, SizeOf(Dirty), 0);
end;

procedure TDrawTests.TestDraw_ASCII;
begin
  Draw(5, 3, White, Black, 'Hi');
  AssertEquals('H', Screen[5, 3].Ch);
  AssertEquals('i', Screen[6, 3].Ch);
end;

procedure TDrawTests.TestDraw_ThreeByte;
begin
  Draw(1, 1, Red, Black, '←');
  AssertEquals('←', Screen[1, 1].Ch);
end;

procedure TDrawTests.TestDrawHLine_Range;
var C: Integer;
begin
  DrawHLine(2, 6, 4, White, Black, '─');
  for C := 2 to 6 do
    AssertEquals('col ' + IntToStr(C), '─', Screen[C, 4].Ch);
  AssertEquals('', Screen[1, 4].Ch);
end;

procedure TDrawTests.TestDrawParagraph_Count;
begin
  AssertEquals(1, DrawParagraph('word', 1, 1, 72, White, Black));
end;

procedure TDrawTests.TestDrawParagraph_Wraps;
var Lines: Integer;
begin
  Lines := DrawParagraph(
    'The quick brown fox jumps over the lazy dog. ' +
    'The quick brown fox jumps over the lazy dog.',
    1, 1, 20, White, Black);
  AssertTrue('wraps to >1 line', Lines > 1);
end;

procedure TDrawTests.TestGetItemName_AllNonEmpty;
var I: Integer;
begin
  { Every valid item index must return a non-empty name.
    A missing case in GetItemName would return ''. }
  for I := 1 to 10 do
    AssertTrue('item ' + IntToStr(I) + ' has name', Length(GetItemName(I)) > 0);
end;

procedure TDrawTests.TestDrawItemName_ZoneWidth;
var Col: Integer;
begin
  { DrawItemName pads to exactly ZoneW=55 cols and draws at row FieldH=20. }
  ItemNo := 1;
  Level  := 1;
  DrawItemName;
  for Col := 12 to 66 do
    AssertTrue('col ' + IntToStr(Col) + ' filled',
               Length(Screen[Col, 20].Ch) > 0);
  { Cell just outside the zone must be untouched (still zero-length string). }
  AssertEquals(0, Length(Screen[11, 20].Ch));
  AssertEquals(0, Length(Screen[67, 20].Ch));
end;

procedure TDrawTests.TestDrawItemName_RopeCentred;
begin
  { "Rope" (4 chars) in ZoneW=55: Pad = (55-4) div 2 = 25.
    'R' appears at ZoneStart(12) + Pad(25) = col 37. }
  ItemNo := 1;
  Level  := 1;
  DrawItemName;
  AssertEquals('R', Screen[37, 20].Ch);
end;

procedure TDrawTests.TestDrawItemName_CrownOnLevel9;
begin
  { When ItemNo=9 and Level=9 the Crown (item 10) is shown instead.
    "Crown" (5 chars), Pad = (55-5) div 2 = 25, so 'C' is at col 37. }
  ItemNo := 9;
  Level  := 9;
  DrawItemName;
  AssertEquals('C', Screen[37, 20].Ch);
  AssertEquals('r', Screen[38, 20].Ch);
end;

{ ------------------------------------------------------------------ }
{ TGameLogicTests — AwardPoints, player/item collision, GetItemName  }
{ ------------------------------------------------------------------ }

type
  TGameLogicTests = class(TTestCase)
  protected
    procedure SetUp; override;
  published
    procedure TestAwardPoints_Item1;
    procedure TestAwardPoints_Item5;
    procedure TestAwardPoints_Item9;
    procedure TestAwardPoints_Accumulates;
    procedure TestIsPlayerCaught_True;
    procedure TestIsPlayerCaught_False;
    procedure TestIsPlayerCaught_YMismatch;
    procedure TestIsItemPickedUp_True;
    procedure TestIsItemPickedUp_False;
    procedure TestIsItemPickedUp_YMismatch;
    procedure TestGetItemName_Rope;
    procedure TestGetItemName_Crown;
  end;

procedure TGameLogicTests.SetUp;
begin
  BufFlushEnabled := false;
  FillChar(Screen, SizeOf(Screen), 0);
  FillChar(Dirty, SizeOf(Dirty), 0);
  Score := 0;
  X := 5;  Y := 5;
  EX := 10; EY := 10;
  ItemX := 20; ItemY := 15;
end;

procedure TGameLogicTests.TestAwardPoints_Item1;
begin
  ItemNo := 1;
  AwardPoints;
  AssertEquals(100, Score);
end;

procedure TGameLogicTests.TestAwardPoints_Item5;
begin
  ItemNo := 5;
  AwardPoints;
  AssertEquals(500, Score);
end;

procedure TGameLogicTests.TestAwardPoints_Item9;
begin
  { Item 9 must score 900. The old formula (ItemNo-1)*100 would have
    given 800 — this verifies the corrected formula ItemNo*100. }
  ItemNo := 9;
  AwardPoints;
  AssertEquals(900, Score);
end;

procedure TGameLogicTests.TestAwardPoints_Accumulates;
begin
  ItemNo := 3;
  AwardPoints;
  ItemNo := 7;
  AwardPoints;
  AssertEquals(300 + 700, Score);
end;

procedure TGameLogicTests.TestIsPlayerCaught_True;
begin
  EX := X; EY := Y;
  AssertTrue(IsPlayerCaught);
end;

procedure TGameLogicTests.TestIsPlayerCaught_False;
begin
  EX := X + 1;
  AssertFalse(IsPlayerCaught);
end;

procedure TGameLogicTests.TestIsPlayerCaught_YMismatch;
begin
  { X matches but Y differs — not caught. }
  EX := X;
  EY := Y + 1;
  AssertFalse(IsPlayerCaught);
end;

procedure TGameLogicTests.TestIsItemPickedUp_True;
begin
  ItemX := X; ItemY := Y;
  AssertTrue(IsItemPickedUp);
end;

procedure TGameLogicTests.TestIsItemPickedUp_False;
begin
  ItemX := X + 1;
  AssertFalse(IsItemPickedUp);
end;

procedure TGameLogicTests.TestIsItemPickedUp_YMismatch;
begin
  { X matches but Y differs — not picked up. }
  ItemX := X;
  ItemY := Y + 1;
  AssertFalse(IsItemPickedUp);
end;

procedure TGameLogicTests.TestGetItemName_Rope;
begin
  AssertEquals('Rope', GetItemName(1));
end;

procedure TGameLogicTests.TestGetItemName_Crown;
begin
  AssertEquals('Crown', GetItemName(10));
end;

{ ------------------------------------------------------------------ }
{ TEnemyMoveTests — greedy AI, tick skipping, fallback, stuck        }
{ ------------------------------------------------------------------ }

type
  TEnemyMoveTests = class(TTestCase)
  protected
    procedure SetUp; override;
  published
    procedure TestEnemyMove_SkipsOnOddTick;
    procedure TestEnemyMove_HorizontalPreferred;
    procedure TestEnemyMove_VerticalPreferred;
    procedure TestEnemyMove_EqualDeltaPrefersVertical;
    procedure TestEnemyMove_FallbackToVertical;
    procedure TestEnemyMove_StuckWhenBothBlocked;
    procedure TestEnemyMove_ClearsOldPosition;
  end;

procedure TEnemyMoveTests.SetUp;
begin
  BufFlushEnabled := false;
  FillChar(Screen, SizeOf(Screen), 0);
  FillChar(Dirty, SizeOf(Dirty), 0);
  FillChar(Blocked, SizeOf(Blocked), 0);
  InitBorder;
  EnemyTick := 0;
  X := 40; Y := 10;
  EX := 20; EY := 10;
end;

procedure TEnemyMoveTests.TestEnemyMove_SkipsOnOddTick;
begin
  { EnemyTick <> 0 — the move block is skipped entirely. }
  EnemyTick := 1;
  X := 25; Y := 10;
  EX := 20; EY := 10;
  EnemyMove;
  AssertEquals(20, EX);
  AssertEquals(10, EY);
end;

procedure TEnemyMoveTests.TestEnemyMove_HorizontalPreferred;
begin
  { |DX|=20 > |DY|=0 → horizontal preferred; enemy moves right toward player. }
  X := 40; Y := 10;
  EX := 20; EY := 10;
  EnemyMove;
  AssertEquals(21, EX);
  AssertEquals(10, EY);
end;

procedure TEnemyMoveTests.TestEnemyMove_VerticalPreferred;
begin
  { |DX|=0 < |DY|=5 → vertical preferred; enemy moves down toward player. }
  X := 20; Y := 15;
  EX := 20; EY := 10;
  EnemyMove;
  AssertEquals(20, EX);
  AssertEquals(11, EY);
end;

procedure TEnemyMoveTests.TestEnemyMove_EqualDeltaPrefersVertical;
begin
  { |DX|=|DY|=5 → TryHoriz = (5 > 5) = false → vertical tried first.
    DY>0 so enemy moves down. }
  X := 25; Y := 15;
  EX := 20; EY := 10;
  EnemyMove;
  AssertEquals(20, EX);
  AssertEquals(11, EY);
end;

procedure TEnemyMoveTests.TestEnemyMove_FallbackToVertical;
begin
  { |DX|=20 > |DY|=5 → horizontal preferred, but right cell blocked.
    Falls back to vertical: DY<0 so enemy moves up. }
  X := 40; Y := 5;
  EX := 20; EY := 10;
  Blocked[21, 10] := true;
  EnemyMove;
  AssertEquals(20, EX);    { did not move horizontally }
  AssertEquals(9, EY);     { moved up (toward player) }
end;

procedure TEnemyMoveTests.TestEnemyMove_StuckWhenBothBlocked;
begin
  { Both horizontal and vertical escape routes blocked — enemy stays put. }
  X := 40; Y := 5;
  EX := 20; EY := 10;
  Blocked[21, 10] := true;   { right blocked }
  Blocked[20, 9]  := true;   { up blocked }
  EnemyMove;
  AssertEquals(20, EX);
  AssertEquals(10, EY);
end;

procedure TEnemyMoveTests.TestEnemyMove_ClearsOldPosition;
begin
  { After moving, EnemyMove draws ' ' at the old position. }
  X := 40; Y := 10;
  EX := 20; EY := 10;
  EnemyMove;
  AssertEquals(' ', Screen[20, 10].Ch);   { old position cleared }
  AssertEquals('☻', Screen[21, 10].Ch);  { new position drawn }
end;

{ ------------------------------------------------------------------ }
{ TMovementTests — MoveRight/Left/Up/Down and speed helpers          }
{ ------------------------------------------------------------------ }

type
  TMovementTests = class(TTestCase)
  protected
    procedure SetUp; override;
  published
    procedure TestMoveRight_MovesPlayer;
    procedure TestMoveRight_Blocked;
    procedure TestMoveLeft_MovesPlayer;
    procedure TestMoveUp_MovesPlayer;
    procedure TestMoveDown_MovesPlayer;
    procedure TestSpeedUp_DecreasesDelay;
    procedure TestSpeedUp_DoesNotGoBelowZero;
    procedure TestSlowDown_IncreasesDelay;
  end;

procedure TMovementTests.SetUp;
begin
  BufFlushEnabled := false;
  FillChar(Screen, SizeOf(Screen), 0);
  FillChar(Dirty, SizeOf(Dirty), 0);
  FillChar(Blocked, SizeOf(Blocked), 0);
  InitBorder;
  X := 40; Y := 10;
  BlockX := 1; BlockY := 1;
  MoveDelay := 50;
end;

procedure TMovementTests.TestMoveRight_MovesPlayer;
begin
  MoveRight(X, Y);
  AssertEquals(41, X);
  AssertEquals('☺', Screen[41, 10].Ch);
  AssertEquals(' ', Screen[40, 10].Ch);
end;

procedure TMovementTests.TestMoveRight_Blocked;
begin
  Blocked[41, 10] := true;
  MoveRight(X, Y);
  AssertEquals(40, X);
end;

procedure TMovementTests.TestMoveLeft_MovesPlayer;
begin
  MoveLeft(X, Y);
  AssertEquals(39, X);
  AssertEquals('☺', Screen[39, 10].Ch);
end;

procedure TMovementTests.TestMoveUp_MovesPlayer;
begin
  MoveUp(X, Y);
  AssertEquals(9, Y);
  AssertEquals('☺', Screen[40, 9].Ch);
end;

procedure TMovementTests.TestMoveDown_MovesPlayer;
begin
  MoveDown(X, Y);
  AssertEquals(11, Y);
  AssertEquals('☺', Screen[40, 11].Ch);
end;

procedure TMovementTests.TestSpeedUp_DecreasesDelay;
begin
  MoveDelay := 50;
  SpeedUp;
  AssertEquals(49, MoveDelay);
end;

procedure TMovementTests.TestSpeedUp_DoesNotGoBelowZero;
begin
  MoveDelay := 0;
  SpeedUp;
  AssertEquals(0, MoveDelay);
end;

procedure TMovementTests.TestSlowDown_IncreasesDelay;
begin
  MoveDelay := 50;
  SlowDown;
  AssertEquals(51, MoveDelay);
end;

{ ------------------------------------------------------------------ }
{ TPlaceBlockTests — block placement, cost, and budget behaviour     }
{ ------------------------------------------------------------------ }

type
  TPlaceBlockTests = class(TTestCase)
  protected
    procedure SetUp; override;
  published
    procedure TestPlaceBlock_PlacesBlock;
    procedure TestPlaceBlock_CostsScore;
    procedure TestPlaceBlock_CostsBudget;
    procedure TestPlaceBlock_TracksBXBY;
    procedure TestPlaceBlock_NoBudget_DisablesLaying;
    procedure TestPlaceBlock_NoScore_DisablesLaying;
    procedure TestPlaceBlock_AlreadyBlocked_NoEffect;
  end;

procedure TPlaceBlockTests.SetUp;
begin
  BufFlushEnabled := false;
  FillChar(Screen, SizeOf(Screen), 0);
  FillChar(Dirty, SizeOf(Dirty), 0);
  FillChar(Blocked, SizeOf(Blocked), 0);
  X := 10; Y := 5;
  Score := 1000;
  BlocksRemaining := 100;
  Laying := true;
  BlockX := 1; BlockY := 1;
end;

procedure TPlaceBlockTests.TestPlaceBlock_PlacesBlock;
begin
  PlaceBlock;
  AssertTrue(Blocked[10, 5]);
  AssertEquals('█', Screen[10, 5].Ch);
end;

procedure TPlaceBlockTests.TestPlaceBlock_CostsScore;
begin
  PlaceBlock;
  AssertEquals(980, Score);
end;

procedure TPlaceBlockTests.TestPlaceBlock_CostsBudget;
begin
  PlaceBlock;
  AssertEquals(99, BlocksRemaining);
end;

procedure TPlaceBlockTests.TestPlaceBlock_TracksBXBY;
begin
  PlaceBlock;
  AssertEquals(10, BlockX);
  AssertEquals(5, BlockY);
end;

procedure TPlaceBlockTests.TestPlaceBlock_NoBudget_DisablesLaying;
begin
  BlocksRemaining := 0;
  PlaceBlock;
  AssertFalse(Laying);
  AssertFalse(Blocked[10, 5]);
end;

procedure TPlaceBlockTests.TestPlaceBlock_NoScore_DisablesLaying;
begin
  Score := 10;  { < 20 }
  PlaceBlock;
  AssertFalse(Laying);
  AssertFalse(Blocked[10, 5]);
end;

procedure TPlaceBlockTests.TestPlaceBlock_AlreadyBlocked_NoEffect;
var ScoreBefore: LongInt;
begin
  Blocked[10, 5] := true;
  ScoreBefore := Score;
  PlaceBlock;
  { Score and budget must be unchanged — nothing was placed. }
  AssertEquals(ScoreBefore, Score);
  AssertEquals(100, BlocksRemaining);
  { Laying must not have been disabled (condition requires budget=0 or score<20). }
  AssertTrue(Laying);
end;

{ ------------------------------------------------------------------ }
{ TPlayerStateTests — PlayerCaught penalty, clamp, resets           }
{ ------------------------------------------------------------------ }

type
  TPlayerStateTests = class(TTestCase)
  protected
    procedure SetUp; override;
  published
    procedure TestPlayerCaught_Penalty;
    procedure TestPlayerCaught_ClampAtZero;
    procedure TestPlayerCaught_ResetsItemNo;
    procedure TestPlayerCaught_DecreasesLives;
  end;

procedure TPlayerStateTests.SetUp;
begin
  BufFlushEnabled := false;
  FillChar(Screen, SizeOf(Screen), 0);
  FillChar(Dirty, SizeOf(Dirty), 0);
  FillChar(Blocked, SizeOf(Blocked), 0);
  InitBorder;
  Level := 1;
  Score := 5000;
  Lives := 5;
  ItemNo := 3;
  BlockX := 1; BlockY := 1;
  X := 40; Y := 10;
  EX := 5; EY := 10;
  ItemX := 20; ItemY := 8;
end;

procedure TPlayerStateTests.TestPlayerCaught_Penalty;
begin
  { Score - ItemNo * 1000 = 5000 - 3000 = 2000. }
  Score := 5000;
  ItemNo := 3;
  PlayerCaught;
  AssertEquals(2000, Score);
end;

procedure TPlayerStateTests.TestPlayerCaught_ClampAtZero;
begin
  { Penalty exceeds score: result must be clamped to 0, not negative. }
  Score := 100;
  ItemNo := 5;
  PlayerCaught;
  AssertEquals(0, Score);
end;

procedure TPlayerStateTests.TestPlayerCaught_ResetsItemNo;
begin
  ItemNo := 7;
  PlayerCaught;
  AssertEquals(1, ItemNo);
end;

procedure TPlayerStateTests.TestPlayerCaught_DecreasesLives;
begin
  Lives := 5;
  PlayerCaught;
  AssertEquals(4, Lives);
end;

{ ------------------------------------------------------------------ }
{ TDialogTests — Dialog rendering, return value, and Redraw         }
{ ------------------------------------------------------------------ }
{
  Dialog('Hello', '') geometry:
    TW=5, W=max(9,4,27)=27, X1=(80-27)/2+1=27, X2=53
    BoxH=3 (no prompt), Y1=(20-3)/2+1=9
    Title pad=(27-2-5)/2=10 → Draw(28,10,...) → 'H' at col 38
  Dialog('Test','Yes') geometry:
    TW=4, PW=3, W=27, BoxH=4, Y1=9
    Prompt pad=(27-3)/2=12 → Draw(27,12,...) → 'Y' at col 39
}

type
  TDialogTests = class(TTestCase)
  protected
    procedure SetUp;    override;
    procedure TearDown; override;
  published
    procedure TestDialog_ReturnsKey;
    procedure TestDialog_RedrawsAfter;
    procedure TestDialog_TitleCaptured;
    procedure TestDialog_PromptCaptured;
    procedure TestDialog_MinWidth27;
    procedure TestDialog_NoPromptNoTextBelow;
    procedure TestDialog_WithPromptTextBelow;
    procedure TestGameOver_RedrawsAfter;
  end;

procedure TDialogTests.SetUp;
begin
  KeyTestSetUp;
end;

procedure TDialogTests.TearDown;
begin
  KeyTestTearDown;
end;

procedure TDialogTests.TestDialog_ReturnsKey;
begin
  EnqueueKey(Ord('x'));
  AssertEquals(Ord('x'), Dialog('Title', ''));
end;

procedure TDialogTests.TestDialog_RedrawsAfter;
begin
  { Dialog calls Redraw after WaitKey; DrawBorder draws '█' at (1,1). }
  EnqueueKey(Ord('n'));
  Dialog('Test', '');
  AssertEquals('█', Screen[1, 1].Ch);
end;

procedure TDialogTests.TestDialog_TitleCaptured;
begin
  { 'Hello' (5 chars), W=27, X1=27, Y1=9, Draw at (28,10).
    10 leading spaces → 'H' lands at col 38. }
  KeyProviderFunc := @CapturingDequeueKey;
  EnqueueKey(Ord('x'));
  Dialog('Hello', '');
  AssertEquals('H', KeyCapture[38, 10].Ch);
end;

procedure TDialogTests.TestDialog_PromptCaptured;
begin
  { 'Test'(4)+'Yes'(3), W=27, BoxH=4, Y1=9.
    Prompt pad=(27-3)/2=12 → Draw(27,12,...) → 'Y' at col 27+12=39. }
  KeyProviderFunc := @CapturingDequeueKey;
  EnqueueKey(Ord('x'));
  Dialog('Test', 'Yes');
  AssertEquals('Y', KeyCapture[39, 12].Ch);
end;

procedure TDialogTests.TestDialog_MinWidth27;
begin
  { Short title 'Hi' (2 chars): W enforced to 27. X1=27, X2=53.
    Top border at row Y1=9 must span cols 27..53. }
  KeyProviderFunc := @CapturingDequeueKey;
  EnqueueKey(Ord('x'));
  Dialog('Hi', '');
  AssertEquals('█', KeyCapture[27, 9].Ch);   { left edge of top border }
  AssertEquals('█', KeyCapture[53, 9].Ch);   { right edge }
end;

procedure TDialogTests.TestDialog_NoPromptNoTextBelow;
begin
  { BoxH=3: bottom border at Y1+2=11; row Y1+3=12 must be untouched. }
  KeyProviderFunc := @CapturingDequeueKey;
  EnqueueKey(Ord('x'));
  Dialog('Hi', '');
  AssertEquals('█', KeyCapture[27, 11].Ch);   { bottom border present }
  AssertEquals('',  KeyCapture[27, 12].Ch);   { nothing below the box }
end;

procedure TDialogTests.TestDialog_WithPromptTextBelow;
begin
  { 'Prompt' (6 chars), W=27, pad=(27-6)/2=10 → 'P' at X1+10=37, row 12. }
  KeyProviderFunc := @CapturingDequeueKey;
  EnqueueKey(Ord('x'));
  Dialog('X', 'Prompt');
  AssertEquals('P', KeyCapture[37, 12].Ch);
end;

procedure TDialogTests.TestGameOver_RedrawsAfter;
begin
  { GameOver → Dialog → Redraw; border cell (1,1) should be '█'. }
  EnqueueKey(Ord('n'));
  GameOver;
  AssertEquals('█', Screen[1, 1].Ch);
end;

{ ------------------------------------------------------------------ }
{ TScreenOverlayTests — ShowHelp and ShowStory buffer content        }
{ ------------------------------------------------------------------ }
{
  Center('UGLI HELP')  [9 chars]: pad=(80-9)/2=35 → 'U' at col 36, row 2.
  Center(sPressKey)    [25 chars]: pad=(80-25)/2=27 → 'P' at col 28, row 24.
  Center('The Story of UGLI') [18 chars]: pad=(80-18)/2=31 → 'T' at col 32.
  ShowStory Col=(80-72)/2+1=5; first word 'A' drawn at (5,4).
  Neither ShowHelp nor ShowStory calls Redraw internally — Screen still
  has their content when they return to the test.
}

type
  TScreenOverlayTests = class(TTestCase)
  protected
    procedure SetUp;    override;
    procedure TearDown; override;
  published
    procedure TestShowHelp_RestoresXY;
    procedure TestShowHelp_TitleInBuffer;
    procedure TestShowHelp_KeyHintInBuffer;
    procedure TestShowStory_TitleInBuffer;
    procedure TestShowStory_DrawsParagraph;
  end;

procedure TScreenOverlayTests.SetUp;
begin
  KeyTestSetUp;
end;

procedure TScreenOverlayTests.TearDown;
begin
  KeyTestTearDown;
end;

procedure TScreenOverlayTests.TestShowHelp_RestoresXY;
var OldX, OldY: Integer;
begin
  OldX := X; OldY := Y;
  EnqueueKey(Ord('x'));
  ShowHelp;
  AssertEquals(OldX, X);
  AssertEquals(OldY, Y);
end;

procedure TScreenOverlayTests.TestShowHelp_TitleInBuffer;
begin
  { Center('UGLI HELP'): 35 spaces + 'UGLI HELP'.  Draw(1,2,...) → 'U' at col 36. }
  EnqueueKey(Ord('x'));
  ShowHelp;
  AssertEquals('U', Screen[36, 2].Ch);
end;

procedure TScreenOverlayTests.TestShowHelp_KeyHintInBuffer;
begin
  { Center(sPressKey) [25 chars]: 27 spaces → 'P' at col 28, row 24. }
  EnqueueKey(Ord('x'));
  ShowHelp;
  AssertEquals('P', Screen[28, 24].Ch);
end;

procedure TScreenOverlayTests.TestShowStory_TitleInBuffer;
begin
  { Center('The Story of UGLI') [18 chars]: 31 spaces → 'T' at col 32, row 2. }
  EnqueueKey(Ord('x'));
  ShowStory;
  AssertEquals('T', Screen[32, 2].Ch);
end;

procedure TScreenOverlayTests.TestShowStory_DrawsParagraph;
begin
  { Story paragraph at Col=5, Row=4.  First visible char is 'A' (from 'A king...'). }
  EnqueueKey(Ord('x'));
  ShowStory;
  AssertEquals('A', Screen[5, 4].Ch);
end;

{ ------------------------------------------------------------------ }
{ TGameFlowTests — LevelTransition, LevelComplete, AskPlayAgain,    }
{                  RemoveBlocks, KeyToDir                            }
{ ------------------------------------------------------------------ }

type
  TGameFlowTests = class(TTestCase)
  protected
    procedure SetUp;    override;
    procedure TearDown; override;
  published
    procedure TestKeyToDir_Right;
    procedure TestKeyToDir_Left;
    procedure TestKeyToDir_Up;
    procedure TestKeyToDir_Down;
    procedure TestLevelTransition_SetsDirectionOnRight;
    procedure TestLevelTransition_SetsDirectionOnLeft;
    procedure TestLevelTransition_KeepsDirectionOnOtherKey;
    procedure TestLevelComplete_IncreasesLives;
    procedure TestLevelComplete_ResetsItemNo;
    procedure TestLevelComplete_ResetsBlockXY;
    procedure TestAskPlayAgain_YesReturnsTrue;
    procedure TestAskPlayAgain_NoReturnsFalse;
    procedure TestRemoveBlocks_Yes_ClearsInterior;
    procedure TestRemoveBlocks_No_KeepsBlocked;
  end;

procedure TGameFlowTests.SetUp;
begin
  KeyTestSetUp;
end;

procedure TGameFlowTests.TearDown;
begin
  KeyTestTearDown;
end;

procedure TGameFlowTests.TestKeyToDir_Right;
begin
  AssertEquals(Integer(DirRight), Integer(KeyToDir(KeyRight)));
end;

procedure TGameFlowTests.TestKeyToDir_Left;
begin
  AssertEquals(Integer(DirLeft), Integer(KeyToDir(KeyLeft)));
end;

procedure TGameFlowTests.TestKeyToDir_Up;
begin
  AssertEquals(Integer(DirUp), Integer(KeyToDir(KeyUp)));
end;

procedure TGameFlowTests.TestKeyToDir_Down;
begin
  AssertEquals(Integer(DirDown), Integer(KeyToDir(KeyDown)));
end;

procedure TGameFlowTests.TestLevelTransition_SetsDirectionOnRight;
begin
  EnqueueKey(KeyRight);
  LevelTransition;
  AssertEquals(Integer(DirRight), Integer(Direction));
end;

procedure TGameFlowTests.TestLevelTransition_SetsDirectionOnLeft;
begin
  EnqueueKey(KeyLeft);
  LevelTransition;
  AssertEquals(Integer(DirLeft), Integer(Direction));
end;

procedure TGameFlowTests.TestLevelTransition_KeepsDirectionOnOtherKey;
begin
  Direction := DirDown;
  EnqueueKey(Ord('x'));  { not an arrow key }
  LevelTransition;
  AssertEquals(Integer(DirDown), Integer(Direction));
end;

procedure TGameFlowTests.TestLevelComplete_IncreasesLives;
begin
  Lives := 3;
  EnqueueKey(Ord('x'));  { consumed by LevelTransition's Dialog }
  LevelComplete;
  AssertEquals(4, Lives);
end;

procedure TGameFlowTests.TestLevelComplete_ResetsItemNo;
begin
  ItemNo := 5;
  EnqueueKey(Ord('x'));
  LevelComplete;
  AssertEquals(1, ItemNo);
end;

procedure TGameFlowTests.TestLevelComplete_ResetsBlockXY;
begin
  BlockX := 30; BlockY := 15;
  EnqueueKey(Ord('x'));
  LevelComplete;
  AssertEquals(1, BlockX);
  AssertEquals(1, BlockY);
end;

procedure TGameFlowTests.TestAskPlayAgain_YesReturnsTrue;
begin
  EnqueueKey(Ord('Y'));
  AssertTrue(AskPlayAgain);
end;

procedure TGameFlowTests.TestAskPlayAgain_NoReturnsFalse;
begin
  EnqueueKey(Ord('N'));
  AssertFalse(AskPlayAgain);
end;

procedure TGameFlowTests.TestRemoveBlocks_Yes_ClearsInterior;
begin
  { Place a "user" block at an interior cell. }
  Blocked[20, 10] := true;
  EnqueueKey(Ord('Y'));
  RemoveBlocks;
  { Level 1 has no interior walls, so RemoveBlocks + InitLevel(1) must clear it. }
  AssertFalse(Blocked[20, 10]);
end;

procedure TGameFlowTests.TestRemoveBlocks_No_KeepsBlocked;
begin
  Blocked[20, 10] := true;
  EnqueueKey(Ord('N'));
  RemoveBlocks;
  AssertTrue(Blocked[20, 10]);
end;

{ ------------------------------------------------------------------ }
{ TBufFlushOutputTests — verify each flush variant writes correct    }
{ bytes; TTY / RawTTYFd are redirected to a temp file.              }
{ ------------------------------------------------------------------ }

const TmpFlushPath = '/tmp/ugli_flush_test.tmp';

function ReadTmpFlushFile: AnsiString;
var F: File of Byte; B: Byte;
begin
  Result := '';
  Assign(F, TmpFlushPath);
  Reset(F);
  while not Eof(F) do
    begin Read(F, B); Result := Result + Chr(B); end;
  Close(F);
end;

function CaptureTextFlush(Proc: TFlushProc): AnsiString;
begin
  Assign(TTY, TmpFlushPath); ReWrite(TTY);
  BufFlushEnabled := true;
  Proc();
  BufFlushEnabled := false;
  Close(TTY);
  Result := ReadTmpFlushFile;
end;

function CaptureRawFlush(Proc: TFlushProc): AnsiString;
begin
  RawTTYFd := fpOpen(TmpFlushPath, O_WRONLY or O_CREAT or O_TRUNC, 438);
  BufFlushEnabled := true;
  Proc();
  BufFlushEnabled := false;
  fpClose(RawTTYFd);
  RawTTYFd := -1;
  Result := ReadTmpFlushFile;
end;

type
  TBufFlushOutputTests = class(TTestCase)
  protected
    procedure SetUp; override;
    procedure TearDown; override;
    procedure ResetScene;
  published
    procedure TestBufFlush_HasLineWrapBrackets;
    procedure TestBufFlush_ContainsCellChar;
    procedure TestBufFlush_ClearsDirty;
    procedure TestBufFlush_SameBytesAsV2b;
    procedure TestV3_SingleCell_ContainsCellChar;
    procedure TestV2b_SameBytesAsV2;
    procedure TestV3b_SameBytesAsV3;
    procedure TestV2_TwoAdjacentCells_SkipsSecondCursorPos;
    procedure TestBufFlush_NonConsecCellsEmitCursorPos;
    procedure TestBufFlush_RowJumpEmitsCursorPos;
    procedure TestBufFlush_HUDAfterInteriorEmitsCursorPos;
  end;

procedure TBufFlushOutputTests.ResetScene;
begin
  FillChar(Screen, SizeOf(Screen), 0);
  FillChar(Dirty, SizeOf(Dirty), 0);
  BufPutCell(5, 3, White, Black, 'A');
end;

procedure TBufFlushOutputTests.SetUp;
begin
  ResetScene;
end;

procedure TBufFlushOutputTests.TearDown;
begin
  BufFlushEnabled := false;
end;

{ BufFlush: ESC[?7l ... content ... ESC[?7h }
procedure TBufFlushOutputTests.TestBufFlush_HasLineWrapBrackets;
var S: AnsiString;
begin
  S := CaptureRawFlush(@BufFlush);
  AssertTrue('starts with ESC[?7l', Copy(S, 1, 5) = #27'[?7l');
  AssertTrue('ends with ESC[?7h',   Copy(S, Length(S) - 4, 5) = #27'[?7h');
end;

{ BufFlush: output contains cursor-position and cell character. }
procedure TBufFlushOutputTests.TestBufFlush_ContainsCellChar;
var S: AnsiString;
begin
  S := CaptureRawFlush(@BufFlush);
  AssertTrue('contains cursor pos ESC[3;5H', Pos(#27'[3;5H', S) > 0);
  AssertTrue('contains cell char A',          Pos('A', S) > 0);
end;

{ BufFlush: all dirty flags cleared after flush. }
procedure TBufFlushOutputTests.TestBufFlush_ClearsDirty;
begin
  CaptureRawFlush(@BufFlush);
  AssertFalse('Dirty[5,3] cleared after flush', Dirty[5, 3]);
end;

{ BufFlush must produce exactly the same bytes as V2b. }
procedure TBufFlushOutputTests.TestBufFlush_SameBytesAsV2b;
var BFOut, V2bOut: AnsiString;
begin
  BFOut := CaptureRawFlush(@BufFlush);
  ResetScene;
  V2bOut := CaptureRawFlush(@BufFlushV2b);
  AssertEquals(BFOut, V2bOut);
end;

{ V3 uses a different cursor-first order but must still contain the char. }
procedure TBufFlushOutputTests.TestV3_SingleCell_ContainsCellChar;
var S: AnsiString;
begin
  S := CaptureTextFlush(@BufFlushV3);
  AssertTrue('V3 contains cursor pos ESC[3;5H', Pos(#27'[3;5H', S) > 0);
  AssertTrue('V3 contains cell char A',          Pos('A', S) > 0);
end;

{ V2b (single-write) must produce exactly the same bytes as V2. }
procedure TBufFlushOutputTests.TestV2b_SameBytesAsV2;
var V2Out, V2bOut: AnsiString;
begin
  V2Out := CaptureTextFlush(@BufFlushV2);
  ResetScene;
  V2bOut := CaptureRawFlush(@BufFlushV2b);
  AssertEquals(V2Out, V2bOut);
end;

{ V3b (single-write) must produce exactly the same bytes as V3. }
procedure TBufFlushOutputTests.TestV3b_SameBytesAsV3;
var V3Out, V3bOut: AnsiString;
begin
  V3Out := CaptureTextFlush(@BufFlushV3);
  ResetScene;
  V3bOut := CaptureRawFlush(@BufFlushV3b);
  AssertEquals(V3Out, V3bOut);
end;

{ BufFlush and V2 both skip the cursor-position sequence for the second of
  two adjacent cells (consec-skip behaviour). }
procedure TBufFlushOutputTests.TestV2_TwoAdjacentCells_SkipsSecondCursorPos;
var BFOut, V2Out: AnsiString;
begin
  BufPutCell(6, 3, White, Black, 'B');
  BFOut := CaptureRawFlush(@BufFlush);
  FillChar(Screen, SizeOf(Screen), 0);
  FillChar(Dirty, SizeOf(Dirty), 0);
  BufPutCell(5, 3, White, Black, 'A');
  BufPutCell(6, 3, White, Black, 'B');
  V2Out := CaptureTextFlush(@BufFlushV2);
  AssertTrue('BufFlush omits cursor pos for col 6', Pos(#27'[3;6H', BFOut) = 0);
  AssertTrue('V2 omits cursor pos for col 6',       Pos(#27'[3;6H', V2Out) = 0);
end;

{ Gap cell between two dirty cells — cursor position must be emitted for
  the second one even though it is only 2 cols away from the first. }
procedure TBufFlushOutputTests.TestBufFlush_NonConsecCellsEmitCursorPos;
var S: AnsiString;
begin
  FillChar(Screen, SizeOf(Screen), 0);
  FillChar(Dirty, SizeOf(Dirty), 0);
  BufPutCell(5, 3, White, Black, 'A');  { col 5 — first dirty }
  BufPutCell(7, 3, White, Black, 'C');  { col 7 — non-adjacent (col 6 clean) }
  S := CaptureRawFlush(@BufFlush);
  AssertTrue('non-consec: cursor pos ESC[3;7H must be present', Pos(#27'[3;7H', S) > 0);
end;

{ Dirty cell at end of a row followed by dirty cell at start of the next
  row — cursor position must always be emitted on the row change. }
procedure TBufFlushOutputTests.TestBufFlush_RowJumpEmitsCursorPos;
var S: AnsiString;
begin
  FillChar(Screen, SizeOf(Screen), 0);
  FillChar(Dirty, SizeOf(Dirty), 0);
  BufPutCell(80, 5, Red,   Black, 'X');  { last col of row 5 }
  BufPutCell(1,  6, White, Black, 'Y');  { first col of row 6 }
  S := CaptureRawFlush(@BufFlush);
  AssertTrue('row-jump: cursor pos ESC[6;1H must be present', Pos(#27'[6;1H', S) > 0);
end;

{ Interior dirty cell (row 10) followed by HUD dirty cell (lives counter,
  row 20) — cursor position must be emitted for the HUD cell. }
procedure TBufFlushOutputTests.TestBufFlush_HUDAfterInteriorEmitsCursorPos;
var S: AnsiString;
begin
  FillChar(Screen, SizeOf(Screen), 0);
  FillChar(Dirty, SizeOf(Dirty), 0);
  BufPutCell(40, 10, Red,   Black, 'W');  { interior cell }
  BufPutCell(3,  20, White, Red,   'L');  { lives counter start }
  S := CaptureRawFlush(@BufFlush);
  AssertTrue('HUD after interior: cursor pos ESC[20;3H present', Pos(#27'[20;3H', S) > 0);
  AssertTrue('HUD after interior: char L written', Pos('L', S) > 0);
end;

{ ------------------------------------------------------------------ }
{ Main                                                               }
{ ------------------------------------------------------------------ }

var
  Runner: TTestRunner;

begin
  BufFlushEnabled := false;
  RegisterTest(TStringTests);
  RegisterTest(TBufferTests);
  RegisterTest(TLevelTests);
  RegisterTest(TDrawTests);
  RegisterTest(TGameLogicTests);
  RegisterTest(TEnemyMoveTests);
  RegisterTest(TMovementTests);
  RegisterTest(TPlaceBlockTests);
  RegisterTest(TPlayerStateTests);
  RegisterTest(TDialogTests);
  RegisterTest(TScreenOverlayTests);
  RegisterTest(TGameFlowTests);
  RegisterTest(TBufFlushOutputTests);
  Runner := TTestRunner.Create(nil);
  Runner.Initialize;
  Runner.Run;
  Runner.Free;
end.
