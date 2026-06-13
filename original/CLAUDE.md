# UGLI 2 — Original DOS Game (1996)

Reference documentation for the original Turbo Pascal 7 source files kept in this repo. These files are released under the **GNU General Public License version 3**, the same licence as UGLYCRAFT. They can be built and run with Free Pascal (see `poe build-original`), and serve as design reference for the mechanics and level layouts that inspired UGLYCRAFT.

## Overview

UGLI (version 2, 1996) is a DOS text-mode game written in Turbo Pascal 7 by Daniel Bausch. The player navigates an 80×20 character field collecting 10 types of treasures across 9 levels while being chased by an AI enemy. High scores are saved to `UGLI.HSC`.

## Building (if you ever want to)

- **Turbo Pascal 7** (original): Open `UGLI_2.pp` in the TP7 IDE or run `tpc UGLI_2.pp`
- **Free Pascal / Linux** (recommended): `poe build-original` from the repo root. Fetches the three required UOS source files from GitHub on first run, then compiles with `fpc -Mtp -Fuuos UGLI_2.pp`. Requires `fpc` and `curl` on PATH, and `libportaudio` at runtime for sound.
- **DOSBox + TP7**: Mount the directory and compile from within DOSBox for authentic behaviour.

There are no tests, no lint tools, and no CI setup.

## File structure

### `DANISOFT.pp` (unit `DANISOFT`) — animated splash screen

- `UTF8Cols(S)`: counts display columns in a UTF-8 string (skips continuation bytes)
- `Center(S)`: pads `S` with leading spaces to centre it on an 80-column line
- `Intro`: scrolling colour/sound intro that displays an ASCII art logo (8 lines) with version/copyright info
- Depends on: `Crt`, `UOSSound`

### `UOSSound.pp` (unit `UOSSound`) — FPC/Linux sound

- Wraps UOS + PortAudio to provide `Sound(Hz)`, `NoSound`, `Ton(Hz, Ms)`
- Named effects: `SoundBump`, `SoundPickup`, `SoundCaught`, `SoundGameOver`, `SoundWon`
- Listed last in `uses` to shadow the empty CRT sound stubs on Linux
- UOS source fetched from GitHub at build time; requires `libportaudio.so.2` at runtime

### `UGLI_2.pp` (program `UGLI_2`) — the game itself

Uses `CThreads`, `CRT`, `DOS`, `DANISOFT`, `UOSSound`.

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
| `Direction` | Char | Last direction key pressed; player keeps moving in this direction each tick |
| `Laying` | Boolean | When `true`, a block is placed at the player's position every tick (Space toggles) |

## Key constants (`UGLI_2.pp`)

| Constant | Value | Meaning |
|---|---|---|
| `FieldW` / `FieldH` | 80 / 20 | Play field dimensions |
| `KeyRight/Left/Down/Up` | 77/75/80/72 | Scan codes for arrow keys |
| `KeyPause` / `KeySlower` / `KeyFaster` | 112 / 79 / 71 | P / End / Home |
| `KeyEscape` / `KeySpace` | 27 / 32 | Escape / Space |
| `KeyF1`–`KeyF5` | 59–63 | Function keys F1–F5 |
| `BlocksRemaining` | init 2000 | Block-placement budget |
| `HighScoreFileName` | `'UGLI.HSC'` | High score file path |

## Key procedures

**`InitLevel1`–`InitLevel9`**: Set player start position/direction and populate `Blocked` for level walls. Called via the `InitLevel(N)` dispatcher.

**`DrawBorder`**: Draws the `█` border and marks border cells in `Blocked`.

**`DrawFrame`**: Full level reset — clears `Blocked`, clears screen, calls `DrawBorder`, draws all counters, calls `InitLevel(Level)`, draws key help bar. Use only at genuine level-start time.

**`Redraw`**: Lightweight screen repaint — same visuals as `DrawFrame` but does not touch `Blocked` or call `InitLevel`. Use after overlay screens (help, story).

**`DrawScore` / `DrawLives` / `DrawPauses` / `DrawBlocks`**: Draw individual HUD counters; all called from `DrawFrame` and `Redraw`, and also called individually when only one counter changes.

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

**`RemoveBlocks`**: Modal dialog (J/N). On J: clears all `Blocked`, calls `InitLevel`, redraws border, restores player position and resets `BlockX`/`BlockY`. Always deducts 20 pts.

