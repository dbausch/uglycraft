# WBFlush dump and replay for rendering-artefact bisection

## Status

- [ ] `DumpFd` + modified `WBFlush` in `UGLI_2_Core.inc`
- [ ] `ToggleDump` procedure + F6 keybinding (`GetKey`, `HandleInput`, CleanUp)
- [ ] `UGLI_2_Replay.pp` built with `poe build-replay`
- [ ] `poe build-original` passes
- [ ] `poe build-replay` passes
- [ ] Dump file is unbounded — no size cap applied
- [ ] `BufFlushForce` procedure emits every cell regardless of dirty bits
- [ ] `ToggleDump` calls `BufFlushForce` on start so dump begins with a complete frame
- [ ] Red `●` drawn at (80, 25) inside `BufFlush` whenever `DumpFd ≥ 0`
- [ ] `--dump <file>` / `-d <file>` CLI option: sets dump path and starts recording immediately
- [ ] Manual bisection workflow confirmed (user must confirm)

---

## Purpose

When a rendering glitch occurs (HUD corruption, blanked cells) it is hard to
tell whether:

1. **Short write** — `fpWrite` on a pty fd can legally return fewer bytes than
   requested when the pty write-buffer is near-full.  `WBFlush` currently
   ignores the return value; any un-written bytes are silently dropped, leaving
   the terminal mid-sequence.
2. **Split escape sequence** — if two writes arrive at the terminal in rapid
   succession, a multi-byte escape or UTF-8 character could be split across
   kernel tty-buffer chunks, confusing the terminal parser.
3. **Cursor-position drift** — the consec-skip optimisation in `BufFlush`
   assumes each character is exactly one column wide.  Characters with East
   Asian Width = "Ambiguous" (e.g. `☼` U+263C, `≡` U+2261, `♦` U+2666, `⌂`
   U+2302) may be rendered as two columns wide by some terminals, causing
   subsequent dirty cells on the same row to land one column to the right.
   (See `bufflush-no-consec-skip.md`.)

The dump records every `WBFlush` call verbatim.  The replay utility re-sends
the first N writes to stdout, enabling bisection: find the write N where the
artefact first appears, then inspect the raw bytes to determine whether data is
missing (hypothesis 1/2) or logically wrong (hypothesis 3).

---

## What changes

### `UGLI_2_Core.inc`

Add `DumpFd : cint = -1` to the second `var` block (alongside `WBuf`, `WBufPos`).

Modify `WBFlush` to mirror each write to `DumpFd` when open, terminated by a
`0x00` sentinel byte:

```pascal
{ OLD }
procedure WBFlush;
begin fpWrite(RawTTYFd, WBuf[0], WBufPos); WBufPos := 0; end;

{ NEW }
procedure WBFlush;
var NullByte: Byte;
begin
  fpWrite(RawTTYFd, WBuf[0], WBufPos);
  if DumpFd >= 0 then
    begin
      fpWrite(DumpFd, WBuf[0], WBufPos);
      NullByte := 0;
      fpWrite(DumpFd, NullByte, 1);
    end;
  WBufPos := 0;
end;
```

Add `ToggleDump` (opens or closes `/tmp/ugli_dump.bin`):

```pascal
procedure ToggleDump;
const DumpFileName = '/tmp/ugli_dump.bin';
begin
  if DumpFd >= 0 then
    begin fpClose(DumpFd); DumpFd := -1; end
  else
    DumpFd := fpOpen(DumpFileName, O_WRONLY or O_CREAT or O_TRUNC, $1A4);
end;
```

Add `KeyF6: ToggleDump` to the `HandleInput` case.

Add `17: GetKey := Chr(KeyF6)` to the `ESC [ N ~` numeric case in `GetKey`.

#### No size cap

The dump file is opened and written without any artificial size limit.
No rotation, no early close, no byte counter.  The file grows as long
as recording is active.  (The OS imposes the only practical ceiling.)

#### `BufFlushForce` (new procedure)

Marks every cell in `Dirty` as `true`, then calls `BufFlush`.  The
result is a complete frame emitted as a single `WBFlush` write.

```pascal
procedure BufFlushForce;
var X, Y: Integer;
begin
  for Y := 1 to ScreenH do
    for X := 1 to ScreenW do
      Dirty[X, Y] := true;
  BufFlush;
end;
```

