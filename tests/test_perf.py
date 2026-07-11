"""Coarse performance tripwire (spec 0044 H9).

Catches accidental quadratic behaviour during the world-model refactor.
The threshold is deliberately generous — this must never flake on a slow
machine; it exists to catch order-of-magnitude regressions only.
"""
import time

from tests.harness import Harness


def test_update_throughput():
    """2000 headless ticks of level 1 (movement held) in well under 5 s."""
    with Harness(level=1, seed=1234) as h:
        start = time.perf_counter()
        h.run(['press:right', 'wait:1999'])         # 2000 ticks total
        elapsed = time.perf_counter() - start
    assert len(h.trace['ticks']) == 2000
    assert elapsed < 5.0, f'2000 ticks took {elapsed:.2f}s (limit 5s)'


def test_update_throughput_act2_hard():
    """1000 Act 2 ticks on hard: BFS floods the grid through the
    blocked() query every enemy tick (spec 0047) — the plausible
    passability-as-query regression."""
    with Harness(level=11, difficulty='hard', seed=777) as h:
        start = time.perf_counter()
        h.run(['press:right', 'wait:999'])          # 1000 ticks total
        elapsed = time.perf_counter() - start
    assert len(h.trace['ticks']) == 1000
    assert elapsed < 5.0, f'1000 ticks took {elapsed:.2f}s (limit 5s)'
