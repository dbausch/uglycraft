"""BL-56 / spec 0075: duplicate-colour keys are capped at 4 per colour and
28 locked doors per level, and no locked door is ever orphaned (#keys ==
#doors per colour).

The forced-overflow test is the detector: on the pre-fix generator it FAILS
(a 40-locked-room single grid yields ceil(40/7)=6 of some colour and 40 doors);
post-fix it caps at 4 per colour and 28 doors, downgrading the overflow rooms to
open passages, with keys and doors still balanced per colour.
"""
import collections
import random

import pytest

import levels
from crafting import KEY_COLORS
from levelgraph import LevelGraph, EdgeType, NodeSize
from levellayout import build_level_dict, LayoutError

CAP = 4
MAX_DOORS = CAP * len(KEY_COLORS)   # 28


def _graph_counts(g):
    keys = collections.Counter()
    doors = collections.Counter()
    for node in g.nodes.values():
        for (c,) in node.keys:
            keys[c] += 1
    for e in g.edges:
        if e.edge_type == EdgeType.LOCKED:
            doors[e.params['key_colour']] += 1
    return keys, doors


FORCED = {
    'room_count': (40, 40),
    'edge_types': [EdgeType.LOCKED],
    'node_sizes': [NodeSize.ROOM],
    'layout_strategies': ['horizontal', 'vertical', 'off_centre',
                          'double_t', 't', 'z', 'l'],
    'grid_count': 1,
}


@pytest.mark.parametrize('seed', range(12))
def test_forced_overflow_caps_at_four(seed):
    """A single grid demanding 40 locked rooms must cap at 4/colour, 28 doors,
    with the overflow downgraded to open passages and no orphan keys."""
    g = LevelGraph.generate(FORCED, random.Random(seed))
    keys, doors = _graph_counts(g)
    assert doors, f"seed={seed}: expected some locked doors"
    assert max(keys.values()) <= CAP, \
        f"seed={seed}: {max(keys.values())} keys of one colour > {CAP}: {dict(keys)}"
    assert max(doors.values()) <= CAP, \
        f"seed={seed}: {max(doors.values())} doors of one colour > {CAP}: {dict(doors)}"
    assert sum(doors.values()) <= MAX_DOORS, \
        f"seed={seed}: {sum(doors.values())} locked doors > {MAX_DOORS}"
    # R-K1: no orphan keys / key-less doors, per colour
    for c in set(keys) | set(doors):
        assert keys[c] == doors[c], \
            f"seed={seed} colour={c}: keys={keys[c]} != doors={doors[c]}"


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


@pytest.mark.parametrize('seed', range(6))
def test_shipping_levels_within_cap(seed):
    """Real Act 2 levels 11-20 stay within 4/colour and 28 doors."""
    for idx, fs in enumerate(levels.ACT2_FEATURE_SETS):
        lv = _build(fs, seed)
        keys = collections.Counter()
        doors = collections.Counter()
        for rd in lv['rooms'].values():
            for k in rd.get('keys', []):
                keys[k[2]] += 1
            for d in rd.get('locked_doors', []):
                doors[d[2]] += 1
        level_no = 11 + idx
        if keys:
            assert max(keys.values()) <= CAP, \
                f"seed={seed} L{level_no}: {max(keys.values())} keys/colour: {dict(keys)}"
        if doors:
            assert sum(doors.values()) <= MAX_DOORS, \
                f"seed={seed} L{level_no}: {sum(doors.values())} locked doors"
        for c in set(keys) | set(doors):
            assert keys[c] == doors[c], \
                f"seed={seed} L{level_no} colour={c}: keys={keys[c]} != doors={doors[c]}"
