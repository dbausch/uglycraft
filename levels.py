"""
Level definitions for a 30×16 grid (0-indexed).
Border cells (col 0, col 29, row 0, row 15) are always walls — not listed here.
All coordinates are interior: cols 1-28, rows 1-14.

enemy_starts is a list of positions; EASY always uses only the first one,
HARD uses all of them (1 enemy for levels 1-3, 2 for 4-6, 3 for 7-9).
"""
from constants import COLS, ROWS, WALL_STONE, WALL_REINFORCED, WALL_WOODEN
from crafting import (MAT_ROCKS, MAT_PLANKS, MAT_METAL, MAT_CRYSTAL,
                      KEY_RED, KEY_BLUE)


def _hwall(x1, x2, y):
    return [(x, y) for x in range(x1, x2 + 1)]


def _vwall(x, y1, y2):
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
            _hwall(6, 23, 7),
        ),
    },

    # 3 ── H-shape: two verticals + horizontal with centre gap ─────────────────
    {
        'player_start':  (15, 4),
        'enemy_starts': [(2, 8)],
        'walls': _make_walls(
            _vwall(7,  3, 11),
            _vwall(22, 3, 11),
            _hwall(7,  13, 7),
            _hwall(16, 22, 7),
        ),
    },

    # 4 ── Short pillars + horizontal wall with gap ── 2 enemies ──────────────
    {
        'player_start':  (15, 4),
        'enemy_starts': [(2, 4),    # upper-left, above the crossbar
                         (27, 11)], # lower-right, below the crossbar
        'walls': _make_walls(
            _vwall(5,  2, 6),
            _vwall(24, 2, 6),
            _vwall(5,  9, 13),
            _vwall(24, 9, 13),
            _hwall(2,  13, 8),
            _hwall(16, 27, 8),
        ),
    },

    # 5 ── Cage with openings ── 2 enemies ─────────────────────────────────────
    {
        'player_start':  (15, 8),
        'enemy_starts': [(27, 8),   # right of cage
                         (2, 12)],  # lower-left
        'walls': _make_walls(
            _vwall(7,  3, 12),
            _vwall(22, 3, 12),
            _hwall(8,  21, 3),
            _hwall(8,  12, 12),
            _hwall(17, 21, 12),
        ),
    },

    # 6 ── Grid of pillars ── 2 enemies ────────────────────────────────────────
    {
        'player_start':  (28, 3),
        'enemy_starts': [(2, 8),    # left corridor
                         (3, 13)],  # bottom-left
        'walls': _make_walls(
            *[_vwall(c, 2, 6)  for c in (2, 7, 20, 25)],
            *[_vwall(c, 9, 13) for c in (2, 7, 20, 25)],
            *[_hwall(12, 17, r) for r in (2, 4, 6)],
            *[_hwall(12, 17, r) for r in (9, 11, 13)],
            *[_vwall(c, 2, 6)  for c in (4, 9, 22, 27)],
            *[_vwall(c, 9, 13) for c in (4, 9, 22, 27)],
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
            _hwall(2, 10, 2), _hwall(2, 10, 7),
            _vwall(2, 2, 7),  _vwall(10, 2, 7),
            # Vault B — upper-right, mirror of A (cols 19-27, rows 2-7)
            _hwall(19, 27, 2), _hwall(19, 27, 7),
            _vwall(19, 2, 7),  _vwall(27, 2, 7),
            # Vault C — lower-centre (cols 9-20, rows 9-13)
            _hwall(9, 20, 9),  _hwall(9, 20, 13),
            _vwall(9, 9, 13),  _vwall(20, 9, 13),
        ),
    },

    # 8 ── Alternating tall vertical walls (slalom) ── 3 enemies ──────────────
    {
        'player_start':  (27, 3),
        'enemy_starts': [(2, 12),   # bottom-left
                         (13, 2),   # top-centre (between slalom columns)
                         (23, 12)], # bottom-right (between cols 18 and 24)
        'walls': _make_walls(
            _vwall(6,  1, 11),
            _vwall(12, 4, 14),
            _vwall(18, 1, 11),
            _vwall(24, 4, 14),
        ),
    },

    # 9 ── Divided chambers ── 3 enemies (HARD) ───────────────────────────────
    {
        'player_start':  (15, 8),
        'enemy_starts': [(2, 8),    # left chamber, middle
                         (27, 8),   # right chamber, middle
                         (2, 13)],  # left chamber, bottom
        'walls': _make_walls(
            _vwall(14, 1, 5),
            _vwall(14, 10, 14),
            _vwall(15, 1, 5),
            _vwall(15, 10, 14),
            _hwall(2, 12,  5),
            _hwall(2, 12, 10),
            _hwall(17, 27,  5),
            _hwall(17, 27, 10),
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
        'crown_pos':     (14, 7),         # fixed position, not randomly spawned
        'walls': _make_walls(
            # Triple-layered central vault
            _hwall(9,  20,  2), _hwall(9,  20, 12),
            _vwall(9,   2, 12), _vwall(20,  2, 12),
            _hwall(11, 18,  4), _hwall(11, 18, 10),
            _vwall(11,  4, 10), _vwall(18,  4, 10),
            _hwall(13, 16,  6), _hwall(13, 16,  8),
            _vwall(13,  6,  8), _vwall(16,  6,  8),
            # Corner cavities (open toward centre)
            _vwall(4,  1,  4), _vwall(25,  1,  4),
            _vwall(4, 10, 14), _vwall(25, 10, 14),
            # Scattered single blocks
            [(7, 2)],  [(22, 2)],
            [(7, 13)], [(22, 13)],
            [(5, 5)],  [(24, 5)],
            [(5, 10)], [(6, 10)], [(23, 10)], [(24, 10)],
            [(7, 7)],  [(22, 7)],
            [(10, 14)], [(13, 13)], [(16, 14)], [(19, 13)],
        ),
    },
]


