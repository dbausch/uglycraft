"""Tests for world-graph spanning tree and per-grid strategy selection.

Phase 1 of spec/0017-large-levels.md.
"""
import random
import pytest
from hypothesis import given, settings, strategies as st

from levelgraph import LevelGraph, EdgeType, NodeSize, _spanning_tree
from levellayout import _pick_strategy, build_level_dict
from tests.conftest import FS_ALL, ALL_FEATURE_SETS


# ── Spanning tree ─────────────────────────────────────────────────────────────

class TestSpanningTree:

    def _tree(self, n, seed=0):
        return _spanning_tree(n, random.Random(seed))

    def test_single_grid_returns_one_entry(self):
        result = self._tree(1)
        assert len(result) == 1
        parent_idx, exit_side, pos = result[0]
        assert parent_idx is None
        assert exit_side is None
        assert pos == (0, 0)

    @pytest.mark.parametrize('n', range(1, 11))
    def test_length_equals_n(self, n):
        assert len(self._tree(n)) == n

    @pytest.mark.parametrize('n', range(2, 11))
    def test_unique_positions(self, n):
        positions = [pos for _, _, pos in self._tree(n)]
        assert len(set(positions)) == n

    @pytest.mark.parametrize('n', range(2, 11))
    def test_spanning_tree_has_n_minus_one_edges(self, n):
        parent_edges = sum(1 for p, _, _ in self._tree(n) if p is not None)
        assert parent_edges == n - 1

    @pytest.mark.parametrize('n', range(2, 11))
    def test_parents_appear_before_children(self, n):
        result = self._tree(n)
        seen = set()
        for i, (parent_idx, _, _) in enumerate(result):
            if parent_idx is not None:
                assert parent_idx in seen, \
                    f"node {i}: parent {parent_idx} not yet seen"
            seen.add(i)

    @pytest.mark.parametrize('n', range(2, 11))
    def test_each_child_adjacent_to_parent(self, n):
        result = self._tree(n)
        positions = [pos for _, _, pos in result]
        for i, (parent_idx, exit_side, pos) in enumerate(result):
            if parent_idx is None:
                continue
            ppos = positions[parent_idx]
            dist = abs(pos[0] - ppos[0]) + abs(pos[1] - ppos[1])
            assert dist == 1, \
                f"node {i} at {pos} not adjacent to parent {parent_idx} at {ppos}"

    @pytest.mark.parametrize('n', range(2, 11))
    def test_exit_side_matches_direction(self, n):
        """exit_side must match the actual direction from parent to child."""
        SIDE_TO_DELTA = {
            'right': (1, 0), 'left': (-1, 0),
            'bottom': (0, 1), 'top': (0, -1),
        }
        result = self._tree(n)
        positions = [pos for _, _, pos in result]
        for i, (parent_idx, exit_side, pos) in enumerate(result):
            if parent_idx is None:
                continue
            ppos = positions[parent_idx]
            expected_delta = SIDE_TO_DELTA[exit_side]
            actual_delta = (pos[0] - ppos[0], pos[1] - ppos[1])
            assert actual_delta == expected_delta, \
                f"node {i}: exit_side={exit_side!r} but delta={actual_delta}"

    @given(n=st.integers(min_value=1, max_value=10),
           seed=st.integers(min_value=0, max_value=2**31 - 1))
    @settings(max_examples=300)
    def test_invariants_hold_for_all_inputs(self, n, seed):
        result = _spanning_tree(n, random.Random(seed))
        assert len(result) == n
        positions = [pos for _, _, pos in result]
        assert len(set(positions)) == n
        seen = set()
        for i, (parent_idx, exit_side, pos) in enumerate(result):
            if parent_idx is not None:
                assert parent_idx in seen
            seen.add(i)


# ── Strategy selection ────────────────────────────────────────────────────────

ALL_STRATEGIES = ['horizontal', 'vertical', 'off_centre', 't', 'double_t', 'z', 'l']


def pick(exits, available=None):
    return _pick_strategy(frozenset(exits), available or ALL_STRATEGIES,
                          random.Random(0))


