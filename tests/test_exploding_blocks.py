"""Spec 0068 — doomed push-blocks explode and respawn (BL-37).

RED first: these pin the world-level behaviour (pygame-free) of the new
safe-tile detection, the confinement rule, the fuse/explosion, the score
penalty, and the removal of the on-death block reset.  Rendering/sound are
verified manually (presentation).

Geometry of the isolated puzzle fixture (`_puzzle_level`), a translation of
spec 0068 diagram (1) — plate in the corner of a 4x3 room:

        c2 c3 c4 c5
    r2   T  S  S  x
    r3   S  S  S  x
    r4   x  x  x  x         # = reinforced ring around it

  T plate=(2,2), block start=(3,2) (safe); (5,2) and the whole r4 are unsafe.
"""
import random

import pytest

import world as world_mod
import constants
from world import World
from entities import Block
from constants import WALL_REINFORCED

KEY = 7
DT = 33


# ── plumbing (mirrors tests/test_dispatch.py) ─────────────────────────────────

def _world(make_level, seed=42):
    orig = world_mod.get_level, world_mod.regenerate_level
    world_mod.get_level = lambda n, progress=None: make_level()
    world_mod.regenerate_level = lambda n: make_level()
    random.seed(seed)
    w = World('easy')
    w.drain_events()
    return w, orig


def _restore(orig):
    world_mod.get_level, world_mod.regenerate_level = orig


def _room(walls, **kw):
    room = {'walls': walls, 'enemy_starts': [], 'treasures': [],
            'materials': [], 'keys': [], 'locked_doors': [],
            'pushable_blocks': [], 'pressure_plates': [], 'gates': [],
            'water_tiles': [], 'water_tile_room': {}, 'flame_jets': [],
            'exits': {}, 'tile_owner': {}, 'dead_squares': []}
    room.update(kw)
    return room


def _push(w, dcol, drow, key=KEY):
    moved = w.try_move(dcol, drow, key)
    w.key_released(key)
    return moved


def _kinds(events):
    return [e[0] for e in events]


# ── fixtures ──────────────────────────────────────────────────────────────────

def _ring(c0, c1, r0, r1):
    """Reinforced walls forming a box just outside cols c0..c1, rows r0..r1."""
    w = {}
    for c in range(c0 - 1, c1 + 2):
        w[(c, r0 - 1)] = WALL_REINFORCED
        w[(c, r1 + 1)] = WALL_REINFORCED
    for r in range(r0 - 1, r1 + 2):
        w[(c0 - 1, r)] = WALL_REINFORCED
        w[(c1 + 1, r)] = WALL_REINFORCED
    return w


def _puzzle_level():
    """Isolated 4x3 puzzle room (cols 2-5, rows 2-4), plate corner (2,2),
    block (3,2)."""
    owner = {(c, r): 'puzzle' for c in range(2, 6) for r in range(2, 5)}
    main = _room(_ring(2, 5, 2, 4), tile_owner=owner,
                 pressure_plates=[(2, 2, 'g1')],
                 pushable_blocks=[(3, 2)])
    return {'rooms': {'main': main}, 'start_room': 'main',
            'player_start': (5, 4)}


def _two_owner_level():
    """One grid, two owners meeting with NO wall between: room A (cols 2-5)
    and room B (cols 6-9), rows 2-4. Block in A at (5,3), plate in A."""
    owner = {}
    for c in range(2, 6):
        for r in range(2, 5):
            owner[(c, r)] = 'A'
    for c in range(6, 10):
        for r in range(2, 5):
            owner[(c, r)] = 'B'
    main = _room(_ring(2, 9, 2, 4), tile_owner=owner,
                 pressure_plates=[(2, 3, 'g1')],
                 pushable_blocks=[(5, 3)])
    return {'rooms': {'main': main}, 'start_room': 'main',
            'player_start': (8, 4)}


def _plate(w):
    (_pos, f), = w.room.cells.fixtures_of_kind('plate')
    return f


# ── safe-tile representation (on the plate object) ────────────────────────────

def test_plate_owns_safe_tiles():
    w, orig = _world(_puzzle_level)
    try:
        safe = _plate(w).safe_tiles
        assert (2, 2) in safe          # the plate itself (seed)
        assert (3, 2) in safe          # block's solvable start
        assert (5, 2) not in safe      # far column — unsafe
        assert (3, 4) not in safe      # bottom row — unsafe
        assert w._safe_tiles == w.room.safe_tile_set == safe
    finally:
        _restore(orig)


# ── detection: leaving the safe area ignites ──────────────────────────────────

