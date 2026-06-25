"""Shared fixtures and feature-set constants for the level-gen test suite."""
import random
import pytest
from levelgraph import LevelGraph, EdgeType, NodeSize


# ── Canonical feature sets used across test files ─────────────────────────────

FS_OPEN = {
    'room_count':     (2, 4),
    'edge_types':     [EdgeType.OPEN],
    'node_sizes':     [NodeSize.ROOM],
    'treasure_count': (2, 4),
    'material_types': [],
    'material_count': (0, 0),
    'enemy_count':    (0, 0),
}

FS_LOCKED = {
    'room_count':     (3, 5),
    'edge_types':     [EdgeType.OPEN, EdgeType.LOCKED],
    'node_sizes':     [NodeSize.ROOM, NodeSize.HALL],
    'treasure_count': (3, 5),
    'material_types': [],
    'material_count': (0, 0),
    'enemy_count':    (0, 0),
}

FS_GATED = {
    'room_count':     (3, 5),
    'edge_types':     [EdgeType.OPEN, EdgeType.GATED],
    'node_sizes':     [NodeSize.ROOM, NodeSize.HALL],
    'treasure_count': (3, 5),
    'material_types': [],
    'material_count': (0, 0),
    'enemy_count':    (0, 0),
}

FS_WATER = {
    'room_count':     (3, 5),
    'edge_types':     [EdgeType.OPEN, EdgeType.WATER],
    'node_sizes':     [NodeSize.ROOM, NodeSize.HALL],
    'treasure_count': (3, 5),
    'material_types': ['planks'],
    'material_count': (0, 0),
    'enemy_count':    (0, 0),
}

FS_ALL = {
    'room_count':     (4, 6),
    'edge_types':     [EdgeType.OPEN, EdgeType.BREAKABLE,
                       EdgeType.LOCKED, EdgeType.GATED],
    'node_sizes':     [NodeSize.ROOM, NodeSize.HALL],
    'treasure_count': (4, 8),
    'material_types': ['rocks', 'planks', 'metal'],
    'material_count': (3, 6),
    'enemy_count':    (1, 3),
}

ALL_FEATURE_SETS = [FS_OPEN, FS_LOCKED, FS_GATED, FS_WATER, FS_ALL]


@pytest.fixture(params=range(20))
def rng(request):
    """Deterministic RNG seeded by the parametrize index."""
    return random.Random(request.param)
