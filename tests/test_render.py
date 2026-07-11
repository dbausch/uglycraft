"""Render-path tests: smoke + golden screenshots (spec 0044 H7/H8).

Screenshot goldens are the deliberately fragile tier (spec 0044): pixel
hashes recorded on this machine (font rasterisation may differ across
freetype/SDL versions). Re-record with UGLYCRAFT_REGOLD=1 after any
intentional visual change; drop or reduce these if they cost more than
they catch.
"""
from tests import act2_fixtures as fx
from tests.harness import Harness, assert_golden, screen_hash


def _shot(name, h):
    assert_golden(f'shot_{name}', {'sha256': screen_hash(h)})


def test_act1_render_smoke():
    """Rendering an Act 1 playing field must not raise.

    Red when written: _render_field reads self._current_room_data
    unconditionally (game.py:1230), which is only assigned on the Act 2
    path -> AttributeError on every Act 1 render (BL-33, regression from
    04be23e).
    """
    with Harness(level=1, seed=1234) as h:
        h.run(['wait:3'])
        h.game.render()


def test_shot_title():
    with Harness(level=1, seed=1234) as h:
        h.game.state = 'title'
        h.run(['wait:3'])
        _shot('title', h)


def test_shot_difficulty():
    with Harness(level=1, seed=1234) as h:
        h.game.state = 'difficulty'
        _shot('difficulty', h)


def test_shot_act1_field():
    """Level 3 playing field + HUD (walls, treasure, enemy, player)."""
    with Harness(level=3, seed=1234) as h:
        h.run(['wait:3'])
        _shot('act1_field', h)


def test_shot_boss_field():
    """Level 10: vault rings, boss animation frame pinned by now()."""
    with Harness(level=10, seed=1234) as h:
        h.run(['wait:3'])
        _shot('boss_field', h)


def test_shot_act2_field():
    """Showcase fixture: door, gate, plate, block, water in one frame."""
    with Harness(level_dict=fx.showcase_level(), seed=42) as h:
        h.run(['wait:3'])
        _shot('act2_field', h)


def test_shot_inventory():
    """Inventory/crafting screen over the showcase fixture."""
    with Harness(level_dict=fx.showcase_level(), seed=42) as h:
        h.run(['wait:2', 'key:tab', 'wait:2'])
        _shot('inventory', h)


# ── Spec 0056 (BL-12): border-exit sprite selection ──────────────────────────
# Pure helper: (record, orient, open_channels, opened_doors) -> sprite key or
# None.  Stairs are reserved for inter-floor travel — a same-floor border exit
# never maps to 'staircase'; open borders draw nothing (bare floor gap).

def test_border_sprite_open_draws_nothing():
    from game import border_exit_sprite
    for o in ('h', 'v'):
        assert border_exit_sprite(None, o, set(), set()) is None
        assert border_exit_sprite(('open', None, None), o, set(), set()) is None


def test_border_sprite_locked_closed():
    from game import border_exit_sprite
    home = ('grid_1_0', (29, 8))
    assert border_exit_sprite(('locked', 'red', home), 'h',
                              set(), set()) == 'door_red_h'
    assert border_exit_sprite(('locked', 'blue', home), 'v',
                              set(), set()) == 'door_blue_v'


def test_border_sprite_locked_opened():
    from game import border_exit_sprite
    home = ('grid_1_0', (29, 8))
    opened = {('grid_1_0', 29, 8, 'red')}
    assert border_exit_sprite(('locked', 'red', home), 'h',
                              set(), opened) == 'door_open_h'
    assert border_exit_sprite(('locked', 'red', home), 'v',
                              set(), opened) == 'door_open_v'
    # an opened same-colour door elsewhere is not this door
    other_home = ('grid_2_0', (0, 8))
    assert border_exit_sprite(('locked', 'red', other_home), 'h',
                              set(), opened) == 'door_red_h'


def test_border_sprite_gated_tracks_channel():
    from game import border_exit_sprite
    rec = ('gated', 'border_gate_0', None)
    assert border_exit_sprite(rec, 'h', set(), set()) == 'gate_closed_h'
    assert border_exit_sprite(rec, 'v', {'border_gate_0'}, set()) == 'gate_open_v'
    assert border_exit_sprite(rec, 'h', {'some_other_gate'}, set()) == 'gate_closed_h'
