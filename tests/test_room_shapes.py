"""Tests for room-shapes spec: L-corridor, L-pair rooms, corner closets."""
import random

import pytest
from hypothesis import given, settings, strategies as st

from uglycraft.levelgraph import LevelGraph, EdgeType, NodeSize
from uglycraft.levellayout import (
    PlacedNode,
    _floor_connected,
    _try_l_pair,
    _try_l_pair_vertical,
    build_level_dict,
    derive_walls,
    layout_graph,
    validate_layout,
    STRATEGIES,
    MIN_C, MAX_C, MIN_R, MAX_R,
)
from tests.conftest import FS_ALL, FS_OPEN


# ── L-corridor ────────────────────────────────────────────────────────────────

class TestLCorridor:

    def test_l_in_strategies(self):
        assert 'l' in STRATEGIES

    def _validate(self, graph, seed=0):
        rng = random.Random(seed)
        placed = layout_graph(graph, rng=rng, strategies=['l'])
        walls, _ = derive_walls(graph, placed)
        return validate_layout(graph, placed, walls)

    def test_l_validates_open_graph(self):
        graph = LevelGraph.generate(FS_OPEN, rng=random.Random(0))
        assert self._validate(graph, seed=0) == []

    def test_l_validates_all_edges(self):
        graph = LevelGraph.generate(FS_ALL, rng=random.Random(1))
        assert self._validate(graph, seed=1) == []

    def test_corridor_is_l_shaped(self):
        graph = LevelGraph.generate(FS_OPEN, rng=random.Random(0))
        rng = random.Random(0)
        placed = layout_graph(graph, rng=rng, strategies=['l'])
        cor = next(n for n, nd in graph.nodes.items()
                   if nd.size == NodeSize.CORRIDOR)
        pn = placed[cor]
        # L-shaped corridor must have fewer floor tiles than its bounding box
        assert len(pn.floor_tiles) < pn.w * pn.h

    @given(seed=st.integers(min_value=0, max_value=2**31 - 1))
    @settings(max_examples=100)
    def test_l_strategy_invariant_l(self, seed):
        graph = LevelGraph.generate(FS_ALL, rng=random.Random(seed))
        placed = layout_graph(graph, rng=random.Random(seed), strategies=['l'])
        walls, _ = derive_walls(graph, placed)
        errors = validate_layout(graph, placed, walls)
        assert errors == [], f"seed={seed}: {errors}"


# ── L-pair (horizontal) ───────────────────────────────────────────────────────

class TestLPairHorizontal:

    def _make_placed(self):
        return {}

    def test_l_pair_produces_l_shape(self):
        placed = {}
        consumed = _try_l_pair(
            placed, 'a', 'b',
            col=2, band_row=2, band_h=6,
            w_i=5, w_j=4, band_end=28,
            rng=random.Random(0),
        )
        assert consumed > 0, "L-pair should succeed"
        assert 'a' in placed and 'b' in placed
        pa = placed['a']
        pb = placed['b']
        # A is L-shaped (fewer tiles than bounding box)
        assert len(pa.floor_tiles) < pa.w * pa.h
        # B is a rectangle
        assert len(pb.floor_tiles) == pb.w * pb.h

    def test_l_pair_no_adjacent_tiles(self):
        placed = {}
        _try_l_pair(
            placed, 'a', 'b',
            col=2, band_row=2, band_h=6,
            w_i=5, w_j=4, band_end=28,
            rng=random.Random(0),
        )
        pa, pb = placed['a'], placed['b']
        for c, r in pa.floor_tiles:
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                assert (c + dc, r + dr) not in pb.floor_tiles, \
                    f"A and B have adjacent tiles at ({c},{r})"

    def test_l_pair_has_connection_tile(self):
        """_find_connection_tile must find exactly one shared boundary tile."""
        from uglycraft.levellayout import _find_connection_tile
        placed = {}
        _try_l_pair(
            placed, 'a', 'b',
            col=2, band_row=2, band_h=6,
            w_i=5, w_j=4, band_end=28,
            rng=random.Random(0),
        )
        pa, pb = placed['a'], placed['b']
        # Build synthetic walls: everything not in floor
        all_floor = pa.floor_tiles | pb.floor_tiles
        walls = {(c, r): 1
                 for c in range(MIN_C, MAX_C + 1)
                 for r in range(MIN_R, MAX_R + 1)
                 if (c, r) not in all_floor}
        conn = _find_connection_tile(pa, pb, walls)
        assert conn is not None, "No connection tile found between L-pair rooms"

    @pytest.mark.parametrize('seed', range(30))
    def test_l_pair_in_full_layout(self, seed):
        """Layouts with OPEN-edge adjacent pairs must still validate."""
        fs = {**FS_ALL,
              'room_count': (4, 6),
              'edge_types': [EdgeType.OPEN, EdgeType.OPEN, EdgeType.OPEN,
                             EdgeType.BREAKABLE]}
        graph = LevelGraph.generate(fs, rng=random.Random(seed))
        rng = random.Random(seed)
        placed = layout_graph(graph, rng=rng, strategies=['horizontal'])
        walls, _ = derive_walls(graph, placed)
        errors = validate_layout(graph, placed, walls)
        assert errors == [], f"seed={seed}: {errors}"


