"""sounds.py — Procedural sound effects and background music for UGLYCRAFT.

All audio generated algorithmically — no audio files required.

Orchestral voices (retro/simple synthesis):
  Strings  — detuned sawtooth pair (warm, sustained)
  Bass     — triangle (rounded, punchy)
  Brass    — square wave accents (bright, stabby)
  Lead     — 25%-duty pulse (woodwind-like, cutting)
  Timpani  — sine with exponential pitch+amp decay
  Hi-hat   — exponentially decayed white noise
"""
from __future__ import annotations
import pygame

_RATE = 44100   # sample rate Hz


def _import_numpy():
    try:
        import numpy as np
        return np
    except ImportError:
        return None


# ── Scales (semitone offsets from root, 8 entries each) ──────────────────────

_MAJ  = [0, 2, 4, 5, 7, 9, 11, 12]
_MIN  = [0, 2, 3, 5, 7, 8, 10, 12]
_DOR  = [0, 2, 3, 5, 7, 9, 10, 12]   # Dorian — minor with raised 6th
_PHR  = [0, 1, 3, 5, 7, 8, 10, 12]   # Phrygian — flat 2nd, very dark
_HARM = [0, 2, 3, 5, 7, 8, 11, 12]   # Harmonic minor — raised 7th, exotic
_DIM  = [0, 2, 3, 5, 6, 8,  9, 11]   # Diminished — all tritones

# ── Waveform primitives ───────────────────────────────────────────────────────

def _hz(midi: float) -> float:
    return 440.0 * 2.0 ** ((midi - 69.0) / 12.0)

def _sq(np, freq: float, n: int, vol: float = 1.0):
    """Square wave — bright, buzzy (brass/sfx)."""
    t = np.arange(n, dtype=np.float32) / _RATE
    return np.sign(np.sin(2.0 * np.pi * freq * t)) * vol

def _tri(np, freq: float, n: int, vol: float = 1.0):
    """Triangle wave — smooth, rounded (bass)."""
    t = np.arange(n, dtype=np.float32) / _RATE
    p = (t * freq) % 1.0
    return (2.0 * np.abs(2.0 * p - 1.0) - 1.0) * vol

def _sin(np, freq: float, n: int, vol: float = 1.0):
    t = np.arange(n, dtype=np.float32) / _RATE
    return np.sin(2.0 * np.pi * freq * t) * vol

def _saw(np, freq: float, n: int, vol: float = 1.0):
    """Sawtooth wave — harmonically rich (strings)."""
    t = np.arange(n, dtype=np.float32) / _RATE
    return (2.0 * ((t * freq) % 1.0) - 1.0) * vol

def _pulse(np, freq: float, n: int, duty: float = 0.25, vol: float = 1.0):
    """Pulse wave — brighter than square (woodwind lead)."""
    t = np.arange(n, dtype=np.float32) / _RATE
    return ((t * freq % 1.0 < duty).astype(np.float32) * 2.0 - 1.0) * vol

def _env(np, n: int, atk: float, dec: float, sus: float, rel: float):
    """ADSR envelope; atk/dec/rel in seconds, sus in [0, 1]."""
    env = np.ones(n, dtype=np.float32) * sus
    a = min(round(atk * _RATE), n)
    d = min(round(dec * _RATE), n - a)
    r = min(round(rel * _RATE), n)
    r0 = max(n - r, 0)
    if a: env[:a]    = np.linspace(0.0, 1.0, a)
    if d: env[a:a+d] = np.linspace(1.0, sus, d)
    if r: env[r0:]  *= np.linspace(1.0, 0.0, n - r0)
    return env

def _to_sound(np, arr) -> pygame.Sound:
    mono = np.clip(arr, -1.0, 1.0)
    stereo = np.column_stack([mono, mono])
    return pygame.sndarray.make_sound((stereo * 32767.0).astype(np.int16))


# ── FM synthesis + saturation helpers ────────────────────────────────────────

def _fm(np, carrier_hz: float, mod_ratio: float, index: float, n: int, vol: float = 1.0):
    """FM synthesis: carrier modulated by carrier×mod_ratio at given index."""
    t = np.arange(n, dtype=np.float32) / _RATE
    return np.sin(2.0*np.pi*carrier_hz*t + index * np.sin(2.0*np.pi*carrier_hz*mod_ratio*t)) * vol


def _saturate(np, x, drive: float = 3.0):
    """Tanh waveshaper normalised so ±1 input → ±1 output."""
    return np.tanh(x * drive) / np.tanh(drive)


def _impact(np, rng, n: int, noise_vol: float, tone_hz: float, tone_vol: float,
            noise_decay: float = 80.0, tone_decay: float = 15.0):
    """Physical impact: exponentially decayed noise burst + resonant sine."""
    t = np.arange(n, dtype=np.float32) / _RATE
    noise = rng.standard_normal(n).astype(np.float32) * noise_vol * np.exp(-t * noise_decay)
    tone  = np.sin(2.0*np.pi*tone_hz*t) * tone_vol * np.exp(-t * tone_decay)
    return noise + tone


# ── Sound effects ─────────────────────────────────────────────────────────────

