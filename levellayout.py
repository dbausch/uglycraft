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


# ── Layout ────────────────────────────────────────────────────────────────────

def layout_graph(graph, rng=None):
    """Arrange graph nodes onto a 30×16 grid.

    Strategy:
    - Corridor runs full interior width, 2-3 tiles tall, vertically centred.
    - 1 tile of wall separates the corridor from the room bands above/below.
    - Rooms fill the bands, each separated by 1 tile of wall.
    - Every room is therefore fully enclosed by wall (or border).

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

    # Corridor: full width, 2-3 tiles tall
    cor_h = rng.randint(2, 3)

    # Reserve 1 row of wall above and below the corridor.
    # Remaining space splits into room bands.
    #   above_band_h + 1 (wall) + cor_h + 1 (wall) + below_band_h = INT_H
    remaining = INT_H - cor_h - 2  # subtract corridor and 2 wall rows
    above_h = remaining // 2
    below_h = remaining - above_h
    if above_h < 3:
        above_h = 3
        below_h = remaining - above_h
    if below_h < 3:
        below_h = 3
        above_h = remaining - below_h

    # Positions (all 1-indexed interior coords)
    above_row = MIN_R                      # rooms above start here
    wall_above_row = MIN_R + above_h       # wall row between above rooms and corridor
    cor_row = wall_above_row + 1           # corridor starts here
    wall_below_row = cor_row + cor_h       # wall row between corridor and below rooms
    below_row = wall_below_row + 1         # rooms below start here

    placed = {}
    placed[corridor_name] = PlacedNode(
        corridor_name, MIN_C, cor_row, INT_W, cor_h)

    # Split rooms above/below
    rng.shuffle(room_names)
    mid = (len(room_names) + 1) // 2
    above = room_names[:mid]
    below = room_names[mid:]

    _pack_band(placed, above, rng,
               band_col=MIN_C, band_row=above_row,
               band_w=INT_W, band_h=above_h)

    _pack_band(placed, below, rng,
               band_col=MIN_C, band_row=below_row,
               band_w=INT_W, band_h=below_h)

    return placed


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
                continue
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

    # Prefer centre of shared boundary
    avg_c = sum(c for c, r in candidates) / len(candidates)
    avg_r = sum(r for c, r in candidates) / len(candidates)
    candidates.sort(key=lambda t: abs(t[0] - avg_c) + abs(t[1] - avg_r))
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


def _can_push_block_to(block_positions, target, passable):
    """Check if any block can be pushed to the target.

    Tries each block independently with a proper Sokoban BFS.
    The block being tested is temporarily added back to passable
    (since it will move), but other blocks remain as obstacles.
    """
    for block_start in block_positions:
        # This block's start position needs to be passable (it will move)
        p = passable | {block_start}
        if _sokoban_bfs(block_start, target, p):
            return True
    return False


def _player_reachable(player_start, block_pos, passable):
    """BFS for player movement, treating block_pos as impassable."""
    visited = {player_start}
    frontier = [player_start]
    while frontier:
        c, r = frontier.pop()
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nc, nr = c + dc, r + dr
            if ((nc, nr) in passable and (nc, nr) not in visited
                    and (nc, nr) != block_pos):
                visited.add((nc, nr))
                frontier.append((nc, nr))
    return visited


def _normalize_player(player_pos, block_pos, passable):
    """Reduce player position to a canonical representative of its
    connected component (with block as obstacle). This collapses
    equivalent states where the player is in the same region."""
    reach = _player_reachable(player_pos, block_pos, passable)
    return min(reach)


def _sokoban_bfs(block_start, target, passable):
    """Proper Sokoban solver for a single block.

    State: (block_pos, player_zone) where player_zone is the canonical
    tile of the player's connected component (with the block as wall).

    Transitions: the player walks to a push position (adjacent to block,
    opposite side of push direction), then pushes. After pushing, the
    player stands at the block's old position.
    """
    if block_start == target:
        return True

    # Find ANY passable starting position for the player (not the block)
    player_candidates = [p for p in passable if p != block_start]
    if not player_candidates:
        return False

    # The player could start anywhere in the room that isn't the block.
    # Try each connected component.
    tried_starts = set()
    for ps in player_candidates:
        norm = _normalize_player(ps, block_start, passable)
        if norm in tried_starts:
            continue
        tried_starts.add(norm)

        # BFS: state = (block_pos, player_zone_canonical)
        start_state = (block_start, norm)
        visited = {start_state}
        queue = deque([start_state])

        while queue:
            (bx, by), p_zone = queue.popleft()

            # Player can reach any tile in their zone
            p_reach = _player_reachable(p_zone, (bx, by), passable)

            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                push_from = (bx - dc, by - dr)
                push_to = (bx + dc, by + dr)

                if push_from not in p_reach:
                    continue
                if push_to not in passable:
                    continue

                if push_to == target:
                    return True

                # After push: block at push_to, player at (bx, by)
                new_p_zone = _normalize_player(
                    (bx, by), push_to, passable)
                new_state = (push_to, new_p_zone)

                if new_state not in visited:
                    visited.add(new_state)
                    queue.append(new_state)

    return False


# ── Item placement ────────────────────────────────────────────────────────────

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


def _place_items_in_room(node, placed_node, walls, rng, player_pos=None):
    """Pick floor positions for a node's items.

    Enemies are placed at least MIN_ENEMY_DIST BFS tiles from player_pos
    (if player_pos is in this room).
    """
    floor = sorted(t for t in placed_node.floor_tiles if t not in walls)
    rng.shuffle(floor)
    used = set()

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

    blocks = []
    for _ in node.blocks:
        p = _next()
        if p:
            blocks.append(p)

    plates = []
    for (gate_id,) in node.plates:
        p = _next()
        if p:
            plates.append((*p, gate_id))

    enemy_starts = []
    for _ in node.enemies:
        p = _next(min_dist_from_player=MIN_ENEMY_DIST)
        if p:
            enemy_starts.append(p)

    return treasures, materials, keys, blocks, plates, enemy_starts


def _generate_flame_jets(placed_node, walls, rng):
    """Generate flame jet data for a room. A flame jet is a horizontal or
    vertical line of tiles that cycles on/off.

    Returns list of {'tiles': [(c,r),...], 'on_ms': int, 'off_ms': int}.
    """
    floor = sorted(t for t in placed_node.floor_tiles if t not in walls)
    if len(floor) < 6:
        return []

    # Pick a row or column through the room for the flame line
    pn = placed_node
    mid_r = pn.row + pn.h // 2
    mid_c = pn.col + pn.w // 2

    if rng.random() < 0.5 and pn.w >= 4:
        # Horizontal flame line at mid_r
        tiles = [(c, mid_r) for c in range(pn.col + 1, pn.col + pn.w - 1)
                 if (c, mid_r) not in walls]
    elif pn.h >= 4:
        # Vertical flame line at mid_c
        tiles = [(mid_c, r) for r in range(pn.row + 1, pn.row + pn.h - 1)
                 if (mid_c, r) not in walls]
    else:
        return []

    if len(tiles) < 2:
        return []

    return [{'tiles': tiles, 'on_ms': 2000, 'off_ms': 2000}]


# ── Game-format output ────────────────────────────────────────────────────────

def build_level_dict(graph, rng=None):
    """Generate the complete level dict that game.py expects.

    Includes a 'tile_owner' map in the room data: {(col, row): node_name}
    for every floor tile, used by the game to confine enemies to their room.
    """
    rng = rng or random.Random()

    placed = layout_graph(graph, rng=rng)
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

    # Place items and flame jets per room
    all_treasures = []
    all_materials = []
    all_keys = []
    all_blocks = []
    all_plates = []
    all_enemy_starts = []
    all_flame_jets = []

    for name, node in graph.nodes.items():
        if name not in placed:
            continue
        t, m, k, b, pl, es = _place_items_in_room(
            node, placed[name], walls, rng, player_pos=player_start)
        all_treasures.extend(t)
        all_materials.extend(m)
        all_keys.extend(k)
        all_blocks.extend(b)
        all_plates.extend(pl)
        all_enemy_starts.extend(es)
        if node.has_flames:
            jets = _generate_flame_jets(placed[name], walls, rng)
            all_flame_jets.extend(jets)

    # Locked doors, gates, and water tiles from edges
    all_locked_doors = []
    all_gates = []
    all_water_tiles = []
    orig_walls = {}
    floor = set()
    for pnode in placed.values():
        floor.update(pnode.floor_tiles)
    for c in range(MIN_C, MAX_C + 1):
        for r in range(MIN_R, MAX_R + 1):
            if (c, r) not in floor:
                orig_walls[(c, r)] = WALL_REINFORCED

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

    return {
        'start_room': grid_name,
        'player_start': player_start,
        'rooms': {grid_name: room},
    }
