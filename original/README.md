# UGLI 2 — Running the Original 1996 Source on Modern Linux

This directory contains the original Pascal source of UGLI 2 (1996), a DOS
text-mode game written in Turbo Pascal 7 by Daniel Bausch.  Starting from the
raw CP437 files as they came off the original floppy, a series of changes were
made so the game compiles and runs cleanly under Free Pascal (FPC) on a modern
Linux terminal.  The initial port (version 2.0) kept gameplay identical to the
DOS original; later versions (2.1–2.3) added gameplay improvements and
significant code quality work.  See `CHANGELOG.md` for the full record.

## Building

```bash
# from the repo root
poe build-original   # fetches UOS audio sources, then: cd original && fpc -Fuuos UGLI_2.pp
./original/UGLI_2
```

Or simply `poe run-original` to build and launch in a terminal window.

FPC 3.2.2 (current Arch Linux package) is what this was developed against.

## What was changed, and why

### 1. Source encoding and cleanup

The original files were saved in **CP437** (DOS code page) with **CRLF** line
endings.  Modern FPC on Linux chokes on both.

- Converted source files from CP437 to **UTF-8** and stripped CRLF line
  endings.
- Replaced every `chr(N)` call and `#N` character literal that referred to a
  CP437 box-drawing or graphic character with the equivalent **Unicode
  literal** (e.g. `'█'`, `'☺'`).  This makes the source readable and
  means FPC can emit the right UTF-8 bytes directly.
- All identifiers renamed from original German shorthand to English PascalCase
  (see `CHANGELOG.md` § 2.1 for the full list).

### 2. Dependency reduction

The original program depended on three units: `EXTRA1.PAS` (a TUI library),
`DANISOFT.PAS` (an animated splash screen), and the game itself.  `EXTRA1`
pulled in Turbo Pascal BGI graphics units that do not exist under FPC.

- Stripped `EXTRA1.PAS` to only the single helper function actually used
  (`Zentriert`, a string-centring utility), then inlined it into `DANISOFT.PAS`
  and **deleted `EXTRA1.PAS`** entirely.
- All content from `DANISOFT.PAS` (`UTF8Cols`, `Center`, `Intro`) was later
  merged directly into `UGLI_2.pp` and **`DANISOFT.pp` deleted**, eliminating
  the unit boundary and allowing all procedures to be ordered by dependency
  with no forward declarations.

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
  separate `TTY : Text` file variable is opened to `/dev/tty` and all cursor
  and scroll-region escapes are sent through it.  Two small helpers
  `MyCursorOff` and `MyCursorOn` wrap this.

### 5. Splash screen (`Intro`)

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

### 6. The `Draw` procedure and FPC's cursor tracker bug

The game positions every character with `GotoXY` before writing it.  FPC CRT
maintains an internal cursor position tracker and **skips emitting the
`ESC[y;xH` sequence when the target matches the tracked position**.  The
tracker is advanced by the **byte count** of what is written, not the
display-cell count.  UTF-8 characters that are one cell wide but three bytes
long therefore advance the tracker by 2 more than the real cursor moves,
causing subsequent `GotoXY` calls to be silently dropped — writing characters
at the wrong column or losing them entirely.

The fix is a `Draw(Col, Row, Fg, Bg: Integer; S: String)` procedure that:

1. Splits the string into individual characters (handling 1-, 2-, and 3-byte
   UTF-8 sequences).
2. Before every real `GotoXY(C, Row)`, first calls `GotoXY(1, 1)` to force
   the tracker to a known-wrong value, guaranteeing that the subsequent real
   `GotoXY` always emits its escape sequence.
3. Writes each character individually so the tracker drift per character is
   bounded to one character width.
4. Takes explicit `Fg` and `Bg` color parameters so no call site can
   accidentally inherit stale colors from a prior draw.

All `GotoXY` + `Write` call sites were replaced with `Draw` or `DrawHLine`.

### 7. Sprite rendering fixes

