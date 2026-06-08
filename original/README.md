# UGLI 2 — Running the Original 1996 Source on Modern Linux

This directory contains the original Pascal source of UGLI 2 (1996), a DOS
text-mode game written in Turbo Pascal 7 by Daniel Bausch.  Starting from the
raw CP437 files as they came off the original floppy, a series of changes were
made so the game compiles and runs cleanly under Free Pascal (FPC) on a modern
Linux terminal — with no functional changes to the gameplay itself.

## Building

```bash
# from the repo root
.venv/bin/poe build-original   # runs: cd original && fpc -Mtp UGLI_2.PAS
./original/UGLI_2
```

FPC 3.2.2 (the current Arch Linux package) is what this was developed against.

## What was changed, and why

### 1. Source encoding and cleanup

The original files were saved in **CP437** (DOS code page) with **CRLF** line
endings.  Modern FPC on Linux chokes on both.

- Converted `UGLI_2.PAS` and `DANISOFT.PAS` from CP437 to **UTF-8** and
  stripped CRLF line endings.  The conversion required two passes: a first
  attempt left some German umlauts corrupted and had to be redone.
- Replaced every `chr(N)` call and `#N` character literal that referred to a
  CP437 box-drawing or graphic character with the equivalent **Unicode
  literal** (e.g. `'█'`, `'☺'`, `'╔'`).  This makes the source readable and
  means FPC can emit the right UTF-8 bytes directly.

### 2. Dependency reduction

The original program depended on three units: `EXTRA1.PAS` (a TUI library),
`DANISOFT.PAS` (an animated splash screen), and the game itself.  `EXTRA1`
pulled in Turbo Pascal BGI graphics units (`graph`, `Drivers`, `Boosters`)
that do not exist under FPC.

- Stripped `EXTRA1.PAS` to only the single helper function actually used
  (`Zentriert`, a string-centring utility), then inlined that function into
  `DANISOFT.PAS` and **deleted EXTRA1.PAS** entirely.
- Stripped `DANISOFT.PAS` to the single procedure used by the game
  (`Erkennung`, the splash screen), removing everything else.

### 3. Licensing

The original source contained a specific licensee name in a constant.  That
was replaced with a placeholder string so the source can be shared publicly.

### 4. Terminal cursor handling

FPC on Linux does not have the DOS `CursorOff` / `CursorOn` API.  The game
needs to hide the cursor during play and restore it on exit.

- Replaced `CursorOff` / `CursorOn` calls with direct **ANSI escape
  sequences** (`ESC[?25l` / `ESC[?25h`).
- Cursor control sequences must be written to `/dev/tty`, not to stdout.
  FPC's CRT unit writes to stdout which may be redirected or buffered, so a
  separate `tty : Text` file variable is opened to `/dev/tty` and all cursor
  and scroll-region escapes are sent through it.  Two small helpers
  `MyCursorOff` and `MyCursorOn` wrap this.
- On exit the cursor is always restored even if the game crashes, because the
  write goes to the raw tty rather than through CRT's buffering.

### 5. Splash screen (`DANISOFT.PAS` / `Erkennung`)

The animated colour intro screen had two rendering bugs under FPC:

- **Scroll region not confined**: the intro called `ClrScr` in a loop to cycle
  background colours, which on a modern terminal scrolls the entire screen
  instead of just rows 1–25.  Fixed by emitting `ESC[1;25r` before the intro
  and `ESC[r]` after to confine the scroll region to rows 1–25.
- **Blank lines lost their background colour**: FPC's `Write` of an empty
  string does not emit the SGR (colour) attribute, so blank lines showed the
  terminal's default background instead of the chosen colour.  Fixed by always
  writing at least one space on blank lines and flushing the ANSI erase-to-EOL
  sequence (`ESC[K`) explicitly.

### 6. The `writexy` procedure and FPC's cursor tracker bug

The game positions every character with `GotoXY` before writing it.  FPC CRT
maintains an internal cursor position tracker and **skips emitting the `ESC[y;xH`
sequence when the target matches the tracked position**.  The tracker is
advanced by the **byte count** of what is written, not the display-cell count.
UTF-8 characters that are one cell wide but three bytes long therefore advance
the tracker by 2 more than the real cursor moves, causing subsequent `GotoXY`
calls to be silently dropped — writing characters at the wrong column or
losing them entirely.

The fix is a `writexy(col, row, s)` procedure that:

1. Splits the string into individual characters (handling 1-, 2-, and 3-byte
   UTF-8 sequences).
2. Before every `GotoXY(c, row)`, first calls `GotoXY(1, 1)` to force the
   tracker to a known-wrong value, guaranteeing that the subsequent real
   `GotoXY` always emits its escape sequence.
