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

## Note on "many ALSA probe messages"

The `SuppressStderr` wrapper in `UOSSound.Init` was introduced because PortAudio
writes "failure messages for absent hardware directly to fd 2" during its backend
probe.  These only appear when a backend (JACK, OSS, a missing sound card) fails
to initialise.  On a system where ALSA finds all its configured devices cleanly,
the probe succeeds silently and nothing is written to fd 2.

A `--stderr-log` run on such a system will produce an empty (or near-empty) log
file — the redirect mechanism is correct (confirmed by an ALSA underrun message
that did appear in the log during playback), but the probe generates no output
when audio hardware is clean.

---

## Done when

- [x] `poe build-original` exits 0 (da21e2c)
- [x] `poe test-original` exits 0, 125 tests pass (da21e2c)
- [x] `--stderr-log <file>` captures fd-2 output instead of corrupting the
      terminal — confirmed working: one ALSA underrun message appeared in the
      log during a playback test; probe messages absent because this system's
      audio config is clean
