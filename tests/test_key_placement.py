"""Key placement invariants (spec 0030).

K1  No key is dropped during layout: keys_dict == keys_graph.
K2  Every locked door (interior + border) has a surviving key of its colour
    somewhere in the level; no soft-lock. A barrier whose key is absent must be
    an open passage instead, never a locked door with no key.
K3  Graph-side key reachability is sound: validate_playability() == [].
"""
import random

import pytest
from hypothesis import given, settings, strategies as st

import levels as _levels
from levelgraph import LevelGraph, EdgeType, NodeSize
from levellayout import build_level_dict
from tests.conftest import FS_LOCKED, FS_ALL


# A crowded multi-grid locked feature set: high treasure_count fills rooms (to
# exercise key drops) and grid_count > 1 adds BORDER edges that may be locked
# (to exercise border-door placement during stitching).
FS_CROWDED_LOCKED = {
    'room_count':       (8, 12),
    'edge_types':       [EdgeType.OPEN, EdgeType.LOCKED],
    'node_sizes':       [NodeSize.ROOM, NodeSize.HALL],
    'treasure_count':   (12, 16),
    'material_types':   [],
    'material_count':   (0, 0),
    'enemy_count':      (0, 0),
    'closet_count':     (1, 2),
    'grid_count':       3,
    'layout_strategies': ['horizontal', 'vertical', 'off_centre', 't',
                          'double_t', 'z'],
}

_FEATURE_SETS = (FS_LOCKED, FS_ALL, FS_CROWDED_LOCKED)


def _keys_graph(graph):
    return sum(len(n.keys) for n in graph.nodes.values())


def _level_key_stats(level):
    """Return (keys_dict, door_colours, surviving_key_colours)."""
    keys_dict = 0
    door_colours = []
    key_colours = set()
    for rd in level['rooms'].values():
        ks = rd.get('keys', [])
        keys_dict += len(ks)
        for k in ks:
            key_colours.add(k[2])
        for d in rd.get('locked_doors', []):
            door_colours.append(d[2])
    return keys_dict, door_colours, key_colours


def _build(fs, seed):
    """Build with the standard fresh-rng retry (mirrors _generate_act2).
    Since spec 0065 a dropped locked room aborts the attempt loudly, so a
    retry-less build would fail on seeds production simply retries."""
    from levellayout import LayoutError
    base = random.Random(seed)
    for _ in range(60):
        rng = random.Random(base.randint(0, 2 ** 31))
        graph = LevelGraph.generate(fs, rng)
        try:
            level = build_level_dict(graph, rng=rng,
                                     strategies=fs.get('layout_strategies'))
        except LayoutError:
            continue
        return graph, _keys_graph(graph), level
    raise AssertionError(f"build never succeeded seed={seed}")


# ── K1: no key is ever dropped (spec 0032 C7 spills an unplaced node's keys) ──
#
# Originally K1 was narrower ("every *placed* node's keys survive") because a node
# the layout could not place dropped its keys.  Spec 0032 C7 now spills an
# unplaced node's content into a placed room/corridor, so the guarantee is the
# full one: every key in the graph reaches the level dict.

@pytest.mark.parametrize('fs', _FEATURE_SETS)
@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=100, deadline=None)
def test_keys_never_dropped(fs, seed):
    graph, kg, level = _build(fs, seed)
    if kg == 0:
        return
    kd, _, _ = _level_key_stats(level)
    assert kd == kg, (
        f"seed={seed} fs grids={fs.get('grid_count', 1)}: "
        f"keys_graph={kg} keys_dict={kd} — a key was lost"
    )


# ── K2: every locked door has a surviving key (no soft-lock) ─────────────────

@pytest.mark.parametrize('fs', _FEATURE_SETS)
@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=100, deadline=None)
def test_no_softlocked_doors(fs, seed):
    graph, kg, level = _build(fs, seed)
    if kg == 0:
        return
    _, door_colours, key_colours = _level_key_stats(level)
    soft = [c for c in door_colours if c not in key_colours]
    assert not soft, (
        f"seed={seed} fs grids={fs.get('grid_count', 1)}: "
        f"locked doors with no key anywhere: {soft}"
    )


# ── K3: graph-side key reachability is sound ─────────────────────────────────

@pytest.mark.parametrize('fs', _FEATURE_SETS)
@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=200)
def test_graph_keys_reachable(fs, seed):
    graph = LevelGraph.generate(fs, random.Random(seed))
    assert graph.validate_playability() == [], (
        f"seed={seed}: validate_playability reported unreachable nodes"
    )


# ── R-K1 (spec 0061): barrier↔prerequisite pairing, prerequisites roam ────────
# Keys are never lost, so every LOCKED edge must yield a door: per colour,
# #keys == #locked doors.  Pre-fix, the per-grid coupling check elided any
# interior door whose key sat on another grid (orphan keys — 6/8 level-13
# seeds).  Gates: plates may roam like keys (D2); elision happens only at
# global surviving-plate scope.

import collections

from levellayout import LayoutError

COLS, ROWS = 30, 16


