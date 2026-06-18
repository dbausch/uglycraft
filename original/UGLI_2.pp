{$H+}
program UGLI_2;

uses CThreads, DOS, BaseUnix, SysUtils, termio, gettext, getopts, UOSSound;

label NewGame, StartLevel, PlayAgain, OnGameOver, CleanUp;

const
  User = 'Public Domain';
  Version = '2.5';
  Release = '0043';
  FieldW = 80;
  FieldH = 20;
  ScreenW = FieldW;   { terminal width — buffer covers full 80-column line }
  ScreenH = 25;       { terminal height — game field (20) + key-help bar (5) }
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
  { Color constants (replaces CRT unit definitions) }
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

{$I UGLI_2_Core.inc}

var
  Tio: Termios;

begin
  LoadTranslation;
  ParseCLI;
  OpenLog(LogFile);
  Log('started UGLI 2 v' + Version + '/' + Release);
  Log('flags: skip-intro=' + BoolToStr(SkipIntro, 'true', 'false')
    + ' start-level=' + IntToStr(StartAtLevel));
  Assign(TTY, '/dev/tty');
  ReWrite(TTY);
  MyCursorOff;
  TTYFd    := fpOpen('/dev/tty', O_RDONLY);
  RawTTYFd := fpOpen('/dev/tty', O_WRONLY);
  tcgetattr(TTYFd, SavedTio);
  Tio := SavedTio;
  Tio.c_lflag := Tio.c_lflag and not (ICANON or ECHO or ISIG);
  Tio.c_cc[VMIN]  := 1;
  Tio.c_cc[VTIME] := 0;
  tcsetattr(TTYFd, TCSANOW, Tio);
  RawTio := Tio;
  Init;
  if DumpFile <> '' then
    begin
      DumpFd := fpOpen(DumpFile, O_WRONLY or O_CREAT or O_TRUNC, $1A4);
      BufFlushForce;
    end;
  Log('sound: ' + SoundBackendName);
NewGame:
  if StartAtLevel > 0 then Level := StartAtLevel else Level := 1;
  Score := 0;
  Lives := 10;
  ItemNo := 1;
  BlockX := 1;
  BlockY := 1;
  ItemX := 0;
  Log('new game: level=' + IntToStr(Level));
  PrepareLevel;
  LevelTransition;
StartLevel:
  EnemyTick := 0;
  RandomPos;
  repeat
    Sleep(MoveDelay);
    DrawItem;
    HandleInput;
    if KeyCode = KeyEscape then goto CleanUp;
    if KeyCode = KeyF4 then goto NewGame;
    if KeyCode = KeyF5 then RemoveBlocks;
    EnemyMove;
    if IsPlayerCaught then
      begin
        PlayerCaught;
        Log('caught at (' + IntToStr(EX) + ',' + IntToStr(EY) + ') lives='
          + IntToStr(Lives));
        if Lives = 0 then goto OnGameOver;
      end;
    if IsItemPickedUp then
      begin
        SoundPickup;
        AwardPoints;
        Log('item ' + IntToStr(ItemNo) + ': ' + GetItemName(ItemNo)
          + ' at (' + IntToStr(X) + ',' + IntToStr(Y) + ') score='
          + IntToStr(Score));
        ItemNo := ItemNo + 1;
        ItemX := 0;
        DrawItemName;
        if ItemNo = 10 then
          begin
            Level := Level + 1;
            if Level = 10 then
              begin
                Log('won: score=' + IntToStr(Score));
                WinScreen;
                goto PlayAgain;
              end;
            Log('level ' + IntToStr(Level - 1) + ' complete');
            LevelComplete;
          end;
        BufFlush;
        goto StartLevel;
      end;
    BufFlush;
  until KeyCode = KeyEscape;
OnGameOver:
  Log('game over: score=' + IntToStr(Score));
  GameOver;
PlayAgain:
  if AskPlayAgain then goto NewGame else goto CleanUp;
CleanUp:
  Log('exit');
  tcsetattr(TTYFd, TCSANOW, SavedTio);
  fpClose(TTYFd);
  if DumpFd >= 0 then fpClose(DumpFd);
  if LogFd >= 0 then fpClose(LogFd);
  fpClose(RawTTYFd);
  Write(TTY, #27'[0m'); Flush(TTY);
  Write(TTY, #27'[2J'#27'[H'); Flush(TTY);
  MyCursorOn;
  Close(TTY);
end.
