# UGLYCRAFT

A modern Python/pygame remake of **UGLI** (1996), a DOS treasure-hunt game originally written in Turbo Pascal 7.

![UGLYCRAFT level 3 screenshot](screenshot.png)

Collect nine treasures in each of nine progressively harder levels while being hunted by an ever-closing enemy. Outsmart it by placing walls, buying a shield, or simply running faster than it can think.

---

## Features

- Nine hand-crafted levels with increasingly complex wall layouts
- Greedy chase AI that navigates around obstacles
- Interactive wall placement — block the enemy's path on the fly
- In-game shop: buy a shield or an extra life with collected points
- Adjustable speed (speed up or slow down at any time)
- High-score table persisted to disk
- Crisp pixel-art sprites, all drawn procedurally — no external assets
- Runs at a fixed 960×540 logical resolution, integer-scaled to fit any display:
  - 1024×768 → 1× (centred, black bars)
  - 1920×1080 → 2× (fills screen exactly)
  - `F11` toggles fullscreen

---

## Requirements

- Python 3.10 or later
- [pygame](https://www.pygame.org/) 2.x

---

## Installation

```bash
git clone <repo-url>
cd uglycraft
python3 -m venv .venv
.venv/bin/pip install pygame
```

---

## Running

```bash
.venv/bin/python main.py
```

---

## Controls

| Key | Action |
|---|---|
| Arrow keys | Move |
| `Space` | Place a wall on your current tile (costs 1 placement credit) |
| `Enter` | Open shop |
| `P` | Pause / unpause |
| `F11` | Toggle fullscreen |
| `Escape` | Quit to menu |

### Wall mechanics

Walk into any inner wall three times (releasing the arrow key between each hit) to destroy it. Every two walls destroyed earns one placement credit. Spend a credit with `S` to place a wall on your current tile. The outer border is indestructible.

### Shop

| Key | Item | Cost |
|---|---|---|
| `1` | Shield — absorbs the next hit | 1 000 pts |
| `2` | Extra life | 5 000 pts |

---

## Scoring

Each level contains nine treasures to collect in sequence:

| # | Treasure | Points |
|---|---|---|
| 1 | Rope | 0 |
| 2 | Big Diamond | 100 |
| 3 | Small Gems | 200 |
| 4 | Small Diamond | 300 |
| 5 | Gold Bar | 400 |
| 6 | Silver Bar | 500 |
| 7 | Well | 600 |
| 8 | Lamp | 700 |
| 9 | Big Gem (Crown on level 9) | 800 |

**Final score** = accumulated points × lives remaining when the game ends.

Being caught by the enemy costs `current_item_number × 1000` points and one life. A shield absorbs a single hit without penalty.

---

## Levels

| Level | Layout |
|---|---|
| 1 | Open field |
| 2 | Single horizontal wall |
| 3 | H-shape (two verticals + crossbar with gap) |
| 4 | Short pillars + horizontal barrier with gap |
| 5 | Cage with openings |
| 6 | Grid of pillar columns with a clear corridor |
| 7 | Three overlapping X-shapes |
| 8 | Alternating tall vertical walls (slalom) |
| 9 | Divided chambers — and the Crown awaits |

---

## Project structure

```
main.py        Entry point, display scaling, event loop
game.py        State machine, game logic, rendering
constants.py   Resolution, tile size, colours, timing
sprites.py     All sprites drawn procedurally (no image files)
levels.py      Nine level definitions (wall patterns)
entities.py    Player and Enemy classes
hiscore.py     Top-10 score persistence (uglycraft.hsc)
```

---

## Origins

UGLI was written in 1996 by Daniel Bausch using Turbo Pascal 7 for MS-DOS. The original source code is preserved in this repository (`UGLI_2.PAS`, `DANISOFT.PAS`, `EXTRA1.PAS`) as a historical reference. UGLYCRAFT shares its genre and rough level structure but is otherwise a fresh implementation.

---

## License

UGLYCRAFT is free software: you can redistribute it and/or modify it under the terms of the **GNU General Public License version 3** as published by the Free Software Foundation.

See [LICENSE](LICENSE) for the full text.

The original Pascal source files (`*.PAS`) are © 1996 Daniel Bausch and are included for historical reference only; they are not covered by the GPLv3 grant.
