# UGLYCRAFT

A Python/pygame spiritual remake of **UGLI** (1996), a DOS treasure-hunt game originally written in Turbo Pascal 7.

Collect nine treasures across ten progressively harder levels while being hunted by an ever-closing enemy. Outsmart it by placing walls, buying a shield, or simply staying one step ahead.

**Download compiled binaries (Linux, Windows, and the original DOS game) at [dbausch.itch.io/uglycraft](https://dbausch.itch.io/uglycraft).**

![UGLYCRAFT level 7 — hard mode](screenshot.png)

---

## Features

- Ten hand-crafted levels with increasingly complex wall layouts
- Level 10: a boss enemy with BFS pathfinding and its own locked vault
- Three ogre enemy types that escalate in appearance across level groups
- Interactive wall placement — block the enemy's path on the fly
- Instant shield purchase — absorbs one hit, no shop screen
- Procedural sound effects and music — no external audio files
- High-score table persisted to disk
- All sprites drawn procedurally — no external image files
- Fixed 960×540 logical resolution, integer-scaled to fit any display; F11 toggles fullscreen

---

## Requirements

- Python 3.10 or later
- [pygame](https://www.pygame.org/) 2.x
- [numpy](https://numpy.org/) (for sound; game runs silently without it)

---

## Installation

Install the required tools if you don't have them yet:

```bash
sudo apt install pipx python3-virtualenv   # Debian / Ubuntu
sudo pacman -S python-pipx python-virtualenv  # Arch / Manjaro
pipx ensurepath         # add ~/.local/bin to PATH (then restart your shell)
pipx install poethepoet
```

Clone and set up:

```bash
git clone https://github.com/dbausch/uglycraft.git
cd uglycraft
poe install
```

---

## Building

### Linux executable

```bash
poe build-linux
```

Output: `dist/linux-64/uglycraft` (~41 MB, self-contained).

### Windows executable

Requires Wine (one-time system install):

```bash
sudo pacman -S wine   # Arch / Manjaro
# sudo apt install wine   # Debian / Ubuntu
```

Then set up Python under Wine (one-time):

```bash
poe setup-windows
```

Then build:

```bash
poe build-windows
```

Output: `dist/windows-64/uglycraft.exe` (~25 MB, self-contained).

### Original UGLI 2 (Linux port)

Requires Free Pascal (one-time system install):

```bash
sudo pacman -S fpc   # Arch / Manjaro
# sudo apt install fpc   # Debian / Ubuntu
```

Then build:

```bash
poe build-original
```

Output: `original/UGLI_2`. Requires a terminal of at least 80×25 characters. Tested in [kitty](https://sw.kovidgoyal.net/kitty/).

---

## Running

```bash
poe run
poe run-level 5          # start at a specific level
```

Or directly:

```bash
.venv/bin/python main.py --level N        # start at level N (1–10)
.venv/bin/python main.py --easy/--hard    # set difficulty (default: easy)
```

---

## Deploying to itch.io

Requires [butler](https://itch.io/docs/butler/) and a one-time `butler login`.

```bash
poe deploy                 # push all four channels
poe deploy-original-linux  # push FPC Linux port only
poe deploy-original-dos    # push original DOS exe only
```

`poe deploy` reads the version from the latest git tag automatically.

---

## Controls

| Key | Action |
|---|---|
| Arrow keys | Move; bump a wall 3× to mine it |
| Space | Place wall on current tile (costs 1 credit) |
| Enter | Buy shield instantly (250 pts, lasts 10 s) |
| P | Pause / unpause |
| Escape | Quit to menu |
| F10 | Skip to next level (cheat) |
| F11 | Toggle fullscreen |

---

## Scoring

Each level contains nine treasures to collect in sequence. Points are awarded on collection:

| # | Treasure | Points |
|---|---|---|
| 1 | Coin | 100 |
| 2 | Big Diamond | 200 |
| 3 | Small Gems | 300 |
| 4 | Trophy | 400 |
| 5 | Gold Ingot | 500 |
| 6 | Platinum Ingot | 600 |
| 7 | Necklace | 700 |
| 8 | Lantern | 800 |
| 9 | Emerald | 900 |
| 10 | Crown (level 10 only) | 1000 |

**Final score** = accumulated points × lives remaining.  
Being caught without a shield costs 500 points and one life.

---

## All poe tasks

```bash
poe install                # create venv and install dependencies
poe run                    # run the game
poe run-level N            # run starting at level N
poe build-linux            # build dist/linux-64/uglycraft
poe setup-windows          # one-time: install Python + deps into Wine
poe build-windows          # build dist/windows-64/uglycraft.exe
poe build-original         # build original/UGLI_2 with FPC
poe clean                  # remove all build artifacts
poe deploy                 # push all four itch.io channels
poe deploy-uglycraft       # push Linux and Windows only
poe deploy-original-linux  # push FPC Linux port only
poe deploy-original-dos    # push original DOS exe only
```

---

## Project structure

```
main.py        Entry point, display scaling, event loop
game.py        State machine, game logic, rendering
constants.py   Resolution, tile size, colours, timing
sprites.py     All sprites drawn procedurally (no image files)
levels.py      Ten level definitions (wall patterns + enemy starts)
entities.py    Player and Enemy classes (BFS pathfinding for boss)
sounds.py      SoundManager — 14 SFX + 12 music tracks, all procedural
hiscore.py     Top-10 score persistence (uglycraft.hsc)
```

---

## Origins

UGLI was first written in 1993 by Daniel Bausch using Turbo Pascal on MS-DOS, then developed further through 1996 into a second version with improved mechanics including wall placement. The 1996 source code (`UGLI_2.PAS`, `DANISOFT.PAS`, `EXTRA1.PAS`) is preserved in this repository as a historical reference. UGLYCRAFT shares the genre and core mechanics but is otherwise a fresh implementation.

![UGLI 2 (1996) — screenshot from the FPC port running on Linux](screenshot-original-linux.png)

The screenshot above is taken from the Free Pascal port of the original, running in a Linux terminal. The video below is a let's play of the original DOS executable in DOSBox:

[![UGLI 2 let's play on YouTube](https://img.youtube.com/vi/czsqF9CXxNE/0.jpg)](https://youtu.be/czsqF9CXxNE?si=ySZGeo_gj0kxmMw6)

---

## License

UGLYCRAFT is free software: you can redistribute it and/or modify it under the terms of the **GNU General Public License version 3** as published by the Free Software Foundation.

See [LICENSE](LICENSE) for the full text.

### Third-party licenses (distributables)

The standalone executables bundle the following third-party libraries:

| Library | License | Full text |
|---------|---------|-----------|
| pygame | LGPL 2.1 | `LICENSES/LGPL-2.1.txt` |
| numpy | BSD 3-Clause | `LICENSES/BSD-3-Clause-numpy.txt` |

See `LICENSES/NOTICE.txt` for a summary of bundled components and how to obtain their source.
