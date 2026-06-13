unit DANISOFT;
interface
uses Crt, UOSSound;

procedure Erkennung(S1, S2, S3, S4, S5, S6, S7, S8: String; Ver: String; Nr, User, Copyjahr: String);

implementation

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

function Zentriert(S: String): String;
var Laenge, Blanks, I: Integer;
  BlankZone: String;
begin
  Laenge := UTF8Cols(S);
  Blanks := 39 - (Laenge div 2);
  BlankZone := '';
  for I := 1 to Blanks do BlankZone := BlankZone + ' ';
  Zentriert := BlankZone + S;
end;

procedure Erkennung(S1, S2, S3, S4, S5, S6, S7, S8: String; Ver: String;
  Nr, User, Copyjahr: String);
var I: Integer;
  TTY: Text;

procedure WLn(S: String);
begin
  if S = '' then Write(' ') else Write(S); { at least one char forces FPC to emit SGR }
  Write(TTY, #27'[K'); Flush(TTY);
  WriteLn;
  Write(TTY, #27'[K'); Flush(TTY);
end;

begin
  Assign(TTY, '/dev/tty');
  ReWrite(TTY);
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
  WLn(Zentriert('* DANISOFT * PRÄSENTIERT *'));
  Delay(200);
  WLn('');
  Delay(200);
  WLn('');
  TextColor(Red + Blink);
  TextBackground(7);
  Delay(200);
  WLn(S1);
  Delay(200);
  WLn(S2);
  Delay(200);
  WLn(S3);
  Delay(200);
  WLn(S4);
  Delay(200);
  WLn(S5);
  Delay(200);
  WLn(S6);
  Delay(200);
  WLn(S7);
  Delay(200);
  WLn(S8);
  Delay(200);
  WLn('');
  Delay(200);
  TextColor(Black + Blink);
  TextBackground(7);
  WLn('');
  Delay(200);
  WLn(Zentriert('Hallo, gleich geht''s los!'));
  Delay(200);
  WLn('');
  TextColor(Black);
  TextBackground(15);
  Delay(200);
  WLn(Zentriert(User));
  Delay(200);
  WLn('');
  Delay(200);
  WLn(Zentriert('Version: ' + Ver + '/' + Nr));
  Delay(200);
  WLn('');
  Delay(200);
  WLn(Zentriert(Copyjahr));
  Delay(200);
  WLn('');
  Delay(200);
  WLn('');
  Delay(200);
  TextColor(4);
  Write(Zentriert('Bitte die [Enter] bzw. [Return] - Taste Drücken'));
  WLn('');
  ReadLn;
  ClrScr;
  for I := 40 to 50 do
    begin
      Ton(I, 150);
    end;
  TextColor(Black);
  Write(#27'[r'); { reset scroll region to full screen }
  Close(TTY);
end;
end.
