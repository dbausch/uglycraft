"""Water-challenge invariants (spec 0029).

W1  A placed node's planks are never dropped during layout.
W4  The level dict maps each water tile to exactly one water room (the node
    behind its WATER edge), so the runtime can key the bridge lock on the room.
W5  validate_playability opens a WATER edge only when >= 2 planks are reachable
    (a craftable bridge); a pushable block does NOT open water.

W2 (one bridge per water room) and W3 (no per-grid bridge cap) are runtime
behaviours in game.py and are verified manually in-game.
"""
import random

from hypothesis import given, settings, strategies as st

from levelgraph import LevelGraph, EdgeType, NodeSize
from levellayout import build_level_dict
from tests.conftest import FS_WATER


FS_CROWDED_WATER = {
    'room_count':       (8, 12),
    'edge_types':       [EdgeType.OPEN, EdgeType.WATER],
    'node_sizes':       [NodeSize.ROOM, NodeSize.HALL],
    'treasure_count':   (12, 16),
    'material_types':   ['planks'],
    'material_count':   (0, 0),
    'enemy_count':      (0, 0),
    'grid_count':       3,
    'layout_strategies': ['horizontal', 'vertical', 'off_centre', 't',
                          'double_t', 'z'],
}
_FEATURE_SETS = (FS_WATER, FS_CROWDED_WATER)


def _count_planks_dict(level):
    return sum(1 for rd in level['rooms'].values()
               for m in rd.get('materials', []) if m[2] == 'planks')


def _build(fs, seed):
    rng = random.Random(seed)
    graph = LevelGraph.generate(fs, rng)
    level = build_level_dict(graph, rng=rng, strategies=fs.get('layout_strategies'))
    return graph, level


# ── W1: no plank is ever dropped (spec 0032 C7 spills an unplaced node's planks)

@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=100, deadline=None)
def test_planks_never_dropped(seed):
    for fs in _FEATURE_SETS:
        graph, level = _build(fs, seed)
        planks_graph = sum(
            sum(1 for m in nd.materials if m == ('planks',))
            for nd in graph.nodes.values())
        if planks_graph == 0:
            continue
        assert _count_planks_dict(level) == planks_graph, (
            f"seed={seed} grids={fs.get('grid_count', 1)}: "
            f"planks_graph={planks_graph} "
            f"planks_dict={_count_planks_dict(level)} — a plank was lost"
        )


# ── W4: every water tile maps to exactly one water room ──────────────────────

@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=100, deadline=None)
def test_water_tile_room_mapping(seed):
    for fs in _FEATURE_SETS:
        graph, level = _build(fs, seed)
        for rd in level['rooms'].values():
            water = {tuple(t) for t in rd.get('water_tiles', [])}
            mapping = rd.get('water_tile_room', {})
            if not water:
                assert not mapping, "water_tile_room present without water tiles"
                continue
            # Every water tile is mapped to exactly one room name.
            assert set(mapping.keys()) == water, (
                f"seed={seed}: water tiles {water ^ set(mapping.keys())} "
                f"not mapped 1:1 to a water room"
            )
            # Each mapped name is a real node behind a WATER edge.
            water_rooms = {e.node_b for e in graph.edges
                           if e.edge_type == EdgeType.WATER}
            for tile, name in mapping.items():
                assert name in water_rooms, (
                    f"seed={seed}: tile {tile} maps to {name!r} which is not a "
                    f"water room"
                )


# ── W5: validate_playability requires two reachable planks; block != bridge ──

def _water_graph(n_planks, n_blocks=0):
    g = LevelGraph(random.Random(0))
    g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
    dry = g.add_node('dry', NodeSize.ROOM)
    g.add_edge('corridor', 'dry', EdgeType.OPEN)
    g.add_node('water', NodeSize.ROOM)
    g.add_edge('corridor', 'water', EdgeType.WATER)
    for _ in range(n_planks):
        dry.materials.append(('planks',))
    for _ in range(n_blocks):
        dry.blocks.append(1)
    return g


def test_validate_two_planks_open_water():
    assert _water_graph(n_planks=2).validate_playability() == []


def test_validate_one_plank_does_not_open_water():
    errors = _water_graph(n_planks=1).validate_playability()
    assert errors, "one plank wrongly opened a WATER edge"


def test_validate_block_does_not_open_water():
    errors = _water_graph(n_planks=0, n_blocks=1).validate_playability()
    assert errors, "a pushable block wrongly opened a WATER edge"
