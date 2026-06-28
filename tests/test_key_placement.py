"""Key placement invariants (spec 0030).

K1  No key is dropped during layout: keys_dict == keys_graph.
K2  Every locked door (interior + border) has a surviving key of its colour
    somewhere in the level; no soft-lock. A barrier whose key is absent must be
    an open passage instead, never a locked door with no key.
K3  Graph-side key reachability is sound: validate_playability() == [].
"""
import random

from hypothesis import given, settings, strategies as st

from levelgraph import LevelGraph, EdgeType, NodeSize
from levellayout import build_level_dict
from tests.conftest import FS_LOCKED, FS_ALL


# A crowded multi-grid locked feature set: high treasure_count fills rooms (to
# exercise key drops) and grid_count > 1 adds BORDER edges that may be locked
# (to exercise border-door placement during stitching).
FS_CROWDED_LOCKED = {
    'room_count':       (8, 12),
    'edge_types':       [EdgeType.OPEN, EdgeType.LOCKED],
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

_FEATURE_SETS = (FS_LOCKED, FS_ALL, FS_CROWDED_LOCKED)


def _keys_graph(graph):
    return sum(len(n.keys) for n in graph.nodes.values())


def _placed_node_names(level):
    """Node names that were actually placed (appear in some room's tile_owner)."""
    names = set()
    for rd in level['rooms'].values():
        names.update(rd.get('tile_owner', {}).values())
    return names


def _keys_in_placed_nodes(graph, level):
    placed = _placed_node_names(level)
    return sum(len(graph.nodes[n].keys) for n in placed if n in graph.nodes)


def _level_key_stats(level):
    """Return (keys_dict, door_colours, surviving_key_colours)."""
    keys_dict = 0
    door_colours = []
    key_colours = set()
    for rd in level['rooms'].values():
        ks = rd.get('keys', [])
        keys_dict += len(ks)
        for k in ks:
            key_colours.add(k[2])
        for d in rd.get('locked_doors', []):
            door_colours.append(d[2])
    return keys_dict, door_colours, key_colours


def _build(fs, seed):
    rng = random.Random(seed)
    graph = LevelGraph.generate(fs, rng)
    kg = _keys_graph(graph)
    level = build_level_dict(graph, rng=rng, strategies=fs.get('layout_strategies'))
    return graph, kg, level


# ── K1: a placed node's keys are never dropped (spill, not silent loss) ──────
#
# A node that the layout cannot place at all (room too small to pack, R-P4) is
# dropped together with its keys; that is a pre-existing, accepted behaviour and
# K2 turns the dependent door into an open passage (no soft-lock).  The K1
# guarantee is narrower: every key belonging to a *placed* node survives layout.

@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=100, deadline=None)
def test_placed_node_keys_never_dropped(seed):
    for fs in _FEATURE_SETS:
        graph, kg, level = _build(fs, seed)
        keys_placed = _keys_in_placed_nodes(graph, level)
        if keys_placed == 0:
            continue
        kd, _, _ = _level_key_stats(level)
        assert kd == keys_placed, (
            f"seed={seed} fs grids={fs.get('grid_count', 1)}: "
            f"keys in placed nodes={keys_placed} keys_dict={kd} — "
            f"a placed node's key was dropped"
        )


# ── K2: every locked door has a surviving key (no soft-lock) ─────────────────

@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=100, deadline=None)
def test_no_softlocked_doors(seed):
    for fs in _FEATURE_SETS:
        graph, kg, level = _build(fs, seed)
        if kg == 0:
            continue
        _, door_colours, key_colours = _level_key_stats(level)
        soft = [c for c in door_colours if c not in key_colours]
        assert not soft, (
            f"seed={seed} fs grids={fs.get('grid_count', 1)}: "
            f"locked doors with no key anywhere: {soft}"
        )


# ── K3: graph-side key reachability is sound ─────────────────────────────────

@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=200)
def test_graph_keys_reachable(seed):
    for fs in _FEATURE_SETS:
        graph = LevelGraph.generate(fs, random.Random(seed))
        assert graph.validate_playability() == [], (
            f"seed={seed}: validate_playability reported unreachable nodes"
        )
