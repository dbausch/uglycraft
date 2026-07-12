"""BL-29 / spec 0042 — BORDER openings land on the corridor, and corridors
continue across the border (entry-grid corridor band == exit-grid corridor band).

Pre-fix these are red: ~40 % of BORDER openings land in a room, and the two
corridor bands across an edge are unrelated.
"""
import random

import pytest
from hypothesis import given, settings, strategies as st

from levelgraph import LevelGraph, EdgeType, NodeSize
from levellayout import build_level_dict, LayoutError
from tests.test_key_placement import FS_CROWDED_LOCKED
from tests.test_water_challenge import FS_CROWDED_WATER

COLS, ROWS = 30, 16
INNER = {'left': lambda p: (1, p), 'right': lambda p: (COLS - 2, p),
         'top': lambda p: (p, 1),  'bottom': lambda p: (p, ROWS - 2)}
FULL = {'left': frozenset(range(1, ROWS - 1)),  'right': frozenset(range(1, ROWS - 1)),
        'top':  frozenset(range(1, COLS - 1)),  'bottom': frozenset(range(1, COLS - 1))}


def _build(fs, seed, gc):
    base = random.Random(seed)
    fs = {**fs, 'grid_count': gc}
    for _ in range(60):
        rng = random.Random(base.randint(0, 2 ** 31))
        g = LevelGraph.generate(fs, rng)
        try:
            lv = build_level_dict(g, rng=rng,
                                  strategies=fs.get('layout_strategies'),
                                  grid_count=gc)
            return g, lv
        except LayoutError:
            continue
    raise AssertionError(f"build never succeeded fs={fs.get('name')} seed={seed}")


def _cor_names(graph):
    return {n for n, nd in graph.nodes.items() if nd.size == NodeSize.CORRIDOR}


def _grid_corridor(rd, cor_names):
    """The single corridor node owning tiles in this grid's room dict."""
    owners = set(rd.get('tile_owner', {}).values()) & cor_names
    assert len(owners) == 1, f"expected one corridor per grid, got {owners}"
    return next(iter(owners))


def _band(rd, side, corname):
    to = rd['tile_owner']
    if side in ('left', 'right'):
        col = 1 if side == 'left' else COLS - 2
        return frozenset(rr for (cc, rr), o in to.items() if cc == col and o == corname)
    row = 1 if side == 'top' else ROWS - 2
    return frozenset(cc for (cc, rr), o in to.items() if rr == row and o == corname)


_SETS = (FS_CROWDED_LOCKED, FS_CROWDED_WATER)


@pytest.mark.parametrize('fs', _SETS)
@given(st.integers(min_value=0, max_value=2 ** 32 - 1))
@settings(max_examples=30, deadline=None)
def test_border_openings_land_on_corridor(fs, seed):
    """Every BORDER opening's inner tile is owned by that grid's corridor."""
    for gc in (2, 3):
        graph, lv = _build(fs, seed, gc)
        cor = _cor_names(graph)
        for gname, rd in lv['rooms'].items():
            for ek in rd.get('exits', {}):
                side, _, pos = ek.rpartition('_')
                inner = INNER[side](int(pos))
                owner = rd['tile_owner'].get(inner)
                assert owner in cor, (
                    f"fs={fs.get('name')} seed={seed} gc={gc}: opening {ek} "
                    f"on {gname} lands on {owner!r} (inner {inner}), not a corridor")


@pytest.mark.parametrize('fs', _SETS)
@given(st.integers(min_value=0, max_value=2 ** 32 - 1))
@settings(max_examples=30, deadline=None)
def test_corridors_continue_across_border(fs, seed):
    """For a BORDER edge with neither grid full_border, the two corridor face
    bands are identical (the corridor continues through the border)."""
    for gc in (2, 3):
        graph, lv = _build(fs, seed, gc)
        cor = _cor_names(graph)
        rooms = lv['rooms']
        cor_grid = {}                      # corridor node name -> gname
        for gname, rd in rooms.items():
            cor_grid[_grid_corridor(rd, cor)] = gname
        for e in graph.edges:
            if e.edge_type != EdgeType.BORDER:
                continue
            ga, gb = cor_grid[e.node_a], cor_grid[e.node_b]
            es, en = e.params['exit_side'], e.params['entry_side']
            ba = _band(rooms[ga], es, e.node_a)
            bb = _band(rooms[gb], en, e.node_b)
            if ba == FULL[es] or bb == FULL[en]:
                continue               # full_border source/entry: FREE
            assert ba == bb, (
                f"fs={fs.get('name')} seed={seed} gc={gc}: corridor does not "
                f"continue across {ga}({es})->{gb}({en}): {sorted(ba)} != {sorted(bb)}")


