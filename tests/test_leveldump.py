"""--dump-level ASCII export (spec 0064): handover state, 2D super-grid canvas.

dump_level renders the world exactly as loaded — the moment control would
be handed to the player — via the real World.start_level path.
"""
import pytest

from constants import COLS, ROWS, EASY, HARD
from leveldump import dump_level

SEED = 1234

# spec 0064 table: level -> (entrance, player_start)
EXPECTED = {
    1:  ((29, 7),  (28, 7)),
    2:  ((14, 0),  (14, 1)),
    3:  ((29, 7),  (28, 7)),
    4:  ((14, 0),  (14, 1)),
    5:  ((14, 15), (14, 14)),
    6:  ((29, 7),  (28, 7)),
    7:  ((14, 0),  (14, 1)),
    8:  ((29, 7),  (28, 7)),
    9:  ((29, 7),  (28, 7)),
    10: ((0, 7),   (1, 7)),
}

LEVEL_2_DIAGRAM = """\
     000000000011111111112222222222
     012345678901234567890123456789
   0 ##############E###############
   1 #.............P..............#
   2 #............................#
   3 #............................#
   4 #............................#
   5 #............................#
   6 #............................#
   7 #.....##################.....#
   8 #............................#
   9 #............................#
  10 #............................#
  11 #............................#
  12 #............................#
  13 #............................#
  14 #.............e..............#
  15 ##############################"""


def _grid_rows(dump):
    """Rows of a single-grid dump: two ruler lines, then 16 numbered rows."""
    lines = dump.rstrip('\n').splitlines()
    assert len(lines) == ROWS + 2, f'expected rulers + {ROWS} rows, got {len(lines)} lines'
    for ruler in lines[:2]:
        assert ruler.startswith('     ') and len(ruler) == 5 + COLS
    rows = [line[5:] for line in lines[2:]]
    assert all(len(row) == COLS for row in rows)
    return rows


@pytest.mark.parametrize('level', sorted(EXPECTED))
def test_act1_handover_state(level):
    """One 30x16 grid; E at the spec position with P directly inside;
    exactly one spawned treasure; the crown never shows at handover."""
    rows = _grid_rows(dump_level(level, seed=SEED))
    (ec, er), (pc, pr) = EXPECTED[level]
    flat = ''.join(rows)
    assert rows[er][ec] == 'E' and flat.count('E') == 1
    assert rows[pr][pc] == 'P' and flat.count('P') == 1
    assert flat.count('*') == 1
    assert 'C' not in flat


def test_act1_masked_pin_level_2():
    """HARD dump of level 2, with the spawned treasure masked back to
    floor, equals the spec 0064 diagram verbatim."""
    dump = dump_level(2, difficulty=HARD, seed=SEED)
    assert dump.rstrip('\n').replace('*', '.') == LEVEL_2_DIAGRAM


def test_difficulty_filters_enemies():
    """Level 7 has three authored enemies: EASY loads one, HARD all."""
    easy = ''.join(_grid_rows(dump_level(7, difficulty=EASY, seed=SEED)))
    hard = ''.join(_grid_rows(dump_level(7, difficulty=HARD, seed=SEED)))
    assert easy.count('e') == 1
    assert hard.count('e') == 3


# ── Act 2: 2D super-grid canvas ───────────────────────────────────────────────

ACT2_LEVEL = 13
ACT2_SEED = 777

_DELTA = {'left': (-1, 0), 'right': (1, 0), 'top': (0, -1), 'bottom': (0, 1)}


def _super_positions(data):
    """BFS the stitch topology (as the dump must) to place each grid."""
    pos = {data['start_room']: (0, 0)}
    queue = [data['start_room']]
    while queue:
        key = queue.pop(0)
        gx, gy = pos[key]
        for exit_key, target in data['rooms'][key].get('exits', {}).items():
            side = exit_key.rsplit('_', 1)[0]
            dx, dy = _DELTA[side]
            tpos = (gx + dx, gy + dy)
            if target in pos:
                assert pos[target] == tpos, 'inconsistent stitch topology'
            else:
                pos[target] = tpos
                queue.append(target)
    min_x = min(x for x, _ in pos.values())
    min_y = min(y for _, y in pos.values())
    return {k: (x - min_x, y - min_y) for k, (x, y) in pos.items()}


