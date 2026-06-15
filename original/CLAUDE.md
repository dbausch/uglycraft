# UGLI 2 — Original DOS Game (1996)

Reference documentation for the original Turbo Pascal 7 source files kept in this repo. These files are released under the **GNU General Public License version 3**, the same licence as UGLYCRAFT. They can be built and run with Free Pascal (see `poe build-original`), and serve as design reference for the mechanics and level layouts that inspired UGLYCRAFT.

## Overview

UGLI (version 2, 1996) is a DOS text-mode game written in Turbo Pascal 7 by Daniel Bausch. The player navigates an 80×20 character field collecting 10 types of treasures across 9 levels while being chased by an AI enemy. High scores are saved to `UGLI.HSC`.

## Building (if you ever want to)

- **Turbo Pascal 7** (original): Open `UGLI_2.pp` in the TP7 IDE or run `tpc UGLI_2.pp`
- **Free Pascal / Linux** (recommended): `poe build-original` from the repo root. Fetches the three required UOS source files and `ANSI-87.conf` from GitHub on first run, then compiles with `fpc -Fuuos UGLI_2.pp`. Requires `fpc` and `curl` on PATH, and `libportaudio` at runtime for sound.
- **DOSBox + TP7**: Mount the directory and compile from within DOSBox for authentic behaviour.

Run `poe test-original` to build and execute the fpcunit test suite (111 tests, exits 0 on all-pass).

## File structure

### `UOSSound.pp` (unit `UOSSound`) — FPC/Linux sound

- Wraps UOS + PortAudio to provide `Sound(Hz)`, `NoSound`, `Ton(Hz, Ms)`
- Named effects: `SoundBump`, `SoundPickup`, `SoundCaught`, `SoundGameOver`, `SoundWon`
- UOS source fetched from GitHub at build time; requires `libportaudio.so.2` at runtime

### `UGLI_2_Core.inc` — shared include file

All type/const/var/resourcestring declarations and all procedures. Included by both the game program and the test program via `{$I UGLI_2_Core.inc}`.

### `UGLI_2.pp` (program `UGLI_2`) — the game itself

Uses `CThreads`, `DOS`, `BaseUnix`, `SysUtils`, `termio`, `gettext`, `UOSSound`.

### `UGLI_2_Test.pp` (program `UGLI_2_Test`) — fpcunit test suite

111 unit tests across twelve classes (string utilities, screen buffer, level init, drawing, game logic, enemy AI, player movement, block placement, player-caught state, dialog rendering, screen overlays, game-flow transitions). Build and run with `poe test-original`.

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

## Code style

All Pascal source follows `STYLE.md`. Key rules:

- **Keywords** lowercase: `begin`, `end`, `if`, `then`, `else`, `for`, `do`, `while`, …
- **Types** PascalCase: `String`, `Integer`, `Boolean`, `LongInt`, …
- **User identifiers** English, PascalCase: `DrawBorder`, `BlocksRemaining`, `EnemyMove`
- **Two-letter abbreviations** ALL CAPS: `DX`, `DY`, `EX`, `EY`, `TTY`
- **2-space indentation**; `begin`/`end` always on their own lines
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
| `Direction` | TDirection | Last direction key pressed; player keeps moving in this direction each tick |
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
| `DumpFd` | cint | When ≥ 0, `WBFlush` mirrors each write to this fd with a `0x00` sentinel; toggled by F6 via `ToggleDump`; closed at CleanUp |

## Key constants (`UGLI_2.pp`)

| Constant | Value | Meaning |
|---|---|---|
| `FieldW` / `FieldH` | 80 / 20 | Play field dimensions |
| `KeyRight/Left/Down/Up` | 77/75/80/72 | Scan codes for arrow keys |
| `KeyPause` / `KeySlower` / `KeyFaster` | 112 / 79 / 71 | P / End / Home |
| `KeyEscape` / `KeySpace` | 27 / 32 | Escape / Space |
| `KeyF1`–`KeyF5` | 59–63 | Function keys F1–F5 |
| `KeyF6` | 64 | F6 — toggle WBFlush dump recording (`ESC[17~` in xterm/kitty) |
| `BlocksRemaining` | init 2000 | Block-placement budget |
| `HighScoreFileName` | `'UGLI.HSC'` | High score file path |

## Key procedures

**`InitLevel1`–`InitLevel9`**: Set player start position/direction and populate `Blocked` for level walls. Called via the `InitLevel(N)` dispatcher.

**`DrawBorder`**: Draws the `█` border, marks border cells in `Blocked`, then calls `DrawLevel`, `DrawScore`, `DrawLives`, `DrawPauses`, `DrawBlocks`, and `DrawItemName`.

