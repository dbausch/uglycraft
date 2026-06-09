# UGLI 2 — Original DOS Game (1996)

Reference documentation for the original Turbo Pascal 7 source files kept in this repo. These files are released under the **GNU General Public License version 3**, the same licence as UGLYCRAFT. They can be built and run with Free Pascal (see `poe build-original`), and serve as design reference for the mechanics and level layouts that inspired UGLYCRAFT.

## Overview

UGLI (version 2, 1996) is a DOS text-mode game written in Turbo Pascal 7 by Daniel Bausch. The player navigates an 80×20 character field collecting 10 types of treasures across 9 levels while being chased by an AI enemy. High scores are saved to `UGLI.HSC`.

## Building (if you ever want to)

- **Turbo Pascal 7** (original): Open `UGLI_2.PAS` in the TP7 IDE or run `tpc UGLI_2.PAS`
- **Free Pascal / Linux** (recommended): `poe build-original` from the repo root. Fetches the three required UOS source files from GitHub on first run, then compiles with `fpc -Mtp -Fuuos UGLI_2.PAS`. Requires `fpc` and `curl` on PATH, and `libportaudio` at runtime for sound.
- **DOSBox + TP7**: Mount the directory and compile from within DOSBox for authentic behaviour.

There are no tests, no lint tools, and no CI setup.

## File structure

### `DANISOFT.PAS` (unit `DANISOFT`) — animated splash screen

- `Erkennung`: scrolling color/sound intro that displays an ASCII art logo (8 lines) with version/copyright info
- `Erkennung2`: alternative intro with typewriter-effect text rendering, playing ascending tones as characters appear
- Depends on: `Crt`, `uossound`

### `uossound.pas` (unit `uossound`) — FPC/Linux sound

- Wraps UOS + PortAudio to provide `Sound(Hz)`, `NoSound`, `Ton(Hz, Ms)`
- Named effects: `SoundBrumm`, `SoundPickup`, `SoundCaught`, `SoundGameOver`, `SoundGewonnen`
- Listed last in `uses` to shadow the empty CRT sound stubs on Linux
- UOS source fetched from GitHub at build time; requires `libportaudio.so.2` at runtime

### `UGLI_2.PAS` (program `ugli_2`) — the game itself

Uses `cthreads`, `crt`, `dos`, `danisoft`, `uossound`.

## Key data structures (`UGLI_2.PAS`)

| Identifier | Type | Meaning |
|---|---|---|
| `sper[1..80, 1..20]` | `boolean` array | Collision map; walls and placed blocks set cells to `true` |
| `sperblock[1..2000]` | record array | Tracks player-placed blocks (position + char) for removal |
| `steine` | integer | Block-placement budget (starts 2000, decremented on place) |
| `zahl` | integer | Current treasure index (1–9, then wraps per level) |
| `punkte` | longint | Score |
| `leben` | integer | Lives remaining |
| `pausen` | integer | Pause tokens remaining (starts 20) |
| `langs` | integer | Movement delay in ms (lower = faster; Home/End adjusts) |
| `sx`, `sy` | integer | Player position (1-indexed, column × row) |
| `ex`, `ey` | integer | Enemy position |
| `schild` | boolean | Whether player has active shield |

## Key constants (`UGLI_2.PAS`)

| Constant | Value | Meaning |
|---|---|---|
| `MaxX` / `MaxY` | 80 / 20 | Play field dimensions |
| `CurR/L/U/O` | 77/75/80/72 | Scan codes for arrow keys (right/left/down/up) |
| `langs` | init 45 | Base movement delay in ms (lower = faster) |
| `pausen` | init 20 | Number of pause tokens available |
| `steine` | init 2000 | Block-placement budget |
| `Name` | `'UGLI.HSC'` | High score file path |

## Key procedures

**`initl1`–`initl9`**: Populate `sper` collision map and set player start position/direction for each level. Each draws walls directly using `GotoXY` + character writes and marks corresponding `sper` cells. Levels are defined inline as sequences of `GotoXY`/`Write` calls — no separate data structure.

**`rahmen`**: Clears screen and redraws the border (double-line box characters) + current level layout by calling the appropriate `initlN`.

**`ugli2`** (enemy AI): Greedy chase. Each `timeslot`, computes `dx = ex - sx`, `dy = ey - sy`. If `|dx| ≥ |dy|`, tries to move horizontally toward player first; falls back to vertical if blocked. Vice versa otherwise. No pathfinding — can get stuck behind walls.

**`Taste`**: Main input handler. Dispatches:
- Arrow keys → move player (checks `sper`, plays bump sound if blocked)
- Home/End → speed up/slow down (`langs` ± 5)
- Space → open shop (`Leben` for 5000 pts, `Schild` for 1000 pts)
- S → place block at player position (decrements `steine`, appends to `sperblock`)
- N → remove all player-placed blocks (iterates `sperblock`, clears `sper` entries)
- P → pause (decrements `pausen` token; unlimited if `pausen` ≤ 0 handling not present)
- F1 → help screen
- Escape → quit prompt

**`ZahlenSetzung` / `ZufalsPos`**: Place current treasure at a random non-blocked position. `ZufalsPos` picks random `(x, y)` until `sper[x,y] = false` and position is not occupied by player/enemy.

**`abfrage`**: End-of-game high score entry. Reads player name via `MyEingebProc`, appends `name|score|level` record to `UGLI.HSC`, then displays the full file content on screen.

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

## Treasure types (zahl 1–9, plus Crown)

| zahl | Name (German) | Points |
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

Levels are defined by the `initl1`–`initl9` procedures via inline `GotoXY`/`Write` calls. The field is 80 columns × 20 rows (1-indexed), bordered by a double-line box drawn by `rahmen`. Interior walls are single or double line characters.

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

**FPC/Linux port**: PC speaker is not accessible on Linux. Sound is instead provided by `uossound.pas`, a wrapper around UOS + PortAudio. It exposes the same `Sound(Hz)` / `NoSound` / `Ton(Hz, Ms)` interface as CRT (listed last in `uses` so it shadows the empty CRT stubs), plus named effect procedures: `SoundBrumm`, `SoundPickup`, `SoundCaught`, `SoundGameOver`, `SoundGewonnen`. Requires `libportaudio.so.2` at runtime; falls back to silence if unavailable. UOS source is fetched from GitHub at build time — not committed to the repo.


## How UGLYCRAFT maps from the original

| Original | UGLYCRAFT |
|---|---|
| 80×20 text grid (1-indexed) | 30×16 tile grid (0-indexed, border at edges) |
| Column mapping | `col_new ≈ round((col_orig−1)/79 × 29)` |
| Row mapping | `row_new ≈ round((row_orig−1)/19 × 15)` |
| 9 levels | 10 levels (level 10 adds boss) |
| 1 enemy (greedy chase) | 1–3 enemies (greedy) + BFS boss on level 10 |
| Limited pauses (`pausen`) | Unlimited pause (P key) |
| Block budget (`steine`) | Wall-break credits (earn by breaking walls) |
| Text characters for sprites | Procedurally drawn pixel-art sprites |
| PC speaker sound | pygame.mixer (not yet implemented) |
| UGLI.HSC file | uglycraft.hsc (same concept) |

The remake is a loose spiritual remake — same genre and feel, not an exact port.
