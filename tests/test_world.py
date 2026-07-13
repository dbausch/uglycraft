"""Fine-grained World unit tests (spec 0046 S5) — pygame-free.

First tests written directly against the world.World API that spec 0045
created: no Game, no Surface, no harness.  State is asserted directly;
behaviour is asserted through the drained event stream.

The rule-attribute tests (spawn_mode / crafting / wrapped Act 1) are the
spec-0046 red-first set; the behaviour tests lock the unified path and
must stay green across the Stage 2 refactor.
"""
import random

import pytest

import world as world_mod
from world import World
from constants import WALL_STONE
from tests import act2_fixtures as fx

DIR_DOWN = (0, 1)
KEY = 42          # opaque key id for bump-consumption tracking


@pytest.fixture
def act1():
    """A pinned World on Act 1 level 2 (known wall row at r=7)."""
    random.seed(1234)
    w = World('easy')
    w.start_level(2)
    w.drain_events()
    return w


@pytest.fixture
def fixture_world():
    """A World running the door fixture, served via patched get_level."""
    orig_get, orig_regen = world_mod.get_level, world_mod.regenerate_level
    level = fx.door_level()
    world_mod.get_level = lambda n, progress=None: level
    world_mod.regenerate_level = lambda n: level
    try:
        random.seed(42)
        yield World('easy')
    finally:
        world_mod.get_level = orig_get
        world_mod.regenerate_level = orig_regen


def _kinds(events):
    return [e[0] for e in events]


# ── Spec 0046 rules: red until S1/S2 land ─────────────────────────────────────

def test_act1_is_wrapped_single_room(act1):
    """Act 1 dicts are wrapped as one-room multiroom levels; the room is
    keyed None so golden traces recording _current_room stay identical."""
    assert act1._current_room is None
    assert act1.spawn_mode == 'sequential'
    assert act1.crafting is False
    assert list(act1.cells.items_of_kind('treasure')) == []
    assert act1._level_data['start_room'] is None


def test_preplaced_defaults_for_act2_dicts(fixture_world):
    """Dicts that already have rooms carry no rule keys and get the Act 2
    defaults."""
    w = fixture_world
    assert w.spawn_mode == 'preplaced'
    assert w.crafting is True
    assert w._current_room == w._level_data['start_room']


# ── Behaviour locks: green before and after Stage 2 ───────────────────────────

def test_walk_emits_moved(act1):
    assert act1.try_move(*DIR_DOWN, KEY) is True
    assert _kinds(act1.drain_events()) == ['moved']


def test_bump_three_times_breaks_wall(act1):
    """Level 2: walk from (14,1) down to (14,6), then three bumps break
    the stone wall at (14,7).  A bump only counts after key release."""
    for _ in range(5):
        assert act1.try_move(*DIR_DOWN, KEY)
    act1.drain_events()
    assert (act1.player.col, act1.player.row) == (14, 6)
    assert act1.blocked(14, 7)

    events = []
    for _ in range(3):
        act1.try_move(*DIR_DOWN, KEY)
        act1.key_released(KEY)
        events += act1.drain_events()
    assert _kinds(events) == ['bumped', 'bumped', 'wall_broken']
    assert not act1.blocked(14, 7)
    assert act1._block_halves == 1

    assert act1.try_move(*DIR_DOWN, KEY)     # walk through the gap
    assert (act1.player.col, act1.player.row) == (14, 7)


def test_bump_consumed_until_key_release(act1):
    for _ in range(5):
        act1.try_move(*DIR_DOWN, KEY)
    act1.drain_events()
    act1.try_move(*DIR_DOWN, KEY)
    assert _kinds(act1.drain_events()) == ['bumped']
    act1.try_move(*DIR_DOWN, KEY)            # key never released
    assert act1.drain_events() == []
    assert act1.cells.barrier(14, 7).hits == 1


def test_place_block_costs_credit(act1):
    act1._block_credits = 1
    act1.player.col, act1.player.row = 14, 3   # off the respawn tile (spec 0067)
    c, r = act1.player.col, act1.player.row
    act1.place()
    assert _kinds(act1.drain_events()) == ['block_placed']
    assert act1._block_credits == 0
    assert act1.blocked(c, r) and act1.cells.barrier(c, r).kind == 'placed'

    act1.place()                              # no credit left, on a wall
    assert act1.drain_events() == []