3. Writes each character individually so the tracker drift per character is
   bounded to one character width.

All `GotoXY` + `Write` call sites were replaced with `writexy`.

### 7. Sprite rendering fixes

Three visual artefacts were fixed after the `writexy` work:

- **Enemy ghost**: the enemy position was erased every tick even when the
  enemy had not moved, leaving a blank cell at the old position when the enemy
  was stationary.  Fixed by only erasing the old position when `ugli2`
  actually changed `(xx, yy)`.
- **Player face flicker when bumping walls**: the player sprite was redrawn
  unconditionally after every keypress, causing a flicker on wall bumps.
  Fixed by not re-drawing the player sprite when movement was blocked.
- **Leftover text attributes after PausenZeigen**: the pause display set
  colours that were not reset afterwards, leaving subsequent screen writes in
  the wrong colour.  Fixed by resetting attributes on exit from the procedure.

### 8. Level transition polish

- **Delay before redraw**: in `levelneu`, the 1-second delay that shows the
  new level number ran before the level walls were drawn.  Moved the delay to
  after the `initlN` call so the level is visible before the game pauses.
- **Wall flicker**: a `ReStone` call immediately after `levelneu` cleared all
  non-wall cells and rewrote the walls from scratch, causing a visible
  flash.  This call was redundant (the level was already drawn) and was
  removed.

### 9. End / Home key (`GetKey` wrapper)

On a Linux terminal, **Home** sends `ESC[H` and **End** sends `ESC[F`.  FPC
CRT 3.2.2 (the current stable, Arch build date 2024-05-01) handles `ESC[H`
correctly — it recognises the sequence and returns `#0` + `chr(71)` (the DOS
scan code for Home).  It does **not** handle `ESC[F`: instead it pushes the
three bytes back onto its internal LIFO buffer, so they emerge in **reversed
order** across three consecutive `ReadKey` calls: `'F'` (70), then `'['`
(91), then `ESC` (27).  The trailing ESC was reaching the main-loop quit
check (`if ti = 27 then goto 999`) and terminating the game.

(FPC issue #36328, fixed in FPC trunk commit `1d9aadd717` on 2026-04-10, is
not yet in any released FPC version.)

The fix is a `GetKey` wrapper around `ReadKey` that implements a three-state
machine:

| State | Sees | Action |
|---|---|---|
| 0 (idle) | `#0` | Extended-key prefix: read next byte and return it as the key code |
| 0 (idle) | `'F'` | Start of reversed End sequence → state 1, return `#0` (suppress) |
| 0 (idle) | anything else | Return as-is |
| 1 (saw F) | `'['` | Second byte of End sequence → state 2, return `#0` (suppress) |
| 1 (saw F) | anything else | Reset to state 0, re-evaluate the byte |
| 2 (saw F+[) | `ESC` | End sequence complete → state 0, return `chr(lans)` (slow-down key) |
| 2 (saw F+[) | anything else | Reset to state 0, re-evaluate the byte |

The state persists between calls so the three bytes can be spread across
different procedures.  Crucially, **every `ReadKey` call in the entire program
was replaced with `GetKey`**, including calls inside `langsam`, `schnell`,
`Hilfe`, `levelneu`, and everywhere else.  This is essential: if any procedure
consumes a byte via the raw `ReadKey`, the state machine desynchronises and
the trailing ESC leaks to the quit check anyway.

The wrapper also handles the forward-sequence case (`#0` prefix) correctly, so
Home continues to work, and it is forward-compatible with future FPC versions
that do handle `ESC[F` — those will return `#0` + `chr(79)` which maps to the
same `chr(lans)` result via the `#0`-prefix branch.

### 10. UTF-8 column count in `Zentriert`

`Zentriert` centres a string within the 80-column display by computing
`39 - (Length(s) DIV 2)` leading spaces.  `Length` counts **bytes**, so
multi-byte UTF-8 characters — German umlauts such as `Ä`, `Ö`, `Ü`, `ß` used
in `'PRÄSENTIERT'` and `'Drücken'` — inflate the byte count and shift the
output too far left.

Fixed by introducing a `UTF8Cols` helper that counts **display columns** instead
of bytes.  It iterates over the string and increments the counter only for bytes
that are not UTF-8 continuation bytes (i.e. bytes outside the range `$80`–`$BF`).
Each such byte starts a new character, so the result equals the number of
terminal columns the string occupies regardless of how many bytes each character
uses.  `Zentriert` now calls `UTF8Cols(s)` in place of `Length(s)`.
