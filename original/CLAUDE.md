# UGLI 2 — Original DOS Game (1996)

Reference documentation for the original Turbo Pascal 7 source files kept in this repo. These files are released under the **GNU General Public License version 3**, the same licence as UGLYCRAFT. They can be built and run with Free Pascal (see `poe build-original`), and serve as design reference for the mechanics and level layouts that inspired UGLYCRAFT.

## Overview

UGLI (version 2, 1996) is a DOS text-mode game written in Turbo Pascal 7 by Daniel Bausch. The player navigates an 80×20 character field collecting 10 types of treasures across 9 levels while being chased by an AI enemy. High scores are saved to `UGLI.HSC`.

## Building (if you ever want to)

- **Turbo Pascal 7** (original): Open `UGLI_2.pp` in the TP7 IDE or run `tpc UGLI_2.pp`
- **Free Pascal / Linux** (recommended): `poe build-original` from the repo root. Fetches the three required UOS source files and `ANSI-87.conf` from GitHub on first run, then compiles with `fpc -Fuuos UGLI_2.pp`. Requires `fpc` and `curl` on PATH, and `libportaudio` at runtime for sound.
- **DOSBox + TP7**: Mount the directory and compile from within DOSBox for authentic behaviour.

Run `poe test-original` to build and execute the fpcunit test suite (159 tests, exits 0 on all-pass).

## File structure

### `UOSSound.pp` (unit `UOSSound`) — FPC/Linux sound

- Wraps UOS + PortAudio to provide `Sound(Hz)`, `NoSound`, `Beep(Hz, Ms)`, `BeepAsync(Hz, Ms)`
- `Beep` is synchronous (blocks caller); `BeepAsync` returns immediately, a background timer thread silences after the given duration
- Named effects: `SoundBump`, `SoundPickup`, `SoundCaught` (async); `SoundGameOver`, `SoundWon` (sync)
- UOS source fetched from GitHub at build time; requires `libportaudio.so.2` at runtime

### `UGLI_2_Core.inc` — shared include file

All type/const/var/resourcestring declarations and all procedures. Included by both the game program and the test program via `{$I UGLI_2_Core.inc}`.

### `UGLI_2.pp` (program `UGLI_2`) — the game itself

Uses `CThreads`, `DOS`, `BaseUnix`, `SysUtils`, `termio`, `gettext`, `getopts`, `UOSSound`.

### `UGLI_2_Test.pp` (program `UGLI_2_Test`) — fpcunit test suite

159 unit tests across sixteen classes (string utilities, screen buffer, level init, drawing, game logic, enemy AI, player movement, block placement, player-caught state, dialog rendering, screen overlays, game-flow transitions, CLI help text, structured logging, dump/recording, dump file binary inspection, character constants and drawing helpers, utility functions). Build and run with `poe test-original`.

### `translations/` — runtime locale files

- `UGLI_2.pot` — PO template; regenerate with `poe make-pot` after rebuilding
- `de.po` / `de.mo` — German translation (source + compiled binary)
- Place `<lang>.mo` next to the binary (in a `translations/` subdirectory) to
  add a new language; `Init` detects the system locale via `GetLanguageIDs` and
  loads the matching `.mo` with `TranslateResourceStrings`

## Knowledge base

`original/kb/` contains reference files loaded on demand.

| File | Contents |
|---|---|
| `original/kb/level-layouts.md` | Wall coordinates and start positions for all 9 levels |
| `original/kb/game-mechanics.md` | Scoring, lives, speed/timing, item sequence, block/pause systems |
| `original/kb/display-system.md` | Screen buffer, ANSI colour encoding, SGR sequences, GetKey VT100 parser |
| `original/kb/crt-removal.md` | Why CRT was removed, what replaced each CRT call, colour mapping |
| `original/kb/i18n.md` | Translated strings, YesKey/NoKey system, adding a language |
| `original/kb/sound-system.md` | UOS+PortAudio architecture, history of stderr suppression, committed vs. fetched UOS sources, `--log` behaviour |

## Code style

All Pascal source follows `STYLE.md`. Key rules:

- **Keywords** lowercase: `begin`, `end`, `if`, `then`, `else`, `for`, `do`, `while`, …
- **Types** PascalCase: `String`, `Integer`, `Boolean`, `LongInt`, …
- **User identifiers** English, PascalCase: `DrawBorder`, `BlocksRemaining`, `EnemyMove`
- **Two-letter abbreviations** ALL CAPS: `DX`, `DY`, `EX`, `EY`, `TTY`
- **2-space indentation**; `begin`/`end` always on their own lines
- **No space before `:`**; one space after: `X: Integer`, `1: begin`
- **Binary operators** always surrounded by one space: `X := Y + 1`, `if A = B then`
- **No alignment**: never add extra spaces to align `:`, `=`, `:=`, or other operators across lines
- No blank line immediately after `begin` or before `end`/`until`

