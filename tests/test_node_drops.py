"""No-silent-node-drop invariants (spec 0032 / BL-23).

N1  Closets are placed in multi-grid levels (they were dropped because
    _build_subgraph never copied them into per-grid subgraphs).
N2  No content-bearing node (keys / materials / treasures / plates / blocks) is
    silently dropped: a successful build places every such node, otherwise it
    raises LayoutError and the generator regenerates.
"""
import random

import pytest
from hypothesis import given, settings, strategies as st

from levelgraph import LevelGraph, EdgeType, NodeSize
from levellayout import build_level_dict, LayoutError
from levels import ACT2_FEATURE_SETS


FS_CLOSETS = {
    'room_count':       (4, 6),
    'edge_types':       [EdgeType.OPEN, EdgeType.LOCKED],
    'node_sizes':       [NodeSize.ROOM, NodeSize.HALL],
    'treasure_count':   (6, 10),
    'material_types':   [],
    'material_count':   (0, 0),
    'enemy_count':      (0, 0),
    'closet_prob':      0.7,
    'grid_count':       3,
    'layout_strategies': ['horizontal', 'vertical', 'off_centre', 't',
                          'double_t', 'z'],
}


def _build(fs, seed, grid_count=None):
    """Build, mirroring _generate_act2_level's retry-on-LayoutError."""
    grids = grid_count if grid_count is not None else fs.get('grid_count', 1)
    base = random.Random(seed)
    for _ in range(60):
        rng = random.Random(base.randint(0, 2**31))
        graph = LevelGraph.generate({**fs, 'grid_count': grids}, rng)
        try:
            level = build_level_dict(graph, rng=rng,
                                     strategies=fs.get('layout_strategies'),
                                     grid_count=grids)
            return graph, level
        except LayoutError:
            continue
    raise AssertionError(f"build never succeeded for seed={seed}, grids={grids}")


def _placed_names(level):
    names = set()
    for rd in level['rooms'].values():
        names.update(rd.get('tile_owner', {}).values())
    return names


# ── C6: multi-grid no longer omits closets — they are carved, not dropped ────

def test_multigrid_carves_closets():
    """The multi-grid omission bug (BL-23) dropped 100% of closets.  With C6 they
    are copied into per-grid subgraphs and carved; a closet is only skipped (and
    its content spilled by C7) on the rare too-small/dropped parent, so the carve
    rate must be high (was 0% for any grid_count > 1)."""
    for grids in (2, 3, 4):
        placed_ct = total = 0
        for seed in range(40):
            graph, level = _build(FS_CLOSETS, seed, grid_count=grids)
            names = _placed_names(level)
            closets = [n for n, nd in graph.nodes.items()
                       if nd.size == NodeSize.CLOSET]
            total += len(closets)
            placed_ct += sum(1 for c in closets if c in names)
        assert total > 0
        rate = placed_ct / total
        assert rate >= 0.9, (
            f"grids={grids}: closet carve rate {rate:.2f} too low (omission?)")


def test_closets_not_counted_in_strategy_selection(monkeypatch):
    """Closets are carved from their parent and occupy no zone, so they must not
    count toward room-count strategy selection — otherwise a grid picks a layout
    with more zones than it has regular rooms, leaving unoccupied zones."""
    import levellayout as L
    overzoned = []
    orig = L.build_level_dict

    def spy(graph, rng=None, strategies=None, **kw):
        # inner per-grid builds: a single forced strategy, no BORDER edges
        if (strategies and len(strategies) == 1
                and not any(e.edge_type == EdgeType.BORDER for e in graph.edges)):
            reg = sum(1 for nd in graph.nodes.values()
                      if nd.size in (NodeSize.ROOM, NodeSize.HALL))
            max_zones = L._STRATEGY_MAX_ZONES.get(strategies[0], 2)
            if reg < max_zones:
                overzoned.append((strategies[0], reg, max_zones))
        return orig(graph, rng=rng, strategies=strategies, **kw)

    monkeypatch.setattr(L, 'build_level_dict', spy)
    for seed in range(30):
        _build(FS_CLOSETS_TIGHT, seed)
    assert not overzoned, f"grids picked over-zoned strategies: {overzoned[:5]}"


# ── C7: content is never lost — spilled to room/corridor when a node is unplaced

# Closet-heavy with many (hence small) rooms, so closets frequently cannot be
# carved and must spill their content (and some rooms drop and spill too).
FS_CLOSETS_TIGHT = {
    'room_count':       (8, 12),
    'edge_types':       [EdgeType.OPEN, EdgeType.LOCKED],
    'node_sizes':       [NodeSize.ROOM, NodeSize.HALL],
    'treasure_count':   (10, 14),
    'material_types':   ['rocks', 'metal'],
    'material_count':   (6, 10),
    'enemy_count':      (0, 0),
    'closet_prob':      0.8,
    'grid_count':       3,
    'layout_strategies': ['horizontal', 'vertical', 'off_centre', 't',
                          'double_t', 'z'],
}


def _content_graph(g):
    return (sum(len(n.keys) for n in g.nodes.values()),
            sum(len(n.treasures) for n in g.nodes.values()),
            sum(len(n.materials) for n in g.nodes.values()))


def _content_dict(level):
    return (sum(len(rd.get('keys', [])) for rd in level['rooms'].values()),
            sum(len(rd.get('treasures', [])) for rd in level['rooms'].values()),
            sum(len(rd.get('materials', [])) for rd in level['rooms'].values()))


def _assert_content_preserved(g, level, ctx, has_flames=False):
    """Keys and materials are never lost (spilled when a node is unplaced).
    Treasures are also preserved EXCEPT in flame levels, where flame rooms
    intentionally relocate their treasures to jet far-tiles (R-F4), so the count
    can legitimately fall.  (Push-puzzle plates are excluded: a dropped puzzle
    room's gate is elided.)"""
    gk, gt, gm = _content_graph(g)
    dk, dt, dm = _content_dict(level)
    assert dk == gk, f"{ctx}: keys graph={gk} dict={dk}"
    assert dm == gm, f"{ctx}: materials graph={gm} dict={dm}"
    if not has_flames:
        assert dt == gt, f"{ctx}: treasures graph={gt} dict={dt}"


@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=40, deadline=None)
def test_closet_content_never_lost(seed):
    g, level = _build(FS_CLOSETS_TIGHT, seed)
    _assert_content_preserved(g, level, f"tight seed={seed}")


@pytest.mark.parametrize('idx', range(len(ACT2_FEATURE_SETS)))
@pytest.mark.parametrize('seed', [0, 1])
def test_content_never_lost_real_act2(idx, seed):
    fs = ACT2_FEATURE_SETS[idx]
    g, level = _build(fs, seed * 100 + idx)
    _assert_content_preserved(g, level, f"idx={idx} seed={seed}",
                              has_flames=fs.get('has_flames', False))
