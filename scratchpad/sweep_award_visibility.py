"""Player-perspective award statistics (spec 0058 review, 2026-07-12).

For every generated Act 2 level, classify each room by its EFFECTIVE
protection — the bottleneck barrier on the easiest path from the grid's
corridor, reconstructed from the final level dict exactly as a player
experiences it:

  open       — reachable through open doorways only
  breakable  — easiest path crosses a stone/wooden wall
  keyed      — easiest path needs a key, a plate puzzle, or a bridge
  (+flames)  — room contains flame jets (its entry may still be open;
               the flames protect the award inside)

Then tally award items and enemy starts per room and validate against
the spec-0058 economy:

  E1  awards(room) == challenge(room, from graph) + enemies(room)
  E2  every award in an effectively-open or breakable room without
      flames is enemy-guarded (guard awards are the only reason such
      rooms hold awards)

plus a readability matrix: how many award-bearing rooms does the player
see per protection class, and how many of their awards are "free" once
the (killable, room-confined) guard is gone.

Run manually:  .venv/bin/python scratchpad/sweep_award_visibility.py [n_seeds]
"""
import collections
import heapq
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import levels
from constants import WALL_REINFORCED
from levelgraph import LevelGraph, EdgeType, NodeSize
from levellayout import build_level_dict, LayoutError

CARDINAL = ((1, 0), (-1, 0), (0, 1), (0, -1))
SEV = {'open': 0, 'breakable': 1, 'keyed': 2}


def _build(fs, seed):
    base = random.Random(seed)
    for _ in range(60):
        rng = random.Random(base.randint(0, 2 ** 31))
        g = LevelGraph.generate(fs, rng)
        try:
            return g, build_level_dict(g, rng=rng,
                                       strategies=fs.get('layout_strategies'))
        except LayoutError:
            continue
    raise AssertionError(f"build failed seed={seed}")


def _passages(rd):
    """[(owner_a, owner_b, severity)] for one grid's room dict."""
    to = rd['tile_owner']
    walls = rd['walls']
    doors = {(c, r) for c, r, _ in rd.get('locked_doors', [])}
    gates = {(c, r) for c, r, _ in rd.get('gates', [])}
    water = {tuple(t) for t in rd.get('water_tiles', [])}
    out = []
    seen = set()
    candidates = set(doors) | set(gates) | set(water) | set(walls)
    # open doorway holes are neither owned nor in walls: scan the floor
    # neighbourhood instead of the whole grid
    for t in to:
        for dc, dr in CARDINAL:
            candidates.add((t[0] + dc, t[1] + dr))
    for t in candidates:
        if t in to or t in seen:
            continue
        owners = {to.get((t[0] + dc, t[1] + dr)) for dc, dr in CARDINAL}
        owners.discard(None)
        if len(owners) < 2:
            continue
        if t in doors or t in gates:
            sev = 'keyed'
        elif t in water:
            sev = 'keyed'          # needs planks -> a bridge
        elif t in walls:
            if walls[t] == WALL_REINFORCED:
                continue
            sev = 'breakable'
        else:
            sev = 'open'
        seen.add(t)
        for a in owners:
            for b in owners:
                if a < b:
                    out.append((a, b, sev))
    return out


def _effective_class(rd, corridor):
    """{owner: severity 0/1/2} — bottleneck path cost from the corridor."""
    adj = collections.defaultdict(list)
    for a, b, sev in _passages(rd):
        adj[a].append((b, SEV[sev]))
        adj[b].append((a, SEV[sev]))
    best = {corridor: 0}
    heap = [(0, corridor)]
    while heap:
        cost, node = heapq.heappop(heap)
        if cost > best.get(node, 99):
            continue
        for nb, sev in adj[node]:
            nc = max(cost, sev)
            if nc < best.get(nb, 99):
                best[nb] = nc
                heapq.heappush(heap, (nc, nb))
    return best


def main(n_seeds=12):
    matrix = collections.Counter()   # (class, awards_in_room, enemies) -> rooms
    e1_violations = []
    e2_violations = []
    rooms_total = 0
    for seed in range(n_seeds):
        for idx, fs in enumerate(levels.ACT2_FEATURE_SETS):
            level_no = 11 + idx
            graph, lv = _build(fs, seed)
            protected = {n for n, nd in graph.nodes.items() if nd.has_flames}
            for e in graph.edges:
                if e.edge_type in (EdgeType.LOCKED, EdgeType.GATED,
                                   EdgeType.WATER):
                    protected.add(e.node_b)
            cor = {n for n, nd in graph.nodes.items()
                   if nd.size == NodeSize.CORRIDOR}
            flame_rooms = {n for n, nd in graph.nodes.items() if nd.has_flames}

            for gname, rd in lv['rooms'].items():
                to = rd['tile_owner']
                grid_cor = next(o for o in to.values() if o in cor)
                eff = _effective_class(rd, grid_cor)
                awards = collections.Counter()
                for c, r, _no in rd.get('treasures', []):
                    awards[to.get((c, r))] += 1
                enemies = collections.Counter()
                for c, r, _t in rd.get('enemy_starts', []):
                    enemies[to.get((c, r))] += 1
                owners = {o for o in to.values() if o != grid_cor}
                for room in owners:
                    rooms_total += 1
                    sev = eff.get(room, 2)
                    cls = ('flame' if room in flame_rooms
                           else ('open', 'breakable', 'keyed')[sev])
                    a, en = awards[room], enemies[room]
                    matrix[(cls, min(a, 3), min(en, 3))] += 1
                    expected = (1 if room in protected else 0) + en
                    if a != expected:
                        e1_violations.append(
                            (seed, level_no, room, cls, a, expected))
                    if (a > en and cls in ('open', 'breakable')
                            and room not in protected):
                        e2_violations.append(
                            (seed, level_no, room, cls, a, en))
        print(f'seed {seed}: done')

    print(f'\n{rooms_total} rooms across {n_seeds * 10} levels')
    print('\nclass      awards enemies  rooms')
    for (cls, a, en), n in sorted(matrix.items()):
        print(f'{cls:<10} {a:>6} {en:>7} {n:>6}')

    total_awards = sum(a * n for (c, a, en), n in matrix.items())
    free_after_guard = sum(
        a * n for (c, a, en), n in matrix.items()
        if c in ('open', 'breakable') and a > 0)
    print(f'\nawards total (capped tally): {total_awards}')
    print(f'awards in effectively open/breakable rooms: {free_after_guard} '
          f'({100 * free_after_guard / max(1, total_awards):.0f}%) — these '
          f'read as free once their room-confined guard is dead')
    print(f'\nE1 (economy) violations: {len(e1_violations)}')
    for v in e1_violations[:10]:
        print('  E1:', v)
    print(f'E2 (unguarded open-room awards) violations: {len(e2_violations)}')
    for v in e2_violations[:10]:
        print('  E2:', v)
    return 1 if e1_violations or e2_violations else 0


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    sys.exit(main(n))