def _build_forced(fs, seed, gc, strategies):
    base = random.Random(seed)
    fs = {**fs, 'grid_count': gc}
    for _ in range(60):
        rng = random.Random(base.randint(0, 2 ** 31))
        g = LevelGraph.generate(fs, rng)
        try:
            lv = build_level_dict(g, rng=rng, strategies=strategies, grid_count=gc)
            return g, lv
        except LayoutError:
            continue
    raise AssertionError(f"forced build failed fs={fs.get('name')} seed={seed}")


def test_full_border_exits_are_varied():
    """With every grid forced to full_border (all edges full<->full), openings
    must not all sit at the grid centre — the source grid actively varies its
    exit band within an attachable range (spec 0042)."""
    positions = []
    for fs in _SETS:
        for seed in range(25):
            graph, lv = _build_forced(fs, seed, 4, ['full_border'])
            for rd in lv['rooms'].values():
                for ek in rd.get('exits', {}):
                    side, _, pos = ek.rpartition('_')
                    positions.append((side, int(pos)))
    assert positions, "no border openings sampled"
    distinct_pos = {pos for _, pos in positions}
    # pre-fix this is {7, 14} (left/right + top/bottom centres) → 2 values
    assert len(distinct_pos) >= 6, (
        f"full_border exits cluster at centre: {sorted(distinct_pos)}")


# ── Spec 0056 (BL-12): border_barriers records ────────────────────────────────
# Stitching must record (kind, param, home) on BOTH room dicts of every BORDER
# edge, 1:1 with the exits keys, matching the entity actually placed (guarded
# by the same surviving-prerequisite checks).

FS_CROWDED_GATED = {
    'room_count':       (8, 12),
    'edge_types':       [EdgeType.OPEN, EdgeType.GATED],
    'node_sizes':       [NodeSize.ROOM, NodeSize.HALL],
    'treasure_count':   (12, 16),
    'material_types':   [],
    'material_count':   (0, 0),
    'enemy_count':      (0, 0),
    'closet_count':     (1, 2),
    'grid_count':       3,
    'layout_strategies': ['horizontal', 'vertical', 'off_centre', 't',
                          'double_t', 'z'],
}

_REC_SETS = (FS_CROWDED_LOCKED, FS_CROWDED_GATED)

_BORDER_TILE = {'right':  lambda p: (COLS - 1, p),
                'left':   lambda p: (0,        p),
                'bottom': lambda p: (p, ROWS - 1),
                'top':    lambda p: (p, 0)}


def _expected_record(edge, gname_a, pos, rooms):
    """The record spec 0056 B1 demands, recomputed from the room dicts."""
    surviving_keys = {k[2] for rd in rooms.values()
                      for k in rd.get('keys', [])}
    surviving_gates = {p[2] for rd in rooms.values()
                       for p in rd.get('pressure_plates', [])}
    barrier = edge.params.get('barrier', 'open')
    es = edge.params['exit_side']
    if barrier == 'locked' and edge.params['key_colour'] in surviving_keys:
        return ('locked', edge.params['key_colour'],
                (gname_a, _BORDER_TILE[es](pos)))
    if barrier == 'gated' and edge.params['gate_id'] in surviving_gates:
        return ('gated', edge.params['gate_id'], None)
    return ('open', None, None)


