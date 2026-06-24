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
    {
        'player_start':  (2, 7),
        'enemy_starts': [(27, 7)],
        'crown_pos':     (14, 7),
        'walls': _make_walls(
            _hwall(9,  20,  2), _hwall(9,  20, 12),
            _vwall(9,   2, 12), _vwall(20,  2, 12),
            _hwall(11, 18,  4), _hwall(11, 18, 10),
            _vwall(11,  4, 10), _vwall(18,  4, 10),
            _hwall(13, 16,  6), _hwall(13, 16,  8),
            _vwall(13,  6,  8), _vwall(16,  6,  8),
            _vwall(4,  1,  4), _vwall(25,  1,  4),
            _vwall(4, 10, 14), _vwall(25, 10, 14),
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
#
# DESIGN RULE: each 30×16 grid reads as a segment of a building floor plan.
# A hallway runs through the grid with rooms opening off it via doorways.
# Every reinforced divider has at least one doorway so all areas are reachable.

ACT2_LEVELS = [

    # 11 ── "The Passage" ── 2 grids ──────────────────────────────────────────
    #
    # Hall grid — a corridor with four rooms:
    #
    #   ┌─────────┬──────────────────┐
    #   │ Storage │    Workshop      │  rows 1-4
    #   │         │                  │
    #   ████D█████┴───────D██████████  row 5 — corridor north wall
    #   │                          →│
    #   │     C O R R I D O R     →│  rows 6-8
    #   │                          →│
    #   ████D██████████████████D█████  row 9 — corridor south wall
    #   │ Closet  ████│    Office   │  rows 10-14
    #   │         ████│             │
    #   └─────────────┴─────────────┘
    #
    # Forge grid — open forge hall with storage below:
    #
    #   ┌────────────────────────────┐
    #   │                            │  rows 1-8: open forge hall
    #   │     Forge Hall             │
    #   │        ██    ██            │  pillars at (10,4/6) and (18,4/6)
    #   │                            │
    #  ←│                            │  entry left at row 7
    #   ███D██████████████████D██████  row 9
    #   │ Alcove  │  WW  │  Supply  │  rows 10-14: three stores
    #   └─────────┴──────┴──────────┘
    {
        'start_room': 'hall',
        'player_start': (2, 7),
        'rooms': {
            'hall': {
                'walls': _typed_walls(
                    # Corridor north wall (row 5): doors at col 4 and col 17
                    _r(_hwall(1, 3, 5)),
                    _r(_hwall(5, 16, 5)),
                    _r(_hwall(18, 28, 5)),
                    # Corridor south wall (row 9): doors at col 5 and col 22
                    _r(_hwall(1, 4, 9)),
                    _r(_hwall(6, 21, 9)),
                    _r(_hwall(23, 28, 9)),
                    # Storage | Workshop divider
                    _r(_vwall(10, 1, 4)),
                    # Closet | Office divider
                    _r(_vwall(15, 9, 14)),
                    # Stone pillar in closet (breakable shortcut to office)
                    _s(_vwall(15, 11, 12)),
                ),
                'enemy_starts': [(25, 3)],
                'patrol_enemies': [
                    {'start': (3, 7),
                     'waypoints': [(3, 7), (26, 7)]},
                ],
                'treasures': [
                    (5, 2, 5),     # gold ingot in Storage
                    (16, 2, 1),    # coin in Workshop
                    (4, 12, 3),    # small gems in Closet
                    (22, 12, 2),   # big diamond in Office
                ],
                'materials': [
                    (3, 3, MAT_ROCKS),   # rocks in Storage
                    (7, 2, MAT_ROCKS),   # rocks in Storage
                    (20, 3, MAT_ROCKS),  # rocks in Workshop
                    (26, 11, MAT_PLANKS),# planks in Office
                ],
                'exits': {'right_7': 'forge'},
            },
            'forge': {
                'walls': _typed_walls(
                    # South wall (row 9): doors at col 5 and col 22
                    _r(_hwall(1, 4, 9)),
                    _r(_hwall(6, 21, 9)),
                    _r(_hwall(23, 28, 9)),
                    # Forge pillars (decorative structure)
                    _r([(10, 4)]), _r([(10, 6)]),
                    _r([(18, 4)]), _r([(18, 6)]),
                    # Alcove | centre store | Supply dividers
                    _r(_vwall(10, 9, 14)),
                    _r(_vwall(19, 9, 14)),
                    # Wooden barriers guarding centre store
                    _w([(13, 9)]),
                    _w([(16, 9)]),
                ),
                'enemy_starts': [(14, 3)],
                'treasures': [
                    (14, 2, 4),    # trophy in Forge Hall
                    (4, 12, 6),    # platinum in Alcove
                    (14, 12, 7),   # necklace in centre store
                    (24, 11, 9),   # emerald in Supply
                ],
                'materials': [
                    (6, 5, MAT_ROCKS),
                    (22, 5, MAT_ROCKS),
                    (4, 11, MAT_PLANKS),
                    (24, 12, MAT_PLANKS),
                ],
                'exits': {'left_7': 'hall'},
            },
        },
    },

    # 12 ── "The Gatehouse" ── 2 grids ────────────────────────────────────────
    #
    # Gate grid — a corridor with a locked red door and side rooms:
    #
    #   ┌──────────┬─────────────────┐
    #   │ Guard    │  Secure Wing    │  rows 1-4
    #   │ Room     │  (red-locked)   │
    #   ████D██████RD████████████████  row 5 — door at col 5, red door at col 11
    #   │                          →│
    #   │     C O R R I D O R     →│  rows 6-8
    #   │                          →│
    #   ████D██████████D█████████████  row 9 — doors at col 4 and col 16
    #   │ Key Room │   Armoury      │  rows 10-14
    #   │ (blue)   │                │
    #   └──────────┴────────────────┘
    #
    # Vault grid — one large vault with nooks on the right:
    #
    #   ┌──────────────────────┬─────┐
    #   │                      │Nook │  rows 1-4
    #   │   Grand Vault        D     │
    #   │                      ██████  row 5 — nook shelf
    #  ←│                            │
    #  ←│                      BD    │  blue door at col 22 (entry to nooks)
    #  ←│                            │
    #   │                      ██████  row 10 — nook shelf
    #   │   (red key here)     D     │
    #   │                      │Nook │  rows 11-14
    #   └──────────────────────┴─────┘
    {
        'start_room': 'gate',
        'player_start': (2, 7),
        'rooms': {
            'gate': {
                'walls': _typed_walls(
                    # Corridor north wall (row 5): door at col 5
                    _r(_hwall(1, 4, 5)),
                    _r(_hwall(6, 10, 5)),
                    # gap at col 11 for red door
                    _r(_hwall(12, 28, 5)),
                    # Corridor south wall (row 9): doors at col 4 and col 16
                    _r(_hwall(1, 3, 9)),
                    _r(_hwall(5, 15, 9)),
                    _r(_hwall(17, 28, 9)),
                    # Guard Room | Secure Wing divider (gap at row 4 for door access)
                    _r(_vwall(11, 1, 3)),
                    # Key Room | Armoury divider with door at row 11
                    _r(_vwall(11, 9, 10)),
                    _r(_vwall(11, 12, 14)),
                ),
                'enemy_starts': [(20, 3), (20, 12)],
                'patrol_enemies': [
                    {'start': (3, 7),
                     'waypoints': [(3, 7), (26, 7)]},
                ],
                'treasures': [
                    (3, 2, 1),     # coin in Guard Room
                    (18, 2, 2),    # diamond in Secure Wing
                    (18, 12, 5),   # gold ingot in Armoury
                ],
                'materials': [
                    (7, 2, MAT_ROCKS),
                    (24, 3, MAT_ROCKS),
                    (5, 12, MAT_ROCKS),
                    (24, 12, MAT_PLANKS),
                ],
                'keys': [
                    (3, 12, KEY_BLUE),
                ],
                'locked_doors': [
                    (11, 5, KEY_RED),    # red door in corridor north wall
                ],
                'exits': {'right_7': 'vault'},
            },
            'vault': {
                'walls': _typed_walls(
                    # East nook walls
                    _r(_vwall(22, 1, 3)),   # upper nook west wall
                    _r(_hwall(24, 28, 5)),  # upper nook floor (door at col 23)
                    _r(_vwall(22, 5, 6)),   # wall segment
                    # gap at (22, 7) for blue door
                    _r(_vwall(22, 8, 9)),   # wall segment
                    _r(_hwall(24, 28, 10)), # lower nook ceiling (door at col 23)
                    _r(_vwall(22, 11, 14)), # lower nook west wall
                ),
                'enemy_starts': [(10, 4)],
                'treasures': [
                    (10, 3, 4),    # trophy in Grand Vault
                    (10, 7, 8),    # lantern in Grand Vault
                    (25, 3, 3),    # small gems in upper nook
                    (25, 12, 6),   # platinum in lower nook
                    (10, 12, 9),   # emerald in Grand Vault
                ],
                'materials': [
                    (4, 3, MAT_ROCKS),
                    (4, 12, MAT_PLANKS),
                    (25, 7, MAT_METAL),
                    (18, 11, MAT_METAL),
                ],
                'keys': [
                    (14, 11, KEY_RED),
                ],
                'locked_doors': [
                    (22, 7, KEY_BLUE),
                ],
                'exits': {'left_7': 'gate'},
            },
        },
    },

    # 13 ── "The Mechanism" ── 2 grids ───────────────────────────────────────
    #
    # Entry grid — corridor with workshop above and machine room below,
    # each containing a gate that blocks a treasure side-room:
    #
    #   ┌───────────┬G┬──────────────┐
    #   │ Workshop  │ │ Treasure A   │  rows 1-4
    #   │ (blocks)  │ │  (gate_a)    │
    #   ████D███████┘ └██████████████  row 5 — door at col 5
    #   │                          →│
    #   │     C O R R I D O R     →│  rows 6-9
    #   │                          →│
    #   │                          →│
    #   ████D███████┐ ┌██████████████  row 10 — door at col 5
    #   │ Machine   │ │ Vault B      │  rows 11-14
    #   │ (plates)  │ │  (gate_b)    │
    #   └───────────┴G┴──────────────┘
    #
    # Puzzle grid — open area with nooks and a gated lower chamber:
    #
    #   ┌──────┬─────────────┬──────┐
    #   │ Nook │  Upper Hall │ Nook │  rows 1-4
    #   │      D             D      │
    #   │      ██████████████       │  row 5 — inner wall
    #  ←│                           │
    #  ←│   Open Area (blocks)      │  rows 6-9
    #  ←│                           │
    #   │      ██████████████       │  row 10 — inner wall
    #   │      D  Lower     D      │
    #   │ Nook │  G (gate_c)│ Nook │  rows 11-14
    #   └──────┴─────────────┴──────┘
    {
        'start_room': 'entry',
        'player_start': (2, 7),
        'rooms': {
            'entry': {
                'walls': _typed_walls(
                    # Corridor walls: row 5 (door at col 5) and row 10 (door at col 5)
                    _r(_hwall(1, 4, 5)),
                    _r(_hwall(6, 12, 5)),
                    # gap at 13 for gate_a column
                    _r(_hwall(15, 28, 5)),
                    _r(_hwall(1, 4, 10)),
                    _r(_hwall(6, 12, 10)),
                    # gap at 13 for gate_b column
                    _r(_hwall(15, 28, 10)),
                    # Workshop | Treasure A divider (single wall, gate at row 3)
                    _r(_vwall(13, 1, 2)),
                    _r(_vwall(13, 4, 5)),
                    # Machine | Vault B divider (single wall, gate at row 12)
                    _r(_vwall(13, 10, 11)),
                    _r(_vwall(13, 13, 14)),
                ),
                'enemy_starts': [(26, 7), (26, 13)],
                'treasures': [
                    (4, 2, 1),     # coin in Workshop
                    (20, 2, 4),    # trophy in Treasure A (behind gate)
                    (4, 13, 2),    # diamond in Machine Room
                    (20, 13, 5),   # gold ingot in Vault B (behind gate)
                ],
                'materials': [
                    (8, 7, MAT_ROCKS),
                    (12, 8, MAT_ROCKS),
                    (20, 7, MAT_ROCKS),
                ],
                'pushable_blocks': [
                    (7, 3), (10, 3),
                    (7, 12), (10, 12),
                ],
                'pressure_plates': [
                    (12, 2, 'gate_a'),
                    (12, 13, 'gate_b'),
                ],
                'gates': [
                    (13, 3, 'gate_a'),
                    (13, 12, 'gate_b'),
                ],
                'exits': {'right_7': 'puzzle'},
            },
            'puzzle': {
                'walls': _typed_walls(
                    # Nook walls: small side rooms with doors at row 4/11
                    _r(_vwall(6, 1, 3)),
                    _r(_vwall(6, 5, 5)),
                    _r(_vwall(22, 1, 3)),
                    _r(_vwall(22, 5, 5)),
                    _r(_vwall(6, 10, 10)),
                    _r(_vwall(6, 12, 14)),
                    _r(_vwall(22, 10, 10)),
                    _r(_vwall(22, 12, 14)),
                    # Inner walls forming upper/lower halls
                    _r(_hwall(7, 21, 5)),
                    _r(_hwall(7, 21, 10)),
                    # Lower hall divider with gate at row 11
                    _r(_vwall(14, 10, 10)),
                    _r(_vwall(14, 13, 14)),
                ),
                'enemy_starts': [(14, 2)],
                'patrol_enemies': [
                    {'start': (10, 7),
                     'waypoints': [(10, 7), (18, 7)]},
                ],
                'treasures': [
                    (3, 2, 7),     # necklace in left upper nook
                    (25, 2, 3),    # small gems in right upper nook
                    (14, 7, 6),    # platinum in open area (risky!)
                    (14, 12, 9),   # emerald behind gate_c
                ],
                'materials': [
                    (3, 12, MAT_PLANKS),
                    (25, 12, MAT_PLANKS),
                    (14, 3, MAT_METAL),
                ],
                'pushable_blocks': [
                    (12, 7), (16, 7),
                ],
                'pressure_plates': [
                    (14, 8, 'gate_c'),
                ],
                'gates': [
                    (14, 11, 'gate_c'),
                ],
                'exits': {'left_7': 'entry'},
            },
        },
    },
]

LEVELS.extend(ACT2_LEVELS)
