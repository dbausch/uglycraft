# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

UGLI (version 2, 1996) is a DOS text-mode game written in Turbo Pascal 7 by Daniel Bausch. The player navigates an 80×20 character field collecting 10 types of treasures across 9 levels while being chased by an AI enemy. High scores are saved to `UGLI.HSC`.

## Building

This code targets **Turbo Pascal 7 for DOS**. There is no makefile or modern build system. Compilation options:

- **Turbo Pascal 7** (original): Open `UGLI_2.PAS` in the TP7 IDE or run `tpc UGLI_2.PAS`
- **Free Pascal** (modern): `fpc -Mtp UGLI_2.PAS` (TP compatibility mode). Note: `EXTRA1.PAS` uses `graph`, `Drivers`, and `Boosters` units which may need stubs or the WinCrt/graph replacements.
- **DOSBox + TP7**: Mount the directory and compile from within DOSBox for authentic behavior.

There are no tests, no lint tools, and no CI setup.

## Architecture

Three files, compiled in dependency order:

**`EXTRA1.PAS`** (unit `extra1`) — reusable TUI library. Provides:
- `Fenster`/`FensterMitObenLinks`/`FensterMitUntenMittig`: draw bordered windows with configurable corner/edge characters and colors via a DSL-style `Params` string (e.g. `FatLine`, `TwoLines` constants)
- `HLinie`/`VLinie`: draw horizontal/vertical lines
- `MyEingebProc`: inline text input field with cursor movement and editing
- `Auswahl`: menu selection from a `WahlRec` list
- `Ton`/`TonAuf`/`TonAb`/`DateiTon`: PC speaker sound routines
- `ColorPosWrite`, `Farbe`, `BlinkText`: color/position text output helpers
- `Zentriert`, `RechtsBund`, `Str`, `StrZahl`: string utilities
- Depends on CRT, DOS, `graph`, `Drivers`, `Boosters` (Turbo Pascal BGI)

**`DANISOFT.PAS`** (unit `DANISOFT`) — animated splash screen unit. Provides:
- `Erkennung`: scrolling color/sound intro that displays an ASCII art logo (8 lines) with version/copyright info
- `Erkennung2`: alternative intro with typewriter-effect text rendering
- Depends on `Extra1`

**`UGLI_2.PAS`** (program `ugli_2`) — the game itself. Uses `crt`, `dos`, `danisoft`.
- `sper[1..80, 1..20]: boolean` — collision map; walls and placed blocks set cells to `true`
- `initl1`–`initl9`: populate the collision map and set player start position/direction for each level
- `rahmen`: clears and redraws the border + current level layout
- `ugli2`: AI enemy movement — chooses x or y axis based on which delta is larger, moves toward player each `timeslot`
- `Taste`: main input handler; dispatches arrow keys, speed controls, help screens, and the in-game shop
- `ZahlenSetzung` / `ZufalsPos`: place the current treasure at a random non-blocked position
- `abfrage`: end-of-game high score entry; appends to `UGLI.HSC` then displays the full file
- Main loop uses `goto` labels (100, 300, 997, 998, 999) rather than structured loops

## Key constants (UGLI_2.PAS)

| Constant | Value | Meaning |
|----------|-------|---------|
| `MaxX`/`MaxY` | 80/20 | Play field dimensions |
| `CurR/L/U/O` | 77/75/80/72 | Scan codes for arrow keys |
| `langs` | init 45 | Base movement delay in ms (lower = faster) |
| `pausen` | init 20 | Number of pause tokens available |
| `steine` | init 2000 | Block-placement budget |
| `Name` | `'UGLI.HSC'` | High score file path |