@pytest.mark.parametrize('fs', _REC_SETS)
@given(st.integers(min_value=0, max_value=2 ** 32 - 1))
@settings(max_examples=15, deadline=None)
def test_border_barrier_records_on_both_sides(fs, seed):
    for gc in (2, 3):
        graph, lv = _build(fs, seed, gc)
        cor = _cor_names(graph)
        rooms = lv['rooms']
        cor_grid = {}
        for gname, rd in rooms.items():
            cor_grid[_grid_corridor(rd, cor)] = gname
            assert set(rd.get('exits', {})) == \
                set(rd.get('border_barriers', {})), (
                    f"fs={fs.get('name')} seed={seed} gc={gc}: exits and "
                    f"border_barriers keys differ on {gname}")
        for e in graph.edges:
            if e.edge_type != EdgeType.BORDER:
                continue
            ga, gb = cor_grid[e.node_a], cor_grid[e.node_b]
            es, en = e.params['exit_side'], e.params['entry_side']
            key_a = next(k for k, v in rooms[ga]['exits'].items()
                         if v == gb and k.rpartition('_')[0] == es)
            pos = int(key_a.rpartition('_')[2])
            key_b = f'{en}_{pos}'
            rec_a = rooms[ga]['border_barriers'][key_a]
            rec_b = rooms[gb]['border_barriers'][key_b]
            assert rec_a == rec_b, (
                f"records differ across {ga}({es})->{gb}({en}): "
                f"{rec_a} != {rec_b}")
            assert rec_a == _expected_record(e, ga, pos, rooms)
            kind, param, home = rec_a
            bt = _BORDER_TILE[es](pos)
            doors_at_bt = [d for d in rooms[ga].get('locked_doors', [])
                           if (d[0], d[1]) == bt]
            gates_at_bt = [g for g in rooms[ga].get('gates', [])
                           if (g[0], g[1]) == bt]
            if kind == 'locked':
                assert doors_at_bt == [(*bt, param)]
                assert home == (ga, bt)
            elif kind == 'gated':
                assert gates_at_bt == [(*bt, param)]
            else:
                assert not doors_at_bt and not gates_at_bt, (
                    f"open record but entity at {bt} on {ga}")


def test_border_barrier_kinds_covered():
    """Guards the record test against vacuity: all three kinds must occur
    within the sampled seed range."""
    kinds = set()
    for seed in range(40):
        for fs in _REC_SETS:
            _, lv = _build(fs, seed, 3)
            for rd in lv['rooms'].values():
                kinds |= {rec[0]
                          for rec in rd.get('border_barriers', {}).values()}
        if kinds >= {'open', 'locked', 'gated'}:
            return
    raise AssertionError(f"barrier kinds seen in sweep: {kinds}")


def test_degraded_border_records_open():
    """A locked border whose key did not survive placement degrades to an
    open passage: record ('open', None, None) on both sides, no phantom
    door entity — the player never sees a door they needed no key for."""
    from levelgraph import LevelGraphBuilder
    for attempt in range(60):
        b = LevelGraphBuilder(random.Random(7 + attempt))
        b.add_open_room()
        b._graph.nodes['corridor'].super_pos = (1, 1)
        b.start_next_grid(2, 1, 'right', barrier='locked', key_colour='red')
        b.add_open_room()
        g = b._graph
        for nd in g.nodes.values():
            nd.keys = [k for k in nd.keys if k[0] != 'red']
        try:
            lv = build_level_dict(g, rng=random.Random(attempt), grid_count=2)
            break
        except LayoutError:
            continue
    else:
        raise AssertionError("degraded-border build never succeeded")
    rooms = lv['rooms']
    recs = [rec for rd in rooms.values()
            for rec in rd.get('border_barriers', {}).values()]
    assert recs, "no border_barriers records at all"
    assert all(rec == ('open', None, None) for rec in recs), recs
    for rd in rooms.values():
        assert set(rd['exits']) == set(rd.get('border_barriers', {}))
        for (c, r, _colour) in rd.get('locked_doors', []):
            assert 0 < c < COLS - 1 and 0 < r < ROWS - 1, (
                f"phantom border door at {(c, r)}")


def test_full_border_usage_stays_low():
    """Coordinate-at-layout must not collapse most grids to full_border."""
    full = total = 0
    for fs in _SETS:
        for seed in range(20):
            for gc in (2, 3):
                graph, lv = _build(fs, seed, gc)
                cor = _cor_names(graph)
                for gname, rd in lv['rooms'].items():
                    total += 1
                    corname = _grid_corridor(rd, cor)
                    # full_border grid: corridor reaches a side across the whole line
                    if any(_band(rd, s, corname) == FULL[s]
                           for s in ('left', 'right', 'top', 'bottom')):
                        full += 1
    assert total and full / total < 0.30, f"full_border share {full}/{total} too high"