# ── Act 2 helpers ─────────────────────────────────────────────────────────────

def _typed_walls(*segments):
    """Build a dict {(col, row): wall_type} from (wall_type, positions) pairs."""
    walls = {}
    for wall_type, positions in segments:
        for pos in positions:
            c, r = pos
            if 1 <= c <= COLS - 2 and 1 <= r <= ROWS - 2:
                walls[(c, r)] = wall_type
    return walls

def _r(*args):
    """Shorthand for reinforced wall segments."""
    return (WALL_REINFORCED, _make_walls(*args))

def _s(*args):
    """Shorthand for stone wall segments."""
    return (WALL_STONE, _make_walls(*args))

def _w(*args):
    """Shorthand for wooden wall segments."""
    return (WALL_WOODEN, _make_walls(*args))


# ── Act 2 levels ──────────────────────────────────────────────────────────────

ACT2_LEVELS = [

    # 11 ── "The Passage" ── 2 rooms ──────────────────────────────────────────
    #
    # First Act 2 level. Two rooms connected by a right/left exit at row 7.
    # Reinforced walls form corridors and chambers. A patrol guard walks the
    # main corridor. Stone walls block a shortcut.
    {
        'start_room': 'hall',
        'player_start': (2, 3),
        'rooms': {
            'hall': {
                'walls': _typed_walls(
                    # Reinforced corridor walls
                    _r(_hwall(1, 28, 5)),             # horizontal divider
                    _r(_hwall(1, 28, 10)),            # lower divider
                    _r(_vwall(14, 1, 4)),             # upper pillar
                    _r(_vwall(14, 11, 14)),           # lower pillar
                    # Stone walls blocking shortcuts (breakable)
                    _s(_hwall(12, 16, 5)),            # gap in upper divider
                    _s(_vwall(14, 6, 9)),             # centre pillar (breakable)
                ),
                'enemy_starts': [(27, 8)],
                'patrol_enemies': [
                    {'start': (5, 8),
                     'waypoints': [(5, 8), (25, 8)]},
                ],
                'treasures': [
                    (4, 2, 5),     # gold ingot, upper-left
                    (22, 3, 1),    # coin, upper-right
                    (8, 12, 3),    # small gems, lower-left
                    (20, 13, 2),   # big diamond, lower-right
                ],
                'materials': [
                    (10, 3, MAT_ROCKS),
                    (18, 3, MAT_ROCKS),
                    (3, 8, MAT_ROCKS),
                    (26, 12, MAT_PLANKS),
                ],
                'exits': {'right_7': 'forge'},
            },
            'forge': {
                'walls': _typed_walls(
                    # Reinforced room structure
                    _r(_vwall(8, 1, 14)),             # left chamber wall
                    _r(_vwall(20, 1, 14)),            # right chamber wall
                    _r(_hwall(9, 19, 5)),             # upper cross wall
                    _r(_hwall(9, 19, 10)),            # lower cross wall
                    # Wooden barriers (easy to break through)
                    _w([(12, 5)]),                    # gap in upper cross
                    _w([(16, 10)]),                   # gap in lower cross
                ),
                'enemy_starts': [(14, 8)],
                'treasures': [
                    (14, 3, 4),    # trophy, centre upper chamber
                    (10, 8, 6),    # platinum ingot, middle
                    (18, 8, 7),    # necklace, middle
                    (14, 12, 9),   # emerald, centre lower chamber
                ],
                'materials': [
                    (12, 8, MAT_ROCKS),
                    (16, 8, MAT_ROCKS),
                    (10, 12, MAT_PLANKS),
                    (18, 3, MAT_PLANKS),
                ],
                'exits': {'left_7': 'hall'},
            },
        },
    },

    # 12 ── "The Gatehouse" ── 2 rooms ────────────────────────────────────────
    #
    # Locked doors and keys. The main room has a red-locked passage to a
    # treasure chamber; the red key is in the second room behind a blue door.
    # The blue key is in the main room. Teaches: find key → open door.
    {
        'start_room': 'gate',
        'player_start': (2, 7),
        'rooms': {
            'gate': {
                'walls': _typed_walls(
                    # Reinforced structure: two chambers divided by a thick wall
                    _r(_vwall(14, 1, 6)),
                    _r(_vwall(14, 9, 14)),
                    # Upper chamber walls
                    _r(_hwall(1, 13, 4)),
                    _r(_hwall(15, 28, 4)),
                    # Lower chamber walls
                    _r(_hwall(1, 13, 11)),
                    _r(_hwall(15, 28, 11)),
                    # Pillars
                    _r([(7, 7)]), _r([(7, 8)]),
                    _r([(21, 7)]), _r([(21, 8)]),
                ),
                'enemy_starts': [(12, 2), (20, 13)],
                'patrol_enemies': [
                    {'start': (4, 7),
                     'waypoints': [(4, 7), (4, 13)]},
                ],
                'treasures': [
                    (3, 2, 1),     # coin, upper-left
                    (10, 2, 2),    # diamond, upper area
                    (24, 13, 5),   # gold ingot, lower-right
                ],
                'materials': [
                    (6, 2, MAT_ROCKS),
                    (22, 2, MAT_ROCKS),
                    (6, 13, MAT_ROCKS),
                    (22, 13, MAT_PLANKS),
                ],
                'keys': [
                    (26, 2, KEY_BLUE),   # blue key in upper-right
                ],
                'locked_doors': [
                    (14, 7, KEY_RED),    # red door in centre divider
                ],
                'exits': {'right_7': 'vault'},
            },
            'vault': {
                'walls': _typed_walls(
                    # Reinforced vault structure (gap at 6,7 for blue door)
                    _r(_vwall(6, 1, 6)),
                    _r(_vwall(6, 8, 14)),
                    _r(_vwall(22, 1, 14)),
                    _r(_hwall(7, 21, 4)),
                    _r(_hwall(7, 21, 11)),
                    # Inner alcoves
                    _r(_vwall(12, 5, 10)),
                    _r(_vwall(16, 5, 10)),
                    # Wooden barriers inside
                    _w([(12, 7)]),
                    _w([(16, 8)]),
                ),
                'enemy_starts': [(14, 3)],
                'treasures': [
                    (14, 7, 4),    # trophy, inner vault
                    (14, 8, 8),    # lantern, inner vault
                    (9, 7, 3),     # small gems, side alcove
                    (19, 8, 6),    # platinum ingot, side alcove
                    (14, 13, 9),   # emerald, bottom
                ],
                'materials': [
                    (9, 3, MAT_ROCKS),
                    (19, 3, MAT_PLANKS),
                    (9, 12, MAT_METAL),
                    (19, 12, MAT_METAL),
                ],
                'keys': [
                    (14, 12, KEY_RED),   # red key in lower centre
                ],
                'locked_doors': [
                    (6, 7, KEY_BLUE),    # blue door on left vault wall
                ],
                'exits': {'left_7': 'gate'},
            },
        },
    },
]

LEVELS.extend(ACT2_LEVELS)
