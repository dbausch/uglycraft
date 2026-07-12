"""Content-registry tests (spec 0052, world model Stage 6) — pygame-free.

Red-first: the generic fixture layer, CONTENT_PARSERS, and Block
occupants do not exist when these are written.  The behaviour locks for
plates/flames/blocks live in test_dispatch.py and carry over unchanged.
"""
import random

import pytest

import world as world_mod
from world import World
from tests import act2_fixtures as fx

DT = 33


def _all_kinds_room():
    """A room dict exercising every registry-parsed content kind."""
    jet = {'tiles': [(18, 8), (19, 8)], 'source': (17, 8),
           'dir': (1, 0), 'on_ms': 1000, 'off_ms': 1000}
    return fx._room(
        {(11, 8): 'stone', (11, 9): 'wooden', (11, 10): 'reinforced'},
        locked_doors=[(12, 8, 'red')],
        gates=[(12, 9, 'gx')],
        water_tiles=[(13, 8)],
        water_tile_room={(13, 8): 'w1'},
        treasures=[(5, 5, 1)],
        materials=[(5, 6, 'planks')],
        keys=[(5, 7, 'red')],
        pressure_plates=[(4, 8, 'gx')],
        flame_jets=[jet],
        exits={'right_8': 'g2'},
    )


# ── G1: the parse registry ────────────────────────────────────────────────────

def test_content_parsers_cover_all_cell_content_keys():
    """One registry entry per cells-parsed room-dict key.  Occupants
    (pushable_blocks, enemy_starts, patrol_enemies) and room metadata
    (tile_owner, dead_squares, exits) are deliberately NOT here — they
    belong to Room.from_data / border handling."""
    from cells import CONTENT_PARSERS
    assert [key for key, _ in CONTENT_PARSERS] == [
        'walls', 'locked_doors', 'gates', 'water_tiles',
        'treasures', 'materials', 'keys',
        'pressure_plates', 'flame_jets', 'entrance',
    ]


def test_build_room_cells_parses_every_kind():
    from cells import build_room_cells
    cells = build_room_cells(_all_kinds_room())
    assert cells.barrier(11, 8).kind == 'stone'
    assert cells.barrier(12, 8).kind == 'door'
    assert cells.barrier(12, 9).kind == 'gate'
    assert cells.is_water(13, 8) and cells.water_room(13, 8) == 'w1'
    assert [i.kind for _, i in cells.items_of_kind('treasure')] == ['treasure']
    (plate_entry,) = cells.fixtures_of_kind('plate')
    assert plate_entry == ((4, 8), plate_entry[1])
    assert plate_entry[1].payload == 'gx'
    ((npos, nozzle),) = list(cells.fixtures_of_kind('flame_nozzle'))
    assert npos == (17, 8)                       # the jet's source tile
    assert nozzle.payload['tiles'] == [(18, 8), (19, 8)]
    assert nozzle.payload['_tile_set'] == frozenset({(18, 8), (19, 8)})
    assert cells.barrier(29, 8) is None          # exit gap still opened


# ── G2: fixture layer + Room compat views ─────────────────────────────────────

def test_room_plates_and_flame_jets_are_views_over_cells():
    from rooms import Room
    room = Room.from_data('g1', _all_kinds_room(), 'easy')
    assert room.plates == [(4, 8, 'gx')]
    (jet,) = room.flame_jets
    assert jet['_tile_set'] == frozenset({(18, 8), (19, 8)})
    # views, not stored fields: mutating cells is enough
    for pos, f in list(room.cells.fixtures_of_kind('plate')):
        room.cells.remove_fixture(pos, f)
    assert room.plates == []


# ── G3: blocks are occupants with identity ────────────────────────────────────

def test_blocks_are_objects_with_identity():
    from rooms import Room
    from entities import Block
    data = fx._room({}, pushable_blocks=[(6, 8), (9, 9)])
    room = Room.from_data('g1', data, 'easy')
    assert all(isinstance(b, Block) for b in room.blocks)
    assert room.block_positions() == [(6, 8), (9, 9)]
    assert room.blocks_initial == ((6, 8), (9, 9))
    assert room.block_at(6, 8) is room.blocks[0]
    assert room.block_at(1, 1) is None


def test_push_moves_the_same_block_object():
    def make():
        return fx._level({'main': fx._room(
            {}, pushable_blocks=[(6, 8)])}, player=(8, 8))
    orig = world_mod.get_level, world_mod.regenerate_level
    world_mod.get_level = lambda n, progress=None: make()
    world_mod.regenerate_level = lambda n: make()
    try:
        random.seed(42)
        w = World('easy')
        block = w.room.blocks[0]
        w.player.col, w.player.row = 7, 8
        w.try_move(-1, 0, 1)                    # push left: (6,8) -> (5,8)
        assert w.room.blocks[0] is block        # same object moved
        assert (block.col, block.row) == (5, 8)
        assert w.blocked(5, 8) and not w.blocked(6, 8)
    finally:
        world_mod.get_level, world_mod.regenerate_level = orig
