# UGLYCRAFT — Sound System Reference

## Generation

All sounds are generated at `SoundManager.__init__` time using numpy arrays at `SR = 44100 Hz`. SFX RNG is seeded with `42` (fixed, deterministic). Level music RNGs are seeded with `level * 13`.

`_ok = False` and all dicts empty if numpy is unavailable, `pygame.mixer.init` fails, or any other exception during generation. All `play()` / `start_music()` calls silently no-op. The game is fully playable without audio.

## Waveform Primitives

| Name | Description |
|---|---|
| `_sq` | Sign of sin — ideal square wave |
| `_tri` | Triangle: `abs(2 * ((t*f)%1) - 1) * 2 - 1` |
| `_sin` | Pure sine |
| `_saw` | Sawtooth: `2 * ((t*f)%1) - 1` |
| `_pulse` | Duty-cycle square: `(t*f)%1 < duty` |
| `_env` | ADSR envelope (times in seconds, sustain level in 0–1) |
| `_fm` | FM: carrier modulated by `sin(2π * carrier * mod_ratio * t)` at given index |
| `_saturate` | tanh waveshaper, normalised ±1 → ±1 |
| `_impact` | Exponentially decayed noise + decaying sine (physical impact sounds) |

## Music Architecture

Each of the 10 level tracks is an 8-bar loop. `eighth_s = 30.0 / bpm` (one eighth note = half a beat). BPM range: ~96 (level 1) to ~140 (level 10), incrementing ~4–5 per level.

**Per bar, 8 voices:**
1. **Strings** — detuned sawtooth pair at ±0.4% detune; root + 3rd + 5th of the bar's scale
2. **Bass** — triangle; root on beats 1 & 3, 5th on beats 2 & 4
3. **Brass** — square stab on beat 1 only, fades over 2 beats
4. **Lead melody** — staccato FM pulse per non-rest step in `_LEVEL_THEMES`; duration 55% of eighth note
5. **Second lead** — FM stabs at the octave below; quarter-note duration (50% of beat)
6. **Kick** — beats 1 and 3
7. **Snare** — beats 2 and 4 (backbeat)
8. **Hi-hat** — off-eighth positions ("and" of every beat)

Melody content per level comes from `_LEVEL_THEMES` — a dict mapping level number to a list of 64 step entries (8 bars × 8 steps), each entry a MIDI note or `None` (rest).

## Music Key Scheme

`start_music(key)` accepts `'title'`, `'win'`, or `int 1–10`. Deduplication: if `_current_key == key`, returns immediately — music is not restarted. This means music continues from where it left off when the player dies and stays on the same level (intentional).

Music occupies channel 0 exclusively; SFX use channels 1+.

## SFX Trigger Map

| Sound key | Trigger |
|---|---|
| `move` | Successful player step |
| `bump` | Wall collision, 1st or 2nd hit |
| `break` | Wall destroyed (3rd hit) |
| `collect` | Treasure picked up |
| `credit` | Wall-break credit earned |
| `place_block` | Player places a block |
| `shield_buy` | Shield purchased (Enter) |
| `shield_expire` | Shield timer reaches 0 |
| `caught_shield` | Caught while shielded |
| `caught` | Caught without shield (life lost) |
| `level_up` | Level advance (also on win) |
| `game_over` | Game over |
| `boss_appear` | Level 10 start |
| `item_hit` | Boss walks over a non-Crown treasure |
| `denied` | Refused deliberate action — shared "action denied" beep (spec 0074): keyless door, refused bridge, refused block placement, refused shield buy. One per key press; silent on inert-barrier navigation and plain wall mining. |
