"""
Level definitions for a 30×16 grid (0-indexed).
Border cells (col 0, col 29, row 0, row 15) are always walls — not listed here.
All coordinates are interior: cols 1-28, rows 1-14.

enemy_starts is a list of positions; EASY always uses only the first one,
HARD uses all of them (1 enemy for levels 1-3, 2 for 4-6, 3 for 7-9).
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
LEVELS = [

    # 1 ── Open field ──────────────────────────────────────────────────────────
    {
        'player_start':  (15, 8),
        'enemy_starts': [(2, 8)],
        'walls': _make_walls(),
    },

    # 2 ── Single horizontal wall ──────────────────────────────────────────────
    {
        'player_start':  (15, 3),
        'enemy_starts': [(2, 8)],
        'walls': _make_walls(
            _h(6, 23, 7),
        ),
    },

    # 3 ── H-shape: two verticals + horizontal with centre gap ─────────────────
    {
        'player_start':  (15, 4),
        'enemy_starts': [(2, 8)],
        'walls': _make_walls(
            _v(7,  3, 11),
            _v(22, 3, 11),
            _h(7,  13, 7),
            _h(16, 22, 7),
        ),
    },

    # 4 ── Short pillars + horizontal wall with gap ── 2 enemies ──────────────
    {
        'player_start':  (15, 4),
        'enemy_starts': [(2, 4),    # upper-left, above the crossbar
                         (27, 11)], # lower-right, below the crossbar
        'walls': _make_walls(
            _v(5,  2, 6),
            _v(24, 2, 6),
            _v(5,  9, 13),
            _v(24, 9, 13),
            _h(2,  13, 8),
            _h(16, 27, 8),
        ),
    },

    # 5 ── Cage with openings ── 2 enemies ─────────────────────────────────────
    {
        'player_start':  (15, 8),
        'enemy_starts': [(27, 8),   # right of cage
                         (2, 12)],  # lower-left
        'walls': _make_walls(
            _v(7,  3, 12),
            _v(22, 3, 12),
            _h(8,  21, 3),
            _h(8,  12, 12),
            _h(17, 21, 12),
        ),
    },

    # 6 ── Grid of pillars ── 2 enemies ────────────────────────────────────────
    {
        'player_start':  (28, 3),
        'enemy_starts': [(2, 8),    # left corridor
                         (2, 13)],  # bottom-left
        'walls': _make_walls(
            *[_v(c, 2, 6)  for c in (5, 10, 15, 20, 25)],
            *[_v(c, 9, 13) for c in (5, 10, 15, 20, 25)],
            *[_v(c, 2, 6)  for c in (7, 12, 17, 22, 27)],
            *[_v(c, 9, 13) for c in (7, 12, 17, 22, 27)],
        ),
    },

    # 7 ── Three sealed vaults — must break walls to reach treasures inside ── 3 enemies
    {
        'player_start':  (14, 1),   # top corridor, between the two upper vaults
        'enemy_starts': [(2,  8),   # left side of middle corridor
                         (27, 8),   # right side of middle corridor
                         (14, 14)], # bottom corridor
        'walls': _make_walls(
            # Vault A — upper-left (cols 2-10, rows 2-7)
            _h(2, 10, 2), _h(2, 10, 7),
            _v(2, 2, 7),  _v(10, 2, 7),
            # Vault B — upper-right, mirror of A (cols 19-27, rows 2-7)
            _h(19, 27, 2), _h(19, 27, 7),
            _v(19, 2, 7),  _v(27, 2, 7),
            # Vault C — lower-centre (cols 9-20, rows 9-13)
            _h(9, 20, 9),  _h(9, 20, 13),
            _v(9, 9, 13),  _v(20, 9, 13),
        ),
    },

    # 8 ── Alternating tall vertical walls (slalom) ── 3 enemies ──────────────
    {
        'player_start':  (27, 3),
        'enemy_starts': [(2, 12),   # bottom-left
                         (13, 2),   # top-centre (between slalom columns)
                         (23, 12)], # bottom-right (between cols 18 and 24)
        'walls': _make_walls(
            _v(6,  1, 11),
            _v(12, 4, 14),
            _v(18, 1, 11),
            _v(24, 4, 14),
        ),
    },

    # 9 ── Divided chambers ── 3 enemies (HARD) ───────────────────────────────
    {
        'player_start':  (15, 8),
        'enemy_starts': [(2, 8),    # left chamber, middle
                         (27, 8),   # right chamber, middle
                         (2, 13)],  # left chamber, bottom
        'walls': _make_walls(
            _v(14, 1, 5),
            _v(14, 10, 14),
            _v(15, 1, 5),
            _v(15, 10, 14),
            _h(2, 12,  5),
            _h(2, 12, 10),
            _h(17, 27,  5),
            _h(17, 27, 10),
        ),
    },

    # 10 ── Boss level: triple-layered vault, corner cavities, electric boss ─────
    #
    # Crown is at a FIXED position (14, 8) inside the innermost vault ring.
    # To reach it the player must break through three separate wall layers
    # (9 total hits = 4 placement credits earned along the way).
    #
    # Corner cavities: col 4 / col 25 form the inner walls of 4 pockets,
    # each open toward the centre — tactical hiding spots vs the boss.
    {
        'player_start':  (2, 7),
        'enemy_starts': [(27, 7)],        # the boss — 1 enemy on all difficulties
        'crown_pos':     (14, 8),         # fixed position, not randomly spawned
        'walls': _make_walls(
            # Triple-layered central vault
            _h(9,  20,  3), _h(9,  20, 12),
            _v(9,   3, 12), _v(20,  3, 12),
            _h(11, 18,  5), _h(11, 18, 10),
            _v(11,  5, 10), _v(18,  5, 10),
            _h(13, 16,  7), _h(13, 16,  9),
            _v(13,  7,  9), _v(16,  7,  9),
            # Corner cavities (open toward centre)
            _v(4,  1,  4), _v(25,  1,  4),
            _v(4, 10, 14), _v(25, 10, 14),
            # Scattered single blocks
            [(7, 2)],  [(22, 2)],
            [(7, 13)], [(22, 13)],
            [(5, 5)],  [(24, 5)],
            [(5, 10)], [(24, 10)],
            [(7, 7)],  [(22, 7)],
        ),
    },
]
