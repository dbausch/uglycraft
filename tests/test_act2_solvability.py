"""End-to-end solvability / regression invariants for built levels.

Covers the recent water (spec 0029) and key (spec 0030) findings together with a
broad regression over the REAL Act 2 feature sets (the shipping content).

Note: ``build_level_dict`` already raises if ``validate_layout`` or
``validate_push_puzzles`` fail, so a successful build already proves the layout
faithfully represents the graph and every push puzzle is solvable.  These tests
add the layout-level guarantees build_level_dict does NOT itself enforce:

  - placed-node keys and planks all survive into the level dict (K1 / W1)
  - every locked door (interior + border) has a surviving key — no soft-lock (K2)
  - every water tile maps 1:1 to a water room, and there are enough planks to
    craft one bridge per water room (W4 + water economy)
  - player_start is a passable floor tile
  - every multi-grid exit points to a real grid and has a reciprocal exit
"""
import random

import pytest
from hypothesis import given, settings, strategies as st

from uglycraft.levelgraph import LevelGraph, EdgeType
from uglycraft.levellayout import build_level_dict, LayoutError
from uglycraft.levels import ACT2_FEATURE_SETS
from tests.conftest import FS_LOCKED, FS_GATED, FS_WATER, FS_ALL
from tests.test_key_placement import FS_CROWDED_LOCKED
from tests.test_water_challenge import FS_CROWDED_WATER


def _build(fs, seed):
    """Build a level, mirroring _generate_act2_level's retry-on-LayoutError."""
    base = random.Random(seed)
    for _ in range(50):
        rng = random.Random(base.randint(0, 2**31))
        graph = LevelGraph.generate(fs, rng)
        try:
            level = build_level_dict(
                graph, rng=rng, strategies=fs.get('layout_strategies'),
                grid_count=fs.get('grid_count', 1))
            return graph, level
        except LayoutError:
            continue
    raise AssertionError(f"build never succeeded for seed={seed}")


def assert_layout_solvable(graph, level):
    # K1 / W1 / C7 — every key and plank survives into the level dict (an
    # un-carvable closet or dropped room spills its content; spec 0032 C7).
    keys_dict = sum(len(rd.get('keys', [])) for rd in level['rooms'].values())
    keys_graph = sum(len(nd.keys) for nd in graph.nodes.values())
    assert keys_dict == keys_graph, "a key was lost"

    planks_dict = sum(1 for rd in level['rooms'].values()
                      for m in rd.get('materials', []) if m[2] == 'planks')
    planks_graph = sum(sum(1 for m in nd.materials if m == ('planks',))
                       for nd in graph.nodes.values())
    assert planks_dict == planks_graph, "a plank was lost"

    # K2 — every locked door (interior + border) has a surviving key.
    key_colours = {k[2] for rd in level['rooms'].values()
                   for k in rd.get('keys', [])}
    for rd in level['rooms'].values():
        for door in rd.get('locked_doors', []):
            assert door[2] in key_colours, f"soft-lock: door {door} has no key"

    # W4 + water economy — every water tile maps 1:1 to a real water room, and
    # there are enough planks to craft one bridge (2 planks) per water room.
    real_water_rooms = {e.node_b for e in graph.edges
                        if e.edge_type == EdgeType.WATER}
    water_rooms = set()
    for rd in level['rooms'].values():
        water = {tuple(t) for t in rd.get('water_tiles', [])}
        mapping = {tuple(k): v for k, v in rd.get('water_tile_room', {}).items()}
        assert set(mapping) == water, "water tiles not 1:1 mapped to a water room"
        for name in mapping.values():
            assert name in real_water_rooms, f"{name!r} is not a water room"
        water_rooms.update(mapping.values())
    assert planks_dict // 2 >= len(water_rooms), (
        f"{planks_dict // 2} craftable bridges for {len(water_rooms)} water rooms")

    # player_start is a passable floor tile of the start room.
    start = level['rooms'][level['start_room']]
    ps = tuple(level['player_start'])
    assert ps not in start['walls'], "player_start is inside a wall"

    # Multi-grid exits: each exit targets a real grid with a reciprocal exit.
    for gname, rd in level['rooms'].items():
        for exit_key, target in rd.get('exits', {}).items():
            assert target in level['rooms'], f"exit {exit_key} -> missing {target}"
            back = level['rooms'][target].get('exits', {})
            assert gname in back.values(), (
                f"no reciprocal exit from {target} back to {gname}")


# ── Broad cheap regression: single-grid feature sets, many seeds ─────────────

_CHEAP_SETS = (FS_LOCKED, FS_GATED, FS_WATER, FS_ALL)


@pytest.mark.parametrize('fs', _CHEAP_SETS)
@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=60, deadline=None)
def test_single_grid_levels_solvable(fs, seed):
    graph, level = _build(fs, seed)
    assert_layout_solvable(graph, level)


# ── Crowded multi-grid: exercises border doors + multi-water-room grids ──────

_CROWDED_SETS = (FS_CROWDED_LOCKED, FS_CROWDED_WATER)


@pytest.mark.parametrize('fs', _CROWDED_SETS)
@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=25, deadline=None)
def test_crowded_multigrid_levels_solvable(fs, seed):
    graph, level = _build(fs, seed)
    assert_layout_solvable(graph, level)


# ── Regression over the REAL Act 2 feature sets (shipping content) ───────────

@pytest.mark.parametrize('idx', range(len(ACT2_FEATURE_SETS)))
@pytest.mark.parametrize('seed', [0, 1, 2])
def test_real_act2_levels_solvable(idx, seed):
    fs = ACT2_FEATURE_SETS[idx]
    graph, level = _build(fs, seed * 100 + idx)
    assert_layout_solvable(graph, level)
