
program UGLI_2;

uses CThreads, Crt, Dos, DANISOFT, UOSSound;
label 100, 300, 999, 998, 1, 997;

const
  User = 'Public Domain';
  Vers = '2.1';
  Nr = '0042';
  MaxX = 80;
  MaxY = 20;
  CurR = 77;
  CurL = 75;
  CurU = 80;
  CurO = 72;
  Unbr = 112;
  Lans = 79;
  Kauf = 32;
  Sped = 71;
  Name = 'UGLI.HSC';
  Copy = 'Released under the terms of the GNU GPLv3';

var
  Steine, Langs, OP, Pausen, Timeslot, TI, I, J, Zahl, Level, Leben,
  VX, VY, SX, SY, LocX, LocY, DX, DY, X, Y, XX, YY, EscState: Integer;
  Punkte: LongInt;
  Sper: array[1..MaxX, 1..MaxY] of Boolean;
  T: Char;
  F, Tty: Text;
  IZ, A, S: String;
  Zeile: String[80];
  Schutz: Boolean;

procedure MyCursorOn;
begin
  Write(Tty, #27'[?25h');
end;
procedure MyCursorOff;
begin
  Write(Tty, #27'[?25l');
end;

procedure WriteXY(Col, Row: Integer; S: String);
var I, C, N: Integer; Ch: String;
begin

  Write(Tty, #27'[?7l'); { disable autowrap for the duration }
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
      Write(Tty, #27'[1;1H'); { poison }
      Write(Tty, #27'[', Row, ';', C, 'H'); { real position }
      Write(Tty, Ch);
      Inc(I, N);
      Inc(C);
    end;
  Write(Tty, #27'[?7h'); { re-enable autowrap }
  Flush(Tty); { drain buffer before CRT sync — prevents a
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

procedure ReStone;
var
  I, J: Integer;
  C: String;
begin
  TextColor(Red);
  for I := 2 to 79 do
    begin
      for J := 2 to 19 do
        begin
          if Sper[I, J] then
            C := '█'
          else
            C := ' ';
          WriteXY(I, J, C);
        end;
    end;
end;

procedure Abfrage;
begin
  ClrScr;
  WriteLn;
  WriteLn('VORNAME ');
  MyCursorOn;
  GotoXY(9, 2); ReadLn(IZ);
  WriteLn('NAME ');
  GotoXY(6, 3); ReadLn(A);
  MyCursorOff;
  Str(Punkte * Leben, S); WriteXY(1, 4, 'Punkte ' + S);
  Assign(F, Name);

  Append(F);

  if IOResult = 0
  then
    begin
      WriteLn(F, IZ, ' ', A, '    ', Punkte * Leben);
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
          WriteLn(F, IZ, ' ', A, '    ', Punkte * Leben);
          Close(F);
          WriteLn;
        end;

    end;
  ReadLn;
  ClrScr;
  Assign(F, Name);

  Reset(F);

  if IOResult = 0
  then
    begin
      while not Eof(F) do
        begin
          ReadLn(F, Zeile);
          WriteLn(Zeile);
        end;
      Close(F);
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
          while not Eof(F) do
            begin
              ReadLn(F, Zeile);
              WriteLn(Zeile);
            end;
          Close(F);
        end;

    end;
  GotoXY(1, 25);
  Write('Bitte [Return] -Taste drücken..');
  ReadLn;

end;

procedure Cls;
begin
  ClrScr;
end;

procedure Verwirrung;
begin
  Erkennung(
  '                  **        **    **********   **           **                 ',
  '                  **        **   **        **  **           **                 ',
  '                  **        **   **        **  **           **                 ',
  '                  **        **   **            **           **                 ',
  '                  **        **   **     *****  **           **                 ',
  '                  **        **   **        **  **           **                 ',
  '                  **        **   **        **  **           **                 ',
  '                   **********     **********   **********   **                 ',
  Vers, Nr, User, Copy);
end;

procedure PunkteZaehlen;
begin
  if Zahl = 2 then Punkte := Punkte + 100;
  if Zahl = 3 then Punkte := Punkte + 200;
  if Zahl = 4 then Punkte := Punkte + 300;
  if Zahl = 5 then Punkte := Punkte + 400;
  if Zahl = 6 then Punkte := Punkte + 500;
  if Zahl = 7 then Punkte := Punkte + 600;
  if Zahl = 8 then Punkte := Punkte + 700;
  if Zahl = 9 then Punkte := Punkte + 800;
  if Zahl = 10 then Punkte := Punkte + 900;
  TextBackground(Red);
  TextColor(15);
  WriteXY(3, 1, 'PUNKTE '); Write(Punkte);
  TextBackground(0);

end;

procedure InitL1;
begin
  X := 40;
  Y := 10;
  T := Chr(CurR);
end; {InitL1}

procedure InitL2;
var
  I: Integer;
begin
  for I := 18 to 62 do
    begin
      Sper[I, 10] := true;
    end;

  X := 40;
  Y := 5;
  T := Chr(CurR);;
end; {InitL2}

procedure InitL3;
var
  I: Integer;
begin
  for I := 5 to 15 do
    begin
      Sper[20, I] := true;
      Sper[60, I] := true;
    end;
  for I := 20 to 60 do
    begin
      Sper[I, 10] := true;
    end;
  Sper[39, 10] := false;
  Sper[40, 10] := false;
  Sper[41, 10] := false;

  X := 40;
  Y := 9;
  T := Chr(CurO);
end; {InitL3}

procedure InitL4;
var
  I: Integer;
begin
  for I := 4 to 8 do
    begin
      Sper[15, I] := true;
      Sper[65, I] := true;
    end;
  for I := 5 to 75 do
    Sper[I, 10] := true;
  for I := 12 to 16 do
    begin
      Sper[15, I] := true;
      Sper[65, I] := true;
    end;
  Sper[39, 10] := false;
  Sper[40, 10] := false;
  Sper[41, 10] := false;

  X := 40;
  Y := 9;
  T := Chr(CurR);
end; {InitL4}

procedure InitL5;
var
  I: Integer;
begin
  for I := 5 to 15 do
    begin
      Sper[20, I] := true;
      Sper[60, I] := true;
    end;
  for I := 22 to 58 do
    begin
      Sper[I, 7] := true;
      Sper[I, 13] := true;
    end;
  for I := 20 to 60 do
    begin
      Sper[I, 10] := false;
    end;

  X := 40;
  Y := 10;
  T := Chr(CurO);
end; {InitL5}

procedure InitL6;
var
  I: Integer;
begin
  for I := 2 to 8 do
    begin
      Sper[10, I] := true;
      Sper[20, I] := true;
      Sper[30, I] := true;
      Sper[40, I] := true;
      Sper[50, I] := true;
      Sper[60, I] := true;
      Sper[70, I] := true;
    end;
  for I := 12 to 19 do
    begin
      Sper[10, I] := true;
      Sper[20, I] := true;
      Sper[30, I] := true;
      Sper[40, I] := true;
      Sper[50, I] := true;
      Sper[60, I] := true;
      Sper[70, I] := true;
    end;
  for I := 5 to 15 do
    begin
      Sper[15, I] := true;
      Sper[25, I] := true;
      Sper[35, I] := true;
      Sper[45, I] := true;
      Sper[55, I] := true;
      Sper[65, I] := true;
    end;
  for I := 6 to 74 do
    begin
      Sper[I, 10] := true;
      Sper[I, 9] := false;
      Sper[I, 11] := false;
    end;
  Sper[38, 10] := false;
  Sper[39, 10] := false;
  Sper[40, 10] := false;
  Sper[41, 10] := false;
  Sper[42, 10] := false;

  X := 75;
  Y := 5;
  T := Chr(CurU);
end; {InitL6}

procedure InitL7;
var
  I, J: Integer;
begin
  J := 0;
  for I := 3 to 17 do
    begin
      Inc(J);
      Sper[5 + J, I] := true;
      Sper[33 + J, I] := true;
      Sper[60 + J, I] := true;
    end;
  J := 16;
  for I := 3 to 17 do
    begin
      Dec(J);
      Sper[5 + J, I] := true;
      Sper[33 + J, I] := true;
      Sper[60 + J, I] := true;
    end;
  for J := 9 to 11 do
    for I := 2 to 79 do
    Sper[I, J] := false;
  for I := 6 to 74 do
    Sper[I, 10] := true;
  for I := 54 to 56 do
    Sper[I, 10] := false;
  for I := 26 to 28 do
    Sper[I, 10] := false;

  X := 75;
  Y := 10;
  T := Chr(CurR);
end; {InitL7}

procedure InitL8;
var
  I: Integer;
begin
  for I := 2 to 15 do
    begin
      Sper[10, I] := true;
      Sper[30, I] := true;
      Sper[50, I] := true;
      Sper[70, I] := true;
    end;
  for I := 5 to 19 do
    begin
      Sper[20, I] := true;
      Sper[40, I] := true;
      Sper[60, I] := true;
    end;

  X := 75;
  Y := 5;
  T := Chr(CurU);
end; {InitL8}

procedure InitL9;
var I: Integer;
begin
  for I := 5 to 15 do
    begin
      Sper[20, I] := true;
      Sper[60, I] := true;
      Sper[39, I] := true;
      Sper[41, I] := true;
    end;
  for I := 21 to 38 do
    Sper[I, 5] := true;
  for I := 42 to 59 do
    Sper[I, 5] := true;
  for I := 22 to 37 do
    Sper[I, 15] := true;
  for I := 43 to 58 do
    Sper[I, 15] := true;

  X := 40;
  Y := 10;
  T := Chr(CurO);
end;

procedure InitL(L: Integer);
begin
  case L of
    1: InitL1;
    2: InitL2;
    3: InitL3;
    4: InitL4;
    5: InitL5;
    6: InitL6;
    7: InitL7;
    8: InitL8;
    9: InitL9;
  end; {case}
  ReStone;
end; {InitL}

procedure Wertsachen;
begin
  Cls;
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
  if Raw = #0then
    begin

      EscState := 0;
      if KeyPressed then Raw := ReadKey else Raw := #0;
    end
  else if (EscState = 2) and (Raw = #27) then
    begin

      EscState := 0; Raw := Chr(Lans);
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

procedure Hilfe;
begin
  VX := X;
  VY := Y;
  TextColor(13);
  Cls;
  WriteXY(2, 1, '                  HILFE VON UGLI');
  WriteXY(2, 2, '[p] = Pause (1 Pause Weniger)');
  WriteXY(2, 3, 'Bewegungs-Tasten: ◄─ = links  ↓ = unten  ─► = rechts  ↑ = oben');
  WriteXY(2, 4, '[Esc] = Abbruch');
  WriteXY(2, 5, '[Ende] = Langsamer');
  WriteXY(2, 6, '[Pos1] = Schneller');
  WriteXY(2, 7, '[F4] = Neustart');
  WriteXY(2, 8, '[F3] = Anzeige der noch vorhandenen Pausen (oben-links)');
  WriteXY(2, 9, '[F2] = Die Geschichte von Ugli');
  WriteXY(2, 10, '[s] = Setzt an der Posision von dir einen Block (danach Richtungstaste drücken)');
  WriteXY(2, 11, '[n] = alle gesetzeten Blöcke wieder entfernen');
  WriteXY(2, 12, '');
  WriteXY(2, 13, 'Achtung:  wenn irgend eine andere Taste gedrückt wird rast Ugli auf dich und du');
  WriteXY(2, 14, 'bist verloren');
  WriteXY(2, 17, '                  T A S T E   D R Ü C K E N');
  T := GetKey;
  X := VX;
  Y := VY;
end;

procedure LevelNeu;
begin
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
    T := GetKey;
    WriteXY(27, 8, '                           ');
    WriteXY(27, 9, '                           ');
    WriteXY(27, 10, '                           ');
    WriteXY(27, 11, '                           ');
  end;
  InitL(Level);
  Delay(1000);
end;

procedure Brumm;
begin
  SoundBrumm;
end; {brumm}

procedure Unten(var X: Integer; var Y: Integer);
var Oldy: Integer;
begin
  Oldy := Y;
  if Sper[X, Y + 1] then Brumm
  else Y := Y + 1;
  if Y <> Oldy then
    begin
      WriteXY(X, Oldy, ' ');
      TextColor(14);
      WriteXY(X, Y, '☺');
    end;
  GotoXY(1, 1);
  TextColor(4);
  WriteXY(SX, SY, '█');
end; {unten}

procedure Links(var X: Integer; var Y: Integer);
var Oldx: Integer;
begin
  Oldx := X;
  if Sper[X - 1, Y] then Brumm
  else X := X - 1;
  if X <> Oldx then
    begin
      WriteXY(Oldx, Y, ' ');
      TextColor(14);
      WriteXY(X, Y, '☺');
    end;
  GotoXY(1, 1);
  TextColor(4);
  WriteXY(SX, SY, '█');
end; {links}

procedure Rechts(var X: Integer; var Y: Integer);
var Oldx: Integer;
begin
  Oldx := X;
  if Sper[X + 1, Y] then Brumm
  else X := X + 1;
  if X <> Oldx then
    begin
      WriteXY(Oldx, Y, ' ');
      TextColor(14);
      WriteXY(X, Y, '☺');
    end;
  GotoXY(1, 1);
  TextColor(4);
  WriteXY(SX, SY, '█');
end; {rechts}

procedure Oben(var X: Integer; var Y: Integer);
var Oldy: Integer;
begin
  Oldy := Y;
  if Sper[X, Y - 1] then Brumm
  else Y := Y - 1;
  if Y <> Oldy then
    begin
      WriteXY(X, Oldy, ' ');
      TextColor(14);
      WriteXY(X, Y, '☺');
    end;
  GotoXY(1, 1);
  TextColor(4);
  WriteXY(SX, SY, '█');
end; {oben}

procedure Rahmen;
var I, J: Integer;
begin
  TextColor(4);
  for I := 1 to MaxX do
    begin
      for J := 1 to MaxY do
        begin
          Sper[I, J] := false;
        end; {FOR J}
    end; {FOR I}

  ClrScr;
  for I := 1 to 80 do
    begin
      TextColor(4);
      WriteXY(I, 1, '█');
      TextColor(4);
      WriteXY(I, 20, '█');
      Sper[I, 1] := true;
      Sper[I, 20] := true;
    end; {FOR}
  for I := 2 to 19 do
    begin
      TextColor(4);
      WriteXY(1, I, '█');
      TextColor(4);
      WriteXY(80, I, '█');
      Sper[1, I] := true;
      Sper[80, I] := true;
    end; {FOR}
  WriteLevel;
  TextBackground(0);
  InitL(Level);

  TextColor(11);
  WriteXY(1, 21, '◄─ = links  ↓ = unten  ─► = rechts  ↑ = oben');
  DrawHLine(1, 80, 22, '─');
  WriteXY(1, 23, '<F1> = Hilfe  <F2> = Geschichte von UGLI  <F3> = Pausen zeigen  <F4> = Neustart ');
  DrawHLine(1, 80, 24, '─');
  WriteXY(1, 25, '<P> = Pause  <Ende> = Langsamer  <Pos1> = Schneller  <Esc> = Ende     ');
end; {rahmen}

procedure UGLI2;
var
  Oldxx, Oldyy: Integer;
  Tryx: Boolean;
  Tryn: Integer;
begin
  if Timeslot = 0 then
    begin
      Oldxx := XX;
      Oldyy := YY;
      DX := X - XX;
      DY := Y - YY;
      Tryx := Abs(DX) > Abs(DY);
      for Tryn := 1 to 2 do
        begin
          if Tryx then
            begin
              if (DX > 0) and (Sper[XX + 1, YY] = false) then
                begin
                  XX := XX + 1;
                  break;
                end;
              if (DX < 0) and (Sper[XX - 1, YY] = false) then
                begin
                  XX := XX - 1;
                  break;
                end;
            end
          else
            begin
              if (DY > 0) and (Sper[XX, YY + 1] = false) then
                begin
                  YY := YY + 1;
                  break;
                end;
              if (DY < 0) and (Sper[XX, YY - 1] = false) then
                begin
                  YY := YY - 1;
                  break;
                end;
            end;
          Tryx := not Tryx;
        end;
      if (XX <> Oldxx) or (YY <> Oldyy) then
        WriteXY(Oldxx, Oldyy, ' ');
      TextColor(6);
      WriteXY(XX, YY, '☻');
    end;
end; {ugli2}

procedure Untbr;
label 200;
begin
  if Pausen = 0 then goto 200;
  Pausen := Pausen - 1;
  Delay(5000);
200:
end;

procedure Geschichte;
begin
  TextColor(13);
  Cls;
  WriteXY(3, 1, '                Geschichte von UGLI');
  WriteXY(3, 3, 'Du  bist  von  einem  König  in  eine  Burg eingeschlossen worden.');
  WriteXY(3, 4, 'Mit  den  Worten: "Ich lasse  Dich  erst wieder frei, wenn Du alle');
  WriteXY(3, 5, 'meine  Schätze  wieder  gefunden  hast", knallte  er  die  Tür zu.');
  WriteXY(3, 6, 'Da  bleibt Dir wohl  nichts anderes  mehr übrig, als seine Schätze');
  WriteXY(3, 7, 'zu holen. Du rennst also sofort los, um alle Schätze einzusammeln.');
  WriteXY(3, 9, '                 T A S T E   D R Ü C K E N');
  T := GetKey;
end;

procedure Langsam;
begin
  Delay(50);
  Langs := Langs + 1;
  WriteXY(3, 5, '        T A S T E   D R Ü C K E N');
  T := GetKey;
  WriteXY(3, 5, '                                   ');
  VX := X;
  VY := Y;
  TextColor(Red);
  for J := 1 to 80 do
    begin
      if Sper[J, 5] = true then WriteXY(J, 5, '█') else WriteXY(J, 5, ' ');
    end;
  X := VX;
  Y := VY;
end;

procedure Schnell;
begin
  Delay(50);
  if Langs > 0 then
    begin
      Langs := Langs - 1;
      WriteXY(3, 5, '        T A S T E   D R Ü C K E N');
      T := GetKey;
      TextColor(Red);
      for J := 1 to 80 do
        begin
          if Sper[J, 5] = true then WriteXY(J, 5, '█') else WriteXY(J, 5, ' ');
        end;
    end;
  if Langs = 0 then
    begin
      WriteXY(3, 3, '                Schneller geht''s nicht');
      WriteXY(3, 5, '        T A S T E   D R Ü C K E N');
      T := GetKey;
      TextColor(Red);
      for I := 3 to 5 do
        begin
          for J := 1 to 80 do
            begin
              if Sper[J, I] = true then WriteXY(J, I, '█') else WriteXY(J, I, ' ');
            end;
        end;
    end;
end;

procedure GameOver;
begin
  WriteXY(XX, YY, ' ');
  WriteXY(X, Y, ' ');
  WriteXY(LocX, LocY, ' ');
  DrawHLine(28, 49, 2, '█');
  WriteXY(28, 3, '██ G A M E  O V E R ██');
  DrawHLine(28, 49, 4, '█');
  SoundGameOver;
end;

procedure PausenZeigen;
begin
  Str(Pausen, S); WriteXY(65, 1, 'PAUSEN ' + S);
  WriteXY(21, 9, 'T A S T E   D R Ü C K E N');
  T := GetKey;
  TextColor(4);
  WriteXY(21, 9, '                           ');
  DrawHLine(65, 79, 1, '█');
  ReStone;
end;

procedure Gewonnen;
begin
  TextColor(12 + Blink);
  DrawHLine(30, 56, 8, '█');
  WriteXY(30, 9, '██    G E W O N N E N    ██');
  DrawHLine(30, 56, 10, '█');
  TextColor(4);
  WriteXY(30, 11, ' T A S T E   D R Ü C K E N ');
  Delay(1000);
  SoundGewonnen;
  TextBackground(Black);
  TextColor(Random(255));
  TextAttr := Random(255);
  TextBackground(1);
  Cls;
  while KeyPressed do T := GetKey;
  T := #0;
  repeat
    begin
      TextAttr := Random(255);
      if KeyPressed then
        begin
          T := GetKey;
          OP := Ord(T);
        end;
      Write('*');
      Delay(10);
    end;
  until OP > 0;
  TextBackground(Black);
  TextColor(9);
  Abfrage;
  Cls;
end;

procedure Def;
begin
  Randomize;
  Verwirrung;
  Wertsachen;
  TextBackground(0);
  TextColor(4);
  Cls;
  Langs := 100;
  Pausen := 20;
  SX := 1;
  SY := 1;

  XX := 5;
  YY := 10;
  X := 40;
  Y := 10;
  Steine := 2000;
  Punkte := 0;
  Leben := 9;
  Level := 0;
  Zahl := 9;
end;

procedure Fressen;
begin
  if Schutz = false then
    begin
      Rahmen;
      SoundCaught;
      Punkte := Punkte - Zahl * 1000;
      if Punkte < 0 then Punkte := 0;
      Zahl := 1;
      Leben := Leben - 1;
      SX := 1;
      SY := 1;
    end
  else
    Schutz := false;
end;

procedure ZahlenSetzung;
begin
  TextColor(2);
  if Zahl = 1 then
    begin
      TextBackground(Black);
      TextColor(Brown);
      WriteXY(LocX, LocY, '|');
    end;
  if Zahl = 2 then
    begin
      TextBackground(Black);
      TextColor(LightBlue);
      WriteXY(LocX, LocY, '☼');
    end;
  if Zahl = 3 then
    begin
      TextColor(LightRed);
      TextBackground(Black);
      WriteXY(LocX, LocY, ':');
    end;
  if Zahl = 4 then
    begin
      TextBackground(Black);
      TextColor(LightBlue);
      WriteXY(LocX, LocY, '*');
    end;
  if Zahl = 5 then
    begin
      TextColor(Yellow);
      WriteXY(LocX, LocY, '=');
    end;
  if Zahl = 6 then
    begin
      TextColor(LightGray);
      WriteXY(LocX, LocY, '≡');
    end;
  if Zahl = 7 then
    begin
      TextColor(Cyan);
      WriteXY(LocX, LocY, 'Γ');
    end;
  if Zahl = 8 then
    begin
      TextColor(Yellow);
      WriteXY(LocX, LocY, 'Φ');
    end;
  if Zahl = 9 then
    begin
      TextColor(LightGreen);
      WriteXY(LocX, LocY, '♦');
    end;
  if (Zahl = 9) and (Level = 9) then
    begin
      TextColor(Yellow);
      WriteXY(LocX, LocY, '⌂');
    end;
  TextBackground(Black);
end;

procedure ZufalsPos;
begin
  repeat
    LocX := Round((Random * 77) + 2); {Zufalls-Zahlen-X-Pos}
    LocY := Round((Random * 17) + 2); {Zufalls-Zahlen-Y-Pos}
  until not Sper[LocX, LocY];
end;

procedure GeheimTricks;
begin
  Cls;
  WriteLn('************* G E H E I M ************');
  WriteLn;
  WriteLn('Drückst du aber <F10> kommst du ein level weiter !!!');
  WriteLn('Mit <s> kann man Steine Setzen !!!');
  WriteLn('Mit <n> kann man alle gesetzten Steine entfernen !!!');
  WriteLn;
  WriteLn('  ↓,↑,', '→', ' oder ', '←', '   DRÜCKEN');
  T := GetKey;
  ReStone;
  TextColor(11);
  WriteXY(1, 21, '◄─ = links  ↓ = unten  ─► = rechts  ↑ = oben');
  DrawHLine(1, 80, 22, '─');
  WriteXY(1, 23, '<F1> = Hilfe  <F2> = Geschichte von UGLI  <F3> = Pausen zeigen  <F4> = Neustart ');
  DrawHLine(1, 80, 24, '─');
  WriteXY(1, 25, '<P> = Pause  <Ende> = Langsamer  <Pos1> = Schneller  <Esc> = Ende     ');
end;

procedure Kaufen;
begin
  Window(2, 2, 79, 19);
  TextBackground(0);
  ClrScr;
  WriteLn('1 )    Schutzschild (Währt einen angrif ab, dann ist es kaputt)  Kostet  1000');
  WriteLn('2 ♥    Leben        (Macht ein leben mehr)                       Kostet  5000');
  T := GetKey;
  Window(1, 1, 80, 25);
  ReStone;
end;

procedure Taste;
begin
  if KeyPressed then
    T := GetKey;
  Timeslot := (Timeslot + 1) mod 2;
  GotoXY(1, 1);
  TI := Ord(T);
  case TI of
    CurR: Rechts(X, Y);
    CurL: Links(X, Y);
    CurO: Oben(X, Y);
    CurU: Unten(X, Y);
    Unbr: Untbr;
    Lans: Langsam;
    Sped: Schnell;
    Kauf: Kaufen;
    49:
      begin
        if Punkte >= 1000 then
          begin
            if Schutz = true then
              WriteXY(2, 2, 'Du hast schon ein Schutzschild.')
            else
              begin
                Schutz := true;
                Punkte := Punkte - 1000;
              end;
          end;
        WriteXY(35, 2, '↑,↓,← oder ← Drücken');
        T := GetKey;
        ReStone;
      end;
    50:
      begin
        if Punkte >= 5000 then
          begin
            Leben := Leben + 1;
            Punkte := Punkte - 5000;
          end;
        WriteXY(2, 2, '↑,↓,← oder ← Drücken');
        T := GetKey;
        ReStone;
      end;
  end; {case}
  if TI = 59 then
    begin
      TextColor(6);
      Hilfe;
      ReStone;
    end;
  if TI = 60 then
    begin
      Geschichte;
      ReStone;
    end;
  if TI = 61 then
    begin
      PausenZeigen;
    end;
  TextColor(14);
  WriteXY(X, Y, '☺');

end;

procedure SteineSetzen;
begin
  Steine := Steine - 1;
  if (Steine > 0) and (Punkte >= 20) then
    begin
      TextColor(4);
      WriteXY(X, Y, '█');
      if Punkte > 0 then Punkte := Punkte - 20;
      Sper[X, Y] := true;
      SX := X;
      SY := Y;
      WriteXY(21, 9, 'T A S T E    D R Ü C K E N');
      Str(Steine: 4, S); WriteXY(21, 10, 'Noch vorhandene Steine: ' + S);
      T := GetKey;
      WriteXY(21, 10, '                            ');
      WriteXY(21, 9, '                            ');
      ReStone;
      X := SX;
      Y := SY;
    end
  else
    begin
      if Steine = 0 then WriteXY(21, 9, 'Keine Steine mehr da!');
      if Punkte < 20 then WriteXY(21, 10, 'Nicht genug Punkte!');
      T := GetKey;
      ReStone;
    end;
end;

procedure SteineNehmen;
begin
  WriteXY(3, 3, '╔═══════════════════════════════════╗');
  WriteXY(3, 4, '║   S T E I N E  ═══  N E H M E N   ║');
  WriteXY(3, 5, '╟───────────────────────────────────╢');
  WriteXY(3, 6, '║Wirklich Alle Steine entfernen(J/N)║');
  WriteXY(3, 7, '║                                   ║');
  WriteXY(3, 8, '╚═══════════════════════════════════╝');
  GotoXY(7, 7); T := UpCase(GetKey);
  ReStone;
  VX := X;
  VY := Y;
  if Punkte >= 20 then
    begin
      case T of
        'J':
          begin
            for I := 1 to 80 do
              for J := 1 to 25 do
              begin
                Sper[I, J] := false;
              end;
            TextColor(4);
            TextBackground(0);
            InitL(Level);
            SX := 1;
            SY := 1;
          end;
      end;
    end;
  if Punkte > 0 then Punkte := Punkte - 20;
  WriteXY(3, 9, 'TASTE DRÜCKEN');
  T := GetKey;
  for I := 1 to 80 do
    begin
      TextColor(4);
      WriteXY(I, 1, '█');
      TextColor(4);
      WriteXY(I, 20, '█');
      Sper[I, 1] := true;
      Sper[I, 20] := true;
    end; {FOR}
  for I := 2 to 19 do
    begin
      TextColor(4);
      WriteXY(1, I, '█');
      TextColor(4);
      WriteXY(80, I, '█');
      Sper[1, I] := true;
      Sper[80, I] := true;
    end; {FOR}
  WriteLevel;
  TextBackground(0);
  ReStone;
  X := VX;
  Y := VY;
  A := '';
end;

begin
  Assign(Tty, '/dev/tty');
  ReWrite(Tty);
  MyCursorOff;
  repeat
1:
    Def;
300:
    Level := 0;
    Zahl := 9;
    Leben := 9;
    Schutz := false;
100:
    Timeslot := 0;
    Zahl := Zahl + 1;
    PunkteZaehlen;
    if Zahl = 10 then
      begin
        Zahl := 1; {Zahl Zurückstellen}
        Level := Level + 1; {Levelzahl + 1}
        SX := 1;
        SY := 1;
        if Level = 1 then {Anfangs-Punkte}
          begin
            Punkte := 0;
          end;
        XX := 5; {X-Pos Gegner}
        YY := 10; {Y-Pos Gegner}
        if Level = 10 then {Abfrage: Wenn Level = 10 dann Gewonnen}
          begin
            Gewonnen;
            goto 997; {Goto Ende}
          end;
        Rahmen;
        Leben := Leben + 1; {Leben + 1}
        LevelNeu; {LevelNeu}
        TextBackground(Red); TextColor(15);
        Str(Punkte, S); WriteXY(3, 1, 'PUNKTE ' + S);
        TextBackground(0);
      end; {if zahl = 10}

    ZufalsPos;

    repeat
      Delay(Langs);
      ZahlenSetzung;
      TextColor(4);
      Taste;
      if TI = 27 then goto 999;
      if TI = 62 then goto 300;
      if TI = 115 then SteineSetzen;
      if TI = 110 then SteineNehmen;
      UGLI2;
      if (X = XX) and (Y = YY) then
        begin
          Fressen; ReStone;
        end;
      TextBackground(LightRed);
      TextColor(15);
      Str(Leben, S); WriteXY(6, 20, 'LEBEN ' + S);
      TextBackground(0);
      if Leben = 0 then
        begin

          goto 998;
        end;

      if (LocX = X) and (LocY = Y) then
        begin
          SoundPickup;
          goto 100;
        end;
    until TI = 27;
998:

    GameOver;
997:
    DrawHLine(25, 51, 8, '█');
    WriteXY(25, 9, '██ NOCHMAL SPIELEN (J/N) ██');
    WriteXY(25, 10, '██                       ██');
    DrawHLine(25, 51, 11, '█');
    repeat
      GotoXY(30, 10);
      T := UpCase(GetKey);
      case T of
        'J': goto 300;
        'N': goto 999;
      end;
    until I = 3000;

  until TI = 27;

999:
  Cls;
  Write(Tty, #27'[0m'); Flush(Tty); { reset all attributes before exit }
  MyCursorOn;
  Close(Tty);
end.

