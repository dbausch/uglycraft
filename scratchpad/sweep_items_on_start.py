"""Statistical R-P8 sweep (spec 0057 / BL-16): no item on player_start
or the entrance tile.

Generates Act 2 levels across many seeds and checks the START room's
treasures, materials, keys, pressure plates, and pushable blocks against
the level's player_start and the room's entrance tile.  Item coordinates
are per-grid, so only the start grid's lists are comparable.

Detector validation: run on the PRE-fix commit first — it must report
>= 1 violation there (that hit becomes the pinned regression seed in
tests/test_entrance.py).  Post-fix: 0 violations.

Run manually:  .venv/bin/python scratchpad/sweep_items_on_start.py [n_seeds]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import levels
from levels import get_level

ITEM_LISTS = ('treasures', 'materials', 'keys',
              'pressure_plates', 'pushable_blocks')


def main(n_seeds=40):
    items_checked = 0
    hits = []
    for seed in range(n_seeds):
        levels.set_game_seed(seed)
        for n in range(11, 21):
            level = get_level(n)
            room = level['rooms'][level['start_room']]
            ps = tuple(level['player_start'])
            forbidden = {ps}
            if 'entrance' in room:
                forbidden.add(tuple(room['entrance']))
            for lname in ITEM_LISTS:
                for entry in room.get(lname, []):
                    items_checked += 1
                    pos = (entry[0], entry[1])
                    if pos in forbidden:
                        hits.append((seed, n, lname, entry))
                        print(f'HIT: seed={seed} level={n} {lname} '
                              f'entry={entry} player_start={ps}')
        print(f'seed {seed}: done ({items_checked} items so far)')
    print(f'\n{items_checked} start-room items checked, '
          f'{len(hits)} violations')
    return 1 if hits else 0


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    sys.exit(main(n))
