"""Tests for Transformation 2: Abstract Graph → Positioned Graph.

Mathematical Invariant L (Layout Faithfulness)
==============================================
For star-topology graphs G (all rooms connect to the corridor node) with
horizontal, vertical, or off_centre layout strategy:
    validate_layout(G, placed, walls) = []

where placed = layout_graph(G, strategy=S)
and   walls  = derive_walls(G, placed)[0].

Proof sketch for horizontal strategy (vertical is symmetric):

  Let the corridor span rows [cor_row, cor_row+h−1], all columns [MIN_C, MAX_C].
  Each room R is placed in a band immediately adjacent to the corridor,
  separated by exactly one wall row W_row.

  Claim: ∀R, _find_connection_tile(R, corridor) ≠ None.

  The wall tile (c, W_row) for any column c in R's column range satisfies:
    • (c, W_row − 1) or (c, W_row + 1) is in R.floor_tiles  (R is in the band)
    • (c, W_row + 1) or (c, W_row − 1) is in corridor.floor_tiles  (corridor spans all columns)
  → (c, W_row) is adjacent to floor tiles of both R and corridor.
  → _find_connection_tile finds it.

  Since all edges in a star-topology graph are corridor↔room edges,
  and all such edges are realised, validate_layout passes. □

Corollary: derive_walls() must RAISE if a connected pair has no shared
boundary (not silently drop the edge). This corollary is tested in
test_missing_connection_raises.

These tests are RED until:
  • the silent `continue` in derive_walls() becomes a ValueError raise
  (spec/0010-level-gen-refactor.md, step 2)
"""
import random
import pytest
from hypothesis import given, settings, strategies as st

from levelgraph import LevelGraph, EdgeType, NodeSize
from levellayout import (
    layout_graph, derive_walls, validate_layout, PlacedNode, build_level_dict,
    MIN_C, MAX_C, MIN_R, MAX_R,
)
from tests.conftest import FS_ALL, FS_OPEN, FS_LOCKED, FS_GATED, ALL_FEATURE_SETS

VALID_STRATEGIES = ['horizontal', 'vertical', 'off_centre', 't', 'double_t', 'z', 'l']


# ── Unit tests ────────────────────────────────────────────────────────────────

class TestLayoutFaithfulness:

    def _full_validate(self, graph, strategy, seed=0):
        rng = random.Random(seed)
        placed = layout_graph(graph, rng=rng, strategies=[strategy])
        walls, _ = derive_walls(graph, placed)
        return validate_layout(graph, placed, walls)

    def test_horizontal_simple(self):
        graph = LevelGraph.generate(FS_OPEN, rng=random.Random(0))
        assert self._full_validate(graph, 'horizontal') == []

    def test_vertical_simple(self):
        graph = LevelGraph.generate(FS_OPEN, rng=random.Random(1))
        assert self._full_validate(graph, 'vertical') == []

    def test_off_centre_simple(self):
        graph = LevelGraph.generate(FS_OPEN, rng=random.Random(2))
        assert self._full_validate(graph, 'off_centre') == []

    def test_horizontal_with_locks_and_gates(self):
        graph = LevelGraph.generate(FS_ALL, rng=random.Random(3))
        assert self._full_validate(graph, 'horizontal') == []

    def test_vertical_with_locks_and_gates(self):
        graph = LevelGraph.generate(FS_ALL, rng=random.Random(4))
        assert self._full_validate(graph, 'vertical') == []

    def test_off_centre_with_locks_and_gates(self):
        graph = LevelGraph.generate(FS_ALL, rng=random.Random(5))
        assert self._full_validate(graph, 'off_centre') == []

    def test_missing_connection_raises_not_silently_skipped(self):
        """derive_walls() must raise ValueError when an edge has no shared
        boundary tile. Current code silently skips it — this test will FAIL
        until the silent `continue` is promoted to a raise."""
        from levelgraph import LevelGraph as G2, EdgeType, NodeSize
        graph = G2()
        graph.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        graph.add_node('room_0',   NodeSize.ROOM)
        graph.add_edge('corridor', 'room_0', EdgeType.OPEN)

        # Place nodes with no shared boundary (corridor top-left, room bottom-right)
        placed = {
            'corridor': PlacedNode('corridor',  1,  1,  5, 2),
            'room_0':   PlacedNode('room_0',   22, 11,  5, 3),
        }
        with pytest.raises(ValueError, match="no shared boundary"):
            derive_walls(graph, placed)

    def test_t_strategy_available(self):
        from levellayout import STRATEGIES
        assert 't' in STRATEGIES

    def test_double_t_strategy_available(self):
        from levellayout import STRATEGIES
        assert 'double_t' in STRATEGIES

    def test_z_strategy_available(self):
        from levellayout import STRATEGIES
        assert 'z' in STRATEGIES


