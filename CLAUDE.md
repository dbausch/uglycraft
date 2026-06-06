# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current version

**v0.9** — bump this whenever a new git tag is created.

## What this is

This repo contains two things:

1. **The original game** — UGLI (version 2, 1996), a DOS text-mode game written in Turbo Pascal 7 by Daniel Bausch. Three source files: `UGLI_2.PAS`, `DANISOFT.PAS`, `EXTRA1.PAS`. See [`original/CLAUDE.md`](original/CLAUDE.md) for a full analysis of the original code, data structures, and mechanics.

2. **UGLYCRAFT** — a new Python/pygame spiritual remake of UGLI, written from scratch. This is the active project.

## Running UGLYCRAFT

```bash
.venv/bin/python main.py
```

Virtual environment at `.venv` (Python 3.14, pygame 2.6.1). Create with `python3 -m venv .venv && .venv/bin/pip install pygame`.

Debug flags (skip menus, start mid-game):

```bash
.venv/bin/python main.py --level N      # start at level N (1–10)
.venv/bin/python main.py --easy / --hard  # set difficulty (default: easy)
```

In debug mode the high-score entry screen is suppressed.

## Architecture (8 Python files)

| File | Role |
|---|---|
| `constants.py` | Logical resolution, tile size, colours, timing constants |
| `sprites.py` | All sprites drawn procedurally via `pygame.draw` — no image files |
| `levels.py` | 10 level definitions as dicts with `walls` and `enemy_starts` |
| `entities.py` | `Player` and `Enemy` (+ `Entity` base) — tile-grid movement, BFS pathfinding |
| `hiscore.py` | Top-10 score persistence to `uglycraft.hsc` |
| `sounds.py` | `SoundManager` — 14 procedural SFX + 12 music tracks (10 levels, title, win) |
| `game.py` | Full state machine + rendering |
| `main.py` | Window creation, integer scaling, top-level event loop |

## Key design

**Resolution:** 960×540 logical (16:9). Integer-scaled to fit display. F11 toggles fullscreen.

**Grid:** 30 columns × 16 rows of 32×32 px tiles. Status bar is 28 px tall (bottom). Border tiles are always walls.

**Sprites:** All procedurally drawn — no external image files.

**Enemy sprites:** Three ogre types selected by level group: ogre 1 (levels 1–3), ogre 2 (levels 4–6), ogre 3 (levels 7–9). Level 10 uses a 4-phase animated boss ogre. Four bouncing ogres (one per type) are shown in the title-screen corners.

**Difficulty:** Easy uses only the first `enemy_starts` position (1 enemy); Hard uses all positions (1 enemy for levels 1–3, 2 for levels 4–6, 3 for levels 7–9, always 1 boss on level 10).

**Treasure sequence (`item_no`):** Collect items 1–9 in order per level, then advance. On level 10 (boss level), item_no=9 is replaced by item_no=10 (Crown), which spawns at a fixed position inside the vault.

**Scoring:** Points on collection (100/200/…/900 for item_no 1–9, 1000 for the Crown on level 10). Final score = accumulated score × lives remaining. High scores record both the score and the level reached.

**Lives:** Start with 9. +1 on each level clear. On caught: if shielded → shield consumed, no life lost, hitting enemy respawned far away; else lose a life, deduct `LIFE_PENALTY` pts (min 0), player returns to level start, hitting enemy still respawned far away.

**Shield:** Press Enter in-game to instantly buy a shield for `SHIELD_COST_PTS` pts (requires score ≥ cost, no shield already active). Shield lasts `SHIELD_DURATION_MS` ms then expires automatically. HUD shows remaining seconds.

**Wall mechanics:** Inner walls have hit points (`WALL_HITS_TO_BREAK = 3`). Bumping a wall damages it; after enough hits it breaks. Every `BREAKS_PER_CREDIT = 2` walls destroyed earns one wall-placement credit. Space places a wall at the player's tile (costs 1 credit).

**Speed scaling:** Both player and enemies are 7% slower per level below 10: `interval = BASE_MS × 1.07^(10 − level)`. Level 10 always runs at the base rates (`BASE_MOVE_MS` / `BOSS_MOVE_MS`).

**Enemy AI (levels 1–9):** Greedy chase — if |dx| ≥ |dy| tries horizontal first, else vertical first; falls back to perpendicular if blocked. Moves every `BASE_ENEMY_MS = 160` ms (scaled by level).

**Boss AI (level 10):** Single boss ogre. On Hard uses BFS pathfinding (always finds shortest path); on Easy uses the same greedy chase as normal enemies. Moves every `BOSS_MOVE_MS = 80` ms (same speed as player). If boss walks over a treasure it is relocated to a new random open tile.

**Sound:** `SoundManager` in `sounds.py` owns all audio. 14 procedural SFX (FM synthesis, physical impact modelling, tanh saturation). 10 level music tracks (8-bar loops, composed melodic themes, marching rhythm). Title screen and win screen each have their own orchestral loop. Music key: `'title'`, `'win'`, or `int 1–10`. Fails silently if numpy or the mixer is unavailable.

## Key constants (`constants.py`)

| Constant | Value | Meaning |
|---|---|---|
| `COLS` / `ROWS` | 30 / 16 | Play field dimensions in tiles |
| `TILE` | 32 | Tile size in pixels |
| `BASE_MOVE_MS` | 80 | Player movement interval at level 10 (ms); scaled up on earlier levels |
| `BASE_ENEMY_MS` | 160 | Normal enemy movement interval at level 10 (ms); scaled up on earlier levels |
| `BOSS_MOVE_MS` | 80 | Boss movement interval (ms); not scaled — boss always moves at player speed |
| `STARTING_LIVES` | 9 | Lives at game start |
| `WALL_HITS_TO_BREAK` | 3 | Bumps to destroy one inner wall |
| `BREAKS_PER_CREDIT` | 2 | Walls destroyed per placement credit earned |
| `SHIELD_COST_PTS` | 250 | Instant shield cost (Enter key) |
| `SHIELD_DURATION_MS` | 10000 | Shield lifetime in ms |
| `LIFE_PENALTY` | 500 | Flat points lost on death |
| `FPS` | 30 | Frame rate cap |

## Game states

```
TITLE → DIFFICULTY → LEVEL_INTRO → PLAYING ↔ PAUSED
                                       ↓
                                GAME_OVER / WIN → ENTER_SCORE → SHOW_SCORES → PLAY_AGAIN
                                               ↘ SHOW_SCORES ↗  (if score doesn't qualify)
```

`PLAY_AGAIN` goes back to `DIFFICULTY` (yes) or `TITLE` (no).

A `STORY` state exists in code but is not reachable from the UI.

## Controls

**Title screen**

| Key | Action |
|---|---|
| Enter | Start game (goes to difficulty selection) |
| H | View high scores |
| Q | Quit |

**In-game**

| Key | Action |
|---|---|
| Arrow keys | Move (held = auto-repeat after 180 ms, then every 80 ms); bump a wall 3× to mine it |
| Space | Place wall at player's tile (costs 1 placement credit) |
| Enter | Buy shield instantly (250 pts, lasts 10 s) |
| P | Pause / unpause |
| Escape | Go to "play again?" prompt |
| F10 | Cheat: skip to next level |
| F11 | Toggle fullscreen |
