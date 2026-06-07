unit DANISOFT;
interface
uses Crt;

procedure Erkennung(s1,s2,s3,s4,s5,s6,s7,s8:String;ver:Real;Nr,User,copyjahr:String);

implementation

function Zentriert(s:String) : String;
var Laenge,Blanks,i : Integer;
    BlankZone : String;
Begin
  Laenge := Length(s);
  Blanks := 39 - (Laenge DIV 2);
  BlankZone := '';
  For I := 1 to Blanks do BlankZone := BlankZone + ' ';
  Zentriert := BlankZone + s;
End;

procedure Erkennung(s1,s2,s3,s4,s5,s6,s7,s8:String;ver:Real;
                    Nr,User,copyjahr:String);
var I : Integer;
    StrVer : String;
begin
 Write(#27'[1;25r'); { confine scrolling to rows 1-25 }
 For I := 0 to 7 do
  Begin
   TextBackground(I);
   clrscr;
   sound(I * 150);
   delay(300);
   nosound;
   delay(20);
  end;
  nosound;
  delay(100);
  TextColor(Black);
  TextBackground(0);
  gotoxy(1,1);
  textcolor(15);
  For i := 1 to 25 do
  Begin
    delay(200);
    gotoxy(1,i);
    ClrEol;
    write('                        |                            |');
  End;
  textcolor(0);
  textbackground(7);
  gotoxy(1,25);
  delay(200);
  writeln;
  delay(200);
  writeln;
  delay(200);
  writeln;
  delay(200);
  writeln;
  delay(200);
  writeln(Zentriert('* DANISOFT * PRÄSENTIERT *'));
  delay(200);
  writeln;
  TextColor(red+Blink);
  TextBackground(7);
  delay(200);
  writeln(s1);
  delay(200);
  writeln(s2);
  delay(200);
  writeln(s3);
  delay(200);
  writeln(s4);
  delay(200);
  writeln(s5);
  delay(200);
  writeln(s6);
  delay(200);
  writeln(s7);
  delay(200);
  writeln(s8);
  delay(200);
  writeln;
  delay(200);
  TextColor(black+Blink);
  TextBackground(7);
  Writeln;
  delay(200);
  Writeln(Zentriert('Hallo, gleich geht''s los!'));
  delay(200);
  writeln;
  TextColor(black);
  TextBackground(15);
  delay(200);
  writeln(Zentriert('Nicht kopierbares Programm für ' + User));
  delay(200);
  writeln;
  delay(200);
  System.Str(ver:2:2,StrVer);
  writeln(Zentriert('Version: ' + StrVer + '/' + Nr));
  delay(200);
  writeln;
  delay(200);
  writeln(Zentriert(copyjahr));
  delay(200);
  writeln;
  delay(200);
  writeln;
  delay(200);
  textcolor(4);
  write(Zentriert('Bitte die [Enter] bzw. [Return] - Taste Drücken'));
  readln;
  ClrScr;
  for I := 40 to 50 do
    begin
      sound(I);
      delay(150);
      nosound;
    end;
  textcolor(Black);
  Write(#27'[r'); { reset scroll region to full screen }
end;

end.
