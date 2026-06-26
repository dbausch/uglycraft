"""Layout algorithm: arrange a level graph onto 30×16 grids.

Takes a LevelGraph and produces the game-format dict that game.py expects.

Key invariant: every pair of rooms is separated by at least 1 tile of wall.
Edges are the ONLY passages between rooms — exactly one wall tile per edge
is converted to a doorway/lock/gate. This guarantees the grid faithfully
represents the graph topology.
"""
import random
from collections import deque
from constants import (COLS, ROWS, WALL_STONE, WALL_REINFORCED, WALL_WOODEN)
from levelgraph import LevelGraph, NodeSize, EdgeType, SIZE_RANGES

# Interior bounds
MIN_C, MAX_C = 1, COLS - 2   # 1-28
MIN_R, MAX_R = 1, ROWS - 2   # 1-14
INT_W = MAX_C - MIN_C + 1    # 28
INT_H = MAX_R - MIN_R + 1    # 14

MIN_ENEMY_DIST = 10


class PlacedNode:
    """A graph node placed at a spatial position on the grid."""

    __slots__ = ('name', 'col', 'row', 'w', 'h', 'floor_tiles')

    def __init__(self, name, col, row, w, h):
        self.name = name
        self.col = col
        self.row = row
        self.w = w
        self.h = h
        self.floor_tiles = frozenset(
            (c, r) for c in range(col, col + w) for r in range(row, row + h)
        )


# ── Layout strategies ─────────────────────────────────────────────────────────

STRATEGIES = ['horizontal', 'vertical', 'off_centre']


def layout_graph(graph, rng=None, strategies=None):
    """Arrange graph nodes onto a 30×16 grid using a random strategy.

    Returns {node_name: PlacedNode}.
    """
    rng = rng or random.Random()

    corridor_name = None
    for name, node in graph.nodes.items():
        if node.size == NodeSize.CORRIDOR:
            corridor_name = name
            break
    if corridor_name is None:
        raise ValueError("Graph has no CORRIDOR node")

    room_names = [n for n in graph.nodes if n != corridor_name]
    available = strategies or STRATEGIES
    strategy = rng.choice(available)

    if strategy == 'vertical':
        return _layout_vertical(corridor_name, room_names, rng)
    elif strategy == 'off_centre':
        return _layout_off_centre(corridor_name, room_names, rng)
    else:
        return _layout_horizontal(corridor_name, room_names, rng)


def _layout_horizontal(corridor_name, room_names, rng):
    """Corridor runs left-right, rooms above and below."""
    cor_h = rng.randint(2, 3)
    remaining = INT_H - cor_h - 2
    above_h = remaining // 2
    below_h = remaining - above_h
    if above_h < 3:
        above_h = 3
        below_h = remaining - above_h
    if below_h < 3:
        below_h = 3
        above_h = remaining - below_h

    cor_row = MIN_R + above_h + 1
    placed = {}
    placed[corridor_name] = PlacedNode(
        corridor_name, MIN_C, cor_row, INT_W, cor_h)

    rng.shuffle(room_names)
    mid = (len(room_names) + 1) // 2

    _pack_band(placed, room_names[:mid], rng,
               band_col=MIN_C, band_row=MIN_R,
               band_w=INT_W, band_h=above_h)
    _pack_band(placed, room_names[mid:], rng,
               band_col=MIN_C, band_row=cor_row + cor_h + 1,
               band_w=INT_W, band_h=below_h)

    return placed


def _layout_vertical(corridor_name, room_names, rng):
    """Corridor runs top-bottom, rooms left and right."""
    cor_w = rng.randint(2, 3)
    remaining = INT_W - cor_w - 2
    left_w = remaining // 2
    right_w = remaining - left_w
    if left_w < 5:
        left_w = 5
        right_w = remaining - left_w
    if right_w < 5:
        right_w = 5
        left_w = remaining - right_w

    cor_col = MIN_C + left_w + 1
    placed = {}
    placed[corridor_name] = PlacedNode(
        corridor_name, cor_col, MIN_R, cor_w, INT_H)

    rng.shuffle(room_names)
    mid = (len(room_names) + 1) // 2

    _pack_band_vertical(placed, room_names[:mid], rng,
                         band_col=MIN_C, band_row=MIN_R,
                         band_w=left_w, band_h=INT_H)
    _pack_band_vertical(placed, room_names[mid:], rng,
                         band_col=cor_col + cor_w + 1, band_row=MIN_R,
                         band_w=right_w, band_h=INT_H)

    return placed


def _layout_off_centre(corridor_name, room_names, rng):
    """Corridor shifted up or down, asymmetric room bands."""
    cor_h = rng.randint(2, 3)
    remaining = INT_H - cor_h - 2
    # Shift: one band gets 60-80% of the space
    split = rng.uniform(0.3, 0.7)
    above_h = max(3, int(remaining * split))
    below_h = max(3, remaining - above_h)
    if above_h + below_h > remaining:
        above_h = remaining - below_h

    cor_row = MIN_R + above_h + 1
    placed = {}
    placed[corridor_name] = PlacedNode(
        corridor_name, MIN_C, cor_row, INT_W, cor_h)

    rng.shuffle(room_names)
    # Put more rooms in the bigger band
    if above_h >= below_h:
        big_count = (len(room_names) + 1) * 2 // 3
    else:
        big_count = len(room_names) // 3
    big_count = max(1, min(len(room_names) - 1, big_count))

    _pack_band(placed, room_names[:big_count], rng,
               band_col=MIN_C, band_row=MIN_R,
               band_w=INT_W, band_h=above_h)
    _pack_band(placed, room_names[big_count:], rng,
               band_col=MIN_C, band_row=cor_row + cor_h + 1,
               band_w=INT_W, band_h=below_h)

    return placed


