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


# ── Sound effects ─────────────────────────────────────────────────────────────

def _build_sfx(np) -> dict:
    def sfx_move():
        n = round(_RATE * 0.025)
        return _to_sound(np, _sq(np, 880, n, 0.08) * _env(np, n, 0.001, 0.004, 0.0, 0.02))

    def sfx_bump():
        n = round(_RATE * 0.10)
        tone = _tri(np, 110, n, 0.22)
        rng = np.random.default_rng(1)
        noise = rng.standard_normal(n).astype(np.float32) * 0.10
        return _to_sound(np, (tone + noise) * _env(np, n, 0.003, 0.02, 0.30, 0.06))

    def sfx_break():
        n = round(_RATE * 0.22)
        rng = np.random.default_rng(2)
        noise = rng.standard_normal(n).astype(np.float32) * 0.38
        tone = _tri(np, 60, n, 0.28)
        return _to_sound(np, np.clip(noise + tone, -1.0, 1.0) * _env(np, n, 0.003, 0.04, 0.25, 0.14))

    def sfx_collect():
        notes = [72, 76, 79, 84]
        nd = round(_RATE * 0.055)
        buf = np.zeros(nd * len(notes), dtype=np.float32)
        for i, m in enumerate(notes):
            buf[i*nd:(i+1)*nd] = _sq(np, _hz(m), nd, 0.20) * _env(np, nd, 0.002, 0.01, 0.5, 0.025)
        return _to_sound(np, buf)

    def sfx_credit():
        n = round(_RATE * 0.18)
        nd = n // 2
        buf = np.zeros(n, dtype=np.float32)
        buf[:nd] = _sin(np, _hz(76), nd, 0.28) * _env(np, nd, 0.002, 0.02, 0.6, 0.08)
        buf[nd:] = _sin(np, _hz(81), nd, 0.28) * _env(np, nd, 0.002, 0.02, 0.6, 0.08)
        return _to_sound(np, buf)

    def sfx_place_wall():
        n = round(_RATE * 0.09)
        return _to_sound(np, _sq(np, 220, n, 0.22) * _env(np, n, 0.005, 0.012, 0.4, 0.06))

    def sfx_shield_buy():
        n = round(_RATE * 0.28)
        t = np.arange(n, dtype=np.float32) / _RATE
        freq = 350.0 + 800.0 * (t / t[-1])
        phase = np.cumsum(2.0 * np.pi * freq / _RATE)
        wave = np.sign(np.sin(phase)) * 0.20
        return _to_sound(np, wave * _env(np, n, 0.01, 0.02, 0.7, 0.08))

    def sfx_shield_expire():
        n = round(_RATE * 0.22)
        t = np.arange(n, dtype=np.float32) / _RATE
        freq = 850.0 - 400.0 * (t / t[-1])
        phase = np.cumsum(2.0 * np.pi * freq / _RATE)
        wave = np.sin(phase) * 0.20
        return _to_sound(np, wave * _env(np, n, 0.005, 0.01, 0.6, 0.12))

    def sfx_caught_shield():
        n = round(_RATE * 0.22)
        rng = np.random.default_rng(3)
        noise = rng.standard_normal(n).astype(np.float32) * 0.25
        tone = _sin(np, _hz(64), n, 0.22)
        return _to_sound(np, (noise + tone) * _env(np, n, 0.002, 0.03, 0.35, 0.12))

    def sfx_caught():
        midi_seq = [72, 69, 66, 63, 60, 57]
        nd = round(_RATE * 0.09)
        buf = np.zeros(nd * len(midi_seq), dtype=np.float32)
        for i, m in enumerate(midi_seq):
            buf[i*nd:(i+1)*nd] = (
                _sq(np, _hz(m), nd, 0.16) * _env(np, nd, 0.002, 0.01, 0.55, 0.04)
              + _tri(np, _hz(m - 12), nd, 0.12) * _env(np, nd, 0.002, 0.01, 0.45, 0.04)
            )
        return _to_sound(np, buf)

    def sfx_level_up():
        midi_seq = [60, 64, 67, 72, 76, 79, 84]
        nd = round(_RATE * 0.08)
        buf = np.zeros(nd * len(midi_seq), dtype=np.float32)
        for i, m in enumerate(midi_seq):
            buf[i*nd:(i+1)*nd] = (
                _sq(np, _hz(m), nd, 0.20) * _env(np, nd, 0.003, 0.01, 0.55, 0.04)
              + _tri(np, _hz(m - 12), nd, 0.13) * _env(np, nd, 0.003, 0.01, 0.45, 0.04)
            )
        return _to_sound(np, buf)

    def sfx_game_over():
        midi_seq = [60, 59, 57, 55, 53, 52, 48]
        nd = round(_RATE * 0.13)
        buf = np.zeros(nd * len(midi_seq), dtype=np.float32)
        for i, m in enumerate(midi_seq):
            buf[i*nd:(i+1)*nd] = (
                _sq(np, _hz(m), nd, 0.18) * _env(np, nd, 0.003, 0.02, 0.50, 0.07)
              + _tri(np, _hz(m - 12), nd, 0.13) * _env(np, nd, 0.003, 0.02, 0.45, 0.07)
            )
        return _to_sound(np, buf)

    def sfx_boss_appear():
        n = round(_RATE * 0.35)
        drone = _sq(np, _hz(35), n, 0.18) * _env(np, n, 0.01, 0.06, 0.65, 0.15)
        n2 = round(_RATE * 0.08)
        stab = np.zeros(n, dtype=np.float32)
        stab[:n2] = _sq(np, _hz(84), n2, 0.28) * _env(np, n2, 0.001, 0.012, 0.0, 0.06)
        return _to_sound(np, np.clip(drone + stab, -1.0, 1.0))

    def sfx_item_hit():
        # Enemy displaced a treasure — soft two-tone ping
        n = round(_RATE * 0.14)
        hi = _sin(np, _hz(79), n, 0.16) * _env(np, n, 0.001, 0.025, 0.0, 0.025)
        lo = _tri(np, _hz(67), n, 0.13) * _env(np, n, 0.002, 0.04, 0.15, 0.07)
        return _to_sound(np, hi + lo)

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
    }