**`DrawItem` / `RandomPos`**: Place current treasure at a random non-blocked position.

**`HighScoreEntry`**: End-of-game high score entry. Reads player name, appends `name score` record to `UGLI.HSC`, then displays the full file content on screen.

## Main loop structure

Uses named `goto` labels:

```
label GameLoop, NewGame, NextItem, PlayAgain, OnGameOver, CleanUp;
...
GameLoop: { outer repeat — calls Init }
NewGame:  { reset Level=0, Lives=10, ItemNo=9 }
NextItem: { increment ItemNo; if 10: advance level, DrawFrame, LevelTransition }
          { repeat: Delay, DrawItem, HandleInput, EnemyMove, collision checks }
          {   treasure collected → goto NextItem }
          {   lives = 0 → goto OnGameOver }
          { until Escape }
OnGameOver: { calls GameOver }
PlayAgain:  { "NOCHMAL SPIELEN (J/N)" prompt }
            {   J → goto NewGame;  N → goto CleanUp }
CleanUp:  { ClrScr, reset terminal, exit }
```

## Treasure types (ItemNo 1–9)

| ItemNo | Name (German) | Points |
|---|---|---|
| 1 | Seil (Rope) | 0 |
| 2 | Großer Diamant (Big Diamond) | 100 |
| 3 | Kleine Edelsteine (Small Gems) | 200 |
| 4 | Kleiner Diamant (Small Diamond) | 300 |
| 5 | Goldbarren (Gold Bar) | 400 |
| 6 | Silberbarren (Silver Bar) | 500 |
| 7 | Brunnen (Well) | 600 |
| 8 | Lampe (Lamp) | 700 |
| 9 | Großer Edelstein (Big Gem) | 800 |

Points formula: `(ItemNo − 1) × 100`.

## Level structure (original 80×20 grid)

Levels are defined by the `InitLevel1`–`InitLevel9` procedures via `Blocked[x,y] := true` assignments. The field is 80 columns × 20 rows (1-indexed), bordered by `█` drawn by `DrawBorder`.

| Level | Theme |
|---|---|
| 1 | Open field — no interior walls |
| 2 | Single horizontal wall across middle |
| 3 | H-shape (two verticals connected by horizontal) |
| 4 | Short pillars + horizontal bar with gap |
| 5 | Cage (rectangular enclosure with small openings) |
| 6 | Grid of pillars (regularly spaced) |
| 7 | X-shapes / diagonal-feeling arrangements |
| 8 | Alternating tall vertical walls (slalom) |
| 9 | Divided chambers (multiple walled rooms) |

## Sound design

**Original DOS**: All sound via PC speaker. Frequencies played directly via port $42/$43.

**FPC/Linux port**: PC speaker is not accessible on Linux. Sound is instead provided by `UOSSound.pp`, a wrapper around UOS + PortAudio. It exposes the same `Sound(Hz)` / `NoSound` / `Ton(Hz, Ms)` interface as CRT (listed last in `uses` so it shadows the empty CRT stubs), plus named effect procedures: `SoundBump`, `SoundPickup`, `SoundCaught`, `SoundGameOver`, `SoundWon`. Requires `libportaudio.so.2` at runtime; falls back to silence if unavailable. UOS source is fetched from GitHub at build time — not committed to the repo.


## How UGLYCRAFT maps from the original

| Original | UGLYCRAFT |
|---|---|
| 80×20 text grid (1-indexed) | 30×16 tile grid (0-indexed, border at edges) |
| Column mapping | `col_new ≈ round((col_orig−1)/79 × 29)` |
| Row mapping | `row_new ≈ round((row_orig−1)/19 × 15)` |
| 9 levels | 10 levels (level 10 adds boss) |
| 1 enemy (greedy chase) | 1–3 enemies (greedy) + BFS boss on level 10 |
| Limited pauses (`PausesRemaining`) | Unlimited pause (P key) |
| Block budget (`BlocksRemaining`) | Wall-break credits (earn by breaking walls) |
| Text characters for sprites | Procedurally drawn pixel-art sprites |
| PC speaker sound | pygame.mixer (not yet implemented) |
| UGLI.HSC file | uglycraft.hsc (same concept) |

The remake is a loose spiritual remake — same genre and feel, not an exact port.
