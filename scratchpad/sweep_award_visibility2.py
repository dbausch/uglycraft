"""Player-perspective award statistics, v2 — the FINAL world (2026-07-12).

v1 analysed the generator's level dict; the player never sees that.  The
runtime applies further transformations, chiefly `Room.from_data`
(rooms.py): cells parsing AND the difficulty trim — on EASY each world
room (= one whole grid) keeps all special enemies but at most ONE
regular chaser.  Spec 0058 places 2 enemies per grid, so EASY halves the
enemies while their guard awards stay.

This sweep goes through the production path (`levels.set_game_seed` +
`get_level`) and then constructs every grid's Room exactly as the world
does on entry (`Room.from_data`, per difficulty), reading enemies from
`room.enemies` and awards from the CELLS item layer.  Effective room
protection is the bottleneck path from the grid's corridor over the
cells view (doors/gates/water = keyed, stone/wood walls = breakable).

Expectations (spec 0058 economy, as the PLAYER experiences it):
  E1  awards(room) == challenge-award (0/1) + GENERATED enemies(room)
  E2  every award in an effectively open/breakable non-flame room has a
      LIVE guard in the constructed world

Run:  .venv/bin/python scratchpad/sweep_award_visibility2.py [n_seeds]
"""
import collections
import heapq
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import levels
from constants import WALL_REINFORCED, WALL_STONE, WALL_WOODEN, EASY, HARD
from levels import get_level
from rooms import Room

CARDINAL = ((1, 0), (-1, 0), (0, 1), (0, -1))
COLS, ROWS = 30, 16


def _cells_passages(cells, to):
    """[(owner_a, owner_b, severity)] from the runtime cells view."""
    out = []
    for c in range(COLS):
        for r in range(ROWS):
            if (c, r) in to:
                continue
            owners = {to.get((c + dc, r + dr)) for dc, dr in CARDINAL}
            owners.discard(None)
            if len(owners) < 2:
                continue
            b = cells.barrier(c, r)
            if b is None:
                sev = 2 if cells.is_water(c, r) and not cells.bridge(c, r) \
                    else 0
            elif b.kind in ('door', 'gate'):
                sev = 2
            elif b.kind in (WALL_STONE, WALL_WOODEN, 'placed'):
                sev = 1
            else:
                continue        # reinforced / border: not a passage
            for a in owners:
                for bo in owners:
                    if a < bo:
                        out.append((a, bo, sev))
    return out


def _effective(cells, to, corridor):
    adj = collections.defaultdict(list)
    for a, b, sev in _cells_passages(cells, to):
        adj[a].append((b, sev))
        adj[b].append((a, sev))
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


def main(n_seeds=8):
    for difficulty, dname in ((EASY, 'EASY'), (HARD, 'HARD')):
        matrix = collections.Counter()
        e2 = []
        gen_vs_world_enemy_loss = 0
        rooms_total = 0
        for seed in range(n_seeds):
            levels.set_game_seed(seed)
            for n in range(11, 21):
                lv = get_level(n)
                for gname, rd in lv['rooms'].items():
                    room = Room.from_data(gname, rd, difficulty)
                    cells = room.cells
                    to = rd['tile_owner']
                    corridor = next(o for o in to.values()
                                    if o.startswith('corridor'))
                    eff = _effective(cells, to, corridor)

                    awards = collections.Counter()
                    for (c, r), _it in cells.items_of_kind('treasure'):
                        awards[to.get((c, r))] += 1
                    live = collections.Counter()
                    for e in room.enemies:
                        live[to.get((e.col, e.row))] += 1
                    gen = collections.Counter()
                    for c, r, _t in rd.get('enemy_starts', []):
                        gen[to.get((c, r))] += 1
                    gen_vs_world_enemy_loss += (
                        sum(gen.values()) - sum(live.values()))

                    flame_owner = {to.get(t) for jet in rd.get(
                        'flame_jets', []) for t in jet['tiles']}
                    for owner in {o for o in to.values() if o != corridor}:
                        rooms_total += 1
                        sev = eff.get(owner, 2)
                        cls = ('flame' if owner in flame_owner
                               else ('open', 'breakable', 'keyed')[sev])
                        a, lv_e = awards[owner], live[owner]
                        matrix[(cls, min(a, 3), min(lv_e, 3))] += 1
                        if a > lv_e and cls in ('open', 'breakable'):
                            e2.append((seed, n, gname, owner, cls, a, lv_e))
            print(f'{dname} seed {seed}: done')

        print(f'\n== {dname} ==  ({rooms_total} rooms, '
              f'{gen_vs_world_enemy_loss} generated enemies dropped by the '
              f'world)')
        print('class      awards live-enemies  rooms')
        for (cls, a, en), cnt in sorted(matrix.items()):
            print(f'{cls:<10} {a:>6} {en:>12} {cnt:>6}')
        total_awards = sum(a * cnt for (c, a, en), cnt in matrix.items())
        unguarded = sum(
            a * cnt for (c, a, en), cnt in matrix.items()
            if c in ('open', 'breakable') and a > en)
        print(f'awards: {total_awards}; E2 violations '
              f'(open/breakable awards without live guard): {len(e2)}')
        for v in e2[:8]:
            print('  E2:', v)
    return 0


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    sys.exit(main(n))
