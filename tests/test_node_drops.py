"""No-silent-node-drop invariants (spec 0032 / BL-23).

N1  Closets are placed in multi-grid levels (they were dropped because
    _build_subgraph never copied them into per-grid subgraphs).
N2  No content-bearing node (keys / materials / treasures / plates / blocks) is
    silently dropped: a successful build places every such node, otherwise it
    raises LayoutError and the generator regenerates.
"""
import random

from hypothesis import given, settings, strategies as st

from levelgraph import LevelGraph, EdgeType, NodeSize
from levellayout import build_level_dict, LayoutError


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


def _has_content(node):
    return bool(node.keys or node.materials or node.treasures
                or node.plates or node.blocks)


# ── N1: closets survive in multi-grid (and single-grid) ──────────────────────

@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=40, deadline=None)
def test_closets_survive_multigrid(seed):
    for grids in (1, 2, 4):
        graph, level = _build(FS_CLOSETS, seed, grid_count=grids)
        placed = _placed_names(level)
        dropped = [n for n, nd in graph.nodes.items()
                   if nd.size == NodeSize.CLOSET and n not in placed]
        assert not dropped, (
            f"seed={seed} grids={grids}: closets dropped {dropped}")


# ── N2: no content-bearing node dropped — closet-rich multi-grid set ─────────

@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=40, deadline=None)
def test_no_content_node_dropped_closet_set(seed):
    graph, level = _build(FS_CLOSETS, seed)
    placed = _placed_names(level)
    dropped = [n for n, nd in graph.nodes.items()
               if n not in placed and _has_content(nd)]
    assert not dropped, f"seed={seed}: content-bearing nodes dropped {dropped}"


# Note: the strict "no content-bearing node dropped" guarantee across the real
# Act 2 sets (where a closet can land on a too-small or dropped parent) is part
# of spec 0032 C7 (content spill / puzzle elision) and is tested in step 2.
