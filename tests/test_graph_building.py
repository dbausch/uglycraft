"""Tests for Transformation 1: Challenge Sequence → Abstract Graph.

Mathematical Invariant G (Graph Reachability)
=============================================
For all sequences of LevelGraphBuilder operations B and all seeds s,
    B(s).build().validate_playability() = []

Proof by structural induction on B:

  Base case — empty sequence:
    G = {corridor, no items}. validate_playability trivially returns []. ✓

  add_open_room(parent):
    Adds node R, edge (parent, R, OPEN). OPEN edges are always traversable.
    R has no items at creation, so it need not be reachable for item access
    (validate_playability only errs on unreachable nodes WITH items).
    R is reachable via parent ∈ reachable(G). Invariant preserved. ✓

  add_breakable_room():
    Same as OPEN — BREAKABLE is always traversable. ✓

  add_locked_room(colour, parent):
    Adds R, edge (parent, R, LOCKED, colour), key(colour) in K where
    K ∈ reachable(G).
    BFS from corridor reaches K, acquires key(colour), then traverses the
    LOCKED edge to R. R becomes reachable. Items in R (if any) are reachable. ✓

  add_gated_room(gate_id, parent):
    Adds R, edge (parent, R, GATED, gate_id), plate(gate_id)+block in P where
    P ∈ reachable(G).
    BFS reaches P, acquires plate+block, traverses GATED edge to R. ✓

  add_water_room(parent):
    Adds R, edge (parent, R, WATER), 2×planks in W where W ∈ reachable(G).
    BFS reaches planks, traverses WATER edge. ✓

  By induction, every sequence maintains the invariant. □

These tests are RED until LevelGraphBuilder is implemented
(spec/level-gen-refactor.md, step 1).
"""
import random
import pytest
from hypothesis import given, settings, strategies as st

from levelgraph import LevelGraph, LevelGraphBuilder, EdgeType, NodeSize
from tests.conftest import ALL_FEATURE_SETS, FS_LOCKED, FS_GATED, FS_WATER, FS_ALL


# ── Unit tests: each builder operation preserves the invariant ────────────────

class TestBuilderOperations:

    def test_base_case_corridor_only(self):
        """Empty builder → valid graph (base case of induction)."""
        b = LevelGraphBuilder(random.Random(0))
        assert b.build().validate_playability() == []

    def test_add_open_room(self):
        b = LevelGraphBuilder(random.Random(1))
        b.add_open_room()
        assert b.build().validate_playability() == []

    def test_add_breakable_room(self):
        b = LevelGraphBuilder(random.Random(2))
        b.add_breakable_room()
        assert b.build().validate_playability() == []

    def test_add_locked_room_key_placed_before_lock(self):
        """Key must be in a reachable room, not behind the lock it opens."""
        b = LevelGraphBuilder(random.Random(3))
        b.add_open_room()
        room = b.add_locked_room('red')
        graph = b.build()
        errors = graph.validate_playability()
        assert errors == [], errors

        # Key must NOT be in the locked room itself
        locked_node = graph.nodes[room]
        assert locked_node.keys == [], (
            f"Key placed inside the locked room {room!r}")

    def test_add_gated_room_puzzle_in_reachable(self):
        """Plate+block must be in a reachable room before the gate."""
        b = LevelGraphBuilder(random.Random(4))
        b.add_open_room()
        b.add_gated_room('gate_1')
        assert b.build().validate_playability() == []

    def test_add_water_room_planks_in_reachable(self):
        b = LevelGraphBuilder(random.Random(5))
        b.add_open_room()
        b.add_water_room()
        assert b.build().validate_playability() == []

    def test_multiple_locked_doors_different_colours(self):
        b = LevelGraphBuilder(random.Random(6))
        b.add_locked_room('red')
        b.add_locked_room('blue')
        b.add_locked_room('green')
        assert b.build().validate_playability() == []

    def test_same_colour_locked_doors(self):
        """Two LOCKED edges with the same colour: one key suffices per door."""
        b = LevelGraphBuilder(random.Random(7))
        b.add_open_room()
        b.add_locked_room('red')
        b.add_locked_room('red')
        assert b.build().validate_playability() == []

    def test_multiple_gates(self):
        b = LevelGraphBuilder(random.Random(8))
        b.add_open_room()
        b.add_gated_room('gate_a')
        b.add_gated_room('gate_b')
        assert b.build().validate_playability() == []

    def test_mixed_challenge_sequence(self):
        b = LevelGraphBuilder(random.Random(9))
        b.add_open_room()
        b.add_locked_room('red')
        b.add_gated_room('gate_1')
        b.add_breakable_room()
        b.add_water_room()
        b.add_open_room()
        assert b.build().validate_playability() == []

    def test_enemy_placement_uses_eligible_rooms_only(self):
        """Enemies must be placed in ROOM/HALL nodes with no puzzle and no flames."""
        b = LevelGraphBuilder(random.Random(10))
        b.add_open_room(size=NodeSize.ROOM)
        b.add_gated_room('gate_1', size=NodeSize.ROOM)
        b.add_enemies(2)
        graph = b.build()
        for name, node in graph.nodes.items():
            if node.enemies:
                assert node.size in (NodeSize.ROOM, NodeSize.HALL), (
                    f"Enemy in non-ROOM/HALL node {name!r} (size={node.size})")
                assert not node.blocks and not node.plates, (
                    f"Enemy in puzzle room {name!r}")
                assert not node.has_flames, (
                    f"Enemy in flame room {name!r}")


# ── Property-based tests: Invariant G holds for all sequences ─────────────────

OPERATIONS = st.one_of(
    st.just(('open',)),
    st.just(('breakable',)),
    st.tuples(st.just('locked'), st.sampled_from(['red', 'blue', 'green'])),
    st.tuples(st.just('gated'),  st.from_regex(r'gate_[a-z]', fullmatch=True)),
    st.just(('water',)),
)


@given(
    seed=st.integers(min_value=0, max_value=2**31 - 1),
    ops=st.lists(OPERATIONS, min_size=1, max_size=8),
)
@settings(max_examples=300)
def test_invariant_g_any_builder_sequence(seed, ops):
    """INVARIANT G: ∀ builder sequences, validate_playability() = []."""
    rng = random.Random(seed)
    b = LevelGraphBuilder(rng)
    for op in ops:
        kind = op[0]
        if kind == 'open':
            b.add_open_room()
        elif kind == 'breakable':
            b.add_breakable_room()
        elif kind == 'locked':
            b.add_locked_room(op[1])
        elif kind == 'gated':
            b.add_gated_room(op[1])
        elif kind == 'water':
            b.add_water_room()
    errors = b.build().validate_playability()
    assert errors == [], f"seed={seed}, ops={ops}: {errors}"


@given(seed=st.integers(min_value=0, max_value=2**31 - 1))
@settings(max_examples=200)
def test_generate_always_valid_no_retry(seed):
    """LevelGraph.generate() must produce a valid graph on the FIRST try.
    If this fails for any seed, the retry loop is masking a real bug."""
    for fs in ALL_FEATURE_SETS:
        graph = LevelGraph.generate(fs, rng=random.Random(seed))
        errors = graph.validate_playability()
        assert errors == [], f"seed={seed}, fs edge_types={fs['edge_types']}: {errors}"
