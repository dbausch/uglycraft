"""Spec 0058 (BL-20+) — enemy & award economy.

Enemies leave the graph phase; a level-wide layout distributor places
exactly 2 × G enemies by room size (largest all-floor square s, capacity
s − 2, corridor banned).  Award items exist only as challenge rewards
(one per locked / gated / flame / water room, graph phase) or guard
rewards (one per enemy, layout phase).  Challenge counts scale with the
grid count: max(1, G // 2) flame rooms, max(1, G // 3) water rooms.

Red when written: add_enemies draws 1–7 enemies level-wide regardless of
G, add_treasures sprinkles 6–18 unmotivated awards, feature sets still
carry treasure_count / enemy_count / WATER-in-edge_types, and the
distributor does not exist.
"""
import random

import pytest
from hypothesis import given, settings, strategies as st

import levels
from levelgraph import LevelGraph, EdgeType, NodeSize
from levellayout import build_level_dict, LayoutError

FS = levels.ACT2_FEATURE_SETS          # indices 0..9 = levels 11..20


# ── Shared build cache (generation is expensive; every sweep reuses it) ──────

_BUILDS = {}


def _build(fs_idx, seed):
    key = (fs_idx, seed)
    if key not in _BUILDS:
        fs = FS[fs_idx]
        base = random.Random(seed)
        for _ in range(60):
            rng = random.Random(base.randint(0, 2 ** 31))
            g = LevelGraph.generate(fs, rng)
            try:
                lv = build_level_dict(g, rng=rng,
                                      strategies=fs.get('layout_strategies'))
                _BUILDS[key] = (g, lv)
                break
            except LayoutError:
                continue
        else:
            raise AssertionError(f"build failed fs={fs_idx} seed={seed}")
    return _BUILDS[key]


# Sweep scope: grid counts 1–6 (levels 11–16) with two seeds; the
# expensive late levels (7–10 grids) with one pinned seed each — chosen
# because they violated the 2 × G total before the spec-0060 room
# rescale (red then, capacity gate since).  The scratchpad detector
# covers more seeds.
_SWEEP = ([(i, s) for i in range(6) for s in range(2)]
          + [(6, 4), (7, 4), (8, 1), (9, 2)])


# ── Helpers (independent re-implementations, not the layout's own code) ──────

def _largest_square(tiles):
    """Side of the largest all-floor square inside a tile set (DP)."""
    ts = set(tiles)
    dp = {}
    best = 0
    for t in sorted(ts):
        c, r = t
        dp[t] = 1 + min(dp.get((c - 1, r), 0), dp.get((c, r - 1), 0),
                        dp.get((c - 1, r - 1), 0))
        best = max(best, dp[t])
    return best


def _floors_by_owner(rd):
    owners = {}
    for t, o in rd['tile_owner'].items():
        owners.setdefault(o, set()).add(t)
    return owners


def _corridor_names(graph):
    return {n for n, nd in graph.nodes.items()
            if nd.size == NodeSize.CORRIDOR}


def _flame_owners(lv):
    """Rooms owning flame-jet tiles — the dict-level truth (spec 0062:
    flames are layout-placed; the graph carries no flame data)."""
    owners = set()
    for rd in lv['rooms'].values():
        to = rd['tile_owner']
        for jet in rd.get('flame_jets', []):
            owners.add(to.get(tuple(jet['tiles'][0])))
    return owners


def _challenge_rooms(graph, lv):
    """Rooms protected by a challenge: behind a LOCKED/GATED/WATER edge
    (graph), or owning real flame jets (dict, spec 0062)."""
    prot = _flame_owners(lv)
    for e in graph.edges:
        if e.edge_type in (EdgeType.LOCKED, EdgeType.GATED, EdgeType.WATER):
            prot.add(e.node_b)
    return prot


def _candidate_rooms(graph, lv):
    """Enemy-host candidates: non-corridor, no blocks/plates, not a
    flame room (dict-level, spec 0062)."""
    flames = _flame_owners(lv)
    return [n for n, nd in graph.nodes.items()
            if nd.size != NodeSize.CORRIDOR
            and not nd.blocks and not nd.plates and n not in flames]


def _enemy_starts(lv):
    """[(grid, (c, r), etype)] across all grids."""
    out = []
    for gname, rd in lv['rooms'].items():
        for c, r, etype in rd.get('enemy_starts', []):
            out.append((gname, (c, r), etype))
    return out


def _award_owners(lv):
    """{(grid, owner): count} for every treasure item."""
    counts = {}
    for gname, rd in lv['rooms'].items():
        to = rd['tile_owner']
        for c, r, _no in rd.get('treasures', []):
            owner = to.get((c, r))
            counts[(gname, owner)] = counts.get((gname, owner), 0) + 1
    return counts


# ── 1+2: size rule, corridor ban, enemy total ────────────────────────────────

