"""Room-object tests (spec 0051, refactor Stage 5) — pygame-free.

Red-first: the Room class does not exist when these are written.  The
persistence/transition behaviour locks live in test_dispatch.py and
test_world.py and carry over unchanged — these tests pin the new API
and the lazy/visited semantics.
"""
import random

import pytest

import world as world_mod
from world import World
from constants import WALL_WOODEN
from tests import act2_fixtures as fx

DT = 33


def _world(make_level, seed=42, difficulty='easy'):
    orig = world_mod.get_level, world_mod.regenerate_level
    world_mod.get_level = lambda n, progress=None: make_level()
    world_mod.regenerate_level = lambda n: make_level()
    random.seed(seed)
    w = World(difficulty)
    w.drain_events()
    return w, orig


def _restore(orig):
    world_mod.get_level, world_mod.regenerate_level = orig


def _cross(w, dcol, key=9):
    w.try_move(dcol, 0, key)
    w.key_released(key)
    w.try_move(dcol, 0, key)
    w.key_released(key)


ROOM_DATA_KEYS = dict(
    walls={(11, 8): WALL_WOODEN},
    enemy_starts=[(20, 3), (21, 4), (22, 5, 'forge_ogre')],
    patrol_enemies=[{'start': (25, 10), 'waypoints': [(25, 10), (25, 12)]}],
    pushable_blocks=[(6, 8)],
    pressure_plates=[(4, 8, 'g1')],
    dead_squares=[(2, 2)],
)


def _room_dict():
    return fx._room({(11, 8): WALL_WOODEN}, **{
        k: v for k, v in ROOM_DATA_KEYS.items() if k != 'walls'})


# ── Room.from_data (red until R1) ─────────────────────────────────────────────

def test_from_data_populates_fields():
    from rooms import Room
    data = _room_dict()
    room = Room.from_data('g1', data, 'easy')
    assert room.key == 'g1'
    assert room.data is data
    assert room.cells.barrier(11, 8).kind == WALL_WOODEN
    assert room.blocks == [(6, 8)]
    assert room.blocks_initial == ((6, 8),)
    assert room.plates == [(4, 8, 'g1')]
    assert (2, 2) in room.dead_squares
    assert room.tile_owner == {}


def test_from_data_enemy_selection_by_difficulty():
    from rooms import Room
    from entities import ForgeOgre, PatrolEnemy
    easy = Room.from_data('g1', _room_dict(), 'easy')
    # EASY: all specials + one regular chaser + one patrol
    kinds = [type(e).__name__ for e in easy.enemies]
    assert kinds.count('ForgeOgre') == 1
    assert kinds.count('PatrolEnemy') == 1
    assert kinds.count('Enemy') == 1
    hard = Room.from_data('g1', _room_dict(), 'hard')
    kinds = [type(e).__name__ for e in hard.enemies]
    assert kinds.count('Enemy') == 2          # all regular chasers
    assert kinds.count('ForgeOgre') == 1
    assert kinds.count('PatrolEnemy') == 1


# ── Lazy identity persistence (red until R2/R3) ───────────────────────────────

def _two_grids():
    g1 = fx._room({}, pushable_blocks=[(6, 8)],
                  pressure_plates=[(4, 8, 'x1')],
                  exits={'right_8': 'g2'})
    g2 = fx._room({}, exits={'left_8': 'g1'})
    return fx._level({'g1': g1, 'g2': g2}, start='g1', player=(10, 8))


def test_rooms_persist_by_identity():
    w, orig = _world(_two_grids)
    try:
        first = w.room
        assert w._rooms['g1'] is first
        assert w._current_room == 'g1'        # property over room.key
        w.player.col, w.player.row = 28, 8
        _cross(w, 1)                          # -> g2 (created lazily)
        assert w.room is w._rooms['g2']
        assert set(w._rooms) == {'g1', 'g2'}
        w.player.col, w.player.row = 1, 8
        _cross(w, -1)                         # -> back
        assert w.room is first                # SAME object, no copying
    finally:
        _restore(orig)


def test_reset_blocks_covers_visited_only_and_unvisited_stay_initial():
    w, orig = _world(_two_grids)
    try:
        w.room.blocks[:] = [(9, 9)]           # moved in g1 (visited)
        w._reset_blocks()                     # death reset
        assert w.room.blocks == [(6, 8)]      # back at initial
        assert 'g2' not in w._rooms           # unvisited: nothing to reset
        w.player.col, w.player.row = 28, 8
        _cross(w, 1)                          # first entry AFTER the death
        assert w.room.key == 'g2'             # builds from pristine data
    finally:
        _restore(orig)


def test_roomstate_is_gone():
    import rooms
    assert not hasattr(rooms, 'RoomState')
    w, orig = _world(_two_grids)
    try:
        assert not hasattr(w, '_room_states')
        assert not hasattr(w, '_room_blocks')
        assert not hasattr(w, '_room_plates')
    finally:
        _restore(orig)
