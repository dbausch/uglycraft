"""Broad Stage 4 coverage (spec 0050): channels, bump dispatch, item layer.

Two kinds of tests, deliberately mixed:

- BEHAVIOUR LOCKS — written against *observable* state only (passability,
  events, inventory, score), green before the refactor and required to
  stay green through it.  They give Stage 4 fine-grained failure
  localisation beyond the golden traces.
- API PINS — red until the spec-0050 surfaces exist (`World.channel`,
  the barrier bump table, the cell item layer).
"""
import random

import pytest

import world as world_mod
from world import World
from constants import WALL_STONE, WALL_WOODEN, WALL_REINFORCED
from entities import Block
from tests import act2_fixtures as fx

KEY = 7
DT = 33


# ── plumbing ──────────────────────────────────────────────────────────────────

def _world(make_level, seed=42):
    orig = world_mod.get_level, world_mod.regenerate_level
    world_mod.get_level = lambda n, progress=None: make_level()
    world_mod.regenerate_level = lambda n: make_level()
    random.seed(seed)
    w = World('easy')
    w.drain_events()
    return w, orig


def _restore(orig):
    world_mod.get_level, world_mod.regenerate_level = orig


def _kinds(events):
    return [e[0] for e in events]


def _step(w, dcol, drow, key=KEY):
    w.try_move(dcol, drow, key)
    w.key_released(key)


# ── Q1: gate/channel behaviour locks (observable via passability) ─────────────

GATE = (15, 8)
PLATE = (4, 8)
BLOCK = (6, 8)


def _gate_world():
    """gate_level without the enemy: plate (4,8), block (6,8), gate (15,8)."""
    level = fx.gate_level()
    level['rooms']['main']['enemy_starts'] = []
    return level


def test_gate_closed_until_plate_pressed():
    w, orig = _world(_gate_world)
    try:
        assert w.blocked(*GATE)
        w.update(DT)                          # plate pass with nothing on it
        assert w.blocked(*GATE)
    finally:
        _restore(orig)


def test_player_on_plate_opens_gate_at_plate_pass():
    w, orig = _world(_gate_world)
    try:
        w.player.col, w.player.row = PLATE
        assert w.blocked(*GATE)               # not yet latched
        w.update(DT)                          # plate pass runs
        assert not w.blocked(*GATE)
        w.player.col, w.player.row = (10, 10)
        w.update(DT)                          # stepping off closes it again
        assert w.blocked(*GATE)
    finally:
        _restore(orig)


def test_enemy_on_plate_opens_gate():
    level = fx.gate_level()                   # has an enemy at (20,3)
    w, orig = _world(lambda: level)
    try:
        e = w.enemies[0]
        e.col, e.row = PLATE
        w.player.col, w.player.row = (20, 12)  # far away, no collision
        w.update(DT)
        assert not w.blocked(*GATE)
    finally:
        _restore(orig)


def test_block_on_plate_holds_gate_open():
    w, orig = _world(_gate_world)
    try:
        w.room.blocks[:] = [Block(*PLATE)]    # park the block on the plate
        w.update(DT)
        assert not w.blocked(*GATE)
        # ... and the plate tile itself is blocked (the block sits there)
        assert w.blocked(*PLATE)
    finally:
        _restore(orig)


def test_gate_state_not_visible_before_plate_pass():
    """Timing pin (the reason Stage 3 deferred derivation): occupancy
    changes become visible to passability only at the plate pass, never
    mid-tick at query time."""
    w, orig = _world(_gate_world)
    try:
        w.player.col, w.player.row = PLATE
        for _ in range(5):
            assert w.blocked(*GATE)           # queries alone never open it
        w.update(DT)
        assert not w.blocked(*GATE)
    finally:
        _restore(orig)


def test_foreign_channels_survive_local_latch():
    """Cross-grid gates: a channel held high by a block parked in grid g1
    must stay high while the player is in g2 — both when g2 has no plates
    at all and when g2's own (unpressed) plates are latched.  The old
    _gate_open code only ever touched the current room's gate-ids."""
    def make():
        g1 = fx._room({}, pressure_plates=[(4, 8, 'x1')],
                      pushable_blocks=[(6, 8)],
                      exits={'right_8': 'g2'})
        g2 = fx._room({}, tile_owner={},
                      pressure_plates=[(20, 3, 'x2')],   # never pressed
                      gates=[(15, 8, 'x1')],
                      exits={'left_8': 'g1'})
        return fx._level({'g1': g1, 'g2': g2}, start='g1', player=(10, 8))

    w, orig = _world(make)
    try:
        w.room.blocks[:] = [Block(4, 8)]      # block parked on the plate
        w.update(DT)
        assert w.channel('x1')
        w.player.col, w.player.row = 28, 8
        _step(w, 1, 0); _step(w, 1, 0)        # -> g2
        assert w._current_room == 'g2'
        for _ in range(12):                    # past the 300 ms transition
            w.update(DT)                       #   freeze; g2's latch runs
        assert w.channel('x1'), 'foreign channel wiped by local latch'
        assert not w.blocked(15, 8)            # the x1 gate stands open
        assert not w.channel('x2')
    finally:
        _restore(orig)