@pytest.mark.parametrize('fs_idx,seed', _SWEEP)
def test_enemy_size_rule_and_total(fs_idx, seed):
    graph, lv = _build(fs_idx, seed)
    G = FS[fs_idx].get('grid_count', 1)
    cor = _corridor_names(graph)

    candidates = set(_candidate_rooms(graph, lv))
    per_room = {}
    for gname, rd in lv['rooms'].items():
        owners = _floors_by_owner(rd)
        for c, r, etype in rd.get('enemy_starts', []):
            owner = rd['tile_owner'].get((c, r))
            assert owner is not None, f"enemy start {(c, r)} not on floor"
            assert owner not in cor, (
                f"fs={fs_idx} seed={seed}: enemy start {(c, r)} in "
                f"corridor {owner!r} on {gname}")
            # R-F1 successor: hosts are candidate rooms only — never a
            # flame, plate, or block room (was a graph-level lock in
            # test_placement_rules before spec 0058).
            assert owner in candidates, (
                f"fs={fs_idx} seed={seed}: enemy in non-candidate room "
                f"{owner!r} (flames/plates/blocks) on {gname}")
            per_room[(gname, owner)] = per_room.get((gname, owner), 0) + 1

    for (gname, owner), k in per_room.items():
        floors = _floors_by_owner(lv['rooms'][gname])[owner]
        s = _largest_square(floors)
        assert k <= s - 2, (
            f"fs={fs_idx} seed={seed}: room {owner!r} on {gname} holds "
            f"{k} enemies but s={s} (capacity {s - 2})")

    total = len(_enemy_starts(lv))
    assert total == 2 * G, (
        f"fs={fs_idx} seed={seed}: {total} enemies, expected {2 * G}")

    # Capacity never limits real feature sets (else 2×G could not be met).
    cap = 0
    for gname, rd in lv['rooms'].items():
        owners = _floors_by_owner(rd)
        for name in _candidate_rooms(graph, lv):
            if name in owners:
                cap += max(0, _largest_square(owners[name]) - 2)
    assert cap >= 2 * G, (
        f"fs={fs_idx} seed={seed}: capacity {cap} < {2 * G}")


# ── 3+5: award economy and guard-award pairing ───────────────────────────────

@pytest.mark.parametrize('fs_idx,seed', _SWEEP)
def test_award_economy(fs_idx, seed):
    graph, lv = _build(fs_idx, seed)
    cor = _corridor_names(graph)
    protected = _challenge_rooms(graph, lv)

    awards = _award_owners(lv)
    enemies = {}
    for gname, pos, _t in _enemy_starts(lv):
        owner = lv['rooms'][gname]['tile_owner'][pos]
        enemies[(gname, owner)] = enemies.get((gname, owner), 0) + 1

    # Per room: awards == challenge reward (0/1) + one per enemy.  The
    # corridor may hold awards only as full-room spill overflow, which the
    # total-conservation check below still balances.
    for (gname, owner), n in awards.items():
        if owner in cor:
            continue
        expected = (1 if owner in protected else 0) + \
            enemies.get((gname, owner), 0)
        assert n == expected, (
            f"fs={fs_idx} seed={seed}: room {owner!r} on {gname} has {n} "
            f"awards, expected {expected} (challenge="
            f"{owner in protected}, enemies={enemies.get((gname, owner), 0)})")
    for (gname, owner), k in enemies.items():
        got = awards.get((gname, owner), 0)
        expected = (1 if owner in protected else 0) + k
        assert got == expected, (
            f"fs={fs_idx} seed={seed}: enemy room {owner!r} on {gname} has "
            f"{got} awards, expected {expected}")

    # Total conservation: #awards = #challenge rooms + #enemies placed.
    # (Challenge rooms dropped by the packer spill their award — it still
    # exists, so the total holds level-wide.)
    total_awards = sum(awards.values())
    expected_total = len(protected) + len(_enemy_starts(lv))
    assert total_awards == expected_total, (
        f"fs={fs_idx} seed={seed}: {total_awards} awards, expected "
        f"{expected_total} ({len(protected)} challenges + "
        f"{len(_enemy_starts(lv))} enemies)")


# ── 4: directed distributor tests (pure core, synthetic sizes) ───────────────

def _dist(sizes, count, seed=0, forge=False):
    from levellayout import _enemy_distribution
    return _enemy_distribution(sizes, count, random.Random(seed), forge=forge)


def test_distribution_first_enemy_biggest_room():
    got = _dist([('a', 4), ('b', 9), ('c', 5)], 1)
    assert [r for r, _t in got] == ['b']


def test_distribution_round_robin_before_doubling():
    got = _dist([('a', 9), ('b', 5)], 3)
    assert [r for r, _t in got] == ['a', 'b', 'a']


