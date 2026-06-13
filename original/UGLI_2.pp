program UGLI_2;

uses CThreads, CRT, DOS, DANISOFT, UOSSound;

label GameLoop, NewGame, NextItem, PlayAgain, OnGameOver, CleanUp;

const
  User = 'Public Domain';
  Version = '2.1';
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

var
  BlocksRemaining, MoveDelay, Code, PausesRemaining, EnemyTick, KeyCode, I, J,
  ItemNo, Level, Lives, SaveX, SaveY, BlockX, BlockY, ItemX, ItemY, DX, DY, X,
  Y, EX, EY, EscState: Integer;
  Score: LongInt;
  Blocked: array[1..FieldW, 1..FieldH] of Boolean;
  Key, Direction: Char;
  Laying: Boolean;
  F, TTY: Text;
  FirstName, LastName, S: String;
  Line: String[80];

procedure MyCursorOn;
begin
  Write(TTY, #27'[?25h');
end;

procedure MyCursorOff;
begin
  Write(TTY, #27'[?25l');
end;

procedure WriteXY(Col, Row: Integer; S: String);
var I, C, N: Integer; Ch: String;
begin
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
  Flush(TTY); { drain buffer before CRT sync — prevents a
                deferred tty flush from displacing the cursor
                between gotoxy(c,row) and the caller's write() }
  GotoXY(1, 1);
  GotoXY(C, Row); { sync CRT's position tracker }
end;

procedure WriteLevel;
var S: String;
begin
  TextBackground(Red);
  TextColor(15);
  Str(Level, S);
  WriteXY(36, 1, 'LEVEL ' + S);
end;

procedure DrawHLine(X1, X2, Y: Integer; Ch: String);
var I: Integer;
begin
  for I := X1 to X2 do
    WriteXY(I, Y, Ch);
end;

procedure DrawInner;
var
  I, J: Integer;
  C: String;
begin
  TextColor(Red);
  for I := 2 to 79 do
    begin
      for J := 2 to 19 do
        begin
          if Blocked[I, J] then
            C := '█'
          else
            C := ' ';
          WriteXY(I, J, C);
        end;
    end;
end;

procedure HighScoreEntry;
begin
  ClrScr;
  WriteLn;
  WriteLn('VORNAME ');
  MyCursorOn;
  GotoXY(9, 2); ReadLn(FirstName);
  WriteLn('NAME ');
  GotoXY(6, 3); ReadLn(LastName);
  MyCursorOff;
  Str(Score * Lives, S); WriteXY(1, 4, 'Punkte ' + S);
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
          WriteLn('Datei UGLI.HSC konnte nicht erzeugt werden.');
        end
      else
        begin
          WriteLn(F, FirstName, ' ', LastName, '    ', Score * Lives);
          Close(F);
          WriteLn;
        end;
    end;
  ReadLn;
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
          WriteLn('Datei ' + HighScoreFileName + ' konnte nicht erzeugt werden.');
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
  Write('Bitte [Return]-Taste drücken...');
  ReadLn;
end;

procedure ShowIntro;
begin
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
end;

procedure DrawScore;
var S: String;
begin
  TextBackground(Red);
  TextColor(15);
  Str(Score, S);
  WriteXY(3, 1, 'PUNKTE ' + S);
  TextBackground(0);
end; {DrawScore}

procedure DrawLives;
var S: String;
begin
  TextBackground(LightRed);
  TextColor(15);
  Str(Lives, S);
  WriteXY(3, 20, 'LEBEN ' + S);
  TextBackground(0);
end; {DrawLives}

procedure DrawPauses;
var S: String;
begin
  TextBackground(Red);
  TextColor(15);
  Str(PausesRemaining:2, S);
  WriteXY(70, 1, 'PAUSEN ' + S);
  TextBackground(0);
end; {DrawPauses}

procedure DrawBlocks;
var S: String;
begin
  TextBackground(LightRed);
  TextColor(15);
  Str(BlocksRemaining:4, S);
  WriteXY(68, 20, 'STEINE ' + S);
  TextBackground(0);
end; {DrawBlocks}

procedure AwardPoints;
begin
  Score := Score + (ItemNo - 1) * 100;
  DrawScore;
end;

procedure InitLevel1;
begin
  X := 40;
  Y := 10;
  Key := Chr(KeyRight);
end; {InitLevel1}

procedure InitLevel2;
var
  I: Integer;
begin
  for I := 18 to 62 do
    begin
      Blocked[I, 10] := true;
    end;
  X := 40;
  Y := 5;
  Key := Chr(KeyRight);
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
  X := 40;
  Y := 9;
  Key := Chr(KeyUp);
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
  for I := 5 to 75 do
    Blocked[I, 10] := true;
  for I := 12 to 16 do
    begin
      Blocked[15, I] := true;
      Blocked[65, I] := true;
    end;
  Blocked[39, 10] := false;
  Blocked[40, 10] := false;
  Blocked[41, 10] := false;
  X := 40;
  Y := 9;
  Key := Chr(KeyRight);
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
  X := 40;
  Y := 10;
  Key := Chr(KeyUp);
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
  X := 75;
  Y := 5;
  Key := Chr(KeyDown);
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
  X := 75;
  Y := 10;
  Key := Chr(KeyRight);
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
  X := 75;
  Y := 5;
  Key := Chr(KeyDown);
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
  X := 40;
  Y := 10;
  Key := Chr(KeyUp);
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
  Direction := Key;
  DrawInner;
end; {InitLevel}

procedure ShowItemDescriptions;
begin
  ClrScr;
  WriteLn;
  WriteLn(' L I S T E   D E R   E I N Z U S A M M E L N D E N   S C H Ä T Z E ');
  WriteLn;
  WriteLn('    | Seil ');
  WriteLn('    ☼ grosser glänzender Diamant ');
  WriteLn('    : kleine Edelsteiene ');
  WriteLn('    * kleiner glänzender Diamant ');
  WriteLn('    = Goldbarren ');
  WriteLn('    ≡ Silberbarren ');
  WriteLn('    Γ Brunnen ');
  WriteLn('    Φ Lampe ');
  WriteLn('    ♦ grosser Edelstein ');
  WriteLn('    ⌂ Krone ');
  WriteLn;
  GotoXY(1, 15);
  WriteLn('   S P I E L A N L E I T U N G   ');
  WriteLn;
  WriteLn('Du drückst jetzt die Return-Taste(Enter), dann drückst du eine der ');
  WriteLn('Richtungstasten danach musst du mit den Richtungstasten die oben gezeigten ');
  WriteLn('Dinge einsammeln.       (Die Krone kommt ganz zum Schluss.)');
  WriteLn('Während des Spiels kann man mit <F1> die anderen Tasten die zum bedienen ');
  WriteLn('des Spiels nachlesen.');
  ReadLn;
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

procedure ShowHelp;
begin
  SaveX := X;
  SaveY := Y;
  TextColor(13);
  ClrScr;
  WriteXY(2, 1, '                  HILFE VON UGLI');
  WriteXY(2, 2, '[p] = Pause (1 Pause Weniger)');
  WriteXY(2, 3, 'Bewegungs-Tasten: ← = links  ↓ = unten  → = rechts  ↑ = oben');
  WriteXY(2, 4, '[Esc] = Abbruch');
  WriteXY(2, 5, '[Ende] = Langsamer');
  WriteXY(2, 6, '[Pos1] = Schneller');
  WriteXY(2, 7, '[F4] = Neustart');
  WriteXY(2, 8, '[F3] = Leben kaufen (Kostet 5000 Punkte)');
  WriteXY(2, 9, '[F2] = Die Geschichte von Ugli');
  WriteXY(2, 10, '[Space] = Blöcke legen umschalten (an/aus, kostet je 20 Punkte)');
  WriteXY(2, 11, '[F5] = Alle gesetzten Blöcke wieder entfernen');
  WriteXY(2, 12, '[F1] = Diese Hilfe');
  WriteXY(2, 15, '                  T A S T E   D R Ü C K E N');
  Key := GetKey;
  X := SaveX;
  Y := SaveY;
end;

procedure LevelTransition;
var UserDir: Char;
begin
  UserDir := #0;
  begin
    repeat
      DrawHLine(27, 53, 8, '█');
      WriteXY(27, 9, '█');
      Str(Level, S);
      WriteXY(28, 9, ' L E V E L   ' + S + '           ');
      WriteXY(53, 9, '█');
      DrawHLine(27, 53, 10, '█');
      WriteXY(27, 11, ' T A S T E   D R Ü C K E N ');
      Delay(1000);
    until KeyPressed;
    Key := GetKey;
    if Key in [Chr(KeyRight), Chr(KeyLeft), Chr(KeyUp), Chr(KeyDown)] then
      UserDir := Key;
    WriteXY(27, 8, '                           ');
    WriteXY(27, 9, '                           ');
    WriteXY(27, 10, '                           ');
    WriteXY(27, 11, '                           ');
  end;
  InitLevel(Level);
  if UserDir <> #0 then Direction := UserDir;
  Delay(1000);
end;

procedure BumpSound;
begin
  SoundBump;
end; {BumpSound}

procedure MoveDown(var X: Integer; var Y: Integer);
var OldY: Integer;
begin
  OldY := Y;
  if Blocked[X, Y + 1] then BumpSound
  else Y := Y + 1;
  if Y <> OldY then
    begin
      WriteXY(X, OldY, ' ');
      TextColor(14);
      WriteXY(X, Y, '☺');
    end;
  GotoXY(1, 1);
  TextColor(4);
  WriteXY(BlockX, BlockY, '█');
end; {MoveDown}

procedure MoveLeft(var X: Integer; var Y: Integer);
var OldX: Integer;
begin
  OldX := X;
  if Blocked[X - 1, Y] then BumpSound
  else X := X - 1;
  if X <> OldX then
    begin
      WriteXY(OldX, Y, ' ');
      TextColor(14);
      WriteXY(X, Y, '☺');
    end;
  GotoXY(1, 1);
  TextColor(4);
  WriteXY(BlockX, BlockY, '█');
end; {MoveLeft}

procedure MoveRight(var X: Integer; var Y: Integer);
var OldX: Integer;
begin
  OldX := X;
  if Blocked[X + 1, Y] then BumpSound
  else X := X + 1;
  if X <> OldX then
    begin
      WriteXY(OldX, Y, ' ');
      TextColor(14);
      WriteXY(X, Y, '☺');
    end;
  GotoXY(1, 1);
  TextColor(4);
  WriteXY(BlockX, BlockY, '█');
end; {MoveRight}

procedure MoveUp(var X: Integer; var Y: Integer);
var OldY: Integer;
begin
  OldY := Y;
  if Blocked[X, Y - 1] then BumpSound
  else Y := Y - 1;
  if Y <> OldY then
    begin
      WriteXY(X, OldY, ' ');
      TextColor(14);
      WriteXY(X, Y, '☺');
    end;
  GotoXY(1, 1);
  TextColor(4);
  WriteXY(BlockX, BlockY, '█');
end; {MoveUp}

procedure DrawKeys;
begin
  TextColor(11);
  WriteXY(1, 21, '← = links  ↓ = unten  → = rechts  ↑ = oben');
  DrawHLine(1, 80, 22, '─');
  WriteXY(1, 23, '<F1> = Hilfe  <F2> = Geschichte von UGLI  <F3> = Leben kaufen  <F4> = Neustart');
  DrawHLine(1, 80, 24, '─');
  WriteXY(1, 25, '<P> = Pause  <Ende> = Langsamer  <Pos1> = Schneller  <Esc> = Ende');
end; {DrawKeys}

procedure DrawFrame;
var I, J: Integer;
begin
  TextColor(4);
  for I := 1 to FieldW do
    begin
      for J := 1 to FieldH do
        begin
          Blocked[I, J] := false;
        end; {for J}
    end; {for I}
  ClrScr;
  for I := 1 to 80 do
    begin
      TextColor(4);
      WriteXY(I, 1, '█');
      TextColor(4);
      WriteXY(I, 20, '█');
      Blocked[I, 1] := true;
      Blocked[I, 20] := true;
    end; {for}
  for I := 2 to 19 do
    begin
      TextColor(4);
      WriteXY(1, I, '█');
      TextColor(4);
      WriteXY(80, I, '█');
      Blocked[1, I] := true;
      Blocked[80, I] := true;
    end; {for}
  WriteLevel;
  DrawScore;
  DrawLives;
  DrawPauses;
  DrawBlocks;
  TextBackground(0);
  InitLevel(Level);
  DrawKeys;
end; {DrawFrame}

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
        WriteXY(OldEX, OldEY, ' ');
      TextColor(6);
      WriteXY(EX, EY, '☻');
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

procedure ShowStory;
begin
  TextColor(13);
  ClrScr;
  WriteXY(3, 1, '                Geschichte von UGLI');
  WriteXY(3, 3, 'Du  bist  von  einem  König  in  eine  Burg eingeschlossen worden.');
  WriteXY(3, 4, 'Mit  den  Worten: "Ich lasse  Dich  erst wieder frei, wenn Du alle');
  WriteXY(3, 5, 'meine  Schätze  wieder  gefunden  hast", knallte  er  die  Tür zu.');
  WriteXY(3, 6, 'Da  bleibt Dir wohl  nichts anderes  mehr übrig, als seine Schätze');
  WriteXY(3, 7, 'zu holen. Du rennst also sofort los, um alle Schätze einzusammeln.');
  WriteXY(3, 9, '                 T A S T E   D R Ü C K E N');
  Key := GetKey;
end;

procedure SlowDown;
begin
  MoveDelay := MoveDelay + 1;
end;

procedure SpeedUp;
begin
  if MoveDelay > 0 then MoveDelay := MoveDelay - 1;
end;

procedure GameOver;
begin
  WriteXY(EX, EY, ' ');
  WriteXY(X, Y, ' ');
  WriteXY(ItemX, ItemY, ' ');
  DrawHLine(28, 49, 2, '█');
  WriteXY(28, 3, '██ G A M E  O V E R ██');
  DrawHLine(28, 49, 4, '█');
  SoundGameOver;
end;

procedure WinScreen;
begin
  TextColor(12 + Blink);
  DrawHLine(30, 56, 8, '█');
  WriteXY(30, 9, '██    G E W O N N E N    ██');
  DrawHLine(30, 56, 10, '█');
  TextColor(4);
  WriteXY(30, 11, ' T A S T E   D R Ü C K E N ');
  Delay(1000);
  SoundWon;
  TextBackground(Black);
  TextColor(Random(255));
  TextAttr := Random(255);
  TextBackground(1);
  ClrScr;
  while KeyPressed do Key := GetKey;
  Key := #0;
  repeat
    begin
      TextAttr := Random(255);
      if KeyPressed then
        begin
          Key := GetKey;
          Code := Ord(Key);
        end;
      Write('*');
      Delay(10);
    end;
  until Code > 0;
  TextBackground(Black);
  TextColor(9);
  HighScoreEntry;
  ClrScr;
end;

procedure Init;
begin
  Randomize;
  ShowIntro;
  ShowItemDescriptions;
  TextBackground(0);
  TextColor(4);
  ClrScr;
  MoveDelay := 100;
  PausesRemaining := 20;
  BlockX := 1;
  BlockY := 1;
  EX := 5;
  EY := 10;
  X := 40;
  Y := 10;
  BlocksRemaining := 2000;
  Score := 0;
  Lives := 9;
  Level := 0;
  ItemNo := 9;
  Laying := false;
end;

procedure PlayerCaught;
begin
  DrawFrame;
  SoundCaught;
  Score := Score - ItemNo * 1000;
  if Score < 0 then Score := 0;
  ItemNo := 1;
  Lives := Lives - 1;
  BlockX := 1;
  BlockY := 1;
end;

procedure DrawItem;
begin
  TextColor(2);
  if ItemNo = 1 then
    begin
      TextBackground(Black);
      TextColor(Brown);
      WriteXY(ItemX, ItemY, '|');
    end;
  if ItemNo = 2 then
    begin
      TextBackground(Black);
      TextColor(LightBlue);
      WriteXY(ItemX, ItemY, '☼');
    end;
  if ItemNo = 3 then
    begin
      TextColor(LightRed);
      TextBackground(Black);
      WriteXY(ItemX, ItemY, ':');
    end;
  if ItemNo = 4 then
    begin
      TextBackground(Black);
      TextColor(LightBlue);
      WriteXY(ItemX, ItemY, '*');
    end;
  if ItemNo = 5 then
    begin
      TextColor(Yellow);
      WriteXY(ItemX, ItemY, '=');
    end;
  if ItemNo = 6 then
    begin
      TextColor(LightGray);
      WriteXY(ItemX, ItemY, '≡');
    end;
  if ItemNo = 7 then
    begin
      TextColor(Cyan);
      WriteXY(ItemX, ItemY, 'Γ');
    end;
  if ItemNo = 8 then
    begin
      TextColor(Yellow);
      WriteXY(ItemX, ItemY, 'Φ');
    end;
  if ItemNo = 9 then
    begin
      TextColor(LightGreen);
      WriteXY(ItemX, ItemY, '♦');
    end;
  if (ItemNo = 9) and (Level = 9) then
    begin
      TextColor(Yellow);
      WriteXY(ItemX, ItemY, '⌂');
    end;
  TextBackground(Black);
end;

procedure RandomPos;
begin
  repeat
    ItemX := Round((Random * 77) + 2);
    ItemY := Round((Random * 17) + 2);
  until not Blocked[ItemX, ItemY];
end;


procedure PlaceBlock; forward;

procedure HandleInput;
begin
  KeyCode := 0;
  if KeyPressed then
    begin
      Key := GetKey;
      KeyCode := Ord(Key);
      case KeyCode of
        KeyRight, KeyLeft, KeyUp, KeyDown: Direction := Key;
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
            TextColor(6);
            ShowHelp;
            DrawFrame;
            DrawInner;
          end;
        KeyF2:
          begin
            ShowStory;
            DrawFrame;
            DrawInner;
          end;
      end; {case}
    end;
  EnemyTick := (EnemyTick + 1) mod 2;
  GotoXY(1, 1);
  case Ord(Direction) of
    KeyRight: MoveRight(X, Y);
    KeyLeft: MoveLeft(X, Y);
    KeyUp: MoveUp(X, Y);
    KeyDown: MoveDown(X, Y);
  end; {case}
  if Laying then PlaceBlock;
  TextColor(14);
  WriteXY(X, Y, '☺');
end;

procedure PlaceBlock;
begin
  if (BlocksRemaining = 0) or (Score < 20) then
    Laying := false
  else if not Blocked[X, Y] then
    begin
      TextColor(4);
      WriteXY(X, Y, '█');
      Blocked[X, Y] := true;
      BlockX := X;
      BlockY := Y;
      Score := Score - 20;
      BlocksRemaining := BlocksRemaining - 1;
      DrawBlocks;
      DrawScore;
    end;
end;

procedure RemoveBlocks;
begin
  WriteXY(3, 3, '╔═══════════════════════════════════╗');
  WriteXY(3, 4, '║   S T E I N E  ═══  N E H M E N   ║');
  WriteXY(3, 5, '╟───────────────────────────────────╢');
  WriteXY(3, 6, '║Wirklich Alle Steine entfernen(J/N)║');
  WriteXY(3, 7, '║                                   ║');
  WriteXY(3, 8, '╚═══════════════════════════════════╝');
  GotoXY(7, 7); Key := UpCase(GetKey);
  DrawInner;
  SaveX := X;
  SaveY := Y;
  if Score >= 20 then
    begin
      case Key of
        'J':
          begin
            for I := 1 to 80 do
              for J := 1 to 25 do
                begin
                  Blocked[I, J] := false;
                end;
            TextColor(4);
            TextBackground(0);
            InitLevel(Level);
            BlockX := 1;
            BlockY := 1;
          end;
      end;
    end;
  if Score > 0 then Score := Score - 20;
  WriteXY(3, 9, 'TASTE DRÜCKEN');
  Key := GetKey;
  for I := 1 to 80 do
    begin
      TextColor(4);
      WriteXY(I, 1, '█');
      TextColor(4);
      WriteXY(I, 20, '█');
      Blocked[I, 1] := true;
      Blocked[I, 20] := true;
    end; {for}
  for I := 2 to 19 do
    begin
      TextColor(4);
      WriteXY(1, I, '█');
      TextColor(4);
      WriteXY(80, I, '█');
      Blocked[1, I] := true;
      Blocked[80, I] := true;
    end; {for}
  WriteLevel;
  TextBackground(0);
  DrawInner;
  X := SaveX;
  Y := SaveY;
  LastName := '';
end;

begin
  Assign(TTY, '/dev/tty');
  ReWrite(TTY);
  MyCursorOff;
  repeat
GameLoop:
    Init;
NewGame:
    Level := 0;
    ItemNo := 9;
    Lives := 9;
NextItem:
    EnemyTick := 0;
    ItemNo := ItemNo + 1;
    AwardPoints;
    if ItemNo = 10 then
      begin
        ItemNo := 1;
        Level := Level + 1;
        BlockX := 1;
        BlockY := 1;
        if Level = 1 then
          begin
            Score := 0;
          end;
        EX := 5; {Enemy X}
        EY := 10; {Enemy Y}
        if Level = 10 then
          begin
            WinScreen;
            goto PlayAgain;
          end;
        DrawFrame;
        Lives := Lives + 1;
        LevelTransition;
      end; {if ItemNo = 10}
    RandomPos;
    repeat
      Delay(MoveDelay);
      DrawItem;
      TextColor(4);
      HandleInput;
      if KeyCode = KeyEscape then goto CleanUp;
      if KeyCode = KeyF4 then goto NewGame;
      if KeyCode = KeyF5 then RemoveBlocks;
      EnemyMove;
      if (X = EX) and (Y = EY) then
        begin
          PlayerCaught; DrawInner;
        end;
      DrawLives;
      if Lives = 0 then
        begin
          goto OnGameOver;
        end;
      if (ItemX = X) and (ItemY = Y) then
        begin
          SoundPickup;
          goto NextItem;
        end;
    until KeyCode = KeyEscape;
OnGameOver:
    GameOver;
PlayAgain:
    DrawHLine(25, 51, 8, '█');
    WriteXY(25, 9, '██ NOCHMAL SPIELEN (J/N) ██');
    WriteXY(25, 10, '██                       ██');
    DrawHLine(25, 51, 11, '█');
    GotoXY(30, 10);
    repeat
      Key := UpCase(GetKey);
      case Key of
        'J': goto NewGame;
        'N': goto CleanUp;
      end;
    until false;
  until KeyCode = KeyEscape;
CleanUp:
  ClrScr;
  Write(TTY, #27'[0m'); Flush(TTY); { reset all attributes before exit }
  MyCursorOn;
  Close(TTY);
end.

