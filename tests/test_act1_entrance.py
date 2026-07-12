"""Act 1 entrance doors at fixed per-level positions (spec 0064 / BL-42).

Every Act 1 level dict carries an `entrance` border tile with the player
start directly inside it, and enemies repositioned per the spec table
(centre row 7 / centre col 14; player and enemies border-adjacent).
"""
import pytest

from constants import COLS, ROWS
from levels import LEVELS
from world import _as_multiroom

# spec 0064 table: level -> (entrance, player_start, enemy_starts in order)
EXPECTED = {
    1:  ((29, 7),  (28, 7),  [(1, 7)]),
    2:  ((14, 0),  (14, 1),  [(14, 14)]),
    3:  ((29, 7),  (28, 7),  [(1, 7)]),
    4:  ((14, 0),  (14, 1),  [(1, 14), (28, 14)]),
    5:  ((14, 15), (14, 14), [(1, 1), (28, 1)]),
    6:  ((29, 7),  (28, 7),  [(1, 1), (1, 14)]),
    7:  ((14, 0),  (14, 1),  [(1, 7), (28, 7), (14, 14)]),
    8:  ((29, 7),  (28, 7),  [(1, 7), (14, 1), (14, 14)]),
    9:  ((29, 7),  (28, 7),  [(1, 1), (1, 7), (1, 14)]),
    10: ((0, 7),   (1, 7),   [(28, 7)]),
}

LEVEL_NUMS = sorted(EXPECTED)


def _on_border(c, r):
    return c in (0, COLS - 1) or r in (0, ROWS - 1)


def _interior(c, r):
    return 1 <= c <= COLS - 2 and 1 <= r <= ROWS - 2


@pytest.mark.parametrize('level', LEVEL_NUMS)
def test_positions_pinned(level):
    """Entrance, player start, and enemy starts equal the spec 0064 table."""
    lvl = LEVELS[level - 1]
    entrance, start, enemies = EXPECTED[level]
    assert lvl.get('entrance') == entrance
    assert tuple(lvl['player_start']) == start
    assert [tuple(e[:2]) for e in lvl['enemy_starts']] == enemies


@pytest.mark.parametrize('level', LEVEL_NUMS)
def test_invariants(level):
    """Entrance on the border ring, start directly inside it, everyone on
    interior floor tiles, no enemy on the player start."""
    lvl = LEVELS[level - 1]
    ec, er = lvl['entrance']
    pc, pr = lvl['player_start']
    assert _on_border(ec, er)
    assert abs(ec - pc) + abs(er - pr) == 1
    assert _interior(pc, pr)
    assert (pc, pr) not in lvl['walls']
    for e in lvl['enemy_starts']:
        c, r = e[0], e[1]
        assert _interior(c, r)
        assert (c, r) not in lvl['walls']
        assert (c, r) != (pc, pr)


@pytest.mark.parametrize('level', LEVEL_NUMS)
def test_as_multiroom_forwards_entrance(level):
    """The Act 1 wrapper must forward `entrance` into the single room dict,
    or the render path (game.py) never sees it."""
    data = _as_multiroom(LEVELS[level - 1])
    assert data['rooms'][None].get('entrance') == EXPECTED[level][0]
