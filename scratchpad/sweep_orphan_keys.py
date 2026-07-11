"""Statistical R-K1 sweep (spec 0061): barrier↔prerequisite pairing.

Generates >= 100 Act 2 levels and counts:

  orphan   — per-colour #keys != #locked doors
  softgate — gate entity whose gate_id has no surviving plate
  elided   — GATED edge between placed nodes with surviving plate but
             no gate entity (under-elision of the old per-grid check
             never applied to gates; guards the new global scope)

Detector validation: run on the PRE-fix commit first — orphan hits are
certain (6/8 level-13 seeds).  Post-fix: 0 violations.

Run manually:  .venv/bin/python scratchpad/sweep_orphan_keys.py [n_seeds]
"""
import collections
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import levels
from levelgraph import LevelGraph, EdgeType
from levellayout import build_level_dict, LayoutError


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


def main(n_seeds=12):
    built = 0
    hits = []
    for seed in range(n_seeds):
        for idx, fs in enumerate(levels.ACT2_FEATURE_SETS):
            level_no = 11 + idx
            graph, lv = _build(fs, seed)
            built += 1

            keys = collections.Counter()
            doors = collections.Counter()
            gates = {}
            plates = set()
            placed = {o for rd in lv['rooms'].values()
                      for o in rd['tile_owner'].values()}
            for rd in lv['rooms'].values():
                for k in rd.get('keys', []):
                    keys[k[2]] += 1
                for d in rd.get('locked_doors', []):
                    doors[d[2]] += 1
                for c, r, gid in rd.get('gates', []):
                    gates[gid] = True
                for c, r, gid in rd.get('pressure_plates', []):
                    plates.add(gid)

            for col in set(keys) | set(doors):
                if keys[col] != doors[col]:
                    hits.append((seed, level_no, 'orphan', col))
                    print(f'ORPHAN: seed={seed} L{level_no} colour={col} '
                          f'keys={keys[col]} doors={doors[col]}')
            for gid in gates:
                if gid not in plates:
                    hits.append((seed, level_no, 'softgate', gid))
                    print(f'SOFTGATE: seed={seed} L{level_no} {gid}')
            for e in graph.edges:
                if e.edge_type != EdgeType.GATED:
                    continue
                gid = e.params['gate_id']
                if (e.node_a in placed and e.node_b in placed
                        and gid in plates and gid not in gates):
                    hits.append((seed, level_no, 'elided', gid))
                    print(f'ELIDED: seed={seed} L{level_no} {gid}')
        print(f'seed {seed}: done ({built} levels so far)')
    print(f'\n{built} levels checked, {len(hits)} violations')
    return 1 if hits else 0


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    sys.exit(main(n))