# ── Q1: channel API pins (red until spec 0050) ────────────────────────────────

def test_channel_query_api():
    w, orig = _world(_gate_world)
    try:
        assert w.channel('g1') is False
        w.player.col, w.player.row = PLATE
        w.update(DT)
        assert w.channel('g1') is True
        assert w.channel('nonexistent') is False
    finally:
        _restore(orig)


def test_gate_open_attribute_is_gone():
    """The stored _gate_open set is deleted; _channels is the latch."""
    w, orig = _world(_gate_world)
    try:
        assert not hasattr(w, '_gate_open')
        assert w._channels == set()
    finally:
        _restore(orig)


# ── Q2: bump-outcome behaviour locks, one per barrier kind ────────────────────

def _walls_world(walls):
    def make():
        g = fx._room(dict(walls))
        return fx._level({'main': g}, player=(10, 8))
    return _world(make)


def test_border_bump_is_inert():
    w, orig = _walls_world({})
    try:
        w.player.col, w.player.row = (1, 8)
        w.try_move(-1, 0, KEY)                # bump the border at (0,8)
        assert w.drain_events() == []
        assert w.blocked(0, 8)
    finally:
        _restore(orig)


def test_reinforced_bump_is_inert():
    w, orig = _walls_world({(11, 8): WALL_REINFORCED})
    try:
        w.try_move(1, 0, KEY)
        assert w.drain_events() == []
        assert w.blocked(11, 8)
    finally:
        _restore(orig)


def test_stone_breaks_in_three_bumps():
    w, orig = _walls_world({(11, 8): WALL_STONE})
    try:
        events = []
        for _ in range(3):
            _step(w, 1, 0)
            events += w.drain_events()
        assert _kinds(events) == ['bumped', 'bumped', 'wall_broken']
        assert not w.blocked(11, 8)
    finally:
        _restore(orig)


def test_wooden_breaks_in_two_bumps():
    w, orig = _walls_world({(11, 8): WALL_WOODEN})
    try:
        events = []
        for _ in range(2):
            _step(w, 1, 0)
            events += w.drain_events()
        assert _kinds(events) == ['bumped', 'wall_broken']
        assert not w.blocked(11, 8)
    finally:
        _restore(orig)


def test_placed_wall_breaks_in_three_player_bumps():
    def make():
        level = fx._level({'main': fx._room({})}, player=(10, 8))
        level['crafting'] = False        # Act 1 credit placement mechanics
        return level
    w, orig = _world(make)
    try:
        w._place_credits = 1
        w.player.col, w.player.row = (12, 8)   # off the respawn tile (spec 0067)
        w.place()                              # placed barrier under player
        w.drain_events()
        w.player.col, w.player.row = (11, 8)   # step off, bump it from left
        events = []
        for _ in range(3):
            _step(w, 1, 0)
            events += w.drain_events()
        assert _kinds(events) == ['bumped', 'bumped', 'wall_broken']
    finally:
        _restore(orig)


def test_gate_bump_is_inert():
    w, orig = _world(_gate_world)
    try:
        w.player.col, w.player.row = (14, 8)
        w.try_move(1, 0, KEY)                  # bump the closed gate
        assert w.drain_events() == []
        assert w.blocked(*GATE)
    finally:
        _restore(orig)


def test_keyless_door_bump_is_inert():
    w, orig = _world(fx.door_level)
    try:
        w.player.col, w.player.row = (14, 8)
        w.try_move(1, 0, KEY)
        assert w.drain_events() == []
        assert w.blocked(15, 8)
    finally:
        _restore(orig)


def test_bump_dispatch_table_exists():
    """API pin (red until Q2): the barrier bump table, one entry per
    kind — None = inert, 'key' = door auto-open, int = hits to break."""
    from cells import BARRIER_BUMP
    assert BARRIER_BUMP == {
        'border': None, 'reinforced': None, 'gate': None,
        'door': 'key',
        'stone': 3, 'wooden': 2, 'placed': 3,
    }


# ── Q3: item collection behaviour locks ───────────────────────────────────────

def _items_level(treasures=(), materials=(), keys=()):
    def make():
        main = fx._room({}, tile_owner={},
                        treasures=list(treasures),
                        materials=list(materials),
                        keys=list(keys))
        return fx._level({'main': main}, player=(10, 8))
    return make


