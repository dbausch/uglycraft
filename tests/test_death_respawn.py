"""Death respawn: reset player + all enemies to *safe* starts; no crafting on
the respawn tile (spec 0067 / BL-50, BL-51).

Red-first, world-level (pygame-free).  On any life loss every enemy in every
visited room is respawned to its start — but only when that start is
unblocked, clear of the player, and in the component the player reaches in
that room (anti-trap); otherwise it relocates into that component.  The
player returns to the start room.  A crafted wall cannot be placed on the
start room's player_start.
"""
import random

import pytest

import world as world_mod
from world import World
from constants import COLS, ROWS
from cells import Barrier
from crafting import CRAFT_BLOCK
from tests import act2_fixtures as fx

KEY = 7


# ── fixtures / helpers ────────────────────────────────────────────────────────

def _patch(level):
    orig = world_mod.get_level, world_mod.regenerate_level
    world_mod.get_level = lambda n, progress=None: level
    world_mod.regenerate_level = lambda n: level
    return orig


def _restore(orig):
    world_mod.get_level, world_mod.regenerate_level = orig


def _act1(walls=(), player=(1, 7), enemies=((28, 7),), entrance=(0, 7)):
    """Minimal Act 1 level dict (open room + chosen walls)."""
    return {'walls': set(walls), 'player_start': player,
            'enemy_starts': [tuple(e) for e in enemies], 'entrance': entrance}


def _world(level, difficulty='hard', seed=1234):
    orig = _patch(level)
    random.seed(seed)
    w = World(difficulty)      # __init__ starts level 1 = our patched level
    w.drain_events()
    return w, orig


def _kinds(events):
    return [e[0] for e in events]


def _cross(w, dcol):
    """Step onto the border exit tile, then press off-grid to transition."""
    w.try_move(dcol, 0, KEY); w.key_released(KEY)
    w.try_move(dcol, 0, KEY); w.key_released(KEY)


def _grid_owner(node, lo=1, hi=COLS - 1):
    return {(c, r): node for c in range(lo, hi) for r in range(1, ROWS - 1)}


def _two_grid(p=(2, 8)):
    """Two full grids g1<->g2 (border exit at row 8), one enemy each."""
    g1 = fx._room(set(), exits={'right_8': 'g2'}, tile_owner=_grid_owner('g1'),
                  enemy_starts=[(5, 5)])
    g2 = fx._room(set(), exits={'left_8': 'g1'}, tile_owner=_grid_owner('g2'),
                  enemy_starts=[(24, 5)])
    return fx._level({'g1': g1, 'g2': g2}, start='g1', player=p)


# ── BL-50: all enemies reset on death ─────────────────────────────────────────

def test_all_enemies_reset_to_start_on_death():
    w, orig = _world(_act1(enemies=((28, 7), (28, 3))))
    try:
        starts = [(e.col, e.row) for e in w.enemies]
        for i, e in enumerate(w.enemies):
            e.col, e.row = 10 + i, 10          # wander them off their starts
        w.lives = 5
        w._lose_life()
        assert w.lives == 4
        assert (w.player.col, w.player.row) == (1, 7)
        assert [(e.col, e.row) for e in w.enemies] == starts
    finally:
        _restore(orig)


def test_caught_enemy_resets_not_relocated_far():
    w, orig = _world(_act1(enemies=((28, 7),)))
    try:
        start = (w.enemies[0].col, w.enemies[0].row)
        w.enemies[0].col, w.enemies[0].row = 14, 7
        w.lives, w.shield = 5, False
        w._on_caught(w.enemies[0])
        assert w.lives == 4                              # life lost
        assert (w.enemies[0].col, w.enemies[0].row) == start
    finally:
        _restore(orig)


def test_shielded_catch_relocates_without_reset():
    """Lock: a shielded hit loses no life and just shoves the catcher away."""
    w, orig = _world(_act1(enemies=((28, 7),)))
    try:
        w.lives, w.shield, w._shield_timer = 5, True, 5000
        w.enemies[0].col, w.enemies[0].row = w.player.col + 1, w.player.row
        w._on_caught(w.enemies[0])
        assert w.lives == 5 and not w.shield
        e = w.enemies[0]
        assert abs(e.col - w.player.col) + abs(e.row - w.player.row) >= 2
    finally:
        _restore(orig)