**Never add `CRT` to `uses`.** CRT emits SGR 1 (bold) for bright foreground colours instead of the correct 90–97 high-intensity codes, which renders incorrectly on modern terminals. All colour constants (0–15 + `Blink=$80`) are defined locally; terminal output goes through the off-screen buffer (`BufPutCell` / `BufFlush`) and direct ANSI escape sequences.

## Key data structures (`UGLI_2.pp`)

| Identifier | Type | Meaning |
|---|---|---|
| `Blocked[1..80, 1..20]` | `Boolean` array | Collision map; border, level walls, and player-placed blocks set cells to `true` |
| `BlocksRemaining` | Integer | Block-placement budget (starts 2000, decremented on place, costs 20 pts each) |
| `ItemNo` | Integer | Current treasure index (1–9, wraps per level) |
| `Score` | LongInt | Score |
| `Lives` | Integer | Lives remaining (starts 10) |
| `PausesRemaining` | Integer | Pause tokens remaining (starts 20) |
| `MoveDelay` | Integer | Movement delay in ms (lower = faster; Home/End adjusts) |
| `X`, `Y` | Integer | Player position (1-indexed, column × row) |
| `BlockX`, `BlockY` | Integer | Position of the last player-placed block; redrawn by movement functions |
| `EX`, `EY` | Integer | Enemy position |
| `Direction` | TDirection | Current movement direction; updated by `DirDequeue` or directly |
| `DirQueue[0..7]` | `TDirection` ring buffer | Queued direction changes from input drain; `DirHead`/`DirTail` index into it |
| `StartX`, `StartY` | Integer | Player start position for the current level (set by `InitLevelN`, applied by `PrepareLevel`) |
| `StartEX`, `StartEY` | Integer | Enemy start position for the current level |
| `StartDir` | TDirection | Starting direction for the current level |
| `Laying` | Boolean | When `true`, a block is placed at the player's position every tick (Space toggles) |
| `Screen[1..80, 1..25]` | `TScreenBuffer` | Off-screen cell buffer; each `TScreenCell` holds `Ch: String[4]`, `Fg: Byte`, `Bg: Byte` |
| `Dirty[1..80, 1..25]` | `Boolean` array | Marks cells changed since the last `BufFlush` |
| `BufFlushEnabled` | Boolean | When `false`, `BufFlush` clears dirty flags without writing to TTY (used by test suite) |
| `TTYFd` | cint | Read-only `/dev/tty` file descriptor (raw key input via `fpRead`) |
| `RawTTYFd` | cint | Write-only `/dev/tty` file descriptor (single-write terminal output via `fpWrite` in `BufFlush`) |
| `WBuf[0..65535]` | `array of Byte` | Output byte buffer for `BufFlush`; filled by `WB`/`WBCh`/`WBInt`, flushed by `WBFlush` |
| `WBufPos` | Integer | Current write position in `WBuf` |
| `DumpFd` | cint | When ≥ 0, `WBFlush` mirrors each write to this fd with a `0x00` sentinel; toggled by F6 via `ToggleDump` or set by `--dump`; closed at CleanUp |
| `DumpFile` | string | Set by `--dump <file>`; when non-empty, `DumpFd` is opened after `Init` and `BufFlushForce` emits the initial frame |
| `SkipIntro` | Boolean | Set by `--skip-intro` or `--level`; when `true`, `Init` skips the animated logo sequence |
| `StartAtLevel` | Integer | Set by `--level N` (1–9); 0 means not set. When > 0, `Init` skips `ShowItemDescriptions`; `NewGame:` uses it as the initial level; F4 restarts at this level |
| `LogFile` | string | Set by `--log <file>`; passed to `OpenLog` which routes fd 2 to the file (empty → `/dev/null`) and keeps `LogFd` open for structured `Log()` entries |
| `LogFd` | cint | When ≥ 0, `Log()` writes timestamped entries here; closed at CleanUp |

## Key constants (`UGLI_2.pp`)

