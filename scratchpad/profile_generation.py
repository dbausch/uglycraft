"""cProfile the level-generation hot path (spec 0070).

Run from the repo root:  .venv/bin/python scratchpad/profile_generation.py

Builds six representative sweep feature sets × 25 seeds under cProfile and
prints the top functions by self and cumulative time.  Used to find and verify
the spec-0070 optimizations (validate_layout bbox prune; _place_puzzle
_comp_map hoist).  Baseline before spec 0070: ~29.4 s / 150 builds; after:
~24.8 s.  See kb/architecture.md "Generation performance".
"""
import cProfile
import os
import pstats
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from levelgraph import LevelGraph
from levellayout import build_level_dict, LayoutError
from tests.conftest import FS_LOCKED, FS_GATED, FS_WATER, FS_ALL
from tests.test_key_placement import FS_CROWDED_LOCKED
from tests.test_water_challenge import FS_CROWDED_WATER

SETS = [FS_LOCKED, FS_GATED, FS_WATER, FS_ALL,
        FS_CROWDED_LOCKED, FS_CROWDED_WATER]


def _build(fs, seed):
    base = random.Random(seed)
    for _ in range(60):
        rng = random.Random(base.randint(0, 2 ** 31))
        g = LevelGraph.generate(fs, rng)
        try:
            return build_level_dict(g, rng=rng,
                                    strategies=fs.get('layout_strategies'),
                                    grid_count=fs.get('grid_count', 1))
        except LayoutError:
            continue
    return None


def workload(seeds=25):
    n = 0
    for seed in range(seeds):
        for fs in SETS:
            _build(fs, seed)
            n += 1
    return n


if __name__ == '__main__':
    pr = cProfile.Profile()
    pr.enable()
    count = workload()
    pr.disable()
    print(f"built {count} levels")
    st = pstats.Stats(pr)
    st.sort_stats('tottime')
    print("\n===== TOP 20 BY TOTTIME (self time) =====")
    st.print_stats(20)
    st.sort_stats('cumulative')
    print("\n===== TOP 15 BY CUMULATIVE =====")
    st.print_stats(15)