# ── BL-50: safe respawn (blocked / adjacent / anti-trap) ──────────────────────

def test_blocked_start_relocates_off_the_wall():
    w, orig = _world(_act1(enemies=((28, 7),)))
    try:
        w.cells.set_barrier((28, 7), Barrier('placed'))   # wall on the start tile
        w.lives = 5
        w._lose_life()
        e = w.enemies[0]
        assert (e.col, e.row) != (28, 7)          # not inside the wall
        assert not w.blocked(e.col, e.row)
    finally:
        _restore(orig)


def test_never_respawns_on_or_next_to_player():
    w, orig = _world(_act1(player=(1, 7), enemies=((2, 7),)))
    try:
        w.lives = 5
        w._lose_life()
        e = w.enemies[0]
        assert abs(e.col - 1) + abs(e.row - 7) >= 2   # not on/adjacent to player
    finally:
        _restore(orig)


def test_anti_trap_sealed_home_relocates_into_reachable():
    walls = {(4, 5), (6, 5), (5, 4), (5, 6)}          # seal (5,5) into a pocket
    w, orig = _world(_act1(player=(1, 7), enemies=((5, 5),), walls=walls))
    try:
        w.lives = 5
        w._lose_life()
        e = w.enemies[0]
        pdist = w._bfs_from(w.player.col, w.player.row)
        assert (e.col, e.row) != (5, 5)               # not left sealed
        assert (e.col, e.row) in pdist                # reachable from the player
    finally:
        _restore(orig)


# ── BL-51: no crafting on the respawn tile ────────────────────────────────────

def test_no_block_placed_on_respawn_tile_act1():
    w, orig = _world(_act1(player=(1, 7)))
    try:
        w._block_credits = 1
        w.player.col, w.player.row = 1, 7             # standing on the respawn tile
        w.place()
        assert _kinds(w.drain_events()) == []         # nothing placed
        assert not w.blocked(1, 7)
        assert w._block_credits == 1                  # credit not consumed

        w.player.col, w.player.row = 3, 7             # control: elsewhere it works
        w.place()
        assert 'block_placed' in _kinds(w.drain_events())
        assert w.blocked(3, 7)
    finally:
        _restore(orig)


def test_no_block_placed_on_respawn_tile_act2():
    level = fx._level({'main': fx._room(set(), tile_owner=fx._owner())},
                      player=(10, 8))
    w, orig = _world(level)
    try:
        w.inventory.crafted[CRAFT_BLOCK] = 2
        w.inventory.active_item = CRAFT_BLOCK
        w.player.col, w.player.row = 10, 8            # the respawn tile
        w.place()
        assert _kinds(w.drain_events()) == []
        assert not w.blocked(10, 8)
        assert w.inventory.crafted[CRAFT_BLOCK] == 2   # item not consumed
    finally:
        _restore(orig)


# ── BL-50 / Decision 1: multi-grid ────────────────────────────────────────────

def test_act2_death_returns_to_start_room():
    w, orig = _world(_two_grid(p=(2, 8)))
    try:
        w.player.col, w.player.row = 28, 8
        _cross(w, 1)                                  # g1 -> g2
        assert w._current_room == 'g2'
        w.lives = 5
        w._lose_life()
        assert w._current_room == 'g1'                # back to the start grid
        assert (w.player.col, w.player.row) == (2, 8)
    finally:
        _restore(orig)


def test_enemies_in_all_visited_rooms_reset():
    w, orig = _world(_two_grid(p=(2, 8)))
    try:
        g1_enemy = w.enemies[0]
        g1_enemy.col, g1_enemy.row = 8, 8             # wander g1's enemy
        w.player.col, w.player.row = 28, 8
        _cross(w, 1)                                  # visit g2
        assert w._current_room == 'g2'
        g2_enemy = w.enemies[0]
        g2_enemy.col, g2_enemy.row = 20, 8            # wander g2's enemy
        w.lives = 5
        w._lose_life()
        assert (g1_enemy.col, g1_enemy.row) == (5, 5)   # both back at their starts
        assert (g2_enemy.col, g2_enemy.row) == (24, 5)
    finally:
        _restore(orig)