def test_buy_shield_needs_score(act1):
    act1.score = 100
    act1.buy_shield()
    assert act1.drain_events() == [] and not act1.shield

    act1.score = 300
    act1.buy_shield()
    assert _kinds(act1.drain_events()) == ['shield_bought']
    assert act1.shield and act1.score == 50   # SHIELD_COST_PTS == 250


# ── Cell-model behaviour through the World API (spec 0047 T6) ─────────────────

def _fixture(make_level):
    """World running a hand-built level dict via patched get_level."""
    orig_get, orig_regen = world_mod.get_level, world_mod.regenerate_level
    world_mod.get_level = lambda n, progress=None: make_level()
    world_mod.regenerate_level = lambda n: make_level()
    try:
        random.seed(42)
        return World('easy'), (orig_get, orig_regen)
    finally:
        pass


def _restore(saved):
    world_mod.get_level, world_mod.regenerate_level = saved


def test_door_opens_with_key_through_query():
    w, saved = _fixture(fx.door_level)
    try:
        assert w.blocked(15, 8)                       # locked door blocks
        w.drain_events()
        w.inventory.add_key('red')
        w.player.col, w.player.row = 14, 8
        w.try_move(1, 0, KEY)                          # bump -> auto-open
        assert _kinds(w.drain_events()) == ['door_opened']
        assert w.cells.barrier(15, 8) is None
        assert not w.blocked(15, 8)
        assert not w.inventory.has_key('red')
    finally:
        _restore(saved)


def test_gate_follows_channel_state():
    w, saved = _fixture(fx.gate_level)
    try:
        assert w.blocked(15, 8)                        # gate closed
        w._channels.add('g1')
        assert not w.blocked(15, 8)                    # channel high -> open
        w._channels.clear()
        assert w.blocked(15, 8)
        assert w.cells.barrier(15, 8).kind == 'gate'   # barrier persists
    finally:
        _restore(saved)


def test_block_blocks_and_push_updates_query():
    w, saved = _fixture(fx.gate_level)
    try:
        block = w.room.blocks[0]
        bc, br = block.col, block.row
        assert w.blocked(bc, br)
        w.drain_events()
        w.player.col, w.player.row = bc + 1, br
        w.try_move(-1, 0, KEY)                         # push left
        assert _kinds(w.drain_events()) == ['bumped', 'moved']
        assert not w.blocked(bc, br)                   # vacated
        assert w.blocked(bc - 1, br)                   # new position blocks
    finally:
        _restore(saved)


def test_bridge_makes_water_passable():
    w, saved = _fixture(fx.water_level)
    try:
        water = next(iter(w.cells.water_tiles()))
        assert w.blocked(*water)
        w.cells.add_bridge(water)
        assert not w.blocked(*water)
        assert w.cells.is_water(*water)                # water is still there
    finally:
        _restore(saved)


# ── No bridge onto a plate's landing tile (spec 0049 P4) ──────────────────────

def _water_plate_level():
    """water_level plus a plate at (14,8) — the room-side landing tile of
    the bridge buildable at stream tile (15,8)."""
    level = fx.water_level()
    level['rooms']['main']['pressure_plates'] = [(14, 8, 'g1')]
    return level


def test_no_bridge_created_beside_a_plate():
    """Bumping a water tile whose landing tile carries a plate must not
    build a bridge (a solved puzzle must never seal a passage); a
    neighbouring stream tile with plate-free landings still works."""
    w, saved = _fixture(_water_plate_level)
    try:
        w.inventory.crafted['bridge'] = 1
        w.drain_events()
        w.player.col, w.player.row = 14, 8       # standing on the plate
        w.try_move(1, 0, KEY)                    # bump W(15,8) -> refused
        w.key_released(KEY)
        assert all(e[0] != 'bridge_built' for e in w.drain_events())
        assert w.blocked(15, 8)
        assert w.inventory.has_item('bridge')    # nothing consumed

        # Control: W(15,7) one tile up the same stream is not
        # plate-adjacent — the water room stays reachable.
        w.player.col, w.player.row = 14, 7
        w.try_move(1, 0, KEY)
        assert any(e[0] == 'bridge_built' for e in w.drain_events())
        assert not w.blocked(15, 7)
    finally:
        _restore(saved)


# ── Regeneration net demotion (spec 0048 U5, BL-36) ───────────────────────────

