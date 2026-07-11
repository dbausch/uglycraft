"""Statistical R-P7 sweep (spec 0049): no plate on a landing tile.

Generates Act 2 levels across many seeds and checks every pressure
plate against both halves of the invariant, from the level dict alone:

  (a) water flanks — the plate is not cardinally adjacent to any water
      tile (the landing tile of a buildable bridge passage);
  (b) doorway landings — no cardinal neighbour of the plate is a
      passage tile: a tile without a floor owner that is an open hole
      (not in walls), a non-reinforced wall (breakable), a door, or a
      gate, and that touches floor of a second room on another side.

(b) is a dict-level reconstruction (the generator's graph/placed view
is gone by now), so a hit is a *candidate* violation to inspect, not
automatically a bug — but zero hits is a real absence statement.

Run manually:  .venv/bin/python scratchpad/sweep_plate_clearance.py [n_seeds]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import levels
from constants import WALL_REINFORCED
from levels import get_level

CARDINAL = ((1, 0), (-1, 0), (0, 1), (0, -1))


def passage_tile(pos, room, owner):
    """Is pos a passage tile (existing or openable) out of room `owner`?"""
    if pos in room.get('tile_owner', {}):
        return False                      # room/corridor floor, not a passage
    walls = room['walls']
    doors = {(c, r) for c, r, _ in room.get('locked_doors', [])}
    gates = {(c, r) for c, r, _ in room.get('gates', [])}
    if pos in walls and walls[pos] == WALL_REINFORCED \
            and pos not in doors and pos not in gates:
        return False                      # never opens
    # must touch floor of a DIFFERENT owner on some side
    to = room.get('tile_owner', {})
    others = {to.get((pos[0] + dc, pos[1] + dr)) for dc, dr in CARDINAL}
    others.discard(None)
    others.discard(owner)
    return bool(others)


def main(n_seeds=50):
    plates_checked = 0
    hits = []
    for seed in range(n_seeds):
        levels.set_game_seed(seed)
        for n in range(11, 21):
            level = get_level(n)
            for rkey, room in level['rooms'].items():
                water = {tuple(t) for t in room.get('water_tiles', [])}
                owner_map = room.get('tile_owner', {})
                for pc, pr, gid in room.get('pressure_plates', []):
                    plates_checked += 1
                    owner = owner_map.get((pc, pr))
                    for dc, dr in CARDINAL:
                        npos = (pc + dc, pr + dr)
                        if npos in water:
                            hits.append((seed, n, rkey, (pc, pr), 'water', npos))
                            print(f'WATER FLANK: seed={seed} level={n} '
                                  f'plate={(pc, pr)} water={npos}')
                        elif passage_tile(npos, room, owner):
                            hits.append((seed, n, rkey, (pc, pr), 'landing', npos))
                            print(f'LANDING: seed={seed} level={n} room={rkey} '
                                  f'plate={(pc, pr)} passage={npos}')
        print(f'seed {seed}: done ({plates_checked} plates so far)')
    print(f'\n{plates_checked} plates checked, {len(hits)} violations')
    return 1 if hits else 0


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    sys.exit(main(n))
