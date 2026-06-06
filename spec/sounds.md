# Sound and Music

## Overview

| # | Deliverable | Status |
|---|---|---|
| 1 | `sounds.py` with `SoundManager` class | ✗ |
| 2 | 13 procedural sound effects (all game events) | ✗ |
| 3 | 10 procedural music tracks (one per level) | ✗ |
| 4 | Music tempo and tension increase with level | ✗ |
| 5 | Mixer pre-init in `main.py` | ✗ |
| 6 | `SoundManager` integrated into `Game` | ✗ |
| 7 | Music pauses/unpauses with P key | ✗ |

## Sound effects

| Name | Trigger | Sound design |
|---|---|---|
| `move` | Player steps to new tile | Very short high blip (25 ms square) |
| `bump` | Player bumps destructible wall | Low thud: triangle + noise, 100 ms |
| `break` | Wall destroyed | Noisy crash: noise + low triangle, 220 ms |
| `collect` | Treasure picked up | Rising 4-note arpeggio (C5 E5 G5 C6) |
| `credit` | Wall placement credit earned | Two-tone chime (E5 → A5) |
| `place_wall` | Wall placed at player's tile | Solid thunk (square 220 Hz, 90 ms) |
| `shield_buy` | Shield purchased with Enter | Ascending frequency sweep, 280 ms |
| `shield_expire` | Shield timer runs out | Descending sweep, 220 ms |
| `caught_shield` | Hit while shielded (shield absorbed) | Noise burst + tone, 220 ms |
| `caught` | Hit, life lost | Descending diminished phrase (6 notes) |
| `level_up` | Level cleared or game won | Ascending major fanfare (7 notes) |
| `game_over` | All lives gone | Descending chromatic phrase (7 notes) |
| `boss_appear` | Level 10 starts | Ominous low drone + high stab, 350 ms |

## Music system

All music generated procedurally in `sounds.py` using numpy.  No audio files.

**Structure:** Each track is a 4-bar loop at 8th-note resolution.
**Voices:** Square wave melody (arpeggio over chord changes), triangle wave
bass (root/fifth alternation on quarter notes).
**Loop:** Seamless — buffer starts and ends on beat boundaries.

**Arpeggio patterns** (scale degree indices 0–4, staying within a fifth;
-1 = rest):

| Name | Pattern | Character |
|---|---|---|
| `_ARP_A` | `[0,2,4,2, 0,2,4,2]` | Gentle ascending-descending |
| `_ARP_B` | `[0,4,2,-1, 4,2,4,0]` | Bouncy with rest |
| `_ARP_C` | `[0,2,4,4, 2,4,2,0]` | Fifth emphasis |
| `_ARP_D` | `[0,4,2,4, 2,4,4,0]` | Persistent push |
| `_ARP_E` | `[0,2,3,2, 4,3,2,0]` | Minor/dim colour (degree 3) |
| `_ARP_F` | `[0,4,3,4, 0,3,4,-1]` | Tense, with rest |

**Level music parameters:**

| Level | BPM | Key | Mode | Chord prog | Character |
|-------|-----|-----|------|------------|-----------|
| 1 | 90 | C | Major | I–V–vi–IV | Cheerful |
| 2 | 100 | G | Major | I–IV–V–I | Lively |
| 3 | 110 | D | Major | I–V–IV–V | Energetic |
| 4 | 120 | A | Major | I–IV–V–I | Adventurous |
| 5 | 130 | E | Major | I–IV–I–V | Driving |
| 6 | 140 | A | Minor | i–VII–VI–VII | Tense |
| 7 | 150 | D | Minor | i–iv–VII–i | Urgent |
| 8 | 160 | G | Minor | i–III–VII–i | Dark |
| 9 | 170 | E | Phrygian | i–♭II–i–♭II | Ominous |
| 10 | 180 | — | Diminished | descending dim | Terrifying |

## Architecture

**New file:** `sounds.py`

```
SoundManager
  .__init__()       — generates all SFX and music tracks; handles init errors gracefully
  .play(name)       — fire-and-forget SFX on auto-assigned channel
  .start_music(lvl) — start looping track for level (no-op if already on that level)
  .stop_music()     — stop music channel; clears current-level tracking
  .pause_music()    — pause music channel (for P-pause)
  .unpause_music()  — resume music channel
```

Channel 0 is reserved for music; channels 1–15 are used by SFX.

**`main.py`:** `pygame.mixer.pre_init(44100, -16, 2, 512)` before `pygame.init()`.

**`game.py` integration hooks:**

| Where | Call |
|---|---|
| `__init__` | `self.sounds = SoundManager()` |
| `_start_level` | `sounds.start_music(level_num)`; play `boss_appear` on level 10 |
| `_try_move_key` | `sounds.play('move')` on successful step |
| `_register_bump` | `sounds.play('bump')` when wall hit (not broken) |
| `_break_wall` | `sounds.play('break')`; `sounds.play('credit')` if credit earned |
| `_buy_shield` | `sounds.play('shield_buy')` on success |
| `_place_wall` | `sounds.play('place_wall')` on success |
| `_on_caught` | `sounds.play('caught_shield')` or `sounds.play('caught')` |
| `_update_playing` (shield expire) | `sounds.play('shield_expire')` |
| `_update_playing` (treasure) | `sounds.play('collect')` |
| `_advance_level` (not final) | `sounds.play('level_up')` |
| `_end_game` | `sounds.stop_music()`; play `level_up` or `game_over` |
| P key pressed → PAUSED | `sounds.pause_music()` |
| P key pressed → PLAYING | `sounds.unpause_music()` |

## Done when:

1. ✗ `sounds.py` exists; `SoundManager` importable; fails gracefully without numpy.
2. ✗ All 13 SFX audible at appropriate game events.
3. ✗ Music tracks 1–10 generate and loop without gaps or clicks.
4. ✗ Each level's music is noticeably faster and darker than the previous.
5. ✗ Music pauses when P is pressed and resumes on P again.
6. ✗ Boss-appear sting plays when entering level 10.
7. ✗ Game continues normally if mixer init fails (silent fallback).
