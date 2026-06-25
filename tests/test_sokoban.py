"""Tests for Transformation 3: Positioned Graph → Tile Grid + Items.

Mathematical Invariant S (Sokoban Solvability)
==============================================
Let plate = (px, py), D = (dc, dr) a cardinal direction,
    block  = plate + D  = (px+dc, py+dr),
    player = plate + 2D = (px+2dc, py+2dr).

If block ∈ passable and player ∈ passable, then
    _sokoban_bfs(block, plate, passable, ∅) = True.

Proof:
  player is passable and player ≠ block, so the player can stand there.
  Player moves in direction −D: this pushes block from (plate+D) to plate.
  Block is now on the target. Puzzle solved in exactly one push. □

Corollary (1-push placement):
  After placing the plate, if we choose a block position T = plate + D such
  that both T and plate + 2D are passable (a "1-push position"), then
  validate_push_puzzles() will pass without a BFS search.

Corollary (1-push position existence):
  In any rectangular room of width ≥ 3 or height ≥ 3, at least one 1-push
  position exists for any plate placement. Since all game room sizes
  (CLOSET: 3×3 minimum, ROOM: 5×4, HALL: 8×5) exceed this bound, the
  corollary holds for all generated rooms.

These tests also cover the end-to-end pipeline, which must produce valid
push puzzles on the first attempt without any retry.

Tests in this file that are currently RED:
  • test_pipeline_push_puzzles_never_fail_end_to_end — currently raises
    ValueError on some seeds (retry loop masks this)
  (spec/level-gen-refactor.md, step 3)
"""
import random
import pytest
from hypothesis import given, settings, strategies as st

from levellayout import (
    _sokoban_bfs, _compute_dead_squares, validate_push_puzzles,
    build_level_dict,
)
from levelgraph import LevelGraph
from tests.conftest import FS_GATED, FS_ALL

CARDINAL = [(1, 0), (-1, 0), (0, 1), (0, -1)]


# ── Unit tests: mathematical properties of the BFS ────────────────────────────

class TestSokobanBFS:

    def _rect_passable(self, col, row, w, h):
        return frozenset(
            (c, r) for c in range(col, col + w) for r in range(row, row + h)
        )

    def test_block_already_at_target(self):
        passable = self._rect_passable(1, 1, 5, 5)
        assert _sokoban_bfs((3, 3), (3, 3), passable, set())

    def test_one_push_right(self):
        passable = self._rect_passable(1, 1, 5, 3)
        assert _sokoban_bfs((3, 2), (4, 2), passable, set())

    def test_one_push_left(self):
        passable = self._rect_passable(1, 1, 5, 3)
        assert _sokoban_bfs((3, 2), (2, 2), passable, set())

    def test_one_push_down(self):
        passable = self._rect_passable(1, 1, 3, 5)
        assert _sokoban_bfs((2, 2), (2, 3), passable, set())

    def test_one_push_up(self):
        passable = self._rect_passable(1, 1, 3, 5)
        assert _sokoban_bfs((2, 3), (2, 2), passable, set())

    def test_multi_push_path(self):
        # 1×7 corridor: block starts at (2,1), target at (6,1).
        # Player stands at (1,1) to begin the push — that tile IS passable.
        # Note: block at (1,1) would be unsolvable because the player cannot
        # stand at (0,1) to initiate the first push (not in passable).
        passable = frozenset((c, 1) for c in range(1, 8))
        assert _sokoban_bfs((2, 1), (6, 1), passable, set())

    def test_unsolvable_block_in_corner_no_target(self):
        # Block trapped in top-left corner, target is centre — dead square
        passable = self._rect_passable(1, 1, 5, 5)
        dead = _compute_dead_squares(passable, [(3, 3)])
        assert (1, 1) in dead
        assert not _sokoban_bfs((1, 1), (3, 3), passable, dead)

    def test_unsolvable_impossible_path(self):
        # Block separated from target by a wall with no path around it
        passable = frozenset([(1, 1), (2, 1)])  # only two tiles
        # Target at (2,1), block at (1,1) — player cannot stand anywhere to push
        # (player needs to be at (0,1) which is not in passable)
        result = _sokoban_bfs((1, 1), (2, 1), passable, set())
        assert not result


# ── Invariant S: 1-push positions are always solvable ─────────────────────────

@given(
    plate_c=st.integers(min_value=4, max_value=24),
    plate_r=st.integers(min_value=4, max_value=11),
    direction=st.sampled_from(CARDINAL),
)
@settings(max_examples=500)
def test_invariant_s_one_push_position_is_solvable(plate_c, plate_r, direction):
    """INVARIANT S: block at plate+D with plate+2D passable → solvable in 1 push."""
    dc, dr = direction
    plate  = (plate_c,        plate_r)
    block  = (plate_c + dc,   plate_r + dr)
    player = (plate_c + 2*dc, plate_r + 2*dr)

    # Build a generous room containing all three tiles
    passable = frozenset(
        (c, r)
        for c in range(plate_c - 3, plate_c + 4)
        for r in range(plate_r - 3, plate_r + 4)
    )
    assert block  in passable
    assert player in passable

    result = _sokoban_bfs(block, plate, passable, dead_squares=set())
    assert result, (
        f"1-push failed: direction={direction}, plate={plate}, "
        f"block={block}, player={player}")