def _pack_band_vertical(placed, room_names, rng,
                         band_col, band_row, band_w, band_h):
    """Pack rooms into a vertical band (left or right of a vertical corridor)."""
    if not room_names:
        return

    n = len(room_names)
    walls_between = n - 1
    usable = band_h - walls_between
    if usable < n * 3:
        base = 3
    else:
        base = usable // n

    heights = [base] * n
    leftover = usable - base * n
    for i in range(max(0, leftover)):
        heights[i % n] += 1
    rng.shuffle(heights)

    row = band_row
    for i, name in enumerate(room_names):
        h = heights[i]
        w = band_w

        if row + h > MAX_R + 1:
            h = MAX_R + 1 - row
        if band_col + w > MAX_C + 1:
            w = MAX_C + 1 - band_col

        if w >= 3 and h >= 2:
            placed[name] = PlacedNode(name, band_col, row, w, h)

        row += h + 1


def _pack_band(placed, room_names, rng, band_col, band_row, band_w, band_h):
    """Pack rooms into a horizontal band with 1-tile wall between each."""
    if not room_names:
        return

    n = len(room_names)
    # n rooms need (n-1) wall tiles between them.
    # Remaining width is distributed among rooms.
    walls_between = n - 1
    usable = band_w - walls_between
    if usable < n * 3:
        base = 3
    else:
        base = usable // n

    widths = [base] * n
    leftover = usable - base * n
    for i in range(max(0, leftover)):
        widths[i % n] += 1
    rng.shuffle(widths)

    col = band_col
    for i, name in enumerate(room_names):
        w = widths[i]
        h = band_h

        # Clamp
        if col + w > MAX_C + 1:
            w = MAX_C + 1 - col
        if band_row + h > MAX_R + 1:
            h = MAX_R + 1 - band_row

        if w >= 3 and h >= 2:
            placed[name] = PlacedNode(name, col, band_row, w, h)

        col += w + 1  # +1 for wall column between rooms


# ── Tile ownership map ────────────────────────────────────────────────────────

def build_tile_owner(placed):
    """Build {(col, row): node_name} for every floor tile."""
    owner = {}
    for name, pn in placed.items():
        for tile in pn.floor_tiles:
            owner[tile] = name
    return owner


# ── Wall derivation ──────────────────────────────────────────────────────────

def derive_walls(graph, placed):
    """Derive walls from negative space and punch edges as the only passages.

    Invariant: two rooms are separated by complete wall on their shared
    boundary, with exactly one tile removed per edge.
    """
    floor = set()
    for pn in placed.values():
        floor.update(pn.floor_tiles)

    # Everything interior that isn't floor is wall (reinforced)
    walls = {}
    for c in range(MIN_C, MAX_C + 1):
        for r in range(MIN_R, MAX_R + 1):
            if (c, r) not in floor:
                walls[(c, r)] = WALL_REINFORCED

    # Process edges: find the shared-boundary wall tile(s), convert them
    water_tiles = []
    for edge in graph.edges:
        if edge.node_a not in placed or edge.node_b not in placed:
            continue
        pa = placed[edge.node_a]
        pb = placed[edge.node_b]

        if edge.edge_type == EdgeType.WATER:
            stream = _build_water_stream(pa, pb, walls)
            for wt in stream:
                walls.pop(wt, None)
            water_tiles.extend(stream)
        else:
            conn = _find_connection_tile(pa, pb, walls)
            if conn is None:
                raise ValueError(
                    f"Edge {edge.node_a!r}<->{edge.node_b!r} has no shared "
                    f"boundary tile. "
                    f"{pa.name} at col={pa.col} row={pa.row} "
                    f"w={pa.w} h={pa.h}; "
                    f"{pb.name} at col={pb.col} row={pb.row} "
                    f"w={pb.w} h={pb.h}")
            if edge.edge_type == EdgeType.OPEN:
                walls.pop(conn, None)
            elif edge.edge_type == EdgeType.BREAKABLE:
                wtype = edge.params.get('wall_type', 'stone')
                walls[conn] = WALL_STONE if wtype == 'stone' else WALL_WOODEN
            elif edge.edge_type in (EdgeType.LOCKED, EdgeType.GATED,
                                     EdgeType.STAIRS):
                walls.pop(conn, None)

    return walls, water_tiles


