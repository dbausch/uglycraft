{$H+}
program UGLI_2;

uses CThreads, CRT, DOS, UOSSound;

label NewGame, StartLevel, PlayAgain, OnGameOver, CleanUp;

const
  User = 'Public Domain';
  Version = '2.3';
  Release = '0042';
  FieldW = 80;
  FieldH = 20;
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
  { Foreground / background color roles }
  WallFg    = Red;       { border and interior wall blocks █ }
  PlayerFg  = Yellow;    { player smiley ☺ }
  EnemyFg   = Brown;     { enemy smiley ☻ }
  CounterFg = White;     { HUD counter text }
  CounterBg = Red;       { background for all HUD counters }
  FieldBg   = Black;     { playing field background }
  KeyHelpFg = LightCyan; { key-help bar text }
  HelpFg    = Magenta;   { help-screen and story-screen text }
  SplashFg  = White;     { level-transition splash text }
  DialogFg  = White;     { modal dialog text (AskPlayAgain, RemoveBlocks) }
  WinFg      = LightRed;   { win-screen text }
  ItemDescFg = Black;      { item-descriptions screen foreground }
  ItemDescBg = LightGray;  { item-descriptions screen background }
  ItemCount  = 10;

type
  TDirection = (DirRight, DirLeft, DirDown, DirUp);
  TItemData = record
    Ch: String[4];   { UTF-8 character (max 3 bytes) }
    Fg: Integer;     { foreground color during gameplay }
  end;

const
  Items : array[1..ItemCount] of TItemData = (
    (Ch: '|'; Fg: Brown),
    (Ch: '☼'; Fg: LightBlue),
    (Ch: ':'; Fg: LightRed),
    (Ch: '*'; Fg: LightBlue),
    (Ch: '='; Fg: Yellow),
    (Ch: '≡'; Fg: LightGray),
    (Ch: 'Γ'; Fg: Cyan),
    (Ch: 'Φ'; Fg: Yellow),
    (Ch: '♦'; Fg: LightGreen),
    (Ch: '⌂'; Fg: Yellow)
  );

var
  BlocksRemaining, MoveDelay, PausesRemaining, EnemyTick, KeyCode, I, J,
  ItemNo, Level, Lives, SaveX, SaveY, BlockX, BlockY, ItemX, ItemY, DX, DY, X,
  Y, EX, EY, EscState, StartX, StartY, StartEX, StartEY: Integer;
  Score: LongInt;
  Blocked: array[1..FieldW, 1..FieldH] of Boolean;
  Key: Char;
  Direction, StartDir: TDirection;
  Laying: Boolean;
  F, TTY: Text;
  FirstName, LastName, S: String;
  Line: String[80];
  YesKey, NoKey: set of Byte;

resourcestring
  { Item names — parallel to Items[1..10] }
  sItemName1  = 'Rope';
  sItemName2  = 'Large Sparkling Diamond';
  sItemName3  = 'Small Gems';
  sItemName4  = 'Small Sparkling Diamond';
  sItemName5  = 'Gold Bar';
  sItemName6  = 'Silver Bar';
  sItemName7  = 'Well';
  sItemName8  = 'Lamp';
  sItemName9  = 'Large Gem';
  sItemName10 = 'Crown';
  { Yes/No key characters — single uppercase letter each.
    YesKey/NoKey sets are built from these at startup (see Init).
    Translators: keep sYesNo consistent with these two values. }
  sYesChar = 'Y';
  sNoChar  = 'N';
  { HUD counter labels (trailing space before the number) }
  sLabelLevel  = 'LEVEL ';
  sLabelScore  = 'SCORE ';
  sLabelLives  = 'LIVES ';
  sLabelPauses = 'PAUSES ';
  sLabelBlocks = 'BLOCKS ';
  { Key help bar — 3 lines at rows 21, 23, 25 }
  sKeys1 = '← = left  ↓ = down  → = right  ↑ = up';
  sKeys2 = '<F1> = Help  <F2> = Story of UGLI  <F3> = Buy life  <F4> = Restart';
  sKeys3 = '<P> = Pause  <End> = Slower  <Home> = Faster  <Esc> = Quit';
  { Help screen (ShowHelp) }
  sHelpTitle  = 'UGLI HELP';
  sHelpP      = '[P] = Pause (uses 1 pause)';
  sHelpArrows = 'Arrow keys: ← = left  ↓ = down  → = right  ↑ = up';
  sHelpEsc    = '[Esc] = Quit';
  sHelpEnd    = '[End] = Slower';
  sHelpHome   = '[Home] = Faster';
  sHelpF4     = '[F4] = Restart';
  sHelpF3     = '[F3] = Buy a life (costs 5000 points)';
  sHelpF2     = '[F2] = The story of UGLI';
  sHelpSpace  = '[Space] = Toggle block placement (on/off, costs 20 pts each)';
  sHelpF5     = '[F5] = Remove all placed blocks';
  sHelpF1     = '[F1] = This help screen';
  { Story screen (ShowStory) }
  sStoryTitle = 'The Story of UGLI';
  sStoryLine1 = 'A king has locked you in his castle.';
  sStoryLine2 = 'With the words: "I will not set you free until you have';
  sStoryLine3 = 'found all of my treasures," he slammed the door shut.';
  sStoryLine4 = 'There is nothing left for you to do but collect his treasures.';
  sStoryLine5 = 'So you start running immediately to collect them all.';
  { Item descriptions screen (ShowItemDescriptions) }
  sItemListTitle = 'T R E A S U R E S   T O   C O L L E C T';
  sItemInstTitle = 'H O W   T O   P L A Y';
  sItemInst1 = 'Press a key, then press one of the arrow keys.';
  sItemInst2 = 'Use the arrow keys to collect the treasures shown above.';
  sItemInst3 = '(The crown comes last.) During the game, press <F1> to see';
  sItemInst4 = 'the other keys available during play.';
  { Shared prompt used in intro, help, story, item list, HS entry, win screen }
  sPressKey = 'P R E S S   A   K E Y';
  { Dialog titles and prompts }
  sLevelPrefix  = 'L E V E L  ';   { level number appended at runtime }
  sGameOver     = 'G A M E   O V E R';
  sYouWon       = 'Y O U   W O N';
  sRemoveBlocks = 'R E M O V E   B L O C K S';
  sPlayAgain    = 'P L A Y   A G A I N ?';
  sYesNo        = 'Y / N';         { must match sYesChar / sNoChar }
  { High score entry (HighScoreEntry) }
  sFirstName   = 'FIRST NAME ';
  sLastName    = 'LAST NAME ';
  sScoreEntry  = 'Score ';
  sHSFileError = 'Could not create high score file.';
  { Intro (hard-coded inside Intro procedure body) }
  sIntroBrand   = '* DANISOFT * PRESENTS *';
  sIntroWelcome = 'Hello, get ready to play!';

