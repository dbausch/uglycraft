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

from uglycraft.levelgraph import LevelGraph, EdgeType, NodeSize
from uglycraft.levellayout import (
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
        from uglycraft.levelgraph import LevelGraph as G2, EdgeType, NodeSize
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
        from uglycraft.levellayout import STRATEGIES
        assert 't' in STRATEGIES

    def test_double_t_strategy_available(self):
        from uglycraft.levellayout import STRATEGIES
        assert 'double_t' in STRATEGIES

    def test_z_strategy_available(self):
        from uglycraft.levellayout import STRATEGIES
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
        from uglycraft.levellayout import _STRATEGY_MAX_ZONES
        assert isinstance(_STRATEGY_MAX_ZONES, dict)

    def test_simple_strategies_have_max_2(self):
        from uglycraft.levellayout import _STRATEGY_MAX_ZONES
        for s in ['horizontal', 'vertical', 'off_centre']:
            assert _STRATEGY_MAX_ZONES[s] == 2, f"{s} should have max_zones=2"

    def test_t_has_max_3(self):
        from uglycraft.levellayout import _STRATEGY_MAX_ZONES
        assert _STRATEGY_MAX_ZONES['t'] == 3

    def test_heavy_strategies_have_max_4(self):
        from uglycraft.levellayout import _STRATEGY_MAX_ZONES
        for s in ['double_t', 'z', 'l']:
            assert _STRATEGY_MAX_ZONES[s] == 4, f"{s} should have max_zones=4"

    def test_all_strategies_covered(self):
        from uglycraft.levellayout import _STRATEGY_MAX_ZONES, STRATEGIES
        for s in STRATEGIES:
            assert s in _STRATEGY_MAX_ZONES, f"{s} missing from _STRATEGY_MAX_ZONES"

    def test_full_border_max_zones_is_1(self):
        from uglycraft.levellayout import _STRATEGY_MAX_ZONES
        assert _STRATEGY_MAX_ZONES.get('full_border') == 1


class TestPickStrategyRoomCount:
    def test_n_rooms_2_never_picks_4zone(self):
        from uglycraft.levellayout import _pick_strategy, _STRATEGY_MAX_ZONES, STRATEGIES
        for seed in range(200):
            result = _pick_strategy(frozenset(), STRATEGIES, random.Random(seed), n_rooms=2)
            assert _STRATEGY_MAX_ZONES.get(result, 2) <= 2, \
                f"seed={seed}: picked {result!r} (max_zones={_STRATEGY_MAX_ZONES.get(result)}) for n_rooms=2"

    def test_n_rooms_3_allows_t_not_4zone(self):
        from uglycraft.levellayout import _pick_strategy, _STRATEGY_MAX_ZONES, STRATEGIES
        results = {_pick_strategy(frozenset(), STRATEGIES, random.Random(s), n_rooms=3)
                   for s in range(200)}
        assert 't' in results, "t (max_zones=3) should be chosen with n_rooms=3"
        for r in results:
            assert _STRATEGY_MAX_ZONES.get(r, 2) <= 3, \
                f"picked {r!r} (max_zones={_STRATEGY_MAX_ZONES.get(r)}) for n_rooms=3"

    def test_n_rooms_4_allows_heavy_strategies(self):
        from uglycraft.levellayout import _pick_strategy, STRATEGIES
        results = {_pick_strategy(frozenset(), STRATEGIES, random.Random(s), n_rooms=4)
                   for s in range(200)}
        assert 'double_t' in results or 'z' in results or 'l' in results, \
            "4-zone strategies should be eligible with n_rooms=4"

    def test_pick_strategy_single_available_is_filtered(self):
        """_pick_strategy has no len(available)==1 guard — room-count filter
        always runs, falling back to full_border when filtered is empty."""
        from uglycraft.levellayout import _pick_strategy
        result = _pick_strategy(frozenset(), ['double_t'], random.Random(0), n_rooms=2)
        assert result == 'full_border'

    def test_n_rooms_1_no_exit_uses_full_border(self):
        """Strict filter: no strategy has max_zones ≤ 1 except full_border."""
        from uglycraft.levellayout import _pick_strategy, STRATEGIES
        for seed in range(50):
            result = _pick_strategy(frozenset(), STRATEGIES, random.Random(seed), n_rooms=1)
            assert result == 'full_border', \
                f"seed={seed}: expected full_border for n_rooms=1, got {result!r}"

    def test_n_rooms_1_tb_exit_uses_full_border(self):
        """1-room grid with tb exit: vertical is ineligible (max_zones=2 > 1)."""
        from uglycraft.levellayout import _pick_strategy, STRATEGIES
        for seed in range(50):
            result = _pick_strategy(frozenset({'top'}), STRATEGIES,
                                    random.Random(seed), n_rooms=1)
            assert result == 'full_border', \
                f"seed={seed}: expected full_border for n_rooms=1 tb exit, got {result!r}"

    def test_n_rooms_2_can_use_vertical(self):
        """Strict filter still allows 2-zone strategies for n_rooms=2."""
        from uglycraft.levellayout import _pick_strategy, STRATEGIES
        results = {_pick_strategy(frozenset({'top'}), STRATEGIES,
                                  random.Random(s), n_rooms=2)
                   for s in range(100)}
        assert 'vertical' in results, \
            "vertical (max_zones=2) should be eligible for n_rooms=2 with tb exit"


@pytest.mark.parametrize('seed', range(20))
def test_layout_graph_1room_uses_full_border(seed):
    """With 1 regular room and the default strategy pool, layout_graph must
    use full_border (the only strategy with max_zones ≤ 1)."""
    graph = LevelGraph()
    graph.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
    graph.add_node('r0', NodeSize.ROOM)
    graph.add_edge('corridor', 'r0', EdgeType.OPEN)

    placed = layout_graph(graph, rng=random.Random(seed))
    walls, _ = derive_walls(graph, placed)
    assert validate_layout(graph, placed, walls) == [], f"seed={seed}: layout error"

    cor = next(n for n, nd in graph.nodes.items() if nd.size == NodeSize.CORRIDOR)
    left_col_rows = {r for c, r in placed[cor].floor_tiles if c == MIN_C}
    assert left_col_rows == set(range(MIN_R, MAX_R + 1)), \
        f"seed={seed}: expected full_border corridor for 1-room graph"


class TestFullBorderFallback:
    """full_border is chosen when all exit-compatible strategies are over-zoned."""

    def _one_room_graph(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('r0', NodeSize.ROOM)
        g.add_edge('corridor', 'r0', EdgeType.OPEN)
        return g

    def _is_full_border(self, placed, graph):
        """True when the corridor covers every row in the left column —
        full_border fills the whole perimeter; other strategies only touch
        the left edge at the band/stem rows (2–3 tiles, not all 14)."""
        cor = next(n for n, nd in graph.nodes.items() if nd.size == NodeSize.CORRIDOR)
        tiles = placed[cor].floor_tiles
        left_col_rows = {r for c, r in tiles if c == MIN_C}
        return left_col_rows == set(range(MIN_R, MAX_R + 1))

    def test_perpendicular_exits_small_room_count_uses_full_border(self):
        """exits={'left','bottom'}, heavy-only pool, 1 room → full_border."""
        from uglycraft.levellayout import _pick_strategy
        heavy_pool = ['double_t', 'z', 'l']
        for seed in range(30):
            result = _pick_strategy(frozenset({'left', 'bottom'}), heavy_pool,
                                    random.Random(seed), n_rooms=1)
            assert result == 'full_border', \
                f"seed={seed}: expected full_border, got {result!r}"

    def test_three_exits_small_room_count_uses_full_border(self):
        """exits={'left','right','top'}, heavy-only pool, 1 room → full_border."""
        from uglycraft.levellayout import _pick_strategy
        heavy_pool = ['double_t', 'z', 'l']
        for seed in range(30):
            result = _pick_strategy(frozenset({'left', 'right', 'top'}), heavy_pool,
                                    random.Random(seed), n_rooms=1)
            assert result == 'full_border', \
                f"seed={seed}: expected full_border, got {result!r}"

    def test_layout_graph_heavy_pool_falls_back_to_full_border(self):
        """layout_graph: all-heavy pool + 1 room → full_border corridor."""
        graph = self._one_room_graph()
        for seed in range(20):
            placed = layout_graph(graph, rng=random.Random(seed),
                                  strategies=['double_t', 'z', 'l'])
            assert self._is_full_border(placed, graph), \
                f"seed={seed}: expected full_border corridor"
            walls, _ = derive_walls(graph, placed)
            assert validate_layout(graph, placed, walls) == [], f"seed={seed}: layout error"

    def test_layout_graph_single_strategy_override_bypasses_filter(self):
        """layout_graph: len(available)==1 guard preserves explicit override."""
        graph = LevelGraph()
        graph.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        for i in range(4):
            graph.add_node(f'r{i}', NodeSize.ROOM)
            graph.add_edge('corridor', f'r{i}', EdgeType.OPEN)
        for seed in range(10):
            placed = layout_graph(graph, rng=random.Random(seed),
                                  strategies=['double_t'])
            # Single-strategy override → double_t used, not full_border
            assert not self._is_full_border(placed, graph), \
                f"seed={seed}: single-strategy override should use double_t, not full_border"


@pytest.mark.parametrize('seed', range(20))
def test_layout_graph_2room_no_heavy_strategy(seed):
    """With 2 regular rooms and the full strategy pool, layout_graph must not
    pick a strategy with max_zones > 2 (which would leave empty wall zones)."""
    from uglycraft.levellayout import _STRATEGY_MAX_ZONES, STRATEGIES
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


# ── R-P4 / R-P6: packing-function minimum dimensions and n-cap ────────────────

class TestPackBandCapacity:
    """R-P4 (min w≥2, h≥2) and R-P6 (n_max cap) for both packing functions."""

    def test_pack_band_width5_fits_two_rooms(self):
        """band_w=5 must fit 2 rooms: 2 + 1-gap + 2 = 5."""
        from uglycraft.levellayout import _pack_band
        placed = {}
        _pack_band(placed, ['a', 'b'], random.Random(0),
                   band_col=1, band_row=1, band_w=5, band_h=2)
        assert 'a' in placed, "first room not placed"
        assert 'b' in placed, "second room not placed"
        a, b = placed['a'], placed['b']
        assert a.w >= 2 and b.w >= 2
        assert b.col == a.col + a.w + 1, "gap between rooms must be exactly 1"

    def test_pack_band_width4_one_room_uses_full_width(self):
        """band_w=4, n=2: n_max=1; the single placed room fills the zone."""
        from uglycraft.levellayout import _pack_band
        placed = {}
        _pack_band(placed, ['a', 'b'], random.Random(0),
                   band_col=1, band_row=1, band_w=4, band_h=2)
        assert 'a' in placed, "first room not placed"
        assert 'b' not in placed, "second room must not be placed (n_max=1 for band_w=4)"
        assert placed['a'].w == 4, f"expected width=4, got {placed['a'].w}"

    def test_pack_band_vertical_height5_fits_two_rooms(self):
        """band_h=5 must fit 2 rooms: 2 + 1-gap + 2 = 5."""
        from uglycraft.levellayout import _pack_band_vertical
        placed = {}
        _pack_band_vertical(placed, ['a', 'b'], random.Random(0),
                            band_col=1, band_row=1, band_w=3, band_h=5)
        assert 'a' in placed, "first room not placed"
        assert 'b' in placed, "second room not placed"
        a, b = placed['a'], placed['b']
        assert a.h >= 2 and b.h >= 2
        assert b.row == a.row + a.h + 1, "gap between rooms must be exactly 1"

    def test_pack_band_vertical_height4_one_room_uses_full_height(self):
        """band_h=4, n=2: n_max=1; the single placed room fills the zone."""
        from uglycraft.levellayout import _pack_band_vertical
        placed = {}
        _pack_band_vertical(placed, ['a', 'b'], random.Random(0),
                            band_col=1, band_row=1, band_w=3, band_h=4)
        assert 'a' in placed, "first room not placed"
        assert 'b' not in placed, "second room must not be placed (n_max=1 for band_h=4)"
        assert placed['a'].h == 4, f"expected height=4, got {placed['a'].h}"


# ── BL-09: greedy zone assignment ─────────────────────────────────────────────

class TestNextRoomTiles:
    """Unit tests for _next_room_tiles (tile count for the next room in a zone)."""

    def test_pack_band_first_room(self):
        from uglycraft.levellayout import _next_room_tiles, _pack_band
        # zw=3, zh=10, k=0: base=(3-0)//(0+1)=3 → 3*10=30
        assert _next_room_tiles(3, 10, _pack_band, 0) == 30

    def test_pack_band_zone_full(self):
        from uglycraft.levellayout import _next_room_tiles, _pack_band
        # zw=3, zh=10, k=1: base=(3-1)//(1+1)=1 < 2 → 0
        assert _next_room_tiles(3, 10, _pack_band, 1) == 0

    def test_pack_band_wide_zone_second_room(self):
        from uglycraft.levellayout import _next_room_tiles, _pack_band
        # zw=7, zh=5, k=1: base=(7-1)//(1+1)=3 → 3*5=15
        assert _next_room_tiles(7, 5, _pack_band, 1) == 15

    def test_pack_band_vertical_first_room(self):
        from uglycraft.levellayout import _next_room_tiles, _pack_band_vertical
        # zw=6, zh=4, k=0: base=(4-0)//(0+1)=4 → 6*4=24
        assert _next_room_tiles(6, 4, _pack_band_vertical, 0) == 24

    def test_pack_band_vertical_zone_full(self):
        from uglycraft.levellayout import _next_room_tiles, _pack_band_vertical
        # zw=6, zh=4, k=1: base=(4-1)//(1+1)=1 < 2 → 0
        assert _next_room_tiles(6, 4, _pack_band_vertical, 1) == 0


class TestGreedyZoneAssignment:
    """Integration tests for greedy distribution in _layout_corridor."""

    def _call_corridor(self, room_names, col_frac=0.2, rng_seed=0):
        from uglycraft.levellayout import _layout_corridor
        rng = random.Random(rng_seed)
        # col_frac=0.2 → c_stem=5, stem_w=3:
        #   near Zone A (w=3, cap=1), near Zone B (w=20, cap=7),
        #   far Zone C (w=28, cap=9). total_cap=17.
        return _layout_corridor(
            'corridor', list(room_names), rng,
            stems=[('near', col_frac, (3, 3))],
        )

    def test_all_rooms_placed_when_capacity_sufficient(self):
        """Greedy places all rooms; round-robin would drop the 4th (2nd in Zone A)."""
        # 4 rooms, 3 valid zones: round-robin assigns rooms 0,3 to Zone A (cap=1),
        # silently dropping room 3.  Greedy sends it to a wider zone instead.
        room_names = ['r0', 'r1', 'r2', 'r3']
        placed = self._call_corridor(room_names)
        for name in room_names:
            assert name in placed, f"room {name!r} was silently dropped"

    def test_layout_error_when_capacity_exceeded(self):
        """LayoutError raised when rooms outnumber total zone capacity."""
        from uglycraft.levellayout import LayoutError
        # Zone caps sum to 17; 18 rooms must overflow.
        room_names = [f'r{i}' for i in range(18)]
        with pytest.raises(LayoutError):
            self._call_corridor(room_names)

    def test_empty_zones_filled_before_non_empty(self):
        """Every valid zone gets a room before any zone gets a second one."""
        # col_frac=0.2 → 3 valid zones: Zone A (w=3), Zone B (w=20), Zone C (w=28).
        # Without empty-zones-first, greedy stacks rooms in Zone C (most tiles),
        # leaving Zone A empty.  With the rule, all 3 zones receive exactly 1 room.
        # A room in Zone A has w=3; assert that width appears among placed rooms.
        placed = self._call_corridor(['r0', 'r1', 'r2'])
        room_widths = [pn.w for name, pn in placed.items() if name != 'corridor']
        assert any(w == 3 for w in room_widths), (
            "No room landed in the narrow Zone A (w=3); "
            "empty-zones-first rule not enforced"
        )

    def test_single_room_goes_to_wide_zone(self):
        """With 1 room, greedy skips the narrow Zone A (w=3) for a wider zone."""
        # Round-robin takes index 0 → Zone A (w=3).
        # Greedy picks Zone B (w=20) or Zone C (w=28); either gives w > 3.
        placed = self._call_corridor(['r0'])
        assert 'r0' in placed
        assert placed['r0'].w > 3, (
            f"expected room in a wide zone (w > 3), got w={placed['r0'].w}"
        )
