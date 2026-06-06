unit DANISOFT;
interface
uses Crt,Extra1;

procedure Erkennung(s1,s2,s3,s4,s5,s6,s7,s8:String;ver:Real;Nr,User,copyjahr:String);
Procedure Erkennung2(s1,s2,s3,s4,s5,s6,s7,s8:String;sc,sbk:Byte;vers,Nr,user,copy_j_n:String);

implementation

procedure Erkennung(s1,s2,s3,s4,s5,s6,s7,s8:String;ver:Real;
                    Nr,User,copyjahr:String);
var I : Integer;
    StrVer : String;
begin
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
  writeln(Zentriert('* DANISOFT * PRéSENTIERT *'));
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
  writeln(Zentriert('Nicht kopierbares Programm fÅr ' + User));
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
  write(Zentriert('Bitte die [Enter] bzw. [Return] - Taste DrÅcken'));
  readln;
  ClrScr;
  for I := 40 to 50 do
    begin
      sound(I);
      delay(150);
      nosound;
    end;
  textcolor(Black);
end;

Procedure Erkennung2(s1,s2,s3,s4,s5,s6,s7,s8:String;sc,sbk:Byte;vers,Nr,user,copy_j_n:String);
const
     Bibb = true;
     Schreibmaschine = false;

var I,c : Integer;
    t : Char;

function Zent(s:String) : Integer;
var Laenge,Blanks : Integer;
Begin
  Laenge := Length(s);
  Blanks := 40 - (Laenge DIV 2);
  Zent := Blanks;
End;

Procedure Schreib(s:String;schnell:Boolean;fg,hg:Integer);
var x,y,I:Integer;
Begin
  x := WhereX;
  y := WhereY;
  textcolor(fg);
  textbackground(hg);
  For I := 1 to length(s) do Write(' ');
  gotoxy(x,y);
  IF schnell then
  Begin
    Sound(600);
    Write(s);
    delay(40);
    Nosound;
  End
  else
  Begin
    For I := 1 to length(s) do
    Begin
      Sound(40);
      Write(s[I]);
      delay(50);
      Nosound;
      delay(35);
    End;
  End;
End;

Begin
  textbackground(0);
  ClrScr;
  c := 1;
  For I := 1 to 1999 do
  Begin
    Textcolor(c);
    Write('€');
    Inc(c);
    IF c = 16 then c := 1;
    Sound(WhereX*WhereY+40);
    delay(3);
  End;
  textbackground(5);
  ClrEol;
  Sound(WhereX*WhereY);
  delay(3);
  NoSound;
  Delay(200);
  gotoxy(Zent('* DANISOFT * PRéSENTIERT *'),4);
  Schreib('* DANISOFT *',Bibb,14,1);
  delay(300);
  Schreib(' PRéSENTIERT *',Schreibmaschine,14,1);
  gotoxy(Zent(s1),7);
  Schreib(s1,Bibb,sc,sbk);
  gotoxy(Zent(s2),8);
  Schreib(s2,Bibb,sc,sbk);
  gotoxy(Zent(s3),9);
  Schreib(s3,Bibb,sc,sbk);
  gotoxy(Zent(s4),10);
  Schreib(s4,Bibb,sc,sbk);
  gotoxy(Zent(s5),11);
  Schreib(s5,Bibb,sc,sbk);
  gotoxy(Zent(s6),12);
  Schreib(s6,Bibb,sc,sbk);
  gotoxy(Zent(s7),13);
  Schreib(s7,Bibb,sc,sbk);
  gotoxy(Zent(s8),14);
  Schreib(s8,Bibb,sc,sbk);
  delay(300);
  gotoxy(Zent('Dieses Programm ist lizenziert fÅr '+user),18);
  Schreib('Dieses Programm ist lizenziert fÅr ',Bibb,14,1);
  delay(300);
  Schreib(user,Schreibmaschine,14,1);
  gotoxy(Zent('Version '+ vers +'/'+Nr),20);
  delay(300);
  Schreib('Version ',Bibb,11,0);
  delay(300);
  Schreib(Vers,Schreibmaschine,11,0);
  delay(300);
  Schreib('/',Bibb,11,0);
  delay(300);
  Schreib(Nr,Schreibmaschine,11,0);
  gotoxy(Zent('Copyright (C) '+copy_j_n),22);
  delay(300);
  Schreib('Copyright (C) ',Bibb,12,1);
  delay(300);
  Schreib(copy_j_n,Schreibmaschine,12,1);
  gotoxy(Zent('Bitte die [Return] bzw. [Enter] Taste drÅcken!'),25);
  Schreib('Bitte die [Return] bzw. [Enter] Taste drÅcken!',Schreibmaschine,10,7);
  repeat
   t := readkey;
  until t = #13;
End;

end.