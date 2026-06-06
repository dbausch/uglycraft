unit extra1;
interface

function Zentriert(s:String) : String;

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

End.
