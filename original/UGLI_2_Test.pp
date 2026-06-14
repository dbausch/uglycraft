{$mode objfpc}{$H+}
program UGLI_2_Test;

uses CThreads, CRT, DOS, BaseUnix, SysUtils, gettext, UOSSound,
     termio,
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
  HighScoreFileName = 'UGLI.HSC';
  License = 'Released under the terms of the GNU GPLv3';
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
    procedure TestWordWrap_Short;
    procedure TestWordWrap_Wraps;
    procedure TestJustify_TwoWords;
    procedure TestJustify_OneWord;
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
    procedure TestBufFill_AllCells;
    procedure TestBufDesaturate_Gray;
    procedure TestBufFlush_ClearsDirty;
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
  BufFill(Red, Red, 'X');
  BufDesaturate;
  AssertEquals(LightGray, Integer(Screen[4, 7].Fg));
  AssertEquals(Black, Integer(Screen[4, 7].Bg));
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
    procedure TestInitLevel1to9_StartPos;
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

{ ------------------------------------------------------------------ }
{ TDrawTests — Draw, DrawHLine, DrawParagraph via buffer             }
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
    procedure TestIsPlayerCaught_True;
    procedure TestIsPlayerCaught_False;
    procedure TestIsItemPickedUp_True;
    procedure TestIsItemPickedUp_False;
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

procedure TGameLogicTests.TestGetItemName_Rope;
begin
  AssertEquals('Rope', GetItemName(1));
end;

procedure TGameLogicTests.TestGetItemName_Crown;
begin
  AssertEquals('Crown', GetItemName(10));
end;

{ ------------------------------------------------------------------ }
{ Main                                                               }
{ ------------------------------------------------------------------ }

var
  Runner: TTestRunner;
  Tio: Termios;

begin
  { CRT's init clears ONLCR; restore it so WriteLn output starts at column 1 }
  tcgetattr(1, Tio);
  Tio.c_oflag := Tio.c_oflag or (OPOST or ONLCR);
  tcsetattr(1, TCSANOW, Tio);
  BufFlushEnabled := false;
  RegisterTest(TStringTests);
  RegisterTest(TBufferTests);
  RegisterTest(TLevelTests);
  RegisterTest(TDrawTests);
  RegisterTest(TGameLogicTests);
  Runner := TTestRunner.Create(nil);
  Runner.Initialize;
  Runner.Run;
  Runner.Free;
end.
