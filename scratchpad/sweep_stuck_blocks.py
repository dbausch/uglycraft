"""Statistical stuck-block sweep (spec 0048 U6, successor to the lost
repro_bl13.py referenced in kb/architecture.md).

Generates Act 2 levels across many seeds and replicates the
_verify_blocks condition on every block's START position, using the
same passability the runtime uses (RoomCells.blocked + other blocks).
Before spec 0048 the kb-recorded rate was 2 stuck blocks per 175
block-bearing levels (both water-wedged); after 0048 the expected
count is ZERO.

Run manually (generation cost keeps it out of the suite):

    .venv/bin/python scratchpad/sweep_stuck_blocks.py [n_seeds]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import levels
from cells import build_room_cells
from constants import COLS, ROWS
from levels import get_level


def block_stuck(cells, block, other_blocks):
    bc, br = block
    for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        pf = (bc - dc, br - dr)
        pt = (bc + dc, br + dr)
        ok = True
        for c, r in (pf, pt):
            if not (0 < c < COLS - 1 and 0 < r < ROWS - 1):
                ok = False
            elif cells.blocked(c, r) or (c, r) in other_blocks:
                ok = False
        if ok:
            return False
    return True


def main(n_seeds=25):
    total_levels = 0
    block_levels = 0
    stuck = []
    for seed in range(n_seeds):
        levels.set_game_seed(seed)
        for n in range(11, 21):
            level = get_level(n)
            total_levels += 1
            has_blocks = False
            for rkey, room in level['rooms'].items():
                blocks = [tuple(b) for b in room.get('pushable_blocks', [])]
                if not blocks:
                    continue
                has_blocks = True
                cells = build_room_cells(room)
                for b in blocks:
                    others = set(blocks) - {b}
                    if block_stuck(cells, b, others):
                        stuck.append((seed, n, rkey, b))
                        print(f'STUCK: seed={seed} level={n} '
                              f'room={rkey} block={b}')
            if has_blocks:
                block_levels += 1
        print(f'seed {seed}: done ({block_levels} block-bearing levels so far)')
    print(f'\n{total_levels} levels, {block_levels} with blocks, '
          f'{len(stuck)} stuck blocks')
    return 1 if stuck else 0


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    sys.exit(main(n))
