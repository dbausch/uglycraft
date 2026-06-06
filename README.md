# UGLYCRAFT

A Python/pygame spiritual remake of **UGLI** (1996), a DOS treasure-hunt game originally written in Turbo Pascal 7.

Collect nine treasures across ten progressively harder levels while being hunted by an ever-closing enemy. Outsmart it by placing walls, buying a shield, or simply staying one step ahead.

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

```bash
git clone <repo-url>
cd uglycraft
python3 -m venv .venv
.venv/bin/pip install pygame numpy
```

---

## Running

```bash
.venv/bin/python main.py
```

Debug flags (skip menus, start mid-game):

```bash
.venv/bin/python main.py --level N        # start at level N (1–10)
.venv/bin/python main.py --easy/--hard    # set difficulty (default: easy)
```

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

## Building a Linux executable

No cross-compilation needed — PyInstaller runs natively.

### One-time setup

```bash
.venv/bin/pip install pyinstaller
```

### Building

```bash
.venv/bin/pyinstaller --onefile --noconsole --name uglycraft main.py
```

Output: `dist/uglycraft` (~41 MB, self-contained).

### Testing

```bash
dist/uglycraft
```

---

## Building a Windows executable (from Linux)

### One-time setup

Requires Wine and the Python 3.13 Windows installer (Python 3.14 is not yet supported by pygame's Windows wheels).

```bash
# 1. Install Wine
sudo pacman -S wine          # Arch / Manjaro
# sudo apt install wine      # Debian / Ubuntu

# 2. Download Python 3.13 for Windows
curl -LO https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe

# 3. Install Python into Wine
#    In the GUI: tick "Add Python to PATH", then Install Now
wine python-3.13.0-amd64.exe

# 4. Install dependencies into the Wine Python
WINEDEBUG=-all wine \
  ~/.wine/drive_c/users/$USER/AppData/Local/Programs/Python/Python313/python.exe \
  -m pip install pygame numpy pyinstaller
```

### Building

```bash
WINEDEBUG=-all wine \
  ~/.wine/drive_c/users/$USER/AppData/Local/Programs/Python/Python313/python.exe \
  -m PyInstaller --onefile --noconsole --name uglycraft main.py
```

Output: `dist/uglycraft.exe` (~25 MB, self-contained).

The Wine prefix and all dependencies persist — subsequent rebuilds only need the PyInstaller command above.

### Testing

```bash
wine dist/uglycraft.exe
```

---

## Publishing to itch.io

Requires [butler](https://itch.io/docs/butler/) and a one-time `butler login`.

```bash
butler push dist/uglycraft     dbausch/uglycraft:linux-64   --userversion 1.0
butler push dist/uglycraft.exe dbausch/uglycraft:windows-64 --userversion 1.0
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

UGLI was written in 1996 by Daniel Bausch using Turbo Pascal 7 for MS-DOS. The original source code is preserved in this repository (`UGLI_2.PAS`, `DANISOFT.PAS`, `EXTRA1.PAS`) as a historical reference. UGLYCRAFT shares its genre and rough level structure but is otherwise a fresh implementation.

---

## License

UGLYCRAFT is free software: you can redistribute it and/or modify it under the terms of the **GNU General Public License version 3** as published by the Free Software Foundation.

See [LICENSE](LICENSE) for the full text.

The original Pascal source files (`*.PAS`) are © 1996 Daniel Bausch and are included for historical reference only; they are not covered by the GPLv3 grant.