def _build_sfx(np) -> dict:
    rng = np.random.default_rng(42)

    def sfx_move():
        n   = round(_RATE * 0.030)
        sig = _impact(np, rng, n, 0.15, 250.0, 0.30, noise_decay=180.0, tone_decay=70.0)
        return _to_sound(np, _saturate(np, sig, 2.0))

    def sfx_bump():
        n   = round(_RATE * 0.110)
        sig = _impact(np, rng, n, 0.40, 95.0, 0.35, noise_decay=38.0, tone_decay=7.0)
        return _to_sound(np, _saturate(np, sig, 4.0))

    def sfx_break():
        n   = round(_RATE * 0.220)
        n2  = round(_RATE * 0.150)
        sig  = _impact(np, rng, n,  0.55, 60.0,  0.40, noise_decay=14.0, tone_decay=4.5)
        sig2 = _impact(np, rng, n2, 0.30, 130.0, 0.20, noise_decay=45.0, tone_decay=18.0)
        buf = sig.copy()
        buf[:n2] += sig2
        return _to_sound(np, _saturate(np, buf, 5.5))

    def sfx_collect():
        notes = [72, 76, 79, 84]
        nd  = round(_RATE * 0.038)
        buf = np.zeros(nd * len(notes), dtype=np.float32)
        for i, m in enumerate(notes):
            t  = np.arange(nd, dtype=np.float32) / _RATE
            ev = np.exp(-t * 14.0) * 0.40
            buf[i*nd:(i+1)*nd] = _saturate(np, _fm(np, _hz(m), 1.0, 3.2, nd) * ev, 2.2)
        return _to_sound(np, buf)

    def sfx_credit():
        nd  = round(_RATE * 0.055)
        buf = np.zeros(nd * 2, dtype=np.float32)
        for i, m in enumerate([76, 81]):
            t  = np.arange(nd, dtype=np.float32) / _RATE
            ev = np.exp(-t * 9.0) * 0.45
            buf[i*nd:(i+1)*nd] = _saturate(np, _fm(np, _hz(m), 2.756, 2.8, nd) * ev, 2.5)
        return _to_sound(np, buf)

    def sfx_place_wall():
        n   = round(_RATE * 0.110)
        sig = _impact(np, rng, n, 0.50, 80.0, 0.40, noise_decay=30.0, tone_decay=5.5)
        return _to_sound(np, _saturate(np, sig, 5.5))

    def sfx_shield_buy():
        n = round(_RATE * 0.280)
        t = np.arange(n, dtype=np.float32) / _RATE
        c_hz  = 300.0 + 700.0 * (t / t[-1])
        m_idx = 1.5   +   3.5 * (t / t[-1])
        c_ph  = np.cumsum(2.0 * np.pi * c_hz / _RATE)
        m_ph  = np.cumsum(2.0 * np.pi * c_hz * 0.5 / _RATE)
        wave  = np.sin(c_ph + m_idx * np.sin(m_ph)) * 0.40
        ev    = _env(np, n, 0.020, 0.030, 0.70, 0.08)
        return _to_sound(np, _saturate(np, wave * ev, 3.2))

    def sfx_shield_expire():
        n = round(_RATE * 0.220)
        t = np.arange(n, dtype=np.float32) / _RATE
        c_hz  = 900.0 * np.exp(-t * 6.0) + 120.0
        m_idx = 4.0   * np.exp(-t * 5.0) + 0.5
        c_ph  = np.cumsum(2.0 * np.pi * c_hz / _RATE)
        m_ph  = np.cumsum(2.0 * np.pi * c_hz * 0.75 / _RATE)
        wave  = np.sin(c_ph + m_idx * np.sin(m_ph)) * 0.35
        ev    = _env(np, n, 0.005, 0.015, 0.65, 0.14)
        return _to_sound(np, _saturate(np, wave * ev, 3.0))

    def sfx_caught_shield():
        n = round(_RATE * 0.220)
        t = np.arange(n, dtype=np.float32) / _RATE
        wave  = _fm(np, 240.0, 1.0, 6.5, n, 0.30)
        noise = rng.standard_normal(n).astype(np.float32) * 0.25 * np.exp(-t * 35.0)
        sig   = (wave + noise) * _env(np, n, 0.002, 0.025, 0.35, 0.12)
        return _to_sound(np, _saturate(np, sig, 4.5))

    def sfx_caught():
        midi_seq = [72, 69, 66, 63, 60, 57]
        nd  = round(_RATE * 0.050)
        buf = np.zeros(nd * len(midi_seq), dtype=np.float32)
        for i, m in enumerate(midi_seq):
            t  = np.arange(nd, dtype=np.float32) / _RATE
            ev = np.exp(-t * 10.0) * 0.35
            buf[i*nd:(i+1)*nd] = _saturate(np, _fm(np, _hz(m), 1.5, 4.5, nd) * ev, 4.5)
        n_thud = round(_RATE * 0.080)
        buf[:n_thud] += _saturate(np, _impact(np, rng, n_thud, 0.45, 80.0, 0.30,
                                              noise_decay=40.0, tone_decay=8.0), 4.0)
        return _to_sound(np, np.clip(buf, -1.0, 1.0))

    def sfx_level_up():
        midi_seq = [60, 64, 67, 72, 76, 79, 84]
        nd  = round(_RATE * 0.048)
        buf = np.zeros(nd * len(midi_seq), dtype=np.float32)
        for i, m in enumerate(midi_seq):
            t   = np.arange(nd, dtype=np.float32) / _RATE
            ev  = np.exp(-t * 7.0) * 0.38
            sub = np.sin(2.0*np.pi*_hz(m-12)*t) * np.exp(-t * 9.0) * 0.18
            buf[i*nd:(i+1)*nd] = _saturate(np, _fm(np, _hz(m), 1.0, 2.0, nd) * ev + sub, 2.5)
        return _to_sound(np, buf)

    def sfx_game_over():
        midi_seq = [60, 59, 57, 55, 53, 52, 48]
        nd  = round(_RATE * 0.070)
        buf = np.zeros(nd * len(midi_seq), dtype=np.float32)
        for i, m in enumerate(midi_seq):
            t   = np.arange(nd, dtype=np.float32) / _RATE
            ev  = np.exp(-t * 5.5) * 0.38
            sub = np.sin(2.0*np.pi*_hz(m-12)*t) * np.exp(-t * 7.0) * 0.18
            buf[i*nd:(i+1)*nd] = _saturate(np, _fm(np, _hz(m), 1.4, 1.8, nd) * ev + sub, 3.0)
        return _to_sound(np, buf)

    def sfx_boss_appear():
        n = round(_RATE * 0.350)
        t = np.arange(n, dtype=np.float32) / _RATE
        c_hz  = 35.0 + 45.0 * (t / t[-1])
        m_idx = 6.0  * (t / t[-1])
        c_ph  = np.cumsum(2.0 * np.pi * c_hz / _RATE)
        m_ph  = np.cumsum(2.0 * np.pi * c_hz * np.pi / _RATE)
        drone = np.sin(c_ph + m_idx * np.sin(m_ph)) * 0.35 * _env(np, n, 0.05, 0.10, 0.70, 0.15)
        n2    = round(_RATE * 0.090)
        stab  = _fm(np, _hz(84), 1.0, 4.0, n2, 0.40) * _env(np, n2, 0.003, 0.015, 0.0, 0.07)
        buf   = drone.copy()
        buf[:n2] += stab
        return _to_sound(np, _saturate(np, buf, 4.0))

    def sfx_item_hit():
        n   = round(_RATE * 0.140)
        sig = _impact(np, rng, n, 0.28, 120.0, 0.22, noise_decay=60.0, tone_decay=10.0)
        n2  = round(_RATE * 0.120)
        t2  = np.arange(n2, dtype=np.float32) / _RATE
        ring = _fm(np, 440.0, 2.5, 3.0, n2, 0.22) * np.exp(-t2 * 18.0)
        buf  = sig.copy()
        buf[:n2] += ring
        return _to_sound(np, _saturate(np, buf, 3.0))

    def sfx_entrance_open():
        # The entrance unlocks (spec 0066): a big, distorted "ta-daa" fanfare
        # — a stab, then a note a perfect FOURTH above, held and ringing
        # (~1 s).  A detuned-sawtooth ENSEMBLE with vibrato gives a choir
        # "aah" shimmer over the brass core; heavy tanh saturation adds the
        # grit.  Distinct from every other cue, so it never reads as "usual".
        def _voice(midi, n, vol, env):
            t = np.arange(n, dtype=np.float32) / _RATE
            f = _hz(midi)
            vib = 1.0 + 0.006 * np.sin(2.0 * np.pi * 5.5 * t)   # ~5.5 Hz vibrato
            # Choir: an ensemble of detuned saws (supersaw) → many-voices "aah".
            choir = np.zeros(n, dtype=np.float32)
            for d in (-0.013, -0.008, -0.003, 0.003, 0.008, 0.013, 0.019):
                ph = np.cumsum(2.0 * np.pi * f * (1.0 + d) * vib / _RATE)
                choir += 2.0 * ((ph / (2.0 * np.pi)) % 1.0) - 1.0
            choir /= 7.0
            # Brass core (square + fifth) for the fanfare body.
            core = _sq(np, f, n, 0.7) + _sq(np, f * 1.5, n, 0.35)
            return _saturate(np, (choir * 1.5 + core) * env * vol, 7.0)

        ta  = round(_RATE * 0.18)          # "ta"  — short accent
        gap = round(_RATE * 0.02)
        daa = round(_RATE * 0.80)          # "daa" — held, swelling choir
        buf = np.zeros(ta + gap + daa, dtype=np.float32)
        buf[:ta] += _voice(67, ta, 0.34,   # G4
                           _env(np, ta, 0.006, 0.05, 0.70, 0.05))
        off = ta + gap
        buf[off:off+daa] += _voice(72, daa, 0.36,   # C5 — a fourth above G4
                                   _env(np, daa, 0.030, 0.12, 0.78, 0.35))
        return _to_sound(np, np.clip(buf, -1.0, 1.0))

    return {
        'move':          sfx_move(),
        'bump':          sfx_bump(),
        'break':         sfx_break(),
        'collect':       sfx_collect(),
        'credit':        sfx_credit(),
        'place_wall':    sfx_place_wall(),
        'shield_buy':    sfx_shield_buy(),
        'shield_expire': sfx_shield_expire(),
        'caught_shield': sfx_caught_shield(),
        'caught':        sfx_caught(),
        'level_up':      sfx_level_up(),
        'game_over':     sfx_game_over(),
        'boss_appear':   sfx_boss_appear(),
        'item_hit':      sfx_item_hit(),
        'entrance_open': sfx_entrance_open(),
    }