**`DrawItemName`**: Draws the current item's name centred in the safe zone of the bottom border row (cols 12–66, ZoneW=55), padding with spaces to erase any previously longer name. Called from `DrawBorder` and from the main-loop pickup handler.

**`GetItemName(I)`**: Returns the `resourcestring` name for item index `I` (1–10) via a `case` statement.

**`PrepareLevel`**: Full level reset — clears interior `Blocked` cells, calls `InitLevel(Level)` (sets walls and `Start*` defaults), copies `Start*` to live `X/Y/EX/EY/Direction`, then calls `Redraw`. Called at genuine level-start time and when the player is caught.

**`BufFlush`**: Emits all dirty cells to the terminal via a single `fpWrite` syscall (V2b algorithm). Batches `ESC[?7l`, per-cell SGR and content, and `ESC[?7h` into `WBuf`, then calls `WBFlush`. Skips `ESC[r;cH` cursor-position when the cursor is already at the next adjacent cell (same row, next column). If `BufFlushEnabled = false`, clears dirty flags and returns immediately without writing to the terminal (used by the test suite). Always called after composing a complete frame; partial updates go through `BufPutCell` / `BufFill` first.

**`Redraw`**: Lightweight screen repaint — `BufFill` (clear buffer), `DrawBorder`, `DrawKeys`, `DrawInner`, `BufFlush`. Does not touch `Blocked` or call `InitLevel`. Use after overlay screens (help, story).

**`DrawScore` / `DrawLives` / `DrawPauses` / `DrawBlocks`**: Draw individual HUD counters; all called from `DrawBorder` (via `Redraw`) and also called individually when only one counter changes.

**`EnemyMove`** (enemy AI): Greedy chase. Each `EnemyTick`, computes `DX = EX - X`, `DY = EY - Y`. If `|DX| ≥ |DY|`, tries to move horizontally toward player first; falls back to vertical if blocked. Vice versa otherwise. No pathfinding — can get stuck behind walls.

**`HandleInput`**: Main input handler. Sets `KeyCode := 0` at entry so each keystroke is processed exactly once. Dispatches:
- Arrow keys → set `Direction`
- Home/End → adjust `MoveDelay`
- Space → toggle `Laying` (continuous block-placement mode)
- F1 → help screen
- F2 → story screen
- F3 → buy a life (5000 pts)
- P → pause (5 s, decrements `PausesRemaining`)
- Escape → quit (checked in main loop after `HandleInput`)
- F4 → restart (checked in main loop)
- F5 → `RemoveBlocks` (checked in main loop)

**`PlaceBlock`**: Places a `█` at the player's current position if not already blocked; costs 20 pts. Auto-disables `Laying` if points or block budget run out.

**`RemoveBlocks`**: Modal dialog (Y/N in English; J/N in German). On yes: clears interior `Blocked`, calls `InitLevel` (rebuilds level walls only — live position, direction, and enemy are untouched), redraws border, resets `BlockX`/`BlockY`. No point cost.

**`DrawItem` / `RandomPos`**: Place current treasure at a random non-blocked position.

**`HighScoreEntry`**: End-of-game high score entry. Reads player name, appends `name score` record to `UGLI.HSC`, then displays the full file content on screen.

## Main loop structure

Uses named `goto` labels:

```
label NewGame, StartLevel, PlayAgain, OnGameOver, CleanUp;
...
NewGame:    { Level := 1; Score := 0; Lives := 10; ItemNo := 1; PrepareLevel; LevelTransition }
StartLevel: { EnemyTick := 0; RandomPos }
            { repeat: Sleep(MoveDelay), DrawItem, HandleInput, EnemyMove, collision checks }
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


## Internationalisation (i18n)

All user-visible strings are declared as `resourcestring` (English defaults). FPC extracts them to `UGLI_2.rsj` at compile time. At runtime, `Init` calls `GetLanguageIDs` to detect the two-letter locale code and loads `translations/<lang>.mo` with `TranslateResourceStrings` if the file exists. `YesKey` and `NoKey` (sets of byte) are built from `sYesChar`/`sNoChar` resourcestrings after translation so the yes/no key characters track the loaded language.

`GetItemName(I)` is the sole access point for translated item names — `TItemData` no longer has a `Name` field. `DrawItemName` centres the current item name in the bottom border safe zone (cols 12–66).

To add a language: compile the game (generates `UGLI_2.rsj`), run `poe make-pot` to refresh `translations/UGLI_2.pot`, copy it to `translations/<lang>.po`, fill in `msgstr` values, compile with `msgfmt translations/<lang>.po -o translations/<lang>.mo`, and copy the `.mo` alongside the binary.

