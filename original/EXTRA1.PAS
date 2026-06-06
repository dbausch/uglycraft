unit extra1;
interface
uses crt,dos,graph,Drivers,Boosters;

type
    WahlRec = Record
     Moglich : Array[1..23] of String;
     Anz : Integer;
    End;
    AttrRec = Record
     VGAkt : Boolean;
     HGAkt : Boolean;
     VG : Byte;
     HG : Byte;
     Zeichen : Char;
    End;
    FensterAttrRec = Record
     LO : AttrRec;
     O : AttrRec;
     RO : AttrRec;
     L : AttrRec;
     R : AttrRec;
     LU : AttrRec;
     U : AttrRec;
     RU : AttrRec;
    End;
    HLinieAttrRec = Record
     L : AttrRec;
     M : AttrRec;
     R : AttrRec;
    End;
    VLinieAttrRec = Record
     O : AttrRec;
     M : AttrRec;
     U : AttrRec;
    End;

const
   Schwarz        =  0;
   Blau           =  1;
   Gruen          =  2;
   Tuerkis        =  3;
   Rot            =  4;
   Fuchsinrot     =  5;
   Braun          =  6;
   Hellgrau       =  7;
   Dunkelgrau     =  8;
   Hellblau       =  9;
   HellGruen      = 10;
   Helltuerkis    = 11;
   Hellrot        = 12;
   Hellfuchsinrot = 13;
   Gelb           = 14;
   Weiss          = 15;
   Blinkend       = 128;

   WahlLine : Array[1..23] of Boolean = (False,False,False,False,False,False,
                                         False,False,False,False,False,False,
                                         False,False,False,False,False,False,
                                         False,False,False,False,False);
   DoInit = True;
   DoNotInit = False;

   On = True;
   Off = false;

   OneLine = '(CloÚ,VGloAkt,HGloAkt)'+
             '(CoÄ,VGoAkt,HGoAkt)'+
             '(Cro¿,VGroAkt,HGroAkt)'+
             '(Cl³,VGlAkt,HGlAkt)'+
             '(Cr³,VGrAkt,HGrAkt)'+
             '(CluÀ,VGluAkt,HGluAkt)'+
             '(CuÄ,VGuAkt,HGuAkt)'+
             '(CruÙ,VGruAkt,HGruAkt)';

   TwoLines ='(CloÉ,VGloAkt,HGloAkt)'+
             '(CoÍ,VGoAkt,HGoAkt)'+
             '(Cro»,VGroAkt,HGroAkt)'+
             '(Clº,VGlAkt,HGlAkt)'+
             '(Crº,VGrAkt,HGrAkt)'+
             '(CluÈ,VGluAkt,HGluAkt)'+
             '(CuÍ,VGuAkt,HGuAkt)'+
             '(Cru¼,VGruAkt,HGruAkt)';

   Beides1 = '(CloÖ,VGloAkt,HGloAkt)'+
             '(CoÄ,VGoAkt,HGoAkt)'+
             '(Cro·,VGroAkt,HGroAkt)'+
             '(Clº,VGlAkt,HGlAkt)'+
             '(Crº,VGrAkt,HGrAkt)'+
             '(CluÓ,VGluAkt,HGluAkt)'+
             '(CuÄ,VGuAkt,HGuAkt)'+
             '(Cru½,VGruAkt,HGruAkt)';

   Beides2 = '(CloÕ,VGloAkt,HGloAkt)'+
             '(CoÍ,VGoAkt,HGoAkt)'+
             '(Cro¸,VGroAkt,HGroAkt)'+
             '(Cl³,VGlAkt,HGlAkt)'+
             '(Cr³,VGrAkt,HGrAkt)'+
             '(CluÔ,VGluAkt,HGluAkt)'+
             '(CuÍ,VGuAkt,HGuAkt)'+
             '(Cru¾,VGruAkt,HGruAkt)';

   OneLineUp='(CloÚ,VGlo015,HGlo007)'+
             '(CoÄ,VGo015,HGo007)'+
             '(Cro¿,VGro008,HGro007)'+
             '(Cl³,VGl015,HGl007)'+
             '(Cr³,VGr000,HGr007)'+
             '(CluÀ,VGlu008,HGlu007)'+
             '(CuÄ,VGu000,HGu007)'+
             '(CruÙ,VGru000,HGru007)';
   OneLineDown='(CloÚ,VGlo000,HGlo007)'+
             '(CoÄ,VGo000,HGo007)'+
             '(Cro¿,VGro008,HGro007)'+
             '(Cl³,VGl000,HGl007)'+
             '(Cr³,VGr015,HGr007)'+
             '(CluÀ,VGlu008,HGlu007)'+
             '(CuÄ,VGu015,HGu007)'+
             '(CruÙ,VGru015,HGru007)';
   FatLine=  '(CloÛ,VGloAkt,HGloAkt)'+
             '(Coß,VGoAkt,HGoAkt)'+
             '(CroÛ,VGroAkt,HGroAkt)'+
             '(ClÛ,VGlAkt,HGlAkt)'+
             '(CrÛ,VGrAkt,HGrAkt)'+
             '(CluÛ,VGluAkt,HGluAkt)'+
             '(CuÜ,VGuAkt,HGuAkt)'+
             '(CruÛ,VGruAkt,HGruAkt)';
   FatLine2= '(CloÜ,VGloAkt,HGloAkt)'+    {ÜÜÜÜÜÜÜÜ}
             '(CoÜ,VGoAkt,HGoAkt)'+       {ÛHallo Û}
             '(CroÜ,VGroAkt,HGroAkt)'+    {Û Mama Û}
             '(ClÛ,VGlAkt,HGlAkt)'+       {ßßßßßßßß}
             '(CrÛ,VGrAkt,HGrAkt)'+
             '(Cluß,VGluAkt,HGluAkt)'+
             '(Cuß,VGuAkt,HGuAkt)'+
             '(Cruß,VGruAkt,HGruAkt)';
   LineHOneLineWVL='(ClÇ,VGlAkt,HGlAkt)'+
                   '(CmÄ,VGmAkt,HGmAkt)'+
                   '(Cr¶,VGrAkt,HGrAkt)';
   LinieOneLine='(ClÄ,VGlAkt,HGlAkt)'+
                '(CmÄ,VGmAkt,HGmAkt)'+
                '(CrÄ,VGrAkt,HGrAkt)';
   LinieFatLine1='(CoÜ,VGoAkt,HGoAkt)'+
                 '(CmÛ,VGmAkt,HGmAkt)'+
                 '(CuÛ,VGuAkt,HGuAkt)';
   _Init   = 100;
   _Only   = 100;
   _The    = 100;
   _Params = 100;
   IncorectFensterSyntax = 1;
   IncorectLinieSyntax = 2;

   EgLightColor : Boolean = False;

var XMax : Integer;
    YMax : Integer;
    Takt : Integer;
    EgXPos,
    EgYPos,
    EgBack : Integer;
    FensterAttr : FensterAttrRec;
    HLinieAttr : HLinieAttrRec;
    VLinieAttr : VLinieAttrRec;
    BB : Boolean;

function Auswahl(Mogl:WahlRec) : String;
Procedure AddEntry(var Mogl:WahlRec;Entry:String;Init:Boolean);
Procedure WordToBin(W:Word; var Bin:String);
function MyEingebProc(x,y,Laenge,col:Word; Vorgabe:String) : String;
procedure BlinkText(FG,HG,X,Y,A:Integer;B:String);
procedure ColorPosWrite(color,hintergrund,x,y:Integer;s:String);
procedure Farbe(color,hinter:Integer);
procedure Fenster(x1,y1,x2,y2:Integer;Params,KopfText,Statuszeile:String);
procedure FensterMitObenLinks(x1,y1,x2,y2:Integer;Params,KopfText,Statuszeile:String);
procedure FensterMitUntenMittig(x1,y1,x2,y2:Integer;Params,KopfText,Statuszeile:String);
procedure HLinie(x1,x2,y:Integer;Params,Text:String);
procedure VLinie(x,y1,y2:Integer;Params,Text:String);
procedure Fuellen(Zeichen:Char;x1,y1,x2,y2:Integer);
procedure Zeit(x,y:Integer);
Procedure Ask(var Erg:String; Text:String;x,y:Integer);
Procedure KleinGross(KleinText:String;var GrossText:String;sz : Boolean);
procedure InstallGraph(Var Err : Integer);
procedure SetCursorSpeed(NewSpeed : Word);
procedure TonAuf(Lang1 : Word);
procedure TonAb(Lang1 : Word);
procedure DateiTon(s:String);
procedure Ton(Laenge,Oktave,Note:Integer);
procedure BlinkBit(Switch : boolean);
function Zentriert(s:String) : String;
function RechtsBund(s:String) : String;
function GetKey : String;
function StrZahl(Str : String) : Integer;
function Str(Zahl:Longint) : String;
function Ex1Error : Integer;
function TA(VG,HG:Byte):Byte;
implementation
const ErrorCode : Integer = 0;

function Ex1Error : Integer;
Begin
  Ex1Error := ErrorCode;
  ErrorCode := 0;
End;

procedure SetCursorSpeed(NewSpeed : Word);
begin
  Port[$60] := $F3;
  Delay(200);
  Port[$60] := NewSpeed;
end;

function MyEingebProc(x,y,Laenge,col:Word; Vorgabe:String) : String;
Var Sx,Sy : Word;
    ch : Char;
    PosInString : Word;
    I : Integer;
    Len : Byte;
    s : String;
    SAttr : Byte;
    Temp : Byte;
    Nib1,Nib2 : Byte;

 Procedure ShiftLeft(Von,Wieviel:Integer);
 var Ziel : String;
     I : Integer;
 Begin
   Ziel := '';
   For I := 1 to Von-Wieviel-1 do Ziel := Ziel + s[I];
   For I := Von to Len do
   Begin
     Ziel := Ziel + S[I];
   End;
   Len := Len-Wieviel;
   s := Ziel;
 End;

 Procedure ShiftRight(Von,Wieviel:Integer);
 var Ziel : String;
     I : Integer;
 Begin
   Ziel := '';
   For I := 1 to Von-1 do Ziel := Ziel + s[I];
   For I := Von to Von+(Wieviel-1) do Ziel := Ziel + ' ';
   For I := Von to Len do
   Begin
     Ziel := Ziel + s[I];
   End;
   Len := Len+Wieviel;
   s := Ziel;
 End;