def _wedge_level():
    """Two grids; g1 has a pocket at (2,2) the player can wedge the
    (2,4) block into with two upward pushes from below."""
    g1 = fx._room({(1, 2): WALL_STONE, (3, 2): WALL_STONE, (2, 1): WALL_STONE},
                  pushable_blocks=[(2, 4)], exits={'right_8': 'g2'})
    g2 = fx._room({}, exits={'left_8': 'g1'})
    return fx._level({'g1': g1, 'g2': g2}, start='g1', player=(2, 7))


def _stuck_fresh_level():
    """g2's block is wedged from generation — the fresh-entry net must
    still catch this (the generator-bug last resort)."""
    g1 = fx._room({}, exits={'right_8': 'g2'})
    g2 = fx._room({(19, 2): WALL_STONE, (21, 2): WALL_STONE, (20, 1): WALL_STONE},
                  pushable_blocks=[(20, 2)], exits={'left_8': 'g1'})
    return fx._level({'g1': g1, 'g2': g2}, start='g1', player=(25, 8))


def _clean_level():
    g1 = fx._room({}, exits={'right_8': 'g2'})
    g2 = fx._room({}, exits={'left_8': 'g1'})
    return fx._level({'g1': g1, 'g2': g2}, start='g1', player=(25, 8))


def _cross(w, dcol, key):
    """Step onto the border exit tile and press once more to transition."""
    w.try_move(dcol, 0, key)
    w.key_released(key)
    w.try_move(dcol, 0, key)
    w.key_released(key)


def test_reentry_with_wedged_block_never_regenerates():
    """Player-wedged block + leave + return must NOT regenerate the level
    (BL-36 trigger (a)).  Red until _verify_blocks is fresh-entry-only."""
    orig = world_mod.get_level, world_mod.regenerate_level
    regen_calls = []
    world_mod.get_level = lambda n, progress=None: _wedge_level()
    world_mod.regenerate_level = lambda n: regen_calls.append(n) or _wedge_level()
    try:
        random.seed(1)
        w = World('easy')
        for _ in range(4):                       # walk up, push block twice
            w.try_move(0, -1, 1)
            w.key_released(1)
        assert w.room.block_positions() == [(2, 2)]  # wedged: 0 push dirs
        level_data = w._level_data

        w.player.col, w.player.row = 28, 8
        _cross(w, 1, 2)                          # g1 -> g2
        assert w._current_room == 'g2'
        w.drain_events()
        w.player.col, w.player.row = 1, 8
        _cross(w, -1, 3)                         # g2 -> back into g1
        events = w.drain_events()

        assert w._current_room == 'g1'
        assert not regen_calls                   # net did not fire
        assert w._level_data is level_data       # same level, same progress
        assert all(e[0] != 'level_started' for e in events)
        assert w.room.block_positions() == [(2, 2)]  # block stays wedged
    finally:
        world_mod.get_level, world_mod.regenerate_level = orig


def test_fresh_entry_stuck_block_regenerates_without_stale_teleport():
    """A generator-stuck block on FIRST entry still regenerates, but the
    player must end at the fresh level's start — not teleported to the
    stale entry tile of a level that no longer exists (BL-36 compound).
    Red until _try_room_transition detects the regeneration."""
    orig = world_mod.get_level, world_mod.regenerate_level
    state = {'regenerated': False}

    def get_level(n, progress=None):
        return _clean_level() if state['regenerated'] else _stuck_fresh_level()

    def regenerate(n):
        state['regenerated'] = True
        return _clean_level()

    world_mod.get_level = get_level
    world_mod.regenerate_level = regenerate
    try:
        random.seed(1)
        w = World('easy')
        w.player.col, w.player.row = 28, 8
        w.try_move(1, 0, 2)                      # step onto the exit tile
        w.key_released(2)
        w.drain_events()
        w.try_move(1, 0, 2)                      # off-grid press: stuck -> regen
        events = w.drain_events()

        assert state['regenerated']              # the net fired (last resort)
        assert ('level_started', 1) in events    # level restarted cleanly
        assert (w.player.col, w.player.row) == (25, 8)   # fresh player_start
        assert w._transition_timer == 0          # no flash into the new level
        assert all(e[0] != 'moved' for e in events)      # no phantom step
    finally:
        world_mod.get_level, world_mod.regenerate_level = orig