def test_push_out_of_safe_area_ignites():
    w, orig = _world(_puzzle_level)
    try:
        w.player.col, w.player.row = (2, 2)
        assert _push(w, 1, 0)                  # (3,2)->(4,2), safe
        assert w.room.blocks[0].fuse is None
        w.drain_events()
        assert _push(w, 1, 0)                  # (4,2)->(5,2), UNSAFE
        assert w.room.block_positions() == [(5, 2)]
        assert w.room.blocks[0].fuse == constants.BLOCK_FUSE_MS
        assert 'block_fuse_lit' in _kinds(w.drain_events())
    finally:
        _restore(orig)


def test_push_within_safe_area_no_ignite():
    w, orig = _world(_puzzle_level)
    try:
        w.player.col, w.player.row = (2, 2)
        assert _push(w, 1, 0)                  # (3,2)->(4,2), safe
        assert w.room.blocks[0].fuse is None
        assert 'block_fuse_lit' not in _kinds(w.drain_events())
    finally:
        _restore(orig)


def test_block_on_plate_never_ignites():
    w, orig = _world(_puzzle_level)
    try:
        w.room.blocks[0].col, w.room.blocks[0].row = (2, 2)   # park on plate
        w._light_doomed_fuses()
        assert w.room.blocks[0].fuse is None
    finally:
        _restore(orig)


# ── confinement: can't be pushed out of the room ──────────────────────────────

def test_confinement_refused_at_owner_boundary():
    w, orig = _world(_two_owner_level)
    try:
        w.player.col, w.player.row = (4, 3)
        # block (5,3) is owner A; (6,3) is owner B — the push must be refused
        assert not _push(w, 1, 0)
        assert w.room.block_positions() == [(5, 3)]
        assert w.room.blocks[0].fuse is None       # refused push never ignites
    finally:
        _restore(orig)


# ── fused block stays movable but can't re-enter the safe area ────────────────

def test_fused_block_stays_movable_but_stays_unsafe():
    w, orig = _world(_puzzle_level)
    try:
        w.player.col, w.player.row = (2, 2)
        _push(w, 1, 0)                             # ->(4,2)
        _push(w, 1, 0)                             # ->(5,2), ignites
        b = w.room.blocks[0]
        assert b.fuse == constants.BLOCK_FUSE_MS
        w.drain_events()
        # push it down along the unsafe far column: still moves, fuse unchanged
        assert _push(w, 0, 1)                      # (5,2)->(5,3)
        assert w.room.block_positions() == [(5, 3)]
        assert b.fuse == constants.BLOCK_FUSE_MS   # not re-lit, not cancelled
        assert (5, 3) not in w._safe_tiles         # never back in the safe area
    finally:
        _restore(orig)


# ── detonation: penalty + respawn ─────────────────────────────────────────────

def test_detonate_deducts_500_and_respawns():
    w, orig = _world(_puzzle_level)
    try:
        w.score = 1000
        w.player.col, w.player.row = (2, 2)
        _push(w, 1, 0)
        _push(w, 1, 0)                             # block at (5,2), fused
        w.drain_events()
        kinds = []
        for _ in range(constants.BLOCK_FUSE_MS // DT + 3):
            w.update(DT)
            kinds += _kinds(w.drain_events())
        assert 'block_exploded' in kinds
        assert w.score == 500                      # 1000 - 500
        assert w.room.block_positions() == [(3, 2)]   # back at start
        assert w.room.blocks[0].fuse is None
    finally:
        _restore(orig)


def test_detonate_penalty_floored_at_zero():
    w, orig = _world(_puzzle_level)
    try:
        w.score = 0
        w.player.col, w.player.row = (2, 2)
        _push(w, 1, 0)
        _push(w, 1, 0)
        for _ in range(constants.BLOCK_FUSE_MS // DT + 3):
            w.update(DT)
        assert w.score == 0                        # floored, never negative
    finally:
        _restore(orig)


# ── on death, blocks are NOT reset (Decision 6) ───────────────────────────────

def test_death_does_not_reset_blocks():
    w, orig = _world(_puzzle_level)
    try:
        w.room.blocks[0].col, w.room.blocks[0].row = (4, 2)   # moved off start
        assert w.lives >= 2
        w._lose_life()                             # non-fatal
        assert w.room.block_positions() == [(4, 2)]   # NOT reset to (3,2)
    finally:
        _restore(orig)


def test_reset_blocks_method_removed():
    w, orig = _world(_puzzle_level)
    try:
        assert not hasattr(w, '_reset_blocks')
    finally:
        _restore(orig)
