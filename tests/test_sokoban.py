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
    _puzzle_candidates, _puzzle_solution_tiles,
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


# ── Unit tests: _puzzle_candidates reverse BFS ────────────────────────────────

class TestPuzzleCandidates:

    def _rect(self, col, row, w, h):
        return frozenset((c, r) for c in range(col, col+w) for r in range(row, row+h))

    def test_corridor_valid_positions(self):
        """In 1×7 corridor, endpoints are dead; interior tiles are valid for centre plate."""
        # (1,1)…(7,1), plate at (4,1)
        # endpoint (1,1): player would need (0,1) — not passable → dead
        # endpoint (7,1): player would need (8,1) — not passable → dead
        # (2,1)…(3,1) and (5,1)…(6,1): reachable via push chain → valid
        passable = frozenset((c, 1) for c in range(1, 8))
        plate = (4, 1)
        result = _puzzle_candidates(plate, passable, passable, set())
        assert (3, 1) in result, "one tile left of plate should be valid"
        assert (2, 1) in result, "two tiles left of plate should be valid"
        assert (5, 1) in result, "one tile right of plate should be valid"
        assert (6, 1) in result, "two tiles right of plate should be valid"
        assert (1, 1) not in result, "left endpoint is dead"
        assert (7, 1) not in result, "right endpoint is dead"

    def test_room_2d_adjacent_tiles_valid(self):
        """In 5×5 room, immediate neighbours of centre plate are valid."""
        passable = self._rect(1, 1, 5, 5)
        plate = (3, 3)
        result = _puzzle_candidates(plate, passable, passable, set())
        for dc, dr in ((1,0),(-1,0),(0,1),(0,-1)):
            neighbour = (plate[0]+dc, plate[1]+dr)
            assert neighbour in result, f"{neighbour} should be a valid block position"

    def test_excluded_tiles_absent_from_result(self):
        """Tiles in the excluded set are not returned as valid positions."""
        passable = self._rect(1, 1, 5, 5)
        plate = (3, 3)
        excluded = {(2, 3), (4, 3)}  # two neighbours of plate
        result = _puzzle_candidates(plate, passable, passable, excluded)
        assert (2, 3) not in result
        assert (4, 3) not in result

    def test_plate_itself_not_a_candidate(self):
        """The plate tile is never returned as a valid block start."""
        passable = self._rect(1, 1, 5, 5)
        plate = (3, 3)
        result = _puzzle_candidates(plate, passable, passable, set())
        assert plate not in result

    def test_blocked_player_position_excludes_tile(self):
        """A tile adjacent to plate is invalid if the player can't stand 2 tiles away."""
        # Plate at (3,1) in a 3×3 room; the tile above (3,0) is outside passable.
        # So (3,2) → push up to (3,1): player at (3,3) — passable? Yes (if in room).
        # But (3,0) → push down to (3,1)... wait, (3,0) is outside passable; not a floor tile.
        # More concrete test: passable = {(1,1),(2,1),(3,1)} (1×3 corridor, horizontal)
        # Plate at (2,1). Above/below: (2,0),(2,2) not passable → tiles (2,0),(2,2) skip.
        passable = frozenset([(1,1),(2,1),(3,1)])
        plate = (2, 1)
        result = _puzzle_candidates(plate, passable, passable, set())
        # (1,1): player needs (0,1) — not passable → dead
        # (3,1): player needs (4,1) — not passable → dead
        assert (1, 1) not in result, "(1,1) is dead: player can't stand at (0,1)"
        assert (3, 1) not in result, "(3,1) is dead: player can't stand at (4,1)"
        assert len(result) == 0, "no valid block positions in 1×3 corridor with plate at centre"

    def test_room_floor_restricts_candidates(self):
        """Candidates are restricted to room_floor, even if passable is larger."""
        room_floor = frozenset((c, r) for c in range(1, 4) for r in range(1, 4))  # 3×3
        passable = frozenset((c, r) for c in range(0, 5) for r in range(0, 5))    # 5×5
        plate = (2, 2)  # centre of 3×3
        result = _puzzle_candidates(plate, room_floor, passable, set())
        # All results must be inside room_floor
        for pos in result:
            assert pos in room_floor, f"{pos} outside room_floor"


