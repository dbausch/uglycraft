"""Live Room objects and exit detection for multi-room levels."""
from constants import COLS, ROWS, HARD
from cells import build_room_cells
from entities import Enemy, ForgeOgre, PatrolEnemy


class Room:
    """A live room (spec 0051, refactor Stage 5): owns everything
    room-scoped.  Rooms persist by IDENTITY — entering a visited room
    swaps World.room to this object; there is no snapshot copying."""

    __slots__ = ('key', 'data', 'cells', 'enemies', 'blocks',
                 'blocks_initial', 'plates', 'tile_owner',
                 'dead_squares', 'flame_jets')

    def __init__(self, key, data, cells, enemies, blocks, plates):
        self.key = key
        self.data = data
        self.cells = cells
        self.enemies = enemies
        self.blocks = blocks
        self.blocks_initial = tuple(blocks)   # death-reset positions
        self.plates = plates
        self.tile_owner = data.get('tile_owner', {})
        self.dead_squares = set(tuple(t) for t in data.get('dead_squares', []))
        self.flame_jets = data.get('flame_jets', [])
        for jet in self.flame_jets:
            jet['_tile_set'] = frozenset(tuple(t) for t in jet['tiles'])

    @classmethod
    def from_data(cls, key, data, difficulty):
        """Build a room from its level-dict entry (first entry only).
        Consumes no RNG, so creation order cannot shift random draws."""
        cells = build_room_cells(data)
        starts = data.get('enemy_starts', [])
        patrols = data.get('patrol_enemies', [])
        if difficulty == HARD:
            active = starts
            active_patrols = patrols
        else:
            # EASY: keep all special enemies + up to 1 regular chaser
            special = [s for s in starts if len(s) >= 3 and s[2] != 'chaser']
            regular = [s for s in starts if len(s) < 3 or s[2] == 'chaser']
            active = special + regular[:1]
            active_patrols = patrols[:1] if patrols else []
        enemies = []
        for edata in active:
            if len(edata) >= 3:
                ec, er, etype = edata[0], edata[1], edata[2]
            else:
                ec, er, etype = edata[0], edata[1], 'chaser'
            if etype == 'forge_ogre':
                enemies.append(ForgeOgre(ec, er))
            else:
                enemies.append(Enemy(ec, er))
        for pdata in active_patrols:
            enemies.append(PatrolEnemy(pdata['start'][0], pdata['start'][1],
                                       pdata['waypoints']))
        return cls(key, data,
                   cells=cells,
                   enemies=enemies,
                   blocks=list(data.get('pushable_blocks', [])),
                   plates=list(data.get('pressure_plates', [])))

    @classmethod
    def placeholder(cls):
        """Empty room so World is queryable before the first level loads."""
        from cells import RoomCells
        return cls(None, {}, RoomCells(), [], [], [])


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
