"""Spec 0053 / BL-31 — entrance & player start anchored via grid zero.

Multi-grid graphs model the outside of the dungeon as grid zero at the
super-grid origin (0,0): the spanning tree never occupies it, the start
grid sits in the adjacent cell, and its face toward the origin
(graph.entrance_side) never carries a BORDER edge.  The level entrance
sits on that face, with the player start on the corridor tile directly
inside.
"""
import collections
import random

import pytest
from hypothesis import given, settings, strategies as st

from uglycraft import levels
from uglycraft.levelgraph import LevelGraph, EdgeType, NodeSize
from uglycraft.levellayout import build_level_dict, LayoutError
from tests.conftest import FS_ALL

COLS, ROWS = 30, 16
DELTA = {'right': (1, 0), 'left': (-1, 0), 'bottom': (0, 1), 'top': (0, -1)}
SIDES = frozenset(DELTA)


def _build(seed, gc):
    base = random.Random(seed)
    fs = {**FS_ALL, 'grid_count': gc}
    for _ in range(60):
        rng = random.Random(base.randint(0, 2 ** 31))
        g = LevelGraph.generate(fs, rng)
        try:
            return g, build_level_dict(g, rng=rng)
        except LayoutError:
            continue
    raise AssertionError(f"build never succeeded seed={seed} gc={gc}")


def _start_corridor(graph):
    return next(n for n, nd in graph.nodes.items() if nd.is_start)


def _border_sides(graph, corridor):
    """Sides of `corridor`'s grid that carry a BORDER edge."""
    sides = set()
    for e in graph.edges:
        if e.edge_type != EdgeType.BORDER:
            continue
        if e.node_a == corridor:
            sides.add(e.params['exit_side'])
        elif e.node_b == corridor:
            sides.add(e.params['entry_side'])
    return sides


def _side_of(tile):
    c, r = tile
    if c == 0:
        return 'left'
    if c == COLS - 1:
        return 'right'
    if r == 0:
        return 'top'
    if r == ROWS - 1:
        return 'bottom'
    return None


def _face(side):
    if side == 'left':
        return {(0, r) for r in range(ROWS)}
    if side == 'right':
        return {(COLS - 1, r) for r in range(ROWS)}
    if side == 'top':
        return {(c, 0) for c in range(COLS)}
    return {(c, ROWS - 1) for c in range(COLS)}


# ── Graph level: grid zero reservation ────────────────────────────────────────

@given(st.integers(0, 2**32 - 1), st.integers(2, 8))
@settings(max_examples=150, deadline=None)
def test_grid_zero_reserved(seed, gc):
    fs = {**FS_ALL, 'grid_count': gc}
    g = LevelGraph.generate(fs, random.Random(seed))
    assert g.entrance_side in SIDES
    start = _start_corridor(g)
    # The start grid faces grid zero across the entrance side.
    sc, sr = g.nodes[start].super_pos
    dc, dr = DELTA[g.entrance_side]
    assert (sc + dc, sr + dr) == (0, 0)
    # No grid ever occupies the origin (checked on every Prim step).
    for n, nd in g.nodes.items():
        if nd.size == NodeSize.CORRIDOR:
            assert nd.super_pos != (0, 0), f"{n} occupies grid zero"
    # The entrance side carries no BORDER edge.
    assert g.entrance_side not in _border_sides(g, start)


# ── Single-grid: uniform entrance side (spec 0055) ────────────────────────────

def test_single_grid_entrance_side_uniform():
    """Single-grid graphs draw their entrance side from grid zero too;
    over 400 seeds every side gets a substantial share (uniform = 25 %).
    Pre-fix: entrance_side is None and level-11 entrances were 64 % left /
    30 % top / 6 % bottom / 0 % right (fixed scan order)."""
    counts = collections.Counter()
    for seed in range(400):
        g = LevelGraph.generate({**FS_ALL, 'grid_count': 1},
                                random.Random(seed))
        assert g.entrance_side in SIDES
        counts[g.entrance_side] += 1
    for side in SIDES:
        assert counts[side] >= 60, f"side share skewed: {dict(counts)}"


