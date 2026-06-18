# Async sound and `Ton` → `Beep` rename

## Status

- [x] Rename `Ton` to `Beep` in `UOSSound.pp` and all call sites
- [x] Add `BeepAsync(Hz, Ms)` — non-blocking, auto-silences after Ms
- [x] `SoundBump` uses `BeepAsync` (5 ms, no gameplay lag)
- [x] `SoundPickup` uses `BeepAsync` (50 ms, no pickup lag)
- [x] `SoundCaught` uses `BeepAsync` (200 ms, non-blocking)
- [x] `PlayerCaught` flashes entire field red for 200 ms while sound plays
- [x] Synchronous callers (`SoundGameOver`, `SoundWon`, intro) unchanged

## Background

The Turbo Pascal sound system uses `Sound(Hz)` + `Delay(Ms)` + `NoSound()`
to produce timed beeps.  The current FPC port replicates this in `Ton(Hz, Ms)`
which calls `Sound`, `Sleep`, `NoSound` — blocking the main thread.

Since UOS already runs in its own audio thread, the main thread only needs to
tell UOS *when to start* and *when to stop*.  For short gameplay sounds
(bump, pickup, caught) the blocking sleep adds unnecessary input lag.

## Design

### `BeepAsync(Hz, Ms)`

Starts the tone and returns immediately.  A background mechanism silences it
after `Ms` milliseconds.  If a new `Sound`, `Beep`, or `BeepAsync` call
arrives before the timer expires, the old timer is cancelled (the new sound
simply replaces it — no overlapping tones).

Implementation: use an `RTLEvent`.  A single persistent timer thread waits on
the event with a timeout equal to the requested duration.  On timeout it calls
`NoSound`.  On signal (new sound arrived) it restarts with the new duration.
The thread is created lazily on first `BeepAsync` call.

### `Beep(Hz, Ms)` (synchronous)

Same as current `Ton`: `Sound(Hz); Sleep(Ms); NoSound`.  Used by fanfares
and intro sequences where the delay is intentional and synchronized with
visuals.

### Red flash on `PlayerCaught`

When the player is caught, the entire playing field (rows 1–20, cols 1–80,
including the border) is filled with red background for 200 ms while the
caught sound plays asynchronously.  `PrepareLevel` is called immediately
after, which calls `Redraw` and restores the normal colours.

Implementation in `PlayerCaught`:
1. `BeepAsync(80, 200)` — start the caught sound
2. Paint every cell in `Screen[1..80, 1..20]` with a red background, flush
3. `Sleep(200)` — hold the red flash (sound plays in parallel)
4. Continue with `PrepareLevel` which redraws everything

### Sounds unchanged (remain synchronous)

| Procedure | Why keep blocking |
|---|---|
| `SoundGameOver` | Dramatic fanfare; `Dialog` follows and should wait |
| `SoundWon` | Celebration sequence before high-score entry |
| Intro colour sweep (line 720) | Each `Beep` is synchronized with a screen fill |
| Intro exit sweep (line 795) | Descending pitch during exit animation |

## Done when

- [x] `Ton` renamed to `Beep` everywhere; no remaining references to `Ton` — `592f6b3`
- [x] `BeepAsync` exists, is non-blocking, auto-silences after the given duration — `592f6b3`
- [x] Concurrent calls to `BeepAsync` or `Sound` cancel any pending timer (no overlap) — `592f6b3`
- [x] `SoundBump` calls `BeepAsync(40, 5)` — wall bumps don't block movement — `592f6b3`
- [x] `SoundPickup` calls `BeepAsync(250, 50)` — item pickup doesn't lag — `592f6b3`
- [x] `SoundCaught` calls `BeepAsync(80, 200)` — caught sound is non-blocking — `592f6b3`
- [x] `PlayerCaught` shows a full-field red flash for 200 ms during the sound — `592f6b3`
- [x] `SoundGameOver`, `SoundWon`, intro sounds still use synchronous `Beep` — `592f6b3`
- [x] Game compiles (`poe build-original` exits 0) — `592f6b3`
- [x] All tests pass (`poe test-original` exits 0) — `592f6b3`
- [x] Manual check: pickup no longer causes noticeable movement lag — confirmed
- [x] Manual check: red flash is visible when caught — confirmed
