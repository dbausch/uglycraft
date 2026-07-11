"""Placement-rule invariants for level generation.

Rules documented in spec/phase3-hazards.md § Placement Rules.

R-F1  Flames and enemies never share a room.
R-F2  Flame rooms are never behind a WATER edge.
R-F3  Jet never placed at entry row/column  (verified via R-F3a: far_tiles non-empty).
R-F4  Awards in flame rooms are only on the far side of the jet.
R-F5  Flame placement happens before enemy distribution → always placed.
R-W1  Water edge planks are only in non-water rooms (player's side).
"""

import random

from hypothesis import given, settings, strategies as st

from levelgraph import LevelGraph, EdgeType
from levellayout import build_level_dict, LayoutError
from tests.conftest import FS_FLAMES, FS_GATED, FS_WATER, FS_WATER_FLAMES


# ── R-F1: flames and enemies never share a room ───────────────────────────────
# Enemies left the graph phase with spec 0058; the invariant is now enforced
# at layout (enemy hosts are candidate rooms only) and locked by
# tests/test_enemy_room_size.py::test_enemy_size_rule_and_total.


# ── R-F2: flame rooms never behind a WATER edge ───────────────────────────────

@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=200)
def test_flame_room_never_has_water_edge(seed):
    """R-F2 successor: flames are layout-placed since spec 0062; the
    _place_flames candidate pool excludes rooms behind a WATER edge.
    Checked on the built dict."""
    from tests.test_flames import _flame_rooms
    rng = random.Random(seed)
    graph = LevelGraph.generate(FS_WATER_FLAMES, rng)
    try:
        level = build_level_dict(graph, rng=rng)
    except LayoutError:
        return
    water_rooms = {e.node_b for e in graph.edges
                   if e.edge_type == EdgeType.WATER}
    flame_owners = {owner for (_gn, owner) in _flame_rooms(level)}
    assert not (flame_owners & water_rooms), (
        f"flame rooms behind a WATER edge: {flame_owners & water_rooms}")


# ── R-F3a: jet far_tiles non-empty (proves entry tile is never inside a jet) ──

@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=50, deadline=15000)
def test_flame_jet_far_tiles_nonempty(seed):
    rng = random.Random(seed)
    graph = LevelGraph.generate(FS_FLAMES, rng)
    level = build_level_dict(graph, rng=rng)
    room = next(iter(level['rooms'].values()))
    for jet in room.get('flame_jets', []):
        assert jet.get('far_tiles'), (
            f"Flame jet at source={jet.get('source')} has no far_tiles"
        )


# ── R-F4: awards in flame rooms are only on the far side ─────────────────────

@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=50, deadline=15000)
def test_flame_room_awards_on_far_side(seed):
    """Each flame jet has at least one treasure in its far_tiles; none on beam."""
    rng = random.Random(seed)
    graph = LevelGraph.generate(FS_FLAMES, rng)
    level = build_level_dict(graph, rng=rng)
    room = next(iter(level['rooms'].values()))
    jets = room.get('flame_jets', [])
    if not jets:
        return

    treasures = {(tc, tr) for tc, tr, _ in room.get('treasures', [])}

    for jet in jets:
        far: set = set(jet.get('far_tiles', []))
        beam: set = set(jet.get('tiles', [])) | {jet['source']}

        # No treasure sits on the beam itself
        on_beam = treasures & beam
        assert not on_beam, (
            f"Treasure(s) {on_beam} are inside the flame jet beam"
        )

        # At least one award landed on the far side (when a far side exists)
        if far:
            assert treasures & far, (
                f"No award on far side of flame jet at source={jet['source']}"
            )


# ── R-F5: has_flames level always gets a flame node ──────────────────────────

@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=200)
def test_flames_always_placed_when_requested(seed):
    """R-F5 successor: flames are layout-placed since spec 0062 — a
    has_flames level either carries real jets in the dict or the build
    raises LayoutError (fresh-seed retry); it is never silently
    flameless."""
    from tests.test_flames import _flame_rooms
    rng = random.Random(seed)
    graph = LevelGraph.generate(FS_FLAMES, rng)
    try:
        level = build_level_dict(graph, rng=rng)
    except LayoutError:
        return
    assert _flame_rooms(level), (
        "has_flames level built without a single flame room")


# ── R-W1: water edge planks only in non-water rooms ──────────────────────────

@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=200)
def test_water_planks_not_in_water_rooms(seed):
    graph = LevelGraph.generate(FS_WATER, random.Random(seed))
    water_far_nodes = {
        e.node_b for e in graph.edges if e.edge_type == EdgeType.WATER
    }
    for name in water_far_nodes:
        node = graph.nodes[name]
        assert not any(m == ('planks',) for m in node.materials), (
            f"Water room {name!r} contains planks — must be on player's side"
        )


# ── Spec 0049: plates never flank water (buildable-passage landings) ──────────

from levelgraph import NodeSize
from levellayout import LayoutError

FS_GATED_WATER = {
    'room_count':     (4, 6),
    'edge_types':     [EdgeType.OPEN, EdgeType.GATED, EdgeType.WATER],
    'node_sizes':     [NodeSize.ROOM, NodeSize.HALL],
    'treasure_count': (3, 5),
    'material_types': ['planks'],
    'material_count': (0, 0),
    'enemy_count':    (0, 0),
}


@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=50, deadline=None)
def test_plates_never_flank_water(seed):
    """A plate cardinally adjacent to water would sit on the landing tile
    of a buildable bridge passage (spec 0049 P3)."""
    graph = LevelGraph.generate(FS_GATED_WATER, random.Random(seed))
    try:
        level = build_level_dict(graph, rng=random.Random(seed))
    except LayoutError:
        return                       # retryable seed; nothing to assert
    for room in level['rooms'].values():
        water = {tuple(t) for t in room.get('water_tiles', [])}
        if not water:
            continue
        for pc, pr, _gid in room.get('pressure_plates', []):
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                assert (pc + dc, pr + dr) not in water, (
                    f'seed {seed}: plate ({pc},{pr}) flanks water '
                    f'{(pc + dc, pr + dr)}')


@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=50, deadline=None)
def test_plates_never_on_landing_tiles(seed):
    """R-P7 doorway half, reconstructed from the level dict: no plate is
    cardinally adjacent to a passage tile — an unowned tile that is an
    open hole / non-reinforced wall / door / gate touching floor of a
    second room.  (Caught the orig_walls bug: 61/1400 plates violated
    pre-0049, 9/1400 after the first fix attempt.)"""
    graph = LevelGraph.generate(FS_GATED, random.Random(seed))
    try:
        level = build_level_dict(graph, rng=random.Random(seed))
    except LayoutError:
        return
    for room in level['rooms'].values():
        owners = room.get('tile_owner', {})
        walls = room['walls']
        openable = {(c, r) for c, r, _ in room.get('locked_doors', [])}
        openable |= {(c, r) for c, r, _ in room.get('gates', [])}
        water = {tuple(t) for t in room.get('water_tiles', [])}

        def is_passage(pos, owner):
            if pos in owners or pos in water:
                return False
            if (walls.get(pos) == 'reinforced' and pos not in openable):
                return False
            others = {owners.get((pos[0] + dc, pos[1] + dr))
                      for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))}
            others.discard(None)
            others.discard(owner)
            return bool(others)

        for pc, pr, gid in room.get('pressure_plates', []):
            owner = owners.get((pc, pr))
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                npos = (pc + dc, pr + dr)
                assert not is_passage(npos, owner), (
                    f'seed {seed}: plate ({pc},{pr}) on landing tile of '
                    f'passage {npos}')
