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
from levelgraph import (LevelGraph, NodeSize, EdgeType, SIZE_RANGES,
                        COVERS_LR as _COVERS_LR, COVERS_TB as _COVERS_TB,
                        COVERS_ALL as _COVERS_ALL, COVERS_L as _COVERS_L)
from cells import build_room_cells

# Interior bounds
MIN_C, MAX_C = 1, COLS - 2   # 1-28
MIN_R, MAX_R = 1, ROWS - 2   # 1-14
INT_W = MAX_C - MIN_C + 1    # 28
INT_H = MAX_R - MIN_R + 1    # 14

MIN_ENEMY_DIST = 10


class LayoutError(Exception):
    """Raised when a layout strategy cannot place all assigned rooms."""


class CorridorAnchorError(LayoutError):
    """Raised when a strategy cannot place its corridor segment at the band
    required to continue a neighbouring grid's corridor across a BORDER edge."""


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

# Strategy side-coverage tables live in levelgraph since spec 0060 (the
# spanning tree consults them too); imported above under their old names.

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


def _pick_entrance(corridor_tiles, occupied_sides=frozenset(),
                   entrance_side=None):
    """Return (entrance_tile, player_start_tile) for a corridor.

    entrance_tile:    a border-wall tile (col 0, col COLS-1, row 0, row ROWS-1)
    player_start_tile: the adjacent corridor floor tile

    entrance_side set (multi-grid start grid, spec 0053): the side reserved by
    grid zero — the entrance is placed there deterministically, on the border
    tile outside the centre-most on-side corridor tile.  The corridor is
    guaranteed to reach that side (it is in required_exits → R-S1); if it does
    not, LayoutError triggers a fresh-seed retry.

    entrance_side None: scanning mode — first side in (left, top, bottom,
    right) order that the corridor reaches and occupied_sides does not name.
    Single-grid levels always resolve here (nothing is occupied).  Non-start
    grids use this mode solely to derive the corridor enemy-distance reference
    tile; only in that role can every reached side be occupied, so the
    reference fallback below returns an arbitrary corridor tile whose
    entrance value is never surfaced.
    """
    if entrance_side is not None:
        entry = next((e for e in _ENTRANCE_SIDES if e[0] == entrance_side),
                     None)
        if entry is None:
            raise LayoutError(f"unknown entrance side {entrance_side!r}")
        _, to_entrance, pick_center = entry
        on_side = _BORDER_EDGE_TILES[entrance_side]() & corridor_tiles
        if not on_side:
            raise LayoutError(
                f"corridor does not reach entrance side {entrance_side!r}")
        player_tile = pick_center(on_side)
        return to_entrance(player_tile), player_tile

    for side, to_entrance, pick_center in _ENTRANCE_SIDES:
        if side in occupied_sides:
            continue
        edge_tiles = _BORDER_EDGE_TILES[side]()
        on_side = edge_tiles & corridor_tiles
        if not on_side:
            continue
        player_tile = pick_center(on_side)
        return to_entrance(player_tile), player_tile
    # Reference fallback (non-start grids only, see docstring): any corridor
    # tile; the derived entrance is never used as a level entrance.
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