# ── Music ─────────────────────────────────────────────────────────────────────



def _kick(np, n: int, start_hz: float = 72.0, decay: float = 22.0, vol: float = 0.14):
    """Sine with exponential pitch + amplitude decay — bass drum."""
    t = np.arange(n, dtype=np.float32) / _RATE
    freq_env = start_hz * np.exp(-t * decay)
    phase = np.cumsum(2.0 * np.pi * freq_env / _RATE)
    return np.sin(phase) * np.exp(-t * 18.0) * vol


def _hihat(np, rng, n: int, vol: float = 0.055):
    """Exponentially decayed noise — closed hi-hat."""
    t = np.arange(n, dtype=np.float32) / _RATE
    noise = rng.standard_normal(n).astype(np.float32)
    return noise * np.exp(-t * 130.0) * vol


def _snare(np, rng, n: int, vol: float = 0.085):
    """White noise burst + brief 220 Hz tone — snare / side-stick."""
    t     = np.arange(n, dtype=np.float32) / _RATE
    noise = rng.standard_normal(n).astype(np.float32)
    tone  = np.sin(2.0 * np.pi * 220.0 * t) * 0.25
    return (noise + tone) * np.exp(-t * 60.0) * vol


def _strings(np, root_midi: int, scale: list, bar_n: int,
             vol_per_saw: float = 0.055, detune: float = 0.004):
    """Detuned sawtooth chord (root + 3rd + 5th), slow attack — ensemble strings."""
    buf = np.zeros(bar_n, dtype=np.float32)
    for deg in (0, 2, 4):
        f = _hz(root_midi + scale[deg])
        ev = _env(np, bar_n, 0.07, 0.09, 0.68, 0.12)
        buf += _saw(np, f * (1.0 + detune), bar_n, vol_per_saw) * ev
        buf += _saw(np, f * (1.0 - detune), bar_n, vol_per_saw) * ev
    return buf


