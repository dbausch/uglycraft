"""Spec 0060 — Act 2 room scaling with grid count (BL-21 + BL-22 + BL-25).

Room counts become a per-grid ramp (2–4 per grid early, 4–6 at level
20), levels 11–13 lose complex layout strategies, and exit sides are
dictated by the strategy list: the spanning tree and the entrance draw
only use sides the level's strategies can cover, so side-mismatch
full_border fallbacks are structurally absent.

Red when written: room counts sit near 1 room per grid on levels
14–20, strategy lists still carry z/l/double_t on 11–13, and
levelgraph exposes no coverage predicate.
"""
import random

import pytest

import levels
from levelgraph import LevelGraph, EdgeType, NodeSize

FS = levels.ACT2_FEATURE_SETS          # indices 0..9 = levels 11..20


# ── Feature-set bounds contract ───────────────────────────────────────────────

def test_room_count_scales_per_grid():
    for i, fs in enumerate(FS):
        level = 11 + i
        G = fs.get('grid_count', 1)
        lo, hi = fs['room_count']
        assert lo >= 2 * G, (
            f"level {level}: room min {lo} < 2 per grid (G={G})")
        assert hi <= 6 * G, (
            f"level {level}: room max {hi} > 6 per grid (G={G})")
        required = len(dict.fromkeys(fs['edge_types']))
        if fs.get('has_water'):
            required += max(1, G // 3)
        assert lo >= required, (
            f"level {level}: room min {lo} < {required} required rooms")


# ── Strategy contract (BL-22) ─────────────────────────────────────────────────

# Levels 14-20: today's list plus the corner strategy (review 2026-07-11).
_RICH = ['horizontal', 'vertical', 'off_centre', 'double_t', 't', 'z', 'l']


@pytest.mark.parametrize('idx,expected', [
    (0, ['horizontal', 'vertical']),
    (1, ['horizontal', 'vertical']),
    (2, ['horizontal', 'vertical', 'l']),
    (3, _RICH), (4, _RICH), (5, _RICH), (6, _RICH),
    (7, _RICH), (8, _RICH), (9, _RICH),
])
def test_strategy_lists(idx, expected):
    assert FS[idx]['layout_strategies'] == expected, f"level {11 + idx}"


# ── Exit sides dictated by the strategy list ─────────────────────────────────

def _grid_side_sets(g):
    """{corridor: frozenset of required sides} — BORDER faces plus the
    entrance side on the start corridor."""
    sides = {n: set() for n, nd in g.nodes.items()
             if nd.size == NodeSize.CORRIDOR}
    for e in g.edges:
        if e.edge_type != EdgeType.BORDER:
            continue
        sides[e.node_a].add(e.params['exit_side'])
        sides[e.node_b].add(e.params['entry_side'])
    start = next(n for n, nd in g.nodes.items() if nd.is_start)
    if getattr(g, 'entrance_side', None):
        sides[start].add(g.entrance_side)
    return sides


@pytest.mark.parametrize('idx', range(10))
def test_required_sides_always_coverable(idx):
    """No grid's required side set may exceed what the level's listed
    strategies cover under that grid's anchor status — full_border by
    side mismatch is structurally impossible (spec 0060).  Non-start
    grids continue their parent's corridor band, so arm strategies
    (z/s/l) leave their pool (R-T5): only the start grid may turn."""
    from levelgraph import coverable_sides
    fs = FS[idx]
    for seed in range(10):
        g = LevelGraph.generate(fs, random.Random(seed))
        start = next(n for n, nd in g.nodes.items() if nd.is_start)
        for cor, sides in _grid_side_sets(g).items():
            assert coverable_sides(sides, fs['layout_strategies'],
                                   anchored=(cor != start)), (
                f"level {11 + idx} seed={seed}: grid {cor!r} needs "
                f"{sorted(sides)} (anchored={cor != start}), not "
                f"coverable by {fs['layout_strategies']}")


def test_levels_11_12_chain_along_entrance_axis():
    """With only the two spines listed, the grids (including grid zero at
    the origin) stay collinear — the level is a straight chain along the
    entrance axis."""
    for idx in (0, 1):
        fs = FS[idx]
        for seed in range(20):
            g = LevelGraph.generate(fs, random.Random(seed))
            pos = [(0, 0)] + [nd.super_pos for nd in g.nodes.values()
                              if nd.size == NodeSize.CORRIDOR]
            same_col = len({c for c, _r in pos}) == 1
            same_row = len({r for _c, r in pos}) == 1
            assert same_col or same_row, (
                f"level {11 + idx} seed={seed}: grids not collinear "
                f"with grid zero: {pos}")