# ── Level level: entrance anchoring ───────────────────────────────────────────

@given(st.integers(0, 2**32 - 1), st.integers(1, 6))
@settings(max_examples=15, deadline=None)
def test_entrance_anchored_to_player_start(seed, gc):
    g, lv = _build(seed, gc)
    room = lv['rooms'][lv['start_room']]
    ent = room['entrance']
    ps = lv['player_start']
    side = _side_of(ent)
    assert side == g.entrance_side, (
        f"entrance {ent} not on reserved side {g.entrance_side!r}")
    assert abs(ent[0] - ps[0]) + abs(ent[1] - ps[1]) == 1, (
        f"entrance {ent} not adjacent to player start {ps}")
    assert room['tile_owner'][ps] == _start_corridor(g), (
        f"player start {ps} not corridor-owned")
    # The entrance face carries no inter-grid exit and no border barrier.
    for key in room.get('exits', {}):
        assert not key.startswith(f'{side}_'), (
            f"border exit {key!r} on the entrance side")
    face = _face(side)
    for c, r, *_ in room.get('locked_doors', []):
        assert (c, r) not in face, f"locked border door at {(c, r)}"
    for c, r, *_ in room.get('gates', []):
        assert (c, r) not in face, f"border gate at {(c, r)}"


# ── Pinned pre-fix regression case ────────────────────────────────────────────

def test_pinned_fallback_case():
    """Game seed 4 / level 13 hit the pre-fix col-0 fallback: entrance (0,1),
    player start (14,1), distance 14 (sweep 2026-07-12)."""
    old_seed = levels._game_seed
    try:
        levels.set_game_seed(4)
        levels._act2_cache.clear()
        d = levels.get_level(13)
        ps = d['player_start']
        ent = d['rooms'][d['start_room']]['entrance']
        assert abs(ent[0] - ps[0]) + abs(ent[1] - ps[1]) == 1, (
            f"entrance {ent} not adjacent to player start {ps}")
    finally:
        levels._game_seed = old_seed
        levels._act2_cache.clear()


# ── R-P8 (spec 0057 / BL-16): no item on player_start or the entrance ────────

ITEM_LISTS = ('treasures', 'materials', 'keys',
              'pressure_plates', 'pushable_blocks')


def _assert_start_tiles_item_free(lv):
    room = lv['rooms'][lv['start_room']]
    forbidden = {tuple(lv['player_start'])}
    if 'entrance' in room:
        forbidden.add(tuple(room['entrance']))
    for lname in ITEM_LISTS:
        hit = [e for e in room.get(lname, [])
               if (e[0], e[1]) in forbidden]
        assert not hit, (
            f"{lname} on player_start/entrance {sorted(forbidden)}: {hit}")


@pytest.mark.parametrize('gc', range(1, 7))
@given(st.integers(0, 2**32 - 1))
@settings(max_examples=5, deadline=None)     # 6 × 5 = 30, same total as before
def test_no_item_on_player_start_or_entrance(gc, seed):
    """No treasure, material, key, plate, or block may occupy the start
    grid's player_start or entrance tile (R-P8).

    ``gc`` (grid count) is a pytest param, not a hypothesis draw, so each of
    the 6 values becomes its own xdist-distributable item; the example budget
    is split 6 × 5 to keep the total 30 builds unchanged (spec 0069)."""
    _g, lv = _build(seed, gc)
    _assert_start_tiles_item_free(lv)


def test_pinned_item_on_player_start():
    """Game seed 4 / level 13 placed a rocks material on player_start
    (14, 14) pre-fix (sweep 2026-07-11, scratchpad/sweep_items_on_start.py).
    Red before the spec-0057 seeding of global_used, green after."""
    old_seed = levels._game_seed
    try:
        levels.set_game_seed(4)
        levels._act2_cache.clear()
        _assert_start_tiles_item_free(levels.get_level(13))
    finally:
        levels._game_seed = old_seed
        levels._act2_cache.clear()