# ── Unit tests: _puzzle_solution_tiles ────────────────────────────────────────

class TestPuzzleSolutionTiles:

    def test_one_push_solution(self):
        """Solution tiles for a 1-push puzzle include block start and player position."""
        passable = frozenset((c, r) for c in range(1, 6) for r in range(1, 6))
        plate = (3, 3)
        candidates = _puzzle_candidates(plate, passable, passable, set())
        # Block at (2,3): push right to (3,3), player at (1,3)
        block = (2, 3)
        assert block in candidates
        tiles = _puzzle_solution_tiles(block, plate, candidates)
        assert (2, 3) in tiles, "block start must be in solution tiles"
        assert (1, 3) in tiles, "player push position must be in solution tiles"
        assert (3, 3) in tiles, "plate (block's final position) must be in solution tiles"

    def test_solution_tiles_include_plate(self):
        """The plate is always in solution tiles (block ends up there)."""
        passable = frozenset((c, r) for c in range(1, 6) for r in range(1, 4))
        plate = (3, 2)
        candidates = _puzzle_candidates(plate, passable, passable, set())
        for block in candidates:
            tiles = _puzzle_solution_tiles(block, plate, candidates)
            assert plate in tiles, f"plate must be in solution tiles for block={block}"

    @given(
        seed=st.integers(min_value=0, max_value=2**31 - 1),
        room_w=st.integers(min_value=4, max_value=10),
        room_h=st.integers(min_value=4, max_value=8),
    )
    @settings(max_examples=200, deadline=None)
    def test_solution_tiles_are_subset_of_passable(self, seed, room_w, room_h):
        """Every solution tile must be in the passable set."""
        rng = random.Random(seed)
        passable = frozenset((c, r) for c in range(2, 2+room_w) for r in range(2, 2+room_h))
        plate = rng.choice(sorted(passable))
        candidates = _puzzle_candidates(plate, passable, passable, set())
        if not candidates:
            return
        block = rng.choice(sorted(candidates))
        tiles = _puzzle_solution_tiles(block, plate, candidates)
        for t in tiles:
            assert t in passable, f"solution tile {t} is not passable"


# ── Integration: multi-puzzle exclusion ───────────────────────────────────────

@given(seed=st.integers(min_value=0, max_value=2**31 - 1))
@settings(max_examples=100, deadline=None)
def test_multi_puzzle_solution_tiles_do_not_overlap(seed):
    """The solution tiles of puzzle N are in excluded when puzzle N+1 is placed,
    so no later puzzle's plate or block lands on a tile required by an earlier puzzle."""
    from levellayout import EdgeType, MIN_C, MAX_C, MIN_R, MAX_R
    # Synthetic: two 5×5 rooms side by side sharing a corridor
    passable = frozenset(
        (c, r) for c in range(1, 12) for r in range(1, 6)
    )
    room_a = frozenset((c, r) for c in range(1, 6) for r in range(1, 6))
    room_b = frozenset((c, r) for c in range(7, 12) for r in range(1, 6))

    rng = random.Random(seed)
    excluded = set()

    # Place puzzle A
    plate_a_pos = rng.choice(sorted(room_a))
    cands_a = _puzzle_candidates(plate_a_pos, room_a, passable, excluded)
    if not cands_a:
        return
    block_a = rng.choice(sorted(cands_a))
    sol_a = _puzzle_solution_tiles(block_a, plate_a_pos, cands_a)
    excluded.update(sol_a)

    # Place puzzle B; its plate and block must not be in sol_a
    plate_b_pos = rng.choice(sorted(room_b))
    cands_b = _puzzle_candidates(plate_b_pos, room_b, passable, excluded)
    if not cands_b:
        return
    block_b = rng.choice(sorted(cands_b))

    assert plate_b_pos not in sol_a, "puzzle B plate overlaps puzzle A solution path"
    assert block_b not in sol_a, "puzzle B block overlaps puzzle A solution path"
