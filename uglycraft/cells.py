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
    door(colour,channel)  opens on a key-match bump by latching its channel
    gate(channel)         blocks iff its channel is low

Passability is NOT answered here: World.blocked(c, r) folds barrier,
terrain/bridge, and the occupant block list together, because the latched
channel state and the blocks live on the World.  This module is pygame-free
(pinned by the spec-0045 import-isolation test via world.py).
"""
from dataclasses import dataclass
from enum import Enum, auto

from collections import deque

from uglycraft.constants import (COLS, ROWS, ENTRANCE_CHANNEL, WALL_BUMPS,
                       WALL_HITS_TO_BREAK, WALL_STONE, WALL_WOODEN)


_DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def safe_block_positions(floor, plate):
    """Block positions in `floor` from which the block can be pushed to `plate`
    by a player *also confined to `floor`* (spec 0068).

    This is a reverse Sokoban with full player-zone tracking: a pull is legal
    only when the player can actually WALK — around the block, within `floor` —
    to the tile it must push from.  `floor` is the room's own walkable tiles;
    wall openings, gates and doors are NOT part of it, so the player can never
    stand "in the doorway" to push a block off the adjacent wall.  Because the
    block is confined and the walls are static, the result is a fixed set.

    State = (block position, the player's connected component of `floor − block`).
    Reverse step from (X, C): a forward push ended at X from X−d with the player
    standing at X−2d; it is legal only if X−d and X−2d are floor tiles and the
    player ended at X−d inside the current component C.  Predecessor state is
    (X−d, component of `floor − {X−d}` containing X−2d)."""
    if plate not in floor:
        return frozenset()

    comp_cache = {}

    def zones(block):
        """Map every tile of `floor − {block}` to its connected component."""
        parts = comp_cache.get(block)
        if parts is None:
            parts = {}
            remaining = floor - {block}
            seen = set()
            for t in remaining:
                if t in seen:
                    continue
                comp = []
                dq = deque([t])
                seen.add(t)
                while dq:
                    c, r = dq.popleft()
                    comp.append((c, r))
                    for dc, dr in _DIRS:
                        n = (c + dc, r + dr)
                        if n in remaining and n not in seen:
                            seen.add(n)
                            dq.append(n)
                fc = frozenset(comp)
                for m in comp:
                    parts[m] = fc
            comp_cache[block] = parts
        return parts

    safe = {plate}
    visited = set()
    q = deque()
    for comp in set(zones(plate).values()):
        state = (plate, comp)
        visited.add(state)
        q.append(state)
    while q:
        (bx, by), comp = q.popleft()
        for dc, dr in _DIRS:
            b = (bx - dc, by - dr)          # predecessor block position
            stood = (bx - 2 * dc, by - 2 * dr)  # player stood to push it
            if b not in floor or stood not in floor:
                continue
            if b not in comp:               # player ends on b — must be reachable now
                continue
            comp_pred = zones(b).get(stood)
            if comp_pred is None:
                continue
            state = (b, comp_pred)
            if state not in visited:
                visited.add(state)
                q.append(state)
                safe.add(b)
    return frozenset(safe)


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
        # A channelled barrier (gate or door) is open iff its channel is
        # latched high; every other barrier always blocks.  Spec 0077 unifies
        # doors with gates — a door is a gate opened by a key bump, its
        # door_id the channel latched on open.
        if self.channel is not None:
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
    fixtures (barriers) keep their specialized one-per-cell store.

    A 'plate' also owns `safe_tiles` (spec 0068): the room-floor tiles from
    which a block can still be pushed to it — everything else is a doom tile.
    Empty for non-plate fixtures."""
    kind: str
    payload: object
    safe_tiles: frozenset = frozenset()


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
    for dc, dr, colour, *rest in room_data.get('locked_doors', []):
        # The door's channel is the generator-minted door_id when present,
        # else a position-derived id for single-room hand-authored data (whose
        # tiles are unique, so it cannot collide).  Spec 0077: opening the door
        # latches this channel high; blocks() then derives passability from it.
        channel = rest[0] if (rest and rest[0] is not None) else f'door_{dc}_{dr}'
        cells.set_barrier((dc, dr),
                          Barrier('door', colour=colour, channel=channel))


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
    """Add each plate fixture and compute its `safe_tiles` (spec 0068): the
    tiles of the plate's OWN room floor from which a block can still be pushed
    to it by a player confined to that same room floor.

    The room floor is the plate's `tile_owner` tiles minus every opening the
    player must not stand in to push (walls, gates, doors, the entrance) — a
    doorway is a way out, not a push-stand tile."""
    plates = room_data.get('pressure_plates', [])
    if not plates:
        return
    walls = room_data.get('walls', {})
    owner = room_data.get('tile_owner', {})
    openings = set(walls)
    for c, r, *_ in room_data.get('gates', []):
        openings.add((c, r))
    for c, r, *_ in room_data.get('locked_doors', []):
        openings.add((c, r))
    ent = room_data.get('entrance')
    if ent is not None:
        openings.add(tuple(ent))
    interior = {(c, r) for c in range(1, COLS - 1) for r in range(1, ROWS - 1)}
    for pc, pr, channel in plates:
        if owner:
            o = owner.get((pc, pr))
            floor = frozenset(t for t, oo in owner.items()
                              if oo == o and t not in openings)
        else:
            floor = frozenset(interior - openings)
        safe = safe_block_positions(floor, (pc, pr))
        cells.add_fixture((pc, pr), Fixture('plate', channel, safe))


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
