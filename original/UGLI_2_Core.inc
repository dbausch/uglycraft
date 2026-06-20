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
    (Ch: 'Φ'; Fg: Yellow),
    (Ch: '⚔'; Fg: Yellow),
    (Ch: '▼'; Fg: LightRed),
    (Ch: '⁂'; Fg: LightMagenta),
    (Ch: '♦'; Fg: LightCyan),
    (Ch: '≡'; Fg: LightGray),
    (Ch: '='; Fg: Yellow),
    (Ch: '🝁'; Fg: LightGray),
    (Ch: '⚑'; Fg: LightGreen),
    (Ch: '♛'; Fg: Yellow)
  );

var
  BlocksRemaining, MoveDelay, PausesRemaining, EnemyTick, KeyCode, I, J,
  ItemNo, Level, Lives, SaveX, SaveY, BlockX, BlockY, ItemX, ItemY, DX, DY, X,
  Y, EX, EY, StartX, StartY, StartEX, StartEY: Integer;
  Score: LongInt;
  Blocked: array[1..FieldW, 1..FieldH] of Boolean;
  Key: Char;
  Direction, StartDir: TDirection;
  Laying: Boolean;
  DirQueue: array[0..7] of TDirection;
  DirHead, DirTail: Integer;
  Screen          : TScreenBuffer;
  Dirty           : array[1..ScreenW, 1..ScreenH] of Boolean;
  BufFlushEnabled : Boolean = true;
  { When non-nil, WaitKey calls this instead of GetKey — set in tests. }
  KeyProviderFunc : function: Integer = nil;
  F, TTY: Text;
  FirstName, LastName, S: String;
  Line: String[80];
  YesKey, NoKey: set of Byte;
  TTYFd           : Integer;   { /dev/tty fd for raw key reads }
  SavedTio, RawTio: Termios;   { saved normal and raw terminal states }
  RawTTYFd        : cint = -1; { /dev/tty fd for single-write BufFlush }

const MaxWBufSize = 65536;

var
  WBuf: array[0..MaxWBufSize - 1] of Byte;
  WBufPos: Integer = 0;
  DumpFd  : cint   = -1;
  DumpFile: string = '';
  SkipIntro: Boolean = false;
  StartAtLevel: Integer = 0;  { 0 = not set via --level; 1-9 = explicit }
  LogFile: string = '';
  LogFd  : cint   = -1;

{ Open the log file (or /dev/null when FileName='') and route stderr (fd 2)
  there for the lifetime of the process.  When FileName is non-empty, keeps
  the fd open in LogFd so Log() can write structured entries alongside any
  ALSA/PortAudio noise that arrives on fd 2. }
procedure OpenLog(const FileName: string);
var Fd: cint;
begin
  if LogFd >= 0 then
    begin
      fpClose(LogFd);
      LogFd := -1;
    end;
  if FileName = '' then
    Fd := fpOpen('/dev/null', O_WRONLY)
  else
    Fd := fpOpen(FileName, O_WRONLY or O_CREAT or O_TRUNC, $1A4);
  if Fd >= 0 then
    begin
      fpDup2(Fd, 2);
      if FileName = '' then
        fpClose(Fd)
      else
        LogFd := Fd;
    end;
end;

{ Write a timestamped log line to the log file.  No-op when LogFd < 0. }
procedure Log(const Msg: string);
var S: AnsiString;
begin
  if LogFd < 0 then Exit;
  S := FormatDateTime('yyyy-mm-dd hh:nn:ss', Now) + '  ' + Msg + LineEnding;
  fpWrite(LogFd, S[1], Length(S));
end;

procedure WB(const S: AnsiString);
var I: Integer;
begin
  for I := 1 to Length(S) do
    begin WBuf[WBufPos] := Byte(S[I]); Inc(WBufPos); end;
end;

procedure WBCh(const S: ShortString);
var I: Integer;
begin
  for I := 1 to Length(S) do
    begin WBuf[WBufPos] := Byte(S[I]); Inc(WBufPos); end;
end;

procedure WBInt(N: Integer);
var S: String[12];
begin Str(N, S); WBCh(S); end;

