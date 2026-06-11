{****************************** B E G I N N *********************************}
{******************************** U G L I ***********************************}
Program ugli_2;

uses cthreads, crt, dos, danisoft, uossound;
label     100, 300, 999, 998, 1, 997;

Const
  user = 'Public Domain';
  vers = '2.1';
  Nr   = '0042';
  MaxX = 80;
  MaxY = 20;
  CurR = 77;
  CurL = 75;
  CurU = 80;
  CurO = 72;
  Unbr = 112;
  lans = 79;
  Kauf = 32;
  sped = 71;
  Name = 'UGLI.HSC';
  copy = 'Released under the terms of the GNU GPLv3';

var
    steine, langs, op, pausen, timeslot, ti, I, J, zahl, level, leben,
    vx, vy, sx, sy, locx, locy, dx, dy, x, y, xx, yy, escState : integer;
    punkte : Longint;
    sper : array [1..MaxX,1..MaxY] of boolean;
    t  : char;
    f, tty : Text;
    IZ,A,S : string;
    Zeile: string[80];
    Schutz : Boolean;

{****************************** B E G I N N *********************************}
{*************************** P R O C E D U R E N ****************************}

procedure MyCursorOn;  begin Write(tty, #27'[?25h'); end;
procedure MyCursorOff; begin Write(tty, #27'[?25l'); end;

procedure writexy(col,row:integer;s:String);
var i,c,n:integer;ch:String;
Begin
 { All output goes directly to the raw tty with autowrap disabled.
   Each character is explicitly repositioned: a poison move to (1,1) first
   guarantees the real position sequence is always freshly emitted.
   CRT's tracker is synced at the end via gotoxy. }
 Write(tty, #27'[?7l');   { disable autowrap for the duration }
 c := col;
 i := 1;
 while i <= Length(s) do
  begin
   if (ord(s[i]) and $F0) = $E0 then n := 3
   else if (ord(s[i]) and $E0) = $C0 then n := 2
   else n := 1;
   ch[0] := chr(n);
   if n >= 1 then ch[1] := s[i];
   if n >= 2 then ch[2] := s[i+1];
   if n >= 3 then ch[3] := s[i+2];
   Write(tty, #27'[1;1H');               { poison }
   Write(tty, #27'[', row, ';', c, 'H'); { real position }
   Write(tty, ch);
   inc(i,n);
   inc(c);
  end;
 Write(tty, #27'[?7h');   { re-enable autowrap }
 Flush(tty);               { drain buffer before CRT sync — prevents a
                             deferred tty flush from displacing the cursor
                             between gotoxy(c,row) and the caller's write() }
 gotoxy(1,1);
 gotoxy(c,row);            { sync CRT's position tracker }
End;

procedure WriteLevel;
var s: String;
begin
   textbackground(Red);
   textcolor(15);
   Str(level, s);
   writexy(36, 1, 'LEVEL ' + s);
end;

procedure DrawHLine(x1,x2,y:integer;ch:String);
var i:integer;
Begin
 for i := x1 to x2 do
  writexy(i,y,ch);
End;

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
          if sper[I, J] then
            C := '█'
          else
            C := ' ';
          writexy(I, J, C);
        end;
    end;
end;

procedure abfrage;
begin
  ClrScr;
  writeln;
  writeln('VORNAME ');
  MyCursorOn;
  gotoxy (9,2); readln(IZ);
  writeln('NAME ');
  gotoxy (6,3); readln(A);
  MyCursorOff;
  Str(punkte * leben, S); writexy(1, 4,'Punkte ' + S);
  Assign(f,Name);
  {$I-}
  Append(f);
  {$I+}

  if IOResult = 0
  then begin
         writeln(f,iz,' ',a,'    ',punkte * leben);
         close(f);
         writeln;
        end
  else begin
         {$I-}
         ReWrite(f);
         if IOResult <> 0 then
         Begin
           Writeln('Datei UGLI.HSC konnte nicht erzeugt werden.');
         End
         else
         Begin
           writeln(f,iz,' ',a,'    ',punkte * leben);
           close(f);
           writeln;
         End;
         {$I+}
       end;
  readln;
  clrscr;
  Assign(f,Name);
  {$I-}
  Reset(f);
  {$I+}
  if IOResult = 0
  then begin
         while not Eof(f) do
         begin
          readln(f,Zeile);
          writeln(Zeile);
         end;
         close(f);
       end
  else begin
         {$I-}
         ReWrite(f);
         if IOResult <> 0 then
         Begin
           Writeln('Datei UGLI.HSC konnte nicht erzeugt werden.');
         End
         else
         Begin
           while not Eof(f) do
           begin
            readln(f,Zeile);
            writeln(Zeile);
           end;
           close(f);
         End;
         {$I+}
       end;
  GotoXY(1,25);
  write('Bitte [Return] -Taste drücken..');
  readln;

end;



procedure cls;
 begin
  clrscr;
 end;

procedure verwirrung;
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
          vers,Nr,user,copy);
end;

procedure punktezaehlen;
Begin
 if zahl = 2 then punkte := punkte + 100;
 if zahl = 3 then punkte := punkte + 200;
 if zahl = 4 then punkte := punkte + 300;
 if zahl = 5 then punkte := punkte + 400;
 if zahl = 6 then punkte := punkte + 500;
 if zahl = 7 then punkte := punkte + 600;
 if zahl = 8 then punkte := punkte + 700;
 if zahl = 9 then punkte := punkte + 800;
 if zahl = 10 then punkte := punkte + 900;
 textbackground(Red);
 textcolor(15);
 writexy(3, 1,'PUNKTE '); Write(punkte);
 textbackground(0);

end;

{****************************** B E G I N N *********************************}
{****************************** L E V E L S *********************************}

procedure InitL1;
begin
  x := 40;
  y := 10;
  t := Chr(CurR);
end; {InitL1}

procedure InitL2;
var
  I: Integer;
Begin
  for I := 18 to 62 do
    begin
      sper[I, 10] := true;
    end;

  x := 40;
  y := 5;
  t := Chr(CurR);;
End; {InitL2}

procedure InitL3;
var
  I: Integer;
begin
  for I := 5 to 15 do
    begin
      sper[20, I] := true;
      sper[60, I] := true;
    end;
  for i := 20 to 60 do
    begin
      sper[I, 10] := true;
    end;
  sper[39,10] := false;
  sper[40,10] := false;
  sper[41,10] := false;

  x := 40;
  y := 9;
  t := Chr(CurO);
end; {InitL3}

procedure InitL4;
var
  I: Integer;
begin
  for I := 4 to 8 do
    begin
      sper[15, I] := true;
      sper[65, I] := true;
    end;
  for I := 5 to 75 do
    sper[I, 10] := true;
  for I := 12 to 16 do
    begin
      sper[15, I] := true;
      sper[65, I] := true;
    end;
  sper[39,10] := false;
  sper[40,10] := false;
  sper[41,10] := false;

  x := 40;
  y := 9;
  t := Chr(CurR);
end; {InitL4}

procedure InitL5;
var
  I: Integer;
begin
  for I := 5 to 15 do
    begin
      sper[20, I] := true;
      sper[60, I] := true;
    end;
  for I := 22 to 58 do
    begin
      sper[I, 7] := true;
      sper[I, 13] := true;
    end;
  for i := 20 to 60 do
    begin
      sper[i,10] := false;
    end;

  x := 40;
  y := 10;
  t := Chr(CurO);
end; {InitL5}

procedure InitL6;
var
  I: Integer;
begin
  for I := 2 to 8 do
    begin
      sper[10, I] := true;
      sper[20, I] := true;
      sper[30, I] := true;
      sper[40, I] := true;
      sper[50, I] := true;
      sper[60, I] := true;
      sper[70, I] := true;
    end;
  for I := 12 to 19 do
    begin
      sper[10, I] := true;
      sper[20, I] := true;
      sper[30, I] := true;
      sper[40, I] := true;
      sper[50, I] := true;
      sper[60, I] := true;
      sper[70, I] := true;
    end;
  for i := 5 to 15 do
    begin
      sper[15,I] := true;
      sper[25,I] := true;
      sper[35,I] := true;
      sper[45,I] := true;
      sper[55,I] := true;
      sper[65,I] := true;
    end;
  for I := 6 to 74 do
    begin
      sper[I, 10] := true;
      sper[I,  9] := false;
      sper[I, 11] := false;
    end;
  sper[38,10] := false;
  sper[39,10] := false;
  sper[40,10] := false;
  sper[41,10] := false;
  sper[42,10] := false;

  x := 75;
  y := 5;
  t := Chr(CurU);
end; {InitL6}

procedure InitL7;
var
  I, J: Integer;
begin
  j := 0;
  for i := 3 to 17 do
  begin
    inc(j);
    sper[5 + j, i] := true;
    sper[33 + j, i] := true;
    sper[60 + j, i] := true;
  end;
  j := 16;
  for i := 3 to 17 do
  begin
    dec(j);
    sper[5+j,i] := true;
    sper[33+j,i] := true;
    sper[60+j,i] := true;
  end;
  for j := 9 to 11 do
    for i := 2 to 79 do
      sper[i,j] := false;
  for i := 6 to 74 do
    sper[i,10] := true;
  for i := 54 to 56 do
    sper[i,10] := false;
  for i := 26 to 28 do
    sper[i,10] := false;

  x := 75;
  y := 10;
  t := Chr(CurR);
end; {InitL7}

procedure InitL8;
var
  I: Integer;
begin
  for I := 2 to 15 do
    begin
      sper[10, I] := true;
      sper[30, I] := true;
      sper[50, I] := true;
      sper[70, I] := true;
    end;
  for I := 5 to 19 do
    begin
      sper[20, I] := true;
      sper[40, I] := true;
      sper[60, I] := true;
    end;

  x := 75;
  y := 5;
  t := Chr(CurU);
end; {InitL8}

procedure InitL9;
var I: Integer;
begin
  for I := 5 to 15 do
    begin
      sper[20, I] := True;
      sper[60, I] := True;
      sper[39, I] := True;
      sper[41, I] := True;
     end;
  for I := 21 to 38 do
    sper[I, 5] := True;
  for I := 42 to 59 do
    sper[I, 5] := True;
  for I := 22 to 37 do
    sper[I, 15] := True;
  for I := 43 to 58 do
    sper[I, 15] := True;

  x := 40;
  y := 10;
  t := Chr(CurO);
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

{******************************** E N D E ***********************************}
{****************************** L E V E L S *********************************}

procedure Wertsachen;
Begin
  cls;
  writeln;
  writeln(' L I S T E   D E R   E I N Z U S A M M E L N D E N   S C H Ä T Z E ');
  writeln;
  writeln('    | Seil ');
  writeln('    ☼ grosser glänzender Diamant ');
  writeln('    : kleine Edelsteiene ');
  writeln('    * kleiner glänzender Diamant ');
  writeln('    = Goldbarren ');
  writeln('    ≡ Silberbarren ');
  writeln('    Γ Brunnen ');
  writeln('    Φ Lampe ');
  writeln('    ♦ grosser Edelstein ');
  writeln('    ⌂ Krone ');
  writeln;
  gotoxy(1,15);
  writeln('   S P I E L A N L E I T U N G   ');
  writeln;
  writeln('Du drückst jetzt die Return-Taste(Enter), dann drückst du eine der ');
  writeln('Richtungstasten danach musst du mit den Richtungstasten die oben gezeigten ');
  writeln('Dinge einsammeln.       (Die Krone kommt ganz zum Schluss.)');
  writeln('Während des Spiels kann man mit <F1> die anderen Tasten die zum bedienen ');
  writeln('des Spiels nachlesen.');
  readln;
End;

{ All key reads go through GetKey so the state machine runs consistently.
  The installed FPC CRT does not handle ESC[F (End); it pushes the bytes
  back LIFO, delivering them reversed across three consecutive calls:
    call 1: 'F' (70)  -> state 1, suppressed (returns #0)
    call 2: '[' (91)  -> state 2, suppressed (returns #0)
    call 3: ESC (27)  -> maps to chr(lans) = End key
  Home (ESC[H) is handled by FPC CRT: arrives as #0 + chr(71) normally.
  escState is a global integer, initialised to 0 at program start. }
function GetKey: char;
var raw: char;
begin
  raw := ReadKey;
  if raw = #0 then begin
    { Extended-key prefix (#0 + scan code). }
    escState := 0;
    if KeyPressed then raw := ReadKey else raw := #0;
  end else if (escState = 2) and (raw = #27) then begin
    { F + '[' + ESC completed: reversed ESC[F = End key. }
    escState := 0; raw := chr(lans);
  end else if (escState = 1) and (raw = '[') then begin
    { Second byte of reversed End sequence; wait for ESC next call. }
    escState := 2; raw := #0;
  end else begin
    { Any other byte resets partial state; check for new 'F' prefix. }
    escState := 0;
    if raw = 'F' then begin escState := 1; raw := #0; end;
  end;
  GetKey := raw;
end;

procedure Hilfe;
begin
  vx := x;
  vy := y;
  textcolor(13);
  cls;
  writexy(2, 1,'                  HILFE VON UGLI');
  writexy(2, 2,'[p] = Pause (1 Pause Weniger)');
  writexy(2, 3,'Bewegungs-Tasten: ◄─ = links  ↓ = unten  ─► = rechts  ↑ = oben');
  writexy(2, 4,'[Esc] = Abbruch');
  writexy(2, 5,'[Ende] = Langsamer');
  writexy(2, 6,'[Pos1] = Schneller');
  writexy(2, 7,'[F4] = Neustart');
  writexy(2, 8,'[F3] = Anzeige der noch vorhandenen Pausen (oben-links)');
  writexy(2, 9,'[F2] = Die Geschichte von Ugli');
  writexy(2,10,'[s] = Setzt an der Posision von dir einen Block (danach Richtungstaste drücken)');
  writexy(2,11,'[n] = alle gesetzeten Blöcke wieder entfernen');
  writexy(2,12,'');
  writexy(2,13,'Achtung:  wenn irgend eine andere Taste gedrückt wird rast Ugli auf dich und du');
  writexy(2,14,'bist verloren');
  writexy(2,17,'                  T A S T E   D R Ü C K E N');
  t := GetKey;
  x := vx;
  y := vy;
end;

procedure levelneu;
begin
  begin
   repeat
       DrawHLine(27,53,8,'█');
       writexy(27, 9,'█');
       Str(level, S);
       writexy(28, 9,' L E V E L   ' + S + '           ');
       writexy(53, 9,'█');
       DrawHLine(27,53,10,'█');
      writexy(27, 11,' T A S T E   D R Ü C K E N ');
    delay(1000);
   until keypressed;
   t := GetKey;
       writexy(27, 8,'                           ');
       writexy(27, 9,'                           ');
      writexy(27, 10,'                           ');
      writexy(27, 11,'                           ');
  end;
  InitL(level);
 delay(1000);
end;

Procedure Brumm;
Begin
 SoundBrumm;
End; {brumm}

procedure unten (Var x:integer; Var y:integer);
var oldy: integer;
begin
  oldy := y;
  if sper[x, y + 1] then Brumm
                    else y := y + 1;
  if y <> oldy then begin
    writexy(x, oldy,' ');
    textcolor(14);
    writexy(x,y,'☺');
  end;
  gotoxy(1,1);
  textcolor(4);
  writexy(sx,sy,'█');
end; {unten}

procedure links (Var x:Integer; Var y:integer);
var oldx: integer;
begin
  oldx := x;
  if sper[x-1, y] then Brumm
                  else x := x - 1;
  if x <> oldx then begin
    writexy(oldx, y,' ');
    textcolor(14);
    writexy(x,y,'☺');
  end;
  gotoxy(1,1);
  textcolor(4);
  writexy(sx,sy,'█');
end;  {links}

procedure rechts (Var x:Integer; Var y:integer);
var oldx: integer;
begin
  oldx := x;
  if sper[x+1, y] then Brumm
                  else x := x + 1;
  if x <> oldx then begin
    writexy(oldx, y,' ');
    textcolor(14);
    writexy(x,y,'☺');
  end;
  gotoxy(1,1);
  textcolor(4);
  writexy(sx,sy,'█');
end;  {rechts}

procedure oben (Var x:Integer; Var y:integer);
var oldy: integer;
begin
  oldy := y;
  if sper[x, y - 1] then Brumm
                    else y := y - 1;
  if y <> oldy then begin
    writexy(x, oldy,' ');
    textcolor(14);
    writexy(x,y,'☺');
  end;
  gotoxy(1,1);
  textcolor(4);
  writexy(sx,sy,'█');
end; {oben}

procedure rahmen;
var I,J:Integer;
begin
 textcolor(4);
 for I := 1 to MaxX do
   begin
    for J := 1 to MaxY do
      begin
       sper[I, J] := false;
      end; {FOR J}
   end; {FOR I}

 ClrScr;
 for I := 1 to 80 do
     begin
     textcolor(4);
      writexy(I, 1,'█');
      textcolor(4);
      writexy(I, 20,'█');
      sper[I, 1] := true;
      sper[I, 20] := true;
     end; {FOR}
 for I := 2 to 19 do
     begin
     textcolor(4);
      writexy(1, I,'█');
      textcolor(4);
      writexy(80, I,'█');
      sper[1, I] := true;
      sper[80, I] := true;
     end; {FOR}
   WriteLevel;
 textbackground(0);
  InitL(level);

     textcolor(11);
     writexy(1, 21,'◄─ = links  ↓ = unten  ─► = rechts  ↑ = oben');
     DrawHLine(1,80,22,'─');
     writexy(1, 23,'<F1> = Hilfe  <F2> = Geschichte von UGLI  <F3> = Pausen zeigen  <F4> = Neustart ');
     DrawHLine(1,80,24,'─');
     writexy(1, 25,'<P> = Pause  <Ende> = Langsamer  <Pos1> = Schneller  <Esc> = Ende     ');
end; {rahmen}

procedure ugli2;
var
  oldxx, oldyy: integer;
  tryx: boolean;
  tryn: integer;
begin
  if timeslot = 0 then
    begin
      oldxx := xx;
      oldyy := yy;
      dx := x - xx;
      dy := y - yy;
      tryx := Abs(dx) > Abs(dy);
      for tryn := 1 to 2 do
        begin
          if tryx then
            begin
              if (dx > 0) and (sper[xx + 1,yy] = false) then
                begin
                  xx := xx + 1;
                  break;
                end;
              if (dx < 0) and (sper[xx - 1, yy] = false) then
                begin
                  xx := xx - 1;
                  break;
                end;
            end
          else
            begin
              if (dy > 0) and (sper[xx, yy + 1] = false) then
                begin
                  yy := yy + 1;
                  break;
                end;
              if (dy < 0) and (sper[xx, yy - 1] = false) then
                begin
                  yy := yy - 1;
                  break;
                end;
            end;
          tryx := not tryx;
        end;
      if (xx <> oldxx) Or (yy <> oldyy) then
        writexy(oldxx, oldyy,' ');
      textcolor(6);
      writexy(xx, yy,'☻');
    end;
end; {ugli2}

procedure untbr;
label 200;
begin
 if pausen = 0 then goto 200;
 pausen := pausen - 1;
 delay(5000);
 200:
end;

procedure Geschichte;
begin
textcolor(13);
cls;
writexy(3, 1,'                Geschichte von UGLI');
writexy(3, 3,'Du  bist  von  einem  König  in  eine  Burg eingeschlossen worden.');
writexy(3, 4,'Mit  den  Worten: "Ich lasse  Dich  erst wieder frei, wenn Du alle');
writexy(3, 5,'meine  Schätze  wieder  gefunden  hast", knallte  er  die  Tür zu.');
writexy(3, 6,'Da  bleibt Dir wohl  nichts anderes  mehr übrig, als seine Schätze');
writexy(3, 7,'zu holen. Du rennst also sofort los, um alle Schätze einzusammeln.');
writexy(3, 9,'                 T A S T E   D R Ü C K E N');
t := GetKey;
end;

procedure langsam;
begin
  delay(50);
  langs := langs + 1;
  writexy(3, 5,'        T A S T E   D R Ü C K E N');
  t := GetKey;
  writexy(3, 5,'                                   ');
  vx := x;
  vy := y;
  textcolor(Red);
  for J := 1 to 80 do
  Begin
    if sper[J,5] = true then writexy(J,5,'█') else writexy(J,5,' ');
  End;
  x := vx;
  y := vy;
end;

procedure schnell;
begin
 delay(50);
 if langs > 0 then
 begin
  langs := langs - 1;
  writexy(3, 5,'        T A S T E   D R Ü C K E N');
  t := GetKey;
  textcolor(Red);
  for J := 1 to 80 do
  Begin
    if sper[J,5] = true then writexy(J,5,'█') else writexy(J,5,' ');
  End;
 end;
 if langs = 0 then
 begin
  writexy(3, 3,'                Schneller geht''s nicht');
  writexy(3, 5,'        T A S T E   D R Ü C K E N');
  t := GetKey;
  textcolor(Red);
  for I := 3 to 5 do
  Begin
    for J := 1 to 80 do
    Begin
      if sper[J,I] = true then writexy(J,I,'█') else writexy(J,I,' ');
    End;
  End;
 end;
end;

procedure GameOver;
 begin
    writexy(xx, yy,' ');
    writexy(x, y,' ');
    writexy(locx, locy,' ');
    DrawHLine(28,49,2,'█');
    writexy(28, 3,'██ G A M E  O V E R ██');
    DrawHLine(28,49,4,'█');
    SoundGameOver;
end;

procedure PausenZeigen;
begin
 Str(Pausen, S); writexy(65, 1,'PAUSEN ' + S);
 writexy(21, 9,'T A S T E   D R Ü C K E N');
 t := GetKey;
 textcolor(4);
 writexy(21, 9,'                           ');
 DrawHLine(65,79,1,'█');
 ReStone;
end;

procedure Gewonnen;
begin
 textcolor(12+Blink);
 DrawHLine(30,56,8,'█');
 writexy(30, 9,'██    G E W O N N E N    ██');
 DrawHLine(30,56,10,'█');
 textcolor(4);
 writexy(30,11,' T A S T E   D R Ü C K E N ');
 delay(1000);
 SoundGewonnen;
 TEXTBACKGROUND(black);
 TextColor(random(255));
 textattr := random(255);
 textbackground(1);
 cls;
 While KeyPressed do t := GetKey;
 t := #0;
 repeat
  begin
   textattr := random(255);
   if keypressed then
   Begin
     t := GetKey;
     op := ord(t);
   End;
   write('*');
   delay(10);
  end;
 until op > 0;
 TEXTBACKGROUND(black);
 TextColor(9);
 Abfrage;
 cls;
end;

Procedure Def;
begin
 randomize;
 verwirrung;
 Wertsachen;
 textbackground(0);
 textcolor(4);
 cls;
 langs := 100;
 pausen := 20;
 sx := 1;
 sy := 1;

 xx := 5;
 yy := 10;
 x := 40;
 y := 10;
 steine := 2000;
 punkte := 0;
 leben := 9;
 level := 0;
 zahl := 9;
end;

procedure fressen;
begin
   If Schutz = false then
   Begin
     rahmen;
     SoundCaught;
     punkte := punkte - Zahl * 1000;
     If Punkte < 0 then punkte := 0;
     zahl := 1;
     leben := leben - 1;
     sx := 1;
     sy := 1;
   End
   else
   Schutz := false;
end;

procedure ZahlenSetzung;
begin
 TextColor(2);
 if zahl = 1 then
   begin
     textbackground(Black);
     textcolor(Brown);
     writexy(locx, locy,'|');
   end;
 if zahl = 2 then
   begin
     textbackground(Black);
     textcolor(LightBlue);
     writexy(locx, locy,'☼');
   end;
 if zahl = 3 then
   begin
     textcolor(LightRed);
     textbackground(Black);
     writexy(locx,locy,':');
   end;
 if zahl = 4 then
   begin
     textbackground(Black);
     textcolor(LightBlue);
     writexy(locx,locy,'*');
   end;
 if zahl = 5 then
   begin
     textcolor(yellow);
     writexy(locx,locy,'=');
   end;
 if zahl = 6 then
   begin
     textcolor(LightGray);
     writexy(locx,locy,'≡');
   end;
 if zahl = 7 then
   begin
     textcolor(Cyan);
     writexy(locx,locy,'Γ');
   end;
 if zahl = 8 then
   begin
     textcolor(yellow);
     writexy(locx,locy,'Φ');
   end;
if zahl = 9 then
  begin
    textcolor(LightGreen);
    writexy(locx, locy,'♦');
  end;
 if (zahl = 9) and (level = 9) then
   begin
     textcolor(yellow);
     writexy(locx, locy,'⌂');
   end;
 textbackground(Black);
end;

procedure ZufalsPos;
begin
     Repeat
      locx := round((random * 77) + 2);  {Zufalls-Zahlen-X-Pos}
      locy := round((random * 17) + 2);  {Zufalls-Zahlen-Y-Pos}
     Until Not sper[locx,locy];
end;

procedure GeheimTricks;
begin
  cls;
  writeln('************* G E H E I M ************');
  writeln;
  writeln('Drückst du aber <F10> kommst du ein level weiter !!!');
  writeln('Mit <s> kann man Steine Setzen !!!');
  writeln('Mit <n> kann man alle gesetzten Steine entfernen !!!');
  writeln;
  writeln('  ↓,↑,','→',' oder ','←','   DRÜCKEN');
  t := GetKey;
  ReStone;
  textcolor(11);
  writexy(1, 21,'◄─ = links  ↓ = unten  ─► = rechts  ↑ = oben');
  DrawHLine(1,80,22,'─');
  writexy(1, 23,'<F1> = Hilfe  <F2> = Geschichte von UGLI  <F3> = Pausen zeigen  <F4> = Neustart ');
  DrawHLine(1,80,24,'─');
  writexy(1, 25,'<P> = Pause  <Ende> = Langsamer  <Pos1> = Schneller  <Esc> = Ende     ');
End;

procedure Kaufen;
Begin
  window(2,2,79,19);
  textbackground(0);
  clrscr;
  writeln('1 )    Schutzschild (Währt einen angrif ab, dann ist es kaputt)  Kostet  1000');
  writeln('2 ♥    Leben        (Macht ein leben mehr)                       Kostet  5000');
  t := GetKey;
  window(1,1,80,25);
  ReStone;
End;

procedure Taste;
  Begin
    if KeyPressed then
      t := GetKey;
    timeslot := (timeslot + 1) MOD 2;
    gotoxy(1, 1);
    ti := ord(t);
    Case ti of
     CurR: rechts(x, y);
     CurL: links(x, y);
     CurO: oben(x, y);
     CurU: unten(x, y);
     unbr: untbr;
     lans: langsam;
     sped: schnell;
     Kauf: Kaufen;
     49  : Begin
             if punkte >= 1000 then
             Begin
               If Schutz = true then
                 writexy(2,2,'Du hast schon ein Schutzschild.')
               else
               Begin
                 Schutz := true;
                 punkte := punkte - 1000;
               End;
             End;
             writexy(35,2,'↑,↓,← oder ← Drücken');
             t := GetKey;
             ReStone;
           End;
     50  : Begin
             if punkte >= 5000 then
             Begin
               Leben := Leben + 1;
               punkte := punkte - 5000;
             End;
             writexy(2,2,'↑,↓,← oder ← Drücken');
             t := GetKey;
             ReStone;
           End;
    End; {case}
    if ti = 59 then
      begin
        textcolor(6);
        Hilfe;
        ReStone;
      end;
    if ti = 60 then
      begin
        Geschichte;
        ReStone;
      end;
    if ti = 61 then
      begin
        PausenZeigen;
      end;
    textcolor(14);
    writexy(x,y,'☺');

  End;

procedure SteineSetzen;
Begin
  steine := steine - 1;
  if (steine > 0) and (punkte >= 20) then
    Begin
      textcolor(4);
      writexy(x,y,'█');
      if punkte > 0 then punkte := punkte - 20;
      sper[x,y] := true;
      sx := x;
      sy := y;
      writexy(21, 9,'T A S T E    D R Ü C K E N');
      Str(steine:4, S); writexy(21, 10,'Noch vorhandene Steine: ' + S);
      t := GetKey;
      writexy(21,10,'                            ');
      writexy(21, 9,'                            ');
      ReStone;
      x := sx;
      y := sy;
    End
  Else
    Begin
      if Steine = 0 then writexy(21, 9,'Keine Steine mehr da!');
      if Punkte < 20 then writexy(21,10,'Nicht genug Punkte!');
      t := GetKey;
      ReStone;
    End;
End;

procedure SteineNehmen;
Begin
 writexy(3,3,'╔═══════════════════════════════════╗');
 writexy(3,4,'║   S T E I N E  ═══  N E H M E N   ║');
 writexy(3,5,'╟───────────────────────────────────╢');
 writexy(3,6,'║Wirklich Alle Steine entfernen(J/N)║');
 writexy(3,7,'║                                   ║');
 writexy(3,8,'╚═══════════════════════════════════╝');
 gotoxy(7,7); t := UpCase(GetKey);
 ReStone;
 vx := x;
 vy := y;
 if punkte >= 20 then
 Begin
   case t of
    'J': Begin
           For I := 1 to 80 do
            For J := 1 to 25 do
             Begin
              sper[I,J] := false;
             End;
           textcolor(4);
           textbackground(0);
           InitL(level);
           sx := 1;
           sy := 1;
         End;
   End;
 End;
 if punkte > 0 then punkte := punkte - 20;
 writexy(3,9,'TASTE DRÜCKEN');
 t := GetKey;
 for I := 1 to 80 do
     begin
     textcolor(4);
      writexy(I, 1,'█');
      textcolor(4);
      writexy(I, 20,'█');
      sper[I, 1] := true;
      sper[I, 20] := true;
     end; {FOR}
 for I := 2 to 19 do
     begin
     textcolor(4);
      writexy(1, I,'█');
      textcolor(4);
      writexy(80, I,'█');
      sper[1, I] := true;
      sper[80, I] := true;
     end; {FOR}
   WriteLevel;
 textbackground(0);
 ReStone;
 x := vx;
 y := vy;
 a := '';
end;



{******************************** E N D E ***********************************}
{*************************** P R O C E D U R E N ****************************}
{────────────────────────────────────────────────────────────────────────────}
{****************************** B E G I N N *********************************}
{************************ H A U P T P R O G R A M M *************************}

begin
  Assign(tty, '/dev/tty');
  Rewrite(tty);
  MyCursorOff;
  repeat
   1:
   Def;
   300:
   level := 0;
   zahl := 9;
   leben := 9;
   Schutz := false;
   100:
     timeslot := 0;
     zahl := zahl + 1;
     punktezaehlen;
     if zahl = 10 then
      Begin
       zahl := 1;                     {Zahl Zurückstellen}
       level := level + 1;            {Levelzahl + 1}
       sx := 1;
       sy := 1;
       if level = 1 then              {Anfangs-Punkte}
       begin
        punkte := 0;
       end;
       xx := 5;                       {X-Pos Gegner}
       yy := 10;                      {Y-Pos Gegner}
       if level = 10 then             {Abfrage: Wenn Level = 10 dann Gewonnen}
       begin
        Gewonnen;
        goto 997;                     {Goto Ende}
       end;
       rahmen;
       leben := leben + 1;            {Leben + 1}
       levelneu;                      {LevelNeu}
       textbackground(Red); textcolor(15);
       Str(punkte, S); writexy(3, 1,'PUNKTE ' + S);
       textbackground(0);
      end;                            {if zahl = 10}

    ZufalsPos;

    Repeat
     delay(langs);
     ZahlenSetzung;
     textcolor(4);
     Taste;
     if ti = 27 then goto 999;
     if ti = 62 then goto 300;
     if ti = 115 then SteineSetzen;
     if ti = 110 then SteineNehmen;
     ugli2;
     if (x = xx) and (y = yy) then Begin fressen; ReStone; End;
     textbackground(LightRed);
     textcolor(15);
     Str(leben, S); writexy(6, 20,'LEBEN ' + S);
     textbackground(0);
     if leben = 0 then
      begin
       {GameOver}
       goto 998;
      end;

     if (locx = x) AND (locy = y) then
       Begin
         SoundPickup;
         goto 100;
       End;
    Until ti = 27;
998:

GameOver;
997:
DrawHLine(25,51,8,'█');
writexy(25, 9,'██ NOCHMAL SPIELEN (J/N) ██');
writexy(25,10,'██                       ██');
DrawHLine(25,51,11,'█');
repeat
gotoxy(30,10);
t := UpCase(GetKey);
case t of
 'J' : GOTO 300;
 'N' : GOTO 999;
End;
until i = 3000;

until ti = 27;

999:
cls;
 Write(tty, #27'[0m'); Flush(tty);   { reset all attributes before exit }
 MyCursorOn;
 Close(tty);
end.
{******************************** E N D E ***********************************}
{************************ H A U P T P R O G R A M M *************************}

{******************************** E N D E ***********************************}
{******************************** U G L I ***********************************}