# ── Property-based tests: Invariant L holds for all seeds ─────────────────────

@pytest.mark.parametrize('strategy', VALID_STRATEGIES)
@given(seed=st.integers(min_value=0, max_value=2**31 - 1))
@settings(max_examples=150)
def test_invariant_l_all_edges_realised(strategy, seed):
    """INVARIANT L: for horizontal/vertical/off_centre, validate_layout = []."""
    rng = random.Random(seed)
    graph = LevelGraph.generate(FS_ALL, rng=rng)
    placed = layout_graph(graph, rng=random.Random(seed), strategies=[strategy])
    walls, _ = derive_walls(graph, placed)
    errors = validate_layout(graph, placed, walls)
    assert errors == [], f"strategy={strategy!r}, seed={seed}: {errors}"


@pytest.mark.parametrize('fs', ALL_FEATURE_SETS)
@given(seed=st.integers(min_value=0, max_value=2**31 - 1))
@settings(max_examples=100)
def test_invariant_l_all_feature_sets(fs, seed):
    """Invariant L must hold for every canonical feature set."""
    rng = random.Random(seed)
    graph = LevelGraph.generate(fs, rng=rng)
    strategy = random.Random(seed + 1).choice(VALID_STRATEGIES)
    placed = layout_graph(graph, rng=random.Random(seed + 2),
                          strategies=[strategy])
    walls, _ = derive_walls(graph, placed)
    errors = validate_layout(graph, placed, walls)
    assert errors == [], f"fs={fs['edge_types']}, seed={seed}: {errors}"


# ── Fix A: L-corridor orientation ─────────────────────────────────────────────

@pytest.mark.parametrize('required_exits,expected_sides', [
    (frozenset({'top',    'right'}), {'top',    'right'}),
    (frozenset({'top',    'left'}),  {'top',    'left'}),
    (frozenset({'bottom', 'right'}), {'bottom', 'right'}),
    (frozenset({'bottom', 'left'}),  {'bottom', 'left'}),
])
def test_l_orientation_matches_required_exits(required_exits, expected_sides):
    """L-corridor floor tiles must touch the correct pair of grid borders."""
    for seed in range(5):
        rng = random.Random(seed)
        graph = LevelGraph.generate(FS_OPEN, rng=rng)
        placed = layout_graph(graph, rng=random.Random(seed),
                              strategies=['l'],
                              required_exits=required_exits)
        corridor_name = next(
            n for n, node in graph.nodes.items()
            if node.size == NodeSize.CORRIDOR)
        tiles = placed[corridor_name].floor_tiles

        for side in expected_sides:
            if side == 'top':
                assert any(r == MIN_R for (c, r) in tiles), \
                    f"seed={seed}, exits={required_exits}: no top exit"
            elif side == 'bottom':
                assert any(r == MAX_R for (c, r) in tiles), \
                    f"seed={seed}, exits={required_exits}: no bottom exit"
            elif side == 'left':
                assert any(c == MIN_C for (c, r) in tiles), \
                    f"seed={seed}, exits={required_exits}: no left exit"
            elif side == 'right':
                assert any(c == MAX_C for (c, r) in tiles), \
                    f"seed={seed}, exits={required_exits}: no right exit"


# ── Fix C: Z-corridor single-stroke shape ─────────────────────────────────────

@pytest.mark.parametrize('seed', range(10))
def test_z_corridor_not_full_width_arm(seed):
    """Z-corridor must not produce a full-width or full-height arm."""
    rng = random.Random(seed)
    graph = LevelGraph.generate(FS_OPEN, rng=rng)
    placed = layout_graph(graph, rng=random.Random(seed), strategies=['z'])
    corridor_name = next(
        n for n, node in graph.nodes.items()
        if node.size == NodeSize.CORRIDOR)
    tiles = placed[corridor_name].floor_tiles

    all_interior_cols = set(range(MIN_C, MAX_C + 1))
    all_interior_rows = set(range(MIN_R, MAX_R + 1))

    for row in range(MIN_R, MAX_R + 1):
        row_cols = {c for (c, r) in tiles if r == row}
        assert row_cols != all_interior_cols, \
            f"seed={seed}: row {row} fully covered (H-shape arm)"

    for col in range(MIN_C, MAX_C + 1):
        col_rows = {r for (c, r) in tiles if c == col}
        assert col_rows != all_interior_rows, \
            f"seed={seed}: col {col} fully covered (I-shape arm)"


# ── Spec 0021: Room-count-driven strategy selection ───────────────────────────

