"""Live Room objects and exit detection for multi-room levels."""
from constants import COLS, ROWS, HARD
from cells import build_room_cells
from entities import Block, Enemy, ForgeOgre, PatrolEnemy


class Room:
    """A live room (spec 0051, refactor Stage 5): owns everything
    room-scoped.  Rooms persist by IDENTITY — entering a visited room
    swaps World.room to this object; there is no snapshot copying."""

    __slots__ = ('key', 'data', 'cells', 'enemies', 'enemies_initial',
                 'blocks', 'blocks_initial', 'tile_owner', 'dead_squares')

    def __init__(self, key, data, cells, enemies, blocks):
        self.key = key
        self.data = data
        self.cells = cells
        self.enemies = enemies
        # Original spawn tiles, captured once (spec 0067) — the death-respawn
        # reset restores from these, exactly as blocks_initial does for blocks.
        self.enemies_initial = tuple((e.col, e.row) for e in enemies)
        self.blocks = blocks                  # [Block, ...] — occupants
        self.blocks_initial = tuple((b.col, b.row) for b in blocks)
        self.tile_owner = data.get('tile_owner', {})
        self.dead_squares = set(tuple(t) for t in data.get('dead_squares', []))

    # ── Occupant helpers (spec 0052 G3) ───────────────────────────────────────

    def block_at(self, c, r):
        for b in self.blocks:
            if b.col == c and b.row == r:
                return b
        return None

    def block_positions(self):
        return [(b.col, b.row) for b in self.blocks]

    # ── Compat views over the fixture layer (spec 0052 G2) ────────────────────

    @property
    def plates(self):
        """[(c, r, channel), ...] — a view over the plate fixtures."""
        return [(c, r, f.payload)
                for (c, r), f in self.cells.fixtures_of_kind('plate')]

    @property
    def safe_tile_set(self):
        """Union of every plate's `safe_tiles` (spec 0068): the room-floor
        tiles from which a block can still be pushed to some plate.  A block
        pushed off this set is doomed.  Computed from the plate objects — no
        position-keyed map beside them."""
        return frozenset().union(
            *(f.safe_tiles for _, f in self.cells.fixtures_of_kind('plate')))

    @property
    def flame_jets(self):
        """Jet dicts — a view over the flame-nozzle fixtures."""
        return [f.payload
                for _, f in self.cells.fixtures_of_kind('flame_nozzle')]

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
                   blocks=[Block(b[0], b[1])
                           for b in data.get('pushable_blocks', [])])

    @classmethod
    def placeholder(cls):
        """Empty room so World is queryable before the first level loads."""
        from cells import RoomCells
        return cls(None, {}, RoomCells(), [], [])


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