class TestPickStrategy:

    def test_no_exits_returns_something(self):
        result = pick([])
        assert result in ALL_STRATEGIES

    def test_lr_horizontal_compatible(self):
        assert pick(['left', 'right'], ['horizontal']) == 'horizontal'

    def test_lr_vertical_not_compatible_falls_back(self):
        result = pick(['left', 'right'], ['vertical', 'double_t'])
        assert result == 'double_t'

    def test_lr_only_excludes_vertical(self):
        for _ in range(20):
            result = pick(['left', 'right'])
            assert result != 'vertical'

    def test_tb_vertical_compatible(self):
        assert pick(['top', 'bottom'], ['vertical']) == 'vertical'

    def test_tb_horizontal_not_compatible_falls_back(self):
        result = pick(['top', 'bottom'], ['horizontal', 'double_t'])
        assert result == 'double_t'

    def test_tb_only_excludes_horizontal_and_offcentre(self):
        for _ in range(20):
            result = pick(['top', 'bottom'])
            assert result not in ('horizontal', 'off_centre')

    def test_3_exits_requires_double_t_or_z(self):
        for exits in [['left', 'right', 'top'], ['left', 'right', 'bottom'],
                      ['left', 'top', 'bottom'], ['right', 'top', 'bottom']]:
            result = pick(exits)
            assert result in ('double_t', 'z'), \
                f"exits={exits}: got {result!r}"

    def test_4_exits_requires_double_t_or_z(self):
        result = pick(['left', 'right', 'top', 'bottom'])
        assert result in ('double_t', 'z')

    def test_4_exits_fallback_when_only_weak_available(self):
        result = pick(['left', 'right', 'top', 'bottom'], ['horizontal', 'vertical'])
        assert result == 'full_border'

    def test_perpendicular_pair_l_compatible(self):
        for pair in [['left', 'top'], ['left', 'bottom'],
                     ['right', 'top'], ['right', 'bottom']]:
            result = pick(pair, ['l', 'double_t'])
            assert result in ('l', 'double_t')

    def test_l_not_for_lr_pair(self):
        result = pick(['left', 'right'], ['l', 'horizontal'])
        assert result == 'horizontal'

    def test_l_not_for_tb_pair(self):
        result = pick(['top', 'bottom'], ['l', 'vertical'])
        assert result == 'vertical'

    @given(exits=st.frozensets(st.sampled_from(['left', 'right', 'top', 'bottom'])),
           seed=st.integers(min_value=0, max_value=2**31 - 1))
    @settings(max_examples=200)
    def test_result_always_covers_required_exits(self, exits, seed):
        result = _pick_strategy(exits, ALL_STRATEGIES, random.Random(seed))
        # double_t and z cover everything — they're always valid
        # For others, check the result is not obviously wrong
        has_lr = bool(exits & {'left', 'right'})
        has_tb = bool(exits & {'top', 'bottom'})
        if has_lr and has_tb and len(exits) >= 3:
            assert result in ('double_t', 'z')
        if has_lr and not has_tb:
            assert result not in ('vertical',)
        if has_tb and not has_lr:
            assert result not in ('horizontal', 'off_centre')


# ── Integration: LevelGraph.generate() with branching ─────────────────────────

