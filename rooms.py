"""Room state management for multi-room Act 2 levels."""
from constants import COLS, ROWS, WALL_STONE


class RoomState:
    """Snapshot of a single room's mutable state.

    cells (the spec-0047 layered model) carries the room's walls, doors,
    gates, water/bridges, and bump damage; items and enemies keep their
    own lists until their refactor stages."""

    __slots__ = ('cells', 'enemies', 'treasures', 'materials', 'keys',
                 'blocks')

    def __init__(self, cells, enemies,
                 treasures=None, materials=None, keys=None, blocks=None):
        self.cells = cells
        self.enemies = enemies
        self.treasures = treasures or []
        self.materials = materials or []
        self.keys = keys or []
        self.blocks = blocks or []


def parse_level_walls(raw):
    """Normalize level wall data to a dict {(col, row): wall_type}.

    Accepts either a set (Act 1: all stone) or a dict (Act 2: typed walls).
    """
    if isinstance(raw, dict):
        return dict(raw)
    return {pos: WALL_STONE for pos in raw}


def find_exit(col, row, room_data):
    """Check whether (col, row) is an exit tile and return target info.

    Returns (target_room_key, entry_col, entry_row) if (col, row) is an exit,
    or None otherwise.

    Exits are defined in room_data['exits'] as:
        {'{side}_{pos}': target_room_key}
    where side is 'left'|'right'|'top'|'bottom' and pos is the row/col index.
    """
    exits = room_data.get('exits', {})
    for exit_key, target in exits.items():
        side, pos_str = exit_key.rsplit('_', 1)
        pos = int(pos_str)
        if side == 'left' and col == 0 and row == pos:
            return (target, COLS - 1, row)
        elif side == 'right' and col == COLS - 1 and row == pos:
            return (target, 0, row)
        elif side == 'top' and row == 0 and col == pos:
            return (target, col, ROWS - 1)
        elif side == 'bottom' and row == ROWS - 1 and col == pos:
            return (target, col, 0)
    return None
