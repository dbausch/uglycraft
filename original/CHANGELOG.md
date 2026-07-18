# CHANGELOG — UGLI 2 (Linux/FPC port)

All versions listed here refer to the FPC/Linux port of the original 1996 DOS
game. The DOS executable (UGLI_2.EXE) remains unchanged at version 2.0.

---

## [Unreleased]

### Changed

- Silenced the 5 warnings + 18 notes FPC emitted against the fetched
  third-party UOS units (`uos.pas` etc.) on every build: a sentinel-guarded,
  idempotent `{$WARN <n> OFF}` directive block is prepended to the three
  fetched files after download, in `poe build-original` and all three
  PKGBUILDs' `prepare()`. Suppression is scoped strictly to the third-party
  units — diagnostics for the project's own Pascal code are untouched
  (spec 0091, BL-75).
- Hardened the linked binary to FULL RELRO: `-k-z -krelro -k-z -know` added
  after `-Fuuos` on all seven `fpc` invocations (three PKGBUILDs' `build()`
  plus the four `pyproject.toml` original-build tasks), so dev, test, and
  packaged builds link identically. Eagerly binds and then seals the GOT at
  startup (`GNU_RELRO` segment + `BIND_NOW`/`FLAGS_1: NOW`), closing the
  namcap "lacks FULL RELRO" warning. PIE remains out of reach — Arch's FPC
  3.2.2 RTL startup object is not PIC-compiled — and is documented as
  accepted in spec 0095 (BL-74).

### Fixed

- Silenced the three FPC 5061 "read but nowhere assigned" warnings that
  `poe test-original` emitted for `TTYFd`, `SavedTio`, and `RawTio` (globals
  only assigned by the terminal-init code the headless test binary never
  runs). Assigned at the top of `UGLI_2_Test.pp`'s main block, following the
  existing `RawTTYFd` precedent. No behaviour change; `poe build-original`
  output is unaffected.

---

## 2.6

### Changed

- Replaced `Release` constant with `GitVersion`, injected at compile
  time from `git rev-parse --short HEAD` via a generated `git_sha.inc`
  include file.  The intro and log now show the git commit hash instead
  of a manually maintained release number.
- Replaced fictional in-game story (F2) with the real history of UGLI.
  Story body text now loaded from external `translations/history_<lang>.txt`
  files; labels remain as resourcestrings.  Falls back to a translated
  placeholder if the file is not found.
- Renamed "Story of UGLI" to "History of UGLI" in key help bar and help screen.
- Reordered and replaced collectible items: Lamp, Swords, Ruby, Gems,
  Diamond, Silver Bar, Gold Bar, Necklace, Flag, Crown.
- Replaced gems (⛬→⁂), diamond (◆→♦), and crown (🜲→♛) symbols with
  characters that render at single-cell width in monospace fonts.
- Changed ruby color from LightRed to Red.
- Reworked all 9 level layouts: thicker walls (2–3 cells), inner border
  walls on cols 2 and 79, repositioned player and enemy starts.  Level 9
  now features a string-art "UGLI" pattern.
- Reworked high score screen: single name field, "Wall of Fame" headline
  with congratulations message, sorted and ranked top-10 display with
  proper column alignment (4-cell margins).  File format now uses TAB
  separator; old space-separated entries are parsed correctly.
- Added 1-second grace period after being caught, matching the existing
  level-start grace time.  Item, player, and enemy are all visible
  during both grace periods; arrow keys set the initial direction.

### Fixed

- `Draw` now handles 4-byte UTF-8 sequences (U+10000+).  Previously only
  1–3 byte sequences were recognized; 4-byte characters (necklace, crown)
  were split into garbage.

---

## 2.5

### Changed

- Renamed `Ton(Hz, Ms)` to `Beep(Hz, Ms)` in `UOSSound.pp` and all call sites.
- `SoundBump`, `SoundPickup`, and `SoundCaught` now use non-blocking
  `BeepAsync` — the tone plays for a fixed duration via a background timer
  thread without blocking the main loop.
