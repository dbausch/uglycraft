unit DANISOFT;
interface
uses Crt, UOSSound;

function UTF8Cols(S: String): Integer;
function Center(S: String): String;
procedure Intro(Logo1, Logo2, Logo3, Logo4, Logo5, Logo6, Logo7, Logo8: String; Version: String;
  Release, User, CopyYear: String);

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

procedure Intro(Logo1, Logo2, Logo3, Logo4, Logo5, Logo6, Logo7, Logo8: String; Version: String;
  Release, User, CopyYear: String);
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
  WLn(Center('* DANISOFT * PRÄSENTIERT *'));
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
  WLn(Center('Hallo, gleich geht''s los!'));
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
  Write(Center('Bitte die [Enter] bzw. [Return] - Taste Drücken'));
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
