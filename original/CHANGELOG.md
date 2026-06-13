# CHANGELOG — UGLI 2 (Linux/FPC port)

All versions listed here refer to the FPC/Linux port of the original 1996 DOS
game. The DOS executable (UGLI_2.EXE) remains unchanged at version 2.0.

---

## 2.2

### Gameplay fixes
- Start with 10 lives instead of 9; the level-1 transition no longer awards a
  bonus life (it is the game start, not a level completion reward).
- Fix game reset after showing the help screen (F1) or the story screen (F2):
  the player position, direction, and placed blocks were incorrectly wiped
  because a full `DrawFrame` (which calls `InitLevel`) was used instead of a
  lightweight screen repaint.
- Fix the LevelTransition splash border colour: it was inheriting a stale text
  colour from the previous draw call instead of being explicitly white.
- Fix `RemoveBlocks`: after clearing all blocks, `BlockX`/`BlockY` were left
  pointing at the now-empty cell, causing movement functions to redraw a ghost
  block there. They are now reset to (1, 1) — a border cell that is always solid.

### Display fixes
- Score counter padded to 5 digits so shrinking scores do not leave stale
  digits on screen.
- Lives counter padded to 2 digits for the same reason.

### Code quality
- Replace numeric `goto` labels (100/300/997/998/999/1) with descriptive names:
  `NextItem`, `NewGame`, `PlayAgain`, `OnGameOver`, `CleanUp`, `GameLoop`.
- Define named constants for all remaining literal key codes:
  `KeyEscape`, `KeySpace`, `KeyF1`–`KeyF5`.
- `AwardPoints`: replace 9-line if-chain with formula `(ItemNo − 1) × 100`.
- Extract `DrawBorder` from `DrawFrame`; add a lightweight `Redraw` procedure
  (repaints visuals without touching game state) for use after overlay screens.
- `RemoveBlocks`: remove redundant first `DrawInner`, second key-wait prompt,
  duplicated border loop (now calls `DrawBorder`), wrong array bounds
  (`1..25` → `1..FieldH`), and a stray `LastName := ''`.
- Export `Center` and `UTF8Cols` from `DANISOFT`'s interface section; remove
  the duplicate local `Center` function that had been added to `UGLI_2`.
- `ShowStory`: use `DANISOFT.Center()` with column 1 so text is truly centred
  on the 80-column screen.
- `PlayAgain` prompt: draw the box once before the loop; loop only reads keys
  (was: `repeat … until I = 3000`, which also re-drew the box every iteration).
- `HandleInput`: set `KeyCode := 0` at the top so each keystroke is processed
  exactly once; main-loop checks (`Escape`, `F4`, `F5`) no longer fire stale.
- Space toggles continuous block-laying mode (`Laying`); `PlaceBlock` auto-
  disables `Laying` when points or blocks run out.
- `LevelTransition`: if a direction key is pressed while the splash is showing,
  that direction becomes the active direction after the transition.

---

## 2.1

### Gameplay changes
- Remove the shield feature and the shop menu entirely.
- Bind "buy a life (costs 5000 pts)" to F3; show the lives counter on screen at
  all times instead of requiring a key press.
- Pause is now purely time-based (5 s delay); the remaining-pauses count is
  shown permanently in the top-right corner of the frame.
- `SlowDown` (End) and `SpeedUp` (Home) now immediately adjust the delay
  without a blocking key wait.
- The player keeps moving in the last pressed direction; pressing any non-
  direction key no longer stops movement.
- Rebind block placement from S to Space; rebind "remove all placed blocks"
  from N to F5.
- The score counter, lives counter, pauses counter, and block counter are all
  drawn as named procedures (`DrawScore`, `DrawLives`, `DrawPauses`,
  `DrawBlocks`) called from `DrawFrame`, ensuring counters are always redrawn
  after overlays.
- The key-help bar is drawn by a `DrawKeys` procedure, eliminating duplicate
  definitions.
- Fix missing screen redraws after the help overlay and the story overlay.

### Source hygiene (FPC/Linux port)
- Rename all Pascal source files to the `.pp` extension (FPC convention).
- Rename `UOSSound` sound effects to English: `SoundBump`, `SoundWon`.
- Rename all identifiers in `UGLI_2.PAS` and `DANISOFT.PAS` to English
  PascalCase; two-letter position variables (`VX`, `VY`, `DX`, `DY`, …) to
  ALL_CAPS; apply consistent 2-space indentation and lowercase keywords
  throughout (see `STYLE.md` and `IDENTIFIERS.md`).

---

## 2.0 — first Linux/FPC release

Starting point: the original 1996 Turbo Pascal 7 / DOS source (`UGLI_2.PAS`,
`DANISOFT.PAS`) ported to compile and run under Free Pascal on Linux.

### Porting changes applied to reach 2.0
- Convert source files from CP437 to UTF-8; strip CRLF line endings.
- Replace `chr()`/`#N` graphic-character calls with Unicode literals
  (box-drawing characters, block elements, smiley face).
- Strip `DANISOFT.PAS` and `EXTRA1.PAS` down to the functions actually used;
  inline `Zentriert` from `EXTRA1` into `DANISOFT`; delete `EXTRA1.PAS`.
- Fix `Zentriert` to count UTF-8 display columns rather than bytes, so German
  umlauts do not shift centering left.
- Replace `CursorOff`/`CursorOn` with direct ANSI escape sequences via
  `/dev/tty`.
- Route all gameplay `Write()` calls through `WriteXY` to fix cursor
  positioning (CRT's cursor tracker diverged from the terminal's real cursor).
- Fix UTF-8 corruption at column 80 on narrow terminals (disable autowrap for
  the duration of each `WriteXY` call).
- Add UOS + PortAudio sound backend (`UOSSound.pp`) providing `Sound(Hz)`,
  `NoSound`, `Ton(Hz, Ms)`, and named effects; fetched at build time.
- Link `CThreads` to fix Runtime Error 232 on Linux.
- Fix UOS sound: stereo output, volume gating, endless-duration tones,
  suppress stderr noise from PortAudio.
- Reset terminal attributes on exit to prevent bold/colour leaking into shell.
- Adjust `DANISOFT` intro timing and layout for modern terminal emulators.
- Remove unused variables (`l`, `nehm`, `gx`, `gy`).
- Fix long-standing movement bugs: equal horizontal/vertical speed; enemy and
  player ghost artefacts; leftover text attributes after pause display.
- Refactor level initialisation into `InitLevel1`–`InitLevel9` procedures
  called via a dispatcher; centre the level-transition banner on the
  80-column field; extract `WriteLevel`.
- Replace licensee name with `Public Domain`; add GPLv3 licence notice.
