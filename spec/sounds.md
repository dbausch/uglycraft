# Sound and Music

## Status

- [x] `sounds.py` with `SoundManager` class
- [x] 14 procedural sound effects (all game events)
- [x] 10 procedural level music tracks (one per level)
- [x] Music tempo and darkness increase with level
- [x] Mixer pre-init in `main.py`
- [x] `SoundManager` integrated into `Game`
- [x] Music pauses/unpauses with P key
- [x] Title-screen music (D minor, orchestral fanfare)
- [x] Win-screen music (C major, joyful fanfare)

## Sound effects

| Name | Trigger | Sound design |
|---|---|---|
| `move` | Player steps to new tile | Soft click: 250 Hz impact + noise burst, 30 ms, drive 2.0 |
| `bump` | Player bumps destructible wall | Masonry thud: 95 Hz resonance + noise, 110 ms, drive 4.0 |
| `break` | Wall destroyed | Fracture: wide noise + 60 Hz rumble + debris layer, 220 ms, drive 5.5 |
| `collect` | Treasure picked up | FM bell arpeggio (C5 E5 G5 C6), ratio 1:1 idx 3.2, drive 2.2 |
| `credit` | Wall placement credit earned | Inharmonic bell chime: FM ratio 1:2.756 idx 2.8, two tones, drive 2.5 |
| `place_wall` | Wall placed at player's tile | Heavy stone thud: 80 Hz impact, 110 ms, drive 5.5 |
| `shield_buy` | Shield purchased with Enter | Electric charge-up: FM swept 300→1000 Hz, index 1.5→5.0, 280 ms, drive 3.2 |
| `shield_expire` | Shield timer runs out | Discharge: exponential pitch + index decay, 220 ms, drive 3.0 |
| `caught_shield` | Hit while shielded (absorbed) | Electric burst: FM idx 6.5 + noise crack, 220 ms, drive 4.5 |
| `caught` | Hit, life lost | Harsh FM descending phrase (6 notes, ratio 1:1.5 idx 4.5) + body thud |
| `level_up` | Level cleared or game won | Ascending FM fanfare (7 notes, ratio 1:1 idx 2.0) + sub-octave |
| `game_over` | All lives gone | Dark FM descending phrase (7 notes, ratio 1:1.4 idx 1.8) + sub-octave |
| `boss_appear` | Level 10 starts | Inharmonic FM swell (ratio 1:π swept) + high FM stab, 350 ms, drive 4.0 |
| `item_hit` | Boss walks over treasure (internal) | Noise transient + FM metallic ring (ratio 1:2.5 idx 3.0), 140 ms, drive 3.0 |

All 14 effects use three shared primitives: `_impact()` (decayed noise burst + resonant
sine), `_fm()` (frequency modulation), and `_saturate()` (tanh waveshaper).  Drive levels:
2.0 = gentle warmth · 3.0–3.5 = moderate grit · 4.5–5.5 = heavy clipping.

## Music system

All music generated procedurally in `sounds.py` using numpy.  No audio files.

### Synthesis voices

**Lead voice:** FM synthesis (carrier:mod 1:1, index 4.0) soft-clipped by tanh at drive
2.8.  Notes are staccato — each plays for 55% of the eighth-note slot.  A march-accent
array `[1.00, 0.65, 0.80, 0.65, 1.00, 0.65, 0.80, 0.65]` modulates amplitude: beats 1 & 3
hit hard, off-beats are soft.

**Second lead voice:** FM (carrier:mod 1:2.0, index 3.5, drive 2.4) one octave below the
first lead.  Plays quarter-note staccato hits (50 % of a beat slot) on each downbeat —
provides the "oom" of the marching pulse.

**Strings:** Two detuned sawtooth oscillators per chord tone (±0.4 % detune) on the root,
3rd, and 5th of each bar's chord.  Slow ADSR attack.  Sounded one octave below the
melody root.

**Bass:** Triangle wave.  Root on beats 1 & 3, fifth on beats 2 & 4.

**Brass accent:** Square wave stab on each bar's downbeat, fades over ~2 beats.

