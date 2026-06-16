# Unified stderr sink: --stderr-log option and test coverage

## Status

- [x] `InitStderrSink(LogFile: string)` in `UGLI_2_Core.inc`
- [x] `--stderr-log <path>` option parsed via `ParseCLI` / getopts in `UGLI_2_Core.inc`; old `DevNull` inline code removed
- [x] `SuppressStderr` / `RestoreStderr` removed from `UOSSound.pp`
- [x] `TStderrSinkTests` added to `UGLI_2_Test.pp`
- [x] `poe build-original` passes
- [x] `poe test-original` passes (125+ tests, all green)

---

## Motivation

Two independent stderr suppressions existed for the same underlying reason —
library noise must not corrupt terminal rendering — but with different scopes:

| Location | Scope | Mechanism |
|---|---|---|
| `UGLI_2.pp` startup | permanent, entire run | inline `fpDup2('/dev/null', 2)` |
| `UOSSound.Init` | temporary, PortAudio probe only | `SuppressStderr` / `RestoreStderr` |

The `UOSSound` pair was designed to restore stderr after init so that
post-init ALSA messages (buffer-underrun warnings during playback) would still
be visible.  Once the permanent redirect was added to `UGLI_2.pp`, the restore
in `UOSSound` became a no-op: it saved `/dev/null`, redirected to `/dev/null`,
then restored `/dev/null`.

This refactor:
1. Unifies the mechanism into one procedure.
2. Lets the user route stderr to a log file for diagnosing sound issues.
3. Adds tests.

---

## What changes

### `UGLI_2_Core.inc` — new procedure (near top, before `WB`)

```pascal
{ Route stderr (fd 2) to LogFile for the lifetime of the process.
  Empty LogFile → /dev/null (silence). Non-empty → open/create/truncate that
  path. A user experiencing sound issues can pass --stderr-log <file> to
  capture ALSA / PortAudio diagnostics without terminal corruption. }
procedure InitStderrSink(const LogFile: string);
var Fd: cint;
begin
  if LogFile = '' then
    Fd := fpOpen('/dev/null', O_WRONLY)
  else
    Fd := fpOpen(LogFile, O_WRONLY or O_CREAT or O_TRUNC, $1A4);
  if Fd >= 0 then
    begin
      fpDup2(Fd, 2);
      fpClose(Fd);
    end;
end;
```

### `UGLI_2.pp`

Replace the inline `DevNull` block and `DevNull: cint` var with:

```pascal
var
  Tio      : Termios;
  StderrLog: string;

begin
  StderrLog := '';
  for I := 1 to ParamCount - 1 do
    if ParamStr(I) = '--stderr-log' then
      StderrLog := ParamStr(I + 1);
  InitStderrSink(StderrLog);
  { ... rest of startup unchanged ... }
```

(Later superseded by the `ParseCLI` / getopts refactor in commit `83e6beb`, which
moved `StderrLog` into `UGLI_2_Core.inc` as a global and routes it through
`ParseCLI`.)

### `UOSSound.pp`

Remove `SuppressStderr`, `RestoreStderr`, their `savedErr` variable, and the
two calls in `Init` (`savedErr := SuppressStderr` and `RestoreStderr(savedErr)`).
The main program's `InitStderrSink` already handles fd 2 permanently before
`Init` is ever called.

### `UGLI_2_Test.pp` — new class `TStderrSinkTests`

`SetUp` saves fd 2 via `fpDup(2)`.  `TearDown` restores it.  This lets each
test call `InitStderrSink` without permanently affecting the test runner's own
stderr.

| Test | Assertion |
|---|---|
| `TestSink_NullSilences` | After `InitStderrSink('')`: `fpWrite(2, …)` succeeds (returns > 0); fd 2 is a character device (fstat `S_IFCHR`) |
| `TestSink_LogFileCaptures` | After `InitStderrSink(tmpfile)`: `fpWrite(2, …)` with known bytes; read file back; bytes match |
| `TestSink_LogFileTruncates` | Call `InitStderrSink` twice on same path; second write overwrites first; file contains only second write's bytes |

---

## Note on ALSA probe messages and PipeWire

The original display corruption was caused by ALSA/PortAudio writing backend
probe failure messages directly to fd 2 during `Pa_Initialize()` — one message
per absent or misconfigured audio backend (JACK, OSS, surround PCM, etc.).

These messages only appear when a backend probe **fails**.  On this system,
PipeWire provides a complete ALSA emulation layer, so every probe that
PortAudio issues succeeds silently.  A minimal test (`ProbeSound.pp` — compiled
and run 2026-06-16, then deleted) confirmed this: calling `Ton()` → `UOSSound.Init`
produced no output whatsoever on fd 2 in an interactive PipeWire session.

A headless C test (same session, no PipeWire audio context) did produce the
expected probe messages, confirming that the `dup2` redirect mechanism is
correct and that messages reach a log file when they are generated.

**Consequence for the spec:** The `--stderr-log` option cannot be confirmed by
observing probe messages on this machine.  The acceptance criterion is met by:
1. `TStderrSinkTests` (three unit tests covering null-sink and log-file capture).
2. Absence of display corruption during play (display was clean since da21e2c).
3. On a system without PipeWire ALSA emulation, probe messages would appear in
   the log file exactly as intended.

---

## Done when

- [x] `poe build-original` exits 0 (da21e2c)
- [x] `poe test-original` exits 0, 125 tests pass (da21e2c)
- [ ] `--stderr-log <file>` captures ALSA probe messages in the log (cannot
      confirm on this machine — PipeWire silences the probe; display corruption
      is gone, TStderrSinkTests pass)
