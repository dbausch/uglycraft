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

    def __init__(self, name, col, row, w, h, floor_tiles=None):
        self.name = name
        self.col = col
        self.row = row
        self.w = w
        self.h = h
        if floor_tiles is not None:
            self.floor_tiles = floor_tiles
        else:
            self.floor_tiles = frozenset(
                (c, r) for c in range(col, col + w) for r in range(row, row + h)
            )


def _l_shape_tiles(col, row, w, h, rng):
    """Return floor_tiles for a random L-shape within bounding box (col,row,w,h)."""
    cut_w = rng.randint(max(1, w // 3), max(1, w // 2))
    cut_h = rng.randint(max(1, h // 3), max(1, h // 2))
    full   = frozenset((c, r) for c in range(col, col + w) for r in range(row, row + h))
    corner = rng.choice(['tl', 'tr', 'bl', 'br'])
    if corner == 'tl':
        cut = {(c, r) for c in range(col, col + cut_w)
                       for r in range(row, row + cut_h)}
    elif corner == 'tr':
        cut = {(c, r) for c in range(col + w - cut_w, col + w)
                       for r in range(row, row + cut_h)}
    elif corner == 'bl':
        cut = {(c, r) for c in range(col, col + cut_w)
                       for r in range(row + h - cut_h, row + h)}
    else:
        cut = {(c, r) for c in range(col + w - cut_w, col + w)
                       for r in range(row + h - cut_h, row + h)}
    return frozenset(full - cut)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _floor_connected(floor_tiles):
    """Return True if all floor tiles form a single 4-connected component."""
    if not floor_tiles:
        return True
    start = next(iter(floor_tiles))
    visited = {start}
    queue = deque([start])
    while queue:
        c, r = queue.popleft()
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (c + dc, r + dr)
            if nb in floor_tiles and nb not in visited:
                visited.add(nb)
                queue.append(nb)
    return len(visited) == len(floor_tiles)


def _try_l_pair(placed, name_i, name_j, col, band_row, band_h, w_i, w_j, band_end, rng):
    """Place two rooms as a horizontal L-pair.

    A (name_i) gets full-width-top + left-bottom (L-shape).
    B (name_j) gets top-right rectangle.
    There is always exactly one shared boundary wall tile between them.

    Returns consumed columns (combined_w + 1 gap) on success, 0 on failure.
    """
    combined_w = w_i + 1 + w_j   # wall column at col+w_i
    if col + combined_w > band_end or band_h < 4:
        return 0

    split_min = band_row + max(1, band_h // 3)
    split_max = band_row + max(1, (2 * band_h) // 3)
    if split_min >= split_max:
        split_row = split_min
    else:
        split_row = rng.randint(split_min, split_max)

    # Need at least 1 row of B (rows band_row..split_row-1)
    # and at least 1 row of A-bottom (rows split_row+1..band_row+band_h-1)
    if split_row <= band_row or split_row >= band_row + band_h - 1:
        return 0

    a_tiles = (
        frozenset((c, r) for c in range(col, col + w_i)
                         for r in range(band_row, split_row + 1))
      | frozenset((c, r) for c in range(col, col + combined_w)
                         for r in range(split_row + 1, band_row + band_h))
    )
    b_tiles = frozenset(
        (c, r) for c in range(col + w_i + 1, col + combined_w)
               for r in range(band_row, split_row)
    )

    if not a_tiles or not b_tiles:
        return 0

    placed[name_i] = PlacedNode(name_i, col, band_row, combined_w, band_h,
                                 floor_tiles=a_tiles)
    placed[name_j] = PlacedNode(name_j, col + w_i + 1, band_row, w_j,
                                 split_row - band_row, floor_tiles=b_tiles)
    return combined_w + 1


def _try_l_pair_vertical(placed, name_i, name_j, row, band_col, band_w, h_i, h_j, row_end, rng):
    """Place two rooms as a vertical L-pair (transpose of the horizontal version).

    A gets top-full-height + right-bottom extension.
    B gets left-bottom rectangle.
    Returns consumed rows + 1 gap on success, 0 on failure.
    """
    combined_h = h_i + 1 + h_j   # wall row at row+h_i
    if row + combined_h > row_end or band_w < 4:
        return 0

    split_min = band_col + max(1, band_w // 3)
    split_max = band_col + max(1, (2 * band_w) // 3)
    if split_min >= split_max:
        split_col = split_min
    else:
        split_col = rng.randint(split_min, split_max)

    if split_col <= band_col or split_col >= band_col + band_w - 1:
        return 0

    a_tiles = (
        frozenset((c, r) for c in range(band_col, band_col + band_w)
                         for r in range(row, row + h_i))
      | frozenset((c, r) for c in range(split_col + 1, band_col + band_w)
                         for r in range(row + h_i + 1, row + combined_h))
    )
    b_tiles = frozenset(
        (c, r) for c in range(band_col, split_col)
               for r in range(row + h_i + 1, row + combined_h)
    )

    if not a_tiles or not b_tiles:
        return 0

    placed[name_i] = PlacedNode(name_i, band_col, row, band_w, combined_h,
                                 floor_tiles=a_tiles)
    placed[name_j] = PlacedNode(name_j, band_col, row + h_i + 1,
                                 split_col - band_col, h_j, floor_tiles=b_tiles)
    return combined_h + 1


# ── Layout strategies ─────────────────────────────────────────────────────────

STRATEGIES = ['horizontal', 'vertical', 'off_centre', 't', 'double_t', 'z', 'l']

# Strategies guaranteed to provide floor tiles at each border group.
_COVERS_LR  = frozenset({'horizontal', 'off_centre', 't', 'double_t', 'z'})
_COVERS_TB  = frozenset({'vertical', 'double_t', 'z'})
_COVERS_ALL = frozenset({'double_t'})
_COVERS_L   = frozenset({'l', 'double_t'})   # l only for 2-exit perpendicular

_STRATEGY_MAX_ZONES = {
    'horizontal':  2,
    'vertical':    2,
    'off_centre':  2,
    't':           3,
    'double_t':    4,
    'z':           4,
    'l':           4,
    'full_border': 1,
}
_SIMPLE_STRATEGIES = frozenset({'horizontal', 'vertical', 'off_centre'})

_EXIT_PAIR_TO_ORIENTATION = {
    frozenset({'top',    'right'}) : 'bl',
    frozenset({'top',    'left'})  : 'br',
    frozenset({'bottom', 'right'}) : 'tl',
    frozenset({'bottom', 'left'})  : 'tr',
}

_ENTRANCE_SIDES = [
    ('left',   lambda t: (0,        t[1]), lambda tiles: min(tiles, key=lambda t: abs(t[1] - (MIN_R + MAX_R) // 2))),
    ('top',    lambda t: (t[0],     0),    lambda tiles: min(tiles, key=lambda t: abs(t[0] - (MIN_C + MAX_C) // 2))),
    ('bottom', lambda t: (t[0], ROWS-1),   lambda tiles: min(tiles, key=lambda t: abs(t[0] - (MIN_C + MAX_C) // 2))),
    ('right',  lambda t: (COLS-1,  t[1]), lambda tiles: min(tiles, key=lambda t: abs(t[1] - (MIN_R + MAX_R) // 2))),
]

_BORDER_EDGE_TILES = {
    'left':   lambda: frozenset((MIN_C, r) for r in range(MIN_R, MAX_R + 1)),
    'top':    lambda: frozenset((c, MIN_R) for c in range(MIN_C, MAX_C + 1)),
    'bottom': lambda: frozenset((c, MAX_R) for c in range(MIN_C, MAX_C + 1)),
    'right':  lambda: frozenset((MAX_C, r) for r in range(MIN_R, MAX_R + 1)),
}


def _pick_entrance(corridor_tiles, occupied_sides=frozenset()):
    """Return (entrance_tile, player_start_tile) for the start corridor.

    entrance_tile:    a border-wall tile (col 0, col COLS-1, row 0, row ROWS-1)
    player_start_tile: the adjacent corridor floor tile

    Tries left, top, bottom, right in order; skips sides in occupied_sides.
    Guaranteed to find a match because every corridor strategy reaches ≥1 border.
    """
    for side, to_entrance, pick_center in _ENTRANCE_SIDES:
        if side in occupied_sides:
            continue
        edge_tiles = _BORDER_EDGE_TILES[side]()
        on_side = edge_tiles & corridor_tiles
        if not on_side:
            continue
        player_tile = pick_center(on_side)
        return to_entrance(player_tile), player_tile
    # Fallback: pick any corridor tile and derive entrance from col 0
    any_tile = min(corridor_tiles, key=lambda t: (t[1], t[0]))
    return (0, any_tile[1]), any_tile


def _pick_strategy(exits, available, rng, n_rooms=0):
    """Choose a layout strategy compatible with the required exit sides.

    exits:     frozenset of sides in {'left', 'right', 'top', 'bottom'}
    available: list of strategy names to choose from
    rng:       random.Random
    n_rooms:   number of regular rooms (used to filter out over-zoned strategies)

    Falls back to 'double_t' if no compatible strategy is in available.
    """
    has_lr = bool(exits & {'left', 'right'})
    has_tb = bool(exits & {'top', 'bottom'})

    if has_lr and has_tb:
        if len(exits) == 2:
            # Exactly one lr side + one tb side → L-shape is compatible
            compatible = _COVERS_L
        else:
            compatible = _COVERS_ALL
    elif has_lr:
        compatible = _COVERS_LR
    elif has_tb:
        compatible = _COVERS_TB
    else:
        # No border exits required (e.g. single isolated grid)
        choices = list(available) if available else ['full_border']
        if n_rooms > 0:
            room_filtered = [s for s in choices
                             if n_rooms >= _STRATEGY_MAX_ZONES.get(s, 2)]
            choices = room_filtered if room_filtered else ['full_border']
        return rng.choice(choices)

    choices = [s for s in (available or STRATEGIES) if s in compatible]
    if not choices:
        return 'full_border'
    if n_rooms > 0:
        room_filtered = [s for s in choices
                         if n_rooms >= _STRATEGY_MAX_ZONES.get(s, 2)]
        choices = room_filtered if room_filtered else ['full_border']
    return rng.choice(choices)


def layout_graph(graph, rng=None, strategies=None, required_exits=None):
    """Arrange graph nodes onto a 30×16 grid using a random strategy.

    required_exits: frozenset of border sides this corridor must reach.
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

    # Build flat edge map: (a, b) → EdgeType (both directions)
    edge_map = {}
    for edge in graph.edges:
        edge_map[(edge.node_a, edge.node_b)] = edge.edge_type
        edge_map[(edge.node_b, edge.node_a)] = edge.edge_type

    node_sizes = {name: node.size for name, node in graph.nodes.items()}

    # Rooms that have no direct corridor edge are nested (closets inside parents)
    all_room_names = [n for n in graph.nodes if n != corridor_name]
    closet_rooms = {}   # {child_name: parent_name}
    regular_rooms = []
    for name in all_room_names:
        has_corridor_edge = any(nb == corridor_name
                                for nb, _ in graph.neighbors(name))
        if not has_corridor_edge:
            # Identify parent: first non-corridor neighbor
            parent = next(
                (nb for nb, _ in graph.neighbors(name) if nb != corridor_name),
                None,
            )
            if parent is not None:
                closet_rooms[name] = parent
            else:
                regular_rooms.append(name)
        else:
            regular_rooms.append(name)

    available = strategies or STRATEGIES
    if len(available) > 1:
        n_rooms = len(regular_rooms)
        room_filtered = [s for s in available
                         if n_rooms >= _STRATEGY_MAX_ZONES.get(s, 2)]
        available = room_filtered if room_filtered else ['full_border']
    strategy = rng.choice(available)

    em = edge_map if edge_map else None
    ns = node_sizes if node_sizes else None

    if strategy == 'vertical':
        placed = _layout_vertical(corridor_name, regular_rooms, rng, em, ns)
    elif strategy == 'off_centre':
        placed = _layout_off_centre(corridor_name, regular_rooms, rng, em, ns)
    elif strategy == 't':
        placed = _layout_corridor(corridor_name, regular_rooms, rng,
                                   stems=[_random_stem(rng)], edge_map=em, node_sizes=ns)
    elif strategy == 'double_t':
        placed = _layout_corridor(corridor_name, regular_rooms, rng,
                                   stems=_double_t_stems(rng), edge_map=em, node_sizes=ns)
    elif strategy == 'z':
        placed = _layout_z(corridor_name, regular_rooms, rng, em, ns,
                           required_exits=required_exits)
    elif strategy == 'l':
        placed = _layout_l(corridor_name, regular_rooms, rng, em, ns,
                           required_exits=required_exits)
    elif strategy == 'full_border':
        placed = _layout_full_border(corridor_name, regular_rooms, rng, em, ns,
                                     required_exits=required_exits)
    else:
        placed = _layout_horizontal(corridor_name, regular_rooms, rng, em, ns)

    if closet_rooms:
        _nest_closets(placed, closet_rooms, graph, rng)

    return placed


def _layout_horizontal(corridor_name, room_names, rng, edge_map=None, node_sizes=None):
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
               band_w=INT_W, band_h=above_h,
               edge_map=edge_map, node_sizes=node_sizes)
    _pack_band(placed, room_names[mid:], rng,
               band_col=MIN_C, band_row=cor_row + cor_h + 1,
               band_w=INT_W, band_h=below_h,
               edge_map=edge_map, node_sizes=node_sizes)

    return placed


def _layout_vertical(corridor_name, room_names, rng, edge_map=None, node_sizes=None):
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
                         band_w=left_w, band_h=INT_H,
                         edge_map=edge_map, node_sizes=node_sizes)
    _pack_band_vertical(placed, room_names[mid:], rng,
                         band_col=cor_col + cor_w + 1, band_row=MIN_R,
                         band_w=right_w, band_h=INT_H,
                         edge_map=edge_map, node_sizes=node_sizes)

    return placed


def _layout_full_border(corridor_name, room_names, rng, edge_map=None, node_sizes=None,
                        required_exits=None):
    """Stitch-fallback layout: corridor = full rectangular frame.

    Every row at col MIN_C/MAX_C and every col at row MIN_R/MAX_R is a corridor
    floor tile, so any pair of stitched grids will always share border rows/cols.
    Rooms are packed into the single interior band (rows MIN_R+2..MAX_R-2).
    """
    frame_tiles = (
        frozenset((c, MIN_R) for c in range(MIN_C, MAX_C + 1)) |
        frozenset((c, MAX_R) for c in range(MIN_C, MAX_C + 1)) |
        frozenset((MIN_C, r) for r in range(MIN_R, MAX_R + 1)) |
        frozenset((MAX_C, r) for r in range(MIN_R, MAX_R + 1))
    )
    placed = {
        corridor_name: PlacedNode(
            corridor_name, MIN_C, MIN_R, INT_W, INT_H,
            floor_tiles=frame_tiles,
        )
    }
    iz_col = MIN_C + 2
    iz_row = MIN_R + 2
    iz_w   = INT_W - 4
    iz_h   = INT_H - 4
    if iz_w >= 3 and iz_h >= 2 and room_names:
        rng.shuffle(room_names)
        _pack_band(placed, room_names, rng,
                   band_col=iz_col, band_row=iz_row,
                   band_w=iz_w, band_h=iz_h,
                   edge_map=edge_map, node_sizes=node_sizes)
    return placed


def _layout_off_centre(corridor_name, room_names, rng, edge_map=None, node_sizes=None):
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
               band_w=INT_W, band_h=above_h,
               edge_map=edge_map, node_sizes=node_sizes)
    _pack_band(placed, room_names[big_count:], rng,
               band_col=MIN_C, band_row=cor_row + cor_h + 1,
               band_w=INT_W, band_h=below_h,
               edge_map=edge_map, node_sizes=node_sizes)

    return placed



def _random_stem(rng):
    """Return one stem spec (side, col_frac, w_range) for a T layout."""
    side = rng.choice(['near', 'far'])
    col_frac = rng.uniform(0.25, 0.75)
    return (side, col_frac, (3, 5))


def _double_t_stems(rng):
    """Return two stem specs for a double-T layout.

    40 % chance stems are aligned (cross-like); 60 % offset.
    """
    frac_near = rng.uniform(0.25, 0.75)
    if rng.random() < 0.4:
        frac_far = frac_near
    else:
        # Keep fracs at least 0.2 apart so stems are visibly offset
        delta = rng.uniform(0.2, 0.5)
        frac_far = frac_near + delta
        if frac_far > 0.75:
            frac_far = frac_near - delta
        frac_far = min(0.75, max(0.25, frac_far))
    return [('near', frac_near, (3, 5)), ('far', frac_far, (3, 5))]


def _layout_corridor(corridor_name, room_names, rng, stems=(),
                     orientation='h', edge_map=None, node_sizes=None):
    """Generalised corridor: full-width band + 0–2 perpendicular stems.

    orientation  'h' horizontal spine, 'v' vertical spine (transposed).
    stems        sequence of (side, col_frac, w_range):
                   side      'near' (top/'h', left/'v') or 'far' (bottom/'h', right/'v')
                   col_frac  float 0–1, stem centre fraction of band width
                   w_range   (min_w, max_w) for stem width
    Stems always extend to the grid border; no tip rooms are pre-allocated.
    """
    rng.shuffle(room_names)

    # --- spine position: centre third (same as _layout_horizontal) ---
    arm_h   = rng.randint(2, 3)
    sp_lo   = MIN_R + INT_H // 3
    sp_hi   = MIN_R + 2 * INT_H // 3 - arm_h
    if sp_lo > sp_hi:
        sp_lo = sp_hi
    r_spine = rng.randint(sp_lo, sp_hi)

    # --- resolve each stem ---
    stem_info = []
    for side, col_frac, w_range in stems:
        stem_w = rng.randint(*w_range)
        c_ctr  = MIN_C + int(col_frac * INT_W)
        c_stem = min(max(c_ctr - stem_w // 2, MIN_C + 1), MAX_C - stem_w)
        stem_info.append({'side': side, 'c': c_stem, 'w': stem_w})

    # --- build corridor floor tiles (spine + stems to border) ---
    cor_tiles = set(
        (c, r)
        for c in range(MIN_C, MAX_C + 1)
        for r in range(r_spine, r_spine + arm_h)
    )
    for s in stem_info:
        rows = (range(r_spine + arm_h, MAX_R + 1) if s['side'] == 'far'
                else range(MIN_R, r_spine))
        for r in rows:
            for c in range(s['c'], s['c'] + s['w']):
                cor_tiles.add((c, r))

    if orientation == 'v':
        cor_tiles = {(r, c) for c, r in cor_tiles}

    placed = {corridor_name: PlacedNode(corridor_name, MIN_C, MIN_R, INT_W, INT_H,
                                         floor_tiles=frozenset(cor_tiles))}

    # --- derive room zones for each side of the spine ---
    near_stems = [s for s in stem_info if s['side'] == 'near']
    far_stems  = [s for s in stem_info if s['side'] == 'far']

    def _side_zones(side_stems, r_start, r_end):
        zh = r_end - r_start + 1
        if zh < 2:
            return []
        if not side_stems:
            return [(MIN_C, r_start, INT_W, zh, _pack_band)]
        s = side_stems[0]
        c, w = s['c'], s['w']
        result = []
        if c - MIN_C - 1 >= 3:
            result.append((MIN_C,     r_start, c - MIN_C - 1, zh, _pack_band))
        if MAX_C - (c + w) >= 3:
            result.append((c + w + 1, r_start, MAX_C - (c + w), zh, _pack_band))
        return result

    zones = (
        _side_zones(near_stems, MIN_R,                r_spine - 2) +
        _side_zones(far_stems,  r_spine + arm_h + 1,  MAX_R)
    )

    if orientation == 'v':
        def _tfn(fn):
            return _pack_band_vertical if fn == _pack_band else _pack_band
        zones = [(r, c, h, w, _tfn(fn)) for c, r, w, h, fn in zones]

    # --- distribute rooms round-robin to valid zones ---
    valid = [(c, r, w, h, fn) for c, r, w, h, fn in zones if w >= 3 and h >= 2]
    if valid:
        per_zone = [[] for _ in valid]
        for i, name in enumerate(room_names):
            per_zone[i % len(valid)].append(name)
        for (zc, zr, zw, zh, fn), names in zip(valid, per_zone):
            if names:
                fn(placed, names, rng, band_col=zc, band_row=zr,
                   band_w=zw, band_h=zh, edge_map=edge_map, node_sizes=node_sizes)

    return placed


def _layout_z(corridor_name, room_names, rng, edge_map=None, node_sizes=None,
              required_exits=None):
    """Single-stroke Z/S corridor with two turns. 4 variants.

    Variants z_h/s_h exit LEFT+RIGHT; z_v/s_v exit TOP+BOTTOM.
    required_exits steers the variant choice when possible.
    """
    if required_exits is not None:
        has_lr = bool(required_exits & {'left', 'right'})
        has_tb = bool(required_exits & {'top', 'bottom'})
    else:
        has_lr = has_tb = False

    if has_lr and not has_tb:
        variant = rng.choice(['z_h', 's_h'])
    elif has_tb and not has_lr:
        variant = rng.choice(['z_v', 's_v'])
    else:
        variant = rng.choice(['z_h', 's_h', 'z_v', 's_v'])

    rng.shuffle(room_names)

    if variant in ('z_h', 's_h'):
        # Single-stroke: first arm exits LEFT (z_h) or RIGHT (s_h).
        arm_h = rng.randint(2, 3)
        arm_w = rng.randint(2, 3)
        r_top = rng.randint(4, MAX_R - arm_h - 5)
        r_bot = rng.randint(r_top + 3, MAX_R - arm_h - 2)
        c_break = rng.randint(5, MAX_C - arm_w - 3)

        if variant == 'z_h':
            # first arm exits LEFT, second arm exits RIGHT
            cor_tiles = (
                frozenset((c, r) for c in range(MIN_C, c_break + arm_w)
                                 for r in range(r_top, r_top + arm_h))
              | frozenset((c, r) for c in range(c_break, c_break + arm_w)
                                 for r in range(r_top, r_bot + arm_h))
              | frozenset((c, r) for c in range(c_break, MAX_C + 1)
                                 for r in range(r_bot, r_bot + arm_h))
            )
            zones = [
                # A: above first arm
                (MIN_C,           MIN_R,            c_break + arm_w - 1,    r_top - 2,
                 _pack_band, None),
                # B: right of connector — extended to MIN_R; all rooms connect via bottom arm
                (c_break + arm_w + 1, MIN_R,        MAX_C - c_break - arm_w, r_bot - MIN_R - 1,
                 _pack_band, None),
                # C: below first arm, left of connector
                (MIN_C,           r_top + arm_h + 1, c_break - 2,            MAX_R - r_top - arm_h,
                 _pack_band, None),
                # D: below second arm
                (c_break,         r_bot + arm_h + 1, MAX_C - c_break + 1,    MAX_R - r_bot - arm_h,
                 _pack_band, None),
            ]
        else:  # s_h: first arm exits RIGHT, second arm exits LEFT
            cor_tiles = (
                frozenset((c, r) for c in range(c_break, MAX_C + 1)
                                 for r in range(r_top, r_top + arm_h))
              | frozenset((c, r) for c in range(c_break, c_break + arm_w)
                                 for r in range(r_top, r_bot + arm_h))
              | frozenset((c, r) for c in range(MIN_C, c_break + arm_w)
                                 for r in range(r_bot, r_bot + arm_h))
            )
            zones = [
                # A: above first arm
                (c_break,         MIN_R,            MAX_C - c_break + 1,    r_top - 2,
                 _pack_band, None),
                # B: left of connector — extended to MIN_R; all rooms connect via bottom arm
                (MIN_C,           MIN_R,            c_break - 2,             r_bot - MIN_R - 1,
                 _pack_band, None),
                # C: below first arm, right of connector
                (c_break + arm_w + 1, r_top + arm_h + 1, MAX_C - c_break - arm_w, MAX_R - r_top - arm_h,
                 _pack_band, None),
                # D: below second arm
                (MIN_C,           r_bot + arm_h + 1, c_break + arm_w - 1,   MAX_R - r_bot - arm_h,
                 _pack_band, None),
            ]

    else:  # z_v / s_v
        arm_w = rng.randint(2, 3)   # arm col-width
        arm_h = rng.randint(2, 3)   # connector row-height
        c_left  = rng.randint(5, MAX_C - arm_w - 8)
        c_right = rng.randint(c_left + 4, MAX_C - arm_w - 3)
        r_break = rng.randint(4, MAX_R - arm_h - 2)

        if variant == 'z_v':
            # first arm exits TOP (left col), second arm exits BOTTOM (right col)
            cor_tiles = (
                frozenset((c, r) for c in range(c_left, c_left + arm_w)
                                 for r in range(MIN_R, r_break + arm_h))
              | frozenset((c, r) for c in range(c_left, c_right + arm_w)
                                 for r in range(r_break, r_break + arm_h))
              | frozenset((c, r) for c in range(c_right, c_right + arm_w)
                                 for r in range(r_break, MAX_R + 1))
            )
            zones = [
                # A: left of first arm (vertical band, full arm height)
                (MIN_C,               MIN_R,               c_left - 2,             r_break + arm_h - 1,
                 _pack_band_vertical, None),
                # B: above connector — extended right to MAX_C; all rooms connect via first arm left wall
                (c_left + arm_w + 1,  MIN_R,               MAX_C - c_left - arm_w, r_break - 2,
                 _pack_band_vertical, None),
                # C: right of second arm — starts at r_break so all rooms reach the arm; no cap
                (c_right + arm_w + 1, r_break,             MAX_C - c_right - arm_w, MAX_R - r_break + 1,
                 _pack_band_vertical, None),
                # D: below connector — extended left to MIN_C; rooms connect via top wall to connector
                (MIN_C,               r_break + arm_h + 1, c_right - 2,            MAX_R - r_break - arm_h,
                 _pack_band_vertical, None),
            ]
        else:  # s_v: first arm exits TOP (right col), second arm exits BOTTOM (left col)
            cor_tiles = (
                frozenset((c, r) for c in range(c_right, c_right + arm_w)
                                 for r in range(MIN_R, r_break + arm_h))
              | frozenset((c, r) for c in range(c_left, c_right + arm_w)
                                 for r in range(r_break, r_break + arm_h))
              | frozenset((c, r) for c in range(c_left, c_left + arm_w)
                                 for r in range(r_break, MAX_R + 1))
            )
            zones = [
                # A: right of first arm (vertical band, full arm height)
                (c_right + arm_w + 1, MIN_R,               MAX_C - c_right - arm_w, r_break + arm_h - 1,
                 _pack_band_vertical, None),
                # B: above connector — extended left to MIN_C; all rooms connect via first arm right wall
                (MIN_C,               MIN_R,               c_right - 2,             r_break - 2,
                 _pack_band_vertical, None),
                # C: left of second arm — starts at r_break so all rooms reach the arm; no cap
                (MIN_C,               r_break,             c_left - 2,              MAX_R - r_break + 1,
                 _pack_band_vertical, None),
                # D: below connector — extended right to MAX_C; rooms connect via top wall to connector
                (c_left + arm_w + 1,  r_break + arm_h + 1, MAX_C - c_left - arm_w, MAX_R - r_break - arm_h,
                 _pack_band_vertical, None),
            ]

    placed = {corridor_name: PlacedNode(corridor_name, MIN_C, MIN_R, INT_W, INT_H,
                                         floor_tiles=cor_tiles)}
    valid = [(zc, zr, zw, zh, fn, mx) for (zc, zr, zw, zh, fn, mx) in zones
             if zw >= 2 and zh >= 2]
    if valid:
        per_zone = [[] for _ in valid]
        rooms_copy = list(room_names)
        # Pass 1: capped zones (max_rooms=1) take one room each, allocated first
        for i, (_, _, _, _, _, mx) in enumerate(valid):
            if mx == 1 and rooms_copy:
                per_zone[i] = [rooms_copy.pop()]
        # Pass 2: remaining rooms round-robin across uncapped zones
        uncapped = [i for i, (_, _, _, _, _, mx) in enumerate(valid) if mx != 1]
        if uncapped:
            for k, name in enumerate(rooms_copy):
                per_zone[uncapped[k % len(uncapped)]].append(name)
        for (zc, zr, zw, zh, fn, _), names in zip(valid, per_zone):
            if names:
                fn(placed, names, rng, band_col=zc, band_row=zr,
                   band_w=zw, band_h=zh, edge_map=edge_map, node_sizes=node_sizes)
    return placed


def _pack_band_vertical(placed, room_names, rng,
                         band_col, band_row, band_w, band_h,
                         edge_map=None, node_sizes=None):
    """Pack rooms into a vertical band (left or right of a vertical corridor)."""
    if not room_names:
        return

    n = len(room_names)
    # Cap to rooms that can actually fit: each needs min h=2 plus 1-tile gap (3 rows/room)
    n = min(n, (band_h + 1) // 3)
    if n == 0:
        return
    walls_between = n - 1
    usable = band_h - walls_between
    base = usable // n  # always ≥ 2 after capping

    heights = [base] * n
    leftover = usable - base * n
    for i in range(max(0, leftover)):
        heights[i % n] += 1
    rng.shuffle(heights)

    band_end = band_row + band_h
    row = band_row
    i = 0
    while i < n:
        name = room_names[i]
        if row + 2 > band_end:
            break

        # Try vertical L-pair for adjacent OPEN-edge rooms
        if (edge_map is not None and i + 1 < n and band_w >= 5 and rng.random() < 0.25):
            name_j = room_names[i + 1]
            et = edge_map.get((name, name_j)) or edge_map.get((name_j, name))
            if et == EdgeType.OPEN:
                h_i = max(2, heights[i])
                h_j = max(2, heights[i + 1])
                if h_i + h_j + 1 >= 8:
                    consumed = _try_l_pair_vertical(
                        placed, name, name_j,
                        row=row, band_col=band_col, band_w=band_w,
                        h_i=h_i, h_j=h_j, row_end=band_end, rng=rng,
                    )
                    if consumed:
                        row += consumed
                        i += 2
                        continue

        h = heights[i]
        w = band_w

        h = min(h, band_end - row, MAX_R + 1 - row)
        if band_col + w > MAX_C + 1:
            w = MAX_C + 1 - band_col

        if w >= 3 and h >= 2:
            placed[name] = PlacedNode(name, band_col, row, w, h)

        row += h + 1
        i += 1


def _pack_band(placed, room_names, rng, band_col, band_row, band_w, band_h,
               edge_map=None, node_sizes=None):
    """Pack rooms into a horizontal band with 1-tile wall between each."""
    if not room_names:
        return

    n = len(room_names)
    # Cap to rooms that can actually fit: each needs min w=2 plus 1-tile gap (3 cols/room)
    n = min(n, (band_w + 1) // 3)
    if n == 0:
        return
    walls_between = n - 1
    usable = band_w - walls_between
    base = usable // n  # always ≥ 2 after capping

    widths = [base] * n
    leftover = usable - base * n
    for i in range(max(0, leftover)):
        widths[i % n] += 1
    rng.shuffle(widths)

    band_end = band_col + band_w
    col = band_col
    i = 0
    while i < n:
        name = room_names[i]
        if col + 2 > band_end:
            break

        # Try horizontal L-pair for adjacent OPEN-edge rooms
        if (edge_map is not None and i + 1 < n and band_h >= 4 and rng.random() < 0.25):
            name_j = room_names[i + 1]
            et = edge_map.get((name, name_j)) or edge_map.get((name_j, name))
            if et == EdgeType.OPEN:
                w_i = max(3, widths[i])
                w_j = max(2, widths[i + 1])
                if w_i + w_j + 1 >= 10:
                    consumed = _try_l_pair(
                        placed, name, name_j,
                        col=col, band_row=band_row, band_h=band_h,
                        w_i=w_i, w_j=w_j, band_end=band_end, rng=rng,
                    )
                    if consumed:
                        col += consumed
                        i += 2
                        continue

        w = widths[i]
        h = band_h

        w = min(w, band_end - col, MAX_C + 1 - col)
        if band_row + h > MAX_R + 1:
            h = MAX_R + 1 - band_row

        if w >= 2 and h >= 2:
            placed[name] = PlacedNode(name, col, band_row, w, h)

        col += widths[i] + 1
        i += 1


def _layout_l(corridor_name, room_names, rng, edge_map=None, node_sizes=None,
              required_exits=None):
    """Corridor is L-shaped; four orientations (bl, br, tl, tr).

    Four zones receive rooms round-robin; Zone T (corner) gets at most 1 room.
    required_exits steers orientation selection when provided.
    """
    orientation = (_EXIT_PAIR_TO_ORIENTATION.get(required_exits)
                   if required_exits is not None else None)
    if orientation is None:
        orientation = rng.choice(['bl', 'br', 'tl', 'tr'])
    arm_h = rng.randint(2, 3)
    arm_w = rng.randint(2, 3)

    # v-arm column: 20-30% or 70-80% from the chosen side
    if orientation in ('bl', 'tl'):
        frac = rng.uniform(0.20, 0.30)
    else:
        frac = rng.uniform(0.70, 0.80)
    cor_col = MIN_C + int(INT_W * frac)
    cor_col = max(MIN_C + arm_w + 2, min(cor_col, MAX_C - arm_w - 3))

    # h-arm row: similar to _layout_horizontal (60-70% or 30-40%)
    if orientation in ('bl', 'br'):
        frac_r = rng.uniform(0.55, 0.70)
    else:
        frac_r = rng.uniform(0.25, 0.40)
    cor_row = MIN_R + int(INT_H * frac_r)
    cor_row = max(MIN_R + arm_h + 2, min(cor_row, MAX_R - arm_h - 2))

    if orientation == 'bl':
        # v-arm exits TOP, h-arm exits RIGHT; empty corner = bottom-left
        v_tiles = frozenset((c, r) for c in range(cor_col, cor_col + arm_w)
                                   for r in range(MIN_R, cor_row + arm_h))
        h_tiles = frozenset((c, r) for c in range(cor_col, MAX_C + 1)
                                   for r in range(cor_row, cor_row + arm_h))
        zones = [
            # A: above h-arm, right of v-arm
            (cor_col + arm_w + 1, MIN_R,
             MAX_C - cor_col - arm_w, cor_row - MIN_R - 1,
             _pack_band),
            # B: left of v-arm (vertical band)
            (MIN_C, MIN_R,
             cor_col - MIN_C - 1, cor_row + arm_h - MIN_R,
             _pack_band_vertical),
            # C: below h-arm, right of v-arm
            (cor_col + arm_w + 1, cor_row + arm_h + 1,
             MAX_C - cor_col - arm_w, MAX_R - cor_row - arm_h,
             _pack_band),
            # T: corner — bottom-left; 1 room spanning full width reaches the
            #    v-arm base cols (cor_col..cor_col+arm_w-1) for a valid door
            (MIN_C, cor_row + arm_h + 1,
             cor_col + arm_w - 1, MAX_R - cor_row - arm_h,
             _pack_band),
        ]
    elif orientation == 'br':
        # v-arm exits TOP, h-arm exits LEFT; empty corner = bottom-right
        v_tiles = frozenset((c, r) for c in range(cor_col, cor_col + arm_w)
                                   for r in range(MIN_R, cor_row + arm_h))
        h_tiles = frozenset((c, r) for c in range(MIN_C, cor_col + arm_w)
                                   for r in range(cor_row, cor_row + arm_h))
        zones = [
            # A: above h-arm, left of v-arm
            (MIN_C, MIN_R,
             cor_col - MIN_C - 1, cor_row - MIN_R - 1,
             _pack_band),
            # B: right of v-arm (vertical band)
            (cor_col + arm_w + 1, MIN_R,
             MAX_C - cor_col - arm_w, cor_row + arm_h - MIN_R,
             _pack_band_vertical),
            # C: below h-arm, left of v-arm
            (MIN_C, cor_row + arm_h + 1,
             cor_col - MIN_C - 1, MAX_R - cor_row - arm_h,
             _pack_band),
            # T: corner — bottom-right
            (cor_col, cor_row + arm_h + 1,
             MAX_C - cor_col + 1, MAX_R - cor_row - arm_h,
             _pack_band),
        ]
    elif orientation == 'tl':
        # v-arm exits BOTTOM, h-arm exits RIGHT; empty corner = top-left
        v_tiles = frozenset((c, r) for c in range(cor_col, cor_col + arm_w)
                                   for r in range(cor_row, MAX_R + 1))
        h_tiles = frozenset((c, r) for c in range(cor_col, MAX_C + 1)
                                   for r in range(cor_row, cor_row + arm_h))
        zones = [
            # A: below h-arm, right of v-arm
            (cor_col + arm_w + 1, cor_row + arm_h + 1,
             MAX_C - cor_col - arm_w, MAX_R - cor_row - arm_h,
             _pack_band),
            # B: left of v-arm, from h-arm down (vertical band)
            (MIN_C, cor_row,
             cor_col - MIN_C - 1, MAX_R - cor_row + 1,
             _pack_band_vertical),
            # C: above h-arm, right of v-arm
            (cor_col + arm_w + 1, MIN_R,
             MAX_C - cor_col - arm_w, cor_row - MIN_R - 1,
             _pack_band),
            # T: corner — top-left; room must reach v-arm base for a valid door
            (MIN_C, MIN_R,
             cor_col + arm_w - 1, cor_row - 2,
             _pack_band),
        ]
    else:  # tr
        # v-arm exits BOTTOM, h-arm exits LEFT; empty corner = top-right
        v_tiles = frozenset((c, r) for c in range(cor_col, cor_col + arm_w)
                                   for r in range(cor_row, MAX_R + 1))
        h_tiles = frozenset((c, r) for c in range(MIN_C, cor_col + arm_w)
                                   for r in range(cor_row, cor_row + arm_h))
        zones = [
            # A: below h-arm, left of v-arm
            (MIN_C, cor_row + arm_h + 1,
             cor_col - MIN_C - 1, MAX_R - cor_row - arm_h,
             _pack_band),
            # B: right of v-arm, from h-arm down (vertical band)
            (cor_col + arm_w + 1, cor_row,
             MAX_C - cor_col - arm_w, MAX_R - cor_row + 1,
             _pack_band_vertical),
            # C: above h-arm, left of v-arm
            (MIN_C, MIN_R,
             cor_col - MIN_C - 1, cor_row - MIN_R - 1,
             _pack_band),
            # T: corner — top-right
            (cor_col, MIN_R,
             MAX_C - cor_col + 1, cor_row - 2,
             _pack_band),
        ]

    cor_tiles = v_tiles | h_tiles
    placed = {corridor_name: PlacedNode(corridor_name, MIN_C, MIN_R,
                                         INT_W, INT_H, floor_tiles=cor_tiles)}

    # Zone T (index 3) gets at most 1 room — a single room spanning the full
    # zone width guarantees it reaches the v-arm base cols for a valid door.
    rooms_copy = list(room_names)
    rng.shuffle(rooms_copy)
    zt = zones[3]
    zone_t_rooms = []
    if rooms_copy and zt[2] >= 3 and zt[3] >= 2:
        zone_t_rooms = [rooms_copy.pop()]

    per_zone = [[], [], []]
    for k, name in enumerate(rooms_copy):
        per_zone[k % 3].append(name)

    for (zc, zr, zw, zh, fn), zone_rooms in zip(zones[:3], per_zone):
        if zone_rooms and zw >= 3 and zh >= 2:
            fn(placed, zone_rooms, rng,
               band_col=zc, band_row=zr, band_w=zw, band_h=zh,
               edge_map=edge_map, node_sizes=node_sizes)

    if zone_t_rooms:
        ztc, ztr, ztw, zth, zt_fn = zt
        zt_fn(placed, zone_t_rooms, rng,
              band_col=ztc, band_row=ztr, band_w=ztw, band_h=zth,
              edge_map=edge_map, node_sizes=node_sizes)

    return placed


def _nest_closets(placed, closet_rooms, graph, rng):
    """Reposition closet rooms into a corner of their parent room.

    The closet shares two outer walls with the parent (it sits at a true
    corner).  The notch is (b_w+1)×(b_h+1): one added vertical wall and
    one added horizontal wall separate the closet from the parent interior.
    """
    for child_name, parent_name in closet_rooms.items():
        if parent_name not in placed:
            continue
        pn_a = placed[parent_name]

        b_w = min(4, max(2, pn_a.w // 5))
        b_h = min(3, max(2, pn_a.h // 3))
        notch_w = b_w + 1   # 1 added vertical wall
        notch_h = b_h + 1   # 1 added horizontal wall

        if pn_a.w < notch_w + 1 or pn_a.h < notch_h + 1:
            _place_closet_adjacent(placed, child_name, pn_a, b_w, b_h)
            continue

        a_floor = pn_a.floor_tiles

        # Four corners: (notch_col, notch_row, closet_col, closet_row)
        # Closet occupies the corner of the notch, sharing the outer walls.
        corners = [
            (pn_a.col,                    pn_a.row,
             pn_a.col,                    pn_a.row),
            (pn_a.col + pn_a.w - notch_w, pn_a.row,
             pn_a.col + pn_a.w - b_w,     pn_a.row),
            (pn_a.col,                    pn_a.row + pn_a.h - notch_h,
             pn_a.col,                    pn_a.row + pn_a.h - b_h),
            (pn_a.col + pn_a.w - notch_w, pn_a.row + pn_a.h - notch_h,
             pn_a.col + pn_a.w - b_w,     pn_a.row + pn_a.h - b_h),
        ]
        rng.shuffle(corners)

        placed_ok = False
        for nc_notch, nr_notch, nc, nr in corners:
            notch = frozenset((c, r)
                              for c in range(nc_notch, nc_notch + notch_w)
                              for r in range(nr_notch, nr_notch + notch_h))
            new_a = a_floor - notch
            if not new_a or not _floor_connected(new_a):
                continue

            b_floor = frozenset((c, r)
                                for c in range(nc, nc + b_w)
                                for r in range(nr, nr + b_h))
            if not b_floor:
                continue

            placed[parent_name] = PlacedNode(parent_name, pn_a.col, pn_a.row,
                                              pn_a.w, pn_a.h, floor_tiles=new_a)
            placed[child_name] = PlacedNode(child_name, nc, nr, b_w, b_h,
                                             floor_tiles=b_floor)
            placed_ok = True
            break

        if not placed_ok:
            _place_closet_adjacent(placed, child_name, pn_a, b_w, b_h)


def _place_closet_adjacent(placed, child_name, pn_a, b_w, b_h):
    """Fallback: place closet as a small rectangle just below parent."""
    c = pn_a.col
    r = pn_a.row + pn_a.h + 1
    r = min(r, MAX_R - b_h + 1)
    c = min(c, MAX_C - b_w + 1)
    placed[child_name] = PlacedNode(child_name, c, r, b_w, b_h)


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

    # Flame-room treasures are placed on far tiles only (see far-tiles pass
    # in build_level_dict); skip them here so nothing lands on the near side.
    treasures = []
    if not node.has_flames:
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


def _generate_flame_jets(placed_node, walls, rng, entry=None):
    """Generate a flame jet that spans wall-to-wall across the room.

    The jet splits the room into two sections. It must cross the room
    (not run parallel to a wall) so there are floor tiles on both sides.
    Returns list of jet dicts with 'tiles', 'source', 'dir', 'on_ms',
    'off_ms', and 'far_tiles' (floor tiles beyond the jet).

    entry: the room's entry tile (col, row).  Jets whose axis coincides with
    the entry row (horizontal) or entry column (vertical) are skipped so the
    entry tile is never on the jet and the BFS seed is always valid.
    """
    pn = placed_node
    if pn.w < 4 and pn.h < 4:
        return []

    # Try horizontal and vertical cross-cuts through the room
    candidates = []

    # Horizontal jet (left→right or right→left) at various rows
    for r in range(pn.row + 1, pn.row + pn.h - 1):
        if entry and r == entry[1]:
            continue
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
        if entry and c == entry[0]:
            continue
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

def build_level_dict(graph, rng=None, strategies=None, grid_count=1,
                     required_exits=None, is_start_grid=True,
                     occupied_sides=frozenset()):
    """Generate the complete level dict that game.py expects.

    Auto-detects multi-grid from BORDER edges in the graph.
    grid_count parameter is kept for API compatibility but ignored when
    BORDER edges are present.
    is_start_grid: when True, stores 'entrance' in the room dict and computes
                   player_start from the entrance tile.
    occupied_sides: sides already used by BORDER exits; entrance avoids these.
    """
    rng = rng or random.Random()

    if any(e.edge_type == EdgeType.BORDER for e in graph.edges):
        return _build_super_grid(graph, rng, strategies)

    placed = layout_graph(graph, rng=rng, strategies=strategies,
                          required_exits=required_exits)
    walls, water_tiles = derive_walls(graph, placed)
    tile_owner = build_tile_owner(placed)

    # Find player start via entrance tile
    start_name = None
    for name, node in graph.nodes.items():
        if node.is_start:
            start_name = name
            break
    pn = placed[start_name]
    entrance_tile, player_start = _pick_entrance(pn.floor_tiles, occupied_sides)

    # Generate flame jets first so we can exclude their tiles from items
    all_flame_jets = []
    flame_tile_set = set()
    for name, node in graph.nodes.items():
        if name not in placed or not node.has_flames:
            continue
        # Find the room's entry tile before generating jets so the jet
        # generator can exclude the conflicting row/column.
        entry_tile = None
        for nb_name, _ in graph.neighbors(name):
            if nb_name not in placed:
                continue
            conn = _find_connection_tile(placed[name], placed[nb_name], walls)
            if conn:
                for dc2, dr2 in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    adj = (conn[0] + dc2, conn[1] + dr2)
                    if adj in placed[name].floor_tiles:
                        entry_tile = adj
                        break
            if entry_tile:
                break

        jets = _generate_flame_jets(placed[name], walls, rng, entry=entry_tile)

        if jets and entry_tile:
            for jet in jets:
                jet_set = set(jet['tiles']) | {jet['source']}
                passable = placed[name].floor_tiles - set(walls.keys()) - jet_set
                near: set = {entry_tile}
                frontier = [entry_tile]
                while frontier:
                    next_f = []
                    for t in frontier:
                        for dc2, dr2 in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                            nb = (t[0] + dc2, t[1] + dr2)
                            if nb in passable and nb not in near:
                                near.add(nb)
                                next_f.append(nb)
                    frontier = next_f
                jet['far_tiles'] = list(passable - near)
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

    # Gate/lock prerequisites that exist in the placed layout
    placed_gate_ids = {
        gate_id
        for name, node in graph.nodes.items()
        if name in placed
        for (gate_id,) in node.plates
    }
    placed_key_colours = {
        colour
        for name, node in graph.nodes.items()
        if name in placed
        for (colour,) in node.keys
    }

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
            colour = edge.params['key_colour']
            if colour in placed_key_colours:
                all_locked_doors.append((*conn, colour))
            # else: prerequisite room was dropped — make this an open passage
        elif edge.edge_type == EdgeType.GATED:
            gate_id = edge.params['gate_id']
            if gate_id in placed_gate_ids:
                all_gates.append((*conn, gate_id))
            # else: prerequisite room was dropped — make this an open passage
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
    if is_start_grid:
        room['entrance'] = entrance_tile

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


def _build_super_grid(graph, rng, strategies):
    """Build a level spanning N 30×16 grids connected by BORDER edges.

    Discovers corridors via BFS from the start corridor, builds each grid
    independently, then stitches them together along their BORDER edges.
    """
    from levelgraph import LevelGraph, NodeSize, EdgeType
    from collections import deque as _deque

    # BFS-discover corridors in visit order (start corridor first)
    start_corridor = next(
        name for name, node in graph.nodes.items()
        if node.is_start and node.size == NodeSize.CORRIDOR)

    corridor_order = []
    visited = {start_corridor}
    queue = _deque([start_corridor])
    while queue:
        cor = queue.popleft()
        corridor_order.append(cor)
        for name, edge in graph.neighbors(cor):
            if edge.edge_type == EdgeType.BORDER and name not in visited:
                visited.add(name)
                queue.append(name)

    def _build_subgraph(corridor, is_start_grid):
        sub = LevelGraph(rng=rng)
        # Each subgraph needs its corridor marked is_start so build_level_dict
        # can find a player_start; the is_start_grid flag is tracked separately.
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

    # Collect required border sides per corridor (columns/rows that must have
    # floor tiles so the stitching step can find a shared position).
    _BORDER_CHECK_COL = {'right': COLS - 2, 'left': 1}
    _BORDER_CHECK_ROW = {'bottom': ROWS - 2, 'top': 1}
    required_sides = {cor: set() for cor in corridor_order}
    for edge in graph.edges:
        if edge.edge_type != EdgeType.BORDER:
            continue
        required_sides[edge.node_a].add(edge.params['exit_side'])
        required_sides[edge.node_b].add(edge.params['entry_side'])

    def _stitch_ok(rooms_by_gname):
        """Return True if all BORDER edges can be stitched (shared rows/cols exist)."""
        for edge in graph.edges:
            if edge.edge_type != EdgeType.BORDER:
                continue
            gname_a = grid_name_map[edge.node_a]
            gname_b = grid_name_map[edge.node_b]
            if gname_a not in rooms_by_gname or gname_b not in rooms_by_gname:
                return False
            room_a = rooms_by_gname[gname_a]
            room_b = rooms_by_gname[gname_b]
            exit_side = edge.params.get('exit_side', 'right')
            entry_side = edge.params.get('entry_side', 'left')
            if exit_side in ('right', 'left'):
                col_a = _BORDER_CHECK_COL[exit_side]
                col_b = _BORDER_CHECK_COL[entry_side]
                rows_a = {r for (c, r) in room_a.get('tile_owner', {}) if c == col_a}
                rows_b = {r for (c, r) in room_b.get('tile_owner', {}) if c == col_b}
                if not (rows_a & rows_b):
                    return False
            else:
                row_a = _BORDER_CHECK_ROW[exit_side]
                row_b = _BORDER_CHECK_ROW[entry_side]
                cols_a = {c for (c, r) in room_a.get('tile_owner', {}) if r == row_a}
                cols_b = {c for (c, r) in room_b.get('tile_owner', {}) if r == row_b}
                if not (cols_a & cols_b):
                    return False
        return True

    # Build each grid independently, choosing a strategy compatible with
    # that grid's required border exits.
    grid_name_map = {cor: (f'grid_{i}' if i > 0 else 'grid_a')
                     for i, cor in enumerate(corridor_order)}
    all_rooms = {}
    all_player_starts = {}
    subgraphs = {}

    for i, corridor in enumerate(corridor_order):
        sub = _build_subgraph(corridor, is_start_grid=(i == 0))
        subgraphs[corridor] = sub
        exits = required_sides[corridor]
        n_rooms = sum(1 for name, node in sub.nodes.items()
                      if node.size != NodeSize.CORRIDOR)
        chosen = [_pick_strategy(frozenset(exits), strategies, rng, n_rooms=n_rooms)]
        d = build_level_dict(sub, rng=rng, strategies=chosen, grid_count=1,
                             required_exits=frozenset(exits),
                             is_start_grid=(i == 0),
                             occupied_sides=exits)
        gname = grid_name_map[corridor]
        all_rooms[gname] = d['rooms']['main']
        all_player_starts[gname] = d['player_start']

    # If any stitch would fail, rebuild every multi-grid subgraph with 'full_border'.
    # 'full_border' places corridor floor tiles on all four grid edges, so any
    # pair of adjacent grids always share floor rows/cols at every border.
    if not _stitch_ok(all_rooms):
        for i, corridor in enumerate(corridor_order):
            exits = required_sides[corridor]
            d = build_level_dict(
                subgraphs[corridor], rng=rng, strategies=['full_border'], grid_count=1,
                is_start_grid=(i == 0),
                occupied_sides=exits)
            gname = grid_name_map[corridor]
            all_rooms[gname] = d['rooms']['main']
            all_player_starts[gname] = d['player_start']

    player_start = all_player_starts[grid_name_map[corridor_order[0]]]

    # Stitch grids along BORDER edges
    _INNER = {
        'right':  (COLS - 2, None),  # (col, row) — None = use shared_pos
        'left':   (1,        None),
        'bottom': (None, ROWS - 2),
        'top':    (None, 1),
    }
    _BORDER_TILE = {
        'right':  lambda pos: (COLS - 1, pos),
        'left':   lambda pos: (0,        pos),
        'bottom': lambda pos: (pos, ROWS - 1),
        'top':    lambda pos: (pos, 0),
    }

    for edge in graph.edges:
        if edge.edge_type != EdgeType.BORDER:
            continue
        gname_a = grid_name_map[edge.node_a]
        gname_b = grid_name_map[edge.node_b]
        room_a  = all_rooms[gname_a]
        room_b  = all_rooms[gname_b]

        exit_side  = edge.params.get('exit_side',  'right')
        entry_side = edge.params.get('entry_side', 'left')

        if exit_side in ('right', 'left'):
            col_a = _INNER[exit_side][0]
            col_b = _INNER[entry_side][0]
            rows_a = {r for (c, r) in room_a['tile_owner'] if c == col_a}
            rows_b = {r for (c, r) in room_b['tile_owner'] if c == col_b}
            shared = sorted(rows_a & rows_b)
            if not shared:
                raise ValueError(
                    f"No shared floor row between {gname_a} ({exit_side}) "
                    f"and {gname_b} ({entry_side})")
            pos = shared[len(shared) // 2]
            room_a['walls'].pop((col_a, pos), None)
            room_b['walls'].pop((col_b, pos), None)
            exit_key_a = f'{exit_side}_{pos}'
            exit_key_b = f'{entry_side}_{pos}'
        else:
            row_a = _INNER[exit_side][1]
            row_b = _INNER[entry_side][1]
            cols_a = {c for (c, r) in room_a['tile_owner'] if r == row_a}
            cols_b = {c for (c, r) in room_b['tile_owner'] if r == row_b}
            shared = sorted(cols_a & cols_b)
            if not shared:
                raise ValueError(
                    f"No shared floor col between {gname_a} ({exit_side}) "
                    f"and {gname_b} ({entry_side})")
            pos = shared[len(shared) // 2]
            room_a['walls'].pop((pos, row_a), None)
            room_b['walls'].pop((pos, row_b), None)
            exit_key_a = f'{exit_side}_{pos}'
            exit_key_b = f'{entry_side}_{pos}'

        exits_a = room_a.get('exits', {})
        exits_b = room_b.get('exits', {})
        exits_a[exit_key_a] = gname_b
        exits_b[exit_key_b] = gname_a
        room_a['exits'] = exits_a
        room_b['exits'] = exits_b

        barrier_tile = _BORDER_TILE[exit_side](pos)
        barrier = edge.params.get('barrier', 'open')
        if barrier == 'locked':
            colour = edge.params['key_colour']
            doors = room_a.get('locked_doors', [])
            doors.append((*barrier_tile, colour))
            room_a['locked_doors'] = doors
        elif barrier == 'gated':
            gate_id = edge.params['gate_id']
            gates = room_a.get('gates', [])
            gates.append((*barrier_tile, gate_id))
            room_a['gates'] = gates

    start_grid = grid_name_map[corridor_order[0]]
    return {
        'start_room': start_grid,
        'player_start': player_start,
        'rooms': all_rooms,
    }