# ── Corollary: 1-push position exists in any game-sized room ──────────────────

@given(
    room_w=st.integers(min_value=3, max_value=12),
    room_h=st.integers(min_value=3, max_value=8),
)
@settings(max_examples=300)
def test_one_push_position_exists_somewhere_in_room(room_w, room_h):
    """For any rectangular room ≥3×3, there exists at least one plate position
    that has a valid 1-push block position (i.e. the 1-push placement algorithm
    can always find a solvable configuration — it just needs to pick the plate
    location appropriately, not at every position).

    Note: NOT every plate position has a 1-push slot. For example, in a 3×3 room
    the centre tile has no 1-push slot because the player would need to stand
    outside the room boundary. But a plate at any non-centre position in 3×3
    does have one (e.g. corners and edge-centres all work)."""
    col, row = 2, 2
    passable = frozenset(
        (c, r) for c in range(col, col + room_w) for r in range(row, row + room_h)
    )
    any_plate_has_push = any(
        any(
            (px + dc, py + dr) in passable and (px + 2*dc, py + 2*dr) in passable
            for dc, dr in CARDINAL
        )
        for px, py in passable
    )
    assert any_plate_has_push, (
        f"No valid 1-push placement exists in any position of {room_w}×{room_h} room")


# ── Dead square correctness ───────────────────────────────────────────────────

class TestDeadSquares:

    def _rect_passable(self, col, row, w, h):
        return frozenset(
            (c, r) for c in range(col, col + w) for r in range(row, row + h)
        )

    def test_target_itself_is_alive(self):
        passable = self._rect_passable(1, 1, 5, 5)
        dead = _compute_dead_squares(passable, [(3, 3)])
        assert (3, 3) not in dead

    def test_corner_is_dead_for_centre_target(self):
        passable = self._rect_passable(1, 1, 5, 5)
        dead = _compute_dead_squares(passable, [(3, 3)])
        assert (1, 1) in dead

    def test_no_dead_squares_when_target_is_corner(self):
        """If the target IS a corner, the corner is not dead."""
        passable = self._rect_passable(1, 1, 5, 5)
        dead = _compute_dead_squares(passable, [(1, 1)])
        assert (1, 1) not in dead

    def test_corridor_endpoint_tiles_are_dead(self):
        """In a 1×9 corridor with target at the centre, the two endpoint tiles
        (1,1) and (9,1) are dead squares: the player cannot stand at (0,1) or
        (10,1) to initiate a push, so a block stranded at either end is stuck.
        Interior tiles (2,1)-(8,1) are alive."""
        passable = frozenset((c, 1) for c in range(1, 10))
        dead = _compute_dead_squares(passable, [(5, 1)])
        assert (1, 1) in dead,  "Left endpoint should be a dead square"
        assert (9, 1) in dead,  "Right endpoint should be a dead square"
        interior_dead = dead - {(1, 1), (9, 1)}
        assert interior_dead == set(), (
            f"Interior tiles should be alive but are dead: {interior_dead}")

    @given(
        seed=st.integers(min_value=0, max_value=2**31 - 1),
        room_w=st.integers(min_value=3, max_value=10),
        room_h=st.integers(min_value=3, max_value=8),
    )
    @settings(max_examples=300)
    def test_dead_squares_do_not_include_target(self, seed, room_w, room_h):
        """The target tile itself must never be a dead square."""
        rng = random.Random(seed)
        passable = frozenset(
            (c, r) for c in range(2, 2 + room_w) for r in range(2, 2 + room_h)
        )
        target = rng.choice(sorted(passable))
        dead = _compute_dead_squares(passable, [target])
        assert target not in dead, (
            f"Target {target} is a dead square in {room_w}×{room_h} room")


# ── End-to-end: push puzzles must pass on first attempt ───────────────────────

@given(seed=st.integers(min_value=0, max_value=2**31 - 1))
@settings(max_examples=100, deadline=None)
def test_pipeline_push_puzzles_never_fail_end_to_end(seed):
    """validate_push_puzzles() must pass for every generated gated level.
    If this raises ValueError, the implementation is retrying to mask a bug."""
    rng = random.Random(seed)
    graph = LevelGraph.generate(FS_GATED, rng=rng)
    level = build_level_dict(graph, rng=random.Random(seed + 1),
                             strategies=['horizontal', 'vertical', 'off_centre'])
    for room_name, room in level['rooms'].items():
        tile_owner = room.get('tile_owner', {})
        errors = validate_push_puzzles(room, tile_owner)
        assert errors == [], (
            f"seed={seed}, room={room_name!r}: push puzzle unsolvable: {errors}")


@given(seed=st.integers(min_value=0, max_value=2**31 - 1))
@settings(max_examples=50, deadline=None)
def test_full_pipeline_no_value_error(seed):
    """build_level_dict must never raise ValueError for any seed.
    A ValueError means a transformation produced an invalid state."""
    rng = random.Random(seed)
    graph = LevelGraph.generate(FS_ALL, rng=rng)
    level = build_level_dict(graph, rng=random.Random(seed + 1),
                             strategies=['horizontal', 'vertical', 'off_centre'])
    assert 'rooms' in level
    assert 'player_start' in level