- When the player is caught, the entire playing field (including border)
  flashes red for 200 ms while the caught sound plays.
- `HandleInput` now drains all pending keys per tick instead of reading one.
  Direction keys are queued in a ring buffer (deduplicated); one direction
  is consumed per tick.  Holding non-direction keys (e.g. End) no longer
  blocks movement for multiple ticks.
- Renamed `HasTTYByte` to `KeyPressed` (standard Turbo Pascal name).

### Fixed

- Item pickup frame is now flushed to the terminal before the level restarts,
  so the player is visibly shown on the item cell at the moment of collection.
- Item is no longer erased for one frame when the enemy walks over it and
  leaves the cell.
- Game no longer hangs on quit when the async sound timer thread is active.
- Red flash on caught now fills the field with solid red instead of preserving
  characters (enemy was previously visible through the flash).
- High score file operations no longer crash on first run when `UGLI.HSC`
  does not exist yet (`{$I-}` was missing, so `Append` raised a runtime error
  instead of letting `IOResult` handle it).

---

## 2.4

### Internationalisation

- All user-visible strings declared as `resourcestring` constants with English
  defaults. Source language changed from German to English; German is now the
  first translation rather than the hard-coded default.
- Runtime locale detection via `GetLanguageIDs` (FPC `gettext` unit).
  `LoadTranslation` probes three locations in priority order: `translations/`
  next to the binary (bundled standalone install), system directories from
  `$XDG_DATA_DIRS` (default `/usr/local/share:/usr/share`) using the FHS path
  `locale/<lang>/LC_MESSAGES/UGLI_2.mo`, and the user directory from
  `$XDG_DATA_HOME` (default `~/.local/share`) using the same FHS path. Falls
  back to English if no matching `.mo` is found.
- German translation provided as `translations/de.po` (source) and `de.mo`
  (compiled binary). The compiled `.mo` ships alongside the game binary.
- `poe make-pot` task regenerates `translations/UGLI_2.pot` from the compiled
  resource string table (`rstconv -i UGLI_2.rsj`).
- Deploy task updated to include `translations/*.mo` in the Linux distribution.
- `TItemData.Name` field removed — FPC `resourcestring` values cannot
  initialise typed constant fields. `GetItemName(I: Integer): String` returns
  the translated item name via a `case` statement. `DrawItemName` procedure
  draws the current item's name centered in the bottom border safe zone (cols
  12–66); called after each pickup and after `Redraw`.
- `YesKey` / `NoKey` moved from typed constants to `var` declarations and built
  from `sYesChar` / `sNoChar` resourcestrings after the translation is loaded,
  so the accepted yes/no key characters track the active language.

### Display

- `ShowHelp`: key entries reformatted as `[Key]   Description` (aligned
  columns, no `=` separator) and reordered logically: movement, block, pause,
  quit, F1–F5, then speed keys. Key-binding lines indented to column 5 for a
  left margin (was column 2, flush with the border).
- `ShowStory` and the instructions section of `ShowItemDescriptions`: long
  hard-coded multi-line text replaced with single `resourcestring` values
  rendered by `DrawParagraph`, which word-wraps and fully justifies the text
  at 72 display columns. The last line of each paragraph is left-aligned, not
  justified.
- "PRESS A KEY" prompt renamed to "PRESS ANY KEY".
- Off-screen screen buffer (`TScreenBuffer`, `TScreenCell`, dirty-cell array):
  all drawing procedures write through `BufPutCell` / `BufFill` into an
  in-memory buffer; `BufFlush` emits only changed cells to TTY via direct SGR
  sequences using the correct CRT→ANSI index mapping (`'04261537'`). A single
  `BufFlush` fires at the end of each game tick; overlay screens (`ShowHelp`,
  `ShowStory`, `Dialog`, …) flush when they have finished composing.
- `BufDesaturate` dims the screen behind dialog boxes: non-white foregrounds
  become `LightGray`; non-black backgrounds become `LightGray`, leaving
  `White`-on-`Black` HUD text fully readable through the overlay.
