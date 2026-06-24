"""Layout algorithm: arrange a level graph onto 30×16 grids.

Takes a LevelGraph and produces the game-format dict that game.py expects.
The layout places the corridor as a horizontal band, then packs rooms
above and below it with tight packing — rooms fill to the grid edges.
Walls are derived from negative space.
"""
import random
from constants import (COLS, ROWS, WALL_STONE, WALL_REINFORCED, WALL_WOODEN)
from levelgraph import LevelGraph, NodeSize, EdgeType, SIZE_RANGES


# Interior bounds (playable area inside border walls)
MIN_C, MAX_C = 1, COLS - 2   # 1-28
MIN_R, MAX_R = 1, ROWS - 2   # 1-14
INT_W = MAX_C - MIN_C + 1    # 28
INT_H = MAX_R - MIN_R + 1    # 14


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


def layout_graph(graph, rng=None):
    """Arrange graph nodes onto a single 30×16 grid with tight packing.

    Layout strategy:
    - Corridor runs the full interior width, centred vertically.
    - Rooms above the corridor fill from the top edge down.
    - Rooms below the corridor fill from the bottom edge up.
    - Each band of rooms is divided into equal-width slots; rooms fill
      their slot's full height (band height) and most of its width.
    - One tile of wall separates adjacent rooms (slot boundary).

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

    # Corridor: full width, 2-3 tiles tall, vertically centred
    cor_h = rng.randint(2, 3)
    space_above = (INT_H - cor_h) // 2
    space_below = INT_H - space_above - cor_h
    # Ensure at least 3 rows above and below for rooms
    if space_above < 3:
        space_above = 3
        space_below = INT_H - space_above - cor_h
    if space_below < 3:
        space_below = 3
        space_above = INT_H - space_below - cor_h

    cor_row = MIN_R + space_above
    placed = {}
    placed[corridor_name] = PlacedNode(
        corridor_name, MIN_C, cor_row, INT_W, cor_h)

    # Split rooms above/below
    rng.shuffle(room_names)
    mid = (len(room_names) + 1) // 2
    above = room_names[:mid]
    below = room_names[mid:]

    # Pack above: rows MIN_R to cor_row-1 (exclusive), full width
    _pack_band(graph, placed, above, rng,
               band_col=MIN_C, band_row=MIN_R,
               band_w=INT_W, band_h=space_above)

    # Pack below: rows cor_row+cor_h to MAX_R (inclusive), full width
    below_row = cor_row + cor_h
    _pack_band(graph, placed, below, rng,
               band_col=MIN_C, band_row=below_row,
               band_w=INT_W, band_h=space_below)

    return placed


def _pack_band(graph, placed, room_names, rng,
               band_col, band_row, band_w, band_h):
    """Pack rooms into a horizontal band, filling it tightly."""
    if not room_names:
        return

    n = len(room_names)
    # Divide band width into n slots, each separated by 1-tile wall
    # Total walls between rooms: n-1. Remaining space split among rooms.
    total_wall = n - 1
    usable_w = band_w - total_wall
    if usable_w < n * 3:
        # Not enough space; use minimum widths
        slot_ws = [3] * n
    else:
        # Distribute roughly equally, randomize slightly
        base_w = usable_w // n
        remainder = usable_w - base_w * n
        slot_ws = [base_w] * n
        for i in range(remainder):
            slot_ws[i] += 1
        # Shuffle the wider slots
        rng.shuffle(slot_ws)

    col = band_col
    for i, name in enumerate(room_names):
        room_w = slot_ws[i]
        room_h = band_h

        # Clamp to interior
        if col + room_w > MAX_C + 1:
            room_w = MAX_C + 1 - col
        if band_row + room_h > MAX_R + 1:
            room_h = MAX_R + 1 - band_row

        if room_w >= 3 and room_h >= 2:
            placed[name] = PlacedNode(name, col, band_row, room_w, room_h)

        col += room_w + 1  # +1 for wall between rooms


def derive_walls(graph, placed):
    """Derive wall dict from placed nodes.

    Everything interior that isn't a room's floor is a reinforced wall.
    Edges become doorways, breakable walls, locked doors, or gates.
    """
    floor = set()
    for pn in placed.values():
        floor.update(pn.floor_tiles)

    walls = {}
    for c in range(MIN_C, MAX_C + 1):
        for r in range(MIN_R, MAX_R + 1):
            if (c, r) not in floor:
                walls[(c, r)] = WALL_REINFORCED

    # Process edges
    for edge in graph.edges:
        if edge.node_a not in placed or edge.node_b not in placed:
            continue
        pa = placed[edge.node_a]
        pb = placed[edge.node_b]
        conn = _find_connection_tile(pa, pb, walls)
        if conn is None:
            continue

        if edge.edge_type == EdgeType.OPEN:
            walls.pop(conn, None)
        elif edge.edge_type == EdgeType.BREAKABLE:
            wt = edge.params.get('wall_type', 'stone')
            walls[conn] = WALL_STONE if wt == 'stone' else WALL_WOODEN
        elif edge.edge_type in (EdgeType.LOCKED, EdgeType.GATED, EdgeType.STAIRS):
            walls.pop(conn, None)

    return walls


def _find_connection_tile(pa, pb, walls):
    """Find a wall tile between two placed nodes suitable for a doorway.

    Returns (col, row) of the best candidate, or None.
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


def _place_items_in_room(node, placed_node, walls, rng):
    """Pick floor positions for a node's items."""
    floor = sorted(t for t in placed_node.floor_tiles if t not in walls)
    rng.shuffle(floor)
    used = set()

    def _next():
        for p in floor:
            if p not in used:
                used.add(p)
                return p
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
        p = _next()
        if p:
            enemy_starts.append(p)

    return treasures, materials, keys, blocks, plates, enemy_starts


def build_level_dict(graph, rng=None):
    """Generate the complete level dict that game.py expects."""
    rng = rng or random.Random()

    placed = layout_graph(graph, rng=rng)
    walls = derive_walls(graph, placed)

    all_treasures = []
    all_materials = []
    all_keys = []
    all_blocks = []
    all_plates = []
    all_enemy_starts = []
    all_locked_doors = []
    all_gates = []

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

    # Locked doors and gates from edges — find connection tiles
    # (need to use the original wall positions before doorways were cut)
    orig_walls = {}
    floor = set()
    for pn in placed.values():
        floor.update(pn.floor_tiles)
    for c in range(MIN_C, MAX_C + 1):
        for r in range(MIN_R, MAX_R + 1):
            if (c, r) not in floor:
                orig_walls[(c, r)] = WALL_REINFORCED

    for edge in graph.edges:
        if edge.node_a not in placed or edge.node_b not in placed:
            continue
        if edge.edge_type not in (EdgeType.LOCKED, EdgeType.GATED):
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

    # Player start: in the corridor, near the left end
    start_name = None
    for name, node in graph.nodes.items():
        if node.is_start:
            start_name = name
            break
    pn = placed[start_name]
    player_start = (pn.col + 1, pn.row + pn.h // 2)

    # Build room dict
    grid_name = 'main'
    room = {'walls': walls}
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

    return {
        'start_room': grid_name,
        'player_start': player_start,
        'rooms': {grid_name: room},
    }