Begin
  Sx := WhereX;
  Sy := WhereY;
  SAttr := TextAttr;
  TextAttr := col * 16;
  If col = 0 then TextColor(15);
  s := '';
  For I := x to x + Laenge-1 do PutStr(h,' ',I,y,TextAttr);
  IF Length(vorgabe) = 0 then
                         Begin
                           PosInString := 1;
                           Len := 0;
                           s := '';
                         End
                         else
                         Begin
                           PosInString := Length(vorgabe) + 1;
                           PutStr(h,s,x,y,TextAttr);
                           Len := Length(vorgabe);
                           s := Vorgabe;
                           PutStr(h,Vorgabe,x,y,TextAttr);
                         End;
  gotoxy(x+Length(Vorgabe),y);
  Repeat
    ch := ReadKey;
    IF (ch > #31) and (PosInString <= Laenge) then
    Begin
      if PosInString > Len then
                           Begin
                             inc(Len);
                             s := s + ch;
                           End
                           else
                           Begin
                             If Len < Laenge then
                             Begin
                               ShiftRight(PosInString,1);
                               s[PosInString] := ch;
                             End
                             else
                             Dec(PosInString);
                           End;
      Inc(PosInString);
    End;
    If (ch = #8) and (PosInString > 1) then
    Begin
      If PosInString > Len then
      Begin
        PutStr(h,' ',x + PosInString - 2,y,TextAttr);
        Delete(s,Len,1);
        Dec(PosInString);
        Dec(Len);
      End
      else
      Begin
        If PosInString > 1 then
        Begin
          PutStr(h,' ',x + Len - 1,y,TextAttr);
          ShiftLeft(PosInString,1);
          Dec(PosInString);
        End; {If PosInString > 1}
      End; {If PosInString > Len}
    End; {If Ch = 8}
    If ch = #0 then {Extendet Keycode}
    Begin
      ch := readkey;
      if ch = #75 then
      Begin
        if PosInString > 1 then
        Begin
          GotoXY(X + PosInString - 2,y);
          Dec(PosInString);
        End;
      End;
      if ch = #77 then
      Begin
        if PosInString <= Len then
        Begin
          GotoXY(X + PosInString,y);
          Inc(PosInString);
        End;
      End;
      if ch = #83 then
      Begin
        if PosInString <= Len then
        Begin
          PutStr(h,' ',X + Len - 1,y,TextAttr);
          ShiftLeft(PosInString+1,1);
        End;
      End;
    End; {If Ch = 0}
    PutStr(h,s,x,y,TextAttr);
    GotoXY(X + PosInString - 1,y);
  Until ch = #13;
  TextAttr := 0;
  If BB = Off then
  Begin
    Nib2 := SAttr DIV 16;
  End
  else
  Begin
    Nib2 := (SAttr DIV 16) MOD 8;
  End;
  If EgLightColor AND (col < 8) then Textcolor(col + 8)
    else If col > 8 then Textcolor(col - 8)
           else TextColor(col);
  TextAttr := TextAttr + (Nib2 * 16);
  For I := x to x + Laenge-1 do PutStr(h,' ',I,y,TextAttr);
  PutStr(h,S,x,y,TextAttr);
  MyEingebProc := s;
  TextAttr := SAttr;
End;

procedure BlinkText(FG,HG,X,Y,A:Integer;B:String);
  Begin
    Repeat
      GotoXY(X,Y);
      TextColor(FG);
      TextBackground(HG);
      Write(B);
      Delay(A);
      GotoXY(X,Y);
      TextColor(HG);
      Write(B);
      Delay(A);
    UNTIL KeyPressed;
End;

procedure ColorPosWrite(color,hintergrund,x,y:Integer;s:String);
Begin
  textcolor(color);
  textbackground(hintergrund);
  PutStr(h,s,x,y,TextAttr);
End;

procedure Farbe(color,hinter:Integer);
Begin
  textcolor(color);
  textbackground(hinter);
End;

procedure Fenster(x1,y1,x2,y2:Integer;Params,KopfText,Statuszeile:String);
var sx,sy,i:Integer;
    OldAttr : Byte;
    OldTextColor : Byte;
    OldTextBackGround : Byte;
 Procedure FilterChars;
 var l : Byte;
     s : String;
     CutS : String;
     CutS2 : String;
     w : Word;
     Err : Integer;
 Begin
   If Pos('Clo',Params) > 0 then FensterAttr.LO.Zeichen := Params[Pos('Clo',Params) + 3];
   If Pos('Co',Params) > 0  then FensterAttr.O.Zeichen  := Params[Pos('Co',Params) + 2];
   If Pos('Cro',Params) > 0 then FensterAttr.RO.Zeichen := Params[Pos('Cro',Params) + 3];
   If (Pos('Cl',Params) > 0) AND (Pos('Cl',Params) <> Pos('Clo',Params)) AND (Pos('Cl',Params) <> Pos('Clu',Params)) then
      FensterAttr.L.Zeichen  := Params[Pos('Cl',Params) + 2]
      else Begin
             CutS := Copy(Params,(Pos('Cl',Params))+3,255);
             If (Pos('Cl',CutS) > 0) AND (Pos('Cl',CutS) <> Pos('Clo',CutS)) AND (Pos('Cl',CutS) <> Pos('Clu',CutS)) then
                FensterAttr.L.Zeichen  := CutS[Pos('Cl',CutS) + 2]
                else Begin
                       CutS2 := Copy(CutS,(Pos('Cl',Params))+3,255);
                       If (Pos('Cl',CutS2) > 0) then FensterAttr.L.Zeichen  := CutS2[Pos('Cr',CutS2) + 2];
                     End;
           End;
   If (Pos('Cr',Params) > 0) AND (Pos('Cr',Params) <> Pos('Cro',Params)) AND (Pos('Cr',Params) <> Pos('Cru',Params)) then
      FensterAttr.R.Zeichen  := Params[Pos('Cr',Params) + 2]
      else Begin
             CutS := Copy(Params,(Pos('Cr',Params))+3,255);
             If (Pos('Cr',CutS) > 0) AND (Pos('Cr',CutS) <> Pos('Cro',CutS)) AND (Pos('Cr',CutS) <> Pos('Cru',CutS)) then
                FensterAttr.R.Zeichen  := CutS[Pos('Cr',CutS) + 2]
                else Begin
                       CutS2 := Copy(CutS,(Pos('Cr',Params))+3,255);
                       If (Pos('Cr',CutS2) > 0) then FensterAttr.R.Zeichen  := CutS2[Pos('Cr',CutS2) + 2];
                     End;
           End;
   If Pos('Clu',Params) > 0 then FensterAttr.LU.Zeichen := Params[Pos('Clu',Params) + 3];
   If Pos('Cu',Params) > 0  then FensterAttr.U.Zeichen  := Params[Pos('Cu',Params) + 2];
   If Pos('Cru',Params) > 0 then FensterAttr.RU.Zeichen := Params[Pos('Cru',Params) + 3];

   If Pos('VGlo',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGlo',Params)+4,3);
     Val(s,FensterAttr.LO.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.LO.VGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.LO.VGAkt := false;
   End;
   If Pos('VGo',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGo',Params)+3,3);
     Val(s,FensterAttr.O.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.O.VGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.O.VGAkt := false;
   End;
   If Pos('VGro',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGro',Params)+4,3);
     Val(s,FensterAttr.RO.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.RO.VGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.RO.VGAkt := false;
   End;
   {***}
   If (Pos('VGl',Params) > 0) AND (Pos('VGl',Params) <> Pos('VGl',Params)) AND (Pos('Cl',Params) <> Pos('Clu',Params)) then
      Begin
        s := Copy(Params,Pos('VGl',Params)+3,3);
        Val(s,FensterAttr.L.VG,Err);
        if Err <> 0 then
        Begin
          if s = 'Akt' then FensterAttr.L.VGAkt := true
                       else ErrorCode := IncorectFensterSyntax;
        End
        else FensterAttr.L.VGAkt := false;
      End
      else Begin
             CutS := Copy(Params,(Pos('VGl',Params))+3,255);
             If (Pos('VGl',CutS) > 0) AND (Pos('VGl',CutS) <> Pos('VGlo',CutS)) AND (Pos('VGl',CutS) <> Pos('VGlu',CutS)) then
                Begin
                  s := Copy(CutS,Pos('VGl',CutS)+3,3);
                  Val(s,FensterAttr.L.VG,Err);
                  if Err <> 0 then
                  Begin
                    if s = 'Akt' then FensterAttr.L.VGAkt := true
                                 else ErrorCode := IncorectFensterSyntax;
                  End
                  else FensterAttr.L.VGAkt := false;
                End
                else Begin
                       CutS2 := Copy(CutS,(Pos('VGl',Params))+3,255);
                       If Pos('VGl',CutS2) > 0 then
                       Begin
                         s := Copy(CutS2,Pos('VGl',CutS2)+3,3);
                         Val(s,FensterAttr.L.VG,Err);
                         if Err <> 0 then
                         Begin
                           if s = 'Akt' then FensterAttr.L.VGAkt := true
                                        else ErrorCode := IncorectFensterSyntax;
                         End
                         else FensterAttr.L.VGAkt := false;
                       End;
                     End;
           End;
   If (Pos('VGr',Params) > 0) AND (Pos('VGr',Params) <> Pos('VGr',Params)) AND (Pos('Cl',Params) <> Pos('Clu',Params)) then
      Begin
        s := Copy(Params,Pos('VGr',Params)+3,3);
        Val(s,FensterAttr.R.VG,Err);
        if Err <> 0 then
        Begin
          if s = 'Akt' then FensterAttr.R.VGAkt := true
                       else ErrorCode := IncorectFensterSyntax;
        End
        else FensterAttr.R.VGAkt := false;
      End
      else Begin
             CutS := Copy(Params,(Pos('VGr',Params))+3,255);
             If (Pos('VGr',CutS) > 0) AND (Pos('VGr',CutS) <> Pos('VGro',CutS)) AND (Pos('VGr',CutS) <> Pos('VGru',CutS)) then
                Begin
                  s := Copy(CutS,Pos('VGr',CutS)+3,3);
                  Val(s,FensterAttr.R.VG,Err);
                  if Err <> 0 then
                  Begin
                    if s = 'Akt' then FensterAttr.R.VGAkt := true
                                 else ErrorCode := IncorectFensterSyntax;
                  End
                  else FensterAttr.R.VGAkt := false;
                End
                else Begin
                       CutS2 := Copy(CutS,(Pos('VGr',Params))+3,255);
                       If Pos('VGr',CutS2) > 0 then
                       Begin
                         s := Copy(CutS2,Pos('VGr',CutS2)+3,3);
                         Val(s,FensterAttr.R.VG,Err);
                         if Err <> 0 then
                         Begin
                           if s = 'Akt' then FensterAttr.R.VGAkt := true
                                        else ErrorCode := IncorectFensterSyntax;
                         End
                         else FensterAttr.R.VGAkt := false;
                       End;
                     End;
           End;
   {***}
   If Pos('VGlu',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGlu',Params)+4,3);
     Val(s,FensterAttr.LU.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.LU.VGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.LU.VGAkt := false;
   End;
   If Pos('VGu',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGu',Params)+3,3);
     Val(s,FensterAttr.U.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.U.VGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.U.VGAkt := false;
   End;
   If Pos('VGru',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGru',Params)+4,3);
     Val(s,FensterAttr.RU.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.RU.VGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.RU.VGAkt := false;
   End;

   If Pos('HGlo',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGlo',Params)+4,3);
     Val(s,FensterAttr.LO.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.LO.HGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.LO.HGAkt := false;
   End;
   If Pos('HGo',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGo',Params)+3,3);
     Val(s,FensterAttr.O.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.O.HGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.O.HGAkt := false;
   End;
   If Pos('HGro',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGro',Params)+4,3);
     Val(s,FensterAttr.RO.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.RO.HGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.RO.HGAkt := false;
   End;
   If (Pos('HGl',Params) > 0) AND (Pos('HGl',Params) <> Pos('HGl',Params)) AND (Pos('Cl',Params) <> Pos('Clu',Params)) then
      Begin
        s := Copy(Params,Pos('HGl',Params)+3,3);
        Val(s,FensterAttr.L.HG,Err);
        if Err <> 0 then
        Begin
          if s = 'Akt' then FensterAttr.L.HGAkt := true
                       else ErrorCode := IncorectFensterSyntax;
        End
        else FensterAttr.L.HGAkt := false;
      End
      else Begin
             CutS := Copy(Params,(Pos('HGl',Params))+3,255);
             If (Pos('HGl',CutS) > 0) AND (Pos('HGl',CutS) <> Pos('HGlo',CutS)) AND (Pos('HGl',CutS) <> Pos('HGlu',CutS)) then
                Begin
                  s := Copy(CutS,Pos('HGl',CutS)+3,3);
                  Val(s,FensterAttr.L.HG,Err);
                  if Err <> 0 then
                  Begin
                    if s = 'Akt' then FensterAttr.L.HGAkt := true
                                 else ErrorCode := IncorectFensterSyntax;
                  End
                  else FensterAttr.L.HGAkt := false;
                End
                else Begin
                       CutS2 := Copy(CutS,(Pos('HGl',Params))+3,255);
                       If Pos('HGl',CutS2) > 0 then
                       Begin
                         s := Copy(CutS2,Pos('HGl',CutS2)+3,3);
                         Val(s,FensterAttr.L.HG,Err);
                         if Err <> 0 then
                         Begin
                           if s = 'Akt' then FensterAttr.L.HGAkt := true
                                        else ErrorCode := IncorectFensterSyntax;
                         End
                         else FensterAttr.L.HGAkt := false;
                       End;
                     End;
           End;
   If (Pos('HGr',Params) > 0) AND (Pos('HGr',Params) <> Pos('HGr',Params)) AND (Pos('Cl',Params) <> Pos('Clu',Params)) then
      Begin
        s := Copy(Params,Pos('HGr',Params)+3,3);
        Val(s,FensterAttr.R.HG,Err);
        if Err <> 0 then
        Begin
          if s = 'Akt' then FensterAttr.R.HGAkt := true
                       else ErrorCode := IncorectFensterSyntax;
        End
        else FensterAttr.R.HGAkt := false;
      End
      else Begin
             CutS := Copy(Params,(Pos('HGr',Params))+3,255);
             If (Pos('HGr',CutS) > 0) AND (Pos('HGr',CutS) <> Pos('HGro',CutS)) AND (Pos('HGr',CutS) <> Pos('HGru',CutS)) then
                Begin
                  s := Copy(CutS,Pos('HGr',CutS)+3,3);
                  Val(s,FensterAttr.R.HG,Err);
                  if Err <> 0 then
                  Begin
                    if s = 'Akt' then FensterAttr.R.HGAkt := true
                                 else ErrorCode := IncorectFensterSyntax;
                  End
                  else FensterAttr.R.HGAkt := false;
                End
                else Begin
                       CutS2 := Copy(CutS,(Pos('HGr',Params))+3,255);
                       If Pos('HGr',CutS2) > 0 then
                       Begin
                         s := Copy(CutS2,Pos('HGr',CutS2)+3,3);
                         Val(s,FensterAttr.R.HG,Err);
                         if Err <> 0 then
                         Begin
                           if s = 'Akt' then FensterAttr.R.HGAkt := true
                                        else ErrorCode := IncorectFensterSyntax;
                         End
                         else FensterAttr.R.HGAkt := false;
                       End;
                     End;
           End;
   If Pos('HGlu',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGlu',Params)+4,3);
     Val(s,FensterAttr.LU.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.LU.HGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.LU.HGAkt := false;
   End;
   If Pos('HGu',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGu',Params)+3,3);
     Val(s,FensterAttr.U.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.U.HGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.U.HGAkt := false;
   End;
   If Pos('HGru',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGru',Params)+4,3);
     Val(s,FensterAttr.RU.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.RU.HGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.RU.HGAkt := false;
   End;
 End;

Begin
  ErrorCode := 0;
  FilterChars;
  if ErrorCode <> 0 then Exit;
  if (x1 = _Init) AND (y1 = _Only) AND (x2 = _The) AND (y2 = _Params) then Exit;
  OldAttr := TextAttr;
  OldTextColor := (OldAttr MOD 16){ + ((OldAttr DIV 128) * 128)};
  OldTextBackGround := (OldAttr DIV 16){ - ((OldAttr DIV 128) * 8)};
  sx := WhereX;
  sy := WhereY;
  {Links Oben}
  If FensterAttr.LO.VGAkt = true then TextAttr := OldTextColor
                                 else TextAttr := FensterAttr.LO.VG;
  If FensterAttr.LO.HGAkt = true then TextAttr := TextAttr + OldTextBackGround * 16
                                 else TextAttr := TextAttr + FensterAttr.LO.HG * 16;
  PutStr(h,FensterAttr.LO.Zeichen,x1,y1,TextAttr);
  {Oben}
  If FensterAttr.O.VGAkt = true then TextAttr := OldTextColor
                                else TextAttr := FensterAttr.O.VG;
  If FensterAttr.O.HGAkt = true then TextAttr := TextAttr + OldTextBackGround * 16
                                else TextAttr := TextAttr + FensterAttr.O.HG * 16;
  For i := x1 + 1 to x2 - 1 do
  Begin
    PutStr(h,FensterAttr.O.Zeichen,i,y1,TextAttr);
  End;
  {Rechts Oben}
  If FensterAttr.RO.VGAkt = true then TextAttr := OldTextColor
                                 else TextAttr := FensterAttr.RO.VG;
  If FensterAttr.RO.HGAkt = true then TextAttr := TextAttr + OldTextBackGround * 16
                                 else TextAttr := TextAttr + FensterAttr.RO.HG * 16;
  PutStr(h,FensterAttr.RO.Zeichen,x2,y1,TextAttr);
  {Links}
  If FensterAttr.L.VGAkt = true then TextAttr := OldTextColor
                                else TextAttr := FensterAttr.L.VG;
  If FensterAttr.L.HGAkt = true then TextAttr := TextAttr + OldTextBackGround * 16
                                else TextAttr := TextAttr + FensterAttr.L.HG * 16;
  For i := y1 + 1 to y2 - 1 do
  Begin
    PutStr(h,FensterAttr.L.Zeichen,x1,i,TextAttr);
  End;
  {Rechts}
  If FensterAttr.R.VGAkt = true then TextAttr := OldTextColor
                                else TextAttr := FensterAttr.R.VG;
  If FensterAttr.R.HGAkt = true then TextAttr := TextAttr + OldTextBackGround * 16
                                else TextAttr := TextAttr + FensterAttr.R.HG * 16;
  For i := y1 + 1 to y2 - 1 do
  Begin
    PutStr(h,FensterAttr.R.Zeichen,x2,i,TextAttr);
  End;
  {Links Unten}
  If FensterAttr.LU.VGAkt = true then TextAttr := OldTextColor
                                 else TextAttr := FensterAttr.LU.VG;
  If FensterAttr.LU.HGAkt = true then TextAttr := TextAttr + OldTextBackGround * 16
                                 else TextAttr := TextAttr + FensterAttr.LU.HG * 16;
  PutStr(h,FensterAttr.LU.Zeichen,x1,y2,TextAttr);
  {Unten}
  If FensterAttr.U.VGAkt = true then TextAttr := OldTextColor
                                else TextAttr := FensterAttr.U.VG;
  If FensterAttr.U.HGAkt = true then TextAttr := TextAttr + OldTextBackGround * 16
                                else TextAttr := TextAttr + FensterAttr.U.HG * 16;
  For i := x1 + 1 to x2 - 1 do
  Begin
    PutStr(h,FensterAttr.U.Zeichen,i,y2,TextAttr);
  End;
  {Rechts Unten}
  If FensterAttr.RU.VGAkt = true then TextAttr := OldTextColor
                                 else TextAttr := FensterAttr.RU.VG;
  If FensterAttr.RU.HGAkt = true then TextAttr := TextAttr + OldTextBackGround * 16
                                 else TextAttr := TextAttr + FensterAttr.RU.HG * 16;
  PutStr(h,FensterAttr.RU.Zeichen,x2,y2,TextAttr);

  IF not (KopfText = '') then
  Begin
    If FensterAttr.O.VGAkt = true then TextAttr := OldTextColor
                                  else TextAttr := FensterAttr.O.VG;
    If FensterAttr.O.HGAkt = true then TextAttr := TextAttr + OldTextBackGround * 16
                                  else TextAttr := TextAttr + FensterAttr.O.HG * 16;
    gotoxy(x1 + 2,y1);
    PutStr(h,' '+Kopftext+' ',((x2-x1) DIV 2) - ((Length(Kopftext)+2) DIV 2) + x1,y1,TextAttr);
  End;
  IF not (StatusZeile = '') then
  Begin
    If FensterAttr.U.VGAkt = true then TextAttr := OldTextColor
                                  else TextAttr := FensterAttr.U.VG;
    If FensterAttr.U.HGAkt = true then TextAttr := TextAttr + OldTextBackGround * 16
                                  else TextAttr := TextAttr + FensterAttr.U.HG * 16;
    PutStr(h,' '+Statuszeile+' ',x1 + 2,y2,TextAttr);
  End;
  gotoxy(sx,sy);
  TextAttr := OldAttr;
End;

procedure FensterMitObenLinks(x1,y1,x2,y2:Integer;Params,KopfText,Statuszeile:String);
var sx,sy,i:Integer;
    OldAttr : Byte;
    OldTextColor : Byte;
    OldTextBackGround : Byte;
 Procedure FilterChars;
 var l : Byte;
     s : String;
     CutS : String;
     CutS2 : String;
     w : Word;
     Err : Integer;
 Begin
   If Pos('Clo',Params) > 0 then FensterAttr.LO.Zeichen := Params[Pos('Clo',Params) + 3];
   If Pos('Co',Params) > 0  then FensterAttr.O.Zeichen  := Params[Pos('Co',Params) + 2];
   If Pos('Cro',Params) > 0 then FensterAttr.RO.Zeichen := Params[Pos('Cro',Params) + 3];
   If (Pos('Cl',Params) > 0) AND (Pos('Cl',Params) <> Pos('Clo',Params)) AND (Pos('Cl',Params) <> Pos('Clu',Params)) then
      FensterAttr.L.Zeichen  := Params[Pos('Cl',Params) + 2]
      else Begin
             CutS := Copy(Params,(Pos('Cl',Params))+3,255);
             If (Pos('Cl',CutS) > 0) AND (Pos('Cl',CutS) <> Pos('Clo',CutS)) AND (Pos('Cl',CutS) <> Pos('Clu',CutS)) then
                FensterAttr.L.Zeichen  := CutS[Pos('Cl',CutS) + 2]
                else Begin
                       CutS2 := Copy(CutS,(Pos('Cl',Params))+3,255);
                       If (Pos('Cl',CutS2) > 0) then FensterAttr.L.Zeichen  := CutS2[Pos('Cr',CutS2) + 2];
                     End;
           End;
   If (Pos('Cr',Params) > 0) AND (Pos('Cr',Params) <> Pos('Cro',Params)) AND (Pos('Cr',Params) <> Pos('Cru',Params)) then
      FensterAttr.R.Zeichen  := Params[Pos('Cr',Params) + 2]
      else Begin
             CutS := Copy(Params,(Pos('Cr',Params))+3,255);
             If (Pos('Cr',CutS) > 0) AND (Pos('Cr',CutS) <> Pos('Cro',CutS)) AND (Pos('Cr',CutS) <> Pos('Cru',CutS)) then
                FensterAttr.R.Zeichen  := CutS[Pos('Cr',CutS) + 2]
                else Begin
                       CutS2 := Copy(CutS,(Pos('Cr',Params))+3,255);
                       If (Pos('Cr',CutS2) > 0) then FensterAttr.R.Zeichen  := CutS2[Pos('Cr',CutS2) + 2];
                     End;
           End;
   If Pos('Clu',Params) > 0 then FensterAttr.LU.Zeichen := Params[Pos('Clu',Params) + 3];
   If Pos('Cu',Params) > 0  then FensterAttr.U.Zeichen  := Params[Pos('Cu',Params) + 2];
   If Pos('Cru',Params) > 0 then FensterAttr.RU.Zeichen := Params[Pos('Cru',Params) + 3];

   If Pos('VGlo',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGlo',Params)+4,3);
     Val(s,FensterAttr.LO.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.LO.VGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.LO.VGAkt := false;
   End;
   If Pos('VGo',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGo',Params)+3,3);
     Val(s,FensterAttr.O.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.O.VGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.O.VGAkt := false;
   End;
   If Pos('VGro',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGro',Params)+4,3);
     Val(s,FensterAttr.RO.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.RO.VGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.RO.VGAkt := false;
   End;
   {***}
   If (Pos('VGl',Params) > 0) AND (Pos('VGl',Params) <> Pos('VGl',Params)) AND (Pos('Cl',Params) <> Pos('Clu',Params)) then
      Begin
        s := Copy(Params,Pos('VGl',Params)+3,3);
        Val(s,FensterAttr.L.VG,Err);
        if Err <> 0 then
        Begin
          if s = 'Akt' then FensterAttr.L.VGAkt := true
                       else ErrorCode := IncorectFensterSyntax;
        End
        else FensterAttr.L.VGAkt := false;
      End
      else Begin
             CutS := Copy(Params,(Pos('VGl',Params))+3,255);
             If (Pos('VGl',CutS) > 0) AND (Pos('VGl',CutS) <> Pos('VGlo',CutS)) AND (Pos('VGl',CutS) <> Pos('VGlu',CutS)) then
                Begin
                  s := Copy(CutS,Pos('VGl',CutS)+3,3);
                  Val(s,FensterAttr.L.VG,Err);
                  if Err <> 0 then
                  Begin
                    if s = 'Akt' then FensterAttr.L.VGAkt := true
                                 else ErrorCode := IncorectFensterSyntax;
                  End
                  else FensterAttr.L.VGAkt := false;
                End
                else Begin
                       CutS2 := Copy(CutS,(Pos('VGl',Params))+3,255);
                       If Pos('VGl',CutS2) > 0 then
                       Begin
                         s := Copy(CutS2,Pos('VGl',CutS2)+3,3);
                         Val(s,FensterAttr.L.VG,Err);
                         if Err <> 0 then
                         Begin
                           if s = 'Akt' then FensterAttr.L.VGAkt := true
                                        else ErrorCode := IncorectFensterSyntax;
                         End
                         else FensterAttr.L.VGAkt := false;
                       End;
                     End;
           End;
   If (Pos('VGr',Params) > 0) AND (Pos('VGr',Params) <> Pos('VGr',Params)) AND (Pos('Cl',Params) <> Pos('Clu',Params)) then
      Begin
        s := Copy(Params,Pos('VGr',Params)+3,3);
        Val(s,FensterAttr.R.VG,Err);
        if Err <> 0 then
        Begin
          if s = 'Akt' then FensterAttr.R.VGAkt := true
                       else ErrorCode := IncorectFensterSyntax;
        End
        else FensterAttr.R.VGAkt := false;
      End
      else Begin
             CutS := Copy(Params,(Pos('VGr',Params))+3,255);
             If (Pos('VGr',CutS) > 0) AND (Pos('VGr',CutS) <> Pos('VGro',CutS)) AND (Pos('VGr',CutS) <> Pos('VGru',CutS)) then
                Begin
                  s := Copy(CutS,Pos('VGr',CutS)+3,3);
                  Val(s,FensterAttr.R.VG,Err);
                  if Err <> 0 then
                  Begin
                    if s = 'Akt' then FensterAttr.R.VGAkt := true
                                 else ErrorCode := IncorectFensterSyntax;
                  End
                  else FensterAttr.R.VGAkt := false;
                End
                else Begin
                       CutS2 := Copy(CutS,(Pos('VGr',Params))+3,255);
                       If Pos('VGr',CutS2) > 0 then
                       Begin
                         s := Copy(CutS2,Pos('VGr',CutS2)+3,3);
                         Val(s,FensterAttr.R.VG,Err);
                         if Err <> 0 then
                         Begin
                           if s = 'Akt' then FensterAttr.R.VGAkt := true
                                        else ErrorCode := IncorectFensterSyntax;
                         End
                         else FensterAttr.R.VGAkt := false;
                       End;
                     End;
           End;
   {***}
   If Pos('VGlu',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGlu',Params)+4,3);
     Val(s,FensterAttr.LU.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.LU.VGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.LU.VGAkt := false;
   End;
   If Pos('VGu',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGu',Params)+3,3);
     Val(s,FensterAttr.U.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.U.VGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.U.VGAkt := false;
   End;
   If Pos('VGru',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGru',Params)+4,3);
     Val(s,FensterAttr.RU.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.RU.VGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.RU.VGAkt := false;
   End;

   If Pos('HGlo',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGlo',Params)+4,3);
     Val(s,FensterAttr.LO.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.LO.HGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.LO.HGAkt := false;
   End;
   If Pos('HGo',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGo',Params)+3,3);
     Val(s,FensterAttr.O.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.O.HGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.O.HGAkt := false;
   End;
   If Pos('HGro',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGro',Params)+4,3);
     Val(s,FensterAttr.RO.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.RO.HGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.RO.HGAkt := false;
   End;
   If (Pos('HGl',Params) > 0) AND (Pos('HGl',Params) <> Pos('HGl',Params)) AND (Pos('Cl',Params) <> Pos('Clu',Params)) then
      Begin
        s := Copy(Params,Pos('HGl',Params)+3,3);
        Val(s,FensterAttr.L.HG,Err);
        if Err <> 0 then
        Begin
          if s = 'Akt' then FensterAttr.L.HGAkt := true
                       else ErrorCode := IncorectFensterSyntax;
        End
        else FensterAttr.L.HGAkt := false;
      End
      else Begin
             CutS := Copy(Params,(Pos('HGl',Params))+3,255);
             If (Pos('HGl',CutS) > 0) AND (Pos('HGl',CutS) <> Pos('HGlo',CutS)) AND (Pos('HGl',CutS) <> Pos('HGlu',CutS)) then
                Begin
                  s := Copy(CutS,Pos('HGl',CutS)+3,3);
                  Val(s,FensterAttr.L.HG,Err);
                  if Err <> 0 then
                  Begin
                    if s = 'Akt' then FensterAttr.L.HGAkt := true
                                 else ErrorCode := IncorectFensterSyntax;
                  End
                  else FensterAttr.L.HGAkt := false;
                End
                else Begin
                       CutS2 := Copy(CutS,(Pos('HGl',Params))+3,255);
                       If Pos('HGl',CutS2) > 0 then
                       Begin
                         s := Copy(CutS2,Pos('HGl',CutS2)+3,3);
                         Val(s,FensterAttr.L.HG,Err);
                         if Err <> 0 then
                         Begin
                           if s = 'Akt' then FensterAttr.L.HGAkt := true
                                        else ErrorCode := IncorectFensterSyntax;
                         End
                         else FensterAttr.L.HGAkt := false;
                       End;
                     End;
           End;
   If (Pos('HGr',Params) > 0) AND (Pos('HGr',Params) <> Pos('HGr',Params)) AND (Pos('Cl',Params) <> Pos('Clu',Params)) then
      Begin
        s := Copy(Params,Pos('HGr',Params)+3,3);
        Val(s,FensterAttr.R.HG,Err);
        if Err <> 0 then
        Begin
          if s = 'Akt' then FensterAttr.R.HGAkt := true
                       else ErrorCode := IncorectFensterSyntax;
        End
        else FensterAttr.R.HGAkt := false;
      End
      else Begin
             CutS := Copy(Params,(Pos('HGr',Params))+3,255);
             If (Pos('HGr',CutS) > 0) AND (Pos('HGr',CutS) <> Pos('HGro',CutS)) AND (Pos('HGr',CutS) <> Pos('HGru',CutS)) then
                Begin
                  s := Copy(CutS,Pos('HGr',CutS)+3,3);
                  Val(s,FensterAttr.R.HG,Err);
                  if Err <> 0 then
                  Begin
                    if s = 'Akt' then FensterAttr.R.HGAkt := true
                                 else ErrorCode := IncorectFensterSyntax;
                  End
                  else FensterAttr.R.HGAkt := false;
                End
                else Begin
                       CutS2 := Copy(CutS,(Pos('HGr',Params))+3,255);
                       If Pos('HGr',CutS2) > 0 then
                       Begin
                         s := Copy(CutS2,Pos('HGr',CutS2)+3,3);
                         Val(s,FensterAttr.R.HG,Err);
                         if Err <> 0 then
                         Begin
                           if s = 'Akt' then FensterAttr.R.HGAkt := true
                                        else ErrorCode := IncorectFensterSyntax;
                         End
                         else FensterAttr.R.HGAkt := false;
                       End;
                     End;
           End;
   If Pos('HGlu',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGlu',Params)+4,3);
     Val(s,FensterAttr.LU.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.LU.HGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.LU.HGAkt := false;
   End;
   If Pos('HGu',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGu',Params)+3,3);
     Val(s,FensterAttr.U.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.U.HGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.U.HGAkt := false;
   End;
   If Pos('HGru',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGru',Params)+4,3);
     Val(s,FensterAttr.RU.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.RU.HGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.RU.HGAkt := false;
   End;
 End;

Begin
  ErrorCode := 0;
  FilterChars;
  if ErrorCode <> 0 then Exit;
  if (x1 = _Init) AND (y1 = _Only) AND (x2 = _The) AND (y2 = _Params) then Exit;
  OldAttr := TextAttr;
  OldTextColor := (OldAttr MOD 16){ + ((OldAttr DIV 128) * 128)};
  OldTextBackGround := (OldAttr DIV 16){ - ((OldAttr DIV 128) * 8)};
  sx := WhereX;
  sy := WhereY;
  {Links Oben}
  If FensterAttr.LO.VGAkt = true then TextAttr := OldTextColor
                                 else TextAttr := FensterAttr.LO.VG;
  If FensterAttr.LO.HGAkt = true then TextAttr := TextAttr + OldTextBackGround * 16
                                 else TextAttr := TextAttr + FensterAttr.LO.HG * 16;
  PutStr(h,FensterAttr.LO.Zeichen,x1,y1,TextAttr);
  {Oben}
  If FensterAttr.O.VGAkt = true then TextAttr := OldTextColor
                                else TextAttr := FensterAttr.O.VG;
  If FensterAttr.O.HGAkt = true then TextAttr := TextAttr + OldTextBackGround * 16
                                else TextAttr := TextAttr + FensterAttr.O.HG * 16;
  For i := x1 + 1 to x2 - 1 do
  Begin
    PutStr(h,FensterAttr.O.Zeichen,i,y1,TextAttr);
  End;
  {Rechts Oben}
  If FensterAttr.RO.VGAkt = true then TextAttr := OldTextColor
                                 else TextAttr := FensterAttr.RO.VG;
  If FensterAttr.RO.HGAkt = true then TextAttr := TextAttr + OldTextBackGround * 16
                                 else TextAttr := TextAttr + FensterAttr.RO.HG * 16;
  PutStr(h,FensterAttr.RO.Zeichen,x2,y1,TextAttr);
  {Links}
  If FensterAttr.L.VGAkt = true then TextAttr := OldTextColor
                                else TextAttr := FensterAttr.L.VG;
  If FensterAttr.L.HGAkt = true then TextAttr := TextAttr + OldTextBackGround * 16
                                else TextAttr := TextAttr + FensterAttr.L.HG * 16;
  For i := y1 + 1 to y2 - 1 do
  Begin
    PutStr(h,FensterAttr.L.Zeichen,x1,i,TextAttr);
  End;
  {Rechts}
  If FensterAttr.R.VGAkt = true then TextAttr := OldTextColor
                                else TextAttr := FensterAttr.R.VG;
  If FensterAttr.R.HGAkt = true then TextAttr := TextAttr + OldTextBackGround * 16
                                else TextAttr := TextAttr + FensterAttr.R.HG * 16;
  For i := y1 + 1 to y2 - 1 do
  Begin
    PutStr(h,FensterAttr.R.Zeichen,x2,i,TextAttr);
  End;
  {Links Unten}
  If FensterAttr.LU.VGAkt = true then TextAttr := OldTextColor
                                 else TextAttr := FensterAttr.LU.VG;
  If FensterAttr.LU.HGAkt = true then TextAttr := TextAttr + OldTextBackGround * 16
                                 else TextAttr := TextAttr + FensterAttr.LU.HG * 16;
  PutStr(h,FensterAttr.LU.Zeichen,x1,y2,TextAttr);
  {Unten}
  If FensterAttr.U.VGAkt = true then TextAttr := OldTextColor
                                else TextAttr := FensterAttr.U.VG;
  If FensterAttr.U.HGAkt = true then TextAttr := TextAttr + OldTextBackGround * 16
                                else TextAttr := TextAttr + FensterAttr.U.HG * 16;
  For i := x1 + 1 to x2 - 1 do
  Begin
    PutStr(h,FensterAttr.U.Zeichen,i,y2,TextAttr);
  End;
  {Rechts Unten}
  If FensterAttr.RU.VGAkt = true then TextAttr := OldTextColor
                                 else TextAttr := FensterAttr.RU.VG;
  If FensterAttr.RU.HGAkt = true then TextAttr := TextAttr + OldTextBackGround * 16
                                 else TextAttr := TextAttr + FensterAttr.RU.HG * 16;
  PutStr(h,FensterAttr.RU.Zeichen,x2,y2,TextAttr);

  IF not (KopfText = '') then
  Begin
    If FensterAttr.O.VGAkt = true then TextAttr := OldTextColor
                                  else TextAttr := FensterAttr.O.VG;
    If FensterAttr.O.HGAkt = true then TextAttr := TextAttr + OldTextBackGround * 16
                                  else TextAttr := TextAttr + FensterAttr.O.HG * 16;
    PutStr(h,' '+Kopftext+' ',x1 + 2,y1,TextAttr);
  End;
  IF not (StatusZeile = '') then
  Begin
    If FensterAttr.U.VGAkt = true then TextAttr := OldTextColor
                                  else TextAttr := FensterAttr.U.VG;
    If FensterAttr.U.HGAkt = true then TextAttr := TextAttr + OldTextBackGround * 16
                                  else TextAttr := TextAttr + FensterAttr.U.HG * 16;
    PutStr(h,' '+Statuszeile+' ',x1 + 2,y2,TextAttr);
  End;
  gotoxy(sx,sy);
  TextAttr := OldAttr;
End;

procedure FensterMitUntenMittig(x1,y1,x2,y2:Integer;Params,KopfText,Statuszeile:String);
var sx,sy,i:Integer;
    OldAttr : Byte;
    OldTextColor : Byte;
    OldTextBackGround : Byte;
 Procedure FilterChars;
 var l : Byte;
     s : String;
     CutS : String;
     CutS2 : String;
     w : Word;
     Err : Integer;
 Begin
   If Pos('Clo',Params) > 0 then FensterAttr.LO.Zeichen := Params[Pos('Clo',Params) + 3];
   If Pos('Co',Params) > 0  then FensterAttr.O.Zeichen  := Params[Pos('Co',Params) + 2];
   If Pos('Cro',Params) > 0 then FensterAttr.RO.Zeichen := Params[Pos('Cro',Params) + 3];
   If (Pos('Cl',Params) > 0) AND (Pos('Cl',Params) <> Pos('Clo',Params)) AND (Pos('Cl',Params) <> Pos('Clu',Params)) then
      FensterAttr.L.Zeichen  := Params[Pos('Cl',Params) + 2]
      else Begin
             CutS := Copy(Params,(Pos('Cl',Params))+3,255);
             If (Pos('Cl',CutS) > 0) AND (Pos('Cl',CutS) <> Pos('Clo',CutS)) AND (Pos('Cl',CutS) <> Pos('Clu',CutS)) then
                FensterAttr.L.Zeichen  := CutS[Pos('Cl',CutS) + 2]
                else Begin
                       CutS2 := Copy(CutS,(Pos('Cl',Params))+3,255);
                       If (Pos('Cl',CutS2) > 0) then FensterAttr.L.Zeichen  := CutS2[Pos('Cr',CutS2) + 2];
                     End;
           End;
   If (Pos('Cr',Params) > 0) AND (Pos('Cr',Params) <> Pos('Cro',Params)) AND (Pos('Cr',Params) <> Pos('Cru',Params)) then
      FensterAttr.R.Zeichen  := Params[Pos('Cr',Params) + 2]
      else Begin
             CutS := Copy(Params,(Pos('Cr',Params))+3,255);
             If (Pos('Cr',CutS) > 0) AND (Pos('Cr',CutS) <> Pos('Cro',CutS)) AND (Pos('Cr',CutS) <> Pos('Cru',CutS)) then
                FensterAttr.R.Zeichen  := CutS[Pos('Cr',CutS) + 2]
                else Begin
                       CutS2 := Copy(CutS,(Pos('Cr',Params))+3,255);
                       If (Pos('Cr',CutS2) > 0) then FensterAttr.R.Zeichen  := CutS2[Pos('Cr',CutS2) + 2];
                     End;
           End;
   If Pos('Clu',Params) > 0 then FensterAttr.LU.Zeichen := Params[Pos('Clu',Params) + 3];
   If Pos('Cu',Params) > 0  then FensterAttr.U.Zeichen  := Params[Pos('Cu',Params) + 2];
   If Pos('Cru',Params) > 0 then FensterAttr.RU.Zeichen := Params[Pos('Cru',Params) + 3];

   If Pos('VGlo',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGlo',Params)+4,3);
     Val(s,FensterAttr.LO.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.LO.VGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.LO.VGAkt := false;
   End;
   If Pos('VGo',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGo',Params)+3,3);
     Val(s,FensterAttr.O.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.O.VGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.O.VGAkt := false;
   End;
   If Pos('VGro',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGro',Params)+4,3);
     Val(s,FensterAttr.RO.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.RO.VGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.RO.VGAkt := false;
   End;
   {***}
   If (Pos('VGl',Params) > 0) AND (Pos('VGl',Params) <> Pos('VGl',Params)) AND (Pos('Cl',Params) <> Pos('Clu',Params)) then
      Begin
        s := Copy(Params,Pos('VGl',Params)+3,3);
        Val(s,FensterAttr.L.VG,Err);
        if Err <> 0 then
        Begin
          if s = 'Akt' then FensterAttr.L.VGAkt := true
                       else ErrorCode := IncorectFensterSyntax;
        End
        else FensterAttr.L.VGAkt := false;
      End
      else Begin
             CutS := Copy(Params,(Pos('VGl',Params))+3,255);
             If (Pos('VGl',CutS) > 0) AND (Pos('VGl',CutS) <> Pos('VGlo',CutS)) AND (Pos('VGl',CutS) <> Pos('VGlu',CutS)) then
                Begin
                  s := Copy(CutS,Pos('VGl',CutS)+3,3);
                  Val(s,FensterAttr.L.VG,Err);
                  if Err <> 0 then
                  Begin
                    if s = 'Akt' then FensterAttr.L.VGAkt := true
                                 else ErrorCode := IncorectFensterSyntax;
                  End
                  else FensterAttr.L.VGAkt := false;
                End
                else Begin
                       CutS2 := Copy(CutS,(Pos('VGl',Params))+3,255);
                       If Pos('VGl',CutS2) > 0 then
                       Begin
                         s := Copy(CutS2,Pos('VGl',CutS2)+3,3);
                         Val(s,FensterAttr.L.VG,Err);
                         if Err <> 0 then
                         Begin
                           if s = 'Akt' then FensterAttr.L.VGAkt := true
                                        else ErrorCode := IncorectFensterSyntax;
                         End
                         else FensterAttr.L.VGAkt := false;
                       End;
                     End;
           End;
   If (Pos('VGr',Params) > 0) AND (Pos('VGr',Params) <> Pos('VGr',Params)) AND (Pos('Cl',Params) <> Pos('Clu',Params)) then
      Begin
        s := Copy(Params,Pos('VGr',Params)+3,3);
        Val(s,FensterAttr.R.VG,Err);
        if Err <> 0 then
        Begin
          if s = 'Akt' then FensterAttr.R.VGAkt := true
                       else ErrorCode := IncorectFensterSyntax;
        End
        else FensterAttr.R.VGAkt := false;
      End
      else Begin
             CutS := Copy(Params,(Pos('VGr',Params))+3,255);
             If (Pos('VGr',CutS) > 0) AND (Pos('VGr',CutS) <> Pos('VGro',CutS)) AND (Pos('VGr',CutS) <> Pos('VGru',CutS)) then
                Begin
                  s := Copy(CutS,Pos('VGr',CutS)+3,3);
                  Val(s,FensterAttr.R.VG,Err);
                  if Err <> 0 then
                  Begin
                    if s = 'Akt' then FensterAttr.R.VGAkt := true
                                 else ErrorCode := IncorectFensterSyntax;
                  End
                  else FensterAttr.R.VGAkt := false;
                End
                else Begin
                       CutS2 := Copy(CutS,(Pos('VGr',Params))+3,255);
                       If Pos('VGr',CutS2) > 0 then
                       Begin
                         s := Copy(CutS2,Pos('VGr',CutS2)+3,3);
                         Val(s,FensterAttr.R.VG,Err);
                         if Err <> 0 then
                         Begin
                           if s = 'Akt' then FensterAttr.R.VGAkt := true
                                        else ErrorCode := IncorectFensterSyntax;
                         End
                         else FensterAttr.R.VGAkt := false;
                       End;
                     End;
           End;
   {***}
   If Pos('VGlu',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGlu',Params)+4,3);
     Val(s,FensterAttr.LU.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.LU.VGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.LU.VGAkt := false;
   End;
   If Pos('VGu',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGu',Params)+3,3);
     Val(s,FensterAttr.U.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.U.VGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.U.VGAkt := false;
   End;
   If Pos('VGru',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGru',Params)+4,3);
     Val(s,FensterAttr.RU.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.RU.VGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.RU.VGAkt := false;
   End;

   If Pos('HGlo',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGlo',Params)+4,3);
     Val(s,FensterAttr.LO.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.LO.HGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.LO.HGAkt := false;
   End;
   If Pos('HGo',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGo',Params)+3,3);
     Val(s,FensterAttr.O.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.O.HGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.O.HGAkt := false;
   End;
   If Pos('HGro',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGro',Params)+4,3);
     Val(s,FensterAttr.RO.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.RO.HGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.RO.HGAkt := false;
   End;
   If (Pos('HGl',Params) > 0) AND (Pos('HGl',Params) <> Pos('HGl',Params)) AND (Pos('Cl',Params) <> Pos('Clu',Params)) then
      Begin
        s := Copy(Params,Pos('HGl',Params)+3,3);
        Val(s,FensterAttr.L.HG,Err);
        if Err <> 0 then
        Begin
          if s = 'Akt' then FensterAttr.L.HGAkt := true
                       else ErrorCode := IncorectFensterSyntax;
        End
        else FensterAttr.L.HGAkt := false;
      End
      else Begin
             CutS := Copy(Params,(Pos('HGl',Params))+3,255);
             If (Pos('HGl',CutS) > 0) AND (Pos('HGl',CutS) <> Pos('HGlo',CutS)) AND (Pos('HGl',CutS) <> Pos('HGlu',CutS)) then
                Begin
                  s := Copy(CutS,Pos('HGl',CutS)+3,3);
                  Val(s,FensterAttr.L.HG,Err);
                  if Err <> 0 then
                  Begin
                    if s = 'Akt' then FensterAttr.L.HGAkt := true
                                 else ErrorCode := IncorectFensterSyntax;
                  End
                  else FensterAttr.L.HGAkt := false;
                End
                else Begin
                       CutS2 := Copy(CutS,(Pos('HGl',Params))+3,255);
                       If Pos('HGl',CutS2) > 0 then
                       Begin
                         s := Copy(CutS2,Pos('HGl',CutS2)+3,3);
                         Val(s,FensterAttr.L.HG,Err);
                         if Err <> 0 then
                         Begin
                           if s = 'Akt' then FensterAttr.L.HGAkt := true
                                        else ErrorCode := IncorectFensterSyntax;
                         End
                         else FensterAttr.L.HGAkt := false;
                       End;
                     End;
           End;
   If (Pos('HGr',Params) > 0) AND (Pos('HGr',Params) <> Pos('HGr',Params)) AND (Pos('Cl',Params) <> Pos('Clu',Params)) then
      Begin
        s := Copy(Params,Pos('HGr',Params)+3,3);
        Val(s,FensterAttr.R.HG,Err);
        if Err <> 0 then
        Begin
          if s = 'Akt' then FensterAttr.R.HGAkt := true
                       else ErrorCode := IncorectFensterSyntax;
        End
        else FensterAttr.R.HGAkt := false;
      End
      else Begin
             CutS := Copy(Params,(Pos('HGr',Params))+3,255);
             If (Pos('HGr',CutS) > 0) AND (Pos('HGr',CutS) <> Pos('HGro',CutS)) AND (Pos('HGr',CutS) <> Pos('HGru',CutS)) then
                Begin
                  s := Copy(CutS,Pos('HGr',CutS)+3,3);
                  Val(s,FensterAttr.R.HG,Err);
                  if Err <> 0 then
                  Begin
                    if s = 'Akt' then FensterAttr.R.HGAkt := true
                                 else ErrorCode := IncorectFensterSyntax;
                  End
                  else FensterAttr.R.HGAkt := false;
                End
                else Begin
                       CutS2 := Copy(CutS,(Pos('HGr',Params))+3,255);
                       If Pos('HGr',CutS2) > 0 then
                       Begin
                         s := Copy(CutS2,Pos('HGr',CutS2)+3,3);
                         Val(s,FensterAttr.R.HG,Err);
                         if Err <> 0 then
                         Begin
                           if s = 'Akt' then FensterAttr.R.HGAkt := true
                                        else ErrorCode := IncorectFensterSyntax;
                         End
                         else FensterAttr.R.HGAkt := false;
                       End;
                     End;
           End;
   If Pos('HGlu',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGlu',Params)+4,3);
     Val(s,FensterAttr.LU.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.LU.HGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.LU.HGAkt := false;
   End;
   If Pos('HGu',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGu',Params)+3,3);
     Val(s,FensterAttr.U.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.U.HGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.U.HGAkt := false;
   End;
   If Pos('HGru',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGru',Params)+4,3);
     Val(s,FensterAttr.RU.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then FensterAttr.RU.HGAkt := true
                    else ErrorCode := IncorectFensterSyntax;
     End
     else FensterAttr.RU.HGAkt := false;
   End;
 End;

Begin
  ErrorCode := 0;
  FilterChars;
  if ErrorCode <> 0 then Exit;
  if (x1 = _Init) AND (y1 = _Only) AND (x2 = _The) AND (y2 = _Params) then Exit;
  OldAttr := TextAttr;
  OldTextColor := (OldAttr MOD 16) + ((OldAttr DIV 128) * 128);
  OldTextBackGround := (OldAttr DIV 16) - ((OldAttr DIV 128) * 8);
  sx := WhereX;
  sy := WhereY;
  {Links Oben}
  If FensterAttr.LO.VGAkt = true then TextColor(OldTextColor)
                                 else TextColor(FensterAttr.LO.VG);
  If FensterAttr.LO.HGAkt = true then TextBackGround(OldTextBackGround)
                                 else TextBackGround(FensterAttr.LO.HG);
  PutStr(h,FensterAttr.LO.Zeichen,x1,y1,TextAttr);
  {Oben}
  If FensterAttr.O.VGAkt = true then TextColor(OldTextColor)
                                 else TextColor(FensterAttr.O.VG);
  If FensterAttr.O.HGAkt = true then TextBackGround(OldTextBackGround)
                                 else TextBackGround(FensterAttr.O.HG);
  For i := x1 + 1 to x2 - 1 do
  Begin
    PutStr(h,FensterAttr.O.Zeichen,i,y1,TextAttr);
  End;
  {Rechts Oben}
  If FensterAttr.RO.VGAkt = true then TextColor(OldTextColor)
                                 else TextColor(FensterAttr.RO.VG);
  If FensterAttr.RO.HGAkt = true then TextBackGround(OldTextBackGround)
                                 else TextBackGround(FensterAttr.RO.HG);
  PutStr(h,FensterAttr.RO.Zeichen,x2,y1,TextAttr);
  {Links}
  If FensterAttr.L.VGAkt = true then TextColor(OldTextColor)
                                 else TextColor(FensterAttr.L.VG);
  If FensterAttr.L.HGAkt = true then TextBackGround(OldTextBackGround)
                                 else TextBackGround(FensterAttr.L.HG);
  For i := y1 + 1 to y2 - 1 do
  Begin
    PutStr(h,FensterAttr.L.Zeichen,x1,i,TextAttr);
  End;
  {Rechts}
  If FensterAttr.R.VGAkt = true then TextColor(OldTextColor)
                                 else TextColor(FensterAttr.R.VG);
  If FensterAttr.R.HGAkt = true then TextBackGround(OldTextBackGround)
                                 else TextBackGround(FensterAttr.R.HG);
  For i := y1 + 1 to y2 - 1 do
  Begin
    PutStr(h,FensterAttr.R.Zeichen,x2,i,TextAttr);
  End;
  {Links Unten}
  If FensterAttr.LU.VGAkt = true then TextColor(OldTextColor)
                                 else TextColor(FensterAttr.LU.VG);
  If FensterAttr.LU.HGAkt = true then TextBackGround(OldTextBackGround)
                                 else TextBackGround(FensterAttr.LU.HG);
  PutStr(h,FensterAttr.LU.Zeichen,x1,y2,TextAttr);
  {Unten}
  If FensterAttr.U.VGAkt = true then TextColor(OldTextColor)
                                 else TextColor(FensterAttr.U.VG);
  If FensterAttr.U.HGAkt = true then TextBackGround(OldTextBackGround)
                                 else TextBackGround(FensterAttr.U.HG);
  For i := x1 + 1 to x2 - 1 do
  Begin
    PutStr(h,FensterAttr.U.Zeichen,i,y2,TextAttr);
  End;
  {Rechts Unten}
  If FensterAttr.RU.VGAkt = true then TextColor(OldTextColor)
                                 else TextColor(FensterAttr.RU.VG);
  If FensterAttr.RU.HGAkt = true then TextBackGround(OldTextBackGround)
                                 else TextBackGround(FensterAttr.RU.HG);
  PutStr(h,FensterAttr.RU.Zeichen,x2,y2,TextAttr);

  IF not (KopfText = '') then
  Begin
    If FensterAttr.O.VGAkt = true then TextColor(OldTextColor)
                                   else TextColor(FensterAttr.O.VG);
    If FensterAttr.O.HGAkt = true then TextBackGround(OldTextBackGround)
                                   else TextBackGround(FensterAttr.O.HG);
    gotoxy(x1 + 2,y1);
    PutStr(h,' '+Kopftext+' ',((x2-x1) DIV 2) - ((Length(Kopftext)+2) DIV 2) + x1,y1,TextAttr);
  End;
  IF not (StatusZeile = '') then
  Begin
    If FensterAttr.U.VGAkt = true then TextColor(OldTextColor)
                                   else TextColor(FensterAttr.U.VG);
    If FensterAttr.U.HGAkt = true then TextBackGround(OldTextBackGround)
                                   else TextBackGround(FensterAttr.U.HG);
    PutStr(h,' '+Statuszeile+' ',((x2-x1) DIV 2) - ((Length(Statuszeile)+2) DIV 2) + x1,y2,TextAttr);
  End;
  gotoxy(sx,sy);
  TextAttr := OldAttr;
End;

procedure Fuellen(Zeichen:Char;x1,y1,x2,y2:Integer);
var I,J : Integer;
Begin
  For I := y1 to y2 do
  Begin
    For J := x1 to x2 do
    Begin
      PutStr(h,Zeichen,J,I,TextAttr);
    End;
  End;
End;

Procedure Ask(var Erg:String; Text:String;x,y:Integer);
var
{	s:String;}
	sx,sy:Integer;
	Textlaenge:Longint;

Begin
  sx := WhereX;
  sy := WhereY;
  gotoxy(x,y);
  Write(Text);
  Textlaenge := Length(Text);
  gotoxy(x+Textlaenge,y);
  Readln(Erg);
  gotoxy(sx,sy);
{  Erg := ;}
End;

procedure Zeit(x,y:Integer);
const p = ':';
var h,min,sec,sec100:Word;
Begin
  GetTime(h,min,sec,sec100);
  gotoxy(x,y);
  write(h:2,p,min:2,p,sec:2,'"',sec100:2);
End;

Procedure KleinGross(KleinText:String;var GrossText:String;sz : Boolean);
var I:Integer; s : Char;
Begin
  For I := 1 to Length(KleinText) do
  Begin
    s := KleinText[i];
    case ord(s) of
     97 : GrossText := GrossText + 'A';
     98 : GrossText := GrossText + 'B';
     99 : GrossText := GrossText + 'C';
     100: GrossText := GrossText + 'D';
     101: GrossText := GrossText + 'E';
     102: GrossText := GrossText + 'F';
     103: GrossText := GrossText + 'G';
     104: GrossText := GrossText + 'H';
     105: GrossText := GrossText + 'I';
     106: GrossText := GrossText + 'J';
     107: GrossText := GrossText + 'K';
     108: GrossText := GrossText + 'L';
     109: GrossText := GrossText + 'M';
     110: GrossText := GrossText + 'N';
     111: GrossText := GrossText + 'O';
     112: GrossText := GrossText + 'P';
     113: GrossText := GrossText + 'Q';
     114: GrossText := GrossText + 'R';
     115: GrossText := GrossText + 'S';
     116: GrossText := GrossText + 'T';
     117: GrossText := GrossText + 'U';
     118: GrossText := GrossText + 'V';
     119: GrossText := GrossText + 'W';
     120: GrossText := GrossText + 'X';
     121: GrossText := GrossText + 'Y';
     122: GrossText := GrossText + 'Z';
     225:
     Begin
       If sz = True then
         Begin
           GrossText := GrossText + 'SS';
         End
       else
         Begin
           GrossText := GrossText + KleinText[i];
         end;
     End;
     132: GrossText := GrossText + 'Ž';
     148: GrossText := GrossText + '™';
     129: GrossText := GrossText + 'š';
     else GrossText := GrossText + KleinText[i];
    End;
  End;
End;

procedure HLinie(x1,x2,y:Integer;Params,Text:String);
var sx,sy,i:Integer;
    OldAttr : Byte;
    OldTextColor : Byte;
    OldTextBackGround : Byte;
 Procedure FilterChars;
 var l : Byte;
     s : String;
     CutS : String;
     CutS2 : String;
     w : Word;
     Err : Integer;
 Begin
   If Pos('Cl',Params) > 0 then HLinieAttr.L.Zeichen := Params[Pos('Cl',Params) + 2];
   If Pos('Cm',Params) > 0 then HLinieAttr.M.Zeichen := Params[Pos('Cm',Params) + 2];
   If Pos('Cr',Params) > 0 then HLinieAttr.R.Zeichen := Params[Pos('Cr',Params) + 2];

   If Pos('VGl',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGl',Params)+3,3);
     Val(s,HLinieAttr.L.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then HLinieAttr.L.VGAkt := true
                    else ErrorCode := IncorectLinieSyntax;
     End
     else HLinieAttr.L.VGAkt := false;
   End;
   If Pos('VGm',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGm',Params)+3,3);
     Val(s,HLinieAttr.M.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then HLinieAttr.M.VGAkt := true
                    else ErrorCode := IncorectLinieSyntax;
     End
     else HLinieAttr.M.VGAkt := false;
   End;
   If Pos('VGr',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGr',Params)+3,3);
     Val(s,HLinieAttr.R.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then HLinieAttr.R.VGAkt := true
                    else ErrorCode := IncorectLinieSyntax;
     End
     else HLinieAttr.R.VGAkt := false;
   End;

   If Pos('HGl',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGl',Params)+3,3);
     Val(s,HLinieAttr.L.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then HLinieAttr.L.HGAkt := true
                    else ErrorCode := IncorectLinieSyntax;
     End
     else HLinieAttr.L.HGAkt := false;
   End;
   If Pos('HGm',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGm',Params)+3,3);
     Val(s,HLinieAttr.M.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then HLinieAttr.M.HGAkt := true
                    else ErrorCode := IncorectLinieSyntax;
     End
     else HLinieAttr.M.HGAkt := false;
   End;
   If Pos('HGr',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGr',Params)+3,3);
     Val(s,HLinieAttr.R.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then HLinieAttr.R.HGAkt := true
                    else ErrorCode := IncorectLinieSyntax;
     End
     else HLinieAttr.R.HGAkt := false;
   End;
 End;

Begin
  ErrorCode := 0;
  FilterChars;
  if ErrorCode <> 0 then Exit;
  if (x1 = _Init) AND (x2 = _The) AND (y = _Params) then Exit;
  OldAttr := TextAttr;
  OldTextColor := (OldAttr MOD 16) + ((OldAttr DIV 128) * 128);
  OldTextBackGround := (OldAttr DIV 16) - ((OldAttr DIV 128) * 8);
  sx := WhereX;
  sy := WhereY;
  {Links}
  If HLinieAttr.L.VGAkt = true then TextColor(OldTextColor)
                               else TextColor(HLinieAttr.L.VG);
  If HLinieAttr.L.HGAkt = true then TextBackGround(OldTextBackGround)
                               else TextBackGround(HLinieAttr.L.HG);
  PutStr(h,HLinieAttr.L.Zeichen,x1,y,TextAttr);
  {Mitte}
  If HLinieAttr.M.VGAkt = true then TextColor(OldTextColor)
                               else TextColor(HLinieAttr.M.VG);
  If HLinieAttr.M.HGAkt = true then TextBackGround(OldTextBackGround)
                               else TextBackGround(HLinieAttr.M.HG);
  For i := x1 + 1 to x2 - 1 do
  Begin
    PutStr(h,HLinieAttr.M.Zeichen,i,y,TextAttr);
  End;
  {Rechts}
  If HLinieAttr.R.VGAkt = true then TextColor(OldTextColor)
                               else TextColor(HLinieAttr.R.VG);
  If HLinieAttr.R.HGAkt = true then TextBackGround(OldTextBackGround)
                               else TextBackGround(HLinieAttr.R.HG);
  PutStr(h,HLinieAttr.R.Zeichen,x2,y,TextAttr);

  IF not (Text = '') then
  Begin
    If HLinieAttr.M.VGAkt = true then TextColor(OldTextColor)
                                 else TextColor(HLinieAttr.M.VG);
    If HLinieAttr.M.HGAkt = true then TextBackGround(OldTextBackGround)
                                 else TextBackGround(HLinieAttr.M.HG);
    PutStr(h,' '+Text+' ',((x2-x1) DIV 2) - ((Length(Text)+2) DIV 2) + x1,y,TextAttr);
  End;
  gotoxy(sx,sy);
  TextAttr := OldAttr;
End;

procedure VLinie(x,y1,y2:Integer;Params,Text:String);
var sx,sy,i:Integer;
    OldAttr : Byte;
    OldTextColor : Byte;
    OldTextBackGround : Byte;
 Procedure FilterChars;
 var l : Byte;
     s : String;
     CutS : String;
     CutS2 : String;
     w : Word;
     Err : Integer;
 Begin
   If Pos('Co',Params) > 0 then VLinieAttr.O.Zeichen := Params[Pos('Co',Params) + 2];
   If Pos('Cm',Params) > 0 then VLinieAttr.M.Zeichen := Params[Pos('Cm',Params) + 2];
   If Pos('Cu',Params) > 0 then VLinieAttr.U.Zeichen := Params[Pos('Cu',Params) + 2];

   If Pos('VGo',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGo',Params)+3,3);
     Val(s,VLinieAttr.O.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then VLinieAttr.O.VGAkt := true
                    else ErrorCode := IncorectLinieSyntax;
     End
     else VLinieAttr.O.VGAkt := false;
   End;
   If Pos('VGm',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGm',Params)+3,3);
     Val(s,VLinieAttr.M.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then VLinieAttr.M.VGAkt := true
                    else ErrorCode := IncorectLinieSyntax;
     End
     else VLinieAttr.M.VGAkt := false;
   End;
   If Pos('VGu',Params) > 0 then
   Begin
     s := Copy(Params,Pos('VGu',Params)+3,3);
     Val(s,VLinieAttr.U.VG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then VLinieAttr.U.VGAkt := true
                    else ErrorCode := IncorectLinieSyntax;
     End
     else VLinieAttr.U.VGAkt := false;
   End;

   If Pos('HGo',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGo',Params)+3,3);
     Val(s,VLinieAttr.O.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then VLinieAttr.O.HGAkt := true
                    else ErrorCode := IncorectLinieSyntax;
     End
     else VLinieAttr.O.HGAkt := false;
   End;
   If Pos('HGm',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGm',Params)+3,3);
     Val(s,VLinieAttr.M.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then VLinieAttr.M.HGAkt := true
                    else ErrorCode := IncorectLinieSyntax;
     End
     else VLinieAttr.M.HGAkt := false;
   End;
   If Pos('HGu',Params) > 0 then
   Begin
     s := Copy(Params,Pos('HGu',Params)+3,3);
     Val(s,VLinieAttr.U.HG,Err);
     if Err <> 0 then
     Begin
       if s = 'Akt' then VLinieAttr.U.HGAkt := true
                    else ErrorCode := IncorectLinieSyntax;
     End
     else VLinieAttr.U.HGAkt := false;
   End;
 End;

Begin
  ErrorCode := 0;
  FilterChars;
  if ErrorCode <> 0 then Exit;
  if (x = _Init) AND (y1 = _The) AND (y2 = _Params) then Exit;
  OldAttr := TextAttr;
  OldTextColor := (OldAttr MOD 16) + ((OldAttr DIV 128) * 128);
  OldTextBackGround := (OldAttr DIV 16) - ((OldAttr DIV 128) * 8);
  sx := WhereX;
  sy := WhereY;
  {Oben}
  If VLinieAttr.O.VGAkt = true then TextColor(OldTextColor)
                               else TextColor(VLinieAttr.O.VG);
  If VLinieAttr.O.HGAkt = true then TextBackGround(OldTextBackGround)
                               else TextBackGround(VLinieAttr.O.HG);
  PutStr(h,VLinieAttr.O.Zeichen,x,y1,TextAttr);
  {Mitte}
  If VLinieAttr.M.VGAkt = true then TextColor(OldTextColor)
                               else TextColor(VLinieAttr.M.VG);
  If VLinieAttr.M.HGAkt = true then TextBackGround(OldTextBackGround)
                               else TextBackGround(VLinieAttr.M.HG);
  For i := y1 + 1 to y2 - 1 do
  Begin
    PutStr(h,VLinieAttr.M.Zeichen,x,i,TextAttr);
  End;
  {Unten}
  If VLinieAttr.U.VGAkt = true then TextColor(OldTextColor)
                               else TextColor(VLinieAttr.U.VG);
  If VLinieAttr.U.HGAkt = true then TextBackGround(OldTextBackGround)
                               else TextBackGround(VLinieAttr.U.HG);
  PutStr(h,VLinieAttr.U.Zeichen,x,y2,TextAttr);

  IF not (Text = '') then
  Begin
    If VLinieAttr.M.VGAkt = true then TextColor(OldTextColor)
                                 else TextColor(VLinieAttr.M.VG);
    If VLinieAttr.M.HGAkt = true then TextBackGround(OldTextBackGround)
                                 else TextBackGround(VLinieAttr.M.HG);
    PutStr(v,' '+Text+' ',x,((y2-y1) DIV 2) - ((Length(Text)+2) DIV 2) + y1,TextAttr);
  End;
  gotoxy(sx,sy);
  TextAttr := OldAttr;
End;


procedure InstallGraph(Var Err : Integer);
var
  grDriver : Integer;
  grMode   : Integer;

Begin
  grDriver := Detect;
  InitGraph(grDriver,grMode,'');
  Err := GraphResult;
End;

procedure TonAuf(Lang1 : Word);
var i,l : Integer;
Begin
  nosound;
  i := 40;
  l := 40;
  repeat
    l := l + 1;
    i := i + 1;
    sound(i);
    delay(Lang1);
  until l = 600;
  nosound;
End;

procedure TonAb(Lang1 : Word);
var i,l : Integer;
Begin
  nosound;
  i := 600;
  l := 600;
  repeat
    l := l - 1;
    i := i - 1;
    sound(i);
    delay(Lang1);
  until l = 40;
  nosound;
End;

procedure DateiTon(s:String);
type
    Pack = Record
      Hoehe : LongInt;
      Lange : LongInt;
    End;
var f : file of Pack;
    Ton : Pack;
Begin
  Assign(f,s);
  {$I-}
  reset(f);
  {$I+}
  IF IOResult <> 0 then Exit;
  While FilePos(f) <> FileSize(f) do
  Begin
    read(f,Ton);
    Sound(Ton.Hoehe);
    delay(Ton.Lange);
    Nosound;
  End;
  Close(f);
End;

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

function RechtsBund(s:String) : String;
var Laenge,Blanks,i : Integer;
    BlankZone : String;
Begin
  Laenge := Length(s);
  Blanks := 79 - Laenge;
  BlankZone := '';
  For I := 1 to Blanks do BlankZone := BlankZone + ' ';
  RechtsBund := BlankZone + s;
End;

function GetKey : String;
var
   Event : TEvent;
   s : String;
Begin
  GetKeyEvent(Event);
  Case Event.KeyCode Of
   0 : GetKey := 'Kein';
   1..255 :
          Begin
            System.Str(Event.KeyCode,s);
            GetKey := 'Alt-"Graue"'+s;
          End;
   7745 : GetKey := 'A';
   12354: GetKey := 'B';
   11843: GetKey := 'C';
   8260 : GetKey := 'D';
   4677 : GetKey := 'E';
   8518 : GetKey := 'F';
   8775 : GetKey := 'G';
   9032 : GetKey := 'H';
   5961 : GetKey := 'I';
   9290 : GetKey := 'J';
   9547 : GetKey := 'K';
   9804 : GetKey := 'L';
   12877: GetKey := 'M';
   12622: GetKey := 'N';
   6223 : GetKey := 'O';
   6480 : GetKey := 'P';
   4177 : GetKey := 'Q';
   4946 : GetKey := 'R';
   8019 : GetKey := 'S';
   5204 : GetKey := 'T';
   5717 : GetKey := 'U';
   12118: GetKey := 'V';
   4439 : GetKey := 'W';
   11608: GetKey := 'X';
   11353: GetKey := 'Y';
   5466 : GetKey := 'Z';
   7777 : GetKey := 'a';
   12386: GetKey := 'b';
   11875: GetKey := 'c';
   8292 : GetKey := 'd';
   4709 : GetKey := 'e';
   8550 : GetKey := 'f';
   8807 : GetKey := 'g';
   9064 : GetKey := 'h';
   5993 : GetKey := 'i';
   9322 : GetKey := 'j';
   9579 : GetKey := 'k';
   9836 : GetKey := 'l';
   12909: GetKey := 'm';
   12654: GetKey := 'n';
   6255 : GetKey := 'o';
   6512 : GetKey := 'p';
   4209 : GetKey := 'q';
   4978 : GetKey := 'r';
   8051 : GetKey := 's';
   5236 : GetKey := 't';
   5749 : GetKey := 'u';
   12150: GetKey := 'v';
   4471 : GetKey := 'w';
   11640: GetKey := 'x';
   11385: GetKey := 'y';
   5498 : GetKey := 'z';
   7681 : GetKey := 'Strg-A';
   12290: GetKey := 'Strg-B';
   11779: GetKey := 'Strg-C';
   8196 : GetKey := 'Strg-D';
   4613 : GetKey := 'Strg-E';
   8454 : GetKey := 'Strg-F';
   8711 : GetKey := 'Strg-G';
   8968 : GetKey := 'Strg-H';
   5897 : GetKey := 'Strg-I';
   9226 : GetKey := 'Strg-J';
   9483 : GetKey := 'Strg-K';
   9740 : GetKey := 'Strg-L';
   12813: GetKey := 'Strg-M';
   12558: GetKey := 'Strg-N';
   6159 : GetKey := 'Strg-O';
   6416 : GetKey := 'Strg-P';
   4113 : GetKey := 'Strg-Q';
   4882 : GetKey := 'Strg-R';
   7955 : GetKey := 'Strg-S';
   5140 : GetKey := 'Strg-T';
   5653 : GetKey := 'Strg-U';
   1205 : GetKey := 'Strg-V';
   4375 : GetKey := 'Strg-W';
   11544: GetKey := 'Strg-X';
   11289: GetKey := 'Strg-Y';
   5402 : GetKey := 'Strg-Z';
   7680 : GetKey := 'Alt-A';
   12288: GetKey := 'Alt-B';
   11776: GetKey := 'Alt-C';
   8192 : GetKey := 'Alt-D';
   4608 : GetKey := 'Alt-E';
   8448 : GetKey := 'Alt-F';
   8704 : GetKey := 'Alt-G';
   8960 : GetKey := 'Alt-H';
   5888 : GetKey := 'Alt-I';
   9216 : GetKey := 'Alt-J';
   9472 : GetKey := 'Alt-K';
   9728 : GetKey := 'Alt-L';
   12800: GetKey := 'Alt-M';
   12544: GetKey := 'Alt-N';
   6144 : GetKey := 'Alt-O';
   6400 : GetKey := 'Alt-P';
   4096 : GetKey := 'Alt-Q';
   4864 : GetKey := 'Alt-R';
   7936 : GetKey := 'Alt-S';
   5120 : GetKey := 'Alt-T';
   5632 : GetKey := 'Alt-U';
   12032: GetKey := 'Alt-V';
   4352 : GetKey := 'Alt-W';
   11520: GetKey := 'Alt-X';
   5376 : GetKey := 'Alt-Y';
   11264: GetKey := 'Alt-Z';
   30720: GetKey := 'Alt-"Normale"1';
   30976: GetKey := 'Alt-"Normale"2';
   31232: GetKey := 'Alt-"Normale"3';
   31488: GetKey := 'Alt-"Normale"4';
   31744: GetKey := 'Alt-"Normale"5';
   32000: GetKey := 'Alt-"Normale"6';
   32256: GetKey := 'Alt-"Normale"7';
   32512: GetKey := 'Alt-"Normale"8';
   32768: GetKey := 'Alt-"Normale"9';
   33024: GetKey := 'Alt-"Normale"0';
   15104: GetKey := 'F1';
   15360: GetKey := 'F2';
   15616: GetKey := 'F3';
   15872: GetKey := 'F4';
   16128: GetKey := 'F5';
   16384: GetKey := 'F6';
   16640: GetKey := 'F7';
   16896: GetKey := 'F8';
   17152: GetKey := 'F9';
   17408: GetKey := 'F10';
   24064: GetKey := 'Strg-F1';
   24320: GetKey := 'Strg-F2';
   24576: GetKey := 'Strg-F3';
   24832: GetKey := 'Strg-F4';
   25088: GetKey := 'Strg-F5';
   25344: GetKey := 'Strg-F6';
   25600: GetKey := 'Strg-F7';
   25856: GetKey := 'Strg-F8';
   26112: GetKey := 'Strg-F9';
   26368: GetKey := 'Strg-F10';
   26624: GetKey := 'Alt-F1';
   26880: GetKey := 'Alt-F2';
   27136: GetKey := 'Alt-F3';
   27392: GetKey := 'Alt-F4';
   27648: GetKey := 'Alt-F5';
   27904: GetKey := 'Alt-F6';
   28160: GetKey := 'Alt-F7';
   28416: GetKey := 'Alt-F8';
   28672: GetKey := 'Alt-F9';
   28928: GetKey := 'Alt-F10';
   20992: GetKey := 'Einfg';
   18176: GetKey := 'Pos1';
   18688: GetKey := 'BildAuf';
   21248: GetKey := 'Entf';
   20224: GetKey := 'Ende';
   20736: GetKey := 'BildAb';
   1024 : GetKey := 'Strg-Einfg';
   30464: GetKey := 'Strg-Pos1';
   33792: GetKey := 'Strg-BildAuf';
   1536 : GetKey := 'Strg-Entf';
   29952: GetKey := 'Strg-Ende';
   30208: GetKey := 'Strg-BildAb';
   7181 : GetKey := 'Return';
   3592 : GetKey := 'Backspace';
   18432: GetKey := 'Oben';
   19200: GetKey := 'Links';
   20480: GetKey := 'Unten';
   19712: GetKey := 'Rechts';
   283  : GetKey := 'Esc';
   3849 : GetKey := 'Tab';
   3840 : GetKey := 'Umschalt-Tab';
   13615: GetKey := '"Graues"/';
   14122: GetKey := '"Graues"*';
   18989: GetKey := '"Graues"-';
   20011: GetKey := '"Graues"+';
   21292: GetKey := '"Graues",';
   21040: GetKey := '"Graue"0';
   20273: GetKey := '"Graue"1';
   20530: GetKey := '"Graue"2';
   20787: GetKey := '"Graue"3';
   19252: GetKey := '"Graue"4';
   19509: GetKey := '"Graue"5';
   19766: GetKey := '"Graue"6';
   18231: GetKey := '"Graue"7';
   18488: GetKey := '"Graue"8';
   18745: GetKey := '"Graue"9';
   545  : GetKey := '!';
   802  : GetKey := '"';
   1045 : GetKey := '';
   1316 : GetKey := '$';
   1573 : GetKey := '%';
   1830 : GetKey := '&';
   2095 : GetKey := '/';
   2344 : GetKey := '(';
   2601 : GetKey := ')';
   2877 : GetKey := '=';
   3135 : GetKey := '?';
   1021 : GetKey := 'ý';
   1276 : GetKey := 'ü';
   2171 : GetKey := '{';
   2395 : GetKey := '[';
   2653 : GetKey := ']';
   2941 : GetKey := '}';
   3164 : GetKey := '\';
   94   : GetKey := '^';
   10744: GetKey := 'ø';
   22076: GetKey := '<';
   22078: GetKey := '>';
   22140: GetKey := '|';
   13030: GetKey := 'æ';
   13100: GetKey := ',';
   13115: GetKey := ';';
   13358: GetKey := '.';
   13370: GetKey := ':';
   13613: GetKey := '-';
   13663: GetKey := '_';
   11043: GetKey := '#';
   11047: GetKey := '''';
   6955 : GetKey := '+';
   7038 : GetKey := '~';
   6954 : GetKey := '*';
   else GetKey := Event.CharCode;
  End;
End;

function StrZahl(Str : String) : Integer;
var Error,Zahl : Integer;
Begin
  Val(Str,Zahl,Error);
  StrZahl := Zahl;
End;

procedure Ton(Laenge,Oktave,Note:Integer);
var eintakt : Integer;
    lang,I  : Integer;
    notwert : Real;
Begin
  eintakt := (60000 DIV Takt) * 4;
  if laenge > 1000 then
  Begin
    laenge := laenge - 1000;
    lang := eintakt DIV laenge;
    lang := lang + (lang DIV 2);
  End
  else
  lang := eintakt DIV laenge;
  if oktave = -2 then notwert := 69.302081;
  if oktave = -1 then notwert := 138.59935;
  if oktave = 0 then notwert := 261.6324;
  if oktave = 1 then notwert := 523.24653;
  if oktave = 2 then notwert := 1046.4263;
  if Note <> 1 then
  Begin
    For I := 2 to Note do
    Begin
      notwert := notwert * 1.05946
    End;
  End;
  if Note < 13 then sound(Round(notwert));
  delay(lang);
  NoSound;
End;

function Str(Zahl:Longint) : String;
var s : String;
Begin
  System.Str(Zahl,S);
  Extra1.Str := s;
End;

Procedure WordToBin(W:Word; var Bin:String);
var LI : LongInt;
Begin
  Bin := '';
  LI := W;
  If (LI - 32768) >= 0 Then
  Begin
    Bin := Bin + '1';
    LI := LI - 32768;
  End
  else Bin := Bin + '0';
  If (LI - 16384) >= 0 Then
  Begin
    Bin := Bin + '1';
    LI := LI - 16384;
  End
  else Bin := Bin + '0';
  If (LI - 8192) >= 0 Then
  Begin
    Bin := Bin + '1';
    LI := LI - 8192;
  End
  else Bin := Bin + '0';
  If (LI - 4096) >= 0 Then
  Begin
    Bin := Bin + '1';
    LI := LI - 4096;
  End
  else Bin := Bin + '0';
  If (LI - 2048) >= 0 Then
  Begin
    Bin := Bin + '1';
    LI := LI - 2048;
  End
  else Bin := Bin + '0';
  If (LI - 1024) >= 0 Then
  Begin
    Bin := Bin + '1';
    LI := LI - 1024;
  End
  else Bin := Bin + '0';
  If (LI - 512) >= 0 Then
  Begin
    Bin := Bin + '1';
    LI := LI - 512;
  End
  else Bin := Bin + '0';
  If (LI - 256) >= 0 Then
  Begin
    Bin := Bin + '1';
    LI := LI - 256;
  End
  else Bin := Bin + '0';
  If (LI - 128) >= 0 Then
  Begin
    Bin := Bin + '1';
    LI := LI - 128;
  End
  else Bin := Bin + '0';
  If (LI - 64) >= 0 Then
  Begin
    Bin := Bin + '1';
    LI := LI - 64;
  End
  else Bin := Bin + '0';
  If (LI - 32) >= 0 Then
  Begin
    Bin := Bin + '1';
    LI := LI - 32;
  End
  else Bin := Bin + '0';
  If (LI - 16) >= 0 Then
  Begin
    Bin := Bin + '1';
    LI := LI - 16;
  End
  else Bin := Bin + '0';
  If (LI - 8) >= 0 Then
  Begin
    Bin := Bin + '1';
    LI := LI - 8;
  End
  else Bin := Bin + '0';
  If (LI - 4) >= 0 Then
  Begin
    Bin := Bin + '1';
    LI := LI - 4;
  End
  else Bin := Bin + '0';
  If (LI - 2) >= 0 Then
  Begin
    Bin := Bin + '1';
    LI := LI - 2;
  End
  else Bin := Bin + '0';
  If (LI - 1) >= 0 Then
  Begin
    Bin := Bin + '1';
    LI := LI - 1;
  End
  else Bin := Bin + '0';
End;

Procedure AddEntry(var Mogl:WahlRec;Entry:String;Init:Boolean);
var I  : Integer;
Begin
  If Init = DoInit then
  Begin
    For I := 1 to 23 do Mogl.Moglich[I] := '';
    Mogl.Anz := 0;
  End;
  if Mogl.Anz < 23 then inc(Mogl.Anz)
                   else Begin
                          Write('Error: Number of entries is higher than maximum (AddEntry)');
                          Exit;
                        End;
  Mogl.Moglich[Mogl.Anz] := Entry;
End;

function Auswahl(Mogl:WahlRec) : String;
var x,y,MaxLang,I,J,Pos:Integer;
    Key : Char;
Begin
  textbackground(1);
  textcolor(15);
  x := WhereX;
  y := WhereY;
  MaxLang := 0;
  For I := 1 to Mogl.Anz do
  Begin
    if MaxLang < Length(Mogl.Moglich[I]) then MaxLang := Length(Mogl.Moglich[I]);
  End;
  textbackground(1);
  For I := x to x + MaxLang + 1 do
   For J := y to y + Mogl.Anz + 1 do
   Begin
     gotoxy(I,J);
     write(' ');
   End;
  gotoxy(x,y);
  write('É'); For I := x+1 to x+MaxLang do write('Í'); write('»');
  gotoxy(x,y+Mogl.Anz+1);
  write('È');For I := x+1 to x+MaxLang do write('Í'); write('¼');
  Pos := 1;
  repeat
   textbackground(1);
   For I := 1 to Mogl.Anz do
   Begin
     gotoxy(x,y+I);
     write('º',Mogl.Moglich[I]);
     gotoxy(x+MaxLang+1,WhereY); write('º');
   End;
   textbackground(0);
   gotoxy(x+1,y+Pos);
   write(Mogl.Moglich[Pos]);
   Key := readkey;
   if Key = #80 then if Pos < Mogl.Anz then Pos := Pos + 1 else Pos := 1; {Unten}
   if Key = #72 then if Pos > 1 then Pos := Pos - 1 else Pos := Mogl.Anz; {Oben}
   if Key = #27 then Begin Auswahl := 'Esc'; Exit End;
  until Key = #13;
  Auswahl := Mogl.Moglich[Pos];
End;

function TA(VG,HG:Byte):Byte;
var Savi:Byte;
Begin
  Savi := TextAttr;
  TextColor(VG);
  TextBackground(Hg);
  TA := TextAttr;
  TextAttr := Savi;
End;

procedure BlinkBit(Switch : boolean);
Begin
  asm
    mov AX, 1003h
    mov Bl, Switch
    int 10h
  end;
  BB := Switch;
end;

Begin
  takt := 96;
  XMax := GetMaxX;
  YMax := GetMaxY;
  Fenster(_Init,_Only,_The,_Params,OneLine,'wird net gezeichnet','auch net');
  BlinkBit(On);
End.