#### `ToggleDump` — full-frame emit on start

When transitioning from closed → open, call `BufFlushForce` after
opening `DumpFd`.  This ensures the recorded stream begins with a
self-contained snapshot of the current screen; replaying from write 0
always shows a coherent frame regardless of prior game state.

```pascal
procedure ToggleDump;
const DumpFileName = '/tmp/ugli_dump.bin';
begin
  if DumpFd >= 0 then
    begin fpClose(DumpFd); DumpFd := -1; end
  else
    begin
      DumpFd := fpOpen(DumpFileName, O_WRONLY or O_CREAT or O_TRUNC, $1A4);
      BufFlushForce;   { emit complete current frame as first dump write }
    end;
end;
```

#### Recording indicator in `BufFlush`

At the start of `BufFlush`, when `DumpFd ≥ 0`, force cell (80, 25) to
a red filled circle:

```pascal
if DumpFd >= 0 then
  BufPutCell(ScreenW, ScreenH, Red, Black, '●');
```

This happens before the dirty-cell emit loop, so the indicator is
always included in the frame whenever recording is active.  When
recording stops, the next `BufFlush` no longer sets the cell; whatever
the game last wrote to (80, 25) is emitted instead.

`●` (U+25CF BLACK CIRCLE) is encoded as three UTF-8 bytes and occupies
one terminal column.

### `UGLI_2.pp`

Add `KeyF6 = 64` to the const block.

Add `DumpFile: string = ''` to the `var` block.

Add `'d'` short option and `'dump'` long option to `ParseCLI`:

```pascal
Opts[5].SetOption('dump', Required_Argument, nil, 'd');
{ ShortOpts: ':hl:d:' }
'd': DumpFile := OptArg;
```

After `Init` (and after `OpenLog` / terminal setup), if `DumpFile ≠ ''`,
open it immediately and emit a full frame:

```pascal
if DumpFile <> '' then
  begin
    DumpFd := fpOpen(DumpFile, O_WRONLY or O_CREAT or O_TRUNC, $1A4);
    BufFlushForce;
  end;
```

`--dump` opens fresh (`O_TRUNC`) on each launch.  The file is
unbounded; append across sessions is not supported.

Add to `CleanUp` (before `fpClose(RawTTYFd)`):
```pascal
if DumpFd >= 0 then fpClose(DumpFd);
```

### `original/UGLI_2_Replay.pp` (new)

Standalone program: reads a zero-byte-delimited dump file and writes the first
N chunks to stdout.

Usage: `./UGLI_2_Replay <dump_file> [n_writes]`

If `n_writes` is omitted, all writes are replayed.

### `pyproject.toml`

```toml
[tool.poe.tasks.build-replay]
help  = "Build the WBFlush replay debugging utility"
shell = "cd original && fpc -Fuuos -oUGLI_2_Replay UGLI_2_Replay.pp"
```

---

## Bisection workflow

```
poe build-original && poe build-replay
```

1. Press **F6** at the start of a game session — recording begins
   (`/tmp/ugli_dump.bin` is created and truncated).
2. Play until the artefact appears; press F6 again (or quit) to stop.
3. In a fresh terminal window:
   ```
   ./original/UGLI_2_Replay /tmp/ugli_dump.bin 50
   ```
   Adjust the write count up/down until the first write that shows corruption
   is isolated.
4. Inspect raw bytes of that write:
   ```
   python3 -c "
   import sys
   data = open('/tmp/ugli_dump.bin','rb').read()
   chunks = data.split(b'\x00')
   n = int(sys.argv[1])
   print(repr(chunks[n]))
   " 42
   ```
   Look for truncated escape sequences (ends mid-`ESC[`) or missing data
   (sudden jump in row/col position).

---

## Done when

- [ ] `poe build-original` exits 0
- [ ] `poe build-replay` exits 0
- [ ] F6 during gameplay: red `●` appears at bottom-right; `/tmp/ugli_dump.bin`
      is created; first write in the file is a complete frame; F6 again removes
      indicator and stops recording (confirmed by user)
- [ ] `./UGLI_2_Replay /tmp/ugli_dump.bin 10` replays first 10 writes to
      stdout correctly; write 0 shows a full screen (confirmed by user)
- [ ] `poe run-original --dump /tmp/ugli_dump.bin` starts recording immediately
      on launch; red `●` visible from the first frame (confirmed by user)
