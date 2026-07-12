"""Graph playability, tile-ownership, and enemy-placement invariants.

Salvaged from the pre-`tests/`-reorganisation root-level `test_levelgraph.py`
(removed 2026-07-12, it was never run by `poe test` which is scoped to
`tests/`).  These are the cases with **no equivalent elsewhere in `tests/`**:

- `validate_playability()` exercised directly over hand-built graphs, every
  edge type including the failure modes (`tests/test_graph_building` covers
  only positive builder-produced graphs; `tests/test_water_challenge` only
  the water negatives).
- `build_tile_owner` ownership invariants.
- the enemy-distance-from-player placement rule.

The rest of the old file (Node/Edge/graph basics, generation, layout,
push-puzzle solvability, `build_level_dict` format, entrance rules) is
already covered by test_graph_building, test_world_graph, test_layout,
test_sokoban, test_entrance, test_placement_rules, etc.
"""
import random
from collections import deque

from constants import COLS, ROWS
from levelgraph import LevelGraph, NodeSize, EdgeType
from levellayout import (layout_graph, build_level_dict, build_tile_owner,
                         MIN_ENEMY_DIST)
from crafting import MAT_ROCKS


class TestPlayability:
    """`validate_playability()` over hand-built graphs — every edge type and
    its failure modes."""

    def test_all_open_is_playable(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('room', NodeSize.ROOM)
        g.add_edge('corridor', 'room', EdgeType.OPEN)
        g.nodes['room'].treasures.append((5,))
        assert g.validate_playability() == []

    def test_breakable_is_playable(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('room', NodeSize.ROOM)
        g.add_edge('corridor', 'room', EdgeType.BREAKABLE)
        g.nodes['room'].treasures.append((3,))
        assert g.validate_playability() == []

    def test_locked_with_key_is_playable(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('vault', NodeSize.ROOM)
        g.add_edge('corridor', 'vault', EdgeType.LOCKED, key_colour='red')
        g.nodes['corridor'].keys.append(('red',))
        g.nodes['vault'].treasures.append((9,))
        assert g.validate_playability() == []

    def test_locked_without_key_fails(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('vault', NodeSize.ROOM)
        g.add_edge('corridor', 'vault', EdgeType.LOCKED, key_colour='red')
        g.nodes['vault'].treasures.append((9,))
        errors = g.validate_playability()
        assert any('unreachable' in e.lower() for e in errors)

    def test_locked_key_behind_same_door_fails(self):
        """Key is in the locked room — can't reach it without the door."""
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('vault', NodeSize.ROOM)
        g.add_edge('corridor', 'vault', EdgeType.LOCKED, key_colour='blue')
        g.nodes['vault'].keys.append(('blue',))
        g.nodes['vault'].treasures.append((7,))
        assert len(g.validate_playability()) > 0

    def test_gated_with_plate_and_block_is_playable(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('workshop', NodeSize.ROOM)
        g.add_node('vault', NodeSize.ROOM)
        g.add_edge('corridor', 'workshop', EdgeType.OPEN)
        g.add_edge('corridor', 'vault', EdgeType.GATED, gate_id='g1')
        g.nodes['workshop'].plates.append(('g1',))
        g.nodes['workshop'].blocks.append(1)
        g.nodes['vault'].treasures.append((4,))
        assert g.validate_playability() == []

    def test_gated_without_block_fails(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('vault', NodeSize.ROOM)
        g.add_edge('corridor', 'vault', EdgeType.GATED, gate_id='g1')
        g.nodes['corridor'].plates.append(('g1',))
        g.nodes['vault'].treasures.append((4,))
        assert len(g.validate_playability()) > 0

    def test_gated_without_plate_fails(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('vault', NodeSize.ROOM)
        g.add_edge('corridor', 'vault', EdgeType.GATED, gate_id='g1')
        g.nodes['corridor'].blocks.append(1)
        g.nodes['vault'].treasures.append((4,))
        assert len(g.validate_playability()) > 0

    def test_chained_locks(self):
        """Key for door B is behind door A. Must open A first."""
        g = LevelGraph()
        g.add_node('start', NodeSize.CORRIDOR, is_start=True)
        g.add_node('room_a', NodeSize.ROOM)
        g.add_node('room_b', NodeSize.ROOM)
        g.add_edge('start', 'room_a', EdgeType.LOCKED, key_colour='red')
        g.add_edge('start', 'room_b', EdgeType.LOCKED, key_colour='blue')
        g.nodes['start'].keys.append(('red',))
        g.nodes['room_a'].keys.append(('blue',))
        g.nodes['room_b'].treasures.append((9,))
        assert g.validate_playability() == []

    def test_empty_node_unreachable_still_reported(self):
        g = LevelGraph()
        g.add_node('start', NodeSize.CORRIDOR, is_start=True)
        g.add_node('island', NodeSize.ROOM)
        errors = g.validate_playability()
        assert any('island' in e for e in errors)

    def test_no_start_node(self):
        g = LevelGraph()
        g.add_node('room', NodeSize.ROOM)
        errors = g.validate_playability()
        assert any('start' in e.lower() for e in errors)

    def test_stairs_are_passable(self):
        g = LevelGraph()
        g.add_node('floor1', NodeSize.CORRIDOR, is_start=True)
        g.add_node('floor2', NodeSize.ROOM)
        g.add_edge('floor1', 'floor2', EdgeType.STAIRS)
        g.nodes['floor2'].treasures.append((1,))
        assert g.validate_playability() == []


class TestTileOwnership:
    """`build_tile_owner` over a laid-out graph: every room floor tile has
    exactly one owner; doorway (transition) tiles are unowned."""

    def test_room_floor_has_owner(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('room', NodeSize.ROOM)
        g.add_edge('corridor', 'room', EdgeType.OPEN)
        placed = layout_graph(g, rng=random.Random(0))
        owner = build_tile_owner(placed)
        for name, pn in placed.items():
            for tile in pn.floor_tiles:
                assert tile in owner, f"Room {name} floor tile {tile} has no owner"
                assert owner[tile] == name

    def test_no_tile_has_two_owners(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('a', NodeSize.ROOM)
        g.add_node('b', NodeSize.ROOM)
        g.add_edge('corridor', 'a', EdgeType.OPEN)
        g.add_edge('corridor', 'b', EdgeType.OPEN)
        placed = layout_graph(g, rng=random.Random(0))
        seen = {}
        for name, pn in placed.items():
            for tile in pn.floor_tiles:
                assert tile not in seen, (
                    f"Tile {tile} owned by both {seen.get(tile)} and {name}")
                seen[tile] = name


class TestEnemyPlacement:
    """Enemy placement invariants, exercised end-to-end through
    build_level_dict."""

    def test_enemy_rooms_have_a_guard_award(self):
        """Post-refactor (spec 0058): enemies are placed at layout time by
        `_distribute_enemies`, and every enemy adds a guard award (a
        treasure) to its room — so any built room with `enemy_starts` has
        `treasures`.  (Replaces the old graph-side `node.enemies` check;
        `Node` no longer carries enemies.)"""
        features = {
            'room_count': (3, 5),
            'edge_types': [EdgeType.OPEN, EdgeType.BREAKABLE],
            'node_sizes': [NodeSize.ROOM, NodeSize.HALL],
            'treasure_count': (4, 8),
            'material_types': [MAT_ROCKS],
            'material_count': (3, 6),
            'enemy_count': (3, 4),
        }
        for seed in range(20):
            rng = random.Random(seed)
            g = LevelGraph.generate(features, rng=rng)
            if g.validate_playability():
                continue
            level = build_level_dict(g, rng=rng)
            saw_enemy_room = False
            for gname, rd in level['rooms'].items():
                if rd.get('enemy_starts'):
                    saw_enemy_room = True
                    assert rd.get('treasures'), (
                        f"seed={seed}: grid {gname!r} has enemies but no treasure")
            assert saw_enemy_room, f"seed={seed}: no enemies placed at all"

    def test_enemies_far_from_player(self):
        features = {
            'room_count': (3, 4),
            'edge_types': [EdgeType.OPEN],
            'node_sizes': [NodeSize.ROOM, NodeSize.HALL],
            'treasure_count': (4, 6),
            'material_types': [MAT_ROCKS],
            'material_count': (2, 3),
            'enemy_count': (2, 3),
        }
        for seed in range(10):
            rng = random.Random(seed)
            g = LevelGraph.generate(features, rng=rng)
            if g.validate_playability():
                continue
            level = build_level_dict(g, rng=rng)
            room = level['rooms']['main']
            pc, pr = level['player_start']
            walls = room['walls']
            passable = {(c, r)
                        for c in range(1, COLS - 1)
                        for r in range(1, ROWS - 1)
                        if (c, r) not in walls}
            dist = {(pc, pr): 0}
            q = deque([(pc, pr)])
            while q:
                cx, cy = q.popleft()
                for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nc, nr = cx + dc, cy + dr
                    if (nc, nr) in passable and (nc, nr) not in dist:
                        dist[(nc, nr)] = dist[(cx, cy)] + 1
                        q.append((nc, nr))
            for edata in room.get('enemy_starts', []):
                ec, er = edata[0], edata[1]
                d = dist.get((ec, er), 0)
                assert d >= MIN_ENEMY_DIST // 2, (
                    f"Seed {seed}: enemy at ({ec},{er}) only {d} tiles from player")
