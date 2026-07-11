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
terrain/bridge, and the occupant block list together, because gate state
(_gate_open) and blocks live on the World.  This module is pygame-free
(pinned by the spec-0045 import-isolation test via world.py).
"""
from dataclasses import dataclass
from enum import Enum, auto

from constants import COLS, ROWS
from rooms import parse_level_walls


class Terrain(Enum):
    FLOOR = auto()
    WATER = auto()


@dataclass
class Barrier:
    """Cell-filling fixture: partitions the grid, entities bump into it.
    Kinds 'stone'/'wooden'/'reinforced' equal the WALL_* constants, so
    WALL_BUMPS.get(kind, WALL_HITS_TO_BREAK) yields today's exact hit
    counts (placed walls fall through to the default 3)."""
    kind: str                   # 'border' | 'reinforced' | 'stone' | 'wooden'
                                #   | 'placed' | 'door' | 'gate'
    colour: str = None          # doors
    channel: str = None         # gates: the gate_id
    hits: int = 0               # bump damage (breakable kinds)

    def blocks(self, gate_open=frozenset()):
        if self.kind == 'gate':
            return self.channel not in gate_open
        return True


class RoomCells:
    """One room's terrain + fixtures.  Sparse: only water terrain and
    cells with fixtures are stored; everything else is bare floor.
    One barrier per cell (a placement rule, not a container limit)."""

    def __init__(self):
        self._water = {}        # (c, r) -> water_room node (or None)
        self._barriers = {}     # (c, r) -> Barrier, insertion-ordered
        self._bridges = set()   # (c, r) with a Bridge fixture

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

    def blocked(self, c, r, gate_open=frozenset()):
        """THE barrier/terrain passability semantics (spec 0048 U1):
        a blocking barrier (gates consult gate_open) or unbridged water.
        Bounds and occupants (pushable blocks) are the caller's layers —
        the runtime folds in live gate state and the block list, the
        push-puzzle validator uses gate_open=∅ and its own block set."""
        b = self._barriers.get((c, r))
        if b is not None and b.blocks(gate_open):
            return True
        return (c, r) in self._water and (c, r) not in self._bridges

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


def build_room_cells(room_data):
    """THE one parser from a room dict to the cell model.

    Insertion order (border, level walls, doors, gates) makes later
    entries win a cell — a door on a border exit tile is a door barrier,
    exactly as the old grid+overlay semantics resolved it."""
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

    for pos, wall_type in parse_level_walls(room_data['walls']).items():
        cells.set_barrier(pos, Barrier(wall_type))

    for dc, dr, colour in room_data.get('locked_doors', []):
        cells.set_barrier((dc, dr), Barrier('door', colour=colour))

    for gc, gr, gate_id in room_data.get('gates', []):
        cells.set_barrier((gc, gr), Barrier('gate', channel=gate_id))

    water_room_map = {tuple(k): v
                      for k, v in room_data.get('water_tile_room', {}).items()}
    for tile in room_data.get('water_tiles', []):
        pos = tuple(tile)
        cells._water[pos] = water_room_map.get(pos)

    return cells