class TestStrategyMaxZones:
    def test_constant_exists(self):
        from levellayout import _STRATEGY_MAX_ZONES
        assert isinstance(_STRATEGY_MAX_ZONES, dict)

    def test_simple_strategies_have_max_2(self):
        from levellayout import _STRATEGY_MAX_ZONES
        for s in ['horizontal', 'vertical', 'off_centre']:
            assert _STRATEGY_MAX_ZONES[s] == 2, f"{s} should have max_zones=2"

    def test_t_has_max_3(self):
        from levellayout import _STRATEGY_MAX_ZONES
        assert _STRATEGY_MAX_ZONES['t'] == 3

    def test_heavy_strategies_have_max_4(self):
        from levellayout import _STRATEGY_MAX_ZONES
        for s in ['double_t', 'z', 'l']:
            assert _STRATEGY_MAX_ZONES[s] == 4, f"{s} should have max_zones=4"

    def test_all_strategies_covered(self):
        from levellayout import _STRATEGY_MAX_ZONES, STRATEGIES
        for s in STRATEGIES:
            assert s in _STRATEGY_MAX_ZONES, f"{s} missing from _STRATEGY_MAX_ZONES"


class TestPickStrategyRoomCount:
    def test_n_rooms_2_never_picks_4zone(self):
        from levellayout import _pick_strategy, _STRATEGY_MAX_ZONES, STRATEGIES
        for seed in range(200):
            result = _pick_strategy(frozenset(), STRATEGIES, random.Random(seed), n_rooms=2)
            assert _STRATEGY_MAX_ZONES.get(result, 2) <= 2, \
                f"seed={seed}: picked {result!r} (max_zones={_STRATEGY_MAX_ZONES.get(result)}) for n_rooms=2"

    def test_n_rooms_3_allows_t_not_4zone(self):
        from levellayout import _pick_strategy, _STRATEGY_MAX_ZONES, STRATEGIES
        results = {_pick_strategy(frozenset(), STRATEGIES, random.Random(s), n_rooms=3)
                   for s in range(200)}
        assert 't' in results, "t (max_zones=3) should be chosen with n_rooms=3"
        for r in results:
            assert _STRATEGY_MAX_ZONES.get(r, 2) <= 3, \
                f"picked {r!r} (max_zones={_STRATEGY_MAX_ZONES.get(r)}) for n_rooms=3"

    def test_n_rooms_4_allows_heavy_strategies(self):
        from levellayout import _pick_strategy, STRATEGIES
        results = {_pick_strategy(frozenset(), STRATEGIES, random.Random(s), n_rooms=4)
                   for s in range(200)}
        assert 'double_t' in results or 'z' in results or 'l' in results, \
            "4-zone strategies should be eligible with n_rooms=4"

    def test_single_strategy_override_not_filtered(self):
        """len(available)==1 passes through without room-count filtering."""
        from levellayout import _pick_strategy
        result = _pick_strategy(frozenset(), ['double_t'], random.Random(0), n_rooms=2)
        assert result == 'double_t'


@pytest.mark.parametrize('seed', range(20))
def test_layout_graph_2room_no_heavy_strategy(seed):
    """With 2 regular rooms and the full strategy pool, layout_graph must not
    pick a strategy with max_zones > 2 (which would leave empty wall zones)."""
    from levellayout import _STRATEGY_MAX_ZONES, STRATEGIES
    graph = LevelGraph()
    graph.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
    graph.add_node('r0', NodeSize.ROOM)
    graph.add_node('r1', NodeSize.ROOM)
    graph.add_edge('corridor', 'r0', EdgeType.OPEN)
    graph.add_edge('corridor', 'r1', EdgeType.OPEN)

    placed = layout_graph(graph, rng=random.Random(seed))
    walls, _ = derive_walls(graph, placed)
    errors = validate_layout(graph, placed, walls)
    assert errors == [], f"seed={seed}: {errors}"

    corridor_name = next(
        n for n, node in graph.nodes.items() if node.size == NodeSize.CORRIDOR)
    corridor_tiles = placed[corridor_name].floor_tiles

    # Infer which strategy was chosen by checking whether the corridor's
    # floor touches all four border rows/cols — a necessary consequence of
    # double_t / z / l being chosen, which would be invalid for n_rooms=2.
    touches_all_lr = (any(c == MIN_C for (c, r) in corridor_tiles) and
                      any(c == MAX_C for (c, r) in corridor_tiles))
    touches_all_tb = (any(r == MIN_R for (c, r) in corridor_tiles) and
                      any(r == MAX_R for (c, r) in corridor_tiles))
    assert not (touches_all_lr and touches_all_tb), \
        f"seed={seed}: corridor touches all 4 borders — double_t/z chosen for 2-room graph"
