"""Layered cell model (spec 0047, refactor Stage 3): terrain + fixtures.

A cell is a stack of layers (→ kb/world-model-review.md §3 Stage 3, §5):
exactly one Terrain underfoot (floor or water) and at most one
cell-filling Barrier fixture, optionally a Bridge fixture over water.
Walls are not terrain — breaking a wall removes a fixture and reveals
the floor that was always beneath; placing a wall installs a fixture.

Barrier opening policies mirror the generator's EdgeType semantics:

    border / reinforced   never opens
    stone                 breaks after 3 bumps      (hits state)
    wooden                breaks after 2 bumps
    placed                player-installed; forge ogre breaks in 2
    door(colour)          opens by key match on bump
    gate(channel)         blocks iff its channel is low

Passability is NOT answered here: World.blocked(c, r) folds barrier,
terrain/bridge, and the occupant block list together, because the latched
channel state and the blocks live on the World.  This module is pygame-free
(pinned by the spec-0045 import-isolation test via world.py).
"""
from dataclasses import dataclass
from enum import Enum, auto

from constants import (COLS, ROWS, ENTRANCE_CHANNEL, WALL_BUMPS,
                       WALL_HITS_TO_BREAK, WALL_STONE, WALL_WOODEN)


def parse_level_walls(raw):
    """Normalize level wall data to a dict {(col, row): wall_type}.

    Accepts either a set (Act 1: all stone) or a dict (Act 2: typed
    walls).  Moved here from rooms.py (spec 0051) so rooms.Room can
    import cells without a cycle."""
    if isinstance(raw, dict):
        return dict(raw)
    return {pos: WALL_STONE for pos in raw}


class Terrain(Enum):
    FLOOR = auto()
    WATER = auto()


@dataclass
class Barrier:
    """Cell-filling fixture: partitions the grid, entities bump into it.
    Kinds 'stone'/'wooden'/'reinforced' equal the WALL_* constants;
    what bumping does is the BARRIER_BUMP table below."""
    kind: str                   # 'border' | 'reinforced' | 'stone' | 'wooden'
                                #   | 'placed' | 'door' | 'gate'
    colour: str = None          # doors
    channel: str = None         # gates: the gate_id
    hits: int = 0               # bump damage (breakable kinds)

    def blocks(self, channels=frozenset()):
        if self.kind == 'gate':
            return self.channel not in channels
        return True


# Bump dispatch table (spec 0050 Q2): what bumping a barrier does.
#   None  → inert (never opens by bumping)
#   'key' → door: opens on key match
#   int   → breakable: hits required to break
BARRIER_BUMP = {
    'border':     None,
    'reinforced': None,
    'gate':       None,
    'door':       'key',
    WALL_STONE:   WALL_BUMPS[WALL_STONE],      # 3
    WALL_WOODEN:  WALL_BUMPS[WALL_WOODEN],     # 2
    'placed':     WALL_HITS_TO_BREAK,          # 3
}


@dataclass
class Item:
    """Pickup lying on a cell (spec 0050 Q3): kind ∈ 'treasure' |
    'material' | 'key'; payload = item_no / material type / colour."""
    kind: str
    payload: object


@dataclass
class Fixture:
    """Generic non-blocking fixture (spec 0052 G2): kind ∈ 'plate'
    (payload = channel name) | 'flame_nozzle' (payload = the jet dict,
    tiles precomputed — ray-cast beams are future work).  Blocking
    fixtures (barriers) keep their specialized one-per-cell store."""
    kind: str
    payload: object


class RoomCells:
    """One room's terrain + fixtures.  Sparse: only water terrain and
    cells with fixtures are stored; everything else is bare floor.
    One barrier per cell (a placement rule, not a container limit)."""

    def __init__(self):
        self._water = {}        # (c, r) -> water_room node (or None)
        self._barriers = {}     # (c, r) -> Barrier, insertion-ordered
        self._bridges = set()   # (c, r) with a Bridge fixture
        self._items = {}        # (c, r) -> [Item, ...], insertion-ordered
        self._fixtures = {}     # (c, r) -> [Fixture, ...], insertion-ordered

    # ── Queries ───────────────────────────────────────────────────────────────

    def terrain(self, c, r):
        return Terrain.WATER if (c, r) in self._water else Terrain.FLOOR

    def is_water(self, c, r):
        return (c, r) in self._water

    def water_room(self, c, r):
        return self._water.get((c, r))

    def water_tiles(self):
        return iter(self._water)

    def barrier(self, c, r):
        return self._barriers.get((c, r))

    def barriers(self, kind=None):
        """Iterate ((c, r), barrier), insertion order (= room-data order)."""
        for pos, b in self._barriers.items():
            if kind is None or b.kind == kind:
                yield pos, b

    def bridge(self, c, r):
        return (c, r) in self._bridges

    def blocked(self, c, r, channels=frozenset()):
        """THE barrier/terrain passability semantics (spec 0048 U1):
        a blocking barrier (gates consult the high channels) or unbridged
        water.  Bounds and occupants (pushable blocks) are the caller's
        layers — the runtime folds in the latched channel state and the
        block list, the push-puzzle validator uses channels=∅ (all gates
        closed) and its own block set."""
        b = self._barriers.get((c, r))
        if b is not None and b.blocks(channels):
            return True
        return (c, r) in self._water and (c, r) not in self._bridges

    # ── Item layer (spec 0050 Q3) ─────────────────────────────────────────────

    def items(self, c, r):
        return tuple(self._items.get((c, r), ()))

    def items_of_kind(self, kind):
        """Iterate (pos, item), insertion order (= room-data order)."""
        for pos, items in self._items.items():
            for item in items:
                if item.kind == kind:
                    yield pos, item

    def add_item(self, pos, item):
        self._items.setdefault(pos, []).append(item)

    def remove_item(self, pos, item):
        bucket = self._items.get(pos)
        if bucket and item in bucket:
            bucket.remove(item)
            if not bucket:
                del self._items[pos]

    # ── Generic fixture layer (spec 0052 G2) ──────────────────────────────────

    def fixtures_of_kind(self, kind):
        """Iterate ((c, r), fixture), insertion order (= room-data order)."""
        for pos, fixtures in self._fixtures.items():
            for fixture in fixtures:
                if fixture.kind == kind:
                    yield pos, fixture

    def add_fixture(self, pos, fixture):
        self._fixtures.setdefault(pos, []).append(fixture)

    def remove_fixture(self, pos, fixture):
        bucket = self._fixtures.get(pos)
        if bucket and fixture in bucket:
            bucket.remove(fixture)
            if not bucket:
                del self._fixtures[pos]

    # ── Mutators ──────────────────────────────────────────────────────────────

    def set_barrier(self, pos, barrier):
        self._barriers[pos] = barrier

    def remove_barrier(self, pos):
        self._barriers.pop(pos, None)

    def add_bridge(self, pos):
        self._bridges.add(pos)


