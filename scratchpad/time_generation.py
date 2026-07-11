"""Generation timing for Act 2 levels (spec 0060 performance budget).

Budget: level 20 <= 12 s, whole Act 2 (levels 11-20, one seed) <= 45 s.
Run before and after the room-count rescale to compare.

Run manually:  .venv/bin/python scratchpad/time_generation.py [n_seeds]
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import levels
from levels import get_level


def main(n_seeds=3):
    worst = {}
    for seed in range(n_seeds):
        levels.set_game_seed(seed)
        total = 0.0
        for n in range(11, 21):
            t0 = time.perf_counter()
            get_level(n)
            dt = time.perf_counter() - t0
            total += dt
            worst[n] = max(worst.get(n, 0.0), dt)
            print(f'seed {seed} L{n}: {dt:6.2f} s')
        print(f'seed {seed} act 2 total: {total:6.2f} s')
    print('\nworst per level:')
    for n in range(11, 21):
        print(f'  L{n}: {worst[n]:6.2f} s')
    ok = worst[20] <= 12.0
    print(f'\nlevel 20 worst {worst[20]:.2f} s — budget 12 s: '
          f'{"OK" if ok else "EXCEEDED"}')
    return 0 if ok else 1


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    sys.exit(main(n))
