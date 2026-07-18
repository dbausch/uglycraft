"""Self-tests for the characterization harness (spec 0044 H2-H4)."""
from uglycraft import levels
from tests.harness import Harness

WALK = ['hold:right:12', 'hold:down:10', 'hold:left:20', 'hold:up:8',
        'wait:10']


def test_set_game_seed_deterministic():
    """Same seed ⇒ same Act 2 level content, twice in a row (H2)."""
    levels.set_game_seed(99)
    first = levels.get_level(11)
    levels.set_game_seed(99)          # clears the cache
    second = levels.get_level(11)
    assert first is not second        # genuinely regenerated
    assert first == second


def test_headless_run_completes():
    """A scripted level-1 run works with no display (H3)."""
    with Harness(level=1) as h:
        trace = h.run(WALK)
    assert len(trace['ticks']) == 60      # 12+10+20+8 hold ticks + 10 wait
    assert trace['ticks'][0][0] == 'playing'
    assert any(key == 'move' for _, key in trace['sounds'])


def test_trace_deterministic():
    """Identical setup + script ⇒ identical trace, twice in-process (H4)."""
    with Harness(level=1, seed=7) as h1:
        t1 = h1.run(WALK)
    with Harness(level=1, seed=7) as h2:
        t2 = h2.run(WALK)
    assert t1 == t2


def test_hard_difficulty_differs():
    """Hard (BFS chase) and easy (greedy chase) produce different traces.

    Was == while BL-34 stood (Act 1 enemies always wandered, so both
    difficulties consumed the same random calls)."""
    with Harness(level=1, difficulty='hard', seed=7) as h:
        t_hard = h.run(WALK)
    with Harness(level=1, difficulty='easy', seed=7) as h:
        t_easy = h.run(WALK)
    assert t_hard['ticks'] != t_easy['ticks']


def _dist_to_player(trace, tick_idx):
    t = trace['ticks'][tick_idx]
    pc, pr = t[4], t[5]
    ec, er = t[7][0]
    return abs(pc - ec) + abs(pr - er)


def test_act1_enemy_chases():
    """BL-34: with the player standing still, the enemy must close in
    decisively on both difficulties (wander never nets this)."""
    for difficulty in ('easy', 'hard'):
        with Harness(level=1, difficulty=difficulty, seed=7) as h:
            trace = h.run(['wait:60'])       # ~6 enemy moves at 294 ms
        start = _dist_to_player(trace, 0)    # 13 tiles apart on level 1
        end = _dist_to_player(trace, -1)
        assert end <= start - 5, (
            f'{difficulty}: enemy closed only {start - end} tiles '
            f'({start} -> {end}) — wandering, not chasing')