# Level music configs: (bpm, list_of_8_bars)
# Each bar: (mel_root_midi, bas_root_midi, scale)
# mel_root: tonic for the harmony of this bar; bas_root: bass root (one octave lower);
# strings play at mel_root - 12.  The lead melody uses _LEVEL_THEMES instead.
_LEVEL_MUSIC_CFG = [
    # L1  A Dorian  i–IV–v–i  96 BPM  dark groove
    ( 96, [(69,45,_DOR),(62,50,_MAJ),(64,52,_MIN),(69,45,_DOR),
           (60,48,_MAJ),(64,52,_MIN),(67,55,_MIN),(69,45,_DOR)]),
    # L2  D Natural Minor  i–VII–VI–v  101 BPM  tense chase
    (101, [(74,50,_MIN),(72,48,_MAJ),(70,46,_MAJ),(67,55,_MIN),
           (69,57,_MIN),(71,59,_MIN),(72,48,_MAJ),(74,50,_MIN)]),
    # L3  G Phrygian  i–♭II–i–♭II  106 BPM  ominous
    (106, [(67,55,_PHR),(65,53,_MAJ),(67,55,_PHR),(65,53,_MAJ),
           (67,55,_PHR),(65,53,_MAJ),(67,55,_PHR),(65,53,_MAJ)]),
    # L4  A Harmonic Minor  i–iv–V–i  111 BPM  exotic danger
    (111, [(69,45,_HARM),(62,50,_MIN),(64,52,_MAJ),(69,45,_HARM),
           (65,53,_MAJ),(62,50,_MIN),(64,52,_MAJ),(69,45,_HARM)]),
    # L5  E Natural Minor  i–VII–VI–v  116 BPM  furious
    (116, [(64,52,_MIN),(62,50,_MAJ),(60,48,_MAJ),(59,47,_MIN),
           (57,45,_MIN),(62,50,_MAJ),(64,52,_MIN),(59,47,_MIN)]),
    # L6  B Phrygian  i–♭II–i–♭VII  120 BPM  very tense
    (120, [(71,59,_PHR),(72,48,_MAJ),(71,59,_PHR),(69,45,_MIN),
           (71,59,_PHR),(72,48,_MAJ),(71,59,_DIM),(69,45,_MIN)]),
    # L7  F# Natural Minor  i–iv–♭VII–i  125 BPM  dark pursuit
    (125, [(66,54,_MIN),(62,50,_MIN),(64,52,_MAJ),(66,54,_MIN),
           (66,54,_DIM),(64,52,_MIN),(62,50,_DIM),(66,54,_MIN)]),
    # L8  C# Diminished  descending dim  130 BPM  chaotic
    (130, [(61,49,_DIM),(64,52,_DIM),(67,55,_DIM),(61,49,_DIM),
           (64,52,_DIM),(67,55,_DIM),(61,49,_DIM),(64,52,_DIM)]),
    # L9  G# Phrygian  i–♭II–♭VII–i  135 BPM  terrifying
    (135, [(68,44,_PHR),(69,45,_MAJ),(67,55,_DIM),(68,44,_PHR),
           (68,44,_DIM),(69,45,_PHR),(67,55,_DIM),(68,44,_PHR)]),
    # L10  Chromatic Dim  all tritones  140 BPM  boss chaos
    (140, [(71,59,_DIM),(68,56,_DIM),(65,53,_DIM),(62,50,_DIM),
           (59,47,_DIM),(56,44,_DIM),(59,47,_DIM),(62,50,_DIM)]),
]