- `Dialog` calls `Redraw` on dismiss to restore the complete game screen;
  previously only `DrawInner` was redrawn, leaving the dimmed border visible.
- `FillScreen(Bg)` fills the whole terminal window (not just the 80×25 buffer)
  with a background color before switching to a full-screen view; fixes
  leftover content visible on terminals wider than 80 columns.
- Intro: line-drawing animation step uses `LightGray` (color 7) for the stripe
  characters; the previously used `White` (color 15) was visually too bright.
  Info-text background uses `LightGray` (SGR 47) rather than bright-white
  (SGR 107), keeping colors within the standard 8-color background range.
- `poe run-original` loads the ANSI-87 kitty theme (`-c original/ANSI-87.conf`)
  so the game window opens with the original VGA 16-color palette instead of
  any user theme.

### Code quality

- Drop `-Mtp` (Turbo Pascal compatibility mode). An audit found no TP-specific
  syntax in use. `{$H+}` added at the top of `UGLI_2.pp` to make
  `String = AnsiString` explicit without relying on the active mode.
  `Draw`'s local character variable corrected from `String` to `String[4]`
  (exposed by the mode change).
- `uses` clause extended with `BaseUnix` (for `fpgetenv` used by the XDG
  directory lookup) and `gettext`.
- `DrawParagraph(Text, Col, Row, Width, Fg, Bg): Integer` — wraps a string to
  `Width` display columns using `WordWrap`, fully justifies each line except
  the last using `Justify`, draws them with `Draw`, and returns the number of
  lines written.
- `WordWrap(S, Width, Lines, N)` — greedy UTF-8-aware word wrapper; uses
  `UTF8Cols` for display-width measurement so multi-byte characters are counted
  by display column, not byte length.
- `Justify(S, Width): String` — distributes extra spaces evenly across
  word gaps to produce a full-width line.
- `UGLI_2_Core.inc` extracted: all type, const, var, resourcestring
  declarations and procedures moved into a shared include file. `UGLI_2.pp`
  is reduced to header, uses, label, const, `{$I UGLI_2_Core.inc}`, and the
  main block.
- CRT unit removed; replaced throughout with direct `termio`/ANSI terminal
  control:
  - Color constants 0–15 and `Blink = $80` defined in the program's `const`
    block.
  - Terminal set to raw mode at startup via `tcgetattr`/`tcsetattr`; restored
    at exit. `HighScoreEntry` temporarily switches to cooked mode for `ReadLn`
    and restores raw mode before returning.
  - `GetKey` rewritten as a VT100 escape-sequence parser that reads directly
    from a `/dev/tty` file descriptor via `fpRead`; arrow keys, F1–F5, Home,
    and End are decoded from ESC sequences (CSI and SS3 forms, Linux console
    `ESC[[X`, and xterm `ESC[N~` variants).
  - `KeyPressed` replaced by `HasTTYByte`, which uses `fpIoctl(FIONREAD)` for
    a non-consuming availability check.
  - `Delay` replaced by `Sleep` (SysUtils).
  - `TextColor`, `TextBackground`, `GotoXY`, `ClrScr`, and `ClrEol` replaced
    by SGR, cursor-position, and erase ANSI sequences written directly to TTY
    or ITTY.

### Performance

- `BufFlush` rewritten as the V2b algorithm: all terminal output is batched
  into a single 64 KB byte buffer and emitted via one `fpWrite` syscall,
  eliminating per-cell kernel round-trips. The cursor-position sequence
  `ESC[r;cH` is also skipped when the cursor is already naturally adjacent
  (same row, next column). Benchmark results (30 reps, Liberation Mono 16pt,
  kitty): full screen 8 460 µs → 74 µs (×114); border update 862 µs → 19 µs
  (×45); 50 random cells 203 µs → 16 µs (×13). `RawTTYFd` (write-only fd for
  `fpWrite`) is now opened alongside `TTYFd` in the main block and closed at
  CleanUp. WBuf infrastructure (`WBuf`, `WBufPos`, `WB`, `WBCh`, `WBInt`,
  `WBFlush`) added to `UGLI_2_Core.inc`.
