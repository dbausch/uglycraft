"""Unit tests for the layered cell model (spec 0047 T1/T6) — pygame-free.

Red-first: cells.py does not exist when these are written.  They pin the
one parser (build_room_cells) and the model's queries and mutators; the
World-level behaviour that folds gate state and blocks into passability
is covered in tests/test_world.py.
"""
import pytest

from uglycraft.constants import COLS, ROWS
from uglycraft.cells import Barrier, Terrain, build_room_cells


ROOM = {
    'walls': {(5, 5): 'stone', (6, 5): 'wooden', (7, 5): 'reinforced'},
    'exits': {'right_8': 'g2', 'top_4': 'g3'},
    'locked_doors': [(15, 8, 'red'), (29, 8, 'blue')],   # second on the exit tile
    'gates': [(10, 4, 'gate_1')],
    'water_tiles': [(20, 7), (20, 8)],
    'water_tile_room': {(20, 7): 'w1', (20, 8): 'w1'},
}


@pytest.fixture
def cells():
    return build_room_cells(ROOM)


def test_level_walls_become_barriers(cells):
    assert cells.barrier(5, 5).kind == 'stone'
    assert cells.barrier(6, 5).kind == 'wooden'
    assert cells.barrier(7, 5).kind == 'reinforced'
    assert cells.barrier(8, 5) is None                  # plain floor


def test_act1_wall_set_defaults_to_stone():
    cells = build_room_cells({'walls': {(3, 3)}})       # set form (Act 1)
    assert cells.barrier(3, 3).kind == 'stone'


def test_border_barriers_with_exit_gaps(cells):
    assert cells.barrier(0, 0).kind == 'border'
    assert cells.barrier(14, 0).kind == 'border'
    assert cells.barrier(0, ROWS - 1).kind == 'border'
    assert cells.barrier(4, 0) is None                  # top_4 exit gap
    # right_8 exit gap carries a door instead of border
    assert cells.barrier(COLS - 1, 8).kind == 'door'
    assert cells.barrier(COLS - 1, 8).colour == 'blue'


def test_door_and_gate_barriers(cells):
    door = cells.barrier(15, 8)
    assert door.kind == 'door' and door.colour == 'red'
    gate = cells.barrier(10, 4)
    assert gate.kind == 'gate' and gate.channel == 'gate_1'


def test_gate_blocks_iff_channel_low(cells):
    gate = cells.barrier(10, 4)
    assert gate.blocks(frozenset())
    assert not gate.blocks(frozenset({'gate_1'}))
    assert cells.barrier(5, 5).blocks(frozenset({'gate_1'}))   # walls always


def test_water_terrain_and_bridge(cells):
    assert cells.terrain(20, 7) is Terrain.WATER
    assert cells.terrain(1, 1) is Terrain.FLOOR
    assert cells.water_room(20, 7) == 'w1'
    assert cells.is_water(20, 8) and not cells.is_water(19, 8)
    assert list(cells.water_tiles()) == [(20, 7), (20, 8)]
    assert not cells.bridge(20, 7)
    cells.add_bridge((20, 7))
    assert cells.bridge(20, 7) and not cells.bridge(20, 8)


def test_break_and_place_mutators(cells):
    cells.remove_barrier((5, 5))
    assert cells.barrier(5, 5) is None                  # floor was underneath
    cells.set_barrier((8, 8), Barrier('placed'))
    assert cells.barrier(8, 8).kind == 'placed'
    assert cells.barrier(8, 8).hits == 0


def test_damage_lives_on_the_barrier(cells):
    b = cells.barrier(5, 5)
    b.hits += 1
    assert cells.barrier(5, 5).hits == 1                # same object


def test_blocked_query_folds_barrier_and_water(cells):
    """RoomCells.blocked is THE passability semantics (spec 0048 U1):
    blocking barrier (gates consult gate_open) or unbridged water."""
    assert cells.blocked(5, 5)                             # stone wall
    assert not cells.blocked(8, 8)                         # bare floor
    assert cells.blocked(15, 8)                            # locked door
    assert cells.blocked(10, 4)                            # gate, channel low
    assert not cells.blocked(10, 4, frozenset({'gate_1'}))
    assert cells.blocked(20, 7)                            # water
    cells.add_bridge((20, 7))
    assert not cells.blocked(20, 7)                        # bridged
    assert cells.blocked(20, 8)                            # other water tile


def test_barrier_iteration_in_insertion_order(cells):
    doors = [(pos, b.colour) for pos, b in cells.barriers('door')]
    assert doors == [((15, 8), 'red'), ((COLS - 1, 8), 'blue')]
    gates = [(pos, b.channel) for pos, b in cells.barriers('gate')]
    assert gates == [((10, 4), 'gate_1')]