# Per-level composed melody themes: 8 bars × 8 eighth-note steps = 64 MIDI pitches.
# -1 = rest.  Pitches are absolute MIDI note numbers, played by the main lead voice.
_LEVEL_THEMES = [
    # L1  A Dorian — "The Wanderer": searching, rises and falls over the minor groove
    [69,72,76,74, 76,72,71,69,  74,78,81,79, 78,76,74,-1,  76,74,72,71, 69,67,66,64,  69,71,72,76, 74,72,71,69,
     79,76,72,74, 76,79,81,-1,  71,69,67,66, 67,69,71,72,  67,70,74,72, 70,67,69,-1,  69,-1,76,74, 72,71,69,64],
    # L2  D Natural Minor — "The Chase": driving descent, relentless forward motion
    [74,77,81,79, 77,76,74,72,  72,70,69,67, 69,70,72,74,  70,72,74,72, 70,69,67,65,  69,-1,67,69, 70,69,67,65,
     67,70,74,72, 70,67,69,70,  69,72,76,74, 72,70,69,-1,  72,74,76,74, 72,70,69,67,  74,72,70,69, 67,65,64,62],
    # L3  G Phrygian — "Shadow Step": the flat-2 half-step (G→Ab) dominates
    [67,68,70,67, 68,70,72,70,  68,67,65,63, 62,63,65,67,  79,77,75,74, 72,70,68,67,  68,70,72,70, 68,67,65,63,
     67,70,74,75, 74,72,70,68,  72,74,75,77, 79,77,75,74,  74,72,70,68, 67,68,70,72,  67,-1,68,67, 65,63,62,67],
    # L4  A Harmonic Minor — "Ancient Danger": the augmented 2nd (F→G#) gives exotic colour
    [69,76,80,81, 80,76,74,72,  74,72,71,69, 68,69,71,74,  76,80,81,80, 76,74,72,71,  69,-1,76,80, 81,80,76,69,
     77,76,74,72, 71,69,68,65,  74,71,68,69, 71,74,76,-1,  76,74,72,71, 69,68,69,76,  69,68,69,72, 76,74,72,69],
    # L5  E Natural Minor — "Pursuit": energetic, wide leaps, barely controlled
    [76,74,71,67, 69,71,74,76,  74,72,71,69, 71,72,74,-1,  72,71,69,67, 66,67,69,71,  71,-1,74,78, 76,74,71,-1,
     69,67,69,71, 72,74,76,78,  74,76,78,79, 78,76,74,72,  76,74,72,71, 69,67,66,64,  71,69,67,66, 64,-1,71,76],
    # L6  B Phrygian — "Edge of Darkness": tense stepwise motion, chromatic inflections
    [71,72,74,72, 71,69,67,66,  72,74,76,74, 72,71,72,-1,  71,69,67,66, 67,69,71,72,  69,67,66,64, 66,67,69,71,
     71,72,71,69, 67,66,67,69,  72,74,76,78, 79,78,76,74,  71,74,78,76, 74,72,71,-1,  69,-1,67,69, 71,69,67,71],
    # L7  F# Natural Minor — "Relentless": aggressive descent, angular leaps, no rest
    [78,76,74,73, 71,69,68,66,  71,69,68,66, 68,69,71,73,  73,74,76,74, 73,71,69,68,  66,-1,71,73, 74,73,71,-1,
     78,74,71,73, 74,76,78,-1,  76,73,69,71, 73,74,76,-1,  74,73,71,69, 68,69,71,73,  66,-1,73,71, 69,68,66,-1],
    # L8  C# Diminished — "Fragmentation": wide leaps, tritones, unstable but purposeful
    [73,76,79,-1, 78,76,75,73,  76,78,79,81, 82,81,79,78,  79,81,82,-1, 81,79,78,76,  73,-1,79,78, 76,75,73,-1,
     75,76,78,79, 81,82,81,79,  81,79,78,76, 75,73,75,76,  78,76,75,73, 75,78,79,81,  79,-1,78,76, 75,73,76,73],
    # L9  G# Phrygian — "Terror": unrelenting, descends from the top then rockets back up
    [80,81,80,78, 76,75,73,71,  81,80,78,76, 75,73,71,69,  71,73,75,76, 78,80,81,-1,  80,-1,81,80, 78,76,75,80,
     68,69,71,73, 75,76,78,80,  81,78,75,76, 78,80,81,-1,  78,76,75,73, 71,73,75,78,  80,-1,80,78, 76,75,73,68],
    # L10  Chromatic Dim — "Boss": tritone arpeggio — high on beat 1, low on beat 3, half-bar repeat
    # Each bar: mel_root+6 (upper) on steps 0&4, mel_root (lower) on steps 2&6, silence elsewhere.
    # Roots descend B→Ab→F→D→B→Ab then rise back: tracks the dim7 harmonic descent.
    [77,-1,71,-1, 77,-1,71,-1,  74,-1,68,-1, 74,-1,68,-1,  71,-1,65,-1, 71,-1,65,-1,  68,-1,62,-1, 68,-1,62,-1,
     65,-1,59,-1, 65,-1,59,-1,  62,-1,56,-1, 62,-1,56,-1,  65,-1,59,-1, 65,-1,59,-1,  68,-1,62,-1, 68,-1,62,-1],
]


