type
  TDirection = (DirRight, DirLeft, DirDown, DirUp);
  TItemData = record
    Ch: String[4];   { UTF-8 character (max 3 bytes) }
    Fg: Integer;     { foreground color during gameplay }
  end;
  TScreenCell = record
    Ch: String[4];   { one UTF-8 character stored in the off-screen buffer }
    Fg: Byte;
    Bg: Byte;
  end;
  TScreenBuffer = array[1..ScreenW, 1..ScreenH] of TScreenCell;

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
  Screen          : TScreenBuffer;
  Dirty           : array[1..ScreenW, 1..ScreenH] of Boolean;
  BufFlushEnabled : Boolean = true;
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
  sHelpArrows = '[←/↓/→/↑]   Change direction';
  sHelpSpace  = '[Space]     Toggle block placement (on/off, costs 20 pts each)';
  sHelpP      = '[P]         Pause a short while (uses 1 pause)';
  sHelpEsc    = '[Esc]       Quit';
  sHelpF1     = '[F1]        This help screen';
  sHelpF2     = '[F2]        The story of UGLI';
  sHelpF3     = '[F3]        Buy a life (costs 5000 points)';
  sHelpF4     = '[F4]        Restart';
  sHelpF5     = '[F5]        Remove all placed blocks';
  sHelpEnd    = '[End]       Slower';
  sHelpHome   = '[Home]      Faster';
  { Story screen (ShowStory) — one paragraph; wrapped + justified at display time }
  sStoryTitle = 'The Story of UGLI';
  sStoryText  = 'A king has locked you in his castle. With the words: "I will not set you free until you have found all of my treasures," he slammed the door shut. There is nothing left for you to do but collect his treasures. So you start running immediately to collect them all.';
  { Item descriptions screen (ShowItemDescriptions) — one paragraph; wrapped at display time }
  sItemListTitle = 'T R E A S U R E S   T O   C O L L E C T';
  sItemInstTitle = 'H O W   T O   P L A Y';
  sItemInstText  = 'Press a key, then press one of the arrow keys. Use the arrow keys to collect the treasures shown above. (The crown comes last.) During the game, press <F1> to see the other keys available during play.';
  { Shared prompt used in intro, help, story, item list, HS entry, win screen }
  sPressKey = 'P R E S S   A N Y   K E Y';
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

{ Fill the entire terminal window (including cells outside the 80x25 game
  area) with Bg, then home the cursor. Use instead of TextBackground+ClrScr
  whenever a background-colour transition must cover large terminal windows. }