- `UGLI_2_BufFlush_Variants.inc` added: alternative flush implementations
  (V2 consec-skip, V3 row-span, V2b/V3b single-write variants) used by the
  performance benchmark and correctness tests.

### Sound

- Fix sound distortion (chopping artefacts and frequency sweep): the UOS synth
  input defaulted to Float32 sample format while `AddIntoDevOut` defaulted to
  Int16. UOS's internal format conversion introduced the artefacts. Both the
  synth and the output device now explicitly use matching parameters: stereo,
  Float32, 44100 Hz, 1024 frames. Sound quality now matches the original DOS
  version.

### Bug fixes

- `HighScoreEntry`: removed a spurious `WaitKey` that appeared after writing
  the player's score to `UGLI.HSC` and before clearing the screen to show the
  high-score table.  The extra key press occurred while the screen still showed
  only the name-entry prompt, giving no feedback to the player.  The procedure
  already waits for a key at the end, after displaying the full score table.
- Stderr (fd 2) is permanently routed to `/dev/null` at startup via
  `InitStderrSink` (in `UGLI_2_Core.inc`).  ALSA buffer-underrun warnings
  and other library diagnostic output previously landed as raw text at the
  terminal cursor position, corrupting the display.  Pass
  `--stderr-log <file>` on the command line to route those messages to a file
  instead (useful when diagnosing sound hardware issues).
- `UOSSound.Init` previously used a local `SuppressStderr`/`RestoreStderr`
  pair to silence PortAudio's init-time ALSA probe.  Now that `InitStderrSink`
  handles fd 2 permanently before `Init` is ever called, the per-call
  suppression was redundant and has been removed.

### Command-line interface

- `--help` / `-h`: print usage and option descriptions, then exit.  Output
  is translated if a matching `.mo` file is found (German: `LC_ALL=de_DE.UTF-8
  ./UGLI_2 --help`).  When passed via `poe run-original`, kitty is not opened;
  help is printed directly to the calling terminal.  Unknown options and
  `--level` without an argument also trigger the help screen.
- `--skip-intro`: skip the animated intro (the logo animation); the
  item-descriptions screen is still shown and the game starts at level 1.
- `--level <N>`: start directly at level N (1–9), skipping both the animated
  intro and the item-descriptions screen.  F4 (restart) returns to level N,
  not level 1.  `--skip-intro --level N` behaves the same as `--level N`.
- `--stderr-log <file>`: route ALSA/PortAudio diagnostic messages to a file
  instead of silencing them (see Bug fixes below).
- CLI parsing refactored to `ParseCLI` using FPC's `getopts` unit
  (`GetLongOpts`); replaces the ad-hoc manual `ParamStr` loop.
- `poe run-original` forwards extra arguments directly: `poe run-original
  --level 5` (no `--` separator needed).  The `--` form also works.

### Debugging

- `WBFlush` now mirrors each write to a dump file when `DumpFd ≥ 0`, appending
  a `0x00` sentinel byte after each chunk.  Press **F6** in-game to toggle
  recording on/off; dump is written to `/tmp/ugli_dump.bin` (truncated at start
  of each recording).  The dump file enables offline bisection of rendering
  artefacts independently of the game session.
- `BufFlushForce` — marks every cell in `Dirty` as `true`, then calls `BufFlush`,
  producing a complete self-contained frame in a single WBFlush write.
- `ToggleDump` calls `BufFlushForce` when opening the dump file so the dump
  always begins with a full-screen snapshot; replaying from write 0 shows a
  coherent frame regardless of prior game state.
- Red `●` (U+25CF) drawn at cell (80, 25) inside `BufFlush` whenever `DumpFd ≥ 0`,
  before the `BufFlushEnabled` guard.  Visible recording indicator; automatically
  captured in the dump stream.  Dump file is unbounded (no size cap).
