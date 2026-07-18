# Silence the three 5061 TTY-variable warnings in the test build (BL-76)

## Status

- [ ] Three assignment lines added at the top of `UGLI_2_Test.pp`'s main
  `begin` block (`TTYFd`, `SavedTio`, `RawTio`)
- [ ] `poe test-original` compiles with **zero** warnings (was 3) and the
  suite still passes (exit 0)
- [ ] `poe build-original` output unchanged (no new messages)

---

## Root cause

`poe test-original` emits three FPC warnings that `poe build-original` does
not:

```
UGLI_2_Core.inc(53,3) Warning: Variable "TTYFd" read but nowhere assigned
UGLI_2_Core.inc(54,3) Warning: Variable "SavedTio" read but nowhere assigned
UGLI_2_Core.inc(54,13) Warning: Variable "RawTio" read but nowhere assigned
```

`TTYFd`, `SavedTio`, and `RawTio` are globals declared in
`UGLI_2_Core.inc:53-54`. Their **only** assignments live in the main
program's body (`UGLI_2.pp:82-90`, the raw-terminal-mode init: `fpOpen`,
`tcgetattr` into `SavedTio`, `tcsetattr`, `RawTio := Tio`). The include file
itself only *reads* them — the key-input path (`UGLI_2_Core.inc:597,610`)
and the high-score name-entry routine (`:1903,1908`).

`UGLI_2_Test.pp` includes the same core (`{$I UGLI_2_Core.inc}`, line 64)
but its program body deliberately never runs the terminal init — the tests
are headless. So within the test compilation FPC's warning 5061 ("read but
nowhere assigned", anchored at the declaration site) is **literally true**:
the three globals are read somewhere and assigned nowhere. Not a false
positive.

The fourth TTY global, `RawTTYFd`, does not warn because it is declared
*with* an initializer (`cint = -1`, `UGLI_2_Core.inc:55`) and the test
assigns it in `CaptureRawFlush` (`UGLI_2_Test.pp:1490`). That is the
existing precedent this fix follows: give the variables an assignment in the
test binary.

## What changes

### `UGLI_2_Test.pp` — main `begin` block

Three lines at the top of the program body (next to the existing
`BufFlushEnabled := false;`), before any test registration:

```pascal
TTYFd := -1;
FillChar(SavedTio, SizeOf(SavedTio), 0);
FillChar(RawTio, SizeOf(RawTio), 0);
```

An assignment anywhere in the program silences 5061 (a `FillChar`
var-parameter counts as an assignment — verified empirically with a minimal
FPC 3.2.2 reproduction that went from 2 warnings to 0). Runtime behaviour is
unchanged: FPC zero-initializes globals anyway, so the `FillChar` calls are
deterministic no-ops, and `TTYFd := -1` is a small robustness bonus — if a
future test ever reached the key-input or name-entry paths by accident, the
syscalls would fail fast on fd −1 instead of operating on fd 0 (stdin).

No change to `UGLI_2.pp` or `UGLI_2_Core.inc`.

## Rejected alternatives (tested)

- **Empty record initializers** at the declarations
  (`SavedTio: Termios = ();`): compiles, but merely trades warning 5061 for
  warning 3177 ("Some fields coming after "" were not initialized").
- **`{$WARN 5061 OFF}`** around the declarations in `UGLI_2_Core.inc`: works
  (the warning anchors to the declaration line), but suppresses diagnostics
  for project-own code — against the scoping discipline established for the
  third-party UOS suppression (→ see `spec/0091-silence-uos-thirdparty-warnings.md`):
  suppression is for code we do not own; our own code gets real fixes.

## Verification

No new test case applies — the deliverable is a compile-log property:

- `poe test-original`: build log contains **zero** warning lines (down
  from the 3 quoted above) and the suite still passes (all tests, exit 0).
- `poe build-original`: output byte-identical in message content to before
  (the single out-of-scope `UOSSound.pp(57)` 6058 note remains; nothing
  new appears) — this spec touches only the test program.

→ Backlog: BL-76 (`kb/backlog.md`) — carries the full investigation record.

## Done when

- [ ] The three assignments are present at the top of `UGLI_2_Test.pp`'s
  main `begin` block.
- [ ] `poe test-original` compiles warning-free and passes (exit 0).
- [ ] `poe build-original` output shows no new messages.
