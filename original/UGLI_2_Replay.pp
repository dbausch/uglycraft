{$H+}
{ Replay utility for WBFlush dumps produced by UGLI_2 (F6 to record).
  Each write in the dump is a raw byte sequence terminated by a 0x00 sentinel.
  Usage: UGLI_2_Replay <dump_file> [n_writes]
  Writes the first n_writes chunks to stdout so the terminal renders them. }
program UGLI_2_Replay;

uses BaseUnix, SysUtils;

const MaxDumpSize = 8 * 1024 * 1024; { 8 MB — covers any reasonable session }

var
  DumpFile : string;
  MaxWrites: LongInt;
  Buf      : PByte;
  F        : cint;
  BytesRead: SizeInt;
  I, ChunkStart, WriteCount: LongInt;

begin
  if ParamCount < 1 then
    begin
      WriteLn(StdErr, 'Usage: UGLI_2_Replay <dump_file> [n_writes]');
      WriteLn(StdErr, '  Replays the first n_writes WBFlush writes to stdout.');
      WriteLn(StdErr, '  Omit n_writes to replay all writes.');
      Halt(1);
    end;

  DumpFile := ParamStr(1);

  if ParamCount >= 2 then
    MaxWrites := StrToInt(ParamStr(2))
  else
    MaxWrites := MaxLongInt;

  F := fpOpen(DumpFile, O_RDONLY);
  if F < 0 then
    begin
      WriteLn(StdErr, 'Cannot open: ', DumpFile);
      Halt(1);
    end;

  GetMem(Buf, MaxDumpSize);
  BytesRead := fpRead(F, Buf^, MaxDumpSize);
  fpClose(F);

  if BytesRead <= 0 then
    begin
      WriteLn(StdErr, 'Empty or unreadable dump file: ', DumpFile);
      FreeMem(Buf);
      Halt(1);
    end;

  WriteCount := 0;
  ChunkStart := 0;
  for I := 0 to BytesRead - 1 do
    begin
      if Buf[I] = 0 then
        begin
          if (I > ChunkStart) and (WriteCount < MaxWrites) then
            fpWrite(1, Buf[ChunkStart], I - ChunkStart);
          Inc(WriteCount);
          ChunkStart := I + 1;
          if WriteCount >= MaxWrites then
            Break;
        end;
    end;

  fpWrite(1, PChar(#27'[26;1H'#27'[?7h'#27'[0m')^, 16);
  WriteLn(StdErr, 'Replayed ', WriteCount, ' write(s).');
  FreeMem(Buf);
end.
