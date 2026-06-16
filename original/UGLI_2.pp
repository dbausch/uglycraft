{$H+}
program UGLI_2;

uses CThreads, DOS, BaseUnix, SysUtils, termio, gettext, UOSSound;

label NewGame, StartLevel, PlayAgain, OnGameOver, CleanUp;

const
  User = 'Public Domain';
  Version = '2.3';
  Release = '0042';
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
  Tio      : Termios;
  StderrLog: string;

begin
  LoadTranslation;
  for I := 1 to ParamCount do
    if (ParamStr(I) = '--help') or (ParamStr(I) = '-h') then
      ShowCLIHelp;
  StderrLog := '';
  for I := 1 to ParamCount do
    begin
      if (ParamStr(I) = '--stderr-log') and (I < ParamCount) then
        StderrLog := ParamStr(I + 1);
      if ParamStr(I) = '--skip-intro' then
        SkipIntro := true;
      if (ParamStr(I) = '--level') and (I < ParamCount) then
        begin
          StartAtLevel := StrToIntDef(ParamStr(I + 1), 1);
          if StartAtLevel < 1 then StartAtLevel := 1;
          if StartAtLevel > 9 then StartAtLevel := 9;
          SkipIntro := true;
          SkipItemDesc := true;
        end;
    end;
  InitStderrSink(StderrLog);
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
NewGame:
  Level := StartAtLevel;
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
    BufFlush;
  until KeyCode = KeyEscape;
OnGameOver:
  GameOver;
PlayAgain:
  if AskPlayAgain then goto NewGame else goto CleanUp;
CleanUp:
  tcsetattr(TTYFd, TCSANOW, SavedTio);
  fpClose(TTYFd);
  if DumpFd >= 0 then fpClose(DumpFd);
  fpClose(RawTTYFd);
  Write(TTY, #27'[0m'); Flush(TTY);
  Write(TTY, #27'[2J'#27'[H'); Flush(TTY);
  MyCursorOn;
  Close(TTY);
end.
