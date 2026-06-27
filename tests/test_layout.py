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
  • chain strategy is removed
  • the silent `continue` in derive_walls() becomes a ValueError raise
  (spec/level-gen-refactor.md, step 2)
"""
import random
import pytest
from hypothesis import given, settings, strategies as st

from levelgraph import LevelGraph, EdgeType, NodeSize
from levellayout import (
    layout_graph, derive_walls, validate_layout, PlacedNode, build_level_dict,
)
from tests.conftest import FS_ALL, FS_OPEN, FS_LOCKED, FS_GATED, ALL_FEATURE_SETS

VALID_STRATEGIES = ['horizontal', 'vertical', 'off_centre', 'cross', 't', 'chain', 'l']


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

    def test_cross_strategy_available(self):
        """cross strategy must be registered in STRATEGIES."""
        from levellayout import STRATEGIES
        assert 'cross' in STRATEGIES

    def test_t_strategy_available(self):
        """t strategy must be registered in STRATEGIES."""
        from levellayout import STRATEGIES
        assert 't' in STRATEGIES

    def test_chain_strategy_available(self):
        """chain strategy must be registered in STRATEGIES."""
        from levellayout import STRATEGIES
        assert 'chain' in STRATEGIES


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