def _act2_level_dict():
    import levels
    levels.set_game_seed(ACT2_SEED)
    return levels.get_level(ACT2_LEVEL)


def _exit_tile(exit_key):
    side, pos_str = exit_key.rsplit('_', 1)
    pos = int(pos_str)
    return {'left': (0, pos), 'right': (COLS - 1, pos),
            'top': (pos, 0), 'bottom': (pos, ROWS - 1)}[side]


def test_act2_canvas_layout():
    """Every grid renders as a 30x16 block at its BFS-derived super
    position; one P and one E overall; facing exit gaps align."""
    data = _act2_level_dict()
    dump = dump_level(ACT2_LEVEL, seed=ACT2_SEED)
    positions = _super_positions(data)
    assert set(positions) == set(data['rooms'])

    # canvas = everything after the index header (separated by a blank line)
    head, _, canvas = dump.partition('\n\n')
    for key in data['rooms']:
        assert str(key) in head
    lines = canvas.rstrip('\n').splitlines()

    def cell(x, y):
        return lines[y][x] if y < len(lines) and x < len(lines[y]) else ' '

    for key, (gx, gy) in positions.items():
        ox, oy = gx * (COLS + 1), gy * (ROWS + 1)
        block = [''.join(cell(ox + c, oy + r) for c in range(COLS))
                 for r in range(ROWS)]
        assert ' ' not in ''.join(block), f'{key}: block not fully rendered'
        for c, r in ((0, 0), (COLS - 1, 0), (0, ROWS - 1), (COLS - 1, ROWS - 1)):
            assert block[r][c] == '#', f'{key}: corner ({c},{r}) not wall'
        # facing exit gaps align across the gutter
        for exit_key, target in data['rooms'][key].get('exits', {}).items():
            ec, er = _exit_tile(exit_key)
            assert block[er][ec] == 'X', f'{key}: exit {exit_key} not X'
            tx, ty = positions[target]
            tox, toy = tx * (COLS + 1), ty * (ROWS + 1)
            side = exit_key.rsplit('_', 1)[0]
            fc, fr = _exit_tile({'left': f'right_{er}', 'right': f'left_{er}',
                                 'top': f'bottom_{ec}', 'bottom': f'top_{ec}'}[side])
            assert cell(tox + fc, toy + fr) == 'X', \
                f'{key}: facing gap of {exit_key} in {target} not X'

    # empty super-cells (inside the bounding box) stay blank
    occupied = set(positions.values())
    max_x = max(x for x, _ in occupied)
    max_y = max(y for _, y in occupied)
    for sx in range(max_x + 1):
        for sy in range(max_y + 1):
            if (sx, sy) not in occupied:
                region = ''.join(cell(sx * (COLS + 1) + c, sy * (ROWS + 1) + r)
                                 for c in range(COLS) for r in range(ROWS))
                assert region.strip() == '', f'super-cell ({sx},{sy}) not blank'

    flat = ''.join(lines)
    assert flat.count('P') == 1
    assert flat.count('E') == 1
    # P and E inside the start grid's block
    sgx, sgy = positions[data['start_room']]
    sx0, sy0 = sgx * (COLS + 1), sgy * (ROWS + 1)
    start_block = ''.join(cell(sx0 + c, sy0 + r)
                          for c in range(COLS) for r in range(ROWS))
    assert 'P' in start_block and 'E' in start_block


def test_act2_deterministic():
    """Same seed, same dump — byte-identical."""
    assert dump_level(ACT2_LEVEL, seed=ACT2_SEED) == \
        dump_level(ACT2_LEVEL, seed=ACT2_SEED)
