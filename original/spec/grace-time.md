# Grace time improvements

## Status

- [ ] Item visible during level-start grace time
- [ ] Arrow key input accepted during grace time to set initial direction
- [ ] Grace time added after being caught (player, enemy, item visible)
- [ ] Game compiles (`poe build-original` exits 0)
- [ ] All tests pass (`poe test-original` exits 0)
- [ ] Manual check: item visible and direction choosable at level start
- [ ] Manual check: grace time after being caught feels right

## Current behaviour

- `LevelTransition` shows a "LEVEL N" dialog, waits for a key (which
  can set direction), then `Sleep(1000)`.  The 1-second sleep happens
  after the dialog closes but before the main loop starts — `RandomPos`
  hasn't been called yet, so the item isn't placed and isn't visible.
- `PlayerCaught` plays the caught sound, flashes the field,
  `Sleep(200)`, resets score/lives/ItemNo, calls `PrepareLevel`
  (which redraws the level with player and enemy), then returns
  directly into the main loop with no grace time.

## Design

### Grace period procedure

Extract a shared `GracePeriod` procedure used by both flows:

```pascal
procedure GracePeriod;
```

1. Call `RandomPos` to place the item (if `ItemX = 0`)
2. Draw the item, player, and enemy
3. `BufFlush`
4. `Sleep(1000)` — 1-second pause
5. Drain any keys pressed during the sleep; if an arrow key was
   pressed, update `Direction`

This replaces the `Sleep(1000)` in `LevelTransition` and adds
equivalent behaviour after `PlayerCaught`.

### LevelTransition changes

```
LevelTransition:
  Dialog(sLevelPrefix + S, sPressKey)  -- unchanged
  if arrow key from dialog → set Direction  -- unchanged
  GracePeriod                           -- replaces Sleep(1000)
```

### Main loop changes

Move `RandomPos` from `StartLevel:` into `GracePeriod` so the item is
placed before the grace period begins.  `StartLevel:` no longer calls
`RandomPos` directly (it already happened in the grace period).

After `PlayerCaught` returns in the main loop, call `GracePeriod`
before continuing.  This gives the player a moment to see the
repositioned field and choose a direction.

### PlayerCaught changes

No changes to `PlayerCaught` itself — it still handles the flash,
score penalty, lives, and `PrepareLevel`.  The grace period is added
by the caller (main loop).

## Done when

- [ ] Item visible during grace time at level start and after caught
- [ ] Arrow key during grace time sets initial direction
- [ ] Grace time after caught matches level-start grace time (1 s)
- [ ] Game compiles (`poe build-original` exits 0)
- [ ] All tests pass (`poe test-original` exits 0)
- [ ] Manual check: both grace time moments feel right
