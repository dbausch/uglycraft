{ BufFlush variant implementations.
  Included by UGLI_2_Bench.pp (for benchmarking) and UGLI_2_Test.pp
  (for output-correctness tests).  Must appear after UGLI_2_Core.inc
  because V2/V3 use Screen, Dirty, TTY, BufFlushEnabled, WBuf, and
  RawTTYFd from core. }

type
  TFlushProc = procedure;

{ ------------------------------------------------------------------ }
{ V2: skip ESC[r;cH when cursor is already at the next cell         }
{ ------------------------------------------------------------------ }

procedure BufFlushV2;
const AnsiClr: array[0..7] of Byte = (0, 4, 2, 6, 1, 5, 3, 7);
var Col, Row, LastFg, LastBg, FgCode, BgCode, LastCol, LastRow: Integer;
begin
  if not BufFlushEnabled then
    begin
      for Col := 1 to ScreenW do
        for Row := 1 to ScreenH do
          Dirty[Col, Row] := false;
      Exit;
    end;
  Write(TTY, #27'[?7l');
  LastFg := -1; LastBg := -1; LastCol := -1; LastRow := -1;
  for Row := 1 to ScreenH do
    for Col := 1 to ScreenW do
      if Dirty[Col, Row] then
        begin
          if (Screen[Col, Row].Fg <> LastFg) or (Screen[Col, Row].Bg <> LastBg) then
            begin
              if Screen[Col, Row].Fg < 8 then
                FgCode := 30 + AnsiClr[Screen[Col, Row].Fg]
              else
                FgCode := 90 + AnsiClr[Screen[Col, Row].Fg - 8];
              BgCode := 40 + AnsiClr[Screen[Col, Row].Bg and 7];
              Write(TTY, #27'[0;', FgCode, ';', BgCode, 'm');
              LastFg := Screen[Col, Row].Fg;
              LastBg := Screen[Col, Row].Bg;
            end;
          if (Col <> LastCol + 1) or (Row <> LastRow) then
            Write(TTY, #27'[', Row, ';', Col, 'H');
          Write(TTY, Screen[Col, Row].Ch);
          LastCol := Col;
          LastRow := Row;
          Dirty[Col, Row] := false;
        end;
  Write(TTY, #27'[?7h');
  Flush(TTY);
end;

{ ------------------------------------------------------------------ }
{ V3: per row, position once at first dirty cell, write span        }
{ Clean cells inside the span are still correct — Screen always     }
{ holds the current display state.                                   }
{ ------------------------------------------------------------------ }

procedure BufFlushV3;
const AnsiClr: array[0..7] of Byte = (0, 4, 2, 6, 1, 5, 3, 7);
var Col, Row, LastFg, LastBg, FgCode, BgCode, First, Last: Integer;
begin
  if not BufFlushEnabled then
    begin
      for Col := 1 to ScreenW do
        for Row := 1 to ScreenH do
          Dirty[Col, Row] := false;
      Exit;
    end;
  Write(TTY, #27'[?7l');
  LastFg := -1; LastBg := -1;
  for Row := 1 to ScreenH do
    begin
      First := 0; Last := 0;
      for Col := 1 to ScreenW do
        if Dirty[Col, Row] then
          begin
            if First = 0 then First := Col;
            Last := Col;
          end;
      if First = 0 then Continue;
      Write(TTY, #27'[', Row, ';', First, 'H');
      for Col := First to Last do
        begin
          if (Screen[Col, Row].Fg <> LastFg) or (Screen[Col, Row].Bg <> LastBg) then
            begin
              if Screen[Col, Row].Fg < 8 then
                FgCode := 30 + AnsiClr[Screen[Col, Row].Fg]
              else
                FgCode := 90 + AnsiClr[Screen[Col, Row].Fg - 8];
              BgCode := 40 + AnsiClr[Screen[Col, Row].Bg and 7];
              Write(TTY, #27'[0;', FgCode, ';', BgCode, 'm');
              LastFg := Screen[Col, Row].Fg;
              LastBg := Screen[Col, Row].Bg;
            end;
          Write(TTY, Screen[Col, Row].Ch);
          Dirty[Col, Row] := false;
        end;
    end;
  Write(TTY, #27'[?7h');
  Flush(TTY);
end;

{ ------------------------------------------------------------------ }
{ V2b: V2 algorithm, all output buffered, emitted via one fpWrite   }
{ ------------------------------------------------------------------ }

procedure BufFlushV2b;
const AnsiClr: array[0..7] of Byte = (0, 4, 2, 6, 1, 5, 3, 7);
var Col, Row, LastFg, LastBg, FgCode, BgCode, LastCol, LastRow: Integer;
begin
  if not BufFlushEnabled then
    begin
      for Col := 1 to ScreenW do
        for Row := 1 to ScreenH do
          Dirty[Col, Row] := false;
      Exit;
    end;
  WBufPos := 0;
  WB(#27'[?7l');
  LastFg := -1; LastBg := -1; LastCol := -1; LastRow := -1;
  for Row := 1 to ScreenH do
    for Col := 1 to ScreenW do
      if Dirty[Col, Row] then
        begin
          if (Screen[Col, Row].Fg <> LastFg) or (Screen[Col, Row].Bg <> LastBg) then
            begin
              if Screen[Col, Row].Fg < 8 then
                FgCode := 30 + AnsiClr[Screen[Col, Row].Fg]
              else
                FgCode := 90 + AnsiClr[Screen[Col, Row].Fg - 8];
              BgCode := 40 + AnsiClr[Screen[Col, Row].Bg and 7];
              WB(#27'[0;'); WBInt(FgCode); WB(';'); WBInt(BgCode); WB('m');
              LastFg := Screen[Col, Row].Fg;
              LastBg := Screen[Col, Row].Bg;
            end;
          if (Col <> LastCol + 1) or (Row <> LastRow) then
            begin WB(#27'['); WBInt(Row); WB(';'); WBInt(Col); WB('H'); end;
          WBCh(Screen[Col, Row].Ch);
          LastCol := Col;
          LastRow := Row;
          Dirty[Col, Row] := false;
        end;
  WB(#27'[?7h');
  WBFlush;
end;

{ ------------------------------------------------------------------ }
{ V3b: V3 algorithm, all output buffered, emitted via one fpWrite   }
{ ------------------------------------------------------------------ }

procedure BufFlushV3b;
const AnsiClr: array[0..7] of Byte = (0, 4, 2, 6, 1, 5, 3, 7);
var Col, Row, LastFg, LastBg, FgCode, BgCode, First, Last: Integer;
begin
  if not BufFlushEnabled then
    begin
      for Col := 1 to ScreenW do
        for Row := 1 to ScreenH do
          Dirty[Col, Row] := false;
      Exit;
    end;
  WBufPos := 0;
  WB(#27'[?7l');
  LastFg := -1; LastBg := -1;
  for Row := 1 to ScreenH do
    begin
      First := 0; Last := 0;
      for Col := 1 to ScreenW do
        if Dirty[Col, Row] then
          begin
            if First = 0 then First := Col;
            Last := Col;
          end;
      if First = 0 then Continue;
      WB(#27'['); WBInt(Row); WB(';'); WBInt(First); WB('H');
      for Col := First to Last do
        begin
          if (Screen[Col, Row].Fg <> LastFg) or (Screen[Col, Row].Bg <> LastBg) then
            begin
              if Screen[Col, Row].Fg < 8 then
                FgCode := 30 + AnsiClr[Screen[Col, Row].Fg]
              else
                FgCode := 90 + AnsiClr[Screen[Col, Row].Fg - 8];
              BgCode := 40 + AnsiClr[Screen[Col, Row].Bg and 7];
              WB(#27'[0;'); WBInt(FgCode); WB(';'); WBInt(BgCode); WB('m');
              LastFg := Screen[Col, Row].Fg;
              LastBg := Screen[Col, Row].Bg;
            end;
          WBCh(Screen[Col, Row].Ch);
          Dirty[Col, Row] := false;
        end;
    end;
  WB(#27'[?7h');
  WBFlush;
end;
