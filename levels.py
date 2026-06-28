"""
Level definitions for a 30×16 grid (0-indexed).
Border cells (col 0, col 29, row 0, row 15) are always walls — not listed here.
All coordinates are interior: cols 1-28, rows 1-14.

enemy_starts is a list of positions; EASY always uses only the first one,
HARD uses all of them (1 enemy for levels 1-3, 2 for 4-6, 3 for 7-9).

Act 2 levels (11+) are generated lazily from graph-based feature sets on first
access via get_level(); see the Act 2 section below (spec 0028 / BL-11).
"""
from constants import COLS, ROWS


def _hwall(x1, x2, y):
    return [(x, y) for x in range(x1, x2 + 1)]


def _vwall(x, y1, y2):
    return [(x, y) for y in range(y1, y2 + 1)]


def _make_walls(*segments):
    walls = set()
    for seg in segments:
        walls.update(seg)
    walls = {(c, r) for c, r in walls if 1 <= c <= COLS - 2 and 1 <= r <= ROWS - 2}
    return walls


# ── Act 1 levels (hand-authored, unchanged) ──────────────────────────────────

LEVELS = [

    # 1 ── Open field
    {
        'player_start':  (15, 8),
        'enemy_starts': [(2, 8)],
        'walls': _make_walls(),
    },

    # 2 ── Single horizontal wall
    {
        'player_start':  (15, 3),
        'enemy_starts': [(2, 8)],
        'walls': _make_walls(
            _hwall(6, 23, 7),
        ),
    },

    # 3 ── H-shape: two verticals + horizontal with centre gap
    {
        'player_start':  (15, 4),
        'enemy_starts': [(2, 8)],
        'walls': _make_walls(
            _vwall(7,  3, 11),
            _vwall(22, 3, 11),
            _hwall(7,  13, 7),
            _hwall(16, 22, 7),
        ),
    },

    # 4 ── Short pillars + horizontal wall with gap ── 2 enemies
    {
        'player_start':  (15, 4),
        'enemy_starts': [(2, 4),
                         (27, 11)],
        'walls': _make_walls(
            _vwall(5,  2, 6),
            _vwall(24, 2, 6),
            _vwall(5,  9, 13),
            _vwall(24, 9, 13),
            _hwall(2,  13, 8),
            _hwall(16, 27, 8),
        ),
    },

    # 5 ── Cage with openings ── 2 enemies
    {
        'player_start':  (15, 8),
        'enemy_starts': [(27, 8),
                         (2, 12)],
        'walls': _make_walls(
            _vwall(7,  3, 12),
            _vwall(22, 3, 12),
            _hwall(8,  21, 3),
            _hwall(8,  12, 12),
            _hwall(17, 21, 12),
        ),
    },

    # 6 ── Grid of pillars ── 2 enemies
    {
        'player_start':  (28, 3),
        'enemy_starts': [(2, 8),
                         (3, 13)],
        'walls': _make_walls(
            *[_vwall(c, 2, 6)  for c in (2, 7, 20, 25)],
            *[_vwall(c, 9, 13) for c in (2, 7, 20, 25)],
            *[_hwall(12, 17, r) for r in (2, 4, 6)],
            *[_hwall(12, 17, r) for r in (9, 11, 13)],
            *[_vwall(c, 2, 6)  for c in (4, 9, 22, 27)],
            *[_vwall(c, 9, 13) for c in (4, 9, 22, 27)],
        ),
    },

    # 7 ── Three sealed vaults ── 3 enemies
    {
        'player_start':  (14, 1),
        'enemy_starts': [(2,  8),
                         (27, 8),
                         (14, 14)],
        'walls': _make_walls(
            _hwall(2, 10, 2), _hwall(2, 10, 7),
            _vwall(2, 2, 7),  _vwall(10, 2, 7),
            _hwall(19, 27, 2), _hwall(19, 27, 7),
            _vwall(19, 2, 7),  _vwall(27, 2, 7),
            _hwall(9, 20, 9),  _hwall(9, 20, 13),
            _vwall(9, 9, 13),  _vwall(20, 9, 13),
        ),
    },

    # 8 ── Slalom ── 3 enemies
    {
        'player_start':  (27, 3),
        'enemy_starts': [(2, 12),
                         (13, 2),
                         (23, 12)],
        'walls': _make_walls(
            _vwall(6,  1, 11),
            _vwall(12, 4, 14),
            _vwall(18, 1, 11),
            _vwall(24, 4, 14),
        ),
    },

    # 9 ── Divided chambers ── 3 enemies
    {
        'player_start':  (15, 8),
        'enemy_starts': [(2, 8),
                         (27, 8),
                         (2, 13)],
        'walls': _make_walls(
            _vwall(14, 1, 5),
            _vwall(14, 10, 14),
            _vwall(15, 1, 5),
            _vwall(15, 10, 14),
            _hwall(2, 12,  5),
            _hwall(2, 12, 10),
            _hwall(17, 27,  5),
            _hwall(17, 27, 10),
        ),
    },

    # 10 ── Boss level
    {
        'player_start':  (2, 7),
        'enemy_starts': [(27, 7)],
        'crown_pos':     (14, 7),
        'walls': _make_walls(
            _hwall(9,  20,  2), _hwall(9,  20, 12),
            _vwall(9,   2, 12), _vwall(20,  2, 12),
            _hwall(11, 18,  4), _hwall(11, 18, 10),
            _vwall(11,  4, 10), _vwall(18,  4, 10),
            _hwall(13, 16,  6), _hwall(13, 16,  8),
            _vwall(13,  6,  8), _vwall(16,  6,  8),
            _vwall(4,  1,  4), _vwall(25,  1,  4),
            _vwall(4, 10, 14), _vwall(25, 10, 14),
            [(7, 2)],  [(22, 2)],
            [(7, 13)], [(22, 13)],
            [(5, 5)],  [(24, 5)],
            [(5, 10)], [(6, 10)], [(23, 10)], [(24, 10)],
            [(7, 7)],  [(22, 7)],
            [(10, 14)], [(13, 13)], [(16, 14)], [(19, 13)],
        ),
    },
]


