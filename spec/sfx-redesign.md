# SFX Redesign — FM synthesis + physical impact + tanh saturation

## Overview

| # | Deliverable | Status |
|---|---|---|
| 1 | `_fm()` helper — FM synthesis voice | ✗ |
| 2 | `_saturate()` helper — tanh waveshaper, applied to every SFX | ✗ |
| 3 | `_impact()` helper — noise transient + resonant sine tail | ✗ |
| 4 | Percussive SFX rebuilt with `_impact` (move, bump, break, place_wall, caught, item_hit) | ✗ |
| 5 | Tonal SFX rebuilt with FM (collect, credit, shield_buy, shield_expire, caught_shield, level_up, game_over, boss_appear) | ✗ |

## Design

**`_fm(carrier_hz, mod_ratio, index, n)`**
`sin(2π·fc·t + index · sin(2π·fm·t))` where `fm = fc × mod_ratio`.
- ratio 1:1, index 2 → warm brass
- ratio 1:1, index 3 → bright bell
- ratio 1:2.756, index 2.8 → inharmonic bell (real bell partial series)
- ratio 1:1.4–1.5, index 4–5 → harsh, metallic, dense
- ratio 1:π (inharmonic), sweeping index → alien/ominous

**`_saturate(x, drive)`**
`tanh(x · drive) / tanh(drive)` — unified warm/gritty texture on all SFX.
Drive levels: 2.0 (gentle) · 3.0–3.5 (moderate) · 4.5–5.5 (heavy clipping).

**`_impact(noise_vol, tone_hz, tone_vol, noise_decay, tone_decay)`**
Physical model: white-noise burst with exponential decay (transient attack)
+ sine resonance with exponential decay (body vibration).

## SFX redesign targets

| Name | Technique | Drive | Description |
|---|---|---|---|
| `move` | impact | 2.0 | Soft tile click: 250 Hz resonance + fast noise burst |
| `bump` | impact | 4.0 | Masonry thud: 95 Hz resonance, slow noise decay |
| `break` | impact × 2 | 5.5 | Fracture: wide noise + 60 Hz rumble + debris layer |
| `collect` | FM 1:1 idx 3.2 | 2.2 | Bright bell arpeggio, C5–C6 major |
| `credit` | FM 1:2.756 idx 2.8 | 2.5 | Inharmonic bell chime, two tones |
| `place_wall` | impact | 5.5 | Heavy stone thud: 80 Hz, dense low decay |
| `shield_buy` | FM swept | 3.2 | Electric charge-up: carrier 300→1000 Hz, index 1.5→5.0 |
| `shield_expire` | FM swept | 3.0 | Discharge: pitch/index exponential decay |
| `caught_shield` | FM idx 6.5 + noise | 4.5 | Electric burst: harsh FM + noise crack |
| `caught` | FM 1:1.5 idx 4.5 + impact | 4.5 | Harsh descent + final body thud |
| `level_up` | FM 1:1 idx 2 + sub | 2.5 | Brass-like fanfare ascending |
| `game_over` | FM 1:1.4 idx 1.8 + sub | 3.0 | Dark descending phrase |
| `boss_appear` | FM 1:π swept + stab | 4.0 | Inharmonic swell + high FM stab |
| `item_hit` | impact + FM 1:2.5 | 3.0 | Thud + metallic ring |

## Done when:

1. ✗ All SFX audibly distinct from chiptune square/triangle sources.
2. ✗ Impact SFX (move/bump/break/place_wall) sound physically grounded.
3. ✗ FM SFX (collect/credit/shields/level_up/game_over) have metallic/harmonic complexity.
4. ✗ Tanh saturation gives consistent grit across all sounds.
5. ✗ `SoundManager._ok` still True after change; game runs without errors.
