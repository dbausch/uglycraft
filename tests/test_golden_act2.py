"""Golden characterization traces for Act 2 mechanics (spec 0044 H6).

One hand-written fixture level per mechanic (tests/act2_fixtures.py) plus
two seeded generator levels as integration traces.
"""
from tests import act2_fixtures as fx
from tests.harness import Harness, assert_golden


def _sound_keys(trace):
    return [key for _, key in trace['sounds']]


def test_door_key():
    """Collect key, bump door (auto-open), collect treasure -> entrance opens.

    Spec 0066: collecting the last award opens the exit (entrance_open)
    rather than advancing instantly; the level ends only by walking out."""
    with Harness(level_dict=fx.door_level(), seed=42) as h:
        trace = h.run(['hold:left:40', 'hold:right:95', 'wait:10'])
    keys = _sound_keys(trace)
    assert keys.count('collect') == 2       # key + treasure
    assert 'break' in keys                  # door opened
    assert 'entrance_open' in keys          # all loot -> entrance opens
    assert_golden('act2_door', trace)


def test_gate_plate_block():
    """Push a block (it overshoots the plate to (3,8), leaving the gate
    closed); then die.  Spec 0068: death no longer resets blocks or the gate —
    the block stays where it was pushed and the player returns to start."""
    with Harness(level_dict=fx.gate_level(), seed=42) as h:
        h.run(['hold:left:12',
               'key:left', 'wait:3', 'key:left', 'wait:3',   # walk to block
               'key:left', 'wait:3', 'key:left', 'wait:3',   # push it left
               'hold:right:60', 'wait:5'])
        # death phase: force a catch
        e = h.game.enemies[0]
        e.col, e.row = h.game.player.col - 1, h.game.player.row
        trace = h.run(['key:left', 'wait:10'])
    keys = _sound_keys(trace)
    assert 'caught' in keys
    # death does NOT reset the block (spec 0068): it stays where it was pushed
    assert h.game.room.block_positions() == [(3, 8)]
    # the plate is unpressed, so the gate is closed via the latch, not a reset
    assert not h.game.world._channels
    assert_golden('act2_gate', trace)


def test_water_bridge():
    """Collect 2 planks, craft a bridge in the inventory (TAB), bump the
    stream -> auto-bridge, cross, collect treasure -> entrance opens.

    Spec 0066: the last award opens the exit (entrance_open) instead of
    advancing on pickup."""
    with Harness(level_dict=fx.water_level(), seed=42) as h:
        trace = h.run([
            'hold:left:40',                  # collect both planks
            'key:tab', 'wait:2',             # open inventory
            'key:down', 'wait:2',            # cursor -> Bridge recipe
            'key:return', 'wait:2',          # craft
            'key:tab', 'wait:2',             # close inventory
            'hold:right:100', 'wait:10'])    # bump water, cross, treasure
    keys = _sound_keys(trace)
    assert 'credit' in keys                  # craft success sound
    assert 'place_block' in keys              # bridge built
    assert 'entrance_open' in keys           # last treasure -> entrance opens
    assert_golden('act2_water', trace)


def test_flame_jet():
    """Walking into the jet during the on-phase costs a life; with the
    shield the same walk is survived."""
    with Harness(level_dict=fx.flame_level(), seed=42) as h:
        h.run(['hold:down:24', 'wait:5'])    # into the flames -> caught
        assert h.game.lives == 8
        h.game.player.col, h.game.player.row = 18, 4
        h.game.world.shield = True
        h.game.world._shield_timer = 30_000
        trace = h.run(['hold:down:24', 'wait:5'])    # shielded walk
    keys = _sound_keys(trace)
    assert keys.count('caught') == 1
    assert h.game.lives == 8                 # shield prevented second loss
    assert_golden('act2_flames', trace)


def test_room_transition_persistence():
    """Cross the border exit, break a wooden wall in g2, leave, return:
    the wall stays broken (room persists by identity)."""
    def steps(direction, n):
        return [f'key:{direction}', 'wait:2'] * n

    with Harness(level_dict=fx.transition_level(), seed=42) as h:
        trace = h.run(
            steps('right', 4)        # (25,8) -> (29,8) exit tile
            + steps('right', 1)      # off-grid press: g1 -> g2, land (0,8)
            + steps('right', 19)     # to (19,8), facing the wooden wall
            + steps('right', 2)      # 2 bumps -> break (wooden)
            + steps('right', 3)      # walk through the gap to (22,8)
            + steps('left', 22)      # back to (0,8)
            + steps('left', 1)       # off-grid press: g2 -> g1, land (29,8)
            + steps('right', 1)      # straight back to g2, land (0,8)
            + steps('right', 21)     # through the PERSISTED gap to (21,8)
            + ['wait:5'])
    keys = _sound_keys(trace)
    assert keys.count('break') == 1
    rooms = {t[6] for t in trace['ticks']}
    assert rooms == {'g1', 'g2'}
    assert h.game._current_room == 'g2'
    assert h.game.player.col == 21           # walked through the broken wall
    assert_golden('act2_transition', trace)


def test_forge_ogre_breaks_placed_block():
    """Seal the ogre pocket with a placed stone wall; the ogre breaks it
    in 2 hits (block_bump_power)."""
    with Harness(level_dict=fx.forge_level(), seed=42) as h:
        h.game.inventory.add_material('rocks', 3)
        trace = h.run(['key:left', 'wait:2',     # step to (10,8)
                       'key:space', 'wait:2',    # quick-place wall there
                       'hold:right:10',          # retreat
                       'wait:60'])               # ogre hits twice -> break
    keys = _sound_keys(trace)
    assert 'place_block' in keys
    assert 'break' in keys                   # ogre destroyed the wall
    assert not list(h.game.cells.barriers('placed'))
    assert_golden('act2_forge', trace)


def test_patrol_guard():
    """Patrol enemy loops its waypoints while the player idles."""
    with Harness(level_dict=fx.patrol_level(), seed=42) as h:
        trace = h.run(['wait:80'])
    positions = {tuple(t[7][0]) for t in trace['ticks']}
    assert len(positions) > 4                # it moved along the route
    assert_golden('act2_patrol', trace)


def test_generated_level_11():
    """Seeded generator level 11: fixed walk, integration trace."""
    with Harness(level=11, seed=777) as h:
        trace = h.run(['hold:right:12', 'hold:down:10', 'hold:left:20',
                       'hold:up:8', 'wait:10'])
    assert_golden('act2_L11_walk', trace)


def test_generated_level_13():
    """Seeded generator level 13: fixed walk, integration trace."""
    with Harness(level=13, seed=777) as h:
        trace = h.run(['hold:right:12', 'hold:down:10', 'hold:left:20',
                       'hold:up:8', 'wait:10'])
    assert_golden('act2_L13_walk', trace)