**Percussion (level tracks only):**
- Kick (decaying sine pitch sweep) on beats 1 and 3.
- Snare (noise + 220 Hz tone burst) on beats 2 and 4 (backbeat).
- Hi-hat (decaying white noise) on the "and" of every beat (off-eighth positions).

### Loop structure

Each level track is an **8-bar loop** at 8th-note resolution (64 steps).  Seamless — the
buffer starts and ends on beat boundaries.  Composed melodic themes of 64 explicit MIDI
pitches drive the lead voice.  Full theme descriptions: `spec/music-themes.md`.

### Title and win screen music

**Title screen** (`key='title'`): D natural minor, 80 BPM, 4 bars.
Orchestration: thick detuned strings in two octaves, low triangle bass, square brass pedal,
timpani on bars 1 & 3, pulse-wave lead with an upper-harmonic doubling.  Melody descends
stepwise with upward lifts — dark, stately, epic.

**Win screen** (`key='win'`): C major, 108 BPM, 4 bars.
Same orchestration as the title theme.  Progression: C – Am – F – G.  Melody opens with a
rising C major arpeggio (fanfare gesture), descends warmly through Am and F, climbs back
for a satisfying G→C resolution.  Joyful but not pompous.

### Level music parameters

| Level | BPM | Key | Mode | Character |
|-------|-----|-----|------|-----------|
| 1 | 96 | A | Dorian | Dark groove |
| 2 | 101 | D | Natural minor | Tense chase |
| 3 | 106 | G | Phrygian | Ominous |
| 4 | 111 | A | Harmonic minor | Exotic danger |
| 5 | 116 | E | Natural minor | Furious |
| 6 | 120 | B | Phrygian | Very tense |
| 7 | 125 | F# | Natural minor | Dark pursuit |
| 8 | 130 | C# | Diminished | Chaotic |
| 9 | 135 | G# | Phrygian | Terrifying |
| 10 | 140 | — | Chromatic diminished | Boss / mechanical |

## Architecture

**File:** `sounds.py`

```
SoundManager
  .__init__()       — generates all SFX and music tracks; handles init errors gracefully
  .play(name)       — fire-and-forget SFX on auto-assigned channel
  .start_music(key) — start looping track; key = 'title', 'win', or int 1–10
                      no-op if already playing the same key
  .stop_music()     — stop music channel; clears current-key tracking
  .pause_music()    — pause music channel (for P-pause)
  .unpause_music()  — resume music channel
```

Channel 0 is reserved for music; channels 1–15 are used by SFX.

**`main.py`:** `pygame.mixer.pre_init(44100, -16, 2, 512)` before `pygame.init()`.

**`game.py` integration hooks:**

| Where | Call |
|---|---|
| `__init__` | `self.sounds = SoundManager()` |
| `_title_init` | `sounds.start_music('title')` |
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
| `_end_game(won=True)` | `sounds.stop_music()`; `sounds.play('level_up')`; `sounds.start_music('win')` |
| `_end_game(won=False)` | `sounds.stop_music()`; `sounds.play('game_over')` |
| P key pressed → PAUSED | `sounds.pause_music()` |
| P key pressed → PLAYING | `sounds.unpause_music()` |

## Done when

- [x] `sounds.py` exists; `SoundManager` importable; fails gracefully without numpy — 1b3ffa2
- [x] All 14 SFX audible at appropriate game events — 1b3ffa2, c2939ec, f8e0938, ad65207
- [x] 10 level music tracks with composed melodic themes loop without gaps — 1b3ffa2, 46c2bfc, 641cc2d, a0ba633, 02cd34d, a09a4de
- [x] Each level's music is noticeably faster and darker than the previous — 1b3ffa2, 641cc2d
- [x] Music pauses when P is pressed and resumes on P again — 1b3ffa2
- [x] Boss-appear sting plays when entering level 10 — 1b3ffa2
- [x] Game continues normally if mixer init fails (silent fallback) — 1b3ffa2
- [x] Title-screen music plays on the title screen — c2939ec
- [x] Win-screen music plays when the player clears all 10 levels — (this session)
