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
    assert act1._room_treasures == {None: []}
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
    """Level 2: walk from (15,3) down to (15,6), then three bumps break
    the stone wall at (15,7).  A bump only counts after key release."""
    for _ in range(3):
        assert act1.try_move(*DIR_DOWN, KEY)
    act1.drain_events()
    assert (act1.player.col, act1.player.row) == (15, 6)
    assert act1.blocked(15, 7)

    events = []
    for _ in range(3):
        act1.try_move(*DIR_DOWN, KEY)
        act1.key_released(KEY)
        events += act1.drain_events()
    assert _kinds(events) == ['bumped', 'bumped', 'wall_broken']
    assert not act1.blocked(15, 7)
    assert act1._breaks_toward_credit == 1

    assert act1.try_move(*DIR_DOWN, KEY)     # walk through the gap
    assert (act1.player.col, act1.player.row) == (15, 7)


def test_bump_consumed_until_key_release(act1):
    for _ in range(3):
        act1.try_move(*DIR_DOWN, KEY)
    act1.drain_events()
    act1.try_move(*DIR_DOWN, KEY)
    assert _kinds(act1.drain_events()) == ['bumped']
    act1.try_move(*DIR_DOWN, KEY)            # key never released
    assert act1.drain_events() == []
    assert act1.cells.barrier(15, 7).hits == 1


def test_place_wall_costs_credit(act1):
    act1._place_credits = 1
    c, r = act1.player.col, act1.player.row
    act1.place()
    assert _kinds(act1.drain_events()) == ['wall_placed']
    assert act1._place_credits == 0
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


def test_gate_follows_gate_open_state():
    w, saved = _fixture(fx.gate_level)
    try:
        assert w.blocked(15, 8)                        # gate closed
        w._gate_open.add('g1')
        assert not w.blocked(15, 8)                    # channel high -> open
        w._gate_open.clear()
        assert w.blocked(15, 8)
        assert w.cells.barrier(15, 8).kind == 'gate'   # barrier persists
    finally:
        _restore(saved)


def test_block_blocks_and_push_updates_query():
    w, saved = _fixture(fx.gate_level)
    try:
        rk = w._current_room
        (bc, br) = w._room_blocks[rk][0]
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