# ── Music ─────────────────────────────────────────────────────────────────────

# Arpeggio patterns (scale degree indices 0–6; -1 = rest).
# Range extended to degree 6 (flat 7th in minor, tritone in diminished).
_ARP_D1 = [ 0, 3, 5, 3,  0, 5, 3, 5]   # minor 3rd + 5th pulse
_ARP_D2 = [ 0, 5, 3, 5,  0, 4, 5, 0]   # 5th emphasis, angular
_ARP_D3 = [ 5, 3, 0, 3,  5, 6, 5, 3]   # descending with flat-7
_ARP_D4 = [ 0, 3, 5, 6,  5, 3, 6, 0]   # flat-7 tension loop
_ARP_D5 = [ 0, 4, 5, 6,  5, 4, 5, 0]   # very active, dissonant
_ARP_D6 = [ 0, 6, 3, 6,  4, 6, 3,-1]   # tritone / diminished shapes


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


# Level music configs: (bpm, list_of_4_bars)
# Each bar: (mel_root_midi, bas_root_midi, scale, arp_pattern)
# mel_root: lead melody start note; bas_root: bass root (one octave below mel area);
# strings play at bas_root + 12 (between bass and melody).
_LEVEL_MUSIC_CFG = [
    # L1  A Dorian  i–IV–v–i  100 BPM  dark groove
    (100, [(69,45,_DOR,_ARP_D1),(62,50,_MAJ,_ARP_D2),(64,52,_MIN,_ARP_D1),(69,45,_DOR,_ARP_D3)]),
    # L2  D Natural Minor  i–VII–VI–v  110 BPM  tense chase
    (110, [(74,50,_MIN,_ARP_D2),(72,48,_MAJ,_ARP_D1),(70,46,_MAJ,_ARP_D2),(67,55,_MIN,_ARP_D3)]),
    # L3  G Phrygian  i–♭II–i–♭II  120 BPM  ominous
    (120, [(67,55,_PHR,_ARP_D1),(65,53,_MAJ,_ARP_D3),(67,55,_PHR,_ARP_D2),(65,53,_MAJ,_ARP_D4)]),
    # L4  A Harmonic Minor  i–iv–V–i  130 BPM  exotic danger
    (130, [(69,45,_HARM,_ARP_D3),(62,50,_MIN,_ARP_D2),(64,52,_MAJ,_ARP_D4),(69,45,_HARM,_ARP_D3)]),
    # L5  E Natural Minor  i–VII–VI–v  140 BPM  furious
    (140, [(64,52,_MIN,_ARP_D4),(62,50,_MAJ,_ARP_D3),(60,48,_MAJ,_ARP_D4),(59,47,_MIN,_ARP_D5)]),
    # L6  B Phrygian  i–♭II–i–♭VII  150 BPM  very tense
    (150, [(71,59,_PHR,_ARP_D4),(72,48,_MAJ,_ARP_D5),(71,59,_PHR,_ARP_D4),(69,45,_MIN,_ARP_D5)]),
    # L7  F# Natural Minor  i–iv–♭VII–i  158 BPM  dark pursuit
    (158, [(66,54,_MIN,_ARP_D5),(62,50,_MIN,_ARP_D4),(64,52,_MAJ,_ARP_D5),(66,54,_MIN,_ARP_D6)]),
    # L8  C# Diminished  descending dim  165 BPM  chaotic
    (165, [(61,49,_DIM,_ARP_D5),(64,52,_DIM,_ARP_D6),(67,55,_DIM,_ARP_D5),(61,49,_DIM,_ARP_D6)]),
    # L9  G# Phrygian  i–♭II–♭VII–i  172 BPM  terrifying
    (172, [(68,44,_PHR,_ARP_D6),(69,45,_MAJ,_ARP_D5),(67,55,_DIM,_ARP_D6),(68,44,_PHR,_ARP_D6)]),
    # L10  Chromatic Dim  all tritones  182 BPM  boss chaos
    (182, [(71,59,_DIM,_ARP_D6),(68,56,_DIM,_ARP_D6),(65,53,_DIM,_ARP_D6),(62,50,_DIM,_ARP_D6)]),
]


