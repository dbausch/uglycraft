"""Render-path tests: smoke + golden screenshots (spec 0044 H7/H8).

Screenshot goldens are the deliberately fragile tier (spec 0044): pixel
hashes recorded on this machine (font rasterisation may differ across
freetype/SDL versions). Re-record with UGLYCRAFT_REGOLD=1 after any
intentional visual change; drop or reduce these if they cost more than
they catch.
"""
from game import Game
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


def _keys_level(colours):
    """Showcase fixture with the given key colours placed on left-room floor."""
    lvl = fx.showcase_level()
    lvl['rooms']['main']['keys'] = [(5, 8 - 2 * i, c) for i, c in enumerate(colours)]
    return lvl


# NOTE: the inventory/crafting overlay is disabled in the tester build
# (spec 0073 D5, ENABLE_INVENTORY_MENU=False), so there is no inventory
# screenshot golden. See tests/test_tester_gating.py for the TAB-disabled test.


def test_shot_hud_keys():
    """HUD key strip: one slot per key colour in the level, lit when held and
    ghosted when not (spec 0071 D3). Level has red/green/purple/cyan; the
    player holds red+green, so purple+cyan render ghosted."""
    lvl = _keys_level(('red', 'green', 'purple', 'cyan'))
    with Harness(level_dict=lvl, seed=1234) as h:
        for c in ('red', 'green'):
            h.game.inventory.add_key(c)
        h.run(['wait:3'])
        _shot('hud_keys', h)


def test_hud_key_strip_per_level_fixed_width():
    """The strip reserves one slot per key colour PRESENT IN THE LEVEL, and
    that width is constant no matter how many are held — no reflow during play
    (spec 0071 D3, refined)."""
    with Harness(level_dict=_keys_level(('red', 'green', 'purple')), seed=1234) as h:
        expect = Game._KEY_SLOT * 3
        assert h.game._level_key_colours == ['red', 'green', 'purple']
        assert h.game._key_strip_element().width == expect        # 0 held
        h.game.inventory.add_key('green')
        assert h.game._key_strip_element().width == expect        # 1 held
        for c in ('red', 'purple'):
            h.game.inventory.add_key(c)
        assert h.game._key_strip_element().width == expect        # all held


def test_hud_key_strip_absent_without_keys():
    """A level with no keys hides the strip entirely, so its HUD space is
    redistributed (spec 0071 D3, refined). Act 1 levels have no keys."""
    with Harness(level=3, seed=1234) as h:
        assert h.game._level_key_colours == []
        assert h.game._key_strip_element() is None


# ── Spec 0072 D2: HUD BRIDGE counter (planks levels only) ─────────────────────

def _hud_labels(h):
    """The label:value texts rendered into the HUD element list this frame."""
    import game as game_mod
    captured = []
    orig = game_mod.LabelValue

    def spy(font, label, value="", color=None, **kw):
        captured.append(label)
        return orig(font, label, value, color, **kw)

    game_mod.LabelValue = spy
    try:
        h.game._render_hud()
    finally:
        game_mod.LabelValue = orig
    return captured


def test_hud_bridge_counter_present_on_planks_level():
    """A level with planks exposes _level_has_planks and renders a BRIDGES
    element immediately left of BLOCKS (spec 0072 D2)."""
    with Harness(level_dict=fx.water_level(), seed=42) as h:
        assert h.game._level_has_planks is True
        labels = _hud_labels(h)
        assert 'BRIDGES' in labels
        assert labels.index('BRIDGES') == labels.index('BLOCKS') - 1


def test_hud_bridge_counter_absent_without_planks():
    """A plankless level (Act 1) sets _level_has_planks False and renders no
    BRIDGES element, so the HBox redistributes the space (spec 0072 D2)."""
    with Harness(level=3, seed=1234) as h:
        assert h.game._level_has_planks is False
        assert 'BRIDGES' not in _hud_labels(h)


def test_shot_hud_bridge():
    """HUD over a planks level with 1 bridge credit and a banked half: the
    BRIDGES counter reads "BRIDGES  1" + a drawn half-block, left of BLOCKS,
    with the gap bands dividing the row (spec 0072/0073)."""
    with Harness(level_dict=fx.water_level(), seed=42) as h:
        h.game.world._bridge_credits = 1
        h.game.world._bridge_halves = 1
        h.run(['wait:3'])
        _shot('hud_bridge', h)


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


# ── Spec 0059: overlay screenshot goldens ─────────────────────────────────────
# The four unchanged overlays were recorded BEFORE the box-fit
# implementation: their passing afterwards machine-proves the 420 px
# minimum keeps them pixel-identical (replaces manual acceptance).
# shot_overlay_win is recorded after — the message changes by design.

def _overlay_shot(name, state, final_score=None):
    with Harness(level=3, seed=1234) as h:
        h.run(['wait:3'])
        if final_score is not None:
            h.game.world._final_score = final_score
            h.game.world._final_level = 20
        h.game.state = state
        _shot(name, h)


def test_shot_overlay_intro():
    _overlay_shot('overlay_intro', 'level_intro')


def test_shot_overlay_pause():
    _overlay_shot('overlay_pause', 'paused')


def test_shot_overlay_game_over():
    _overlay_shot('overlay_game_over', 'game_over')


def test_shot_overlay_play_again():
    _overlay_shot('overlay_play_again', 'play_again')


def test_shot_overlay_win():
    """YOU  WON! centred in its box with the score sub-line (spec 0059)."""
    _overlay_shot('overlay_win', 'win', final_score=12345)
