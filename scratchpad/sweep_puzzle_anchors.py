"""Statistical R-P11 sweep (spec 0063 / BL-45): anchored push puzzles.

Generates >= 120 Act 2 levels and counts:

  landing  — pushable block starting on a landing tile (floor just
             inside a passage of its room, or flanking water)
  anchored — plate whose puzzle is NOT solvable by a player entering
             the plate room from a doorway (independent anchored
             Sokoban replica: player starts in a doorway component)

Detector validation: run PRE-fix — landing hits are near-certain
(hypothesis found one instantly); anchored hits are the rarer BL-45
class.  Post-fix: 0 violations.

Run manually:  .venv/bin/python scratchpad/sweep_puzzle_anchors.py [n_seeds]
"""
import collections
import os
import random
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import levels
from constants import WALL_REINFORCED
from levelgraph import LevelGraph
from levellayout import (build_level_dict, LayoutError,
                         _compute_dead_squares, _player_reachable)

CARDINAL = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _build(fs, seed):
    base = random.Random(seed)
    for _ in range(60):
        rng = random.Random(base.randint(0, 2 ** 31))
        g = LevelGraph.generate(fs, rng)
        try:
            return build_level_dict(g, rng=rng,
                                    strategies=fs.get('layout_strategies'))
        except LayoutError:
            continue
    raise AssertionError(f"build failed seed={seed}")


def _anchored_solvable(block, target, passable, dead, anchors):
    """Independent anchored Sokoban replica (state: block + player zone;
    player starts only in components containing an anchor)."""
    if block == target:
        return True
    starts = set()
    for a in anchors:
        if a in passable and a != block:
            starts.add(min(_player_reachable(a, block, passable)))
    for norm in starts:
        state = (block, norm)
        visited = {state}
        queue = deque([state])
        while queue:
            (bx, by), zone = queue.popleft()
            reach = _player_reachable(zone, (bx, by), passable)
            for dc, dr in CARDINAL:
                pf = (bx - dc, by - dr)
                pt = (bx + dc, by + dr)
                if pf not in reach or pt not in passable or pt in dead:
                    continue
                if pt == target:
                    return True
                nz = min(_player_reachable((bx, by), pt, passable))
                ns = (pt, nz)
                if ns not in visited:
                    visited.add(ns)
                    queue.append(ns)
    return False


def main(n_seeds=12):
    built = 0
    hits = []
    for seed in range(n_seeds):
        for idx, fs in enumerate(levels.ACT2_FEATURE_SETS):
            level_no = 11 + idx
            lv = _build(fs, seed)
            built += 1
            for gname, rd in lv['rooms'].items():
                to = rd['tile_owner']
                walls = rd['walls']
                doors = {(c, r) for c, r, _x in rd.get('locked_doors', [])}
                gates = {(c, r) for c, r, _x in rd.get('gates', [])}
                water = {tuple(t) for t in rd.get('water_tiles', [])}
                blocks = [tuple(b) for b in rd.get('pushable_blocks', [])]
                plates = rd.get('pressure_plates', [])
                if not plates:
                    continue

                def passage(pos, owner):
                    if pos in to or pos in water:
                        return False
                    if (walls.get(pos) == WALL_REINFORCED
                            and pos not in doors and pos not in gates):
                        return False
                    others = {to.get((pos[0] + a, pos[1] + b))
                              for a, b in CARDINAL}
                    others.discard(None)
                    others.discard(owner)
                    return bool(others)

                for bc, br in blocks:
                    owner = to.get((bc, br))
                    for dc, dr in CARDINAL:
                        npos = (bc + dc, br + dr)
                        if npos in water or passage(npos, owner):
                            hits.append((seed, level_no, 'landing',
                                         (bc, br), npos))
                            print(f'LANDING: seed={seed} L{level_no} '
                                  f'block=({bc},{br}) passage={npos}')

                # Anchored solvability per plate: puzzle scope = plate
                # room floor + passable hole tiles.  Anchors are the
                # ENTRY-side standable tiles: hole tiles themselves plus
                # the landing tiles inside the room next to any passage
                # (hole, door, gate, breakable) — the player traverses
                # openable barriers to enter, but can never traverse the
                # block (spec 0063 augmented-entry semantics).
                for pc, pr, gid in plates:
                    proom = to.get((pc, pr))
                    room_tiles = {t for t, o in to.items() if o == proom}
                    holes = set()
                    anchors = set()
                    for t in room_tiles:
                        for dc, dr in CARDINAL:
                            nb = (t[0] + dc, t[1] + dr)
                            if nb in to:
                                continue
                            is_hole = (nb not in walls
                                       and nb not in water
                                       and 0 < nb[0] < 29
                                       and 0 < nb[1] < 15)
                            openable = (nb in doors or nb in gates
                                        or (nb in walls and
                                            walls[nb] != WALL_REINFORCED))
                            if is_hole:
                                holes.add(nb)
                                anchors.add(nb)
                                anchors.add(t)   # landing tile
                            elif openable:
                                anchors.add(t)   # landing tile inside
                    passable = (room_tiles | holes) - set(
                        b for b in blocks)
                    anchors &= passable | holes
                    ok = False
                    for b in blocks:
                        if to.get(b) != proom:
                            continue
                        p = (passable | {b})
                        dead = _compute_dead_squares(p, [(pc, pr)])
                        if _anchored_solvable(b, (pc, pr), p, dead,
                                              anchors):
                            ok = True
                            break
                    if not ok and any(to.get(b) == proom for b in blocks):
                        hits.append((seed, level_no, 'anchored',
                                     (pc, pr), gid))
                        print(f'ANCHORED: seed={seed} L{level_no} '
                              f'plate=({pc},{pr}) gate={gid} room={proom}')
        print(f'seed {seed}: done ({built} levels so far)')
    print(f'\n{built} levels checked, {len(hits)} violations')
    return 1 if hits else 0


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    sys.exit(main(n))