- `--dump <file>` / `-d <file>` CLI option: opens the named file and calls
  `BufFlushForce` immediately after `Init`, so recording starts from the first
  frame without requiring an in-game F6 press.
- `ToggleDump` clears the red `●` indicator (writes a black space at (80, 25)
  and flushes) when dump recording is toggled off.
- `UGLI_2_Replay.pp` — standalone replay utility: reads a zero-byte-delimited
  dump file and writes the first N chunks to stdout. Clears the screen at
  start; resets attributes, re-enables auto-wrap, and positions the cursor at
  row 26 after playback so the shell prompt appears cleanly below the replay.
  Usage: `./UGLI_2_Replay <dump_file> [n_writes]`
- `GetKey` extended with `ESC[17~` → `KeyF6` (xterm/kitty F6 encoding in the
  numeric-sequence case).  `KeyF6 = 64` added to the const block.
- `poe build-replay` task: compiles `UGLI_2_Replay.pp`.

### Testing

- fpcunit test suite (`UGLI_2_Test.pp`): 139 unit tests across fourteen classes
  covering string utilities, screen buffer, level init, drawing, game logic,
  enemy AI, player movement, block placement, player-caught state, dialog
  rendering, screen overlays, game-flow transitions, BufFlush output
  correctness (`TBufFlushOutputTests`), CLI help text, structured logging
  (`TLogTests`), dump/recording features (`TDumpTests`), and dump file binary
  inspection (`TDumpFileTests`). `BufFlushEnabled := false` suppresses terminal
  output in all non-flush tests.
- `poe test-original` task: compiles `UGLI_2_Test.pp` and runs all tests;
  exits 0 on all-pass.
- `poe bench-original` task: compiles and runs `UGLI_2_BufFlush_Bench.pp` in
  a new 80-column kitty terminal for interactive visual correctness checks;
  timing results (3 scenarios × 5 variants) are written to a temp file and
  printed to the poe output stream after the window closes.
- `poe build-original` now also fetches `original/ANSI-87.conf` from the
  kovidgoyal/kitty-themes repository alongside the UOS audio sources (cached
  after first run; excluded from version control).

---

## 2.3

### Bug fixes
- Level 4: horizontal middle wall shortened by one block on each end (was
  columns 5–75); enemy start position (5, 10) was inside the wall.
- `RemoveBlocks`: direction and enemy position are now preserved across the
  `InitLevel` call. Previously only the player position was saved/restored,
  leaving direction reset to the level default and enemy teleported to its
  start position.
- `ShowHelp`: headline moved to row 2, centered, with a blank line before the
  key list. Previously it was at row 1 with no padding.
- `ShowHelp` / `ShowStory`: "T A S T E   D R Ü C K E N" prompt moved to row 24
  (was row 16 and row 9 respectively). `ShowStory` content shifted one row down
  so the headline sits on row 2 with a blank line above it.

### Code quality
- Dialog/message box refactor: unified all key-reading through `WaitKey`
  (drains the key queue, returns the last key code) and `Dialog(Title, Prompt)`
  (draws a centered `█`-bordered box, calls `WaitKey`, restores the interior
  via `DrawInner`).
