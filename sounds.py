"""sounds.py — Procedural sound effects and background music for UGLYCRAFT.

All audio generated algorithmically — no audio files required.
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


# ── Scales (semitone offsets from root) ──────────────────────────────────────

_MAJ = [0, 2, 4, 5, 7, 9, 11, 12]
_MIN = [0, 2, 3, 5, 7, 8, 10, 12]
_PHR = [0, 1, 3, 5, 7, 8, 10, 12]
_DIM = [0, 2, 3, 5, 6, 8,  9, 11]

# ── Waveform helpers (require numpy, called only after np is confirmed) ───────

def _hz(midi: float) -> float:
    return 440.0 * 2.0 ** ((midi - 69.0) / 12.0)

def _sq(np, freq: float, n: int, vol: float = 1.0):
    t = np.arange(n, dtype=np.float32) / _RATE
    return np.sign(np.sin(2.0 * np.pi * freq * t)) * vol

def _tri(np, freq: float, n: int, vol: float = 1.0):
    t = np.arange(n, dtype=np.float32) / _RATE
    p = (t * freq) % 1.0
    return (2.0 * np.abs(2.0 * p - 1.0) - 1.0) * vol

def _sin(np, freq: float, n: int, vol: float = 1.0):
    t = np.arange(n, dtype=np.float32) / _RATE
    return np.sin(2.0 * np.pi * freq * t) * vol

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
    }


# ── Music ─────────────────────────────────────────────────────────────────────

# Arpeggio patterns: scale degree indices (0–4 keep notes within a fifth); -1 = rest.
_ARP_A = [ 0, 2, 4, 2,  0, 2, 4, 2]   # gentle ascending-descending
_ARP_B = [ 0, 4, 2,-1,  4, 2, 4, 0]   # bouncy with rest
_ARP_C = [ 0, 2, 4, 4,  2, 4, 2, 0]   # fifth emphasis
_ARP_D = [ 0, 4, 2, 4,  2, 4, 4, 0]   # persistent push
_ARP_E = [ 0, 2, 3, 2,  4, 3, 2, 0]   # minor colour (degree 3 = minor/dim 3rd)
_ARP_F = [ 0, 4, 3, 4,  0, 3, 4,-1]   # tense, rest on last step

# Level music configs: (bpm, list_of_4_bars)
# Each bar: (mel_root_midi, bas_root_midi, scale, arp_pattern)
_LEVEL_MUSIC_CFG = [
    # L1  C major  I–V–vi–IV  90 BPM  cheerful
    (90,  [(72,48,_MAJ,_ARP_A),(79,55,_MAJ,_ARP_A),(69,57,_MIN,_ARP_A),(65,53,_MAJ,_ARP_A)]),
    # L2  G major  I–IV–V–I  100 BPM  lively
    (100, [(79,55,_MAJ,_ARP_A),(72,48,_MAJ,_ARP_B),(74,50,_MAJ,_ARP_A),(79,55,_MAJ,_ARP_B)]),
    # L3  D major  I–V–IV–V  110 BPM  energetic
    (110, [(74,50,_MAJ,_ARP_B),(69,57,_MAJ,_ARP_B),(67,55,_MAJ,_ARP_B),(69,57,_MAJ,_ARP_B)]),
    # L4  A major  I–IV–V–I  120 BPM  adventurous
    (120, [(69,57,_MAJ,_ARP_C),(62,50,_MAJ,_ARP_C),(64,52,_MAJ,_ARP_C),(69,57,_MAJ,_ARP_C)]),
    # L5  E major  I–IV–I–V  130 BPM  driving
    (130, [(64,52,_MAJ,_ARP_C),(69,57,_MAJ,_ARP_C),(64,52,_MAJ,_ARP_D),(71,59,_MAJ,_ARP_C)]),
    # L6  A minor  i–VII–VI–VII  140 BPM  tense
    (140, [(69,57,_MIN,_ARP_D),(67,55,_MAJ,_ARP_D),(65,53,_MAJ,_ARP_D),(67,55,_MAJ,_ARP_D)]),
    # L7  D minor  i–iv–VII–i  150 BPM  urgent
    (150, [(62,50,_MIN,_ARP_D),(67,55,_MIN,_ARP_E),(60,48,_MAJ,_ARP_E),(62,50,_MIN,_ARP_D)]),
    # L8  G minor  i–III–VII–i  160 BPM  dark
    (160, [(67,55,_MIN,_ARP_E),(70,58,_MAJ,_ARP_E),(65,53,_MAJ,_ARP_F),(67,55,_MIN,_ARP_F)]),
    # L9  E Phrygian  i–♭II–i–♭II  170 BPM  ominous
    (170, [(64,52,_PHR,_ARP_E),(65,53,_MAJ,_ARP_F),(64,52,_PHR,_ARP_F),(65,53,_MAJ,_ARP_F)]),
    # L10  Diminished  descending  180 BPM  terrifying
    (180, [(71,59,_DIM,_ARP_F),(68,56,_DIM,_ARP_F),(65,53,_DIM,_ARP_F),(62,50,_DIM,_ARP_F)]),
]


def _make_music_track(np, level: int) -> pygame.Sound:
    bpm, bars = _LEVEL_MUSIC_CFG[level - 1]
    eighth_s = 30.0 / bpm
    eighth_n = round(eighth_s * _RATE)
    beat_n   = 2 * eighth_n

    buf = np.zeros(len(bars) * 8 * eighth_n, dtype=np.float32)

    for bar_idx, (mel_root, bas_root, scale, arp) in enumerate(bars):
        bar0 = bar_idx * 8 * eighth_n

        # Bass: quarter notes, root on beats 0&2, fifth on beats 1&3
        bas_fifth = bas_root + scale[4]
        for beat in range(4):
            freq = _hz(bas_fifth if beat % 2 else bas_root)
            pos = bar0 + beat * beat_n
            buf[pos:pos+beat_n] += (
                _tri(np, freq, beat_n, 0.18)
                * _env(np, beat_n, 0.01, 0.06, 0.55, 0.08)
            )

        # Melody: arpeggio in 8th notes
        for step, deg in enumerate(arp):
            if deg < 0:
                continue
            freq = _hz(mel_root + scale[deg])
            pos = bar0 + step * eighth_n
            buf[pos:pos+eighth_n] += (
                _sq(np, freq, eighth_n, 0.13)
                * _env(np, eighth_n, 0.003, 0.015, 0.40, 0.025)
            )

    return _to_sound(np, buf)


# ── SoundManager ──────────────────────────────────────────────────────────────

class SoundManager:
    """Owns all audio resources and manages music/SFX playback.

    Fails silently if numpy or the pygame mixer is unavailable.
    """

    def __init__(self):
        self._ok = False
        self._sfx: dict = {}
        self._music: dict = {}
        self._music_ch: pygame.mixer.Channel | None = None
        self._current_level: int | None = None

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
            self._sfx = _build_sfx(np)
            self._music = {lvl: _make_music_track(np, lvl) for lvl in range(1, 11)}
            self._ok = True
        except Exception:
            self._sfx = {}
            self._music = {}
            self._music_ch = None

    def play(self, name: str) -> None:
        snd = self._sfx.get(name)
        if snd is not None:
            snd.play()

    def start_music(self, level: int) -> None:
        if not self._ok or self._music_ch is None:
            return
        if self._current_level == level:
            return
        self._current_level = level
        snd = self._music.get(level)
        if snd is not None:
            self._music_ch.stop()
            self._music_ch.play(snd, loops=-1)

    def stop_music(self) -> None:
        if self._music_ch is not None:
            self._music_ch.stop()
        self._current_level = None

    def pause_music(self) -> None:
        if self._music_ch is not None:
            self._music_ch.pause()

    def unpause_music(self) -> None:
        if self._music_ch is not None:
            self._music_ch.unpause()