def _build_retry(fs, seed):
    """Build with the standard fresh-rng retry (mirrors _generate_act2)."""
    base = random.Random(seed)
    for _ in range(60):
        rng = random.Random(base.randint(0, 2 ** 31))
        g = LevelGraph.generate(fs, rng)
        try:
            return g, build_level_dict(g, rng=rng,
                                       strategies=fs.get('layout_strategies'))
        except LayoutError:
            continue
    raise AssertionError(f"build never succeeded seed={seed}")


def _colour_counts(level):
    keys = collections.Counter()
    doors = collections.Counter()
    for rd in level['rooms'].values():
        for k in rd.get('keys', []):
            keys[k[2]] += 1
        for d in rd.get('locked_doors', []):
            doors[d[2]] += 1
    return keys, doors


@pytest.mark.parametrize('fs', (*_FEATURE_SETS, _levels.ACT2_FEATURE_SETS[2]))
@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=25, deadline=None)
def test_key_door_pairing(fs, seed):
    """R-K1: for every colour, #keys == #locked doors (interior+border)."""
    _graph, level = _build_retry(fs, seed)
    keys, doors = _colour_counts(level)
    assert keys == doors, (
        f"seed={seed} fs grids={fs.get('grid_count', 1)}: "
        f"keys={dict(keys)} != doors={dict(doors)} — orphan keys or "
        f"key-less doors")


def test_pinned_dropped_locked_room():
    """FS_ALL seed 584 (BL-46 / spec 0065): the packer drops locked
    room_5 on the first build attempt; pre-fix its cyan door was silently
    elided while the spilled key survived (K1) — an orphan key violating
    R-K1.  Post-fix that attempt raises LayoutError and the retry yields
    a paired level.  Pinned explicitly so the regression does not depend
    on the local .hypothesis/ database."""
    _g, lv = _build_retry(FS_ALL, 584)
    keys, doors = _colour_counts(lv)
    assert keys == doors, f"keys={dict(keys)} doors={dict(doors)}"


def test_pinned_L13_orphan_keys():
    """Level-13 build seed 7 had 6 keys but only 2 doors pre-fix (spec 0061
    diagnosis, 2026-07-11): 4 interior doors elided because their keys sat
    on other grids."""
    import levels as _levels
    _g, lv = _build_retry(_levels.ACT2_FEATURE_SETS[2], 7)
    keys, doors = _colour_counts(lv)
    assert keys == doors, f"keys={dict(keys)} doors={dict(doors)}"


def test_missing_key_raises_loudly():
    """A LOCKED edge whose colour has no key anywhere in the graph must
    abort the build (LayoutError → fresh-seed retry), never silently
    degrade the door to an open passage."""
    from levelgraph import LevelGraphBuilder
    b = LevelGraphBuilder(random.Random(3))
    b.add_open_room()
    b.add_locked_room('red')
    g = b.build()
    for nd in g.nodes.values():
        nd.keys = [k for k in nd.keys if k[0] != 'red']
    with pytest.raises(LayoutError):
        build_level_dict(g, rng=random.Random(1))


def _gate_plate_grids(level):
    """([(gate_id, grid, is_interior)], {gate_id: plate_grid})."""
    gates = []
    plates = {}
    for gn, rd in level['rooms'].items():
        for c, r, gid in rd.get('gates', []):
            interior = 0 < c < COLS - 1 and 0 < r < ROWS - 1
            gates.append((gid, gn, interior))
        for c, r, gid in rd.get('pressure_plates', []):
            plates[gid] = gn
    return gates, plates


def test_interior_gate_plates_roam():
    """Spec 0061 D2: add_gated_room draws its puzzle room from every
    reachable room (any grid), so across a handful of builds some interior
    gate's plate must sit on a different grid.  Red pre-fix: structurally
    impossible (plates were same-grid by construction)."""
    from tests.test_border_continuity import FS_CROWDED_GATED
    cross = 0
    for seed in range(15):
        _g, lv = _build_retry(FS_CROWDED_GATED, seed)
        gates, plates = _gate_plate_grids(lv)
        cross += sum(1 for gid, gn, interior in gates
                     if interior and plates.get(gid) not in (None, gn))
    assert cross > 0, (
        "no interior gate with a cross-grid plate in 15 builds")


@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=15, deadline=None)
def test_gate_elision_scope(seed):
    """Gates are elided only when their plate genuinely did not survive
    (global scope): every gate entity has a surviving plate of its id,
    and every GATED edge between placed nodes whose plate survived has
    its gate entity — no over- or under-elision."""
    from tests.test_border_continuity import FS_CROWDED_GATED
    graph, lv = _build_retry(FS_CROWDED_GATED, seed)
    gates, plates = _gate_plate_grids(lv)
    gate_ids = {gid for gid, _gn, _i in gates}
    for gid, gn, _interior in gates:
        assert gid in plates, (
            f"seed={seed}: gate {gid!r} on {gn} has no surviving plate")
    placed_names = {o for rd in lv['rooms'].values()
                    for o in rd['tile_owner'].values()}
    for e in graph.edges:
        if e.edge_type != EdgeType.GATED:
            continue
        gid = e.params['gate_id']
        if (e.node_a in placed_names and e.node_b in placed_names
                and gid in plates):
            assert gid in gate_ids, (
                f"seed={seed}: GATED edge {e.node_a}->{e.node_b} placed, "
                f"plate survived, but gate {gid!r} was elided")