def test_treasure_material_key_on_one_tile_all_collected_in_one_tick():
    """One item per CATEGORY per tick: co-located treasure + material +
    key are all three collected in a single update."""
    w, orig = _world(_items_level(treasures=[(11, 8, 1), (20, 8, 2)],
                                  materials=[(11, 8, 'planks')],
                                  keys=[(11, 8, 'red')]))
    try:
        _step(w, 1, 0)                        # onto (11,8)
        w.drain_events()
        w.update(DT)
        assert _kinds(w.drain_events()).count('collected') == 3
        assert w.inventory.materials.get('planks', 0) == 1
        assert w.inventory.has_key('red')
        assert w._loot_collected == 1
    finally:
        _restore(orig)


def test_two_materials_same_tile_need_two_ticks():
    w, orig = _world(_items_level(treasures=[(20, 8, 1)],
                                  materials=[(11, 8, 'planks'),
                                             (11, 8, 'rocks')]))
    try:
        _step(w, 1, 0)
        w.drain_events()
        w.update(DT)
        assert _kinds(w.drain_events()).count('collected') == 1
        w.update(DT)
        assert _kinds(w.drain_events()).count('collected') == 1
        assert w.inventory.materials.get('planks', 0) == 1
        assert w.inventory.materials.get('rocks', 0) == 1
        w.update(DT)
        assert w.drain_events() == []          # nothing left
    finally:
        _restore(orig)


def test_last_treasure_opens_entrance():
    """Spec 0066: collecting the last preplaced award opens the entrance
    (entrance_opened) rather than advancing the level on pickup — the level
    ends only when the player then walks out through the entrance."""
    w, orig = _world(_items_level(treasures=[(11, 8, 1)]))
    try:
        _step(w, 1, 0)
        w.drain_events()
        w.update(DT)
        kinds = _kinds(w.drain_events())
        assert 'collected' in kinds and 'entrance_opened' in kinds
        assert 'level_advanced' not in kinds
    finally:
        _restore(orig)


def test_collected_items_stay_collected_across_rooms():
    """Persistence lock: collect a key in g1, go to g2, come back — the
    key does not reappear."""
    def make():
        g1 = fx._room({}, keys=[(11, 8, 'red')], exits={'right_8': 'g2'})
        g2 = fx._room({}, exits={'left_8': 'g1'})
        return fx._level({'g1': g1, 'g2': g2}, start='g1', player=(10, 8))
    w, orig = _world(make)
    try:
        _step(w, 1, 0)
        w.update(DT)                          # collect the key
        assert w.inventory.has_key('red')
        w.player.col, w.player.row = 28, 8
        _step(w, 1, 0); _step(w, 1, 0)        # -> g2
        w.player.col, w.player.row = 1, 8
        _step(w, -1, 0); _step(w, -1, 0)      # -> back to g1
        w.drain_events()
        w.player.col, w.player.row = (10, 8)
        _step(w, 1, 0)                        # walk over (11,8) again
        w.update(DT)
        assert _kinds(w.drain_events()).count('collected') == 0
    finally:
        _restore(orig)


def test_act1_sequential_treasure_untouched():
    """Act 1's treasure_pos mechanic is not part of the item layer."""
    random.seed(1234)
    w = World('easy')
    w.drain_events()
    assert w.treasure_pos is not None
    w.player.col, w.player.row = w.treasure_pos
    score = w.score
    w.update(DT)
    assert w.score > score
    assert 'collected' in _kinds(w.drain_events())
    assert w.treasure_pos is not None          # next one spawned


# ── Q3: item-layer API pins (red until spec 0050) ─────────────────────────────

def test_cells_item_layer_api():
    from cells import build_room_cells
    room = fx._room({}, treasures=[(11, 8, 3)],
                    materials=[(12, 8, 'planks')],
                    keys=[(13, 8, 'red'), (13, 8, 'blue')])
    cells = build_room_cells(room)
    (t,) = cells.items(11, 8)
    assert (t.kind, t.payload) == ('treasure', 3)
    (m,) = cells.items(12, 8)
    assert (m.kind, m.payload) == ('material', 'planks')
    k1, k2 = cells.items(13, 8)
    assert (k1.payload, k2.payload) == ('red', 'blue')   # insertion order
    assert cells.items(14, 8) == ()
    assert [(pos, i.payload) for pos, i in cells.items_of_kind('key')] \
        == [((13, 8), 'red'), ((13, 8), 'blue')]
    cells.remove_item((11, 8), t)
    assert cells.items(11, 8) == ()


def test_world_items_live_in_cells():
    """The three per-room item dicts are gone; cells carry the items."""
    w, orig = _world(_items_level(treasures=[(11, 8, 1)],
                                  materials=[(12, 8, 'planks')],
                                  keys=[(13, 8, 'red')]))
    try:
        assert not hasattr(w, '_room_treasures')
        assert not hasattr(w, '_room_materials')
        assert not hasattr(w, '_room_keys')
        assert [i.kind for _, i in w.cells.items_of_kind('treasure')] \
            == ['treasure']
    finally:
        _restore(orig)