def _build_water_stream(pa, pb, walls):
    """Build a multi-tile water stream along the shared boundary.

    Returns a list of (col, row) tiles forming the stream. The stream
    runs along the entire shared boundary between two rooms — all wall
    tiles that are adjacent to both rooms' floor areas.
    """
    candidates = []
    for pos in list(walls.keys()):
        adj_a = any((pos[0] + dc, pos[1] + dr) in pa.floor_tiles
                     for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        adj_b = any((pos[0] + dc, pos[1] + dr) in pb.floor_tiles
                     for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if adj_a and adj_b:
            candidates.append(pos)

    if not candidates:
        return []

    # Sort by position for consistent flow direction
    candidates.sort()
    return candidates


def _find_connection_tile(pa, pb, walls):
    """Find a wall tile on the shared boundary between two rooms.

    A shared-boundary tile is a wall tile that is cardinally adjacent to
    floor tiles of BOTH rooms.
    """
    candidates = []
    for pos in walls:
        adj_a = any((pos[0] + dc, pos[1] + dr) in pa.floor_tiles
                     for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        adj_b = any((pos[0] + dc, pos[1] + dr) in pb.floor_tiles
                     for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if adj_a and adj_b:
            candidates.append(pos)

    if not candidates:
        return None

    # Prefer centre of shared boundary; (col, row) breaks ties deterministically
    avg_c = sum(c for c, r in candidates) / len(candidates)
    avg_r = sum(r for c, r in candidates) / len(candidates)
    candidates.sort(key=lambda t: (abs(t[0] - avg_c) + abs(t[1] - avg_r), t[0], t[1]))
    return candidates[0]


# ── Layout invariant validation ──────────────────────────────────────────────

def validate_layout(graph, placed, walls):
    """Check that the layout faithfully represents the graph topology.

    A "passage" is any tile on the shared boundary that the player can
    eventually get through: a doorway (no wall), a breakable wall (stone/
    wooden), a locked door, or a gate. Reinforced wall tiles are NOT
    passages.

    Returns list of error strings (empty = valid).
    """
    errors = []
    edge_set = {}
    for edge in graph.edges:
        edge_set[(edge.node_a, edge.node_b)] = edge.edge_type
        edge_set[(edge.node_b, edge.node_a)] = edge.edge_type

    names = list(placed.keys())
    for i, name_a in enumerate(names):
        pa = placed[name_a]
        for name_b in names[i + 1:]:
            pb = placed[name_b]

            # Check for directly adjacent floor tiles (no wall at all)
            for (c, r) in pa.floor_tiles:
                for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nc, nr = c + dc, r + dr
                    if (nc, nr) in pb.floor_tiles:
                        errors.append(
                            f"Rooms {name_a!r} and {name_b!r} have adjacent "
                            f"floor tiles at ({c},{r})<->({nc},{nr})")

            # Count passages: boundary tiles that are passable (not reinforced)
            passages = []
            for c in range(MIN_C, MAX_C + 1):
                for r in range(MIN_R, MAX_R + 1):
                    # A passage is a tile that is either not a wall, or a
                    # non-reinforced wall (breakable). Reinforced = blocked.
                    if walls.get((c, r)) == WALL_REINFORCED:
                        continue
                    # Is it on the shared boundary?
                    adj_a = any((c + dc, r + dr) in pa.floor_tiles
                                for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                    adj_b = any((c + dc, r + dr) in pb.floor_tiles
                                for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                    if adj_a and adj_b:
                        passages.append((c, r))

            edge_type = edge_set.get((name_a, name_b))
            if edge_type is not None:
                if edge_type == EdgeType.WATER:
                    if len(passages) < 1:
                        errors.append(
                            f"Water edge {name_a!r}<->{name_b!r} has 0 passages")
                elif len(passages) != 1:
                    errors.append(
                        f"Edge {name_a!r}<->{name_b!r} has {len(passages)} "
                        f"passages (expected 1): {passages}")
            else:
                if passages:
                    errors.append(
                        f"No edge between {name_a!r} and {name_b!r} but "
                        f"{len(passages)} passages exist: {passages}")

    return errors


# ── Push puzzle solvability ────────────────────────────────────────────────────

def validate_push_puzzles(room_data, tile_owner):
    """Check that every push puzzle (block → plate) is solvable.

    For each gate_id, finds the blocks and plate in the same room, then
    runs a Sokoban-style BFS to verify the block can reach the plate.

    State: (player_pos, frozenset_of_block_positions)
    Transitions: player moves to adjacent tile; if it's a block and the
    tile behind the block is free, the block is pushed.

    Returns list of error strings (empty = all solvable).
    """
    errors = []
    walls = room_data.get('walls', {})
    blocks = room_data.get('pushable_blocks', [])
    plates = room_data.get('pressure_plates', [])
    gates_list = room_data.get('gates', [])

    if not gates_list or not plates or not blocks:
        return errors

    locked_doors = room_data.get('locked_doors', [])

    # Build set of passable tiles: exclude ALL walls (any type), locked
    # doors, gates (closed), and other blocks — matching what the game does.
    # Breakable walls (stone/wooden) ARE collision in the game until broken,
    # and blocks can't be pushed through them.
    all_obstacles = set()
    for pos in walls:
        all_obstacles.add(pos)
    for dc, dr, _ in locked_doors:
        all_obstacles.add((dc, dr))
    for gc, gr, _ in gates_list:
        all_obstacles.add((gc, gr))
    for bpos in blocks:
        all_obstacles.add(bpos)

    passable = set()
    for c in range(MIN_C, MAX_C + 1):
        for r in range(MIN_R, MAX_R + 1):
            if (c, r) not in all_obstacles:
                passable.add((c, r))

    # Map gate_id → plate position
    plate_map = {}
    for pc, pr, gate_id in plates:
        plate_map[gate_id] = (pc, pr)

    # Map gate_id → which room the plate is in
    gate_rooms = {}
    for gate_id, plate_pos in plate_map.items():
        gate_rooms[gate_id] = tile_owner.get(plate_pos)

    # For each gate, check solvability
    for gc, gr, gate_id in gates_list:
        plate_pos = plate_map.get(gate_id)
        if plate_pos is None:
            errors.append(f"Gate {gate_id} has no pressure plate")
            continue

        plate_room = gate_rooms.get(gate_id)

        # Find blocks in the same room as the plate
        room_blocks = [
            (bc, br) for bc, br in blocks
            if tile_owner.get((bc, br)) == plate_room
        ]
        if not room_blocks:
            errors.append(f"Gate {gate_id}: no blocks in plate room {plate_room}")
            continue

        # Room tiles for movement bounds
        room_tiles = set()
        if plate_room:
            room_tiles = {pos for pos, name in tile_owner.items()
                          if name == plate_room}
        # Also include doorway tiles (not in tile_owner but passable)
        for pos in passable:
            if pos not in walls:
                room_tiles.add(pos)

        # Sokoban BFS: can ANY block reach the plate?
        if _can_push_block_to(room_blocks, plate_pos, passable):
            continue

        errors.append(f"Gate {gate_id}: no block can be pushed to plate at {plate_pos}")

    return errors


def _compute_dead_squares(passable, targets):
    """Pre-compute dead squares using reverse-reachability from targets.

    A dead square is a passable tile from which a block can NEVER be
    pushed to any target. Uses reverse BFS: from each target, simulate
    pulling (reverse-pushing) the block to find all tiles it could have
    come from. Tiles not reached by any target's pull-BFS are dead.

    A reverse-push from position P in direction D means: the block was
    at P+D and got pushed to P. For this to be valid, both P+D (where
    the block was) and P-D (where the player stood) must be passable.
    """
    alive = set()
    for target in targets:
        # Reverse-BFS: from the target, find all tiles a block could
        # have been pushed FROM to eventually reach the target.
        # A forward push in direction D: player at P, block at P+D,
        # block moves to P+2D. So reverse from position Q: the block
        # came from Q-D (origin), pushed by player at Q-2D.
        visited = {target}
        queue = deque([target])
        while queue:
            bx, by = queue.popleft()
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                origin = (bx - dc, by - dr)       # block came from here
                player_was = (bx - 2*dc, by - 2*dr)  # player stood here
                if (origin in passable and player_was in passable
                        and origin not in visited):
                    visited.add(origin)
                    queue.append(origin)
        alive.update(visited)
    return passable - alive


def compute_dead_squares_for_room(room_data):
    """Compute dead squares: tiles where a block can never reach any
    pressure plate, considering only PERMANENT obstacles (reinforced
    walls and borders). Temporary obstacles (doors, gates, breakable
    walls, other blocks) are ignored — they'll be removed during play."""
    walls = room_data.get('walls', {})
    plates = room_data.get('pressure_plates', [])

    if not plates:
        return set()

    # Only reinforced walls are permanent obstacles
    permanent = set()
    for pos, wt in walls.items():
        if wt == WALL_REINFORCED:
            permanent.add(pos)

    passable = set()
    for c in range(MIN_C, MAX_C + 1):
        for r in range(MIN_R, MAX_R + 1):
            if (c, r) not in permanent:
                passable.add((c, r))

    targets = [(pc, pr) for pc, pr, _ in plates]
    return _compute_dead_squares(passable, targets)


def _can_push_block_to(block_positions, target, passable):
    """Check if any block can be pushed to the target.

    Uses dead square detection + Sokoban BFS.
    Dead squares are computed with the block's starting tile included in
    passable: once the block moves away that tile is accessible to the player.
    """
    for block_start in block_positions:
        p = passable | {block_start}  # block's start tile becomes walkable after move
        dead = _compute_dead_squares(p, [target])
        if block_start in dead:
            continue
        if _sokoban_bfs(block_start, target, p, dead):
            return True
    return False


def _player_reachable(player_start, block_pos, passable):
    """BFS for player movement, treating block_pos as impassable."""
    visited = {player_start}
    frontier = deque([player_start])
    while frontier:
        c, r = frontier.popleft()
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nc, nr = c + dc, r + dr
            if ((nc, nr) in passable and (nc, nr) not in visited
                    and (nc, nr) != block_pos):
                visited.add((nc, nr))
                frontier.append((nc, nr))
    return visited


def _normalize_player(player_pos, block_pos, passable):
    """Canonical representative of the player's connected component."""
    reach = _player_reachable(player_pos, block_pos, passable)
    return min(reach)


def _sokoban_bfs(block_start, target, passable, dead_squares):
    """Sokoban BFS for a single block with dead square pruning.

    State: (block_pos, player_zone).
    Rejects any state where the block is on a dead square.
    """
    if block_start == target:
        return True

    player_candidates = [p for p in passable if p != block_start]
    if not player_candidates:
        return False

    tried_starts = set()
    for ps in player_candidates:
        norm = _normalize_player(ps, block_start, passable)
        if norm in tried_starts:
            continue
        tried_starts.add(norm)

        start_state = (block_start, norm)
        visited = {start_state}
        queue = deque([start_state])

        while queue:
            (bx, by), p_zone = queue.popleft()
            p_reach = _player_reachable(p_zone, (bx, by), passable)

            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                push_from = (bx - dc, by - dr)
                push_to = (bx + dc, by + dr)

                if push_from not in p_reach:
                    continue
                if push_to not in passable:
                    continue
                if push_to in dead_squares:
                    continue

                if push_to == target:
                    return True

                new_p_zone = _normalize_player(
                    (bx, by), push_to, passable)
                new_state = (push_to, new_p_zone)

                if new_state not in visited:
                    visited.add(new_state)
                    queue.append(new_state)

    return False


# ── Push puzzle placement ─────────────────────────────────────────────────────

_CARDINAL = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _puzzle_candidates(plate, room_floor, passable, excluded):
    """Reverse BFS from plate: find all room_floor tiles a block can start on
    and still reach plate via push sequences.

    Returns dict {pos: (parent_pos, push_dir)} for path reconstruction.
    push_dir is the direction D such that the block moves in direction D
    from pos toward parent_pos (i.e. block goes pos → parent_pos in one push).

    Tiles in excluded are treated as permanently blocked.
    """
    valid = {}    # pos → (parent_pos, push_dir)
    invalid = set()
    queue = deque()

    px, py = plate
    for dc, dr in _CARDINAL:
        A = (px - dc, py - dr)   # block was here, pushed in direction (dc,dr) to plate
        Q = (px - 2*dc, py - 2*dr)   # player stood here
        if (A in room_floor and A not in excluded and A in passable
                and Q in passable and A not in valid):
            valid[A] = (plate, (dc, dr))
            queue.append(A)
        elif A in room_floor and A in passable and A not in excluded and A not in valid:
            invalid.add(A)

    while queue:
        T = queue.popleft()
        tx, ty = T
        for dc, dr in _CARDINAL:
            S = (tx - dc, ty - dr)   # block was here, pushed in direction (dc,dr) to T
            R = (tx - 2*dc, ty - 2*dr)   # player stood here
            if S in valid or S in invalid or S in excluded:
                continue
            if S not in room_floor or S not in passable or S == plate:
                continue
            if R in passable:
                valid[S] = (T, (dc, dr))
                queue.append(S)
            else:
                invalid.add(S)

    return valid


def _puzzle_solution_tiles(block, plate, candidates):
    """Trace the shortest push path from block to plate using candidates parent pointers.

    Returns the set of tiles that must remain free for this puzzle to be solvable:
    the block's trajectory and the player's push-from positions at each step,
    plus the plate (where the block finally rests).
    """
    tiles = set()
    current = block
    while current != plate:
        next_pos, (dc, dr) = candidates[current]
        player_pos = (current[0] - dc, current[1] - dr)
        tiles.add(current)      # block position before this push
        tiles.add(player_pos)   # player push-from position
        current = next_pos
    tiles.add(plate)            # block's final position
    return tiles


def _place_puzzle(room_name, gate_id, placed, passable, excluded, rng,
                  prior_puzzles=()):
    """Atomically select a (plate, block) pair for gate_id in room_name.

    plate and block are chosen via a backward Sokoban BFS from the plate.
    The BFS tracks (block_pos, player_zone) states, so each configuration is
    visited at most once and player reachability between pushes is guaranteed.
    The block is constrained to room_floor tiles; the player can use the full
    passable set.

    prior_puzzles: iterable of (plate_pos, block_pos) for already-placed
    puzzles.  Their blocks are treated as permanent obstacles — matching
    validate_push_puzzles which checks all puzzles simultaneously.

    Cross-puzzle non-interference is enforced structurally: the new block and
    plate must not land on any tile in `excluded` (the solution tiles of every
    prior puzzle), so prior solutions remain executable.

    Returns (plate_pos, block_pos, solution_tiles).
    Raises ValueError if no valid pair exists in the room.
    """
    room_floor = placed[room_name].floor_tiles
    # Prior blocks are permanent obstacles (validate_push_puzzles treats all
    # blocks as simultaneous obstacles when verifying solvability).
    prior_block_set = {b for _, b in prior_puzzles}
    effective_pass = passable - prior_block_set

    # Precompute connected-component maps for effective_pass minus each unique
    # block position that might appear in the BFS (plate + room_floor tiles).
    # comp_map[block_pos][player_pos] → zone representative (min tile in component).
    # One O(board) BFS per unique block; avoids O(board) per zone lookup.
    comp_cache: dict = {}

    def _comp_map(block_pos):
        if block_pos not in comp_cache:
            space = effective_pass - {block_pos}
            comp: dict = {}
            for start in sorted(space):
                if start in comp:
                    continue
                # BFS to find one connected component.
                q: deque = deque([start])
                members: list = []
                while q:
                    pos = q.popleft()
                    if pos in comp:
                        continue
                    comp[pos] = None   # placeholder
                    members.append(pos)
                    for dc2, dr2 in _CARDINAL:
                        nb = (pos[0] + dc2, pos[1] + dr2)
                        if nb in space and nb not in comp:
                            q.append(nb)
                rep = min(members)
                for m in members:
                    comp[m] = rep
            comp_cache[block_pos] = comp
        return comp_cache[block_pos]

    def get_zone(player_pos, block_pos):
        cm = _comp_map(block_pos)
        return cm.get(player_pos)   # None if player_pos == block_pos (shouldn't happen)

    pairs = []   # (P, B, sol_tiles)

    for P in sorted(room_floor):
        if P not in effective_pass or P in excluded:
            continue

        # --- Backward Sokoban BFS from P, block confined to room_floor ---
        # Initial states: block at P, player in any zone of effective_pass-{P}.
        cm_P = _comp_map(P)
        init_zones: set = set()
        init_states: list = []
        for tile in sorted(effective_pass - {P}):
            z = cm_P.get(tile)
            if z is not None and z not in init_zones:
                init_zones.add(z)
                init_states.append((P, z))

        visited: dict = {}   # state → (parent_state, push_dir) | None
        bfs_q: deque = deque()
        for s in init_states:
            if s not in visited:
                visited[s] = None
                bfs_q.append(s)

        found: dict = {}  # block_start → state (for path reconstruction)

        while bfs_q:
            curr_block, curr_zone = bfs_q.popleft()

            for dc, dr in _CARDINAL:
                old_block = (curr_block[0] - dc, curr_block[1] - dr)
                push_from = (curr_block[0] - 2 * dc, curr_block[1] - 2 * dr)

                # Block must stay in room_floor and not be excluded.
                if old_block not in room_floor or old_block in excluded:
                    continue
                if push_from not in effective_pass:
                    continue

                # After the push the player is at old_block — must be in curr_zone.
                if get_zone(old_block, curr_block) != curr_zone:
                    continue

                # Before the push: block at old_block, player at push_from.
                new_zone = get_zone(push_from, old_block)
                new_state = (old_block, new_zone)

                if new_state in visited:
                    continue

                visited[new_state] = ((curr_block, curr_zone), (dc, dr))
                bfs_q.append(new_state)

                if old_block not in found:
                    found[old_block] = new_state

        # Reconstruct solution tiles for each valid block start.
        for B, first_state in found.items():
            tiles: set = set()
            state = first_state
            while True:
                info = visited.get(state)
                if info is None:
                    tiles.add(state[0])   # plate
                    break
                parent_state, (dc, dr) = info
                bpos = state[0]
                tiles.add(bpos)
                tiles.add((bpos[0] - dc, bpos[1] - dr))  # player push-from
                state = parent_state
            pairs.append((P, B, frozenset(tiles)))

    if not pairs:
        raise ValueError(
            f"No solvable puzzle placement in room {room_name!r} for gate {gate_id!r}")

    P, B, sol = rng.choice(pairs)
    return P, B, sol


# ── Item placement ─────────────────────────────────────────────────────────────

def _bfs_dist(start, passable):
    """BFS distance from start within passable tile set."""
    dist = {start: 0}
    q = deque([start])
    while q:
        c, r = q.popleft()
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nc, nr = c + dc, r + dr
            if (nc, nr) in passable and (nc, nr) not in dist:
                dist[(nc, nr)] = dist[(c, r)] + 1
                q.append((nc, nr))
    return dist


def _place_items_in_room(node, placed_node, walls, rng, player_pos=None,
                          global_used=None):
    """Pick floor positions for a node's items.

    global_used: shared set across all rooms — no two items on the same tile.
    """
    if global_used is None:
        global_used = set()
    floor = sorted(t for t in placed_node.floor_tiles if t not in walls)
    rng.shuffle(floor)
    used = global_used

    # Pre-compute distance from player if in this room
    player_dist = None
    if player_pos and player_pos in placed_node.floor_tiles:
        passable = set(placed_node.floor_tiles) - set(walls.keys())
        player_dist = _bfs_dist(player_pos, passable)

    def _next(min_dist_from_player=0):
        for p in floor:
            if p in used:
                continue
            if min_dist_from_player > 0 and player_dist:
                d = player_dist.get(p, 0)
                if d < min_dist_from_player:
                    continue
            used.add(p)
            return p
        # Fallback: farthest available tile
        if min_dist_from_player > 0 and player_dist:
            best = None
            best_d = -1
            for p in floor:
                if p in used:
                    continue
                d = player_dist.get(p, 0)
                if d > best_d:
                    best_d = d
                    best = p
            if best:
                used.add(best)
                return best
        return None

    treasures = []
    for (item_no,) in node.treasures:
        p = _next()
        if p:
            treasures.append((*p, item_no))

    materials = []
    for (mat_type,) in node.materials:
        p = _next()
        if p:
            materials.append((*p, mat_type))

    keys = []
    for (key_colour,) in node.keys:
        p = _next()
        if p:
            keys.append((*p, key_colour))

    enemy_starts = []
    for enemy_info in node.enemies:
        p = _next(min_dist_from_player=MIN_ENEMY_DIST)
        if p:
            enemy_starts.append((*p, enemy_info[0]))

    return treasures, materials, keys, enemy_starts


def _generate_flame_jets(placed_node, walls, rng):
    """Generate a flame jet that spans wall-to-wall across the room.

    The jet splits the room into two sections. It must cross the room
    (not run parallel to a wall) so there are floor tiles on both sides.
    Returns list of jet dicts with 'tiles', 'source', 'dir', 'on_ms',
    'off_ms', and 'far_tiles' (floor tiles beyond the jet).
    """
    pn = placed_node
    if pn.w < 4 and pn.h < 4:
        return []

    # Try horizontal and vertical cross-cuts through the room
    candidates = []

    # Horizontal jet (left→right or right→left) at various rows
    for r in range(pn.row + 1, pn.row + pn.h - 1):
        tiles = [(c, r) for c in range(pn.col, pn.col + pn.w)
                 if (c, r) in pn.floor_tiles and (c, r) not in walls]
        if len(tiles) < 3:
            continue
        # Check there are floor tiles above AND below the jet row
        above = [(c, r2) for c, r2 in pn.floor_tiles
                 if r2 < r and (c, r2) not in walls]
        below = [(c, r2) for c, r2 in pn.floor_tiles
                 if r2 > r and (c, r2) not in walls]
        if above and below:
            # Source wall: leftmost wall tile adjacent to the first flame tile
            sc, sr = tiles[0][0] - 1, tiles[0][1]
            if walls.get((sc, sr)) == WALL_REINFORCED:
                candidates.append((tiles, (sc, sr), (1, 0), below))

    # Vertical jet (top→bottom or bottom→top) at various columns
    for c in range(pn.col + 1, pn.col + pn.w - 1):
        tiles = [(c, r) for r in range(pn.row, pn.row + pn.h)
                 if (c, r) in pn.floor_tiles and (c, r) not in walls]
        if len(tiles) < 3:
            continue
        left = [(c2, r) for c2, r in pn.floor_tiles
                if c2 < c and (c2, r) not in walls]
        right = [(c2, r) for c2, r in pn.floor_tiles
                 if c2 > c and (c2, r) not in walls]
        if left and right:
            sc, sr = tiles[0][0], tiles[0][1] - 1
            if walls.get((sc, sr)) == WALL_REINFORCED:
                candidates.append((tiles, (sc, sr), (0, 1), right))

    if not candidates:
        return []

    rng.shuffle(candidates)
    tiles, source, direction, far_tiles = candidates[0]
    return [{
        'source': source,
        'dir': direction,
        'tiles': tiles,
        'on_ms': 2000,
        'off_ms': 2000,
        'far_tiles': [t for t in far_tiles],
    }]


# ── Game-format output ────────────────────────────────────────────────────────

def build_level_dict(graph, rng=None, strategies=None, grid_count=1):
    """Generate the complete level dict that game.py expects.

    grid_count=1: single grid (default).
    grid_count=2: split the graph across two grids connected by a border exit.
    """
    rng = rng or random.Random()

    if grid_count >= 2:
        return _build_multi_grid(graph, rng, strategies)

    placed = layout_graph(graph, rng=rng, strategies=strategies)
    walls, water_tiles = derive_walls(graph, placed)
    tile_owner = build_tile_owner(placed)

    # Find player start
    start_name = None
    for name, node in graph.nodes.items():
        if node.is_start:
            start_name = name
            break
    pn = placed[start_name]
    player_start = (pn.col + 1, pn.row + pn.h // 2)

    # Generate flame jets first so we can exclude their tiles from items
    all_flame_jets = []
    flame_tile_set = set()
    for name, node in graph.nodes.items():
        if name not in placed or not node.has_flames:
            continue
        jets = _generate_flame_jets(placed[name], walls, rng)
        for jet in jets:
            flame_tile_set.update(jet['tiles'])
            flame_tile_set.add(jet['source'])
        all_flame_jets.extend(jets)

    # Compute gate and lock tile positions.  These tiles were removed from
    # walls by derive_walls but are still obstacles until opened.  They are
    # needed both for puzzle_passable and later for all_gates/all_locked_doors.
    all_floor_tiles = set().union(*(pn.floor_tiles for pn in placed.values()))
    orig_walls = {(c, r): WALL_REINFORCED
                  for c in range(MIN_C, MAX_C + 1)
                  for r in range(MIN_R, MAX_R + 1)
                  if (c, r) not in all_floor_tiles}
    gate_tiles = set()
    lock_tiles = set()
    for _edge in graph.edges:
        if _edge.node_a not in placed or _edge.node_b not in placed:
            continue
        if _edge.edge_type == EdgeType.GATED:
            _conn = _find_connection_tile(
                placed[_edge.node_a], placed[_edge.node_b], orig_walls)
            if _conn:
                gate_tiles.add(_conn)
        elif _edge.edge_type == EdgeType.LOCKED:
            _conn = _find_connection_tile(
                placed[_edge.node_a], placed[_edge.node_b], orig_walls)
            if _conn:
                lock_tiles.add(_conn)

    # The only information needed to place a solvable push puzzle.
    puzzle_passable = ({(c, r) for c in range(MIN_C, MAX_C + 1)
                        for r in range(MIN_R, MAX_R + 1)}
                       - set(walls.keys())
                       - gate_tiles
                       - lock_tiles)

    # Place push puzzles atomically: choose (plate, block) together so the
    # block is reachable from the plate via the reverse BFS and confirmed
    # solvable by the full Sokoban BFS.  Earlier puzzles' solution tiles are
    # excluded when placing later puzzles.
    all_plates = []
    all_blocks = []
    global_used = set()
    excluded = set()
    prior_puzzles = []   # (plate, block) for all already-placed puzzles

    for name, node in graph.nodes.items():
        if name not in placed or not node.plates:
            continue
        for (gate_id,) in node.plates:
            plate, block, sol = _place_puzzle(
                name, gate_id, placed, puzzle_passable, excluded, rng,
                prior_puzzles=prior_puzzles)
            all_plates.append((*plate, gate_id))
            all_blocks.append(block)
            global_used.update({plate, block})
            excluded.update(sol)
            puzzle_passable = puzzle_passable - {plate}
            prior_puzzles.append((plate, block))

    # Dead squares for floor visual indicator (permanent walls only; not used
    # for block placement — placement is guaranteed solvable by construction).
    dead_squares = set()
    if all_plates:
        permanent = {pos for pos, wt in walls.items() if wt == WALL_REINFORCED}
        perm_passable = frozenset(
            (c, r) for c in range(MIN_C, MAX_C + 1)
            for r in range(MIN_R, MAX_R + 1)
            if (c, r) not in permanent)
        targets = [(pc, pr) for pc, pr, _ in all_plates]
        dead_squares = _compute_dead_squares(perm_passable, targets)

    # Place other items (treasures, materials, keys, enemies).
    # Plates and blocks are already placed above; global_used carries their
    # positions so _place_items_in_room does not collide with them.
    all_treasures = []
    all_materials = []
    all_keys = []
    all_enemy_starts = []

    item_walls = dict(walls)
    for ft in flame_tile_set:
        item_walls[ft] = WALL_REINFORCED

    for name, node in graph.nodes.items():
        if name not in placed:
            continue
        t, m, k, es = _place_items_in_room(
            node, placed[name], item_walls, rng,
            player_pos=player_start, global_used=global_used)
        all_treasures.extend(t)
        all_materials.extend(m)
        all_keys.extend(k)
        all_enemy_starts.extend(es)

    # Place a treasure on the far side of each flame jet
    item_nos = list(range(1, 10))
    for jet in all_flame_jets:
        far = jet.get('far_tiles', [])
        far_free = [t for t in far if t not in flame_tile_set
                    and t not in walls and t not in global_used]
        if far_free:
            pos = rng.choice(far_free)
            global_used.add(pos)
            all_treasures.append((*pos, rng.choice(item_nos)))

    # Locked doors, gates, and water tiles from edges
    # (orig_walls already computed above for puzzle_passable)
    all_locked_doors = []
    all_gates = []
    all_water_tiles = []

    for edge in graph.edges:
        if edge.node_a not in placed or edge.node_b not in placed:
            continue
        if edge.edge_type not in (EdgeType.LOCKED, EdgeType.GATED, EdgeType.WATER):
            continue
        pa = placed[edge.node_a]
        pb = placed[edge.node_b]
        conn = _find_connection_tile(pa, pb, orig_walls)
        if conn is None:
            continue
        if edge.edge_type == EdgeType.LOCKED:
            all_locked_doors.append((*conn, edge.params['key_colour']))
        elif edge.edge_type == EdgeType.GATED:
            all_gates.append((*conn, edge.params['gate_id']))
        elif edge.edge_type == EdgeType.WATER:
            pass  # water tiles already collected by derive_walls

    # Build room dict
    grid_name = 'main'
    room = {
        'walls': walls,
        'tile_owner': tile_owner,
    }
    if all_enemy_starts:
        room['enemy_starts'] = all_enemy_starts
    if all_treasures:
        room['treasures'] = all_treasures
    if all_materials:
        room['materials'] = all_materials
    if all_keys:
        room['keys'] = all_keys
    if all_locked_doors:
        room['locked_doors'] = all_locked_doors
    if all_blocks:
        room['pushable_blocks'] = all_blocks
    if all_plates:
        room['pressure_plates'] = all_plates
    if all_gates:
        room['gates'] = all_gates
    if water_tiles:
        room['water_tiles'] = water_tiles
    if all_flame_jets:
        room['flame_jets'] = all_flame_jets

    # Validate layout invariant
    errors = validate_layout(graph, placed, walls)
    if errors:
        raise ValueError(f"Layout invariant violated: {errors}")

    # Validate push puzzles are solvable
    push_errors = validate_push_puzzles(room, tile_owner)
    if push_errors:
        raise ValueError(f"Unsolvable push puzzle: {push_errors}")

    # Store dead squares (already computed before block placement)
    if dead_squares:
        room['dead_squares'] = list(dead_squares)

    return {
        'start_room': grid_name,
        'player_start': player_start,
        'rooms': {grid_name: room},
    }


def _build_multi_grid(graph, rng, strategies):
    """Build a level spanning two 30x16 grids connected by border exits.

    Uses the BORDER edge in the graph to determine the partition.
    Each side of the BORDER edge becomes a separate grid.
    """
    from levelgraph import LevelGraph, NodeSize, EdgeType

    # Find the BORDER edge and the two corridors it connects
    border_edge = None
    for edge in graph.edges:
        if edge.edge_type == EdgeType.BORDER:
            border_edge = edge
            break
    if border_edge is None:
        raise ValueError("Multi-grid level has no BORDER edge")

    cor_a = border_edge.node_a
    cor_b = border_edge.node_b

    # Partition: each corridor and its connected rooms form a grid
    def _build_subgraph(corridor):
        sub = LevelGraph(rng=rng)
        sub.add_node(corridor, graph.nodes[corridor].size, is_start=True)
        for name, edge in graph.neighbors(corridor):
            if edge.edge_type == EdgeType.BORDER:
                continue
            n = graph.nodes[name]
            node = sub.add_node(name, n.size)
            node.treasures = list(n.treasures)
            node.materials = list(n.materials)
            node.keys = list(n.keys)
            node.blocks = list(n.blocks)
            node.plates = list(n.plates)
            node.enemies = list(n.enemies)
            node.has_flames = n.has_flames
            sub.add_edge(corridor, name, edge.edge_type, **edge.params)
        return sub

    graph_a = _build_subgraph(cor_a)
    graph_b = _build_subgraph(cor_b)

    dict_a = build_level_dict(graph_a, rng=rng, strategies=strategies,
                               grid_count=1)
    dict_b = build_level_dict(graph_b, rng=rng, strategies=strategies,
                               grid_count=1)

    room_a = dict_a['rooms']['main']
    room_b = dict_b['rooms']['main']

    # Find a connection row: any row where both grids have floor
    # adjacent to the border. Can be corridor↔corridor, corridor↔room,
    # or room↔room.
    rows_a = {r for (c, r) in room_a['tile_owner'] if c == COLS - 2}
    rows_b = {r for (c, r) in room_b['tile_owner'] if c == 1}
    shared = sorted(rows_a & rows_b)

    if not shared:
        raise ValueError("No shared floor row between grids")

    exit_row = shared[len(shared) // 2]

    # Clear any wall at the border-adjacent tile on each side
    room_a['walls'].pop((COLS - 2, exit_row), None)
    room_b['walls'].pop((1, exit_row), None)

    room_a['exits'] = {f'right_{exit_row}': 'grid_b'}
    room_b['exits'] = {f'left_{exit_row}': 'grid_a'}

    # Place barrier (door/gate) at the exit tile on grid A's side
    barrier = border_edge.params.get('barrier', 'open')
    exit_tile = (COLS - 1, exit_row)
    if barrier == 'locked':
        colour = border_edge.params['key_colour']
        doors = room_a.get('locked_doors', [])
        doors.append((*exit_tile, colour))
        room_a['locked_doors'] = doors
    elif barrier == 'gated':
        gate_id = border_edge.params['gate_id']
        gates = room_a.get('gates', [])
        gates.append((*exit_tile, gate_id))
        room_a['gates'] = gates

    return {
        'start_room': 'grid_a',
        'player_start': dict_a['player_start'],
        'rooms': {
            'grid_a': room_a,
            'grid_b': room_b,
        },
    }
