"""Hand-written Act 2 fixture levels (spec 0044 H6).

Deterministic mini-levels, one per mechanic, served to the game by patching
world.get_level (see harness.Harness(level_dict=...)).  Layout of the
two-room fixtures (30x16 grid, border implicit):

    cols 1-14 = 'left' room | col 15 = reinforced divider | cols 16-28 = 'right'

with the passage cell(s) at column 15 carrying the mechanic under test
(locked door, gate, water stream).  Player starts at (10, 8).
Each function returns a FRESH dict — the World mutates room data in place.
"""
from uglycraft.constants import WALL_REINFORCED, WALL_WOODEN


def _divider(passages):
    return {(15, r): WALL_REINFORCED for r in range(1, 15)
            if (15, r) not in passages}


def _owner():
    d = {}
    for c in range(1, 15):
        for r in range(1, 15):
            d[(c, r)] = 'left'
    for c in range(16, 29):
        for r in range(1, 15):
            d[(c, r)] = 'right'
    return d


def _room(walls, **kw):
    room = {'walls': walls, 'enemy_starts': [], 'treasures': [],
            'materials': [], 'keys': [], 'locked_doors': [],
            'pushable_blocks': [], 'pressure_plates': [], 'gates': [],
            'water_tiles': [], 'water_tile_room': {}, 'flame_jets': [],
            'exits': {}, 'tile_owner': {}, 'dead_squares': []}
    room.update(kw)
    return room


def _level(rooms, start='main', player=(10, 8)):
    return {'rooms': rooms, 'start_room': start, 'player_start': player}


def door_level():
    """Red key on the left, locked door in the divider, treasure right."""
    main = _room(_divider({(15, 8)}), tile_owner=_owner(),
                 keys=[(5, 8, 'red')],
                 locked_doors=[(15, 8, 'red')],
                 treasures=[(20, 8, 1)])
    return _level({'main': main})


def gate_level():
    """Pressure plate + pushable block hold a divider gate open.
    A wandering enemy on the right enables the death/reset phase."""
    main = _room(_divider({(15, 8)}), tile_owner=_owner(),
                 pressure_plates=[(4, 8, 'g1')],
                 pushable_blocks=[(6, 8)],
                 gates=[(15, 8, 'g1')],
                 enemy_starts=[(20, 3)],
                 treasures=[(20, 8, 1)])
    return _level({'main': main})


def water_level():
    """Water stream in the divider; two planks on the left floor.
    Crossing needs: collect planks, craft bridge (TAB), bump the stream."""
    water = [(15, 7), (15, 8), (15, 9)]
    main = _room(_divider(set(water)), tile_owner=_owner(),
                 materials=[(5, 8, 'planks'), (6, 8, 'planks')],
                 water_tiles=list(water),
                 water_tile_room={t: 'right' for t in water},
                 treasures=[(20, 8, 1)])
    return _level({'main': main})


def flame_level():
    """Flame jet from a wall nozzle at (17,8) sweeping right over
    (18..20, 8). The player approaches from above (start (18,4)) so the
    nozzle wall is not in the walking path. No treasures (the run must
    not advance)."""
    main = _room({(17, 8): WALL_REINFORCED},
                 tile_owner={(c, r): 'main'
                             for c in range(1, 29) for r in range(1, 15)
                             if (c, r) != (17, 8)},
                 flame_jets=[{'tiles': [(18, 8), (19, 8), (20, 8)],
                              'on_ms': 1000, 'off_ms': 1000,
                              'dir': (1, 0), 'source': (17, 8)}])
    return _level({'main': main}, player=(18, 4))


def transition_level():
    """Two grids joined by border exits at row 8; g2 has a wooden wall at
    (20,8) whose broken state must persist across leave/return."""
    g1 = _room({}, exits={'right_8': 'g2'})
    g2 = _room({(20, 8): WALL_WOODEN}, exits={'left_8': 'g1'})
    return _level({'g1': g1, 'g2': g2}, start='g1', player=(25, 8))


def forge_level():
    """Forge ogre in a wall pocket open only at (10,8): the player seals
    it with a placed stone wall, which the ogre breaks in 2 hits."""
    pocket = {(8, 7): WALL_REINFORCED, (9, 7): WALL_REINFORCED,
              (10, 7): WALL_REINFORCED, (8, 9): WALL_REINFORCED,
              (9, 9): WALL_REINFORCED, (10, 9): WALL_REINFORCED,
              (8, 8): WALL_REINFORCED}
    main = _room(pocket,
                 enemy_starts=[(9, 8, 'forge_ogre')])
    return _level({'main': main}, player=(11, 8))


def showcase_level():
    """Screenshot fixture: locked door, gate, plate, block, and a water
    stream all visible in one divider (spec 0044 H7)."""
    passages = {(15, 5), (15, 8), (15, 11)}
    main = _room(_divider(passages), tile_owner=_owner(),
                 keys=[(5, 8, 'red')],
                 locked_doors=[(15, 5, 'red')],
                 pressure_plates=[(4, 8, 'g1')],
                 pushable_blocks=[(6, 8)],
                 gates=[(15, 8, 'g1')],
                 water_tiles=[(15, 11)],
                 water_tile_room={(15, 11): 'right'},
                 materials=[(7, 4, 'planks')],
                 treasures=[(20, 8, 1)])
    return _level({'main': main})


def patrol_level():
    """Patrol guard walking a rectangle; the player just watches."""
    main = _room({}, tile_owner={(c, r): 'main'
                                 for c in range(1, 29) for r in range(1, 15)},
                 patrol_enemies=[{'start': (20, 5),
                                  'waypoints': [(20, 5), (24, 5),
                                                (24, 10), (20, 10)]}])
    return _level({'main': main})