def _make_music_track(np, level: int) -> pygame.Sound:
    """5-voice level music: strings + bass + brass accent + lead + percussion."""
    bpm, bars = _LEVEL_MUSIC_CFG[level - 1]
    eighth_s  = 30.0 / bpm
    eighth_n  = round(eighth_s * _RATE)
    beat_n    = 2 * eighth_n

    buf   = np.zeros(len(bars) * 8 * eighth_n, dtype=np.float32)
    rng   = np.random.default_rng(level * 13)
    theme = _LEVEL_THEMES[level - 1]
    # March accent: beats 1&3 (steps 0,4) strong; beats 2&4 (steps 2,6) medium; off-beats soft
    acc   = [1.00, 0.65, 0.80, 0.65, 1.00, 0.65, 0.80, 0.65]

    for bar_idx, (mel_root, bas_root, scale) in enumerate(bars):
        bar0  = bar_idx * 8 * eighth_n
        bar_n = 8 * eighth_n

        # Strings: detuned sawtooth chord one octave below melody
        str_root = mel_root - 12
        buf[bar0:bar0+bar_n] += _strings(np, str_root, scale, bar_n)

        # Bass: triangle, root on beats 0&2, fifth on 1&3
        bas_fifth = bas_root + scale[4]
        for beat in range(4):
            freq = _hz(bas_fifth if beat % 2 else bas_root)
            pos  = bar0 + beat * beat_n
            buf[pos:pos+beat_n] += (
                _tri(np, freq, beat_n, 0.17)
                * _env(np, beat_n, 0.008, 0.05, 0.55, 0.08)
            )

        # Brass accent: square stab on bar downbeat (beat 0)
        brass_n = beat_n
        buf[bar0:bar0+brass_n] += (
            _sq(np, _hz(bas_root - 12), brass_n, 0.14)
            * _env(np, brass_n, 0.005, 0.07, 0.28, 0.12)
        )

        # Lead: staccato melody with march accent dynamics
        for step in range(8):
            midi = theme[bar_idx * 8 + step]
            if midi < 0:
                continue
            pos    = bar0 + step * eighth_n
            n_stac = round(eighth_n * 0.55)
            freq   = _hz(midi)
            ev     = _env(np, n_stac, 0.003, 0.012, 0.30, 0.012)
            wave   = _fm(np, freq, 1.0, 4.0, n_stac)
            buf[pos:pos+n_stac] += np.tanh(wave * ev * 2.8) * 0.13 * acc[step]

        # Second lead: quarter-note staccato hits, one octave below, brighter FM
        freq2 = _hz(mel_root - 12 + scale[0])
        for beat in range(4):
            pos2  = bar0 + beat * beat_n
            n_e2  = round(beat_n * 0.50)
            ev2   = _env(np, n_e2, 0.005, 0.018, 0.28, 0.012)
            wave2 = _fm(np, freq2, 2.0, 3.5, n_e2)
            buf[pos2:pos2+n_e2] += np.tanh(wave2 * ev2 * 2.4) * 0.10

        # Kick on beats 0 and 2
        for beat in (0, 2):
            kn  = min(round(_RATE * 0.09), beat_n)
            pos = bar0 + beat * beat_n
            buf[pos:pos+kn] += _kick(np, kn)

        # Snare on beats 1 and 3 (backbeat)
        for beat in (1, 3):
            sn  = min(round(_RATE * 0.045), beat_n)
            pos = bar0 + beat * beat_n
            buf[pos:pos+sn] += _snare(np, rng, sn)

        # Hi-hat on off-eighth positions ("and" of every beat)
        for step in (1, 3, 5, 7):
            hn  = min(round(_RATE * 0.012), eighth_n)
            pos = bar0 + step * eighth_n
            buf[pos:pos+hn] += _hihat(np, rng, hn, vol=0.040)

    return _to_sound(np, buf)


# ── Title screen music ────────────────────────────────────────────────────────

