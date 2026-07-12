"""ASCII export of a loaded level (spec 0064): the handover state.

dump_level renders the world exactly as it stands the moment control
would normally be handed to the player — via the real World.start_level
path, never from the raw level dict.  Pygame-free.

Single-grid levels print in the spec-0064 diagram format (two ruler
lines + numbered rows).  Multi-grid levels print an index of grids and
one large 2D canvas with every grid at its super-grid position, derived
by BFS over the stitch topology in the rooms' `exits` keys.
"""
import random

from cells import _exit_tiles
from constants import COLS, ROWS, EASY
from entities import ForgeOgre, PatrolEnemy
from rooms import Room

BARRIER_CHARS = {
    'border': '#', 'stone': '#', 'placed': '#',
    'reinforced': 'R', 'wooden': 'w', 'door': 'D', 'gate': 'G',
}
ITEM_CHARS = {'treasure': '*', 'material': 'm', 'key': 'k'}
FIXTURE_CHARS = {'plate': '_', 'flame_nozzle': '!'}
DELTAS = {'left': (-1, 0), 'right': (1, 0), 'top': (0, -1), 'bottom': (0, 1)}


def _render_grid(room, data, world=None):
    """One room as a list of ROWS strings of COLS symbols.  `world` is
    passed for the live start room only: it overlays the spawned
    treasure and the player."""
    cells = room.cells
    grid = [['.'] * COLS for _ in range(ROWS)]
    for r in range(ROWS):
        for c in range(COLS):
            if cells.is_water(c, r):
                grid[r][c] = '=' if cells.bridge(c, r) else '~'
    for (c, r), barrier in cells.barriers():
        grid[r][c] = BARRIER_CHARS[barrier.kind]
    for c, r in _exit_tiles(data.get('exits', {})):
        if cells.barrier(c, r) is None:
            grid[r][c] = 'X'
    for kind, ch in FIXTURE_CHARS.items():
        for (c, r), _fixture in cells.fixtures_of_kind(kind):
            grid[r][c] = ch
    for kind, ch in ITEM_CHARS.items():
        for (c, r), _item in cells.items_of_kind(kind):
            grid[r][c] = ch
    for c, r in room.block_positions():
        grid[r][c] = 'O'
    for enemy in room.enemies:
        ch = 'F' if isinstance(enemy, ForgeOgre) else \
             'p' if isinstance(enemy, PatrolEnemy) else 'e'
        grid[enemy.row][enemy.col] = ch
    if 'entrance' in data:
        ec, er = data['entrance']
        grid[er][ec] = 'E'
    if world is not None:
        if world.treasure_pos is not None:
            tc, tr = world.treasure_pos
            grid[tr][tc] = 'C' if world.treasure_item_no == 10 else '*'
        grid[world.player.row][world.player.col] = 'P'
    return [''.join(row) for row in grid]


def _super_positions(data):
    """Place each grid on the super-grid by BFS over the stitch exits,
    normalised so the top-left occupied cell is (0, 0)."""
    start = data['start_room']
    pos = {start: (0, 0)}
    queue = [start]
    while queue:
        key = queue.pop(0)
        gx, gy = pos[key]
        for exit_key, target in data['rooms'][key].get('exits', {}).items():
            side = exit_key.rsplit('_', 1)[0]
            dx, dy = DELTAS[side]
            tpos = (gx + dx, gy + dy)
            if target in pos:
                if pos[target] != tpos:
                    raise ValueError(
                        f'inconsistent stitch topology: {target} at '
                        f'{pos[target]} and {tpos}')
            else:
                pos[target] = tpos
                queue.append(target)
    if set(pos) != set(data['rooms']):
        raise ValueError('rooms unreachable via exits: '
                         f'{set(data["rooms"]) - set(pos)}')
    min_x = min(x for x, _ in pos.values())
    min_y = min(y for _, y in pos.values())
    return {k: (x - min_x, y - min_y) for k, (x, y) in pos.items()}


def _single_grid_text(rows):
    lines = ['     ' + ''.join(str(c // 10) for c in range(COLS)),
             '     ' + ''.join(str(c % 10) for c in range(COLS))]
    lines += [f'  {r:2d} ' + rows[r] for r in range(ROWS)]
    return '\n'.join(lines) + '\n'


def _canvas_text(data, grids, positions):
    start = data['start_room']
    keys = [start] + sorted((k for k in grids if k != start), key=str)
    index = []
    for key in keys:
        exits = data['rooms'][key].get('exits', {})
        exits_txt = ', '.join(f'{ek} -> {tgt}' for ek, tgt in exits.items())
        index.append(f'{key} @ {positions[key]}   exits: {exits_txt}')
    width = (max(x for x, _ in positions.values()) + 1) * (COLS + 1) - 1
    height = (max(y for _, y in positions.values()) + 1) * (ROWS + 1) - 1
    canvas = [[' '] * width for _ in range(height)]
    for key, (gx, gy) in positions.items():
        ox, oy = gx * (COLS + 1), gy * (ROWS + 1)
        for r, row in enumerate(grids[key]):
            canvas[oy + r][ox:ox + COLS] = row
    body = '\n'.join(''.join(row).rstrip() for row in canvas)
    return '\n'.join(index) + '\n\n' + body + '\n'


def dump_level(level_num, difficulty=EASY, seed=None):
    """ASCII rendering of level `level_num` (1-20) as loaded.

    With `seed`, both the Act 2 base seed and the runtime rng (which
    feeds the Act 1 treasure spawn) are pinned — the output is fully
    deterministic.
    """
    import levels
    from world import World
    world = World(difficulty)
    # Pin AFTER constructing World: its init rolls a fresh game seed and
    # draws from the global rng (same ordering rule as tests/harness.py).
    if seed is not None:
        random.seed(seed)
        levels.set_game_seed(seed)
    world.start_level(level_num)
    data = world._level_data
    grids = {}
    for key, rdata in data['rooms'].items():
        if key == world.room.key:
            grids[key] = _render_grid(world.room, rdata, world=world)
        else:
            grids[key] = _render_grid(Room.from_data(key, rdata, difficulty),
                                      rdata)
    if len(grids) == 1:
        return _single_grid_text(grids[data['start_room']])
    return _canvas_text(data, grids, _super_positions(data))
