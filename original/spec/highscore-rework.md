# High score entry/screen rework

## Status

- [x] Single name field (no first/last split)
- [x] TAB-separated storage format (name + score)
- [x] Sorted and ranked display (highest score first)
- [x] Entry screen with congratulations headline and instructions
- [x] Proper alignment with 4-column margins, name truncation
- [x] Game compiles (`poe build-original` exits 0)
- [x] All tests pass (`poe test-original` exits 0)
- [x] Manual check: entry screen shows congratulations and instructions
- [x] Manual check: high score list is sorted, ranked, and aligned

## Current behaviour

- `HighScoreEntry` asks for first name and last name separately
- Appends `"FirstName LastName    Score"` to `UGLI.HSC`
- Displays the raw file contents with no sorting or formatting
- Only called from `WinScreen` (after winning the game)

## Design

### Storage format

Each line in `UGLI.HSC`:

```
Name<TAB>Score
```

- Name: free-form string, whatever the player types
- Score: integer (`Score * Lives`), no leading spaces
- TAB (`#9`) separates name from score — unambiguous since TAB
  cannot appear in terminal input

### Entry screen

Clear screen, then display:

```
(row 2)   W A L L   O F   F A M E
(row 4)   Congratulations!  You scored 12345 points.
(row 5)   Please enter your name:
(row 7)   > _                          (cursor here, cooked mode)
```

- Headline: `sHSTitle` resourcestring, centred
- Congratulations line: `sHSCongrats` resourcestring with score
  interpolated (e.g. `'Congratulations!  You scored %d points.'`,
  formatted at runtime with the actual score)
- Prompt: `sHSPrompt` resourcestring
- Single `ReadLn` for the name
- Colour: same as current (LightBlue on Black)

### Display screen

After entry (or when showing existing scores), clear screen and
render the top-10 sorted list:

```
(row 2)   W A L L   O F   F A M E

(row 4)    1.  PlayerName           12345
(row 5)    2.  AnotherPlayer         9870
           ...
(row 13)  10.  OldPlayer              500

(row 25)  P R E S S   A N Y   K E Y
```

- Layout: 4-column left margin, 4-column right margin → 72 usable
  columns (cols 5–76)
- Rank: right-aligned in 3 columns + `.` + 2 spaces
- Name: left-aligned, truncated if needed to fit
- Score: right-aligned at column 76
- Read all entries from file, sort descending by score, display top 10
- Headline: same `sHSTitle`, centred on full 80 columns

### Resourcestrings

```pascal
sHSTitle   = 'W A L L   O F   F A M E';
sHSPrompt  = 'Please enter your name:';
sHSCongrats = 'Congratulations!  You scored ';
sHSPoints   = ' points.';
```

Remove: `sFirstName`, `sLastName`, `sScoreEntry`.

### Variables

Remove: `FirstName`, `LastName`.  Replace with a single local or
reuse `S` for the name input.

### Rendering

All output uses `Draw` / `BufPutCell` / `BufFlush` — never raw
`WriteLn` to the terminal.  This ensures correct column alignment
with UTF-8 names (multi-byte characters counted by `UTF8Cols`, not
`Length`).

The only exception is the name input itself: `ReadLn` requires cooked
mode and writes directly to the terminal.  After `ReadLn` returns,
switch back to raw mode and use `Draw` for everything else.

Name truncation for display uses `UTF8Cols` to measure visible width
and truncates at a character boundary so multi-byte sequences are
never split.

### Procedure changes

`HighScoreEntry`:
1. Clear screen via `BufFill` + `BufFlush`
2. Draw headline, congratulations, prompt via `Draw`
3. `BufFlush`, then switch to cooked mode, cursor on
4. Single `ReadLn` for name
5. Cursor off, switch back to raw mode
6. Compute final score (`Score * Lives`)
7. Append `Name + #9 + IntToStr(FinalScore)` to file
8. Call `ShowHighScores` to display

`ShowHighScores` (new):
1. Read all lines from `UGLI.HSC`, parse `Name<TAB>Score`
2. Sort descending by score
3. `BufFill`, draw headline via `Draw`
4. Render top 10 with rank, name (truncated via `UTF8Cols`), score
   (right-aligned) — all via `Draw`
5. `BufFlush`, show `sPressKey` via `Draw`, `BufFlush`, wait for key

### Backwards compatibility

Old `.HSC` files use `"FirstName LastName    Score"` format (spaces,
no TAB).  On read, if a line has no TAB, treat everything before the
last whitespace-delimited token as the name and the last token as the
score.  This handles old entries gracefully.

## Done when

- [x] Single name field replaces first/last name — `430afeb`
- [x] File format uses TAB separator — `430afeb`
- [x] Old space-separated entries are parsed correctly — `430afeb`, confirmed by user
- [x] Entry screen shows congratulations with score and prompt — `430afeb`, `650e4bb`
- [x] Display shows sorted top-10 with rank, aligned in 72-col layout — `430afeb`, `650e4bb`
- [x] Game compiles (`poe build-original` exits 0) — `430afeb`
- [x] All tests pass (`poe test-original` exits 0) — `430afeb`
- [x] Manual check: entry and display screens look correct — confirmed by user
