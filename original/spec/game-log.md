# Game log: --log / -l option and structured log entries

## Status

- [x] `--stderr-log` renamed to `--log`; short option `-l` added; `--level` loses short form — `278155b`
- [x] `LogFile: string` global replaces `StderrLog`; `LogFd: cint = -1` global added — `278155b`
- [x] `OpenLog(FileName)` replaces `InitStderrSink`: opens file, redirects fd 2, keeps `LogFd` — `278155b`
- [x] `Log(Msg)` procedure writes timestamped line to `LogFd` — `278155b`
- [x] Log entries written: started (version), flags, sound backend, gameplay events, exit — `278155b`
- [x] `UOSSound.Init` writes sound-backend status to fd 2 (reaches log via redirect) — `278155b`
- [x] `TLogTests` replaces `TStderrSinkTests` — all renamed tests green plus new `TestLog_Writes` — `278155b`
- [x] `poe build-original` passes
- [x] `poe test-original` passes
- [x] `poe run-original --log /tmp/ugli.log` produces a readable log — user confirmed 2026-06-17

---

## Motivation

`--stderr-log` was introduced to capture ALSA/PortAudio probe noise.  The
probe is now silent on this system (PipeWire provides clean ALSA emulation),
so the log file was always empty and could never be confirmed.

The option stays useful if the library noise ever returns, but needs to earn
its keep independently: structured game-event entries give it immediate,
testable value and make it a genuine diagnostic tool.

---

## What changes

### CLI rename

| Before | After |
|---|---|
| `--stderr-log <file>` | `--log <file>` |
| `-e <file>` (internal val, never documented) | `-l <file>` (user-visible short form) |
| `--level` val `'l'` | `--level` val `'n'` (internal only, no short form) |

ShortOpts string: `':h'` → `':hl:'`

### `UGLI_2_Core.inc`

**Globals:**
```pascal
LogFile: string = '';  { was StderrLog }
LogFd  : cint   = -1; { kept open for Log() when --log is active }
```

**`OpenLog(const FileName: string)`** (replaces `InitStderrSink`):
- Empty `FileName` → redirect fd 2 to `/dev/null`; `LogFd` stays `-1`
- Non-empty → open/create/truncate file; redirect fd 2 to it; **keep fd open as `LogFd`**

**`Log(const Msg: string)`** (new):
- If `LogFd < 0`, no-op (preserves zero overhead when no log is active)
- Otherwise writes `yyyy-mm-dd hh:nn:ss  <Msg>` + newline to `LogFd`

**Resourcestrings:**
```pascal
sCliLog1 = 'Write a structured log (timestamp, version, flags, game events) to <file>.';
sCliLog2 = 'Library diagnostic messages (ALSA/PortAudio) are also routed there.';
```

**Help text entry:** `'-l, --log <file>'`

**ParseCLI:**
```pascal
Opts[2].SetOption('level', Required_Argument, nil, 'n');  { was 'l' }
Opts[3].SetOption('log',   Required_Argument, nil, 'l');  { was 'stderr-log'/'e' }
{ ShortOpts: ':hl:' }
'n': { --level handler, unchanged }
'l': LogFile := OptArg;
```

### Log entries written from `UGLI_2.pp`

| Where | Entry |
|---|---|
| After `OpenLog` | `started UGLI 2 v<Version>/<Release>` |
| After `OpenLog` | `flags: skip-intro=<bool> start-level=<N>` |
| After `Init` (before `NewGame:`) | `sound: <backend name from UOSSound>` |
| `NewGame:` | `new game: level=<N>` |
| item picked up | `item <N>: <name> at (<X>,<Y>) score=<Score>` |
| level complete | `level <N> complete` |
| player caught | `caught at (<EX>,<EY>) lives=<Lives>` |
| `OnGameOver:` | `game over: score=<Score>` |
| win screen | `won: score=<Score>` |
| `CleanUp:` | `exit` |

### `UOSSound.pp`

`Init` writes a single diagnostic line to fd 2 (which is the log file when
`--log` is active):
- Success: `UOSSound: PortAudio ready (<lib>)`
- Player create failed: `UOSSound: uos_CreatePlayer failed`
- Library not found: `UOSSound: no PortAudio library found`

Add `function SoundBackendName: string` to the interface: returns
`'UOS+PortAudio'`, `'silent (init failed)'`, or `'silent (no library)'`.

### `UGLI_2_Test.pp`

`TStderrSinkTests` → `TLogTests`.  Rename all three existing tests.  Add:

| Test | Assertion |
|---|---|
| `TestLog_Writes` | After `OpenLog(tmpfile)` + `Log('hello')`: file contains a line ending in `'  hello'` |
| `TestLog_NoopWithoutFile` | After `OpenLog('')` + `Log('x')`: no crash; `LogFd = -1` |

TearDown must reset `LogFd := -1` (in addition to restoring fd 2).

### `UGLI_2.pp` — `CleanUp:`

Add before `fpClose(RawTTYFd)`:
```pascal
Log('exit');
if LogFd >= 0 then fpClose(LogFd);
```

---

## Done when

- [x] `poe build-original` exits 0
- [x] `poe test-original` exits 0, all tests pass
- [x] `poe run-original --log /tmp/ugli.log`, play briefly, quit — log contains
      started/flags/sound/new-game/item/exit entries — user confirmed 2026-06-17