procedure FillScreen(Bg: Integer);
begin
  Write(TTY, #27'[', 40 + Bg, 'm'); { set background via ANSI 40–47 }
  Write(TTY, #27'[2J');              { clear whole terminal with that colour }
  Write(TTY, #27'[H');               { home cursor }
  Flush(TTY);
  TextBackground(Bg);                { keep FPC CRT colour tracker in sync }
  GotoXY(1, 1);
end;

procedure BufPutCell(Col, Row: Integer; Fg, Bg: Byte; const Ch: String);
begin
  if (Col < 1) or (Col > ScreenW) or (Row < 1) or (Row > ScreenH) then Exit;
  if (Screen[Col, Row].Ch = Ch) and (Screen[Col, Row].Fg = Fg)
      and (Screen[Col, Row].Bg = Bg) then Exit;
  Screen[Col, Row].Ch := Ch;
  Screen[Col, Row].Fg := Fg;
  Screen[Col, Row].Bg := Bg;
  Dirty[Col, Row] := true;
end;

procedure BufFill(Fg, Bg: Integer; const Ch: String);
var Col, Row: Integer;
begin
  for Col := 1 to ScreenW do
    for Row := 1 to ScreenH do
      BufPutCell(Col, Row, Fg, Bg, Ch);
end;

procedure BufFlush;
var Col, Row, LastFg, LastBg: Integer;
begin
  if not BufFlushEnabled then
    begin
      for Col := 1 to ScreenW do
        for Row := 1 to ScreenH do
          Dirty[Col, Row] := false;
      Exit;
    end;
  Write(TTY, #27'[?7l');   { disable autowrap for the flush }
  LastFg := -1;
  LastBg := -1;
  for Row := 1 to ScreenH do
    for Col := 1 to ScreenW do
      if Dirty[Col, Row] then
        begin
          if (Screen[Col, Row].Fg <> LastFg) or (Screen[Col, Row].Bg <> LastBg) then
            begin
              TextColor(Screen[Col, Row].Fg);
              TextBackground(Screen[Col, Row].Bg);
              LastFg := Screen[Col, Row].Fg;
              LastBg := Screen[Col, Row].Bg;
            end;
          Write(TTY, #27'[', Row, ';', Col, 'H');
          Write(TTY, Screen[Col, Row].Ch);
          Dirty[Col, Row] := false;
        end;
  Write(TTY, #27'[?7h');   { re-enable autowrap }
  Flush(TTY);
  GotoXY(1, 1);             { sync FPC CRT position tracker }
end;

procedure BufDesaturate;
var Col, Row: Integer;
begin
  for Col := 1 to ScreenW do
    for Row := 1 to ScreenH do
      begin
        Screen[Col, Row].Fg := LightGray;
        Screen[Col, Row].Bg := Black;
        Dirty[Col, Row] := true;
      end;
end;

procedure BufCopy(var Dst: TScreenBuffer);
begin
  Dst := Screen;
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

{ Word-wrap S into Lines[0..N-1], each at most Width display columns.
  Breaks only on spaces; Lines must have room for at least 12 entries. }
procedure WordWrap(const S: String; Width: Integer;
                   var Lines: array of String; var N: Integer);
var
  I, LineStart: Integer;
  LastBreak: Integer;   { byte index of last space seen }
  LineW: Integer;       { display cols of current candidate line }
begin
  N := 0;
  I := 1;
  while (I <= Length(S)) and (S[I] = ' ') do Inc(I);
  LineStart := I;
  LastBreak := 0;
  while I <= Length(S) do
    begin
      if S[I] = ' ' then LastBreak := I;
      LineW := UTF8Cols(Copy(S, LineStart, I - LineStart + 1));
      if LineW > Width then
        begin
          if LastBreak > LineStart then
            begin
              Lines[N] := Copy(S, LineStart, LastBreak - LineStart);
              Inc(N);
              I := LastBreak + 1;
              while (I <= Length(S)) and (S[I] = ' ') do Inc(I);
              LineStart := I;
              LastBreak := 0;
            end
          else
            begin
              { single word wider than Width: force break before current char }
              Lines[N] := Copy(S, LineStart, I - LineStart);
              Inc(N);
              LineStart := I;
              LastBreak := 0;
            end;
        end
      else
        Inc(I);
    end;
  if LineStart <= Length(S) then
    begin
      Lines[N] := Copy(S, LineStart, Length(S) - LineStart + 1);
      Inc(N);
    end;
end;

{ Return S stretched to exactly Width display cols by distributing extra
  spaces evenly between words (left gaps get the remainder first).
  Returns S unchanged if it has fewer than 2 words or is already wide enough. }
function Justify(const S: String; Width: Integer): String;
var
  Words: array[0..99] of String;
  WCount, TotalW, Gaps, Extra, Base, Gap, I, K: Integer;
  R: String;
  P, Q: Integer;
begin
  WCount := 0;
  P := 1;
  while P <= Length(S) do
    begin
      while (P <= Length(S)) and (S[P] = ' ') do Inc(P);
      if P > Length(S) then Break;
      Q := P;
      while (Q <= Length(S)) and (S[Q] <> ' ') do Inc(Q);
      Words[WCount] := Copy(S, P, Q - P);
      Inc(WCount);
      P := Q;
    end;
  if WCount < 2 then
    begin
      Justify := S;
      Exit;
    end;
  TotalW := 0;
  for I := 0 to WCount - 1 do TotalW := TotalW + UTF8Cols(Words[I]);
  Gaps  := WCount - 1;
  Extra := Width - TotalW - Gaps;  { spaces beyond the 1-per-gap minimum }
  R := Words[0];
  for I := 0 to Gaps - 1 do
    begin
      Base := Extra div Gaps;
      if I < (Extra mod Gaps) then Inc(Base);
      Gap := 1 + Base;  { at least one space }
      for K := 1 to Gap do R := R + ' ';
      R := R + Words[I + 1];
    end;
  Justify := R;
end;

procedure Draw(Col, Row, Fg, Bg: Integer; S: String);
var I, C, N: Integer; Ch: String[4];
begin
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
      BufPutCell(C, Row, Fg, Bg, Ch);
      Inc(I, N);
      Inc(C);
    end;
end;

procedure DrawHLine(X1, X2, Y, Fg, Bg: Integer; Ch: String);
var I: Integer;
begin
  for I := X1 to X2 do
    Draw(I, Y, Fg, Bg, Ch);
end;

{ Word-wrap Text and draw it justified at (Col, Row), one line per row.
  Every line except the last is stretched to Width cols with Justify.
  Returns the number of lines drawn. }
function DrawParagraph(const Text: String; Col, Row, Width, Fg, Bg: Integer): Integer;
var
  Lines: array[0..11] of String;
  N, I: Integer;
begin
  WordWrap(Text, Width, Lines, N);
  for I := 0 to N - 1 do
    begin
      if I < N - 1 then
        Draw(Col, Row, Fg, Bg, Justify(Lines[I], Width))
      else
        Draw(Col, Row, Fg, Bg, Lines[I]);
      Inc(Row);
    end;
  DrawParagraph := N;
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
  BufFill(FieldBg, FieldBg, ' ');
  DrawBorder;
  DrawKeys;
  DrawInner;
  BufFlush;
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
      BufFlush;
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
  BufFill(FieldBg, FieldBg, ' ');
  Draw(1, 2, Fg, Bg, Center(sHelpTitle));
  Draw(2, 4, Fg, Bg, sHelpArrows);
  Draw(2, 5, Fg, Bg, sHelpSpace);
  Draw(2, 6, Fg, Bg, sHelpP);
  Draw(2, 7, Fg, Bg, sHelpEsc);
  Draw(2, 8, Fg, Bg, sHelpF1);
  Draw(2, 9, Fg, Bg, sHelpF2);
  Draw(2, 10, Fg, Bg, sHelpF3);
  Draw(2, 11, Fg, Bg, sHelpF4);
  Draw(2, 12, Fg, Bg, sHelpF5);
  Draw(2, 13, Fg, Bg, sHelpEnd);
  Draw(2, 14, Fg, Bg, sHelpHome);
  Draw(1, 24, Fg, Bg, Center(sPressKey));
  BufFlush;
  WaitKey;
  X := SaveX;
  Y := SaveY;
end;

procedure ShowStory;
const
  Fg    = HelpFg;
  Bg    = FieldBg;
  TextW = 72;
  Col   = (FieldW - TextW) div 2 + 1;
begin
  BufFill(FieldBg, FieldBg, ' ');
  Draw(1, 2, Fg, Bg, Center(sStoryTitle));
  DrawParagraph(sStoryText, Col, 4, TextW, Fg, Bg);
  Draw(1, 24, Fg, Bg, Center(sPressKey));
  BufFlush;
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
  BufDesaturate;
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
  BufFlush;
  Dialog := WaitKey;
  DrawInner;
  BufFlush;
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
  FillScreen(Bg);
  BufFill(Bg, Bg, ' ');
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
  DrawParagraph(sItemInstText, 5, 18, 72, Fg, Bg);
  Draw(1, 24, Fg, Bg, Center(sPressKey));
  BufFlush;
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
  BufFill(FieldBg, FieldBg, ' ');
  ClrScr;
end;

{ Look up an environment variable; returns '' if unset. }
function GetEnvVar(const Name: String): String;
var P: PAnsiChar;
begin
  P := fpgetenv(PAnsiChar(Name));
  if P = nil then GetEnvVar := '' else GetEnvVar := P;
end;

{ Load locale .mo, probing in priority order (later wins):
    1. <ExeDir>translations/%s.mo                           — bundled alongside binary
    2. <XDG_DATA_DIRS dir>/locale/%s/LC_MESSAGES/UGLI_2.mo — system install
    3. <XDG_DATA_HOME>/locale/%s/LC_MESSAGES/UGLI_2.mo     — user install
  TranslateResourceStrings performs its own fileexists check internally and
  silently ignores missing files, so each call is a no-op when absent. }
procedure LoadTranslation;
var
  ExeDir, DataDirs, DataHome, Dir: String;
  I, J: Integer;
begin
  ExeDir := ParamStr(0);
  I := Length(ExeDir);
  while (I > 0) and (ExeDir[I] <> '/') do Dec(I);
  SetLength(ExeDir, I);

  TranslateResourceStrings(ExeDir + 'translations/%s.mo');

  DataDirs := GetEnvVar('XDG_DATA_DIRS');
  if DataDirs = '' then DataDirs := '/usr/local/share:/usr/share';
  I := 1;
  while I <= Length(DataDirs) do
    begin
      J := I;
      while (J <= Length(DataDirs)) and (DataDirs[J] <> ':') do Inc(J);
      Dir := Copy(DataDirs, I, J - I);
      if Dir <> '' then
        TranslateResourceStrings(Dir + '/locale/%s/LC_MESSAGES/UGLI_2.mo');
      I := J + 1;
    end;

  DataHome := GetEnvVar('XDG_DATA_HOME');
  if DataHome = '' then DataHome := GetEnvVar('HOME') + '/.local/share';
  if DataHome <> '' then
    TranslateResourceStrings(DataHome + '/locale/%s/LC_MESSAGES/UGLI_2.mo');
end;

procedure Init;
begin
  LoadTranslation;
  YesKey := [Ord(UpCase(sYesChar[1])), Ord(LowerCase(sYesChar)[1])];
  NoKey  := [Ord(UpCase(sNoChar[1])),  Ord(LowerCase(sNoChar)[1])];
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
  FillScreen(FieldBg);
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
