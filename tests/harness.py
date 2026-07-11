"""Headless characterization harness for gameplay logic (spec 0044).

Drives a real Game instance without a display: synthesized key events in,
per-tick state snapshots + sound-trigger log out.  Golden traces live in
tests/golden/ and are re-recorded only via UGLYCRAFT_REGOLD=1.
"""
import hashlib
import json
import os
import random

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame

if not pygame.get_init():
    pygame.init()

import levels
import world as world_mod
from constants import LOGICAL_W, LOGICAL_H
from game import Game, PLAYING

DT = 33            # ms per tick (~30 FPS)
CLOCK_START = 1000  # arbitrary nonzero epoch for game.now()

GOLDEN_DIR = os.path.join(os.path.dirname(__file__), 'golden')
REGOLD = bool(os.environ.get('UGLYCRAFT_REGOLD'))

KEY_MAP = {
    'left':   pygame.K_LEFT,
    'right':  pygame.K_RIGHT,
    'up':     pygame.K_UP,
    'down':   pygame.K_DOWN,
    'return': pygame.K_RETURN,
    'space':  pygame.K_SPACE,
    'tab':    pygame.K_TAB,
    'escape': pygame.K_ESCAPE,
    'p':      pygame.K_p,
    'y':      pygame.K_y,
    'n':      pygame.K_n,
    'f10':    pygame.K_F10,
}


class Harness:
    """A pinned, headless Game plus its recorded trace."""

    def __init__(self, level=1, difficulty='easy', seed=1234, level_dict=None):
        self._orig_get_level = None
        self._orig_regenerate = None
        random.seed(seed)
        self.game = Game(pygame.Surface((LOGICAL_W, LOGICAL_H)))
        self.game._debug = True          # never touch the real hiscore file
        self.game.difficulty = difficulty
        self._clock = CLOCK_START
        self.game.now = lambda: self._clock
        self.trace = {
            'meta': {'level': level, 'difficulty': difficulty,
                     'seed': seed, 'dt': DT,
                     'fixture': level_dict is not None},
            'sounds': [],   # [tick, key]
            'music':  [],   # [tick, action, key]
            # [state, level, score, lives, pcol, prow, room,
            #  [[ecol, erow], ...], treasure_pos]
            'ticks':  [],
        }
        self._tick = 0
        self._spy_sounds()
        if level_dict is not None:
            self._patch_levels(level_dict)
        self.game._full_reset()
        levels.set_game_seed(seed)       # after _full_reset (which reseeds)
        if level != 1:
            self.game._start_level(level)
        # Multiroom fixtures served as level 1 skip _spawn_treasure, which
        # normally initialises treasure_item_no on the way through Act 1;
        # _render_hud reads it unconditionally.  Production can't hit this
        # (level 1 is always single-room); give the fixture path a default.
        if not hasattr(self.game.world, 'treasure_item_no'):
            self.game.world.treasure_item_no = 0
        self.game.state = PLAYING

    # ── plumbing ──────────────────────────────────────────────────────────────

    def _spy_sounds(self):
        s = self.game.sounds
        s.play = lambda key: self.trace['sounds'].append([self._tick, key])
        s.start_music = lambda key: self.trace['music'].append(
            [self._tick, 'start', key])
        s.stop_music = lambda: self.trace['music'].append(
            [self._tick, 'stop', None])
        s.pause_music = lambda: self.trace['music'].append(
            [self._tick, 'pause', None])
        s.unpause_music = lambda: self.trace['music'].append(
            [self._tick, 'unpause', None])

    def _patch_levels(self, level_dict):
        """Serve a hand-written fixture dict for every level number."""
        self._orig_get_level = world_mod.get_level
        self._orig_regenerate = world_mod.regenerate_level
        world_mod.get_level = lambda n, progress=None: level_dict
        world_mod.regenerate_level = lambda n: level_dict

    def close(self):
        if self._orig_get_level is not None:
            world_mod.get_level = self._orig_get_level
            world_mod.regenerate_level = self._orig_regenerate
            self._orig_get_level = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ── driving ───────────────────────────────────────────────────────────────

    def tick(self, events=()):
        """One frame: advance the clock, feed events, update, snapshot."""
        self._clock += DT
        self._tick += 1
        for ev in events:
            self.game.handle_event(ev)
        self.game.update(DT)
        g = self.game
        self.trace['ticks'].append([
            g.state, g.level, g.score, g.lives,
            g.player.col, g.player.row, g._current_room,
            [[e.col, e.row] for e in g.enemies],
            list(g.treasure_pos) if g.treasure_pos else None])

    def run(self, script):
        """Execute a script: list of 'press:k', 'release:k', 'key:k',
        'hold:k:N', 'wait:N' steps.  Each expanded step is one tick."""
        for events in _expand(script):
            self.tick(events)
        return self.trace


def _down(name):
    return pygame.event.Event(pygame.KEYDOWN, key=KEY_MAP[name])


def _up(name):
    return pygame.event.Event(pygame.KEYUP, key=KEY_MAP[name])


def _expand(script):
    """Yield one event-list per tick."""
    for step in script:
        parts = step.split(':')
        op = parts[0]
        if op == 'wait':
            for _ in range(int(parts[1])):
                yield ()
        elif op == 'press':
            yield (_down(parts[1]),)
        elif op == 'release':
            yield (_up(parts[1]),)
        elif op == 'key':                      # down + up in one tick
            yield (_down(parts[1]), _up(parts[1]))
        elif op == 'hold':                     # press, hold, release
            n = int(parts[2])
            yield (_down(parts[1]),)
            for _ in range(max(0, n - 2)):
                yield ()
            yield (_up(parts[1]),)
        else:
            raise ValueError(f'unknown script step: {step!r}')


# ── goldens ───────────────────────────────────────────────────────────────────

def _normalize(obj):
    """Round-trip through JSON so tuples/lists compare equal."""
    return json.loads(json.dumps(obj))


def assert_golden(name, data):
    """Compare data against tests/golden/<name>.json (exact).

    UGLYCRAFT_REGOLD=1 rewrites the golden instead of asserting — re-records
    are deliberate, reviewed statements that a behaviour change is intended.
    """
    path = os.path.join(GOLDEN_DIR, f'{name}.json')
    data = _normalize(data)
    if REGOLD or not os.path.exists(path):
        if not REGOLD:
            raise AssertionError(
                f'golden {name!r} missing — record it with UGLYCRAFT_REGOLD=1')
        os.makedirs(GOLDEN_DIR, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=1, sort_keys=True)
        return
    with open(path) as f:
        golden = json.load(f)
    assert data == golden, (
        f'trace differs from golden {name!r} — if the behaviour change is '
        f'intentional, re-record with UGLYCRAFT_REGOLD=1 and review the diff')


def screen_hash(harness):
    """Render the current frame and hash its pixels (spec 0044 H7)."""
    harness.game.render()
    raw = pygame.image.tobytes(harness.game.surf, 'RGB')
    return hashlib.sha256(raw).hexdigest()
