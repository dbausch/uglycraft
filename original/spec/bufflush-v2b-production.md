# BufFlush → V2b (single-write, consec-skip)

## Status

- [x] WBuf infrastructure moved from Variants.inc into Core.inc
- [x] `BufFlush` in Core.inc replaced with V2b algorithm
- [x] `UGLI_2.pp` opens `RawTTYFd` on startup, closes it at CleanUp
- [x] `TBufFlushOutputTests` updated to use `CaptureRawFlush(@BufFlush)`
- [x] `poe build-original` passes
- [x] `poe test-original` passes (119 tests)

---

## Motivation

Benchmark results across three dirty-cell scenarios (30 reps each):

| Scenario | V1 avg | V2b avg | Speedup |
|---|---|---|---|
| Full screen (2000 dirty) | 8 460 µs | 74 µs | ×114 |
| Border only (~197 dirty) | 862 µs | 19 µs | ×45 |
| Sparse (50 random) | 203 µs | 16 µs | ×13 |

V2b batches all terminal output into a single `fpWrite` syscall, eliminating
per-cell kernel round-trips. It also skips the `ESC[r;cH` cursor-position
sequence when the cursor is naturally already at the next cell (same row,
consecutive column).

V3b (row-span + single write) is faster only on full-screen flushes (46 µs)
but slower on every other access pattern. The game spends most time on partial
updates (HUD, single-character player/enemy moves), so V2b wins overall.

---

## What changes

### `original/UGLI_2_Core.inc`

Move the WBuf infrastructure here so it is available to production `BufFlush`
and (via `{$I}` ordering) to the variant procedures in Variants.inc:

```pascal
const MaxWBufSize = 65536;

var
  WBuf     : array[0..MaxWBufSize - 1] of Byte;
  WBufPos  : Integer = 0;
  RawTTYFd : cint    = -1;

procedure WB(const S: AnsiString);
procedure WBCh(const S: ShortString);
procedure WBInt(N: Integer);
procedure WBFlush;
```

Replace `BufFlush` body with the V2b algorithm (consec-skip + single fpWrite):

```pascal
procedure BufFlush;
const AnsiClr: array[0..7] of Byte = (0, 4, 2, 6, 1, 5, 3, 7);
var Col, Row, LastFg, LastBg, FgCode, BgCode, LastCol, LastRow: Integer;
begin
  if not BufFlushEnabled then ...exit...;
  WBufPos := 0;
  WB(#27'[?7l');
  LastFg := -1; LastBg := -1; LastCol := -1; LastRow := -1;
  for Row := 1 to ScreenH do
    for Col := 1 to ScreenW do
      if Dirty[Col, Row] then
        begin
          { colour change }
          { skip ESC[r;cH if already adjacent }
          WBCh(Screen[Col,Row].Ch);
          LastCol := Col; LastRow := Row;
          Dirty[Col, Row] := false;
        end;
  WB(#27'[?7h');
  WBFlush;
end;
```

### `original/UGLI_2_BufFlush_Variants.inc`

Remove the WBuf infrastructure block (now in Core.inc). Keep `TFlushProc`,
V2, V3, V2b, V3b unchanged — they can use `WBuf`/`RawTTYFd` from Core.inc.

### `original/UGLI_2.pp`

Open `RawTTYFd` at startup alongside `TTYFd`:

```pascal
RawTTYFd := fpOpen('/dev/tty', O_WRONLY);
```

Close it at CleanUp:

```pascal
fpClose(RawTTYFd);
```

### `original/UGLI_2_Test.pp` — `TBufFlushOutputTests`

All three tests that called `CaptureTextFlush(@BufFlush)` must switch to
`CaptureRawFlush(@BufFlush)` because the new `BufFlush` writes via `fpWrite`
to `RawTTYFd`, not via Pascal `Write` to `TTY`.

Rename / update:

| Old name | New name | Change |
|---|---|---|
| `TestV1_HasLineWrapBrackets` | `TestBufFlush_HasLineWrapBrackets` | `CaptureRawFlush` |
| `TestV1_ContainsCellChar` | `TestBufFlush_ContainsCellChar` | `CaptureRawFlush` |
| `TestV1_ClearsDirty` | `TestBufFlush_ClearsDirty` | `CaptureRawFlush` |
| `TestV2_SingleCell_SameBytesAsV1` | `TestBufFlush_SameBytesAsV2b` | both sides `CaptureRawFlush`; compare BufFlush to V2b |
| `TestV2_TwoAdjacentCells_SkipsSecondCursorPos` | (unchanged name) | BufFlush side → `CaptureRawFlush`; assert BufFlush also omits `ESC[3;6H]` |

---

## Done when

- [x] `poe build-original` succeeds with zero errors (commit: 82b563d)
- [x] `poe test-original` exits 0, all 119 tests pass (commit: 82b563d)
- [ ] `poe run-original` plays normally at the new flush speed (manual check — must be confirmed explicitly by the user, not inferred from exit code)