# ── Act 2 levels (generated lazily from graph-based feature sets) ─────────────
#
# Levels 11-20 are procedurally generated and expensive to build (up to ~3.6 s
# for a 10-grid level).  They are generated one at a time, on first access, and
# cached for the rest of the game (spec 0028 / BL-11).  Nothing is generated at
# import time.  A new game calls new_game_levels() to pick a fresh seed and
# clear the cache, so each game gets fresh random levels without any up-front
# generation cost.

import random as _rnd
from levelgraph import LevelGraph, EdgeType, NodeSize
from levellayout import build_level_dict, LayoutError
from crafting import MAT_ROCKS, MAT_PLANKS, MAT_METAL


def _act2_feature_sets():
    return [
        # Level 11: 1 grid — open + breakable only
        {
            'room_count': (6, 8),
            'edge_types': [EdgeType.OPEN, EdgeType.OPEN, EdgeType.BREAKABLE],
            'node_sizes': [NodeSize.ROOM, NodeSize.HALL],
            'treasure_count': (6, 8),
            'material_types': [MAT_ROCKS, MAT_PLANKS],
            'material_count': (4, 6),
            'enemy_count': (1, 2),
            'layout_strategies': ['horizontal', 'vertical', 'double_t', 't', 'z', 'l'],
            'grid_count': 1,
        },
        # Level 12: 2 grids — + locked doors
        {
            'room_count': (6, 8),
            'edge_types': [EdgeType.OPEN, EdgeType.BREAKABLE, EdgeType.LOCKED],
            'node_sizes': [NodeSize.ROOM, NodeSize.HALL],
            'treasure_count': (6, 8),
            'material_types': [MAT_ROCKS, MAT_PLANKS, MAT_METAL],
            'material_count': (4, 8),
            'enemy_count': (1, 3),
            'layout_strategies': ['horizontal', 'vertical', 'double_t', 't', 'z'],
            'grid_count': 2,
        },
        # Level 13: 3 grids — + gates
        {
            'room_count': (8, 10),
            'edge_types': [EdgeType.OPEN, EdgeType.BREAKABLE,
                           EdgeType.LOCKED, EdgeType.GATED],
            'node_sizes': [NodeSize.ROOM, NodeSize.HALL],
            'treasure_count': (6, 10),
            'material_types': [MAT_ROCKS, MAT_PLANKS, MAT_METAL],
            'material_count': (5, 8),
            'enemy_count': (2, 3),
            'layout_strategies': ['horizontal', 'vertical', 'off_centre', 'double_t', 't', 'z'],
            'grid_count': 3,
        },
        # Level 14: 4 grids — + water streams
        {
            'room_count': (8, 10),
            'edge_types': [EdgeType.OPEN, EdgeType.BREAKABLE,
                           EdgeType.LOCKED, EdgeType.WATER],
            'node_sizes': [NodeSize.ROOM, NodeSize.HALL],
            'treasure_count': (6, 10),
            'material_types': [MAT_ROCKS, MAT_PLANKS, MAT_METAL],
            'material_count': (5, 8),
            'enemy_count': (2, 3),
            'layout_strategies': ['horizontal', 'vertical', 'off_centre', 'double_t', 't', 'z'],
            'grid_count': 4,
        },
        # Level 15: 5 grids — + flame jets
        {
            'room_count': (8, 10),
            'edge_types': [EdgeType.OPEN, EdgeType.BREAKABLE,
                           EdgeType.LOCKED, EdgeType.GATED, EdgeType.WATER],
            'node_sizes': [NodeSize.ROOM, NodeSize.HALL],
            'treasure_count': (8, 12),
            'material_types': [MAT_ROCKS, MAT_PLANKS, MAT_METAL],
            'material_count': (6, 10),
            'enemy_count': (2, 4),
            'has_flames': True,
            'closet_count': (1, 2),
            'layout_strategies': ['horizontal', 'vertical', 'off_centre', 'double_t', 't', 'z'],
            'grid_count': 5,
        },
        # Level 16: 6 grids — + forge ogre
        {
            'room_count': (8, 10),
            'edge_types': [EdgeType.OPEN, EdgeType.BREAKABLE,
                           EdgeType.LOCKED, EdgeType.GATED, EdgeType.WATER],
            'node_sizes': [NodeSize.ROOM, NodeSize.HALL],
            'treasure_count': (8, 12),
            'material_types': [MAT_ROCKS, MAT_PLANKS, MAT_METAL],
            'material_count': (6, 10),
            'enemy_count': (3, 4),
            'has_flames': True,
            'has_forge_ogre': True,
            'closet_count': (1, 2),
            'layout_strategies': ['horizontal', 'vertical', 'off_centre', 'double_t', 't', 'z'],
            'grid_count': 6,
        },
        # Level 17: 7 grids
        {
            'room_count': (9, 12),
            'edge_types': [EdgeType.OPEN, EdgeType.BREAKABLE,
                           EdgeType.LOCKED, EdgeType.GATED, EdgeType.WATER],
            'node_sizes': [NodeSize.ROOM, NodeSize.HALL],
            'treasure_count': (10, 14),
            'material_types': [MAT_ROCKS, MAT_PLANKS, MAT_METAL],
            'material_count': (8, 12),
            'enemy_count': (3, 5),
            'has_flames': True,
            'has_forge_ogre': True,
            'closet_count': (1, 3),
            'layout_strategies': ['horizontal', 'vertical', 'off_centre', 'double_t', 't', 'z'],
            'grid_count': 7,
        },
        # Level 18: 8 grids
        {
            'room_count': (9, 12),
            'edge_types': [EdgeType.OPEN, EdgeType.BREAKABLE,
                           EdgeType.LOCKED, EdgeType.GATED, EdgeType.WATER],
            'node_sizes': [NodeSize.ROOM, NodeSize.HALL],
            'treasure_count': (12, 16),
            'material_types': [MAT_ROCKS, MAT_PLANKS, MAT_METAL],
            'material_count': (8, 14),
            'enemy_count': (4, 6),
            'has_flames': True,
            'has_forge_ogre': True,
            'closet_count': (1, 3),
            'layout_strategies': ['horizontal', 'vertical', 'off_centre', 'double_t', 't', 'z'],
            'grid_count': 8,
        },
        # Level 19: 9 grids
        {
            'room_count': (9, 12),
            'edge_types': [EdgeType.OPEN, EdgeType.BREAKABLE,
                           EdgeType.LOCKED, EdgeType.GATED, EdgeType.WATER],
            'node_sizes': [NodeSize.ROOM, NodeSize.HALL],
            'treasure_count': (14, 18),
            'material_types': [MAT_ROCKS, MAT_PLANKS, MAT_METAL],
            'material_count': (10, 16),
            'enemy_count': (5, 7),
            'has_flames': True,
            'has_forge_ogre': True,
            'closet_count': (1, 3),
            'layout_strategies': ['horizontal', 'vertical', 'off_centre', 'double_t', 't', 'z'],
            'grid_count': 9,
        },
        # Level 20: 10 grids
        {
            'room_count': (9, 12),
            'edge_types': [EdgeType.OPEN, EdgeType.BREAKABLE,
                           EdgeType.LOCKED, EdgeType.GATED, EdgeType.WATER],
            'node_sizes': [NodeSize.ROOM, NodeSize.HALL],
            'treasure_count': (10, 14),
            'material_types': [MAT_ROCKS, MAT_PLANKS, MAT_METAL],
            'material_count': (8, 12),
            'enemy_count': (4, 6),
            'has_flames': True,
            'has_forge_ogre': True,
            'closet_count': (1, 2),
            'layout_strategies': ['horizontal', 'vertical', 'off_centre', 'double_t', 't', 'z'],
            'grid_count': 10,
        },
    ]


