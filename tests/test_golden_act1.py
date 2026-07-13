"""Golden characterization traces for Act 1 (spec 0044 H5).

Scripts do not aim to win — they cover code paths from a pinned start.
Where a mechanic is expensive to reach by play, the test seeds state
directly (score, positions) before running; the golden pins behaviour
from that state. Re-record deliberately with UGLYCRAFT_REGOLD=1.
"""
import pytest
from tests.harness import Harness, assert_golden

WALK = ['hold:right:12', 'hold:down:10', 'hold:left:20', 'hold:up:8',
        'wait:10']


def _sound_keys(trace):
    return [key for _, key in trace['sounds']]


@pytest.mark.parametrize('level', range(1, 11))
def test_walk_easy(level):
    """Fixed walk on every Act 1 level: movement, bumps, enemy motion."""
    with Harness(level=level, seed=1234) as h:
        trace = h.run(WALK)
    assert 'move' in _sound_keys(trace)
    assert_golden(f'act1_L{level:02d}_walk_easy', trace)


@pytest.mark.parametrize('level', [1, 5])
def test_walk_hard(level):
    """Same walk under hard difficulty (all enemies active, BFS map built)."""
    with Harness(level=level, difficulty='hard', seed=1234) as h:
        trace = h.run(WALK)
    assert_golden(f'act1_L{level:02d}_walk_hard', trace)


def test_wall_break_and_place():
    """Level 2: bump the row-7 wall to destruction twice, earn a placement
    credit, place a wall (SPACE). Covers hits/crack/break/credit/place."""
    with Harness(level=2, seed=1234) as h:
        trace = h.run([
            'hold:down:24',              # walk from (14,1) down to the wall
            'key:down', 'wait:3',        # bump (each press = one bump)
            'key:down', 'wait:3',
            'key:down', 'wait:3',        # third hit breaks (14,7)
            'key:left', 'wait:3',        # step left, face wall at (13,7)
            'key:down', 'wait:3',
            'key:down', 'wait:3',
            'key:down', 'wait:3',        # second break -> 1 credit
            'key:space', 'wait:5',       # place a wall at player position
        ])
    keys = _sound_keys(trace)
    assert keys.count('break') == 2
    assert 'credit' in keys
    assert 'place_block' in keys
    assert_golden('act1_wallbreak_place', trace)


def test_shield_buy_and_expiry():
    """Buy the shield (seeded score), let it run out: 10 s timer.
    Enemies removed — a chasing enemy would consume the shield first."""
    with Harness(level=1, seed=1234) as h:
        h.game.world.score = 1000
        h.game.enemies.clear()
        trace = h.run(['key:return', 'wait:320'])   # 320*33 ms > 10 s
    keys = _sound_keys(trace)
    assert 'shield_buy' in keys
    assert 'shield_expire' in keys
    assert_golden('act1_shield', trace)


def test_death_and_penalty():
    """Enemy placed on an adjacent tile, player steps into it: caught,
    -500 (clamped at 0), life lost, player + all enemies respawn at their
    starts (spec 0067)."""
    with Harness(level=1, seed=1234) as h:
        h.game.world.score = 700
        e = h.game.enemies[0]
        e.col, e.row = h.game.player.col - 1, h.game.player.row
        trace = h.run(['key:left', 'wait:10'])
    keys = _sound_keys(trace)
    assert 'caught' in keys
    last = trace['ticks'][-1]
    assert last[3] == 8                     # lives 9 -> 8
    assert last[2] == 200                   # 700 - 500
    assert_golden('act1_death', trace)


def test_death_with_shield():
    """Shielded catch: no life lost, shield consumed."""
    with Harness(level=1, seed=1234) as h:
        h.game.world.score = 700
        h.game.world.shield = True
        h.game.world._shield_timer = 10_000
        e = h.game.enemies[0]
        e.col, e.row = h.game.player.col - 1, h.game.player.row
        trace = h.run(['key:left', 'wait:10'])
    keys = _sound_keys(trace)
    assert 'caught_shield' in keys
    assert 'caught' not in keys
    assert trace['ticks'][-1][3] == 9       # lives unchanged
    assert_golden('act1_death_shield', trace)


def test_game_over():
    """Last life lost -> GAME_OVER (debug mode never touches hiscore)."""
    with Harness(level=1, seed=1234) as h:
        h.game.world.lives = 1
        e = h.game.enemies[0]
        e.col, e.row = h.game.player.col - 1, h.game.player.row
        trace = h.run(['key:left', 'wait:10'])
    assert 'game_over' in _sound_keys(trace)
    assert trace['ticks'][-1][0] == 'game_over'
    assert_golden('act1_gameover', trace)


def test_level_advance_f10():
    """F10 cheat advances a level: +1 life, level_up, LEVEL_INTRO, music."""
    with Harness(level=1, seed=1234) as h:
        trace = h.run(['key:f10', 'wait:5'])
    assert 'level_up' in _sound_keys(trace)
    last = trace['ticks'][-1]
    assert last[1] == 2 and last[3] == 10
    assert any(m == [0, 'start', 2] or (m[1] == 'start' and m[2] == 2)
               for m in trace['music'])
    assert_golden('act1_advance', trace)


def test_pause_toggle():
    """P pauses (music pauses, world freezes), P resumes."""
    with Harness(level=1, seed=1234) as h:
        trace = h.run(['hold:right:8', 'key:p', 'wait:20', 'key:p',
                       'hold:right:8'])
    states = {t[0] for t in trace['ticks']}
    assert 'paused' in states and 'playing' in states
    assert_golden('act1_pause', trace)
