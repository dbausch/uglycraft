# UGLI 2 — Original DOS Game (1996)

Reference documentation for the original Turbo Pascal 7 source files kept in this repo. These files are released under the **GNU General Public License version 3**, the same licence as UGLYCRAFT. They can be built and run with Free Pascal (see `poe build-original`), and serve as design reference for the mechanics and level layouts that inspired UGLYCRAFT.

## Overview

UGLI (version 2, 1996) is a DOS text-mode game written in Turbo Pascal 7 by Daniel Bausch. The player navigates an 80×20 character field collecting 10 types of treasures across 9 levels while being chased by an AI enemy. High scores are saved to `UGLI.HSC`.

## Building (if you ever want to)

- **Turbo Pascal 7** (original): Open `UGLI_2.pas` in the TP7 IDE or run `tpc UGLI_2.pas`
- **Free Pascal / Linux** (recommended): `poe build-original` from the repo root. Fetches the three required UOS source files from GitHub on first run, then compiles with `fpc -Mtp -Fuuos UGLI_2.pas`. Requires `fpc` and `curl` on PATH, and `libportaudio` at runtime for sound.
- **DOSBox + TP7**: Mount the directory and compile from within DOSBox for authentic behaviour.

There are no tests, no lint tools, and no CI setup.

## File structure

### `DANISOFT.pas` (unit `DANISOFT`) — animated splash screen

- `Intro`: scrolling color/sound intro that displays an ASCII art logo (8 lines) with version/copyright info
- `Intro2`: alternative intro with typewriter-effect text rendering, playing ascending tones as characters appear
- Depends on: `Crt`, `UOSSound`

### `UOSSound.pas` (unit `UOSSound`) — FPC/Linux sound

- Wraps UOS + PortAudio to provide `Sound(Hz)`, `NoSound`, `Ton(Hz, Ms)`
- Named effects: `SoundBump`, `SoundPickup`, `SoundCaught`, `SoundGameOver`, `SoundWon`
- Listed last in `uses` to shadow the empty CRT sound stubs on Linux
- UOS source fetched from GitHub at build time; requires `libportaudio.so.2` at runtime

### `UGLI_2.pas` (program `UGLI_2`) — the game itself

Uses `CThreads`, `CRT`, `DOS`, `DANISOFT`, `UOSSound`.

## Key data structures (`UGLI_2.pas`)

| Identifier | Type | Meaning |
|---|---|---|
| `Blocked[1..80, 1..20]` | `Boolean` array | Collision map; walls and placed blocks set cells to `true` |
| `SperBlock[1..2000]` | record array | Tracks player-placed blocks (position + char) for removal |
| `BlocksRemaining` | Integer | Block-placement budget (starts 2000, decremented on place) |
| `ItemNo` | Integer | Current treasure index (1–9, then wraps per level) |
| `Score` | LongInt | Score |
| `Lives` | Integer | Lives remaining |
| `PausesRemaining` | Integer | Pause tokens remaining (starts 20) |
| `MoveDelay` | Integer | Movement delay in ms (lower = faster; Home/End adjusts) |
| `BlockX`, `BlockY` | Integer | Player position (1-indexed, column × row) |
| `EX`, `EY` | Integer | Enemy position |
| `Shield` | Boolean | Whether player has active shield |

## Key constants (`UGLI_2.pas`)

| Constant | Value | Meaning |
|---|---|---|
| `FieldW` / `FieldH` | 80 / 20 | Play field dimensions |
| `KeyRight/Left/Down/Up` | 77/75/80/72 | Scan codes for arrow keys |
| `MoveDelay` | init 45 | Base movement delay in ms (lower = faster) |
| `PausesRemaining` | init 20 | Number of pause tokens available |
| `BlocksRemaining` | init 2000 | Block-placement budget |
| `HighScoreFileName` | `'UGLI.HSC'` | High score file path |

## Key procedures

**`InitLevel1`–`InitLevel9`**: Populate `Blocked` collision map and set player start position/direction for each level. Each draws walls directly using `GotoXY` + character writes and marks corresponding `Blocked` cells. Levels are defined inline as sequences of `GotoXY`/`Write` calls — no separate data structure.

**`DrawFrame`**: Clears screen and redraws the border (double-line box characters) + current level layout by calling the appropriate `InitLevelN`.

**`EnemyMove`** (enemy AI): Greedy chase. Each `EnemyTick`, computes `DX = EX - BlockX`, `DY = EY - BlockY`. If `|DX| ≥ |DY|`, tries to move horizontally toward player first; falls back to vertical if blocked. Vice versa otherwise. No pathfinding — can get stuck behind walls.

**`HandleInput`**: Main input handler. Dispatches:
- Arrow keys → move player (checks `Blocked`, plays bump sound if blocked)
- Home/End → speed up/slow down (`MoveDelay` ± 5)
- Space → open shop (`Lives` for 5000 pts, `Shield` for 1000 pts)
- S → place block at player position (decrements `BlocksRemaining`, appends to `SperBlock`)
- N → remove all player-placed blocks (iterates `SperBlock`, clears `Blocked` entries)
- P → pause (decrements `PausesRemaining` token)
- F1 → help screen
- Escape → quit prompt

**`DrawItem` / `RandomPos`**: Place current treasure at a random non-blocked position. `RandomPos` picks random `(x, y)` until `Blocked[x,y] = false` and position is not occupied by player/enemy.

**`HighScoreEntry`**: End-of-game high score entry. Reads player name, appends `name|score|level` record to `UGLI.HSC`, then displays the full file content on screen.

## Main loop structure

Uses `goto` labels rather than structured loops:

```
label 100, 300, 997, 998, 999;
...
100: { start of level loop — calls initlN, spawns treasure }
300: { main game tick — calls ugli2 (enemy move), Taste (input), checks collision }
     { if treasure collected → ZahlenSetzung, check level complete → goto 100 }
     { if caught → lose life, check game over → goto 998 }
     goto 300;
997: { level complete fanfare }
998: { game over sequence → abfrage }
999: { exit }
```

## Treasure types (ItemNo 1–9, plus Crown)

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
| 10 | Krone (Crown) | — (level 9 special) |

## Level structure (original 80×20 grid)

Levels are defined by the `InitLevel1`–`InitLevel9` procedures via inline `GotoXY`/`Write` calls. The field is 80 columns × 20 rows (1-indexed), bordered by a double-line box drawn by `DrawFrame`. Interior walls are single or double line characters.

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

**FPC/Linux port**: PC speaker is not accessible on Linux. Sound is instead provided by `UOSSound.pas`, a wrapper around UOS + PortAudio. It exposes the same `Sound(Hz)` / `NoSound` / `Ton(Hz, Ms)` interface as CRT (listed last in `uses` so it shadows the empty CRT stubs), plus named effect procedures: `SoundBump`, `SoundPickup`, `SoundCaught`, `SoundGameOver`, `SoundWon`. Requires `libportaudio.so.2` at runtime; falls back to silence if unavailable. UOS source is fetched from GitHub at build time — not committed to the repo.


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
