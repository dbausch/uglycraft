"""Self-tests for the characterization harness (spec 0044 H2-H4)."""
import levels
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


def test_hard_difficulty_runs():
    """BFS enemies (hard) drive without error.

    Hard and easy traces are currently IDENTICAL: Act 1 enemies always
    wander (chase branch unreachable — post-v1.5 regression, see
    kb/backlog.md "Act 1 enemies never chase").  Strengthen this to
    t_hard != t_easy when that item is fixed.
    """
    with Harness(level=1, difficulty='hard', seed=7) as h:
        t_hard = h.run(WALK)
    with Harness(level=1, difficulty='easy', seed=7) as h:
        t_easy = h.run(WALK)
    assert t_hard['ticks'] == t_easy['ticks']   # documents the regression