procedure WBFlush;
var NullByte: Byte;
begin
  fpWrite(RawTTYFd, WBuf[0], WBufPos);
  if DumpFd >= 0 then
    begin
      fpWrite(DumpFd, WBuf[0], WBufPos);
      NullByte := 0;
      fpWrite(DumpFd, NullByte, 1);
    end;
  WBufPos := 0;
end;

procedure BufPutCell(Col, Row: Integer; Fg, Bg: Byte; const Ch: String); forward;
procedure BufFlush; forward;
procedure BufFlushForce; forward;

procedure ToggleDump;
const DumpFileName = '/tmp/ugli_dump.bin';
begin
  if DumpFd >= 0 then
    begin
      fpClose(DumpFd); DumpFd := -1;
      BufPutCell(ScreenW, ScreenH, Black, Black, ' ');
      BufFlush;
    end
  else
    begin
      DumpFd := fpOpen(DumpFileName, O_WRONLY or O_CREAT or O_TRUNC, $1A4);
      BufFlushForce;
    end;
end;

resourcestring
  { Item names — parallel to Items[1..10] }
  sItemName1  = 'Lamp';
  sItemName2  = 'Swords';
  sItemName3  = 'Ruby';
  sItemName4  = 'Gems';
  sItemName5  = 'Diamond';
  sItemName6  = 'Silver Bar';
  sItemName7  = 'Gold Bar';
  sItemName8  = 'Necklace';
  sItemName9  = 'Flag';
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
  sKeys2 = '<F1> = Help  <F2> = History of UGLI  <F3> = Buy life  <F4> = Restart';
  sKeys3 = '<P> = Pause  <End> = Slower  <Home> = Faster  <Esc> = Quit';
  { Help screen (ShowHelp) }
  sHelpTitle  = 'UGLI HELP';
  sHelpArrows = '[←/↓/→/↑]   Change direction';
  sHelpSpace  = '[Space]     Toggle block placement (on/off, costs 20 pts each)';
  sHelpP      = '[P]         Pause a short while (uses 1 pause)';
  sHelpEsc    = '[Esc]       Quit';
  sHelpF1     = '[F1]        This help screen';
  sHelpF2     = '[F2]        The history of UGLI';
  sHelpF3     = '[F3]        Buy a life (costs 5000 points)';
  sHelpF4     = '[F4]        Restart';
  sHelpF5     = '[F5]        Remove all placed blocks';
  sHelpEnd    = '[End]       Slower';
  sHelpHome   = '[Home]      Faster';
  { History screen (ShowStory) }
  sStoryTitle = 'The History of UGLI';
  sHistoryMissing = 'File not found.';
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
  { CLI help (--help / -h) }
  sCliUsage = 'Usage: UGLI_2 [options]';
  sCliOptions = 'Options:';
  sCliHelp = 'Show this help and exit.';
  sCliLog1 = 'Write a structured log (timestamp, version, flags, game events) to <file>.';
  sCliLog2 = 'Library diagnostic messages (ALSA/PortAudio) are also routed there.';
  sCliSkipIntro = 'Skip the animated intro; still shows the item-descriptions screen.';
  sCliLevel1 = 'Start directly at level N (1–9), skipping intro and item-descriptions screen.';
  sCliDump1  = 'Record every WBFlush write to <file> for rendering-artefact bisection.';
  sCliDump2  = 'Recording starts immediately; red ● appears at bottom-right while active.';

function CLIHelpText: string;
begin
  CLIHelpText :=
    'UGLI 2 v' + Version + LineEnding + LineEnding +
    sCliUsage + LineEnding + LineEnding +
    sCliOptions + LineEnding +
    '  -h, --help' + LineEnding +
    '      ' + sCliHelp + LineEnding +
    '  --skip-intro' + LineEnding +
    '      ' + sCliSkipIntro + LineEnding +
    '  --level <N>' + LineEnding +
    '      ' + sCliLevel1 + LineEnding +
    '  -l, --log <file>' + LineEnding +
    '      ' + sCliLog1 + LineEnding +
    '      ' + sCliLog2 + LineEnding +
    '  -d, --dump <file>' + LineEnding +
    '      ' + sCliDump1 + LineEnding +
    '      ' + sCliDump2 + LineEnding;