_ACT1_COUNT = len(LEVELS)
ACT2_FEATURE_SETS = _act2_feature_sets()
TOTAL_LEVELS = _ACT1_COUNT + len(ACT2_FEATURE_SETS)

# Per-game state for lazy Act 2 generation.
_game_seed = _rnd.Random().randint(0, 2**31)   # base seed for the current game
_act2_cache = {}                               # level_num -> generated level dict


def _generate_act2_level(index, progress=None, base_rng=None):
    """Generate a single Act 2 level dict (0-based index into ACT2_FEATURE_SETS).

    By default uses a seed derived deterministically from _game_seed and the
    index, so the same game always produces the same level for a given index.
    Pass an explicit base_rng (e.g. fresh entropy) to force a different level.
    Retries with a fresh sub-seed on LayoutError (rare, always resolves).
    """
    features = ACT2_FEATURE_SETS[index]
    strats   = features.get('layout_strategies')
    grids    = features.get('grid_count', 1)
    if base_rng is None:
        base_rng = _rnd.Random(_game_seed + index)
    while True:
        rng = _rnd.Random(base_rng.randint(0, 2**31))
        graph = LevelGraph.generate(features, rng=rng)
        try:
            return build_level_dict(graph, rng=rng, strategies=strats,
                                    grid_count=grids, progress=progress)
        except LayoutError:
            pass   # base_rng advances; next iteration uses a fresh sub-seed


