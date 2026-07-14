"""BL-56 sweep: duplicate-colour keys and/or doors per generated level.

Detailed statistics:
  * keys-per-colour histogram: over every (level, colour) slot that has >=1
    key, how many keys that colour has (1, 2, 3, 4, ...).
  * max keys of a single colour ever seen, with (seed, level, colour).
  * per-level-number breakdown: mean total locked doors, mean max-keys-of-
    one-colour, and fraction of levels with any duplicate colour.

Run:  .venv/bin/python scratchpad/sweep_dup_colour.py [n_seeds]
"""
import collections
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import levels
from levelgraph import LevelGraph
from levellayout import build_level_dict, LayoutError


def _build(fs, seed):
    base = random.Random(seed)
    for _ in range(60):
        rng = random.Random(base.randint(0, 2 ** 31))
        g = LevelGraph.generate(fs, rng)
        try:
            return build_level_dict(g, rng=rng,
                                    strategies=fs.get('layout_strategies'))
        except LayoutError:
            continue
    raise AssertionError(f"build failed seed={seed}")


def main(n_seeds=30):
    built = 0
    # keys_per_colour_hist[n] = number of (level, colour) slots with exactly n keys
    keys_per_colour_hist = collections.Counter()
    doors_per_colour_hist = collections.Counter()
    total_keys = 0
    max_one = (0, None, None, None)   # (count, seed, level, colour)
    # per level-number aggregates
    per_level = collections.defaultdict(lambda: {
        'n': 0, 'sum_total_doors': 0, 'sum_max_one': 0,
        'dup_levels': 0, 'max_one': 0})

    for seed in range(n_seeds):
        for idx, fs in enumerate(levels.ACT2_FEATURE_SETS):
            level_no = 11 + idx
            lv = _build(fs, seed)
            built += 1

            keys = collections.Counter()
            doors = collections.Counter()
            for rd in lv['rooms'].values():
                for k in rd.get('keys', []):
                    keys[k[2]] += 1
                for d in rd.get('locked_doors', []):
                    doors[d[2]] += 1

            for col, n in keys.items():
                keys_per_colour_hist[n] += 1
                total_keys += n
                if n > max_one[0]:
                    max_one = (n, seed, level_no, col)
            for col, n in doors.items():
                doors_per_colour_hist[n] += 1

            total_doors = sum(doors.values())
            level_max_one = max(keys.values()) if keys else 0
            has_dup = any(n > 1 for n in keys.values())

            pl = per_level[level_no]
            pl['n'] += 1
            pl['sum_total_doors'] += total_doors
            pl['sum_max_one'] += level_max_one
            pl['dup_levels'] += 1 if has_dup else 0
            pl['max_one'] = max(pl['max_one'], level_max_one)
        print(f'seed {seed} done ({built} levels)', flush=True)

    print(f'\n===== {built} levels checked ({n_seeds} seeds x 10 Act2 levels) =====\n')

    print('KEYS-PER-COLOUR histogram  (a "slot" = one colour in one level '
          'that has >=1 key):')
    tot_slots = sum(keys_per_colour_hist.values())
    for n in sorted(keys_per_colour_hist):
        c = keys_per_colour_hist[n]
        print(f'  {n} key(s) of a colour : {c:5d} slots  ({100*c/tot_slots:5.1f}%)')
    print(f'  total colour-slots      : {tot_slots}')
    print(f'  total keys placed       : {total_keys}')
    dup_slots = sum(c for n, c in keys_per_colour_hist.items() if n > 1)
    print(f'  slots with >1 key       : {dup_slots} '
          f'({100*dup_slots/tot_slots:.1f}% of colour-slots)')

    print('\nDOORS-PER-COLOUR histogram (should mirror keys, R-K1):')
    tot_d = sum(doors_per_colour_hist.values())
    for n in sorted(doors_per_colour_hist):
        c = doors_per_colour_hist[n]
        print(f'  {n} door(s) of a colour: {c:5d} slots  ({100*c/tot_d:5.1f}%)')

    print(f'\nMAX keys of a SINGLE colour in one level: {max_one[0]} '
          f'(seed={max_one[1]} L{max_one[2]} colour={max_one[3]})')

    print('\nPER-LEVEL-NUMBER breakdown:')
    print('  level | mean_doors | mean_max_dup | worst_max_dup | %dup_levels')
    for lvl in sorted(per_level):
        pl = per_level[lvl]
        n = pl['n']
        print(f'   L{lvl:<3} | {pl["sum_total_doors"]/n:9.1f}  |'
              f' {pl["sum_max_one"]/n:11.2f}  | {pl["max_one"]:12d}  |'
              f' {100*pl["dup_levels"]/n:6.1f}%')
    return 0


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    sys.exit(main(n))