| Constant | Value | Meaning |
|---|---|---|
| `FieldW` / `FieldH` | 80 / 20 | Play field dimensions |
| `KeyRight/Left/Down/Up` | 77/75/80/72 | Scan codes for arrow keys |
| `KeyPause` / `KeySlower` / `KeyFaster` | 112 / 79 / 71 | P / End / Home |
| `KeyEscape` / `KeySpace` | 27 / 32 | Escape / Space |
| `KeyF1`–`KeyF5` | 59–63 | Function keys F1–F5 |
| `KeyF6` | 64 | F6 — toggle WBFlush dump recording (`ESC[17~` in xterm/kitty) |
| `PlayerCh` / `EnemyCh` | `'☺'` / `'☻'` | Player and enemy display characters |
| `WallCh` / `HLineCh` | `'█'` / `'─'` | Wall block and horizontal line characters |
| `GitVersion` | (injected) | Short git SHA or version, generated into `git_sha.inc` at build time |
| `BlocksRemaining` | init 2000 | Block-placement budget |
| `HighScoreFileName` | `'UGLI.HSC'` | High score file path |

## Key procedures

**`InitStderrSink(LogFile: string)`**: Routes fd 2 (stderr) permanently to `/dev/null` (when `LogFile = ''`) or to the named file (truncated). Called once at startup before TTY or sound initialisation. Prevents ALSA/PortAudio diagnostic output from corrupting terminal rendering.

**`ParseCLI`**: Parses command-line arguments using FPC's `getopts` unit (`GetLongOpts`). Handles `--help`/`-h` (calls `ShowCLIHelp`), `--skip-intro`, `--level N`, and `--stderr-log <file>`; sets the corresponding globals (`SkipIntro`, `StartAtLevel`, `StderrLog`). Unknown options and `--level` without an argument also call `ShowCLIHelp`. Called at the start of the main block, before `InitStderrSink`.

**`ShowCLIHelp`**: Prints translated usage text to stdout and exits with code 0. Called by `ParseCLI` on `--help`/`-h` or on any parse error.

**`InitLevel1`–`InitLevel9`**: Set player start position/direction and populate `Blocked` for level walls. Called via the `InitLevel(N)` dispatcher.

**`DrawBorder`**: Draws the `█` border, marks border cells in `Blocked`, then calls `DrawLevel`, `DrawScore`, `DrawLives`, `DrawPauses`, `DrawBlocks`, and `DrawItemName`.

**`DrawItemName`**: Draws the current item's name centred in the safe zone of the bottom border row (cols 12–66, ZoneW=55), padding with spaces to erase any previously longer name. Called from `DrawBorder` and from the main-loop pickup handler.

**`GetItemName(I)`**: Returns the `resourcestring` name for item index `I` (1–10) via a `case` statement.

**`PrepareLevel`**: Full level reset — clears interior `Blocked` cells, calls `InitLevel(Level)` (sets walls and `Start*` defaults), copies `Start*` to live `X/Y/EX/EY/Direction`, then calls `Redraw`. Called at genuine level-start time and when the player is caught.

**`BufFlush`**: Emits all dirty cells to the terminal via a single `fpWrite` syscall (V2b algorithm). Before the `BufFlushEnabled` guard, if `DumpFd ≥ 0`, forces cell (80, 25) to a red `●` recording indicator. Batches `ESC[?7l`, per-cell SGR and content, and `ESC[?7h` into `WBuf`, then calls `WBFlush`. Skips `ESC[r;cH` cursor-position when the cursor is already at the next adjacent cell (same row, next column). If `BufFlushEnabled = false`, clears dirty flags and returns immediately without writing to the terminal (used by the test suite).

**`BufFlushForce`**: Marks every cell in `Dirty` as `true`, then calls `BufFlush`. Used by `ToggleDump` (on start) and the `--dump` startup path to ensure the dump begins with a self-contained snapshot of the current screen.

**`Redraw`**: Lightweight screen repaint — `BufFill` (clear buffer), `DrawBorder`, `DrawKeys`, `DrawInner`, `BufFlush`. Does not touch `Blocked` or call `InitLevel`. Use after overlay screens (help, story).

**`DrawScore` / `DrawLives` / `DrawPauses` / `DrawBlocks`**: Draw individual HUD counters; all called from `DrawBorder` (via `Redraw`) and also called individually when only one counter changes.

**`EnemyMove`** (enemy AI): Greedy chase. Each `EnemyTick`, computes `DX = EX - X`, `DY = EY - Y`. If `|DX| ≥ |DY|`, tries to move horizontally toward player first; falls back to vertical if blocked. Vice versa otherwise. No pathfinding — can get stuck behind walls.