Three visual artefacts were fixed after the `Draw` work:

- **Enemy ghost**: the enemy position was erased every tick even when the
  enemy had not moved, leaving a blank cell at the old position when the enemy
  was stationary.  Fixed by only erasing the old position when the enemy
  actually changed position.
- **Player face flicker when bumping walls**: the player sprite was redrawn
  unconditionally after every keypress, causing a flicker on wall bumps.
  Fixed by not re-drawing the player sprite when movement was blocked.
- **Leftover text attributes after `DoPause`**: the pause display set colours
  that were not reset afterwards, leaving subsequent screen writes in the
  wrong colour.  Fixed by resetting attributes on exit from the procedure.

### 8. Level transition polish

- **Delay before redraw**: in `LevelTransition`, the 1-second delay that shows
  the new level number ran before the level walls were drawn.  Moved the delay
  to after the `InitLevelN` call so the level is visible before the game
  pauses.
- **Wall flicker**: a redundant full redraw call immediately after
  `LevelTransition` cleared all non-wall cells and rewrote them from scratch,
  causing a visible flash.  Removed.

### 9. End / Home key (`GetKey` wrapper)

On a Linux terminal, **Home** sends `ESC[H` and **End** sends `ESC[F`.  FPC
CRT 3.2.2 handles `ESC[H` correctly but does **not** handle `ESC[F`: instead
it pushes the three bytes back onto its internal LIFO buffer in **reversed
order**, so they emerge across three consecutive `ReadKey` calls: `'F'` (70),
then `'['` (91), then `ESC` (27).  The trailing ESC was reaching the main-loop
quit check and terminating the game.

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
| 2 (saw F+[) | `ESC` | End sequence complete → state 0, return `chr(KeySlower)` |
| 2 (saw F+[) | anything else | Reset to state 0, re-evaluate the byte |

The state persists between calls so the three bytes can be spread across
different procedures.  **Every `ReadKey` call in the entire program was
replaced with `GetKey`** — if any procedure consumed a byte via raw `ReadKey`,
the state machine would desynchronise and the trailing ESC would leak to the
quit check anyway.

### 10. UTF-8 column count (`UTF8Cols` / `Center`)

The original `Zentriert` centred a string within the 80-column display by
computing `39 - (Length(s) DIV 2)` leading spaces.  `Length` counts
**bytes**, so multi-byte UTF-8 characters — German umlauts — inflate the byte
count and shift the output too far left.

Fixed by introducing a `UTF8Cols` helper that counts **display columns**
instead of bytes: it increments the counter only for bytes that are not UTF-8
continuation bytes (i.e. outside `$80`–`$BF`).  `Center` now calls `UTF8Cols`
in place of `Length`.

### 11. Centring of level banner and status bar label

Two visual centring issues were corrected at version 2.0:

- **Level banner (`LevelTransition`)**: the banner box was positioned starting
  at column 30, making it off-centre.  Shifted to properly centre the
  26-column-wide box on the 80-column field.
- **LEVEL display in status bar**: the `LEVEL N` label was placed at column 35
  via three separate duplicated code blocks.  Corrected to column 36 and
  consolidated into a `DrawLevel` procedure.

### 12. Sound backend (`UOSSound`)

The original game used the PC speaker directly via port I/O — not available
on Linux.  A `UOSSound.pp` unit wraps the
[UOS](https://github.com/fredvs/uos) + PortAudio stack to provide the same
`Sound(Hz)` / `NoSound` / `Ton(Hz, Ms)` interface as Turbo Pascal's CRT, plus
named effect procedures (`SoundBump`, `SoundPickup`, `SoundCaught`,
`SoundGameOver`, `SoundWon`).  Listed last in `uses` so it shadows the empty
CRT sound stubs on Linux.  UOS source is fetched from GitHub at build time;
`libportaudio.so.2` is required at runtime and falls back to silence if
unavailable.

### 13. Gameplay and code improvements (2.1–2.3)

After the initial port reached version 2.0, several rounds of gameplay and
code quality work followed:

- **Gameplay (2.1)**: removed the shield/shop feature; bound life-buying to
  F3; made pause time-based; switched block placement to Space and block
  removal to F5; continuous movement in the last pressed direction.
- **Dialog system (2.3)**: unified all message boxes behind `WaitKey` (drains
  key queue) and `Dialog(Title, Prompt)` (draws a centered `█`-bordered box,
  waits, restores the interior via `DrawInner`).  `DrawInner` now redraws the
  player, enemy, and current item, so any overlay can restore the full game
  field with a single call.
- **`TDirection` enum (2.3)**: replaced `Direction: Char` (which stored
  raw keyboard scan codes) with a `TDirection = (DirRight, DirLeft, DirDown,
  DirUp)` enum.  `KeyToDir` converts scan codes to the enum; `MovePlayer`
  dispatches on it.
- **`TItemData` record (2.3)**: treasure character, name, and gameplay color
  are defined once in an `Items[1..10]` typed constant array.  `DrawItem` and
  `ShowItemDescriptions` both derive from it, eliminating duplicated data.
- **Level initialisation (2.3)**: `InitLevel1`–`InitLevel9` write to
  `StartX/StartY/StartEX/StartEY/StartDir`; `PrepareLevel` copies these to
  live variables.  This means `RemoveBlocks` can call `InitLevel` to rebuild
  walls without disturbing any live game state.

See `CHANGELOG.md` for the complete list of fixes and changes per version.

### 14. Internationalisation (i18n) — FPC `resourcestring` + `gettext`

All user-visible text was hard-coded German.  To make the game playable by
non-German speakers, string extraction and runtime translation support were
added using FPC's built-in mechanism.

**Source language change to English.** Every German string literal in the
source was replaced with a `resourcestring` constant whose default value is
English.  German is now the first `.mo` translation rather than the hard-coded
default.  Users whose system locale is unrecognised see English.

**Drop `-Mtp`.** The code had been compiled with `-Mtp` (Turbo Pascal
compatibility mode) since the initial port.  An audit found no TP-specific
dependencies: no typed constants are reassigned at runtime, no TP-only syntax
is used.  The flag was removed; `{$H+}` was added at the top of the file to
make `String = AnsiString` explicit instead of relying on the active mode.

**`TItemData.Name` removed.** FPC `resourcestring` values cannot appear in
typed constant initialisers, so the `Name: String[40]` field was removed from
`TItemData`.  A `GetItemName(I: Integer): String` function returns the
appropriate resourcestring via a `case` statement.

**`DrawItemName` procedure.** Draws the current item's name centred in the
safe zone of the bottom border row (cols 12–66, between the LIVES counter on
the left and BLOCKS counter on the right), padding with spaces to erase any
previously longer name.  Called from `DrawBorder` and from the main-loop
pickup handler.

**Runtime locale detection.** At startup, `Init` calls `GetLanguageIDs` (from
the FPC `gettext` unit) to detect the system locale, then looks for
`translations/<lang>.mo` next to the binary.  If found, it calls
`TranslateResourceStrings` to patch all resourcestring values with the
translated text.  `YesKey` and `NoKey` are then built from the `sYesChar` and
`sNoChar` resourcestrings so the yes/no key characters track the translation.

**Translation files.** `original/translations/` contains:

- `UGLI_2.pot` — PO template generated with `rstconv -i UGLI_2.rsj`
  (regenerate with `poe make-pot` after rebuilding)
- `de.po` — German translation (fill `msgstr` values, then `msgfmt` to compile)
- `de.mo` — compiled German translation; shipped alongside the binary by
  `poe deploy-original-linux`

To add a new language: copy `UGLI_2.pot` to `<lang>.po`, fill in the
`msgstr` values, compile with `msgfmt <lang>.po -o <lang>.mo`, copy the `.mo`
file to the `translations/` directory next to the binary.