def get_level(level_num, progress=None):
    """Return the level dict for level_num (1-based), generating Act 2 lazily.

    Act 1 levels (1.._ACT1_COUNT) are the hand-authored dicts.  Act 2 levels are
    generated on first access and cached.  `progress(done, total)` is forwarded
    to the generator so callers can render a loading indicator.
    """
    if level_num <= _ACT1_COUNT:
        return LEVELS[level_num - 1]
    if level_num not in _act2_cache:
        _act2_cache[level_num] = _generate_act2_level(
            level_num - _ACT1_COUNT - 1, progress=progress)
    return _act2_cache[level_num]


def regenerate_level(level_num):
    """Force-regenerate a single Act 2 level with fresh entropy.

    Used when a generated level is found to be unplayable (e.g. a stuck push
    block): replaces the cached level with a different one.  Returns the new dict.
    """
    if level_num <= _ACT1_COUNT:
        return LEVELS[level_num - 1]
    index = level_num - _ACT1_COUNT - 1
    _act2_cache[level_num] = _generate_act2_level(index, base_rng=_rnd.Random())
    return _act2_cache[level_num]


def new_game_levels():
    """Start a fresh game: pick a new seed and clear the Act 2 cache.

    Generates nothing — each Act 2 level is built on first access by get_level().
    """
    global _game_seed
    new_seed = _rnd.Random().randint(0, 2**31)
    if new_seed == _game_seed:                 # guarantee a visible reshuffle
        new_seed = (new_seed + 1) % (2**31)
    _game_seed = new_seed
    _act2_cache.clear()