def _exit_tiles(exits):
    """Border positions opened by exit keys '{side}_{pos}'."""
    tiles = set()
    for exit_key in exits:
        side, pos_str = exit_key.rsplit('_', 1)
        pos = int(pos_str)
        if side == 'left':
            tiles.add((0, pos))
        elif side == 'right':
            tiles.add((COLS - 1, pos))
        elif side == 'top':
            tiles.add((pos, 0))
        elif side == 'bottom':
            tiles.add((pos, ROWS - 1))
    return tiles


def _parse_walls(cells, room_data):
    for pos, wall_type in parse_level_walls(room_data['walls']).items():
        cells.set_barrier(pos, Barrier(wall_type))


def _parse_doors(cells, room_data):
    for dc, dr, colour in room_data.get('locked_doors', []):
        cells.set_barrier((dc, dr), Barrier('door', colour=colour))


def _parse_gates(cells, room_data):
    for gc, gr, gate_id in room_data.get('gates', []):
        cells.set_barrier((gc, gr), Barrier('gate', channel=gate_id))


def _parse_water(cells, room_data):
    water_room_map = {tuple(k): v
                      for k, v in room_data.get('water_tile_room', {}).items()}
    for tile in room_data.get('water_tiles', []):
        pos = tuple(tile)
        cells._water[pos] = water_room_map.get(pos)


def _parse_items(kind, dict_key):
    def parse(cells, room_data):
        for c, r, payload in room_data.get(dict_key, []):
            cells.add_item((c, r), Item(kind, payload))
    return parse


def _parse_plates(cells, room_data):
    for pc, pr, channel in room_data.get('pressure_plates', []):
        cells.add_fixture((pc, pr), Fixture('plate', channel))


def _parse_nozzles(cells, room_data):
    for jet in room_data.get('flame_jets', []):
        jet['_tile_set'] = frozenset(tuple(t) for t in jet['tiles'])
        source = tuple(jet.get('source', jet['tiles'][0]))
        cells.add_fixture(source, Fixture('flame_nozzle', jet))


def _parse_entrance(cells, room_data):
    """The level entrance (spec 0066): an openable gate barrier on the
    reserved ENTRANCE_CHANNEL, overwriting the border wall the border loop
    laid at that tile.  Closed (channel low) it blocks and bumps inert like
    the border; award completion latches the channel high to open it."""
    ent = room_data.get('entrance')
    if ent is not None:
        cells.set_barrier(tuple(ent), Barrier('gate', channel=ENTRANCE_CHANNEL))


# The parse registry (spec 0052 G1): one entry per cells-parsed room-dict
# content key.  Occupants (pushable_blocks, enemy_starts, patrol_enemies)
# belong to Room.from_data; tile_owner/dead_squares/exits are room
# metadata handled elsewhere.  Adding a content kind = adding one entry.
CONTENT_PARSERS = (
    ('walls',           _parse_walls),
    ('locked_doors',    _parse_doors),
    ('gates',           _parse_gates),
    ('water_tiles',     _parse_water),
    ('treasures',       _parse_items('treasure', 'treasures')),
    ('materials',       _parse_items('material', 'materials')),
    ('keys',            _parse_items('key', 'keys')),
    ('pressure_plates', _parse_plates),
    ('flame_jets',      _parse_nozzles),
    ('entrance',        _parse_entrance),
)


def build_room_cells(room_data):
    """THE one parser from a room dict to the cell model: border (minus
    exit gaps), then the CONTENT_PARSERS registry in order.  Insertion
    order (border, walls, doors, gates) makes later entries win a cell —
    a door on a border exit tile is a door barrier, exactly as the old
    grid+overlay semantics resolved it."""
    cells = RoomCells()

    exit_gaps = _exit_tiles(room_data.get('exits', {}))
    for c in range(COLS):
        for r in (0, ROWS - 1):
            if (c, r) not in exit_gaps:
                cells.set_barrier((c, r), Barrier('border'))
    for r in range(1, ROWS - 1):
        for c in (0, COLS - 1):
            if (c, r) not in exit_gaps:
                cells.set_barrier((c, r), Barrier('border'))

    for _key, parse in CONTENT_PARSERS:
        parse(cells, room_data)

    return cells
