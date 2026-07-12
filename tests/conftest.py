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

FS_FLAMES = {
    'room_count':     (3, 5),
    'edge_types':     [EdgeType.OPEN, EdgeType.BREAKABLE],
    'node_sizes':     [NodeSize.ROOM, NodeSize.HALL],
    'treasure_count': (3, 6),
    'material_types': [],
    'material_count': (0, 0),
    'enemy_count':    (1, 2),
    'has_flames':     True,
}

FS_WATER_FLAMES = {
    'room_count':     (4, 6),
    'edge_types':     [EdgeType.OPEN, EdgeType.BREAKABLE, EdgeType.WATER],
    'node_sizes':     [NodeSize.ROOM, NodeSize.HALL],
    'treasure_count': (4, 8),
    'material_types': ['planks'],
    'material_count': (0, 0),
    'enemy_count':    (1, 2),
    'has_flames':     True,
}

ALL_FEATURE_SETS = [FS_OPEN, FS_LOCKED, FS_GATED, FS_WATER, FS_ALL]


@pytest.fixture(params=range(20))
def rng(request):
    """Deterministic RNG seeded by the parametrize index."""
    return random.Random(request.param)


@pytest.fixture(scope='session', autouse=True)
def _layout_log_to_tmp(tmp_path_factory):
    """Spec 0065: escaping LayoutErrors append to a diagnostic log file.
    Redirect it for the whole suite so tests never pollute the working
    directory.  Session-scoped: a function-scoped autouse fixture would
    trip hypothesis's function_scoped_fixture health check on every
    @given test."""
    import levellayout
    old = getattr(levellayout, 'LAYOUT_LOG_PATH', None)
    levellayout.LAYOUT_LOG_PATH = str(
        tmp_path_factory.mktemp('layout-log') / 'uglycraft-layout.log')
    yield
    levellayout.LAYOUT_LOG_PATH = old
