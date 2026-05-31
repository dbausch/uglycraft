"""
Level definitions for a 30×16 grid (0-indexed).
Border cells (col 0, col 29, row 0, row 15) are always walls — not listed here.
All coordinates are interior: cols 1-28, rows 1-14.
"""
from constants import COLS, ROWS


def _h(x1, x2, y):
    return [(x, y) for x in range(x1, x2 + 1)]


def _v(x, y1, y2):
    return [(x, y) for y in range(y1, y2 + 1)]


def _make_walls(*segments):
    walls = set()
    for seg in segments:
        walls.update(seg)
    # clip to interior
    walls = {(c, r) for c, r in walls if 1 <= c <= COLS - 2 and 1 <= r <= ROWS - 2}
    return walls


# ── Level data ────────────────────────────────────────────────────────────────
# Each entry: player_start, enemy_start, walls (set of (col,row) tuples)

LEVELS = [

    # 1 ── Open field ──────────────────────────────────────────────────────────
    {
        'player_start': (15, 8),
        'enemy_start':  (2, 8),
        'walls': _make_walls(),
    },

    # 2 ── Single horizontal wall ──────────────────────────────────────────────
    {
        'player_start': (15, 3),
        'enemy_start':  (2, 8),
        'walls': _make_walls(
            _h(6, 23, 7),
        ),
    },

    # 3 ── H-shape: two verticals + horizontal with centre gap ─────────────────
    {
        'player_start': (15, 4),
        'enemy_start':  (2, 8),
        'walls': _make_walls(
            _v(7,  3, 11),
            _v(22, 3, 11),
            _h(7,  13, 7),       # left half of crossbar
            _h(16, 22, 7),       # right half (gap at cols 14-15)
        ),
    },

    # 4 ── Short pillars + horizontal wall with gap ────────────────────────────
    {
        'player_start': (15, 4),
        'enemy_start':  (2, 4),    # above the crossbar at y=8
        'walls': _make_walls(
            _v(5,  2, 6),        # upper left pillar
            _v(24, 2, 6),        # upper right pillar
            _v(5,  9, 13),       # lower left pillar
            _v(24, 9, 13),       # lower right pillar
            _h(2,  13, 8),       # left half crossbar
            _h(16, 27, 8),       # right half crossbar (gap at 14-15)
        ),
    },

    # 5 ── Cage with openings at top, bottom and centre ─────────────────────────
    {
        'player_start': (15, 8),
        'enemy_start':  (27, 8),
        'walls': _make_walls(
            _v(7,  3, 12),
            _v(22, 3, 12),
            _h(8,  21, 3),       # top wall (gaps at col 7 and 22)
            _h(8,  12, 12),      # bottom-left segment
            _h(17, 21, 12),      # bottom-right segment (gap at 13-16)
        ),
    },

    # 6 ── Grid of pillars with horizontal corridor ────────────────────────────
    {
        'player_start': (28, 3),   # far-right, clear of last pillar column
        'enemy_start':  (2, 8),
        'walls': _make_walls(
            # five pillar columns, two rows of blocks each
            *[_v(c, 2, 6)  for c in (5, 10, 15, 20, 25)],
            *[_v(c, 9, 13) for c in (5, 10, 15, 20, 25)],
            # extra stagger row between pillars
            *[_v(c, 2, 6)  for c in (7, 12, 17, 22, 27)],
            *[_v(c, 9, 13) for c in (7, 12, 17, 22, 27)],
            # horizontal corridor at rows 7-8 is kept clear by design
        ),
    },

    # 7 ── Three overlapping X-shapes + clear centre corridor ──────────────────
    {
        'player_start': (28, 8),   # right edge, clear of corridor wall
        'enemy_start':  (2, 7),    # above corridor wall segment
        'walls': _make_walls(
            # left X (centred at col 7, row 8)
            *[[(7 + d, 8 + d), (7 + d, 8 - d),
               (7 - d, 8 + d), (7 - d, 8 - d)] for d in range(1, 5)],
            # centre X (col 15, row 8)
            *[[(15 + d, 8 + d), (15 + d, 8 - d),
               (15 - d, 8 + d), (15 - d, 8 - d)] for d in range(1, 5)],
            # right X (col 23, row 8)
            *[[(23 + d, 8 + d), (23 + d, 8 - d),
               (23 - d, 8 + d), (23 - d, 8 - d)] for d in range(1, 5)],
            # horizontal corridor — rows 7-9 cleared, plus gaps in centre row
            _h(2, 11, 8),        # left centre segment
            _h(19, 27, 8),       # right centre segment (gap at 12-18)
        ),
    },

    # 8 ── Alternating tall vertical walls (slalom) ────────────────────────────
    {
        'player_start': (27, 3),
        'enemy_start':  (2, 12),
        'walls': _make_walls(
            _v(6,  1, 11),
            _v(12, 4, 14),
            _v(18, 1, 11),
            _v(24, 4, 14),
        ),
    },

    # 9 ── Divided chambers ────────────────────────────────────────────────────
    {
        'player_start': (15, 8),
        'enemy_start':  (2, 8),
        'walls': _make_walls(
            # Centre vertical divider with gaps
            _v(14, 1, 5),
            _v(14, 10, 14),
            _v(15, 1, 5),
            _v(15, 10, 14),
            # Left-chamber inner walls
            _h(2, 12,  5),
            _h(2, 12, 10),
            # Right-chamber inner walls
            _h(17, 27,  5),
            _h(17, 27, 10),
        ),
    },
]
