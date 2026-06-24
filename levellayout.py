"""Layout algorithm: arrange a level graph onto 30×16 grids.

Takes a LevelGraph and produces the game-format dict that game.py expects.
The layout places the corridor as a horizontal band, then packs rooms
above and below it. Walls are derived from negative space.
"""
import random
from constants import (COLS, ROWS, WALL_STONE, WALL_REINFORCED, WALL_WOODEN,
                        ACT2_START_LEVEL)
from levelgraph import LevelGraph, NodeSize, EdgeType, SIZE_RANGES


# ── Layout result ─────────────────────────────────────────────────────────────

class PlacedNode:
    """A graph node with a spatial position on the grid."""

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


# ── Layout algorithm ──────────────────────────────────────────────────────────

def layout_graph(graph, rng=None):
    """Arrange graph nodes onto a single 30×16 grid.

    Returns a dict of {node_name: PlacedNode} or raises if packing fails.
    """
    rng = rng or random.Random()

    # Interior bounds
    min_c, max_c = 1, COLS - 2   # 1-28
    min_r, max_r = 1, ROWS - 2   # 1-14
    interior_w = max_c - min_c + 1  # 28
    interior_h = max_r - min_r + 1  # 14

    # Find the corridor node
    corridor_name = None
    for name, node in graph.nodes.items():
        if node.size == NodeSize.CORRIDOR:
            corridor_name = name
            break
    if corridor_name is None:
        raise ValueError("Graph has no CORRIDOR node")

    # Get room nodes (everything except corridor)
    room_names = [n for n in graph.nodes if n != corridor_name]
    neighbors = {name: edge for name, edge in graph.neighbors(corridor_name)}

    # Decide corridor dimensions
    cor_w_range, cor_h_range = SIZE_RANGES[NodeSize.CORRIDOR]
    cor_h = rng.randint(*cor_h_range)  # 2-3
    cor_w = min(interior_w, rng.randint(max(cor_w_range[0], len(room_names) * 4),
                                         cor_w_range[1]))
    cor_w = min(cor_w, interior_w)

    # Centre the corridor vertically, leaving space above and below
    space_above = max(3, (interior_h - cor_h) // 2)
    space_below = interior_h - space_above - cor_h
    if space_below < 3:
        space_above = interior_h - cor_h - 3
        space_below = 3

    cor_col = min_c + (interior_w - cor_w) // 2
    cor_row = min_r + space_above

    placed = {}
    placed[corridor_name] = PlacedNode(corridor_name, cor_col, cor_row,
                                        cor_w, cor_h)

    # Split rooms into above-corridor and below-corridor groups
    rng.shuffle(room_names)
    mid = (len(room_names) + 1) // 2
    above_rooms = room_names[:mid]
    below_rooms = room_names[mid:]

    # Place rooms above the corridor
    _pack_rooms(graph, placed, above_rooms, rng,
                band_col=cor_col, band_row=min_r,
                band_w=cor_w, band_h=space_above,
                corridor_placed=placed[corridor_name])

    # Place rooms below the corridor
    below_band_row = cor_row + cor_h
    _pack_rooms(graph, placed, below_rooms, rng,
                band_col=cor_col, band_row=below_band_row,
                band_w=cor_w, band_h=space_below,
                corridor_placed=placed[corridor_name])

    return placed


def _pack_rooms(graph, placed, room_names, rng,
                band_col, band_row, band_w, band_h,
                corridor_placed):
    """Pack rooms into a horizontal band (above or below the corridor)."""
    if not room_names:
        return

    # Divide the band width among rooms
    n = len(room_names)
    slot_w = band_w // n

    for i, name in enumerate(room_names):
        node = graph.nodes[name]
        w_range, h_range = SIZE_RANGES[node.size]

        # Fit within the slot
        room_w = min(rng.randint(*w_range), slot_w - 1)  # -1 for wall between rooms
        room_w = max(room_w, w_range[0])
        room_h = min(rng.randint(*h_range), band_h)
        room_h = max(room_h, h_range[0])

        # Position: left-aligned within slot
        room_col = band_col + i * slot_w
        room_row = band_row

        # Clamp to interior
        if room_col + room_w > COLS - 1:
            room_w = COLS - 1 - room_col
        if room_row + room_h > ROWS - 1:
            room_h = ROWS - 1 - room_row

        if room_w >= w_range[0] and room_h >= h_range[0]:
            placed[name] = PlacedNode(name, room_col, room_row, room_w, room_h)


# ── Wall derivation ──────────────────────────────────────────────────────────

def derive_walls(graph, placed):
    """Derive wall dict from placed nodes.

    Everything interior that isn't a room's floor is a reinforced wall.
    Edges become doorways, breakable walls, locked doors, or gates.
    """
    # Collect all floor tiles
    floor = set()
    for pn in placed.values():
        floor.update(pn.floor_tiles)

    # Everything else is wall
    walls = {}
    for c in range(1, COLS - 1):
        for r in range(1, ROWS - 1):
            if (c, r) not in floor:
                walls[(c, r)] = WALL_REINFORCED

    # Process edges: find the connection tile between two placed rooms
    for edge in graph.edges:
        if edge.node_a not in placed or edge.node_b not in placed:
            continue
        pa = placed[edge.node_a]
        pb = placed[edge.node_b]
        conn_tile = _find_connection_tile(pa, pb, walls)
        if conn_tile is None:
            continue

        if edge.edge_type == EdgeType.OPEN:
            walls.pop(conn_tile, None)
        elif edge.edge_type == EdgeType.BREAKABLE:
            wt = edge.params.get('wall_type', 'stone')
            walls[conn_tile] = WALL_STONE if wt == 'stone' else WALL_WOODEN
        elif edge.edge_type in (EdgeType.LOCKED, EdgeType.GATED, EdgeType.STAIRS):
            walls.pop(conn_tile, None)

    return walls


def _find_connection_tile(pa, pb, walls):
    """Find a wall tile between two placed nodes where a door can go.

    Looks for wall tiles that are adjacent to both rooms' floor areas.
    Prefers tiles near the centre of the shared boundary.
    """
    candidates = []
    for (c, r) in walls:
        adj_a = any((c + dc, r + dr) in pa.floor_tiles
                     for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        adj_b = any((c + dc, r + dr) in pb.floor_tiles
                     for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if adj_a and adj_b:
            candidates.append((c, r))

    if not candidates:
        return None

    # Prefer centre of shared boundary
    avg_c = sum(c for c, r in candidates) / len(candidates)
    avg_r = sum(r for c, r in candidates) / len(candidates)
    candidates.sort(key=lambda t: abs(t[0] - avg_c) + abs(t[1] - avg_r))
    return candidates[0]


# ── Item placement ────────────────────────────────────────────────────────────

def _place_items_in_room(node, placed_node, walls, rng):
    """Pick floor positions for a node's items. Returns item lists."""
    floor = [t for t in placed_node.floor_tiles if t not in walls]
    if not floor:
        return [], [], [], [], [], []

    rng.shuffle(floor)
    pos_iter = iter(floor)
    used = set()

    def _next_pos():
        for p in pos_iter:
            if p not in used:
                used.add(p)
                return p
        return None

    treasures = []
    for (item_no,) in node.treasures:
        p = _next_pos()
        if p:
            treasures.append((*p, item_no))

    materials = []
    for (mat_type,) in node.materials:
        p = _next_pos()
        if p:
            materials.append((*p, mat_type))

    keys = []
    for (key_colour,) in node.keys:
        p = _next_pos()
        if p:
            keys.append((*p, key_colour))

    blocks = []
    for _ in node.blocks:
        p = _next_pos()
        if p:
            blocks.append(p)

    plates = []
    for (gate_id,) in node.plates:
        p = _next_pos()
        if p:
            plates.append((*p, gate_id))

    enemy_starts = []
    for enemy_info in node.enemies:
        p = _next_pos()
        if p:
            enemy_starts.append(p)

    return treasures, materials, keys, blocks, plates, enemy_starts


# ── Game-format output ────────────────────────────────────────────────────────

def build_level_dict(graph, rng=None):
    """Generate the complete level dict that game.py expects.

    Returns the same format as hand-authored levels in levels.py:
    {
        'start_room': str,
        'player_start': (col, row),
        'rooms': { grid_name: { 'walls': ..., 'treasures': ..., ... } }
    }
    """
    rng = rng or random.Random()

    # Layout
    placed = layout_graph(graph, rng=rng)

    # Derive walls
    walls = derive_walls(graph, placed)

    # Place items
    all_treasures = []
    all_materials = []
    all_keys = []
    all_blocks = []
    all_plates = []
    all_enemy_starts = []
    all_locked_doors = []
    all_gates = []
    patrol_enemies = []

    for name, node in graph.nodes.items():
        if name not in placed:
            continue
        pn = placed[name]
        t, m, k, b, pl, es = _place_items_in_room(node, pn, walls, rng)
        all_treasures.extend(t)
        all_materials.extend(m)
        all_keys.extend(k)
        all_blocks.extend(b)
        all_plates.extend(pl)
        all_enemy_starts.extend(es)

    # Locked doors and gates from edges
    for edge in graph.edges:
        if edge.node_a not in placed or edge.node_b not in placed:
            continue
        pa = placed[edge.node_a]
        pb = placed[edge.node_b]
        conn_tile = _find_connection_tile(pa, pb, walls)
        if conn_tile is None:
            # Connection tile was already removed from walls (doorway)
            # Try to find it in the original wall positions
            temp_walls = {}
            for c in range(1, COLS - 1):
                for r in range(1, ROWS - 1):
                    floor = set()
                    for pn in placed.values():
                        floor.update(pn.floor_tiles)
                    if (c, r) not in floor:
                        temp_walls[(c, r)] = WALL_REINFORCED
            conn_tile = _find_connection_tile(pa, pb, temp_walls)
            if conn_tile is None:
                continue

        if edge.edge_type == EdgeType.LOCKED:
            all_locked_doors.append((*conn_tile, edge.params['key_colour']))
        elif edge.edge_type == EdgeType.GATED:
            all_gates.append((*conn_tile, edge.params['gate_id']))

    # Find player start position
    start_name = None
    for name, node in graph.nodes.items():
        if node.is_start:
            start_name = name
            break
    start_pn = placed[start_name]
    player_start = (start_pn.col + 1, start_pn.row + start_pn.h // 2)

    # Build room dict (single grid for now)
    grid_name = 'main'
    room_data = {'walls': walls}
    if all_enemy_starts:
        room_data['enemy_starts'] = all_enemy_starts
    if all_treasures:
        room_data['treasures'] = all_treasures
    if all_materials:
        room_data['materials'] = all_materials
    if all_keys:
        room_data['keys'] = all_keys
    if all_locked_doors:
        room_data['locked_doors'] = all_locked_doors
    if all_blocks:
        room_data['pushable_blocks'] = all_blocks
    if all_plates:
        room_data['pressure_plates'] = all_plates
    if all_gates:
        room_data['gates'] = all_gates

    return {
        'start_room': grid_name,
        'player_start': player_start,
        'rooms': {grid_name: room_data},
    }