end;

procedure ShowCLIHelp;
begin
  Write(CLIHelpText);
  Halt(0);
end;

procedure ParseCLI;
var
  Opts: array[0..5] of TOption;
  C: Char;
  LongIndex: LongInt;
begin
  Opts[0].SetOption('help', No_Argument, nil, 'h');
  Opts[1].SetOption('skip-intro', No_Argument, nil, 's');
  Opts[2].SetOption('level', Required_Argument, nil, 'n');
  Opts[3].SetOption('log', Required_Argument, nil, 'l');
  Opts[4].SetOption('dump', Required_Argument, nil, 'd');
  Opts[5].SetOption('', No_Argument, nil, #0);
  OptErr := false;
  repeat
    C := GetLongOpts(':hl:d:', @Opts[0], LongIndex);
    case C of
      'h': ShowCLIHelp;
      's': SkipIntro := true;
      'n':
        begin
          StartAtLevel := StrToIntDef(OptArg, 1);
          if StartAtLevel < 1 then StartAtLevel := 1;
          if StartAtLevel > 9 then StartAtLevel := 9;
          SkipIntro := true;
        end;
      'l': LogFile := OptArg;
      'd': DumpFile := OptArg;
      '?', ':': ShowCLIHelp;
    end;
  until C = EndOfOptions;
end;

procedure MyCursorOn;
begin
  Write(TTY, #27'[?25h');
end;

procedure MyCursorOff;
begin
  Write(TTY, #27'[?25l');
end;

procedure FillScreen(Bg: Integer);
const AnsiClr: array[0..7] of Byte = (0, 4, 2, 6, 1, 5, 3, 7);
begin
  Write(TTY, #27'[', 40 + AnsiClr[Bg and 7], 'm');
  Write(TTY, #27'[2J'#27'[H');
  Flush(TTY);
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
{ CRT index → ANSI colour digit: same mapping as FPC CRT's AnsiTbl='04261537' }
const
  AnsiClr: array[0..7] of Byte = (0, 4, 2, 6, 1, 5, 3, 7);
var
  Col, Row, LastFg, LastBg, FgCode, BgCode, LastCol, LastRow: Integer;
begin
  if DumpFd >= 0 then
    BufPutCell(ScreenW, ScreenH, Red, Black, '●');
  if not BufFlushEnabled then
    begin
      for Col := 1 to ScreenW do
        for Row := 1 to ScreenH do
          Dirty[Col, Row] := false;
      Exit;
    end;
  WBufPos := 0;
  WB(#27'[?7l');
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
              WB(#27'[0;'); WBInt(FgCode); WB(';'); WBInt(BgCode); WB('m');
              LastFg := Screen[Col, Row].Fg;
              LastBg := Screen[Col, Row].Bg;
            end;
          if (Col <> LastCol + 1) or (Row <> LastRow) then
            begin WB(#27'['); WBInt(Row); WB(';'); WBInt(Col); WB('H'); end;
          WBCh(Screen[Col, Row].Ch);
          LastCol := Col;
          LastRow := Row;
          Dirty[Col, Row] := false;
        end;
  WB(#27'[?7h');
  WBFlush;
end;

procedure BufFlushForce;
var Col, Row: Integer;
begin
  for Col := 1 to ScreenW do
    for Row := 1 to ScreenH do
      Dirty[Col, Row] := true;
  BufFlush;
end;

procedure BufDesaturate;
var Col, Row: Integer;
begin
  for Col := 1 to ScreenW do
    for Row := 1 to ScreenH do
      begin
        if Screen[Col, Row].Fg <> White then Screen[Col, Row].Fg := LightGray;
        if Screen[Col, Row].Bg <> Black  then Screen[Col, Row].Bg := LightGray;
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
      if (Ord(S[I]) and $F8) = $F0 then N := 4
      else if (Ord(S[I]) and $F0) = $E0 then N := 3
      else if (Ord(S[I]) and $E0) = $C0 then N := 2
      else N := 1;
      Ch[0] := Chr(N);
      if N >= 1 then Ch[1] := S[I];
      if N >= 2 then Ch[2] := S[I + 1];
      if N >= 3 then Ch[3] := S[I + 2];
      if N >= 4 then Ch[4] := S[I + 3];
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

function KeyPressed: Boolean;
const
  FIONREAD = $541B;
var N: Integer;
begin
  N := 0;
  fpIoctl(TTYFd, FIONREAD, @N);
  KeyPressed := N > 0;
end;

{ Read one key press from /dev/tty; parse VT100 escape sequences and return
  the corresponding scan code (same values as the old CRT-based scan codes). }
function GetKey: Char;
var B, B2, B3, B4: Byte;

  function ReadB: Byte;
  var V: Byte;
  begin
    V := 0;
    fpRead(TTYFd, V, 1);
    ReadB := V;
  end;

begin
  B := ReadB;
  if B <> 27 then
    begin
      GetKey := Chr(B);
      Exit;
    end;
  { ESC — start of a terminal escape sequence }
  if not KeyPressed then
    begin
      GetKey := Chr(KeyEscape);
      Exit;
    end;
  B2 := ReadB;
  if B2 = Ord('[') then
    begin
      if not KeyPressed then begin GetKey := Chr(KeyEscape); Exit; end;
      B3 := ReadB;
      case B3 of
        Ord('A'): begin GetKey := Chr(KeyUp);     Exit; end;
        Ord('B'): begin GetKey := Chr(KeyDown);   Exit; end;
        Ord('C'): begin GetKey := Chr(KeyRight);  Exit; end;
        Ord('D'): begin GetKey := Chr(KeyLeft);   Exit; end;
        Ord('H'): begin GetKey := Chr(KeyFaster); Exit; end;
        Ord('F'): begin GetKey := Chr(KeySlower); Exit; end;
        Ord('['):  { Linux console: ESC [ [ X for F1–F5 }
          begin
            if KeyPressed then
              begin
                B4 := ReadB;
                case B4 of
                  Ord('A'): begin GetKey := Chr(KeyF1); Exit; end;
                  Ord('B'): begin GetKey := Chr(KeyF2); Exit; end;
                  Ord('C'): begin GetKey := Chr(KeyF3); Exit; end;
                  Ord('D'): begin GetKey := Chr(KeyF4); Exit; end;
                  Ord('E'): begin GetKey := Chr(KeyF5); Exit; end;
                else
                  GetKey := Chr(B4);
                end;
              end
            else
              GetKey := Chr(B3);
            Exit;
          end;
      else
        { Numeric sequence: ESC [ N ~ (e.g. ESC[11~ = F1) }
        if (B3 >= Ord('0')) and (B3 <= Ord('9')) then
          begin
            B4 := B3 - Ord('0');  { accumulate first digit }
            while KeyPressed do
              begin
                B3 := ReadB;
                if B3 = Ord('~') then Break;
                if (B3 >= Ord('0')) and (B3 <= Ord('9')) then
                  B4 := B4 * 10 + (B3 - Ord('0'));
              end;
            case B4 of
              1:  GetKey := Chr(KeyFaster); { Home }
              4:  GetKey := Chr(KeySlower); { End  }
              11: GetKey := Chr(KeyF1);
              12: GetKey := Chr(KeyF2);
              13: GetKey := Chr(KeyF3);
              14: GetKey := Chr(KeyF4);
              15: GetKey := Chr(KeyF5);
              17: GetKey := Chr(KeyF6);
            else
              GetKey := #0;
            end;
            Exit;
          end;
        GetKey := Chr(B3);
      end;
    end
  else if B2 = Ord('O') then
    begin
      { ESC O X for F1–F4 and Home/End on some terminals }
      if not KeyPressed then begin GetKey := Chr(KeyEscape); Exit; end;
      B3 := ReadB;
      case B3 of
        Ord('P'): begin GetKey := Chr(KeyF1);     Exit; end;
        Ord('Q'): begin GetKey := Chr(KeyF2);     Exit; end;
        Ord('R'): begin GetKey := Chr(KeyF3);     Exit; end;
        Ord('S'): begin GetKey := Chr(KeyF4);     Exit; end;
        Ord('H'): begin GetKey := Chr(KeyFaster); Exit; end;
        Ord('F'): begin GetKey := Chr(KeySlower); Exit; end;
      else
        GetKey := Chr(B3);
      end;
    end
  else
    GetKey := Chr(B2);
end;

function WaitKey: Integer;
begin
  if Assigned(KeyProviderFunc) then
    WaitKey := KeyProviderFunc()
  else
    WaitKey := Ord(GetKey);
end;

procedure Intro(Logo1, Logo2, Logo3, Logo4, Logo5, Logo6, Logo7, Logo8: String; Version: String;
  Release, User, CopyYear: String);
{ CRT index → ANSI colour digit: same mapping as FPC CRT AnsiTbl='04261537' }
const AnsiClr: array[0..7] of Byte = (0, 4, 2, 6, 1, 5, 3, 7);
var I: Integer;
  ITTY: Text;

{ Emit a foreground color SGR code to ITTY (Fg 0-15). }
procedure SetFg(Fg: Integer);
var Code: Integer;
begin
  if (Fg and $7F) >= 8 then
    Code := 90 + AnsiClr[(Fg and $7F) - 8]
  else
    Code := 30 + AnsiClr[Fg and 7];
  if (Fg and Blink) <> 0 then
    Write(ITTY, #27'[5;', Code, 'm')
  else
    Write(ITTY, #27'[', Code, 'm');
end;

{ Emit a background color SGR code to ITTY (Bg 0-7). }
procedure SetBg(Bg: Integer);
begin
  Write(ITTY, #27'[', 40 + AnsiClr[Bg and 7], 'm');
end;

{ Write S with erase-to-EOL and advance to the next line. }
procedure WLn(S: String);
begin
  if S = '' then Write(ITTY, ' ') else Write(ITTY, S);
  Write(ITTY, #27'[K'#13#10#27'[K');
  Flush(ITTY);
end;

begin
  Assign(ITTY, '/dev/tty');
  ReWrite(ITTY);
  Write(ITTY, #27'[1;25r'); { confine scrolling to rows 1-25 }
  Flush(ITTY);
  for I := 0 to 7 do
    begin
      SetBg(I);
      Write(ITTY, #27'[2J'#27'[H');
      Flush(ITTY);
      Beep(I * 150, 300);
      Sleep(20);
    end;
  Sleep(100);
  Write(ITTY, #27'[0;30;40m'#27'[1;1H');   { Black on Black, home }
  SetFg(7);                                 { Light gray fg }
  for I := 1 to 25 do
    begin
      Sleep(200);
      Write(ITTY, #27'[', I, ';1H'#27'[K');
      Write(ITTY, '                        |                            |');
      Flush(ITTY);
    end;
  Write(ITTY, #27'[0;30;47m'#27'[25;1H');  { Black fg, LightGray bg, row 25 }
  Flush(ITTY);
  Sleep(200);
  WLn('');
  Sleep(200);
  WLn(Center(sIntroBrand));
  Sleep(200);
  WLn('');
  Sleep(200);
  WLn('');
  Write(ITTY, #27'[0;47m'); SetFg(Red + Blink); { blink red on LightGray }
  Flush(ITTY);
  Sleep(200);
  WLn(Logo1);
  Sleep(200);
  WLn(Logo2);
  Sleep(200);
  WLn(Logo3);
  Sleep(200);
  WLn(Logo4);
  Sleep(200);
  WLn(Logo5);
  Sleep(200);
  WLn(Logo6);
  Sleep(200);
  WLn(Logo7);
  Sleep(200);
  WLn(Logo8);
  Sleep(200);
  WLn('');
  Sleep(200);
  Write(ITTY, #27'[0;47m'); SetFg(Black + Blink); { blink black on LightGray }
  Flush(ITTY);
  WLn('');
  Sleep(200);
  WLn(Center(sIntroWelcome));
  Sleep(200);
  WLn('');
  Write(ITTY, #27'[0;30;47m'); { Black fg, bright-white bg, blink off }
  Flush(ITTY);
  Sleep(200);
  WLn(Center(User));
  Sleep(200);
  WLn('');
  Sleep(200);
  WLn(Center('Version: ' + Version + '/' + Release));
  Sleep(200);
  WLn('');
  Sleep(200);
  WLn(Center(CopyYear));
  Sleep(200);
  WLn('');
  Sleep(200);
  WLn('');
  Sleep(200);
  SetFg(Red);
  Flush(ITTY);
  Write(ITTY, Center(sPressKey));
  WLn('');
  WaitKey;
  Write(ITTY, #27'[2J'#27'[H');
  for I := 40 to 50 do
    Beep(I, 150);
  Write(ITTY, #27'[r'); { reset scroll region }
  Flush(ITTY);
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
  DirHead := 0; DirTail := 0;
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
      begin
        if (OldEX = ItemX) and (OldEY = ItemY) then
          DrawItem
        else
          Draw(OldEX, OldEY, FieldBg, FieldBg, ' ');
      end;
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
      Sleep(5000);
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
  Draw(5, 4, Fg, Bg, sHelpArrows);
  Draw(5, 5, Fg, Bg, sHelpSpace);
  Draw(5, 6, Fg, Bg, sHelpP);
  Draw(5, 7, Fg, Bg, sHelpEsc);
  Draw(5, 8, Fg, Bg, sHelpF1);
  Draw(5, 9, Fg, Bg, sHelpF2);
  Draw(5, 10, Fg, Bg, sHelpF3);
  Draw(5, 11, Fg, Bg, sHelpF4);
  Draw(5, 12, Fg, Bg, sHelpF5);
  Draw(5, 13, Fg, Bg, sHelpEnd);
  Draw(5, 14, Fg, Bg, sHelpHome);
  Draw(1, 24, Fg, Bg, Center(sPressKey));
  BufFlush;
  WaitKey;
  X := SaveX;
  Y := SaveY;
end;

function LoadHistoryText: String;
var
  ExeDir, Lang, FallbackLang, Path: String;
  F: Text;
  Line, Buf: String;
  Len: Integer;
begin
  ExeDir := ParamStr(0);
  Len := Length(ExeDir);
  while (Len > 0) and (ExeDir[Len] <> '/') do Dec(Len);
  SetLength(ExeDir, Len);

  GetLanguageIDs(Lang, FallbackLang);
  if Length(Lang) >= 2 then
    SetLength(Lang, 2)
  else
    Lang := 'en';

  Path := ExeDir + 'translations/history_' + Lang + '.txt';
  {$I-}
  Assign(F, Path);
  Reset(F);
  if IOResult <> 0 then
  begin
    Path := ExeDir + 'translations/history_en.txt';
    Assign(F, Path);
    Reset(F);
    if IOResult <> 0 then
    begin
      LoadHistoryText := sHistoryMissing;
      Exit;
    end;
  end;
  Buf := '';
  while not Eof(F) do
  begin
    ReadLn(F, Line);
    if Buf <> '' then
      Buf := Buf + LineEnding;
    Buf := Buf + Line;
  end;
  Close(F);
  {$I+}
  LoadHistoryText := Buf;
end;

procedure ShowStory;
const
  Fg    = HelpFg;
  Bg    = FieldBg;
  TextW = 72;
  Col   = (FieldW - TextW) div 2 + 1;
var
  HistoryText, Para: String;
  Row, P, Start: Integer;
begin
  BufFill(FieldBg, FieldBg, ' ');
  Draw(1, 2, Fg, Bg, Center(sStoryTitle));
  HistoryText := LoadHistoryText;
  Row := 4;
  Start := 1;
  P := 1;
  while P <= Length(HistoryText) do
  begin
    if (P < Length(HistoryText)) and (HistoryText[P] = #10) and (HistoryText[P + 1] = #10) then
    begin
      Para := Copy(HistoryText, Start, P - Start);
      Row := Row + DrawParagraph(Para, Col, Row, TextW, Fg, Bg) + 1;
      P := P + 2;
      Start := P;
    end
    else
      Inc(P);
  end;
  if Start <= Length(HistoryText) then
  begin
    Para := Copy(HistoryText, Start, Length(HistoryText) - Start + 1);
    DrawParagraph(Para, Col, Row, TextW, Fg, Bg);
  end;
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
  Redraw;
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

procedure DirEnqueue(D: TDirection);
var Prev: Integer;
begin
  if DirHead <> DirTail then
  begin
    Prev := (DirTail - 1) and 7;
    if DirQueue[Prev] = D then Exit;
  end;
  DirQueue[DirTail] := D;
  DirTail := (DirTail + 1) and 7;
  if DirTail = DirHead then
    DirHead := (DirHead + 1) and 7;
end;

function DirDequeue: Boolean;
begin
  if DirHead = DirTail then
  begin
    DirDequeue := false;
    Exit;
  end;
  Direction := DirQueue[DirHead];
  DirHead := (DirHead + 1) and 7;
  DirDequeue := true;
end;

procedure DirFlush;
begin
  DirHead := DirTail;
end;

procedure MovePlayer;
begin
  DirDequeue;
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
  Sleep(1000);
end;

procedure HandleInput;
begin
  KeyCode := 0;
  while KeyPressed do
  begin
    Key := GetKey;
    KeyCode := Ord(Key);
    case KeyCode of
      KeyRight, KeyLeft, KeyUp, KeyDown: DirEnqueue(KeyToDir(KeyCode));
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
          DirFlush;
          ShowHelp;
          Redraw;
          Break;
        end;
      KeyF2:
        begin
          DirFlush;
          ShowStory;
          Redraw;
          Break;
        end;
      KeyF6: ToggleDump;
      KeyEscape, KeyF4, KeyF5:
        begin
          DirFlush;
          Break;
        end;
    end; {case}
  end;
  EnemyTick := (EnemyTick + 1) mod 2;
  MovePlayer;
  if Laying then PlaceBlock;
  Draw(X, Y, PlayerFg, FieldBg, '☺');
end;

procedure HighScoreEntry;
begin
  { Restore cooked mode so ReadLn works }
  tcsetattr(TTYFd, TCSANOW, SavedTio);
  MyCursorOn;
  { LightBlue on Black }
  Write(TTY, #27'[0;94;40m'#27'[2J'#27'[H'); Flush(TTY);
  WriteLn;
  WriteLn(sFirstName);
  Write(TTY, #27'[2;', UTF8Cols(sFirstName) + 1, 'H'); Flush(TTY);
  ReadLn(FirstName);
  WriteLn(sLastName);
  Write(TTY, #27'[3;', UTF8Cols(sLastName) + 1, 'H'); Flush(TTY);
  ReadLn(LastName);
  MyCursorOff;
  Str(Score * Lives, S); Draw(1, 4, CounterFg, FieldBg, sScoreEntry + S);
  Assign(F, HighScoreFileName);
  {$I-}
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
  {$I+}
  Write(TTY, #27'[2J'#27'[H'); Flush(TTY);
  Assign(F, HighScoreFileName);
  {$I-}
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
  {$I+}
  Write(TTY, #27'[25;1H'); Flush(TTY);
  Write(sPressKey);
  { Re-enable raw mode before returning to game }
  tcsetattr(TTYFd, TCSANOW, RawTio);
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
  Write(TTY, #27'[2J'#27'[H'); Flush(TTY);
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
  if not SkipIntro then
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
  if StartAtLevel = 0 then
    ShowItemDescriptions;
  FillScreen(FieldBg);
  MoveDelay := 100;
  PausesRemaining := 20;
  BlocksRemaining := 2000;
  Laying := false;
  InitBorder;
end;

procedure FlashField;
var Col, Row: Integer;
begin
  for Col := 1 to FieldW do
    for Row := 1 to FieldH do
      BufPutCell(Col, Row, Red, Red, ' ');
  BufFlush;
end;

procedure PlayerCaught;
begin
  SoundCaught;
  FlashField;
  Sleep(200);
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