def test_refused_bridge_never_consumes_the_item():
    """BL-39 reproduction attempt (from kb/findings.md): with two crafted
    bridges, the second placement attempt on an already-bridged water
    room must be refused WITHOUT consuming the item.  Every refusal path
    in _try_auto_bridge returns before inventory.use_item — this test is
    the permanent guard for that ordering."""
    w, saved = _fixture(fx.water_level)
    try:
        w.inventory.crafted['bridge'] = 2
        w.drain_events()
        w.player.col, w.player.row = 14, 8
        w.try_move(1, 0, KEY)                    # bump W(15,8) -> builds
        w.key_released(KEY)
        assert any(e[0] == 'bridge_built' for e in w.drain_events())
        assert w.inventory.crafted['bridge'] == 1   # exactly one consumed

        w.player.col, w.player.row = 14, 7
        w.try_move(1, 0, KEY)                    # bump W(15,7): same water
        w.key_released(KEY)                      #   room -> refused
        assert all(e[0] != 'bridge_built' for e in w.drain_events())
        assert w.inventory.crafted['bridge'] == 1   # NOT consumed
        assert w.blocked(15, 7)                     # and nothing was built

        w.player.col, w.player.row = 14, 9
        w.try_move(1, 0, KEY)                    # third tile, same room
        w.key_released(KEY)
        assert w.inventory.crafted['bridge'] == 1   # still not consumed
    finally:
        _restore(saved)


# ── Auto-craft a bridge from planks on water-bump (spec 0072 D1, BL-28) ────────

def test_auto_bridge_crafts_from_planks():
    """Bumping water with 2 planks and no crafted bridge auto-crafts and
    places the bridge in one action (no crafting menu), consuming the planks."""
    w, saved = _fixture(fx.water_level)
    try:
        w.inventory.add_material('planks', 2)     # 2 planks, no crafted bridge
        assert not w.inventory.has_item('bridge')
        w.drain_events()
        w.player.col, w.player.row = 14, 8
        w.try_move(1, 0, KEY)                      # bump W(15,8)
        assert any(e[0] == 'bridge_built' for e in w.drain_events())
        assert not w.blocked(15, 8)               # water now passable
        assert w.inventory.materials['planks'] == 0   # both planks spent
    finally:
        _restore(saved)


def test_auto_bridge_spends_planks_before_crafted():
    """With both planks and a crafted bridge, raw planks are spent first
    (mirroring quick_place_block); the crafted bridge is untouched."""
    w, saved = _fixture(fx.water_level)
    try:
        w.inventory.crafted['bridge'] = 1
        w.inventory.add_material('planks', 2)
        w.drain_events()
        w.player.col, w.player.row = 14, 8
        w.try_move(1, 0, KEY)                      # bump W(15,8)
        assert any(e[0] == 'bridge_built' for e in w.drain_events())
        assert w.inventory.materials['planks'] == 0   # planks spent first
        assert w.inventory.crafted['bridge'] == 1     # crafted untouched
    finally:
        _restore(saved)


def test_auto_bridge_insufficient_planks_builds_nothing():
    """One plank and no crafted bridge is not enough: no bridge, no plank
    spent, and the water room stays un-bridged so it can be built later."""
    w, saved = _fixture(fx.water_level)
    try:
        w.inventory.add_material('planks', 1)     # one plank only
        w.drain_events()
        w.player.col, w.player.row = 14, 8
        w.try_move(1, 0, KEY)                      # bump W(15,8) -> refused
        w.key_released(KEY)
        assert all(e[0] != 'bridge_built' for e in w.drain_events())
        assert w.blocked(15, 8)                   # nothing built
        assert w.inventory.materials['planks'] == 1   # plank not spent
    finally:
        _restore(saved)


def test_auto_bridge_from_planks_respects_room_lock():
    """The one-bridge-per-water-room lock still holds when the source is
    planks: a second bump on the same stream builds nothing and spends no
    further planks (guard order unchanged)."""
    w, saved = _fixture(fx.water_level)
    try:
        w.inventory.add_material('planks', 4)     # enough for two bridges
        w.drain_events()
        w.player.col, w.player.row = 14, 8
        w.try_move(1, 0, KEY)                      # bump W(15,8) -> builds
        w.key_released(KEY)
        assert any(e[0] == 'bridge_built' for e in w.drain_events())
        assert w.inventory.materials['planks'] == 2

        w.player.col, w.player.row = 14, 7
        w.try_move(1, 0, KEY)                      # same room -> refused
        w.key_released(KEY)
        assert all(e[0] != 'bridge_built' for e in w.drain_events())
        assert w.inventory.materials['planks'] == 2   # no further planks spent
    finally:
        _restore(saved)
