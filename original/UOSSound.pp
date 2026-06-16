unit UOSSound;

{ Sound wrapper for UGLI 2 FPC port.
  Provides Sound(Hz)/NoSound/Ton(Hz,Ms) backed by UOS + PortAudio.
  Falls back to silence if PortAudio is not installed. }

{$mode objfpc}{$H+}

interface

{ Replaces CRT stubs — list UOSSound after crt in uses clause. }
procedure Sound(Hz: Word);
procedure NoSound;

{ Play Hz for Ms milliseconds synchronously. }
procedure Ton(Hz: Word; Ms: Integer);

{ Named sound effects. }
procedure SoundBump;      { wall bump — low 40 Hz blip }
procedure SoundPickup;    { treasure collected }
procedure SoundCaught;    { player caught by enemy }
procedure SoundGameOver;  { game over fanfare }
procedure SoundWon;       { level/game won fanfare }

implementation

uses ctypes, SysUtils, BaseUnix, uos_flat;

const
  PA_LIBS: array[0..1] of string = ('libportaudio.so.2', 'libportaudio.so');

var
  FReady:   Boolean  = False;
  FPlaying: Boolean  = False;
  FPlayer:  cint32   = 0;
  FInput:   cint32   = -1;

{ InitStderrSink in UGLI_2_Core.inc handles fd 2 permanently at startup;
  no per-call suppression needed here. }

procedure Init;
var
  loaded: Boolean;
  i: Integer;
begin
  if FReady then Exit;
  FReady := True;  { mark attempted so we never retry on failure }

  loaded := False;
  for i := 0 to High(PA_LIBS) do
    if uos_LoadLib(PChar(PA_LIBS[i]), nil, nil, nil, nil, nil) = 0 then
    begin
      loaded := True;
      Break;
    end;

  if not loaded then Exit;

  if not uos_CreatePlayer(FPlayer) then Exit;

  { Stereo square wave, silent (volume=0), endless when active.
    duration=-1 sets 1000 ms initially; we switch to endless below. }
  FInput := uos_AddFromSynth(FPlayer, -1, 1, 1, 440, 440, 0, 0,
                              -1, 0, 0, 0, -1, -1, -1);
  if FInput < 0 then Exit;

  if uos_AddIntoDevOut(FPlayer) < 0 then
  begin
    FInput := -1;
    Exit;
  end;

  uos_PlayNoFree(FPlayer);
  FPlaying := True;
  Sleep(150); { wait for audio thread to initialise }

  { Switch to endless (duration=0 → dursine=0) at volume=0 }
  uos_InputSetSynth(FPlayer, FInput, -1, -1, -1, -1, 0, 0, 0, -1, -1, True);
end;

procedure Sound(Hz: Word);
begin
  Init;
  if FInput < 0 then Exit;
  uos_InputSetSynth(FPlayer, FInput, -1, -1, Hz, Hz, 0.5, 0.5, 0, -1, -1, True);
end;

procedure NoSound;
begin
  if FInput < 0 then Exit;
  uos_InputSetSynth(FPlayer, FInput, -1, -1, -1, -1, 0, 0, -1, -1, -1, True);
end;

procedure Ton(Hz: Word; Ms: Integer);
begin
  Sound(Hz);
  Sleep(Ms);
  NoSound;
end;

procedure SoundBump;
begin
  Ton(40, 5);
end;

procedure SoundPickup;
begin
  Ton(250, 50);
end;

procedure SoundCaught;
begin
  Ton(80, 200);
end;

procedure SoundGameOver;
var
  i: Integer;
begin
  Ton(200, 100);
  Ton(150, 100);
  Ton(200, 100);
  Ton(150, 100);
  Ton(100, 100);
  NoSound;
  Sleep(200);
  i := 600;
  while i > 0 do
  begin
    Sound(i);
    Sleep(3);
    Dec(i);
  end;
  NoSound;
  Sleep(1000);
end;

procedure SoundWon;
begin
  Ton(100, 500);
  Ton(200, 500);
  Ton(300, 500);
  Ton(400, 500);
end;

finalization
  if FPlaying then uos_stop(FPlayer);
  if FReady   then uos_free;
end.