- `DrawInner` extended to redraw the player (`☺`), enemy (`☻`), and current
  item after the wall/space pass. `ItemX := 0` is used as a sentinel ("no item
  on field") to prevent a ghost item appearing during `LevelTransition`.
- Add `YesKey` / `NoKey` typed set constants (`set of Byte`) for J/j and N/n.
- `LevelTransition` replaced six ad-hoc `Draw`/`DrawHLine` calls with a single
  `Dialog` call; box now correctly centered at rows 9–11 (was rows 8–10).
- `GameOver`, `WinScreen`, `AskPlayAgain`, `RemoveBlocks` all use `Dialog`;
  Y/N prompts loop the entire `Dialog` call so the box is redrawn on invalid
  input. Star animation removed from `WinScreen`.
- `RemoveBlocks`: 20-point deduction removed.
- `DrawBlocks` HUD label renamed from `STEINE` to `BLÖCKE`.
- `ShowHelp`, `ShowStory`, `ShowItemDescriptions`, `HighScoreEntry`: all
  wait-for-key prompts converted to `WaitKey`.
- `DANISOFT.pp` merged into `UGLI_2.pp` (`UTF8Cols`, `Center`, `Intro`);
  `DANISOFT.pp` deleted. `Intro` now uses `WaitKey` and says
  `T A S T E   D R Ü C K E N` instead of the old Enter/Return prompt.
- All procedures reordered in dependency order; no forward declarations remain.
- `TDirection = (DirRight, DirLeft, DirDown, DirUp)` enum replaces
  `Direction: Char`. `KeyToDir(Code)` converts arrow-key scan codes to
  `TDirection`; `MovePlayer` dispatches on `Direction` to the four move
  procedures. `case Ord(Direction) of KeyRight: …` removed from `HandleInput`.
- `InitLevel1`–`InitLevel9` now write player position, enemy position, and
  direction to `StartX`/`StartY`, `StartEX`/`StartEY`, `StartDir`. `PrepareLevel`
  copies these to the live variables after calling `InitLevel`. `RemoveBlocks`
  therefore calls `InitLevel` to rebuild walls without disturbing any live game
  state; no save/restore needed.
- Eliminate the `NewGame: Level := 0; ItemNo := 9;` bootstrap hack. `NewGame:`
  now directly sets `Level := 1; Score := 0; Lives := 10; ItemNo := 1` and calls
  `PrepareLevel` + `LevelTransition`. No fake level transition occurs.
- Rename label `NextItem:` to `StartLevel:` — it marks the start of playing an
  item, not a transition between items.
- `AwardPoints` is now called *before* `ItemNo := ItemNo + 1` at the pickup site,
  eliminating the off-by-one formula that compensated for the wrong call site.
- Extract `LevelComplete` procedure: increments `Lives` before `PrepareLevel` so
  `Redraw` displays the updated count in the next-level splash.
- Add `IsPlayerCaught` and `IsItemPickedUp` boolean helper functions, replacing
  raw coordinate comparisons in the main loop.
- Each `InitLevel1`–`InitLevel9` now sets `EX := 5; EY := 10` directly, so every
  level owns its enemy start position; the assignments are removed from the main
  block.
- Add `InitBorder` procedure: sets border `Blocked` cells to `true` once at
  program start (called from `Init`). Border cells are now permanent and never
  reset; `PrepareLevel` and `RemoveBlocks` clear interior cells only
  (`2..FieldW−1, 2..FieldH−1`).
- Remove `Blocked` assignments from `DrawBorder` (pure rendering procedure); move
  HUD counter calls (`DrawLevel`, `DrawScore`, `DrawLives`, `DrawPauses`,
  `DrawBlocks`) into `DrawBorder` so `Redraw` delegates to it.
- Remove `DrawInner` call from `InitLevel` (state procedure no longer triggers
  rendering); `Redraw` is the sole owner of `DrawInner`.
- Rename `DrawFrame` → `PrepareLevel` and fix call order: clear interior
  `Blocked`, call `InitLevel(Level)`, then `Redraw` (previously `Redraw` ran
  before `InitLevel`, drawing walls one tick stale).
- `LevelTransition` no longer calls `InitLevel` (state was already set by the
  preceding `PrepareLevel`); calls `DrawInner` after the splash is dismissed to
  restore the interior.
- `Redraw` simplified to `ClrScr + DrawBorder + DrawKeys + DrawInner`; redundant
  explicit `DrawInner` calls removed from F1/F2 handlers and `PlayerCaught`.
- Add named color role constants (`WallFg`, `PlayerFg`, `EnemyFg`, `CounterFg`,
  `CounterBg`, `FieldBg`, `KeyHelpFg`, `HelpFg`, `SplashFg`, `DialogFg`,
  `WinFg`) and local `const Fg/Bg` blocks inside drawing procedures.
- Rename `WriteXY` → `Draw`; add `Fg, Bg: Integer` parameters. Every write now
  declares its own colors; no write can inherit a stale color from a prior call.
  All floating `TextColor`/`TextBackground` calls removed.
- Fix `DrawLives` and `DrawBlocks` using `LightRed` background (bug); all HUD
  counters now use `CounterBg = Red`.
- Rename `WriteLevel` → `DrawLevel` (consistent with `DrawScore`, `DrawLives`, …).
- Add `TItemData` record (`Ch`, `Name`, `Fg`) and `Items[1..10]` typed constant
  array with all treasure data. `DrawItem` reduced from a 10-branch if-chain to
  a single array lookup; crown (index 10) is selected when `Level = 9` and
  `ItemNo = 9`. `ShowItemDescriptions` fully rewritten using `Draw`: headlines
  centered on rows 2 and 16, item list block-centered (longest line determines
  left margin), description text wrapped at 72 display columns with 4-space
  margins, key prompt on row 24. Items shown in `ItemDescFg`/`ItemDescBg`
  (black on gray) regardless of their gameplay color. Typo "Edelsteiene" fixed.

### Gameplay fixes
- Fix rope scoring: rope (item 1) now correctly awards 100 points. The old
  formula `(ItemNo − 1) × 100` made rope worth 0; the new formula `ItemNo × 100`
  gives rope=100, big gem=900, matching the intended value table.
- Fix lives display at Level 1: lives counter now correctly shows 10 from the
  start. Previously a fake level-0→1 transition awarded a bonus life immediately,
  requiring a `if Level > 1` guard to suppress it.

---

## 2.2

### Gameplay fixes
- Start with 10 lives instead of 9; the level-1 transition no longer awards a
  bonus life (it is the game start, not a level completion reward).
- Fix game reset after showing the help screen (F1) or the story screen (F2):
  the player position, direction, and placed blocks were incorrectly wiped
  because a full `DrawFrame` (which calls `InitLevel`) was used instead of a
  lightweight screen repaint.
- Fix the LevelTransition splash border colour: it was inheriting a stale text
  colour from the previous draw call instead of being explicitly white.
- Fix `RemoveBlocks`: after clearing all blocks, `BlockX`/`BlockY` were left
  pointing at the now-empty cell, causing movement functions to redraw a ghost
  block there. They are now reset to (1, 1) — a border cell that is always solid.

### Display fixes
- Score counter padded to 5 digits so shrinking scores do not leave stale
  digits on screen.
- Lives counter padded to 2 digits for the same reason.

### Code quality
- Replace numeric `goto` labels (100/300/997/998/999/1) with descriptive names:
  `NextItem`, `NewGame`, `PlayAgain`, `OnGameOver`, `CleanUp`, `GameLoop`.
- Define named constants for all remaining literal key codes:
  `KeyEscape`, `KeySpace`, `KeyF1`–`KeyF5`.
- `AwardPoints`: replace 9-line if-chain with formula `(ItemNo − 1) × 100`.
- Extract `DrawBorder` from `DrawFrame`; add a lightweight `Redraw` procedure
  (repaints visuals without touching game state) for use after overlay screens.
- `RemoveBlocks`: remove redundant first `DrawInner`, second key-wait prompt,
  duplicated border loop (now calls `DrawBorder`), wrong array bounds
  (`1..25` → `1..FieldH`), and a stray `LastName := ''`.
- Export `Center` and `UTF8Cols` from `DANISOFT`'s interface section; remove
  the duplicate local `Center` function that had been added to `UGLI_2`.
- `ShowStory`: use `DANISOFT.Center()` with column 1 so text is truly centred
  on the 80-column screen.
- `PlayAgain` prompt: draw the box once before the loop; loop only reads keys
  (was: `repeat … until I = 3000`, which also re-drew the box every iteration).
- `HandleInput`: set `KeyCode := 0` at the top so each keystroke is processed
  exactly once; main-loop checks (`Escape`, `F4`, `F5`) no longer fire stale.
- Space toggles continuous block-laying mode (`Laying`); `PlaceBlock` auto-
  disables `Laying` when points or blocks run out.
- `LevelTransition`: if a direction key is pressed while the splash is showing,
  that direction becomes the active direction after the transition.

---

## 2.1

### Gameplay changes
- Remove the shield feature and the shop menu entirely.
- Bind "buy a life (costs 5000 pts)" to F3; show the lives counter on screen at
  all times instead of requiring a key press.
- Pause is now purely time-based (5 s delay); the remaining-pauses count is
  shown permanently in the top-right corner of the frame.
- `SlowDown` (End) and `SpeedUp` (Home) now immediately adjust the delay
  without a blocking key wait.
- The player keeps moving in the last pressed direction; pressing any non-
  direction key no longer stops movement.
- Rebind block placement from S to Space; rebind "remove all placed blocks"
  from N to F5.
- The score counter, lives counter, pauses counter, and block counter are all
  drawn as named procedures (`DrawScore`, `DrawLives`, `DrawPauses`,
  `DrawBlocks`) called from `DrawFrame`, ensuring counters are always redrawn
  after overlays.
- The key-help bar is drawn by a `DrawKeys` procedure, eliminating duplicate
  definitions.
- Fix missing screen redraws after the help overlay and the story overlay.

### Source hygiene (FPC/Linux port)
- Rename all Pascal source files to the `.pp` extension (FPC convention).
- Rename `UOSSound` sound effects to English: `SoundBump`, `SoundWon`.
- Rename all identifiers in `UGLI_2.PAS` and `DANISOFT.PAS` to English
  PascalCase; two-letter position variables (`VX`, `VY`, `DX`, `DY`, …) to
  ALL_CAPS; apply consistent 2-space indentation and lowercase keywords
  throughout (see `STYLE.md` and `IDENTIFIERS.md`).

---

## 2.0 — first Linux/FPC release

Starting point: the original 1996 Turbo Pascal 7 / DOS source (`UGLI_2.PAS`,
`DANISOFT.PAS`) ported to compile and run under Free Pascal on Linux.

### Porting changes applied to reach 2.0
- Convert source files from CP437 to UTF-8; strip CRLF line endings.
- Replace `chr()`/`#N` graphic-character calls with Unicode literals
  (box-drawing characters, block elements, smiley face).
- Strip `DANISOFT.PAS` and `EXTRA1.PAS` down to the functions actually used;
  inline `Zentriert` from `EXTRA1` into `DANISOFT`; delete `EXTRA1.PAS`.
- Fix `Zentriert` to count UTF-8 display columns rather than bytes, so German
  umlauts do not shift centering left.
- Replace `CursorOff`/`CursorOn` with direct ANSI escape sequences via
  `/dev/tty`.
- Route all gameplay `Write()` calls through `WriteXY` to fix cursor
  positioning (CRT's cursor tracker diverged from the terminal's real cursor).
- Fix UTF-8 corruption at column 80 on narrow terminals (disable autowrap for
  the duration of each `WriteXY` call).
- Add UOS + PortAudio sound backend (`UOSSound.pp`) providing `Sound(Hz)`,
  `NoSound`, `Ton(Hz, Ms)`, and named effects; fetched at build time.
- Link `CThreads` to fix Runtime Error 232 on Linux.
- Fix UOS sound: stereo output, volume gating, endless-duration tones,
  suppress stderr noise from PortAudio.
- Reset terminal attributes on exit to prevent bold/colour leaking into shell.
- Adjust `DANISOFT` intro timing and layout for modern terminal emulators.
- Remove unused variables (`l`, `nehm`, `gx`, `gy`).
- Fix long-standing movement bugs: equal horizontal/vertical speed; enemy and
  player ghost artefacts; leftover text attributes after pause display.
- Refactor level initialisation into `InitLevel1`–`InitLevel9` procedures
  called via a dispatcher; centre the level-transition banner on the
  80-column field; extract `WriteLevel`.
- Replace licensee name with `Public Domain`; add GPLv3 licence notice.