def layout_graph(graph, rng=None, strategies=None, required_exits=None,
                 corridor_anchor=None):
    """Arrange graph nodes onto a 30×16 grid using a random strategy.

    required_exits: frozenset of border sides this corridor must reach.
    corridor_anchor: (side, lo, w) — continue a neighbouring grid's corridor
                     band across a BORDER edge (see _layout_corridor).
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
        placed = _layout_vertical(corridor_name, regular_rooms, rng, em, ns,
                                  corridor_anchor=corridor_anchor)
    elif strategy == 'off_centre':
        placed = _layout_off_centre(corridor_name, regular_rooms, rng, em, ns,
                                    corridor_anchor=corridor_anchor)
    elif strategy == 't':
        # A top/bottom anchor needs the single stem on that side.
        if corridor_anchor and corridor_anchor[0] in ('top', 'bottom'):
            want = 'near' if corridor_anchor[0] == 'top' else 'far'
            stems = [(want, rng.uniform(0.25, 0.75), (2, 5))]
        else:
            stems = [_random_stem(rng)]
        placed = _layout_corridor(corridor_name, regular_rooms, rng,
                                   stems=stems, edge_map=em, node_sizes=ns,
                                   corridor_anchor=corridor_anchor)
    elif strategy == 'double_t':
        placed = _layout_corridor(corridor_name, regular_rooms, rng,
                                   stems=_double_t_stems(rng), edge_map=em, node_sizes=ns,
                                   corridor_anchor=corridor_anchor)
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
        placed = _layout_horizontal(corridor_name, regular_rooms, rng, em, ns,
                                    corridor_anchor=corridor_anchor)

    if closet_rooms:
        _carve_closets(placed, closet_rooms, graph, rng, corridor_name)

    return placed


def _layout_horizontal(corridor_name, room_names, rng, edge_map=None, node_sizes=None,
                       corridor_anchor=None):
    """Corridor runs left-right, rooms above and below."""
    if corridor_anchor and corridor_anchor[0] in ('left', 'right'):
        # Continue the neighbour's corridor: spine rows fixed to the band.
        _, lo, w = corridor_anchor
        cor_h = w
        cor_row = lo
        if cor_row < MIN_R or cor_row + cor_h - 1 > MAX_R:
            raise CorridorAnchorError(f"horizontal cannot place spine at {lo}+{w}")
        above_h = max(0, cor_row - MIN_R - 1)
        below_h = max(0, MAX_R - cor_row - cor_h)
    else:
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


def _layout_vertical(corridor_name, room_names, rng, edge_map=None, node_sizes=None,
                     corridor_anchor=None):
    """Corridor runs top-bottom, rooms left and right."""
    if corridor_anchor and corridor_anchor[0] in ('top', 'bottom'):
        # Continue the neighbour's corridor: spine cols fixed to the band.
        _, lo, w = corridor_anchor
        cor_w = w
        cor_col = lo
        if cor_col < MIN_C or cor_col + cor_w - 1 > MAX_C:
            raise CorridorAnchorError(f"vertical cannot place spine at {lo}+{w}")
        left_w = max(0, cor_col - MIN_C - 1)
        right_w = max(0, MAX_C - cor_col - cor_w)
    else:
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


def _layout_off_centre(corridor_name, room_names, rng, edge_map=None, node_sizes=None,
                       corridor_anchor=None):
    """Corridor shifted up or down, asymmetric room bands."""
    if corridor_anchor and corridor_anchor[0] in ('left', 'right'):
        _, lo, w = corridor_anchor
        cor_h = w
        cor_row = lo
        if cor_row < MIN_R or cor_row + cor_h - 1 > MAX_R:
            raise CorridorAnchorError(f"off_centre cannot place spine at {lo}+{w}")
        above_h = max(0, cor_row - MIN_R - 1)
        below_h = max(0, MAX_R - cor_row - cor_h)
    else:
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
    return (side, col_frac, (2, 5))


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
    return [('near', frac_near, (2, 5)), ('far', frac_far, (2, 5))]


def _next_room_tiles(zw, zh, fn, k):
    """Tile count the (k+1)-th room would get in this zone (0 if zone is full).

    k  — rooms already assigned to the zone.
    fn — _pack_band (horizontal) or _pack_band_vertical.
    With k+1 rooms there are k inter-room gaps, so usable = dim - k.
    """
    if fn is _pack_band:
        base = (zw - k) // (k + 1)
        return base * zh if base >= 2 else 0
    else:
        base = (zh - k) // (k + 1)
        return zw * base if base >= 2 else 0


def _layout_corridor(corridor_name, room_names, rng, stems=(),
                     orientation='h', edge_map=None, node_sizes=None,
                     corridor_anchor=None):
    """Generalised corridor: full-width band + 0–2 perpendicular stems.

    orientation  'h' horizontal spine, 'v' vertical spine (transposed).
    stems        sequence of (side, col_frac, w_range):
                   side      'near' (top/'h', left/'v') or 'far' (bottom/'h', right/'v')
                   col_frac  float 0–1, stem centre fraction of band width
                   w_range   (min_w, max_w) for stem width
    Stems always extend to the grid border; no tip rooms are pre-allocated.
    corridor_anchor  (side, lo, w): continue a neighbour's corridor band.  A
                   left/right anchor fixes the spine rows; a top/bottom anchor
                   fixes the matching stem's cols.  Only orientation 'h' (t /
                   double_t) is anchored.
    """
    rng.shuffle(room_names)

    anchor_side = corridor_anchor[0] if corridor_anchor else None
    if anchor_side is not None and orientation != 'h':
        raise CorridorAnchorError("only horizontal corridors are anchored")

    # --- spine position: centre third (same as _layout_horizontal) ---
    if anchor_side in ('left', 'right'):
        _, lo, w = corridor_anchor
        arm_h = w
        if lo < MIN_R or lo + arm_h - 1 > MAX_R:
            raise CorridorAnchorError(f"corridor cannot place spine at {lo}+{w}")
        r_spine = lo
    else:
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

    # A top/bottom anchor fixes the matching stem's cols + width.
    if anchor_side in ('top', 'bottom'):
        _, lo, w = corridor_anchor
        want = 'near' if anchor_side == 'top' else 'far'
        if lo < MIN_C or lo + w - 1 > MAX_C:
            raise CorridorAnchorError(f"corridor cannot place stem at {lo}+{w}")
        matching = [s for s in stem_info if s['side'] == want]
        if not matching:
            raise CorridorAnchorError(f"no {want} stem to continue {anchor_side} band")
        matching[0]['c'] = lo
        matching[0]['w'] = w

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

    # --- distribute rooms greedily: each room goes to the zone that gives it
    #     the most tiles.  Tie-break: larger zone area, then fewer assigned,
    #     then a per-zone random shuffle index. ---
    valid = [(c, r, w, h, fn) for c, r, w, h, fn in zones if w >= 3 and h >= 2]
    if valid:
        zone_rand = list(range(len(valid)))
        rng.shuffle(zone_rand)
        n_assigned = [0] * len(valid)
        per_zone   = [[] for _ in valid]

        for name in room_names:
            empty      = [i for i in range(len(valid)) if n_assigned[i] == 0]
            candidates = empty if empty else range(len(valid))
            best_i   = -1
            best_key = (-1, -1, 0, -1)
            for i in candidates:
                zc, zr, zw, zh, fn = valid[i]
                t = _next_room_tiles(zw, zh, fn, n_assigned[i])
                if t <= 0:
                    continue
                key = (t, zw * zh, -n_assigned[i], zone_rand[i])
                if key > best_key:
                    best_key = key
                    best_i   = i
            if best_i < 0:
                raise LayoutError(
                    f"Cannot place room {name!r}: all zone capacity exhausted"
                )
            per_zone[best_i].append(name)
            n_assigned[best_i] += 1

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


def _rect_tiles(col, row, w, h):
    return frozenset((c, r) for c in range(col, col + w)
                            for r in range(row, row + h))


def _corridor_facing_side(pn, corridor_floor):
    """Side of room pn whose edge faces the corridor: 'top'/'bottom'/'left'/
    'right'.  The corridor floor sits 2 tiles out (floor-wall-floor, R-P5)."""
    col, row, w, h = pn.col, pn.row, pn.w, pn.h
    f = pn.floor_tiles
    if any((c, row - 2) in corridor_floor
           for c in range(col, col + w) if (c, row) in f):
        return 'top'
    if any((c, row + h + 1) in corridor_floor
           for c in range(col, col + w) if (c, row + h - 1) in f):
        return 'bottom'
    if any((col - 2, r) in corridor_floor
           for r in range(row, row + h) if (col, r) in f):
        return 'left'
    if any((col + w + 1, r) in corridor_floor
           for r in range(row, row + h) if (col + w - 1, r) in f):
        return 'right'
    return None


def _carve_strip(col, row, w, h, strip_side, t):
    """Carve a `t`-thick strip off `strip_side`, leaving a 1-tile wall gap.

    Returns (closet_floor, room_floor) or None if it does not fit (the room
    needs at least one tile plus the gap on that axis)."""
    if strip_side in ('top', 'bottom'):
        if h < t + 2:
            return None
        if strip_side == 'top':
            crows, rrows = range(row, row + t), range(row + t + 1, row + h)
        else:
            crows, rrows = range(row + h - t, row + h), range(row, row + h - t - 1)
        cols = range(col, col + w)
        return (frozenset((c, r) for c in cols for r in crows),
                frozenset((c, r) for c in cols for r in rrows))
    if w < t + 2:
        return None
    if strip_side == 'left':
        ccols, rcols = range(col, col + t), range(col + t + 1, col + w)
    else:
        ccols, rcols = range(col + w - t, col + w), range(col, col + w - t - 1)
    rows = range(row, row + h)
    return (frozenset((c, r) for c in ccols for r in rows),
            frozenset((c, r) for c in rcols for r in rows))


def _carve_corner(col, row, w, h, sw, sh, corner):
    """Carve an sw×sh toilet at `corner` ('tl'/'tr'/'bl'/'br'), enclosed by an
    L-wall (its two room-facing sides + the corner cell).  Returns
    (closet_floor, room_floor) or None if it does not fit."""
    if w < sw + 1 or h < sh + 1:
        return None
    left = corner in ('tl', 'bl')
    top = corner in ('tl', 'tr')
    tc0 = col if left else col + w - sw
    tr0 = row if top else row + h - sh
    toilet = _rect_tiles(tc0, tr0, sw, sh)
    wall_col = tc0 + sw if left else tc0 - 1
    wall_row = tr0 + sh if top else tr0 - 1
    lwall = {(wall_col, r) for r in range(tr0, tr0 + sh)}
    lwall |= {(c, wall_row) for c in range(tc0, tc0 + sw)}
    lwall.add((wall_col, wall_row))
    room = _rect_tiles(col, row, w, h) - toilet - lwall
    return toilet, frozenset(room)


def _corner_on_side(corner, side):
    return ((side == 'top' and corner in ('tl', 'tr')) or
            (side == 'bottom' and corner in ('bl', 'br')) or
            (side == 'left' and corner in ('tl', 'bl')) or
            (side == 'right' and corner in ('tr', 'br')))


def _shares_boundary(a, b):
    """True if floor sets `a` and `b` are separated by exactly one wall tile
    somewhere — a tile of `a` is two apart (colinear) from a tile of `b`, so the
    between tile is the shared-boundary wall derive_walls will use."""
    for (c, r) in a:
        if ((c + 2, r) in b or (c - 2, r) in b
                or (c, r + 2) in b or (c, r - 2) in b):
            return True
    return False


def _toilet_size(w, h):
    """Square corner-toilet side for a w×h room: ~1/5 of the area (rounded),
    but only if it leaves at least one room tile behind each of its two new
    walls — i.e. size <= min(w, h) - 2.  Returns None if no toilet fits (e.g. a
    room only 2 tiles in one dimension, or one where the 20% size is too big)."""
    s = max(1, round((0.2 * w * h) ** 0.5))
    return s if s <= min(w, h) - 2 else None


def _pick_closet_carve(pn, side, rng, anchors):
    """Choose a buildable closet carve for room pn (corridor on `side`).

    Returns (closet_floor, room_floor) or None.  Types: back office and side
    office ~1/3 of the room (strips); corner toilet ~1/5, near-square."""
    col, row, w, h = pn.col, pn.row, pn.w, pn.h
    area = w * h
    horizontal_edge = side in ('top', 'bottom')
    edge_len = w if horizontal_edge else h          # tiles facing the corridor
    opp = {'top': 'bottom', 'bottom': 'top',
           'left': 'right', 'right': 'left'}[side]
    perp = ('left', 'right') if horizontal_edge else ('top', 'bottom')

    cands = []

    # back office — strip on the side opposite the corridor (~1/3 of the depth)
    depth = h if horizontal_edge else w
    bo = _carve_strip(col, row, w, h, opp, max(1, round(depth / 3)))
    if bo:
        cands.append(bo)

    # side office — strip on a perpendicular side (~1/3 along the corridor edge)
    if edge_len >= 3:
        along = w if horizontal_edge else h
        t = max(1, round(along / 3))
        for ps in perp:
            so = _carve_strip(col, row, w, h, ps, t)
            if so:
                cands.append(so)

    # corner toilet — square ~1/5 of the area, only if it leaves >= 1 room tile
    # behind each of its two new walls (size <= min(w, h) - 2).
    s = _toilet_size(w, h)
    if s is not None:
        for corner in ('tl', 'tr', 'bl', 'br'):
            if edge_len < 3 and _corner_on_side(corner, side):
                continue
            ct = _carve_corner(col, row, w, h, s, s, corner)
            if ct:
                cands.append(ct)

    valid = [(closet, room) for (closet, room) in cands
             if room and _floor_connected(room)
             and all(_shares_boundary(room, anc) for anc in anchors)]
    return rng.choice(valid) if valid else None


def _carve_closets(placed, closet_rooms, graph, rng, corridor_name):
    """Carve each closet out of its parent room's own tiles (spec 0032).

    A closet is a sub-block of the parent bbox separated from the (reduced)
    room by a 1-tile wall; derive_walls then cuts exactly one door between the
    room and the closet (never to the corridor).

    A closet is skipped (left unplaced) in the rare cases where it cannot be
    carved: the parent was dropped, is non-rectangular, faces no corridor, or is
    too small for any buildable carve.  These residual drops — and spilling such
    a closet's content to the room/corridor instead of losing it — are handled
    by spec 0032 C7 (step 2)."""
    corridor_floor = (placed[corridor_name].floor_tiles
                      if corridor_name in placed else frozenset())
    for child, parent in closet_rooms.items():
        if parent not in placed:
            continue
        # Never carve a closet out of a push-puzzle room: shrinking it could make
        # the plate→block puzzle unsolvable.  Leave it whole; the closet's content
        # is spilled by C7 instead.
        if graph.nodes[parent].plates or graph.nodes[parent].blocks:
            continue
        pn = placed[parent]
        if pn.floor_tiles != _rect_tiles(pn.col, pn.row, pn.w, pn.h):
            continue
        side = _corridor_facing_side(pn, corridor_floor)
        if side is None:
            continue
        # The reduced room must keep its boundary with the corridor and every
        # sibling (every placed graph-neighbour except the closet being carved).
        anchors = [placed[nb].floor_tiles
                   for nb, _ in graph.neighbors(parent)
                   if nb != child and nb in placed]
        carve = _pick_closet_carve(pn, side, rng, anchors)
        if carve is None:
            continue
        closet_floor, room_floor = carve
        placed[parent] = PlacedNode(parent, pn.col, pn.row, pn.w, pn.h,
                                    floor_tiles=room_floor)
        ccols = [c for c, _ in closet_floor]
        crows = [r for _, r in closet_floor]
        placed[child] = PlacedNode(
            child, min(ccols), min(crows),
            max(ccols) - min(ccols) + 1, max(crows) - min(crows) + 1,
            floor_tiles=closet_floor)


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

def validate_push_puzzles(room_data, tile_owner, require_plates=True):
    """Check that every push puzzle (block → plate) is solvable.

    For each gate_id, finds the blocks and plate in the same room, then
    runs a Sokoban-style BFS to verify the block can reach the plate.

    State: (player_pos, frozenset_of_block_positions)
    Transitions: player moves to adjacent tile; if it's a block and the
    tile behind the block is free, the block is pushed.

    require_plates=False skips gates whose plate is not in this room
    instead of flagging them: cross-grid BORDER gates (added at stitch
    time) have their plate+block puzzle in another grid by design, so
    the post-stitch re-validation (spec 0048 U4) must not error on them.

    Returns list of error strings (empty = all solvable).
    """
    errors = []
    walls = room_data.get('walls', {})
    blocks = room_data.get('pushable_blocks', [])
    plates = room_data.get('pressure_plates', [])
    gates_list = room_data.get('gates', [])

    if not gates_list or not plates or not blocks:
        return errors

    # Passable tiles come from the same layered-cell model the runtime
    # queries (spec 0048 / BL-14): walls of every type, locked doors,
    # closed gates, and unbridged water via RoomCells.blocked — the
    # solver has no bridge model, so water is solid, exactly as at
    # runtime.  Other blocks are the occupant layer on top, matching
    # World.blocked.
    cells = build_room_cells(room_data)
    block_set = {tuple(b) for b in blocks}
    passable = set()
    for c in range(MIN_C, MAX_C + 1):
        for r in range(MIN_R, MAX_R + 1):
            if not cells.blocked(c, r) and (c, r) not in block_set:
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
            if require_plates:
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


def _plate_exclusions(room_name, neighbours, placed, walls, water_tiles):
    """Tiles where a pressure plate must never sit (spec 0049): the
    solved state of a push puzzle is a block parked on the plate, and a
    block on a passage's landing tile seals that passage.

    A passage tile is any tile on the shared boundary with a neighbour
    (cardinally adjacent to floor of both rooms) that is not a reinforced
    wall: an open doorway hole, a door, a gate, or a breakable wall the
    player can mine through.  (_find_connection_tile is NOT reusable
    here: it returns the centre-most WALL tile of the boundary, which for
    open doorways is beside the actual hole.)  The landing tiles of those
    passages, plus every cardinal flank of a water tile (the landing
    tiles of buildable bridge passages), are excluded."""
    excluded = set()
    room = placed[room_name]
    room_edge = {(t[0] + dc, t[1] + dr)
                 for t in room.floor_tiles for dc, dr in _CARDINAL
                 if (t[0] + dc, t[1] + dr) not in room.floor_tiles}
    for nb in neighbours:
        if nb not in placed:
            continue
        nb_floor = placed[nb].floor_tiles
        for pos in room_edge:
            if walls.get(pos) == WALL_REINFORCED:
                continue                      # never opens: not a passage
            if not any((pos[0] + dc, pos[1] + dr) in nb_floor
                       for dc, dr in _CARDINAL):
                continue
            for dc, dr in _CARDINAL:
                adj = (pos[0] + dc, pos[1] + dr)
                if adj in room.floor_tiles:
                    excluded.add(adj)         # the landing tile
    for wc, wr in water_tiles:
        for dc, dr in _CARDINAL:
            excluded.add((wc + dc, wr + dr))
    return excluded


def _place_puzzle(room_name, gate_id, placed, passable, excluded, rng,
                  prior_puzzles=(), plate_excluded=frozenset()):
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

    plate_excluded (spec 0049) constrains ONLY the plate position — blocks
    and solution paths may still use those tiles (landing tiles of the
    room's doorways and of buildable bridge passages).

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
        if P not in effective_pass or P in excluded or P in plate_excluded:
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
        # Retryable: a closet carve can shrink the room below what the puzzle
        # needs; regenerate rather than crash (spec 0032 / BL-23).
        raise LayoutError(
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


def _place_items_in_room(node, placed_node, walls, rng,
                          global_used=None, spill_floor=None,
                          flame_treasures=False):
    """Pick floor positions for a node's items.

    global_used: shared set across all rooms — no two items on the same tile.
    spill_floor: corridor floor tiles used as overflow when this room runs out
        of space, so a collectible is never silently dropped.  Collectibles are
        placed in priority order: keys, planks, treasures (awards), then other
        materials.  Raises LayoutError only when both the room and the corridor
        are full (should never happen).
    flame_treasures: place a flame node's treasures here too — used by the
        C7 unplaced-node spill, where no jets exist for the far-tile pass
        (spec 0058 award conservation).

    Enemies are not placed here: distribution is a level-wide layout pass
    since spec 0058 (`_distribute_enemies`).
    """
    if global_used is None:
        global_used = set()
    floor = sorted(t for t in placed_node.floor_tiles if t not in walls)
    rng.shuffle(floor)
    used = global_used
    spill = spill_floor if spill_floor is not None else []

    def _next():
        """Next free tile: this room first, then the corridor (spill)."""
        for p in floor:
            if p not in used:
                used.add(p)
                return p
        for p in spill:
            if p not in used:
                used.add(p)
                return p
        return None

    def _place_collectible():
        p = _next()
        if p is None:
            raise LayoutError(
                f"No free tile (room or corridor) to place an item in "
                f"{node.name!r}")
        return p

    # Priority order: keys -> planks -> treasures (awards) -> other materials.
    keys = []
    for (key_colour,) in node.keys:
        c, r = _place_collectible()
        keys.append((c, r, key_colour))

    plank_mats = [m for m in node.materials if m == ('planks',)]
    other_mats = [m for m in node.materials if m != ('planks',)]

    materials = []
    for (mat_type,) in plank_mats:
        c, r = _place_collectible()
        materials.append((c, r, mat_type))

    # Flame-room treasures are placed on far tiles only (see far-tiles pass
    # in build_level_dict); skip them here so nothing lands on the near side.
    treasures = []
    if not node.has_flames or flame_treasures:
        for (item_no,) in node.treasures:
            c, r = _place_collectible()
            treasures.append((c, r, item_no))

    for (mat_type,) in other_mats:
        c, r = _place_collectible()
        materials.append((c, r, mat_type))

    return treasures, materials, keys


# ── Enemy distribution (spec 0058 / BL-20+) ───────────────────────────────────

def _largest_floor_square(tiles):
    """Side of the largest all-floor square inside a tile set.

    Judges rooms by actual shape: a closet-carved parent's roomy bounding
    box may hide an L-shaped floor with much less dodge space.  Standard
    dynamic programme over (col, row)-sorted tiles.
    """
    ts = set(tiles)
    dp = {}
    best = 0
    for t in sorted(ts):
        c, r = t
        dp[t] = 1 + min(dp.get((c - 1, r), 0), dp.get((c, r - 1), 0),
                        dp.get((c - 1, r - 1), 0))
        if dp[t] > best:
            best = dp[t]
    return best


def _enemy_distribution(sizes, count, rng, forge=False):
    """Assign `count` enemies to candidate rooms by the size rule.

    sizes: [(room_id, s)] or [(room_id, s, floor_area)] in deterministic
    order; s = side of the room's largest all-floor square.  Each assigned
    enemy virtually downsizes its room by one tile in both dimensions
    (effective size e = s − k); a room stays a candidate while e ≥ 3, so
    it never holds more than s − 2 enemies.  Selection per enemy: fewest
    assigned enemies (round-robin), then largest e, then largest floor
    area, then one rng.choice among exact ties.  Enemies past the level's
    capacity are dropped.  Returns [(room_id, enemy_type)] in placement
    order; with forge=True the first placed enemy is the forge ogre.
    """
    info = [(e[0], e[1], e[2] if len(e) > 2 else e[1] * e[1])
            for e in sizes]
    k = {rid: 0 for rid, _s, _a in info}
    out = []
    for i in range(count):
        cands = [c for c in info if c[1] - k[c[0]] >= 3]
        if not cands:
            break
        min_k = min(k[c[0]] for c in cands)
        cands = [c for c in cands if k[c[0]] == min_k]
        best_e = max(c[1] - k[c[0]] for c in cands)
        cands = [c for c in cands if c[1] - k[c[0]] == best_e]
        best_a = max(c[2] for c in cands)
        cands = [c for c in cands if c[2] == best_a]
        rid = cands[0][0] if len(cands) == 1 else \
            rng.choice([c[0] for c in cands])
        etype = 'forge_ogre' if forge and not out else 'chaser'
        k[rid] += 1
        out.append((rid, etype))
    return out


def _pick_enemy_tile(free_floor, taken, rng, player_dist=None):
    """Enemy start tile: any free floor tile (enemies reserve no item tile
    and may stand on an item), preferring tiles ≥ MIN_ENEMY_DIST from the
    player when the player starts in this room — the old enemy-pass
    semantics, kept verbatim (spec 0058)."""
    far = [p for p in free_floor if p not in taken
           and (not player_dist
                or player_dist.get(p, 0) >= MIN_ENEMY_DIST)]
    pool = far or [p for p in free_floor if p not in taken]
    if not pool:
        return None
    return rng.choice(pool)


def _distribute_enemies(level, graph, rng):
    """Level-wide enemy & guard-award pass (spec 0058).

    Places exactly 2 × G enemies for a G-grid level (forge ogre first on
    has_forge_ogre levels) via `_enemy_distribution`; candidates are
    non-corridor nodes without blocks, plates, or flames.  Every enemy
    adds one guard award to its room (corridor spill only when the room's
    floor is exhausted — the sole R-P10 exception).  Runs after all grids
    are built (and, multi-grid, stitched): called by _build_super_grid
    and by the single-grid tail of build_level_dict.
    """
    rooms = level['rooms']
    G = len(rooms)

    # node -> (grid, floor tiles); rooms in BFS build order, tiles in
    # tile_owner insertion order — never a str-set (spec 0054).
    floors = {}
    for gname, rd in rooms.items():
        walls = rd['walls']
        for t, owner in rd['tile_owner'].items():
            if t in walls:
                continue
            floors.setdefault(owner, (gname, set()))[1].add(t)

    sizes = []
    for name, node in graph.nodes.items():
        if (node.size == NodeSize.CORRIDOR or node.blocks or node.plates
                or node.has_flames or name not in floors):
            continue
        _gname, tiles = floors[name]
        sizes.append((name, _largest_floor_square(tiles), len(tiles)))

    assignments = _enemy_distribution(
        sizes, 2 * G, rng, forge=getattr(graph, 'has_forge_ogre', False))

    # Tiles item placement already used, per grid — plus the start tiles
    # (R-P8: nothing may cover player_start or the entrance).
    used = {}
    for gname, rd in rooms.items():
        u = set()
        for lname in ('treasures', 'materials', 'keys', 'pressure_plates',
                      'pushable_blocks'):
            for entry in rd.get(lname, []):
                u.add((entry[0], entry[1]))
        if 'entrance' in rd:
            u.add(tuple(rd['entrance']))
            u.add(tuple(level['player_start']))
        used[gname] = u

    cor_floor = {}
    for name, node in graph.nodes.items():
        if node.size == NodeSize.CORRIDOR and name in floors:
            gname, tiles = floors[name]
            cor_floor[gname] = tiles

    enemy_taken = {}
    for name, etype in assignments:
        gname, tiles = floors[name]
        rd = rooms[gname]
        free = sorted(tiles)

        pdist = None
        ps = tuple(level['player_start'])
        if gname == level['start_room'] and ps in tiles:
            pdist = _bfs_dist(ps, tiles)
        taken = enemy_taken.setdefault((gname, name), set())
        pos = _pick_enemy_tile(free, taken, rng, pdist)
        if pos is None:
            continue   # unreachable: candidates hold ≥ 3×3 floor
        taken.add(pos)
        starts = rd.get('enemy_starts', [])
        starts.append((*pos, etype))
        rd['enemy_starts'] = starts

        award_pool = [t for t in free if t not in used[gname]]
        if not award_pool:
            award_pool = sorted(t for t in cor_floor.get(gname, ())
                                if t not in used[gname])
        if not award_pool:
            raise LayoutError(
                f"no free tile for the guard award of {name!r}")
        apos = rng.choice(award_pool)
        used[gname].add(apos)
        trs = rd.get('treasures', [])
        trs.append((*apos, rng.choice(list(range(1, 10)))))
        rd['treasures'] = trs


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
                     occupied_sides=frozenset(), progress=None,
                     corridor_anchor=None, entrance_side=None,
                     place_enemies=True, global_key_colours=None,
                     defer_gate_elision=False):
    """Generate the complete level dict that game.py expects.

    Auto-detects multi-grid from BORDER edges in the graph.
    grid_count parameter is kept for API compatibility but ignored when
    BORDER edges are present.
    is_start_grid: when True, stores 'entrance' in the room dict and computes
                   player_start from the entrance tile.
    occupied_sides: sides already used by BORDER exits; entrance avoids these.
    entrance_side: the side reserved by grid zero for the level entrance
                   (multi-grid start grid, spec 0053); the entrance is placed
                   there deterministically.
    progress: optional callable(done, total) invoked as generation proceeds so
              callers can render a loading indicator.  For multi-grid levels the
              unit is one grid; for single-grid levels it fires (0, 1)/(1, 1).
    """
    rng = rng or random.Random()

    if any(e.edge_type == EdgeType.BORDER for e in graph.edges):
        return _build_super_grid(graph, rng, strategies, progress=progress)

    if progress:
        progress(0, 1)

    # Grid zero for single-grid levels (spec 0055): honour the graph's
    # reserved entrance side — pre-pick a strategy that covers it (R-S1 then
    # makes the corridor reach it), mirroring the multi-grid _build_grid
    # flow.  Per-grid builds from _build_super_grid arrive with
    # required_exits already set and their strategy pre-picked; manually
    # built graphs carry no entrance_side and keep the scanning behaviour.
    entrance_side = entrance_side or getattr(graph, 'entrance_side', None)
    if entrance_side is not None and required_exits is None:
        required_exits = frozenset({entrance_side})
        n_rooms = sum(1 for nd in graph.nodes.values()
                      if nd.size not in (NodeSize.CORRIDOR, NodeSize.CLOSET))
        strategies = [_pick_strategy(required_exits, strategies or STRATEGIES,
                                     rng, n_rooms=n_rooms)]

    placed = layout_graph(graph, rng=rng, strategies=strategies,
                          required_exits=required_exits,
                          corridor_anchor=corridor_anchor)
    walls, water_tiles = derive_walls(graph, placed)
    tile_owner = build_tile_owner(placed)

    # Find player start via entrance tile
    start_name = None
    for name, node in graph.nodes.items():
        if node.is_start:
            start_name = name
            break
    pn = placed[start_name]
    entrance_tile, player_start = _pick_entrance(pn.floor_tiles, occupied_sides,
                                                 entrance_side=entrance_side)

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
            jet['room'] = name   # award relocation targets this room's jets
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

    # Map each water tile to the water room it gives access to (the node behind
    # the WATER edge, edge.node_b).  The runtime keys the one-bridge-per-water-
    # room lock on this (spec 0029 W2/W4).
    water_tile_room = {}
    for _edge in graph.edges:
        if _edge.edge_type != EdgeType.WATER:
            continue
        if _edge.node_a not in placed or _edge.node_b not in placed:
            continue
        for wt in _build_water_stream(
                placed[_edge.node_a], placed[_edge.node_b], orig_walls):
            water_tile_room[wt] = _edge.node_b

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
    # Water is solid until bridged and the puzzle subsystem has no bridge
    # model, so water tiles are excluded here too (spec 0048 U3 / BL-14) —
    # solutions are never routed across water in the first place.
    puzzle_passable = ({(c, r) for c in range(MIN_C, MAX_C + 1)
                        for r in range(MIN_R, MAX_R + 1)}
                       - set(walls.keys())
                       - gate_tiles
                       - lock_tiles
                       - {tuple(t) for t in water_tiles})

    # Place push puzzles atomically: choose (plate, block) together so the
    # block is reachable from the plate via the reverse BFS and confirmed
    # solvable by the full Sokoban BFS.  Earlier puzzles' solution tiles are
    # excluded when placing later puzzles.
    all_plates = []
    all_blocks = []
    # Spec 0057 (R-P8): the start grid's player_start and entrance tile are
    # off-limits to every item-placement path (room floor, corridor spill,
    # flame far-tiles) — all of them consult this one set.  Non-start grids
    # keep an empty seed: their _pick_entrance result is only the
    # enemy-distance reference tile, never a real entrance (spec 0053).
    global_used = {player_start, entrance_tile} if is_start_grid else set()
    excluded = set()
    prior_puzzles = []   # (plate, block) for all already-placed puzzles

    for name, node in graph.nodes.items():
        if name not in placed or not node.plates:
            continue
        # NOTE: pass the post-carve `walls`, not orig_walls — orig_walls
        # marks every non-floor tile reinforced (a synthetic map for
        # door/gate placement), which hides every carved doorway hole
        # from the passage scan.
        plate_excluded = _plate_exclusions(
            name, [nb for nb, _ in graph.neighbors(name)], placed,
            walls, water_tiles)
        for (gate_id,) in node.plates:
            plate, block, sol = _place_puzzle(
                name, gate_id, placed, puzzle_passable, excluded, rng,
                prior_puzzles=prior_puzzles, plate_excluded=plate_excluded)
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

    # Place other items (treasures, materials, keys).  Enemies are no
    # longer placed per room: they are distributed level-wide after all
    # grids exist (spec 0058, _distribute_enemies).
    # Plates and blocks are already placed above; global_used carries their
    # positions so _place_items_in_room does not collide with them.
    all_treasures = []
    all_materials = []
    all_keys = []

    item_walls = dict(walls)
    for ft in flame_tile_set:
        item_walls[ft] = WALL_REINFORCED

    # Corridor floor tiles serve as the overflow ("spill") target so a
    # collectible is never dropped when its own room is full.
    corridor_name = next(
        (n for n, nd in graph.nodes.items()
         if nd.size == NodeSize.CORRIDOR and n in placed), None)
    spill_floor = []
    if corridor_name is not None:
        spill_floor = sorted(t for t in placed[corridor_name].floor_tiles
                             if t not in item_walls)
        rng.shuffle(spill_floor)

    for name, node in graph.nodes.items():
        if name not in placed:
            continue
        t, m, k = _place_items_in_room(
            node, placed[name], item_walls, rng,
            global_used=global_used, spill_floor=spill_floor)
        all_treasures.extend(t)
        all_materials.extend(m)
        all_keys.extend(k)

    # Spill the content of any UNPLACED node (a closet that could not be carved,
    # or a room dropped by the packer) into a placed neighbour — the closet's
    # room if it is placed, else the corridor — so nothing is lost (spec 0032
    # C7). Push-puzzle plates of an unplaced node are not spilled: the gate is
    # elided instead (it is created only if its plate survived — see below).
    for name, node in graph.nodes.items():
        if name in placed:
            continue
        if not (node.treasures or node.materials or node.keys):
            continue
        target = next((nb for nb, _ in graph.neighbors(name) if nb in placed),
                      corridor_name)
        if target is None or target not in placed:
            raise LayoutError(f"no placed room to spill content of {name!r}")
        t, m, k = _place_items_in_room(
            node, placed[target], item_walls, rng,
            global_used=global_used, spill_floor=spill_floor,
            flame_treasures=True)
        all_treasures.extend(t)
        all_materials.extend(m)
        all_keys.extend(k)

    # Relocate each placed flame room's challenge award to its jets' far
    # side (spec 0058): the reward is collectable only after crossing the
    # flames.  Falls back to any free room tile, then corridor spill, so
    # the award is never lost (C7 conservation).
    for name, node in graph.nodes.items():
        if name not in placed or not node.has_flames or not node.treasures:
            continue
        far_free = [t for jet in all_flame_jets if jet.get('room') == name
                    for t in jet.get('far_tiles', [])
                    if t not in flame_tile_set and t not in walls
                    and t not in global_used]
        room_free = [t for t in sorted(placed[name].floor_tiles)
                     if t not in item_walls and t not in global_used]
        for (item_no,) in node.treasures:
            pool = (far_free or room_free
                    or [t for t in spill_floor if t not in global_used])
            if not pool:
                raise LayoutError(
                    f"no free tile for the flame award of {name!r}")
            pos = rng.choice(pool)
            far_free = [t for t in far_free if t != pos]
            room_free = [t for t in room_free if t != pos]
            global_used.add(pos)
            all_treasures.append((*pos, item_no))

    # Locked doors, gates, and water tiles from edges
    # (orig_walls already computed above for puzzle_passable)
    all_locked_doors = []
    all_gates = []
    all_water_tiles = []

    # Barrier ↔ prerequisite coupling (specs 0030/0061).
    #
    # Doors: keys are NEVER lost (spill guarantee, K1), and key placement
    # is deliberately cross-grid (R-V3) — so the door is created
    # unconditionally, and a colour with no key anywhere in the FULL
    # graph is a loud LayoutError (should-be-impossible, checked), never
    # a silently reshaped level.  The old per-grid check elided every
    # door whose key sat on another grid (orphan keys, spec 0061).
    #
    # Gates: plates CAN be lost (a dropped puzzle room takes its plate;
    # plates are not spilled), so gates keep degrade-to-open — but at
    # global scope: per-grid builds (defer_gate_elision=True) create
    # gates unconditionally and _build_super_grid elides against the
    # surviving plates of ALL grids.  Single-grid builds elide locally,
    # where local == global.
    if global_key_colours is None:
        global_key_colours = {k[0] for nd in graph.nodes.values()
                              for k in nd.keys}
    placed_gate_ids = {gid for *_, gid in all_plates}

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
            if colour not in global_key_colours:
                raise LayoutError(
                    f"locked door {colour!r} has no key anywhere in the "
                    f"graph — K1 regression")
            all_locked_doors.append((*conn, colour))
        elif edge.edge_type == EdgeType.GATED:
            gate_id = edge.params['gate_id']
            if defer_gate_elision or gate_id in placed_gate_ids:
                all_gates.append((*conn, gate_id))
            # else: plate room dropped — make this an open passage
        elif edge.edge_type == EdgeType.WATER:
            pass  # water tiles already collected by derive_walls

    # Build room dict
    grid_name = 'main'
    room = {
        'walls': walls,
        'tile_owner': tile_owner,
    }
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
    if water_tile_room:
        room['water_tile_room'] = water_tile_room
    if all_flame_jets:
        room['flame_jets'] = all_flame_jets
    if is_start_grid:
        room['entrance'] = entrance_tile

    # Validate layout invariant
    errors = validate_layout(graph, placed, walls)
    if errors:
        raise ValueError(f"Layout invariant violated: {errors}")

    # Validate push puzzles are solvable.  LayoutError → fresh-seed retry
    # in _generate_act2_level (a ValueError here would crash generation).
    push_errors = validate_push_puzzles(room, tile_owner)
    if push_errors:
        raise LayoutError(f"Unsolvable push puzzle: {push_errors}")

    # Store dead squares (already computed before block placement)
    if dead_squares:
        room['dead_squares'] = list(dead_squares)

    if progress:
        progress(1, 1)

    level = {
        'start_room': grid_name,
        'player_start': player_start,
        'rooms': {grid_name: room},
    }
    # Level-wide enemy & guard-award pass (spec 0058).  Per-grid builds
    # from _build_super_grid skip this: the super-grid distributes once
    # over all grids after stitching.
    if place_enemies:
        _distribute_enemies(level, graph, rng)
    return level


def _build_super_grid(graph, rng, strategies, progress=None):
    """Build a level spanning N 30×16 grids connected by BORDER edges.

    Discovers corridors via BFS from the start corridor, builds each grid
    independently, then stitches them together along their BORDER edges.

    progress: optional callable(done, total) reporting grids laid out so far.
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
        cnode = sub.add_node(corridor, graph.nodes[corridor].size, is_start=True)
        # Copy the corridor's own items — start_next_grid can place a border
        # key (or treasures/materials) on a corridor; without this they'd be
        # lost when the grid is laid out.
        src = graph.nodes[corridor]
        cnode.treasures = list(src.treasures)
        cnode.materials = list(src.materials)
        cnode.keys = list(src.keys)
        cnode.blocks = list(src.blocks)
        cnode.plates = list(src.plates)
        cnode.has_flames = src.has_flames

        def _copy(dst, s):
            dst.treasures = list(s.treasures)
            dst.materials = list(s.materials)
            dst.keys = list(s.keys)
            dst.blocks = list(s.blocks)
            dst.plates = list(s.plates)
            dst.has_flames = s.has_flames

        # Corridor's room neighbours, then nodes hanging off those rooms (nested
        # closets — they attach to a room, not the corridor, so without this BFS
        # they'd be omitted from the subgraph and dropped; spec 0032 / BL-23).
        frontier = []
        for name, edge in graph.neighbors(corridor):
            if edge.edge_type == EdgeType.BORDER:
                continue
            _copy(sub.add_node(name, graph.nodes[name].size), graph.nodes[name])
            sub.add_edge(corridor, name, edge.edge_type, **edge.params)
            frontier.append(name)
        while frontier:
            par = frontier.pop()
            for name, edge in graph.neighbors(par):
                if edge.edge_type == EdgeType.BORDER or name in sub.nodes:
                    continue
                _copy(sub.add_node(name, graph.nodes[name].size), graph.nodes[name])
                sub.add_edge(par, name, edge.edge_type, **edge.params)
                frontier.append(name)
        return sub

    # Required border sides per corridor (the corridor must reach these so a
    # shared continuation position exists at every BORDER face).
    required_sides = {cor: set() for cor in corridor_order}
    for edge in graph.edges:
        if edge.edge_type != EdgeType.BORDER:
            continue
        required_sides[edge.node_a].add(edge.params['exit_side'])
        required_sides[edge.node_b].add(edge.params['entry_side'])

    # The start grid's face toward grid zero is reserved for the level
    # entrance (spec 0053); the corridor must reach it like any BORDER face
    # so the entrance lands on a corridor tile there.  Grid zero guarantees
    # no BORDER edge ever names this side.
    entrance_side = getattr(graph, 'entrance_side', None)
    if entrance_side:
        required_sides[corridor_order[0]].add(entrance_side)

    grid_name_map = {cor: (f'grid_{i}' if i > 0 else 'grid_a')
                     for i, cor in enumerate(corridor_order)}

    _FULL = {'left':  frozenset(range(MIN_R, MAX_R + 1)),
             'right': frozenset(range(MIN_R, MAX_R + 1)),
             'top':   frozenset(range(MIN_C, MAX_C + 1)),
             'bottom': frozenset(range(MIN_C, MAX_C + 1))}

    def _face_band(room_main, cor_name, side):
        """Positions (rows for left/right, cols for top/bottom) where this
        grid's corridor reaches the inner line of `side`."""
        owner = room_main['tile_owner']
        if side in ('left', 'right'):
            col = MIN_C if side == 'left' else MAX_C
            return frozenset(r for (c, r), o in owner.items()
                             if c == col and o == cor_name)
        row = MIN_R if side == 'top' else MAX_R
        return frozenset(c for (c, r), o in owner.items()
                         if r == row and o == cor_name)

    _ANCHOR_FAMILY = ('horizontal', 'off_centre', 'vertical', 't', 'double_t')

    def _anchor_candidates(exits, n_rooms):
        """Spine/stem strategies that reach every required exit, so the anchored
        side has a corridor segment to fix.  Arm strategies (z/s/l) cannot
        reproduce an arbitrary band and are excluded when an anchor is active."""
        exits = frozenset(exits)
        has_lr = bool(exits & {'left', 'right'})
        has_tb = bool(exits & {'top', 'bottom'})
        if has_lr and has_tb:
            comp = _COVERS_ALL if len(exits) > 2 else _COVERS_L
        elif has_lr:
            comp = _COVERS_LR
        elif has_tb:
            comp = _COVERS_TB
        else:
            comp = frozenset(_ANCHOR_FAMILY)
        avail = [s for s in (strategies or STRATEGIES)
                 if s in comp and s in _ANCHOR_FAMILY]
        # Strict room-count filter (no over-zoned fallback): a grid must not pick
        # a strategy with more zones than it has regular rooms — when nothing fits,
        # _build_grid falls through to full_border (1 zone).  Closets are already
        # excluded from n_rooms by the caller.
        avail = [s for s in avail if n_rooms >= _STRATEGY_MAX_ZONES.get(s, 2)]
        rng.shuffle(avail)
        return avail

    # Spec 0061: per-grid builds cannot see other grids' keys, so the
    # door coupling check runs against the FULL graph's key colours.
    all_key_colours = frozenset(k[0] for nd in graph.nodes.values()
                                for k in nd.keys)

    def _build_grid(sub, corridor, i, anchor):
        """Build one grid, continuing the parent's corridor band when `anchor`
        is set.  Tries compatible strategies, then full_border (whose frame
        reaches every position) as a per-grid last resort."""
        exits = required_sides[corridor]
        # Closets are carved from their parent (they occupy no zone), so they must
        # NOT count toward room-count strategy selection — otherwise a grid picks a
        # layout with more zones than it has regular rooms, leaving zones empty.
        n_rooms = sum(1 for nm, nd in sub.nodes.items()
                      if nd.size not in (NodeSize.CORRIDOR, NodeSize.CLOSET))
        if anchor is None:
            cand = [_pick_strategy(frozenset(exits), strategies, rng,
                                   n_rooms=n_rooms)]
        else:
            cand = _anchor_candidates(exits, n_rooms)
        for strat in cand + ['full_border']:
            try:
                d = build_level_dict(
                    sub, rng=rng, strategies=[strat], grid_count=1,
                    required_exits=frozenset(exits), is_start_grid=(i == 0),
                    occupied_sides=exits, corridor_anchor=anchor,
                    entrance_side=(entrance_side if i == 0 else None),
                    place_enemies=False,
                    global_key_colours=all_key_colours,
                    defer_gate_elision=True)
            except (LayoutError, ValueError):
                continue
            if anchor is not None:
                side, lo, w = anchor
                band = _face_band(d['rooms']['main'], corridor, side)
                if not (band & set(range(lo, lo + w))):
                    continue   # strategy ignored / could not honour the anchor
            return d
        raise LayoutError(f"no strategy placed grid {corridor!r}")

    def _varied_band(side):
        """A full_border grid covers the whole face, so it actively picks a
        varied exit band (instead of always opening at grid centre) within a
        range a non-full child can still continue (spec 0042)."""
        w = rng.randint(2, 3)
        if side in ('left', 'right'):
            lo = rng.randint(MIN_R + 3, MAX_R - w - 2)   # rows ~4..10
        else:
            lo = rng.randint(MIN_C + 6, MAX_C - w - 5)   # cols ~7..21
        return lo, w

    # Build grids in BFS order: a grid's spanning-tree parent is built first and
    # fixes the corridor band on the shared face, so the corridor continues
    # straight across the border (BL-29 / spec 0042).
    all_rooms = {}
    all_player_starts = {}
    built = set()
    chosen_pos = {}   # frozenset(corridor pair) -> opening position (full_border src)
    total_grids = len(corridor_order)
    if progress:
        progress(0, total_grids)
    for i, corridor in enumerate(corridor_order):
        anchor = None
        if i > 0:
            for nbr, edge in graph.neighbors(corridor):
                if edge.edge_type != EdgeType.BORDER or nbr not in built:
                    continue
                if edge.node_a == corridor:
                    child_side = edge.params['exit_side']
                    parent_side = edge.params['entry_side']
                else:
                    child_side = edge.params['entry_side']
                    parent_side = edge.params['exit_side']
                parent_band = _face_band(all_rooms[grid_name_map[nbr]],
                                         nbr, parent_side)
                if parent_band == _FULL[parent_side]:
                    # full_border parent: actively choose a varied exit band and
                    # have the child continue it (recorded so the stitch uses it
                    # even when the child is also full_border).
                    lo, w = _varied_band(child_side)
                    anchor = (child_side, lo, w)
                    chosen_pos[frozenset((corridor, nbr))] = lo + w // 2
                elif parent_band:
                    lo = min(parent_band)
                    w = max(parent_band) - lo + 1
                    anchor = (child_side, lo, w)
                break
        sub = _build_subgraph(corridor, is_start_grid=(i == 0))
        d = _build_grid(sub, corridor, i, anchor)
        gname = grid_name_map[corridor]
        all_rooms[gname] = d['rooms']['main']
        all_player_starts[gname] = d['player_start']
        built.add(corridor)
        if progress:
            progress(i + 1, total_grids)


    player_start = all_player_starts[grid_name_map[corridor_order[0]]]

    # Prerequisites that actually survived placement, across all grids (the
    # inventory is global).  A border door/gate is created only when its key /
    # plate is on the floor somewhere — never a barrier with no prerequisite,
    # which would soft-lock the level.
    surviving_key_colours = {
        k[2] for rd in all_rooms.values() for k in rd.get('keys', [])}
    surviving_gate_ids = {
        p[2] for rd in all_rooms.values() for p in rd.get('pressure_plates', [])}

    # Spec 0061 D2: per-grid builds created interior gates unconditionally
    # (defer_gate_elision); elide here, at global scope, exactly those
    # whose plate did not survive on ANY grid — same semantics as the
    # border gates below.  Plates can genuinely drop with their room, so
    # this stays a silent degrade-to-open, unlike the loud door check.
    for _rd in all_rooms.values():
        if _rd.get('gates'):
            _rd['gates'] = [g for g in _rd['gates']
                            if g[2] in surviving_gate_ids]

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
        cor_a   = edge.node_a   # corridor node names own the corridor tiles
        cor_b   = edge.node_b

        exit_side  = edge.params.get('exit_side',  'right')
        entry_side = edge.params.get('entry_side', 'left')

        # Only the corridor may be opened onto — never a room that happens to
        # reach the border face (BL-29).  Continuation guarantees a shared
        # corridor position exists.
        if exit_side in ('right', 'left'):
            col_a = _INNER[exit_side][0]
            col_b = _INNER[entry_side][0]
            rows_a = {r for (c, r), o in room_a['tile_owner'].items()
                      if c == col_a and o == cor_a}
            rows_b = {r for (c, r), o in room_b['tile_owner'].items()
                      if c == col_b and o == cor_b}
            shared = sorted(rows_a & rows_b)
            if not shared:
                raise ValueError(
                    f"No shared floor row between {gname_a} ({exit_side}) "
                    f"and {gname_b} ({entry_side})")
            want = chosen_pos.get(frozenset((cor_a, cor_b)))
            pos = want if want in shared else shared[len(shared) // 2]
            room_a['walls'].pop((col_a, pos), None)
            room_b['walls'].pop((col_b, pos), None)
            exit_key_a = f'{exit_side}_{pos}'
            exit_key_b = f'{entry_side}_{pos}'
        else:
            row_a = _INNER[exit_side][1]
            row_b = _INNER[entry_side][1]
            cols_a = {c for (c, r), o in room_a['tile_owner'].items()
                      if r == row_a and o == cor_a}
            cols_b = {c for (c, r), o in room_b['tile_owner'].items()
                      if r == row_b and o == cor_b}
            shared = sorted(cols_a & cols_b)
            if not shared:
                raise ValueError(
                    f"No shared floor col between {gname_a} ({exit_side}) "
                    f"and {gname_b} ({entry_side})")
            want = chosen_pos.get(frozenset((cor_a, cor_b)))
            pos = want if want in shared else shared[len(shared) // 2]
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
        record = ('open', None, None)
        if barrier == 'locked' and edge.params['key_colour'] in surviving_key_colours:
            colour = edge.params['key_colour']
            doors = room_a.get('locked_doors', [])
            doors.append((*barrier_tile, colour))
            room_a['locked_doors'] = doors
            record = ('locked', colour, (gname_a, barrier_tile))
        elif barrier == 'gated' and edge.params['gate_id'] in surviving_gate_ids:
            gate_id = edge.params['gate_id']
            gates = room_a.get('gates', [])
            gates.append((*barrier_tile, gate_id))
            room_a['gates'] = gates
            record = ('gated', gate_id, None)
        # else: barrier prerequisite absent — leave the border passage open

        # Spec 0056 (BL-12): mirror the barrier type onto BOTH room dicts as
        # render metadata (like exits — never a cells entry: a real mirror
        # Barrier on the entry tile would block the return transition).
        # The locked record's home names the room and tile of the one real
        # door entity, so the renderer can match _opened_doors entries.
        for room, ek in ((room_a, exit_key_a), (room_b, exit_key_b)):
            bb = room.get('border_barriers', {})
            bb[ek] = record
            room['border_barriers'] = bb

    # Spec 0048 U4: re-validate every room of the stitched whole.
    # Stitching only opens borders and adds border barriers, so this
    # should never fire — it turns "should be impossible" into "checked".
    for _gname, _room in all_rooms.items():
        _errors = validate_push_puzzles(_room, _room.get('tile_owner', {}),
                                        require_plates=False)
        if _errors:
            raise LayoutError(
                f"post-stitch push puzzle unsolvable in {_gname}: {_errors}")

    start_grid = grid_name_map[corridor_order[0]]
    level = {
        'start_room': start_grid,
        'player_start': player_start,
        'rooms': all_rooms,
    }
    # Level-wide enemy & guard-award pass (spec 0058): needs every grid's
    # room sizes, so it runs once here, after all grids are built and
    # stitched (grids in BFS build order).
    _distribute_enemies(level, graph, rng)
    return level