# D-minor melody at 8th-note resolution (4 bars × 8 steps).  -1 = rest.
# A stepwise descent with upward lifts — dark, epic, memorable.
_TITLE_MELODY = [
    74, 72, 70, 69,  67, 65, 67, 69,   # Bar 1 (Dm): D5 C5 Bb4 A4  G4 F4 G4 A4
    70, 69, 67, 65,  64, 62, -1, -1,   # Bar 2  (F): Bb4 A4 G4 F4  E4 D4  _  _
    67, 69, 70, 72,  70, 69, 67, 65,   # Bar 3 (Gm): G4 A4 Bb4 C5  Bb4 A4 G4 F4
    69, -1, 74, 72,  69, -1, 74, -1,   # Bar 4  (A): A4  _  D5 C5  A4  _  D5  _
]

# Chord per bar: (chord_root, scale) — strings + bass built from these
_TITLE_CHORDS = [
    (62, _MIN),   # Dm
    (65, _MAJ),   # F
    (67, _MIN),   # Gm
    (69, _MAJ),   # A major — V of Dm, very dramatic cadence
]


def _make_title_music(np) -> pygame.Sound:
    """Epic D-minor fanfare for the title screen.

    Richer orchestration than level music: thick strings in two octaves,
    low brass pedal, prominent pulse lead, soft timpani on downbeats.
    BPM 80 — stately and slow compared to the frantic level tracks.
    """
    bpm      = 80
    eighth_s = 30.0 / bpm
    eighth_n = round(eighth_s * _RATE)
    beat_n   = 2 * eighth_n
    bar_n    = 8 * eighth_n
    total_n  = 4 * bar_n
    buf      = np.zeros(total_n, dtype=np.float32)

    rng = np.random.default_rng(777)

    for bar_idx, (chord_root, chord_scale) in enumerate(_TITLE_CHORDS):
        bar0 = bar_idx * bar_n

        # Upper strings (chord root octave — between bass and melody)
        buf[bar0:bar0+bar_n] += _strings(np, chord_root, chord_scale, bar_n,
                                         vol_per_saw=0.06, detune=0.004)
        # Lower strings (one octave below — very dark undertone)
        buf[bar0:bar0+bar_n] += _strings(np, chord_root - 12, chord_scale, bar_n,
                                         vol_per_saw=0.04, detune=0.003)

        # Bass: slow, powerful — two half-note roots per bar
        bas_root  = chord_root - 12
        bas_fifth = bas_root + chord_scale[4]
        for beat in range(4):
            freq = _hz(bas_fifth if beat % 2 else bas_root)
            pos  = bar0 + beat * beat_n
            buf[pos:pos+beat_n] += (
                _tri(np, freq, beat_n, 0.19)
                * _env(np, beat_n, 0.015, 0.08, 0.60, 0.12)
            )

        # Brass pedal: low square stab on bar downbeat, fades over 2 beats
        brass_n = 2 * beat_n
        buf[bar0:bar0+brass_n] += (
            _sq(np, _hz(chord_root - 24), brass_n, 0.13)
            * _env(np, brass_n, 0.008, 0.10, 0.40, 0.18)
        )

        # Timpani hit on bars 1 and 3 (bar_idx 0 and 2) — sine + noise burst
        if bar_idx in (0, 2):
            tn = min(round(_RATE * 0.18), bar_n)
            t_t = np.arange(tn, dtype=np.float32) / _RATE
            timp_freq = _hz(chord_root - 12) * 0.75  # slightly detuned, unpitched feel
            ph = np.cumsum(np.full(tn, 2.0 * np.pi * timp_freq / _RATE, dtype=np.float32))
            noise_t = rng.standard_normal(tn).astype(np.float32) * 0.4
            amp = np.exp(-t_t * 11.0)
            buf[bar0:bar0+tn] += (np.sin(ph) * 0.6 + noise_t) * amp * 0.10

    # Lead melody: pulse wave, prominent, with one upper harmonic for brightness
    for step, midi in enumerate(_TITLE_MELODY):
        if midi < 0:
            continue
        pos  = step * eighth_n
        freq = _hz(midi)
        n    = eighth_n
        ev   = _env(np, n, 0.005, 0.020, 0.52, 0.030)
        buf[pos:pos+n] += _pulse(np, freq, n, 0.20, 0.20) * ev
        buf[pos:pos+n] += _pulse(np, freq * 2.0, n, 0.12, 0.06) * ev

    return _to_sound(np, buf)


# ── Win / end-game music ──────────────────────────────────────────────────────

# C-major melody at 8th-note resolution (4 bars × 8 steps).  -1 = rest.
# Opens with a rising C major arpeggio (classic fanfare gesture), descends
# warmly through Am and F, climbs back for a satisfying G→C resolution.
_WIN_MELODY = [
    67, 72, 76, 79,  79, 76, 74, 72,   # Bar 1  (C): G4 C5 E5 G5  G5 E5 D5 C5
    76, 69, 72, 76,  74, 72, 71, 69,   # Bar 2 (Am): E5 A4 C5 E5  D5 C5 B4 A4
    65, 69, 72, 77,  76, 74, 72, 74,   # Bar 3  (F): F4 A4 C5 F5  E5 D5 C5 D5
    67, 74, 79, 74,  79, 76, 72, -1,   # Bar 4  (G): G4 D5 G5 D5  G5 E5 C5  _
]

_WIN_CHORDS = [
    (60, _MAJ),   # C major
    (57, _MIN),   # A minor — relative minor, warmth without drama
    (65, _MAJ),   # F major
    (67, _MAJ),   # G major — V of C, strong cadential lift
]