procedure MyCursorOn;
begin
  Write(TTY, #27'[?25h');
end;

procedure MyCursorOff;
begin
  Write(TTY, #27'[?25l');
end;

function UTF8Cols(S: String): Integer;
var I, Count: Integer;
  B: Byte;
begin
  Count := 0;
  for I := 1 to Length(S) do
    begin
      B := Ord(S[I]);
      if (B < $80) or (B >= $C0) then Inc(Count);
    end;
  UTF8Cols := Count;
end;

function Center(S: String): String;
var Cols, Blanks, I: Integer;
  Padding: String;
begin
  Cols := UTF8Cols(S);
  Blanks := 39 - (Cols div 2);
  Padding := '';
  for I := 1 to Blanks do Padding := Padding + ' ';
  Center := Padding + S;
end;

procedure Draw(Col, Row, Fg, Bg: Integer; S: String);
var I, C, N: Integer; Ch: String[4];
begin
  TextColor(Fg);
  TextBackground(Bg);
  Write(TTY, #27'[?7l'); { disable autowrap for the duration }
  C := Col;
  I := 1;
  while I <= Length(S) do
    begin
      if (Ord(S[I]) and $F0) = $E0 then N := 3
      else if (Ord(S[I]) and $E0) = $C0 then N := 2
      else N := 1;
      Ch[0] := Chr(N);
      if N >= 1 then Ch[1] := S[I];
      if N >= 2 then Ch[2] := S[I + 1];
      if N >= 3 then Ch[3] := S[I + 2];
      Write(TTY, #27'[1;1H'); { poison }
      Write(TTY, #27'[', Row, ';', C, 'H'); { real position }
      Write(TTY, Ch);
      Inc(I, N);
      Inc(C);
    end;
  Write(TTY, #27'[?7h'); { re-enable autowrap }
  Flush(TTY);
  GotoXY(1, 1);
  GotoXY(C, Row); { sync CRT's position tracker }
end;

procedure DrawHLine(X1, X2, Y, Fg, Bg: Integer; Ch: String);
var I: Integer;
begin
  for I := X1 to X2 do
    Draw(I, Y, Fg, Bg, Ch);
end;

function GetKey: Char;
var Raw: Char;
begin
  Raw := ReadKey;
  if Raw = #0 then
    begin
      EscState := 0;
      if KeyPressed then Raw := ReadKey else Raw := #0;
    end
  else if (EscState = 2) and (Raw = #27) then
    begin
      EscState := 0; Raw := Chr(KeySlower);
    end
  else if (EscState = 1) and (Raw = '[') then
    begin
      EscState := 2; Raw := #0;
    end
  else
    begin
      EscState := 0;
      if Raw = 'F' then
        begin
          EscState := 1; Raw := #0;
        end;
    end;
  GetKey := Raw;
end;

function WaitKey: Integer;
var K: Char;
begin
  repeat
    K := GetKey;
  until not KeyPressed;
  WaitKey := Ord(K);
end;

procedure Intro(Logo1, Logo2, Logo3, Logo4, Logo5, Logo6, Logo7, Logo8: String; Version: String;
  Release, User, CopyYear: String);
var I: Integer;
  ITTY: Text;

procedure WLn(S: String);
begin
  if S = '' then Write(' ') else Write(S); { at least one char forces FPC to emit SGR }
  Write(ITTY, #27'[K'); Flush(ITTY);
  WriteLn;
  Write(ITTY, #27'[K'); Flush(ITTY);
end;

begin
  Assign(ITTY, '/dev/tty');
  ReWrite(ITTY);
  Write(#27'[1;25r'); { confine scrolling to rows 1-25 }
  for I := 0 to 7 do
    begin
      TextBackground(I);
      ClrScr;
      Ton(I * 150, 300);
      Delay(20);
    end;
  Delay(100);
  TextColor(Black);
  TextBackground(0);
  GotoXY(1, 1);
  TextColor(15);
  for I := 1 to 25 do
    begin
      Delay(200);
      GotoXY(1, I);
      ClrEol;
      Write('                        |                            |');
    end;
  TextColor(0);
  TextBackground(7);
  GotoXY(1, 25);
  Delay(200);
  WLn('');
  Delay(200);
  WLn(Center(sIntroBrand));
  Delay(200);
  WLn('');
  Delay(200);
  WLn('');
  TextColor(Red + Blink);
  TextBackground(7);
  Delay(200);
  WLn(Logo1);
  Delay(200);
  WLn(Logo2);
  Delay(200);
  WLn(Logo3);
  Delay(200);
  WLn(Logo4);
  Delay(200);
  WLn(Logo5);
  Delay(200);
  WLn(Logo6);
  Delay(200);
  WLn(Logo7);
  Delay(200);
  WLn(Logo8);
  Delay(200);
  WLn('');
  Delay(200);
  TextColor(Black + Blink);
  TextBackground(7);
  WLn('');
  Delay(200);
  WLn(Center(sIntroWelcome));
  Delay(200);
  WLn('');
  TextColor(Black);
  TextBackground(15);
  Delay(200);
  WLn(Center(User));
  Delay(200);
  WLn('');
  Delay(200);
  WLn(Center('Version: ' + Version + '/' + Release));
  Delay(200);
  WLn('');
  Delay(200);
  WLn(Center(CopyYear));
  Delay(200);
  WLn('');
  Delay(200);
  WLn('');
  Delay(200);
  TextColor(4);
  Write(Center(sPressKey));
  WLn('');
  WaitKey;
  ClrScr;
  for I := 40 to 50 do
    begin
      Ton(I, 150);
    end;
  TextColor(Black);
  Write(#27'[r'); { reset scroll region to full screen }
  Close(ITTY);
end;

procedure DrawItem;
var Idx: Integer;
begin
  Idx := ItemNo;
  if (ItemNo = 9) and (Level = 9) then Idx := 10;
  Draw(ItemX, ItemY, Items[Idx].Fg, FieldBg, Items[Idx].Ch);
end;

procedure DrawInner;
const
  Fg = WallFg;
  Bg = FieldBg;
var I, J: Integer;
begin
  for I := 2 to 79 do
    for J := 2 to 19 do
      if Blocked[I, J] then
        Draw(I, J, Fg, Bg, '█')
      else
        Draw(I, J, Fg, Bg, ' ');
  if X >= 2 then
    Draw(X, Y, PlayerFg, FieldBg, '☺');
  if EX >= 2 then
    Draw(EX, EY, EnemyFg, FieldBg, '☻');
  if ItemX >= 2 then
    DrawItem;
end;

procedure DrawLevel;
const
  Fg = CounterFg;
  Bg = CounterBg;
var S: String;
begin
  Str(Level, S);
  Draw(36, 1, Fg, Bg, sLabelLevel + S);
end;

procedure DrawScore;
const
  Fg = CounterFg;
  Bg = CounterBg;
var S: String;
begin
  Str(Score:5, S);
  Draw(3, 1, Fg, Bg, sLabelScore + S);
end;

procedure DrawLives;
const
  Fg = CounterFg;
  Bg = CounterBg;
var S: String;
begin
  Str(Lives:2, S);
  Draw(3, 20, Fg, Bg, sLabelLives + S);
end;

procedure DrawPauses;
const
  Fg = CounterFg;
  Bg = CounterBg;
var S: String;
begin
  Str(PausesRemaining:2, S);
  Draw(70, 1, Fg, Bg, sLabelPauses + S);
end;

procedure DrawBlocks;
const
  Fg = CounterFg;
  Bg = CounterBg;
var S: String;
begin
  Str(BlocksRemaining:4, S);
  Draw(68, 20, Fg, Bg, sLabelBlocks + S);
end;

procedure AwardPoints;
begin
  Score := Score + ItemNo * 100;
  DrawScore;
end;

procedure DrawKeys;
const
  Fg = KeyHelpFg;
  Bg = FieldBg;
begin
  Draw(2, 21, Fg, Bg, sKeys1);
  DrawHLine(1, 80, 22, Fg, Bg, '─');
  Draw(2, 23, Fg, Bg, sKeys2);
  DrawHLine(1, 80, 24, Fg, Bg, '─');
  Draw(2, 25, Fg, Bg, sKeys3);
end; {DrawKeys}

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

function GetItemName(I: Integer): String;
begin
  case I of
    1:  GetItemName := sItemName1;
    2:  GetItemName := sItemName2;
    3:  GetItemName := sItemName3;
    4:  GetItemName := sItemName4;
    5:  GetItemName := sItemName5;
    6:  GetItemName := sItemName6;
    7:  GetItemName := sItemName7;
    8:  GetItemName := sItemName8;
    9:  GetItemName := sItemName9;
    10: GetItemName := sItemName10;
  end;
end;

procedure DrawItemName;
const
  Fg = CounterFg;
  Bg = CounterBg;
  ZoneStart = 12;
  ZoneEnd   = 66;
  ZoneW     = ZoneEnd - ZoneStart + 1;  { = 55 }
var
  Idx, NameW, Pad, I: Integer;
  Name, Padded: String;
begin
  Idx := ItemNo;
  if (ItemNo = 9) and (Level = 9) then Idx := 10;
  Name := GetItemName(Idx);
  NameW := UTF8Cols(Name);
  Pad := (ZoneW - NameW) div 2;
  Padded := '';
  for I := 1 to Pad do Padded := Padded + ' ';
  Padded := Padded + Name;
  while UTF8Cols(Padded) < ZoneW do Padded := Padded + ' ';
  Draw(ZoneStart, FieldH, Fg, Bg, Padded);
end;

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
  DrawItemName;
end; {DrawBorder}

procedure Redraw;
begin
  TextBackground(FieldBg);
  ClrScr;
  DrawBorder;
  DrawKeys;
  DrawInner;
end; {Redraw}

procedure InitLevel1;
begin
  StartX := 40;
  StartY := 10;
  StartDir := DirRight;
  StartEX := 5;
  StartEY := 10;
end; {InitLevel1}

procedure InitLevel2;
var
  I: Integer;
begin
  for I := 18 to 62 do
    begin
      Blocked[I, 10] := true;
    end;
  StartX := 40;
  StartY := 5;
  StartDir := DirRight;
  StartEX := 5;
  StartEY := 10;
end; {InitLevel2}

procedure InitLevel3;
var
  I: Integer;
begin
  for I := 5 to 15 do
    begin
      Blocked[20, I] := true;
      Blocked[60, I] := true;
    end;
  for I := 20 to 60 do
    begin
      Blocked[I, 10] := true;
    end;
  Blocked[39, 10] := false;
  Blocked[40, 10] := false;
  Blocked[41, 10] := false;
  StartX := 40;
  StartY := 9;
  StartDir := DirUp;
  StartEX := 5;
  StartEY := 10;
end; {InitLevel3}

procedure InitLevel4;
var
  I: Integer;
begin
  for I := 4 to 8 do
    begin
      Blocked[15, I] := true;
      Blocked[65, I] := true;
    end;
  for I := 6 to 74 do
    Blocked[I, 10] := true;
  for I := 12 to 16 do
    begin
      Blocked[15, I] := true;
      Blocked[65, I] := true;
    end;
  Blocked[39, 10] := false;
  Blocked[40, 10] := false;
  Blocked[41, 10] := false;
  StartX := 40;
  StartY := 9;
  StartDir := DirRight;
  StartEX := 5;
  StartEY := 10;
end; {InitLevel4}

procedure InitLevel5;
var
  I: Integer;
begin
  for I := 5 to 15 do
    begin
      Blocked[20, I] := true;
      Blocked[60, I] := true;
    end;
  for I := 22 to 58 do
    begin
      Blocked[I, 7] := true;
      Blocked[I, 13] := true;
    end;
  for I := 20 to 60 do
    begin
      Blocked[I, 10] := false;
    end;
  StartX := 40;
  StartY := 10;
  StartDir := DirUp;
  StartEX := 5;
  StartEY := 10;
end; {InitLevel5}

procedure InitLevel6;
var
  I: Integer;
begin
  for I := 2 to 8 do
    begin
      Blocked[10, I] := true;
      Blocked[20, I] := true;
      Blocked[30, I] := true;
      Blocked[40, I] := true;
      Blocked[50, I] := true;
      Blocked[60, I] := true;
      Blocked[70, I] := true;
    end;
  for I := 12 to 19 do
    begin
      Blocked[10, I] := true;
      Blocked[20, I] := true;
      Blocked[30, I] := true;
      Blocked[40, I] := true;
      Blocked[50, I] := true;
      Blocked[60, I] := true;
      Blocked[70, I] := true;
    end;
  for I := 5 to 15 do
    begin
      Blocked[15, I] := true;
      Blocked[25, I] := true;
      Blocked[35, I] := true;
      Blocked[45, I] := true;
      Blocked[55, I] := true;
      Blocked[65, I] := true;
    end;
  for I := 6 to 74 do
    begin
      Blocked[I, 10] := true;
      Blocked[I, 9] := false;
      Blocked[I, 11] := false;
    end;
  Blocked[38, 10] := false;
  Blocked[39, 10] := false;
  Blocked[40, 10] := false;
  Blocked[41, 10] := false;
  Blocked[42, 10] := false;
  StartX := 75;
  StartY := 5;
  StartDir := DirDown;
  StartEX := 5;
  StartEY := 10;
end; {InitLevel6}

procedure InitLevel7;
var
  I, J: Integer;
begin
  J := 0;
  for I := 3 to 17 do
    begin
      Inc(J);
      Blocked[5 + J, I] := true;
      Blocked[33 + J, I] := true;
      Blocked[60 + J, I] := true;
    end;
  J := 16;
  for I := 3 to 17 do
    begin
      Dec(J);
      Blocked[5 + J, I] := true;
      Blocked[33 + J, I] := true;
      Blocked[60 + J, I] := true;
    end;
  for J := 9 to 11 do
    for I := 2 to 79 do
      Blocked[I, J] := false;
  for I := 6 to 74 do
    Blocked[I, 10] := true;
  for I := 54 to 56 do
    Blocked[I, 10] := false;
  for I := 26 to 28 do
    Blocked[I, 10] := false;
  StartX := 75;
  StartY := 10;
  StartDir := DirRight;
  StartEX := 5;
  StartEY := 10;
end; {InitLevel7}

procedure InitLevel8;
var
  I: Integer;
begin
  for I := 2 to 15 do
    begin
      Blocked[10, I] := true;
      Blocked[30, I] := true;
      Blocked[50, I] := true;
      Blocked[70, I] := true;
    end;
  for I := 5 to 19 do
    begin
      Blocked[20, I] := true;
      Blocked[40, I] := true;
      Blocked[60, I] := true;
    end;
  StartX := 75;
  StartY := 5;
  StartDir := DirDown;
  StartEX := 5;
  StartEY := 10;
end; {InitLevel8}

procedure InitLevel9;
var I: Integer;
begin
  for I := 5 to 15 do
    begin
      Blocked[20, I] := true;
      Blocked[60, I] := true;
      Blocked[39, I] := true;
      Blocked[41, I] := true;
    end;
  for I := 21 to 38 do
    Blocked[I, 5] := true;
  for I := 42 to 59 do
    Blocked[I, 5] := true;
  for I := 22 to 37 do
    Blocked[I, 15] := true;
  for I := 43 to 58 do
    Blocked[I, 15] := true;
  StartX := 40;
  StartY := 10;
  StartDir := DirUp;
  StartEX := 5;
  StartEY := 10;
end;

procedure InitLevel(L: Integer);
begin
  case L of
    1: InitLevel1;
    2: InitLevel2;
    3: InitLevel3;
    4: InitLevel4;
    5: InitLevel5;
    6: InitLevel6;
    7: InitLevel7;
    8: InitLevel8;
    9: InitLevel9;
  end; {case}
end; {InitLevel}

procedure PrepareLevel;
var I, J: Integer;
begin
  for I := 2 to FieldW - 1 do
    for J := 2 to FieldH - 1 do
      Blocked[I, J] := false;
  InitLevel(Level);
  X := StartX; Y := StartY;
  EX := StartEX; EY := StartEY;
  Direction := StartDir;
  Redraw;
end; {PrepareLevel}

procedure MoveDown(var X: Integer; var Y: Integer);
const
  Bg = FieldBg;
var OldY: Integer;
begin
  OldY := Y;
  if Blocked[X, Y + 1] then SoundBump
  else Y := Y + 1;
  if Y <> OldY then
    begin
      Draw(X, OldY, Bg, Bg, ' ');
      Draw(X, Y, PlayerFg, Bg, '☺');
    end;
  GotoXY(1, 1);
  Draw(BlockX, BlockY, WallFg, Bg, '█');
end; {MoveDown}

procedure MoveLeft(var X: Integer; var Y: Integer);
const
  Bg = FieldBg;
var OldX: Integer;
begin
  OldX := X;
  if Blocked[X - 1, Y] then SoundBump
  else X := X - 1;
  if X <> OldX then
    begin
      Draw(OldX, Y, Bg, Bg, ' ');
      Draw(X, Y, PlayerFg, Bg, '☺');
    end;
  GotoXY(1, 1);
  Draw(BlockX, BlockY, WallFg, Bg, '█');
end; {MoveLeft}

procedure MoveRight(var X: Integer; var Y: Integer);
const
  Bg = FieldBg;
var OldX: Integer;
begin
  OldX := X;
  if Blocked[X + 1, Y] then SoundBump
  else X := X + 1;
  if X <> OldX then
    begin
      Draw(OldX, Y, Bg, Bg, ' ');
      Draw(X, Y, PlayerFg, Bg, '☺');
    end;
  GotoXY(1, 1);
  Draw(BlockX, BlockY, WallFg, Bg, '█');
end; {MoveRight}

procedure MoveUp(var X: Integer; var Y: Integer);
const
  Bg = FieldBg;
var OldY: Integer;
begin
  OldY := Y;
  if Blocked[X, Y - 1] then SoundBump
  else Y := Y - 1;
  if Y <> OldY then
    begin
      Draw(X, OldY, Bg, Bg, ' ');
      Draw(X, Y, PlayerFg, Bg, '☺');
    end;
  GotoXY(1, 1);
  Draw(BlockX, BlockY, WallFg, Bg, '█');
end; {MoveUp}

procedure EnemyMove;
var
  OldEX, OldEY: Integer;
  TryHoriz: Boolean;
  Attempt: Integer;
begin
  if EnemyTick = 0 then
    begin
      OldEX := EX;
      OldEY := EY;
      DX := X - EX;
      DY := Y - EY;
      TryHoriz := Abs(DX) > Abs(DY);
      for Attempt := 1 to 2 do
        begin
          if TryHoriz then
            begin
              if (DX > 0) and (Blocked[EX + 1, EY] = false) then
                begin
                  EX := EX + 1;
                  break;
                end;
              if (DX < 0) and (Blocked[EX - 1, EY] = false) then
                begin
                  EX := EX - 1;
                  break;
                end;
            end
          else
            begin
              if (DY > 0) and (Blocked[EX, EY + 1] = false) then
                begin
                  EY := EY + 1;
                  break;
                end;
              if (DY < 0) and (Blocked[EX, EY - 1] = false) then
                begin
                  EY := EY - 1;
                  break;
                end;
            end;
          TryHoriz := not TryHoriz;
        end;
      if (EX <> OldEX) or (EY <> OldEY) then
        Draw(OldEX, OldEY, FieldBg, FieldBg, ' ');
      Draw(EX, EY, EnemyFg, FieldBg, '☻');
    end;
end; {EnemyMove}

procedure DoPause;
begin
  if PausesRemaining > 0 then
    begin
      PausesRemaining := PausesRemaining - 1;
      DrawPauses;
      Delay(5000);
    end;
end;

procedure SlowDown;
begin
  MoveDelay := MoveDelay + 1;
end;

procedure SpeedUp;
begin
  if MoveDelay > 0 then MoveDelay := MoveDelay - 1;
end;

procedure PlaceBlock;
begin
  if (BlocksRemaining = 0) or (Score < 20) then
    Laying := false
  else if not Blocked[X, Y] then
    begin
      Draw(X, Y, WallFg, FieldBg, '█');
      Blocked[X, Y] := true;
      BlockX := X;
      BlockY := Y;
      Score := Score - 20;
      BlocksRemaining := BlocksRemaining - 1;
      DrawBlocks;
      DrawScore;
    end;
end;

procedure ShowHelp;
const
  Fg = HelpFg;
  Bg = FieldBg;
begin
  SaveX := X;
  SaveY := Y;
  ClrScr;
  Draw(1, 2, Fg, Bg, Center(sHelpTitle));
  Draw(2, 4, Fg, Bg, sHelpP);
  Draw(2, 5, Fg, Bg, sHelpArrows);
  Draw(2, 6, Fg, Bg, sHelpEsc);
  Draw(2, 7, Fg, Bg, sHelpEnd);
  Draw(2, 8, Fg, Bg, sHelpHome);
  Draw(2, 9, Fg, Bg, sHelpF4);
  Draw(2, 10, Fg, Bg, sHelpF3);
  Draw(2, 11, Fg, Bg, sHelpF2);
  Draw(2, 12, Fg, Bg, sHelpSpace);
  Draw(2, 13, Fg, Bg, sHelpF5);
  Draw(2, 14, Fg, Bg, sHelpF1);
  Draw(1, 24, Fg, Bg, Center(sPressKey));
  WaitKey;
  X := SaveX;
  Y := SaveY;
end;

procedure ShowStory;
const
  Fg = HelpFg;
  Bg = FieldBg;
begin
  ClrScr;
  Draw(1, 2, Fg, Bg, Center(sStoryTitle));
  Draw(1, 4, Fg, Bg, Center(sStoryLine1));
  Draw(1, 5, Fg, Bg, Center(sStoryLine2));
  Draw(1, 6, Fg, Bg, Center(sStoryLine3));
  Draw(1, 7, Fg, Bg, Center(sStoryLine4));
  Draw(1, 8, Fg, Bg, Center(sStoryLine5));
  Draw(1, 24, Fg, Bg, Center(sPressKey));
  WaitKey;
end;

function Dialog(Title: String; Prompt: String): Integer;
const
  Fg = DialogFg;
  Bg = FieldBg;
var
  W, X1, X2, Y1, BoxH, TW, PW, Pad: Integer;
  Buf: String;
begin
  TW := UTF8Cols(Title);
  PW := UTF8Cols(Prompt);
  if TW > PW then W := TW + 4 else W := PW + 4;
  if W < 27 then W := 27;
  X1 := (FieldW - W) div 2 + 1;
  X2 := X1 + W - 1;
  if Prompt = '' then BoxH := 3 else BoxH := 4;
  Y1 := (FieldH - BoxH) div 2 + 1;
  DrawHLine(X1, X2, Y1, Fg, Bg, '█');
  Draw(X1, Y1 + 1, Fg, Bg, '█');
  Pad := (W - 2 - TW) div 2;
  Buf := '';
  for I := 1 to Pad do Buf := Buf + ' ';
  Buf := Buf + Title;
  while UTF8Cols(Buf) < W - 2 do Buf := Buf + ' ';
  Draw(X1 + 1, Y1 + 1, Fg, Bg, Buf);
  Draw(X2, Y1 + 1, Fg, Bg, '█');
  DrawHLine(X1, X2, Y1 + 2, Fg, Bg, '█');
  if Prompt <> '' then
    begin
      Pad := (W - PW) div 2;
      Buf := '';
      for I := 1 to Pad do Buf := Buf + ' ';
      Buf := Buf + Prompt;
      Draw(X1, Y1 + 3, Fg, Bg, Buf);
    end;
  Dialog := WaitKey;
  DrawInner;
end;

function KeyToDir(Code: Integer): TDirection;
begin
  case Code of
    KeyRight: KeyToDir := DirRight;
    KeyLeft:  KeyToDir := DirLeft;
    KeyUp:    KeyToDir := DirUp;
    KeyDown:  KeyToDir := DirDown;
  end;
end;

procedure MovePlayer;
begin
  case Direction of
    DirRight: MoveRight(X, Y);
    DirLeft:  MoveLeft(X, Y);
    DirUp:    MoveUp(X, Y);
    DirDown:  MoveDown(X, Y);
  end;
end;

procedure LevelTransition;
begin
  Str(Level, S);
  KeyCode := Dialog(sLevelPrefix + S, sPressKey);
  if KeyCode in [KeyRight, KeyLeft, KeyUp, KeyDown] then
    Direction := KeyToDir(KeyCode);
  Delay(1000);
end;

procedure HandleInput;
begin
  KeyCode := 0;
  if KeyPressed then
    begin
      Key := GetKey;
      KeyCode := Ord(Key);
      case KeyCode of
        KeyRight, KeyLeft, KeyUp, KeyDown: Direction := KeyToDir(KeyCode);
        KeyPause: DoPause;
        KeySlower: SlowDown;
        KeyFaster: SpeedUp;
        KeySpace: Laying := not Laying;
        KeyF3:
          begin
            if Score >= 5000 then
              begin
                Lives := Lives + 1;
                Score := Score - 5000;
                DrawLives;
                DrawScore;
              end;
          end;
        KeyF1:
          begin
            ShowHelp;
            Redraw;
          end;
        KeyF2:
          begin
            ShowStory;
            Redraw;
          end;
      end; {case}
    end;
  EnemyTick := (EnemyTick + 1) mod 2;
  GotoXY(1, 1);
  MovePlayer;
  if Laying then PlaceBlock;
  Draw(X, Y, PlayerFg, FieldBg, '☺');
end;

procedure HighScoreEntry;
begin
  TextColor(LightBlue);
  TextBackground(Black);
  ClrScr;
  WriteLn;
  WriteLn(sFirstName);
  MyCursorOn;
  GotoXY(UTF8Cols(sFirstName) + 1, 2); ReadLn(FirstName);
  WriteLn(sLastName);
  GotoXY(UTF8Cols(sLastName) + 1, 3); ReadLn(LastName);
  MyCursorOff;
  Str(Score * Lives, S); Draw(1, 4, CounterFg, FieldBg, sScoreEntry + S);
  Assign(F, HighScoreFileName);
  Append(F);
  if IOResult = 0
  then
    begin
      WriteLn(F, FirstName, ' ', LastName, '    ', Score * Lives);
      Close(F);
      WriteLn;
    end
  else
    begin
      ReWrite(F);
      if IOResult <> 0 then
        begin
          WriteLn(sHSFileError);
        end
      else
        begin
          WriteLn(F, FirstName, ' ', LastName, '    ', Score * Lives);
          Close(F);
          WriteLn;
        end;
    end;
  WaitKey;
  ClrScr;
  Assign(F, HighScoreFileName);
  Reset(F);
  if IOResult = 0
  then
    begin
      while not Eof(F) do
        begin
          ReadLn(F, Line);
          WriteLn(Line);
        end;
      Close(F);
    end
  else
    begin
      ReWrite(F);
      if IOResult <> 0 then
        begin
          WriteLn(sHSFileError);
        end
      else
        begin
          while not Eof(F) do
            begin
              ReadLn(F, Line);
              WriteLn(Line);
            end;
          Close(F);
        end;
    end;
  GotoXY(1, 25);
  Write(sPressKey);
  WaitKey;
end;

procedure ShowItemDescriptions;
const
  Fg = ItemDescFg;
  Bg = ItemDescBg;
var
  I, Col, MaxW, ItemW: Integer;
begin
  TextBackground(Bg);
  ClrScr;
  Draw(1, 2, Fg, Bg, Center(sItemListTitle));
  MaxW := 0;
  for I := 1 to ItemCount do
    begin
      ItemW := UTF8Cols(Items[I].Ch) + 2 + UTF8Cols(GetItemName(I));
      if ItemW > MaxW then MaxW := ItemW;
    end;
  Col := (FieldW - MaxW) div 2 + 1;
  for I := 1 to ItemCount do
    Draw(Col, 3 + I, Fg, Bg, Items[I].Ch + '  ' + GetItemName(I));
  Draw(1, 16, Fg, Bg, Center(sItemInstTitle));
  Draw(5, 18, Fg, Bg, sItemInst1);
  Draw(5, 19, Fg, Bg, sItemInst2);
  Draw(5, 20, Fg, Bg, sItemInst3);
  Draw(5, 21, Fg, Bg, sItemInst4);
  Draw(1, 24, Fg, Bg, Center(sPressKey));
  WaitKey;
end;

procedure GameOver;
begin
  SoundGameOver;
  Dialog(sGameOver, '');
end;

procedure WinScreen;
begin
  Dialog(sYouWon, sPressKey);
  SoundWon;
  HighScoreEntry;
  ClrScr;
end;

procedure Init;
begin
  YesKey := [Ord('Y'), Ord('y')];
  NoKey  := [Ord('N'), Ord('n')];
  Randomize;
  Intro(
    '                  **        **    **********   **           **                 ',
    '                  **        **   **        **  **           **                 ',
    '                  **        **   **        **  **           **                 ',
    '                  **        **   **            **           **                 ',
    '                  **        **   **     *****  **           **                 ',
    '                  **        **   **        **  **           **                 ',
    '                  **        **   **        **  **           **                 ',
    '                   **********     **********   **********   **                 ',
    Version, Release, User, License);
  ShowItemDescriptions;
  TextBackground(FieldBg);
  ClrScr;
  MoveDelay := 100;
  PausesRemaining := 20;
  BlocksRemaining := 2000;
  Laying := false;
  InitBorder;
end;

procedure PlayerCaught;
begin
  SoundCaught;
  Score := Score - ItemNo * 1000;
  if Score < 0 then Score := 0;
  ItemNo := 1;
  Lives := Lives - 1;
  BlockX := 1;
  BlockY := 1;
  PrepareLevel;
end;

procedure LevelComplete;
begin
  Lives := Lives + 1;
  ItemNo := 1;
  BlockX := 1;
  BlockY := 1;
  PrepareLevel;
  LevelTransition;
end;

function IsPlayerCaught: Boolean;
begin
  IsPlayerCaught := (X = EX) and (Y = EY);
end;

function IsItemPickedUp: Boolean;
begin
  IsItemPickedUp := (ItemX = X) and (ItemY = Y);
end;

procedure RandomPos;
begin
  repeat
    ItemX := Round((Random * 77) + 2);
    ItemY := Round((Random * 17) + 2);
  until not Blocked[ItemX, ItemY];
end;

procedure RemoveBlocks;
var Code: Integer;
begin
  repeat
    Code := Dialog(sRemoveBlocks, sYesNo);
  until (Byte(Code) in YesKey) or (Byte(Code) in NoKey);
  if Byte(Code) in YesKey then
    begin
      for I := 2 to FieldW - 1 do
        for J := 2 to FieldH - 1 do
          Blocked[I, J] := false;
      InitLevel(Level);
      DrawBorder;
      BlockX := 1; BlockY := 1;
    end;
  DrawInner;
end;

function AskPlayAgain: Boolean;
var Code: Integer;
begin
  repeat
    Code := Dialog(sPlayAgain, sYesNo);
  until (Byte(Code) in YesKey) or (Byte(Code) in NoKey);
  AskPlayAgain := Byte(Code) in YesKey;
end;

begin
  Assign(TTY, '/dev/tty');
  ReWrite(TTY);
  MyCursorOff;
  Init;
NewGame:
  Level := 1;
  Score := 0;
  Lives := 10;
  ItemNo := 1;
  BlockX := 1;
  BlockY := 1;
  ItemX := 0;
  PrepareLevel;
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
        AwardPoints;
        ItemNo := ItemNo + 1;
        ItemX := 0;
        DrawItemName;
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
OnGameOver:
  GameOver;
PlayAgain:
  if AskPlayAgain then goto NewGame else goto CleanUp;
CleanUp:
  ClrScr;
  Write(TTY, #27'[0m'); Flush(TTY); { reset all attributes before exit }
  MyCursorOn;
  Close(TTY);
end.