# ── L-pair (vertical) ────────────────────────────────────────────────────────

class TestLPairVertical:

    def test_v_l_pair_no_adjacent_tiles(self):
        placed = {}
        consumed = _try_l_pair_vertical(
            placed, 'a', 'b',
            row=2, band_col=2, band_w=8,
            h_i=4, h_j=3, row_end=16,
            rng=random.Random(0),
        )
        assert consumed > 0, "Vertical L-pair should succeed"
        pa, pb = placed['a'], placed['b']
        for c, r in pa.floor_tiles:
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                assert (c + dc, r + dr) not in pb.floor_tiles, \
                    f"A and B have adjacent tiles at ({c},{r})"

    def test_v_l_pair_has_connection_tile(self):
        from uglycraft.levellayout import _find_connection_tile
        placed = {}
        _try_l_pair_vertical(
            placed, 'a', 'b',
            row=2, band_col=2, band_w=8,
            h_i=4, h_j=3, row_end=16,
            rng=random.Random(0),
        )
        pa, pb = placed['a'], placed['b']
        all_floor = pa.floor_tiles | pb.floor_tiles
        walls = {(c, r): 1
                 for c in range(MIN_C, MAX_C + 1)
                 for r in range(MIN_R, MAX_R + 1)
                 if (c, r) not in all_floor}
        conn = _find_connection_tile(pa, pb, walls)
        assert conn is not None, "No connection tile found between vertical L-pair rooms"


# ── Corner closet ─────────────────────────────────────────────────────────────

class TestCornerCloset:

    def _make_closet_graph(self, seed=0):
        """Graph: corridor → hall, hall → closet (non-star)."""
        rng = random.Random(seed)
        g = LevelGraph(rng=rng)
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        hall = g.add_node('hall_1', NodeSize.HALL)
        hall.treasures.append((3,))
        closet = g.add_node('closet_1', NodeSize.CLOSET)
        closet.keys.append(('blue',))
        g.add_edge('corridor', 'hall_1', EdgeType.OPEN)
        g.add_edge('hall_1', 'closet_1', EdgeType.OPEN)
        return g

    def test_closet_graph_places_without_error(self):
        graph = self._make_closet_graph(seed=0)
        rng = random.Random(0)
        # Must not raise (closet is nested into the hall's corner)
        placed = layout_graph(graph, rng=rng, strategies=['horizontal'])
        assert 'closet_1' in placed
        assert 'hall_1' in placed

    def test_closet_nested_into_hall_corner(self):
        graph = self._make_closet_graph(seed=0)
        rng = random.Random(0)
        placed = layout_graph(graph, rng=rng, strategies=['horizontal'])
        pn_hall = placed['hall_1']
        pn_closet = placed['closet_1']
        # Closet must be spatially inside (or on the boundary of) the hall's bounding box
        closet_cols = {c for c, r in pn_closet.floor_tiles}
        closet_rows = {r for c, r in pn_closet.floor_tiles}
        assert min(closet_cols) >= pn_hall.col
        assert max(closet_cols) < pn_hall.col + pn_hall.w
        assert min(closet_rows) >= pn_hall.row
        assert max(closet_rows) < pn_hall.row + pn_hall.h

    def test_closet_layout_validates(self):
        graph = self._make_closet_graph(seed=0)
        rng = random.Random(0)
        placed = layout_graph(graph, rng=rng, strategies=['horizontal'])
        walls, _ = derive_walls(graph, placed)
        errors = validate_layout(graph, placed, walls)
        assert errors == [], errors

    def test_closet_build_level_dict(self):
        graph = self._make_closet_graph(seed=0)
        rng = random.Random(0)
        # Must not raise
        ld = build_level_dict(graph, rng=rng, strategies=['horizontal'])
        assert 'rooms' in ld

    @pytest.mark.parametrize('seed', range(15))
    def test_closet_validates_multiple_seeds(self, seed):
        graph = self._make_closet_graph(seed=seed)
        rng = random.Random(seed)
        placed = layout_graph(graph, rng=rng, strategies=['horizontal'])
        walls, _ = derive_walls(graph, placed)
        errors = validate_layout(graph, placed, walls)
        assert errors == [], f"seed={seed}: {errors}"


# ── _floor_connected helper ───────────────────────────────────────────────────

def test_floor_connected_rectangle():
    tiles = frozenset((c, r) for c in range(3, 8) for r in range(2, 6))
    assert _floor_connected(tiles)


def test_floor_connected_l_shape():
    tiles = (frozenset((c, r) for c in range(3, 8) for r in range(2, 4))
           | frozenset((c, r) for c in range(3, 5) for r in range(4, 7)))
    assert _floor_connected(tiles)


def test_floor_connected_two_islands():
    a = frozenset((c, r) for c in range(2, 5) for r in range(2, 5))
    b = frozenset((c, r) for c in range(8, 11) for r in range(8, 11))
    assert not _floor_connected(a | b)