def _make_win_music(np) -> pygame.Sound:
    """Joyful C-major fanfare for the win screen.

    Same instrumentation as the title theme (thick strings, bass, brass,
    timpani, pulse lead). BPM 108 — lively and celebratory, not pompous.
    """
    bpm      = 108
    eighth_s = 30.0 / bpm
    eighth_n = round(eighth_s * _RATE)
    beat_n   = 2 * eighth_n
    bar_n    = 8 * eighth_n
    total_n  = 4 * bar_n
    buf      = np.zeros(total_n, dtype=np.float32)

    rng = np.random.default_rng(888)

    for bar_idx, (chord_root, chord_scale) in enumerate(_WIN_CHORDS):
        bar0 = bar_idx * bar_n

        # Upper strings
        buf[bar0:bar0+bar_n] += _strings(np, chord_root, chord_scale, bar_n,
                                         vol_per_saw=0.06, detune=0.004)
        # Lower strings — one octave below for body
        buf[bar0:bar0+bar_n] += _strings(np, chord_root - 12, chord_scale, bar_n,
                                         vol_per_saw=0.04, detune=0.003)

        # Bass: root on beats 1&3, fifth on 2&4
        bas_root  = chord_root - 12
        bas_fifth = bas_root + chord_scale[4]
        for beat in range(4):
            freq = _hz(bas_fifth if beat % 2 else bas_root)
            pos  = bar0 + beat * beat_n
            buf[pos:pos+beat_n] += (
                _tri(np, freq, beat_n, 0.19)
                * _env(np, beat_n, 0.015, 0.08, 0.60, 0.12)
            )

        # Brass pedal on bar downbeat, fades over 2 beats
        brass_n = 2 * beat_n
        buf[bar0:bar0+brass_n] += (
            _sq(np, _hz(chord_root - 24), brass_n, 0.13)
            * _env(np, brass_n, 0.008, 0.10, 0.40, 0.18)
        )

        # Timpani on bars 1 and 3
        if bar_idx in (0, 2):
            tn    = min(round(_RATE * 0.18), bar_n)
            t_t   = np.arange(tn, dtype=np.float32) / _RATE
            t_frq = _hz(chord_root - 12) * 0.75
            ph    = np.cumsum(np.full(tn, 2.0*np.pi*t_frq/_RATE, dtype=np.float32))
            nz    = rng.standard_normal(tn).astype(np.float32) * 0.4
            buf[bar0:bar0+tn] += (np.sin(ph)*0.6 + nz) * np.exp(-t_t*11.0) * 0.10

    # Lead melody: pulse wave with upper harmonic
    for step, midi in enumerate(_WIN_MELODY):
        if midi < 0:
            continue
        pos  = step * eighth_n
        freq = _hz(midi)
        n    = eighth_n
        ev   = _env(np, n, 0.005, 0.020, 0.52, 0.030)
        buf[pos:pos+n] += _pulse(np, freq, n, 0.20, 0.20) * ev
        buf[pos:pos+n] += _pulse(np, freq * 2.0, n, 0.12, 0.06) * ev

    return _to_sound(np, buf)


# ── SoundManager ──────────────────────────────────────────────────────────────

class SoundManager:
    """Owns all audio resources and manages music/SFX playback.

    Fails silently if numpy or the pygame mixer is unavailable.
    Music key: 'title' for the title screen, int 1–10 for levels.
    """

    def __init__(self):
        self._ok       = False
        self._sfx: dict = {}
        self._music: dict = {}
        self._music_ch: pygame.mixer.Channel | None = None
        self._current_key = None

        np = _import_numpy()
        if np is None:
            return

        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=_RATE, size=-16, channels=2, buffer=512)
            except pygame.error:
                return

        try:
            pygame.mixer.set_num_channels(16)
            self._music_ch = pygame.mixer.Channel(0)
            self._sfx  = _build_sfx(np)
            self._music = {'title': _make_title_music(np), 'win': _make_win_music(np)}
            self._music.update({lvl: _make_music_track(np, lvl) for lvl in range(1, 11)})
            self._ok = True
        except Exception:
            self._sfx  = {}
            self._music = {}
            self._music_ch = None

    def play(self, name: str) -> None:
        snd = self._sfx.get(name)
        if snd is not None:
            snd.play()

    def start_music(self, key) -> None:
        """key: 'title', 'win', or int level number."""
        if not self._ok or self._music_ch is None:
            return
        if self._current_key == key:
            return
        self._current_key = key
        # Act 2 levels reuse Act 1 music tracks cyclically
        lookup = key
        if isinstance(key, int) and key > 10:
            lookup = ((key - 11) % 10) + 1
        snd = self._music.get(lookup)
        if snd is not None:
            self._music_ch.stop()
            self._music_ch.play(snd, loops=-1)

    def stop_music(self) -> None:
        if self._music_ch is not None:
            self._music_ch.stop()
        self._current_key = None

    def pause_music(self) -> None:
        if self._music_ch is not None:
            self._music_ch.pause()

    def unpause_music(self) -> None:
        if self._music_ch is not None:
            self._music_ch.unpause()