def test_distribution_largest_effective_within_round():
    # After a gets 2, e(a)=7 still beats e(b)=5: order a, b? No — round-robin
    # first: a(e9), b(e5), then k equal again: a(e8) beats b(e4), then b.
    got = _dist([('a', 9), ('b', 5)], 4)
    assert [r for r, _t in got] == ['a', 'b', 'a', 'b']


def test_distribution_capacity_caps_room():
    # s=3 → capacity 1; s=4 → capacity 2.
    got = _dist([('a', 3)], 3)
    assert [r for r, _t in got] == ['a']
    got = _dist([('a', 4)], 5)
    assert [r for r, _t in got] == ['a', 'a']


def test_distribution_drop_past_capacity_no_error():
    assert _dist([], 4) == []
    got = _dist([('a', 3), ('b', 3)], 6)
    assert len(got) == 2


def test_distribution_forge_first():
    got = _dist([('a', 5), ('b', 9)], 3, forge=True)
    assert got[0] == ('b', 'forge_ogre')
    assert all(t == 'chaser' for _r, t in got[1:])


@given(st.integers(0, 2 ** 32 - 1))
@settings(max_examples=50, deadline=None)
def test_distribution_invariants(seed):
    rng = random.Random(seed)
    sizes = [(f'r{i}', rng.randint(2, 9))
             for i in range(rng.randint(0, 8))]
    count = rng.randint(0, 20)
    got = _dist(sizes, count, seed=seed + 1)
    per = {}
    for r, _t in got:
        per[r] = per.get(r, 0) + 1
    smap = dict(sizes)
    for r, k in per.items():
        assert k <= smap[r] - 2
    cap = sum(max(0, s - 2) for _r, s in sizes)
    assert len(got) == min(count, cap)


# ── 6: forge guard ────────────────────────────────────────────────────────────

def test_forge_ogre_unique_and_in_biggest_room():
    fs_idx = 5                             # level 16, first forge level
    assert FS[fs_idx].get('has_forge_ogre'), "level 16 must have the forge"
    graph, lv = _build(fs_idx, 0)
    forge = [(g, pos) for g, pos, t in _enemy_starts(lv)
             if t == 'forge_ogre']
    assert len(forge) == 1, f"expected exactly one forge ogre, got {forge}"
    gname, pos = forge[0]
    owner = lv['rooms'][gname]['tile_owner'][pos]
    s_forge = _largest_square(_floors_by_owner(lv['rooms'][gname])[owner])
    s_max = 0
    for gn, rd in lv['rooms'].items():
        owners = _floors_by_owner(rd)
        for name in _candidate_rooms(graph, lv):
            if name in owners:
                s_max = max(s_max, _largest_square(owners[name]))
    assert s_forge == s_max, (
        f"forge in room with s={s_forge}, but max candidate s={s_max}")


# ── 7: graph phase ────────────────────────────────────────────────────────────

@pytest.mark.parametrize('fs_idx', range(10))
def test_graph_awards_and_challenge_scaling(fs_idx):
    fs = FS[fs_idx]
    G = fs.get('grid_count', 1)
    for seed in range(3):
        g = LevelGraph.generate(fs, random.Random(seed))
        # Graph awards belong to graph challenges only: locked/gated/water.
        # Flames are layout-placed since spec 0062 (their award too) —
        # scaling and integrity are locked in tests/test_flames.py.
        protected = {e.node_b for e in g.edges
                     if e.edge_type in (EdgeType.LOCKED, EdgeType.GATED,
                                        EdgeType.WATER)}
        for name, node in g.nodes.items():
            assert not getattr(node, 'enemies', []), (
                f"fs={fs_idx} seed={seed}: graph node {name!r} carries "
                f"enemy data")
            expected = 1 if name in protected else 0
            assert len(node.treasures) == expected, (
                f"fs={fs_idx} seed={seed}: node {name!r} has "
                f"{len(node.treasures)} awards, expected {expected}")

        if fs.get('has_water'):
            water_rooms = sum(1 for e in g.edges
                              if e.edge_type == EdgeType.WATER)
            want = max(1, G // 3)
            assert water_rooms == want, (
                f"fs={fs_idx} seed={seed}: {water_rooms} water rooms, "
                f"expected {want}")


# ── 8: feature-set contract ──────────────────────────────────────────────────

def test_feature_sets_retired_keys_and_water_flag():
    for i, fs in enumerate(FS):
        level = 11 + i
        assert 'treasure_count' not in fs, f"level {level}: treasure_count"
        assert 'enemy_count' not in fs, f"level {level}: enemy_count"
        assert EdgeType.WATER not in fs.get('edge_types', []), (
            f"level {level}: WATER still in the stochastic edge draw")
        if level >= 14:
            assert fs.get('has_water') is True, (
                f"level {level}: has_water missing")
