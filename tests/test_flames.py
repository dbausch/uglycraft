"""Spec 0062 — flames placed after layout, in rooms that can host them.

The graph carries no flame data; a level-wide layout pass picks
jet-capable rooms (max(1, G // 2) per has_flames level), relocates
items off the jet line, and places the flame challenge award on a far
tile.  Flame rooms are disjoint from enemy and push-puzzle rooms.

Red when written: add_flames marks Node.has_flames at graph time with
no geometry knowledge — jet generation fails silently in small rooms
(post-0060), leaving flame rooms without jets but with a freely
accessible award, and the flame count in the dict undershoots the
max(1, G // 2) promise.
"""
import random

import pytest

from uglycraft import levels
from uglycraft.levelgraph import LevelGraph, EdgeType, NodeSize
from uglycraft.levellayout import build_level_dict, LayoutError

FS = levels.ACT2_FEATURE_SETS
_FLAME_FS = [i for i, fs in enumerate(FS) if fs.get('has_flames')]

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
                _BUILDS[key] = (g, build_level_dict(
                    g, rng=rng, strategies=fs.get('layout_strategies')))
                break
            except LayoutError:
                continue
        else:
            raise AssertionError(f"build failed fs={fs_idx} seed={seed}")
    return _BUILDS[key]


def _flame_rooms(lv):
    """{(grid, owner): [jet, ...]} — dict-level truth, via jet tiles."""
    out = {}
    for gn, rd in lv['rooms'].items():
        to = rd['tile_owner']
        for jet in rd.get('flame_jets', []):
            owner = to.get(tuple(jet['tiles'][0]))
            out.setdefault((gn, owner), []).append(jet)
    return out


def _items_by_room(lv, kinds=('treasures', 'materials', 'keys')):
    out = {}
    for gn, rd in lv['rooms'].items():
        to = rd['tile_owner']
        for kind in kinds:
            for entry in rd.get(kind, []):
                pos = (entry[0], entry[1])
                out.setdefault((gn, to.get(pos)), []).append((kind, pos))
    return out


# ── Flame count, far-tile award, jet-line clearance ──────────────────────────

@pytest.mark.parametrize('fs_idx', _FLAME_FS)
@pytest.mark.parametrize('seed', [0, 1])
def test_flame_count_and_integrity(fs_idx, seed):
    _g, lv = _build(fs_idx, seed)
    G = FS[fs_idx].get('grid_count', 1)
    frooms = _flame_rooms(lv)
    assert len(frooms) == max(1, G // 2), (
        f"fs={fs_idx} seed={seed}: {len(frooms)} flame rooms in the dict, "
        f"expected {max(1, G // 2)}")

    treasures = _items_by_room(lv, kinds=('treasures',))
    items = _items_by_room(lv)
    for (gn, owner), jets in frooms.items():
        far = {tuple(t) for j in jets for t in j.get('far_tiles', [])}
        assert far, (
            f"fs={fs_idx} seed={seed}: jets of {owner!r} carry no far "
            f"tiles")
        room_awards = [pos for _k, pos in treasures.get((gn, owner), [])]
        assert len(room_awards) == 1, (
            f"fs={fs_idx} seed={seed}: flame room {owner!r} has "
            f"{len(room_awards)} awards, expected 1")
        assert room_awards[0] in far, (
            f"fs={fs_idx} seed={seed}: flame award {room_awards[0]} of "
            f"{owner!r} not on a far tile")
        jetline = {tuple(t) for j in jets for t in j['tiles']}
        jetline |= {tuple(j['source']) for j in jets}
        on_line = [(k, p) for k, p in items.get((gn, owner), [])
                   if p in jetline]
        assert not on_line, (
            f"fs={fs_idx} seed={seed}: items on the jet line of "
            f"{owner!r}: {on_line}")


# ── The jetless-flame defect: no award without a visible reason ─────────────

@pytest.mark.parametrize('fs_idx', _FLAME_FS)
@pytest.mark.parametrize('seed', [0, 1, 2])
def test_no_award_without_reason(fs_idx, seed):
    """Every award-bearing non-corridor room is challenge-protected
    (locked/gated/water edge, or owns real jets) or hosts an enemy.
    Red today: jetless flame rooms keep their award with no visible
    challenge (the room_18 case, sweep 2026-07-12)."""
    graph, lv = _build(fs_idx, seed)
    cor = {n for n, nd in graph.nodes.items()
           if nd.size == NodeSize.CORRIDOR}
    protected = {e.node_b for e in graph.edges
                 if e.edge_type in (EdgeType.LOCKED, EdgeType.GATED,
                                    EdgeType.WATER)}
    protected |= {owner for (_gn, owner) in _flame_rooms(lv)}
    enemy_rooms = set()
    for gn, rd in lv['rooms'].items():
        to = rd['tile_owner']
        for c, r, _t in rd.get('enemy_starts', []):
            enemy_rooms.add(to.get((c, r)))
    for (gn, owner), entries in _items_by_room(lv, ('treasures',)).items():
        if owner in cor:
            continue
        assert owner in protected or owner in enemy_rooms, (
            f"fs={fs_idx} seed={seed}: room {owner!r} on {gn} holds "
            f"{len(entries)} award(s) with no jets, no barrier, no enemy")


# ── Graph carries no flame data ───────────────────────────────────────────────

def test_graph_has_no_flame_data():
    for fs_idx in range(len(FS)):
        g = LevelGraph.generate(FS[fs_idx], random.Random(0))
        flagged = [n for n, nd in g.nodes.items()
                   if getattr(nd, 'has_flames', False)]
        assert not flagged, (
            f"fs={fs_idx}: graph nodes carry flame data: {flagged}")


# ── Disjointness: flames vs enemies vs push puzzles ──────────────────────────

@pytest.mark.parametrize('fs_idx', _FLAME_FS)
@pytest.mark.parametrize('seed', [0, 1])
def test_flame_rooms_disjoint(fs_idx, seed):
    graph, lv = _build(fs_idx, seed)
    flame_owners = {owner for (_gn, owner) in _flame_rooms(lv)}
    enemy_owners = set()
    for gn, rd in lv['rooms'].items():
        to = rd['tile_owner']
        for c, r, _t in rd.get('enemy_starts', []):
            enemy_owners.add(to.get((c, r)))
    puzzle_owners = {n for n, nd in graph.nodes.items()
                     if nd.blocks or nd.plates}
    assert not (flame_owners & enemy_owners), (
        f"fs={fs_idx} seed={seed}: {flame_owners & enemy_owners}")
    assert not (flame_owners & puzzle_owners), (
        f"fs={fs_idx} seed={seed}: {flame_owners & puzzle_owners}")