class TestGenerateBranching:

    @pytest.mark.parametrize('seed', range(30))
    def test_branching_level_generates(self, seed):
        """build_level_dict completes without error for a multi-grid level."""
        fs = dict(FS_ALL)
        fs['grid_count'] = 4
        rng = random.Random(seed)
        graph = LevelGraph.generate(fs, rng=rng)
        d = build_level_dict(
            graph, rng=random.Random(seed),
            strategies=['horizontal', 'vertical', 'double_t', 'z'])
        assert d is not None
        assert 'rooms' in d

    @pytest.mark.parametrize('seed', range(30))
    def test_respects_room_count(self, seed):
        """The generator lays out a number of base rooms within the requested
        `room_count` range.

        Rethought from the old fixed-count check (`== 3`), which was flaky
        (`4 != 3`) for two reasons: it passed no seed, and it counted every
        non-corridor node — including the auxiliary CLOSET rooms each
        ROOM/HALL may grow with `closet_prob` (spec 0032).  Here closets are
        disabled and excluded, and the assertion is the range, not a point.
        `room_count` is clamped up to the number of distinct required edge
        types (`max(randint, len(required))`); with `edge_types` shorter than
        `room_min` that clamp never raises the floor."""
        lo, hi = 3, 5
        fs = {
            'room_count': (lo, hi),
            'edge_types': [EdgeType.OPEN, EdgeType.BREAKABLE],
            'node_sizes': [NodeSize.ROOM, NodeSize.HALL],
            'closet_prob': 0.0,
        }
        graph = LevelGraph.generate(fs, rng=random.Random(seed))
        rooms = [n for n in graph.nodes.values()
                 if n.size not in (NodeSize.CORRIDOR, NodeSize.CLOSET)]
        assert lo <= len(rooms) <= hi, (
            f"seed={seed}: {len(rooms)} base rooms not in [{lo}, {hi}]")

    @pytest.mark.parametrize('n', [1, 2, 3, 5, 7, 10])
    def test_grid_count_produces_correct_border_edges(self, n):
        """N grids → exactly N-1 BORDER edges (spanning tree)."""
        fs = dict(FS_ALL)
        fs['grid_count'] = n
        graph = LevelGraph.generate(fs, rng=random.Random(42))
        border_edges = [e for e in graph.edges if e.edge_type == EdgeType.BORDER]
        assert len(border_edges) == n - 1

    @pytest.mark.parametrize('n', [2, 3, 4, 5])
    def test_super_grid_positions_unique(self, n):
        """No two corridor nodes share the same super-grid position."""
        fs = dict(FS_ALL)
        fs['grid_count'] = n
        for seed in range(20):
            graph = LevelGraph.generate(fs, rng=random.Random(seed))
            corridors = [node for node in graph.nodes.values()
                         if node.size == NodeSize.CORRIDOR]
            positions = [node.super_pos for node in corridors]
            assert len(set(positions)) == len(positions), \
                f"n={n}, seed={seed}: duplicate super-grid positions {positions}"

    def test_branching_occurs_in_generated_graphs(self):
        """With n=6, some seeds produce a branch corridor (Wilson's natural branching)."""
        fs = dict(FS_ALL)
        fs['grid_count'] = 6
        found_branch = False
        for seed in range(200):
            graph = LevelGraph.generate(fs, rng=random.Random(seed))
            # Count BORDER edges per corridor
            border_count = {}
            for e in graph.edges:
                if e.edge_type == EdgeType.BORDER:
                    border_count[e.node_a] = border_count.get(e.node_a, 0) + 1
            if any(c >= 2 for c in border_count.values()):
                found_branch = True
                break
        assert found_branch, "No branching in 200 seeds with n=6"

    @pytest.mark.parametrize('level_idx,grid_count', [
        (0,  1),   # level 11
        (1,  2),   # level 12
        (2,  3),   # level 13
        (3,  4),   # level 14
        (4,  5),   # level 15
        (5,  6),   # level 16
        (6,  7),   # level 17
        (7,  8),   # level 18
        (8,  9),   # level 19
        (9, 10),   # level 20
    ])
    def test_act2_grid_counts_generate(self, level_idx, grid_count):
        """Each Act 2 grid count generates and lays out without error."""
        fs = dict(FS_ALL)
        fs['grid_count'] = grid_count
        rng = random.Random(42 + level_idx)
        graph = LevelGraph.generate(fs, rng=rng)
        border_edges = [e for e in graph.edges if e.edge_type == EdgeType.BORDER]
        assert len(border_edges) == grid_count - 1
        d = build_level_dict(
            graph, rng=random.Random(42 + level_idx),
            strategies=['horizontal', 'vertical', 'double_t', 'z'])
        assert d is not None
        assert 'rooms' in d
