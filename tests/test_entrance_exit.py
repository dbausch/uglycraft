"""Entrance opens on award completion; level ends by walking out (spec 0066 / BL-43).

Two-phase level completion, mirroring a grid change:

1. Collecting the last award latches a reserved gate channel high (opening
   the entrance) and emits `entrance_opened` — it does NOT advance the level.
2. The open entrance is a walkable exit gap (the ordinary
   `cells.blocked(c, r, channels)` gate query, no `world.blocked` change).
   The player steps onto it, and a further off-screen press ends the level.

The entrance door persists across death (spec 0068: `_lose_life` leaves
`_channels` untouched, so the reserved channel stays high; plate gates now
recompute from live occupancy at the next latch rather than being wiped), and
Act 1 enemies are confined to the interior so they can never occupy the open
door.

These are the red-first tests for spec 0066; `world.blocked` and the gate
query are exercised directly, no Game / Surface / harness.
"""
import random

import pytest

from uglycraft.world import World
from uglycraft.constants import COLS, ROWS

KEY = 42                      # opaque bump-consumption key id
ENTRANCE_CHANNEL = '__entrance__'   # must equal world.ENTRANCE_CHANNEL

# Level 1 (spec 0064): entrance on the right border, start directly inside.
ENT = (29, 7)
INSIDE = (28, 7)

INTERIOR_TILES = frozenset((c, r) for c in range(1, COLS - 1)
                                  for r in range(1, ROWS - 1))


def _kinds(events):
    return [e[0] for e in events]


def _on_border(c, r):
    return c in (0, COLS - 1) or r in (0, ROWS - 1)


def _world(level=1, difficulty='easy', seed=1234):
    random.seed(seed)
    w = World(difficulty)
    w.start_level(level)
    w.drain_events()
    return w


def _open(w):
    """Latch the entrance open and drop the resulting event(s)."""
    w._open_entrance()
    w.drain_events()


# ── The entrance is a gate cell ───────────────────────────────────────────────

def test_entrance_loads_as_a_closed_gate():
    """At load the entrance tile holds a gate barrier on the reserved
    channel; the channel is low, so it is closed and solid."""
    w = _world()
    b = w.cells.barrier(*ENT)
    assert b is not None and b.kind == 'gate'
    assert b.channel == ENTRANCE_CHANNEL
    assert ENTRANCE_CHANNEL not in w._channels
    assert w.entrance_open is False
    assert w.blocked(*ENT) is True


# ── Phase 1: last award opens the door, does not advance ──────────────────────

def test_last_award_opens_entrance_without_advancing():
    """Collecting the 9th sequential award latches the channel high, emits
    `entrance_opened`, and leaves the level number unchanged."""
    w = _world()
    w.room.enemies = []                 # isolate the collection path
    w.item_no = 9                       # next pickup is the final award
    w.treasure_item_no = 9
    w.treasure_pos = (w.player.col, w.player.row)
    w.update(33)
    events = w.drain_events()
    assert 'entrance_opened' in _kinds(events)
    assert w.entrance_open is True
    assert ENTRANCE_CHANNEL in w._channels
    assert w.level == 1                 # did NOT advance


def test_non_final_award_does_not_open():
    """Collecting a non-final award neither opens the entrance nor emits
    `entrance_opened`."""
    w = _world()
    w.room.enemies = []
    w.item_no = 5
    w.treasure_item_no = 5
    w.treasure_pos = (w.player.col, w.player.row)
    w.update(33)
    assert 'entrance_opened' not in _kinds(w.drain_events())
    assert w.entrance_open is False
    assert ENTRANCE_CHANNEL not in w._channels


# ── Phase 2: the open entrance is a walkable exit gap ─────────────────────────

def test_open_entrance_is_walkable_through_the_gate_query():
    """Latching the channel high makes the entrance passable via the
    ordinary cells gate query — no `world.blocked` special-case."""
    w = _world()
    assert w.blocked(*ENT) is True
    w._channels.add(ENTRANCE_CHANNEL)
    assert w.cells.blocked(*ENT, w._channels) is False
    assert w.blocked(*ENT) is False


def test_first_press_steps_onto_the_open_door():
    """From the interior neighbour, one press moves the player ONTO the open
    entrance tile (a normal step, not a bump)."""
    w = _world()
    w.room.enemies = []
    _open(w)
    w.player.col, w.player.row = INSIDE
    assert w.try_move(1, 0, KEY) is True
    assert (w.player.col, w.player.row) == ENT


def test_second_press_off_screen_ends_the_level():
    """Standing on the open entrance, a press off the screen edge advances
    the level (mirroring `_try_room_transition`)."""
    w = _world()
    w.room.enemies = []
    _open(w)
    w.player.col, w.player.row = ENT
    w.try_move(1, 0, KEY)               # off-screen press
    events = w.drain_events()
    assert 'level_advanced' in _kinds(events)
    assert w.level == 2


def test_stepping_on_alone_does_not_advance():
    """The first press only steps onto the door; the level does not end
    until the second, off-screen press."""
    w = _world()
    w.room.enemies = []
    _open(w)
    w.player.col, w.player.row = INSIDE
    w.try_move(1, 0, KEY)              # step on
    w.key_released(KEY)
    assert (w.player.col, w.player.row) == ENT
    assert w.level == 1               # not advanced yet


def test_closed_entrance_is_inert_and_solid():
    """Before it is opened the entrance blocks and pressing into it bumps
    without moving or advancing (behaviour lock)."""
    w = _world()
    w.room.enemies = []
    assert w.blocked(*ENT) is True
    w.player.col, w.player.row = INSIDE
    assert w.try_move(1, 0, KEY) is False
    assert (w.player.col, w.player.row) == INSIDE
    assert w.level == 1


# ── Death / reset: door stays open, plate gates still close ───────────────────

def test_door_stays_open_across_death():
    """A non-fatal death preserves the entrance channel (spec 0068): `_lose_life`
    leaves `_channels` untouched, so the opened entrance stays open and walkable.
    Plate-held gates are no longer wiped on death — they recompute from live
    occupancy at the next latch pass."""
    w = _world()
    w.room.enemies = []
    _open(w)
    w.lives = 3
    w._lose_life()
    assert w.lives == 2               # non-fatal
    assert ENTRANCE_CHANNEL in w._channels
    assert w.entrance_open is True
    assert w.blocked(*ENT) is False   # still walkable


# ── Act 1 enemy confinement ───────────────────────────────────────────────────

def test_act1_enemies_are_interior_confined():
    """Every Act 1 enemy is attached to the interior tile set with no room
    name (so it keeps always-chasing) — it can never step on a border tile."""
    w = _world(difficulty='hard')     # hard spawns the full enemy set
    assert w.enemies                  # sanity: there are enemies to confine
    for e in w.enemies:
        assert e.room_tiles == INTERIOR_TILES
        assert e.room_name is None


def test_enemies_never_occupy_the_open_door():
    """With the door open and the player parked on it, no enemy ever reaches
    any border tile over many ticks."""
    w = _world(difficulty='hard')
    _open(w)
    w.lives = 999
    w.player.col, w.player.row = ENT
    for _ in range(200):
        w.update(33)
        for e in w.enemies:
            assert not _on_border(e.col, e.row), (e.col, e.row)
