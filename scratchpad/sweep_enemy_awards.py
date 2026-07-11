"""Statistical R-P9/R-P10 sweep (spec 0058 / BL-20+).

Generates >= 100 Act 2 levels (all 10 feature sets x seeds) and counts:

  corridor  — enemy start owned by a corridor node
  capacity  — room holding more enemies than s - 2 (s = largest
              all-floor square side)
  total     — level enemy total != 2 x G
  award     — award in a non-corridor room that is neither
              challenge-protected nor an enemy host
  conserve  — level award total != #challenge rooms + #enemies

Detector validation: run on the PRE-fix commit first — it must report
violations there (total/award are certain).  Post-fix: 0 violations.

Run manually:  .venv/bin/python scratchpad/sweep_enemy_awards.py [n_seeds]
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import levels
from levelgraph import LevelGraph, EdgeType, NodeSize
from levellayout import build_level_dict, LayoutError

from tests.test_enemy_room_size import (
    _largest_square, _floors_by_owner, _corridor_names,
    _challenge_rooms, _enemy_starts, _award_owners)


def _build(fs, seed):
    base = random.Random(seed)
    for _ in range(60):
        rng = random.Random(base.randint(0, 2 ** 31))
        g = LevelGraph.generate(fs, rng)
        try:
            return g, build_level_dict(g, rng=rng,
                                       strategies=fs.get('layout_strategies'))
        except LayoutError:
            continue
    raise AssertionError(f"build failed seed={seed}")


def main(n_seeds=12):
    built = 0
    hits = []
    for seed in range(n_seeds):
        for idx, fs in enumerate(levels.ACT2_FEATURE_SETS):
            level = 11 + idx
            graph, lv = _build(fs, seed)
            built += 1
            G = fs.get('grid_count', 1)
            cor = _corridor_names(graph)
            protected = _challenge_rooms(graph)

            starts = _enemy_starts(lv)
            per_room = {}
            for gname, pos, _t in starts:
                owner = lv['rooms'][gname]['tile_owner'].get(pos)
                if owner in cor:
                    hits.append((seed, level, 'corridor', pos))
                    print(f'CORRIDOR: seed={seed} L{level} start={pos}')
                per_room[(gname, owner)] = per_room.get((gname, owner), 0) + 1
            for (gname, owner), k in per_room.items():
                if owner in cor:
                    continue
                s = _largest_square(_floors_by_owner(
                    lv['rooms'][gname])[owner])
                if k > s - 2:
                    hits.append((seed, level, 'capacity', (owner, k, s)))
                    print(f'CAPACITY: seed={seed} L{level} room={owner} '
                          f'k={k} s={s}')
            if len(starts) != 2 * G:
                hits.append((seed, level, 'total', len(starts)))
                print(f'TOTAL: seed={seed} L{level} {len(starts)} != {2 * G}')

            awards = _award_owners(lv)
            enemies_in = {}
            for gname, pos, _t in starts:
                owner = lv['rooms'][gname]['tile_owner'][pos]
                enemies_in[(gname, owner)] = 1
            for (gname, owner), n in awards.items():
                if owner in cor:
                    continue
                if owner not in protected and (gname, owner) not in enemies_in:
                    hits.append((seed, level, 'award', (owner, n)))
                    print(f'AWARD: seed={seed} L{level} room={owner} n={n}')
            total_awards = sum(awards.values())
            expected = len(protected) + len(starts)
            if total_awards != expected:
                hits.append((seed, level, 'conserve',
                             (total_awards, expected)))
                print(f'CONSERVE: seed={seed} L{level} '
                      f'{total_awards} != {expected}')
        print(f'seed {seed}: done ({built} levels so far)')
    print(f'\n{built} levels checked, {len(hits)} violations')
    return 1 if hits else 0


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    sys.exit(main(n))
