"""BL-29 / spec 0033 — BORDER openings land on the corridor, and corridors
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


@given(st.integers(min_value=0, max_value=2 ** 32 - 1))
@settings(max_examples=30, deadline=None)
def test_border_openings_land_on_corridor(seed):
    """Every BORDER opening's inner tile is owned by that grid's corridor."""
    for fs in _SETS:
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


@given(st.integers(min_value=0, max_value=2 ** 32 - 1))
@settings(max_examples=30, deadline=None)
def test_corridors_continue_across_border(seed):
    """For a BORDER edge with neither grid full_border, the two corridor face
    bands are identical (the corridor continues through the border)."""
    for fs in _SETS:
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