**`HandleInput`**: Main input handler. Drains all pending keys from the TTY buffer (`while KeyPressed do`) and dispatches each one:
- Arrow keys → enqueue into `DirQueue` (deduplicated against tail)
- Home/End → adjust `MoveDelay` (fires immediately, multiple events stack)
- Space → toggle `Laying` (continuous block-placement mode)
- F1 → flush direction queue, show help screen, break
- F2 → flush direction queue, show history screen, break
- F3 → buy a life (5000 pts)
- P → pause (5 s, decrements `PausesRemaining`)
- Escape → flush direction queue, break (checked in main loop)
- F4 → flush direction queue, break (checked in main loop)
- F5 → flush direction queue, break (checked in main loop)

After draining, calls `MovePlayer` (pops one direction from `DirQueue`, or continues in current `Direction` if empty), `PlaceBlock` if laying, and draws player.

**`PlaceBlock`**: Places a `█` at the player's current position if not already blocked; costs 20 pts. Auto-disables `Laying` if points or block budget run out.

**`RemoveBlocks`**: Modal dialog (Y/N in English; J/N in German). On yes: clears interior `Blocked`, calls `InitLevel` (rebuilds level walls only — live position, direction, and enemy are untouched), redraws border, resets `BlockX`/`BlockY`. No point cost.

**`DrawBlank(Col, Row)`**: Clears a single cell to `FieldBg` background.

**`DrawPlayer`** / **`DrawEnemy`**: Draw the player or enemy at their current position with standard colours and character constants (`PlayerCh`, `EnemyCh`).

**`DrawItem`** / **`RandomPos`**: Draw the current treasure; place it at a random non-blocked position.

**`GracePeriod`**: 1-second pause with item, player, and enemy visible. Drains any arrow keys pressed during the sleep to set the initial direction. Called at level start (from `LevelTransition`) and after being caught (from the main loop).

**`HighScoreEntry`**: End-of-game high score entry. Shows "Wall of Fame" headline with congratulations and score, reads a single name via `ReadLn`, appends `name<TAB>score` to `UGLI.HSC`, then calls `ShowHighScores`.

**`ShowHighScores`**: Reads all entries from `UGLI.HSC`, sorts descending by score, displays the top 10 with rank numbers, aligned name and right-aligned score (4-column margins). Parses both TAB-separated and old space-separated formats.

## Main loop structure

Uses named `goto` labels:

```
label NewGame, StartLevel, PlayAgain, OnGameOver, CleanUp;
...
NewGame:    { Level := 1; Score := 0; Lives := 10; ItemNo := 1; PrepareLevel; LevelTransition }
StartLevel: { EnemyTick := 0; RandomPos if ItemX = 0 }
            { repeat: Sleep(MoveDelay), DrawItem, HandleInput, EnemyMove, collision checks }
            {   caught → PlayerCaught; GracePeriod (if lives > 0) }
            {   treasure collected → ItemX := 0; goto StartLevel }
            {   lives = 0 → goto OnGameOver }
            { until Escape }
OnGameOver: { calls GameOver }
PlayAgain:  { AskPlayAgain dialog }
            {   Y → goto NewGame;  N → goto CleanUp  (J/N in German) }
CleanUp:  { restore terminal, ANSI clear screen, exit }
```

## Sound

`UOSSound.pp` wraps UOS + PortAudio. Requires `libportaudio.so.2` at runtime; falls back to silence if unavailable. UOS source is fetched from GitHub at build time — not committed to the repo.

Gameplay sounds (`SoundBump`, `SoundPickup`, `SoundCaught`) use `BeepAsync` — the tone plays for a fixed duration via a background timer thread without blocking the main loop. Fanfares (`SoundGameOver`, `SoundWon`) and intro sounds use synchronous `Beep`.


## Internationalisation (i18n)

All user-visible strings are declared as `resourcestring` (English defaults). FPC extracts them to `UGLI_2.rsj` at compile time. At runtime, `Init` calls `GetLanguageIDs` to detect the two-letter locale code and loads `translations/<lang>.mo` with `TranslateResourceStrings` if the file exists. `YesKey` and `NoKey` (sets of byte) are built from `sYesChar`/`sNoChar` resourcestrings after translation so the yes/no key characters track the loaded language.

`GetItemName(I)` is the sole access point for translated item names — `TItemData` no longer has a `Name` field. `DrawItemName` centres the current item name in the bottom border safe zone (cols 12–66).

To add a language: compile the game (generates `UGLI_2.rsj`), run `poe make-pot` to refresh `translations/UGLI_2.pot`, copy it to `translations/<lang>.po`, fill in `msgstr` values, compile with `msgfmt translations/<lang>.po -o translations/<lang>.mo`, and copy the `.mo` alongside the binary.