def _make_music_track(np, level: int) -> pygame.Sound:
    """5-voice level music: strings + bass + brass accent + lead + percussion."""
    bpm, bars = _LEVEL_MUSIC_CFG[level - 1]
    eighth_s  = 30.0 / bpm
    eighth_n  = round(eighth_s * _RATE)
    beat_n    = 2 * eighth_n

    buf = np.zeros(len(bars) * 8 * eighth_n, dtype=np.float32)
    rng = np.random.default_rng(level * 13)

    for bar_idx, (mel_root, bas_root, scale, arp) in enumerate(bars):
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

        # Lead: pulse-wave arpeggio
        for step, deg in enumerate(arp):
            if deg < 0:
                continue
            pos = bar0 + step * eighth_n
            buf[pos:pos+eighth_n] += (
                _pulse(np, _hz(mel_root + scale[deg]), eighth_n, 0.25, 0.14)
                * _env(np, eighth_n, 0.003, 0.015, 0.40, 0.025)
            )

        # Kick on beats 0 and 2
        for beat in (0, 2):
            kn  = min(round(_RATE * 0.09), beat_n)
            pos = bar0 + beat * beat_n
            buf[pos:pos+kn] += _kick(np, kn)

        # Hi-hat on off-beats (beats 1 and 3)
        for beat in (1, 3):
            hn  = min(round(_RATE * 0.016), eighth_n)
            pos = bar0 + beat * beat_n
            buf[pos:pos+hn] += _hihat(np, rng, hn)

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
            self._music = {'title': _make_title_music(np)}
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
        """key: 'title' or int 1–10."""
        if not self._ok or self._music_ch is None:
            return
        if self._current_key == key:
            return
        self._current_key = key
        snd = self._music.get(key)
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
