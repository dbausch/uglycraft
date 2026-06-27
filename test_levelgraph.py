"""Tests for the graph-based level system."""
import random
import unittest
from constants import COLS, ROWS, WALL_REINFORCED, WALL_STONE, WALL_WOODEN
from levelgraph import LevelGraph, Node, Edge, NodeSize, EdgeType, SIZE_RANGES
from levellayout import (layout_graph, derive_walls, build_level_dict,
                          PlacedNode, _find_connection_tile,
                          validate_layout, build_tile_owner, MIN_ENEMY_DIST)
from crafting import MAT_ROCKS, MAT_PLANKS, MAT_METAL


# ── Graph model tests ─────────────────────────────────────────────────────────

class TestNode(unittest.TestCase):

    def test_node_creation(self):
        n = Node('storage', NodeSize.ROOM)
        self.assertEqual(n.name, 'storage')
        self.assertEqual(n.size, NodeSize.ROOM)
        self.assertFalse(n.is_start)
        self.assertEqual(n.treasures, [])

    def test_start_node(self):
        n = Node('corridor', NodeSize.CORRIDOR, is_start=True)
        self.assertTrue(n.is_start)


class TestEdge(unittest.TestCase):

    def test_open_edge(self):
        e = Edge('a', 'b', EdgeType.OPEN)
        self.assertEqual(e.edge_type, EdgeType.OPEN)

    def test_locked_edge(self):
        e = Edge('a', 'b', EdgeType.LOCKED, key_colour='red')
        self.assertEqual(e.params['key_colour'], 'red')

    def test_gated_edge(self):
        e = Edge('a', 'b', EdgeType.GATED, gate_id='gate_1')
        self.assertEqual(e.params['gate_id'], 'gate_1')


class TestLevelGraph(unittest.TestCase):

    def test_add_nodes_and_edges(self):
        g = LevelGraph()
        g.add_node('a', NodeSize.ROOM, is_start=True)
        g.add_node('b', NodeSize.HALL)
        g.add_edge('a', 'b', EdgeType.OPEN)
        self.assertEqual(len(g.nodes), 2)
        self.assertEqual(len(g.edges), 1)

    def test_neighbors(self):
        g = LevelGraph()
        g.add_node('a', is_start=True)
        g.add_node('b')
        g.add_node('c')
        g.add_edge('a', 'b')
        g.add_edge('a', 'c')
        nbrs = g.neighbors('a')
        self.assertEqual(len(nbrs), 2)
        names = {n for n, e in nbrs}
        self.assertEqual(names, {'b', 'c'})


# ── Playability validation tests ──────────────────────────────────────────────

class TestPlayability(unittest.TestCase):

    def test_all_open_is_playable(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('room', NodeSize.ROOM)
        g.add_edge('corridor', 'room', EdgeType.OPEN)
        g.nodes['room'].treasures.append((5,))
        self.assertEqual(g.validate_playability(), [])

    def test_breakable_is_playable(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('room', NodeSize.ROOM)
        g.add_edge('corridor', 'room', EdgeType.BREAKABLE)
        g.nodes['room'].treasures.append((3,))
        self.assertEqual(g.validate_playability(), [])

    def test_locked_with_key_is_playable(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('vault', NodeSize.ROOM)
        g.add_edge('corridor', 'vault', EdgeType.LOCKED, key_colour='red')
        g.nodes['corridor'].keys.append(('red',))
        g.nodes['vault'].treasures.append((9,))
        self.assertEqual(g.validate_playability(), [])

    def test_locked_without_key_fails(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('vault', NodeSize.ROOM)
        g.add_edge('corridor', 'vault', EdgeType.LOCKED, key_colour='red')
        g.nodes['vault'].treasures.append((9,))
        errors = g.validate_playability()
        self.assertTrue(any('unreachable' in e.lower() for e in errors))

    def test_locked_key_behind_same_door_fails(self):
        """Key is in the locked room — can't reach it without the door."""
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('vault', NodeSize.ROOM)
        g.add_edge('corridor', 'vault', EdgeType.LOCKED, key_colour='blue')
        g.nodes['vault'].keys.append(('blue',))
        g.nodes['vault'].treasures.append((7,))
        errors = g.validate_playability()
        self.assertTrue(len(errors) > 0)

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
        self.assertEqual(g.validate_playability(), [])

    def test_gated_without_block_fails(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('vault', NodeSize.ROOM)
        g.add_edge('corridor', 'vault', EdgeType.GATED, gate_id='g1')
        g.nodes['corridor'].plates.append(('g1',))
        g.nodes['vault'].treasures.append((4,))
        errors = g.validate_playability()
        self.assertTrue(len(errors) > 0)

    def test_gated_without_plate_fails(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('vault', NodeSize.ROOM)
        g.add_edge('corridor', 'vault', EdgeType.GATED, gate_id='g1')
        g.nodes['corridor'].blocks.append(1)
        g.nodes['vault'].treasures.append((4,))
        errors = g.validate_playability()
        self.assertTrue(len(errors) > 0)

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
        self.assertEqual(g.validate_playability(), [])

    def test_empty_node_unreachable_still_reported(self):
        g = LevelGraph()
        g.add_node('start', NodeSize.CORRIDOR, is_start=True)
        g.add_node('island', NodeSize.ROOM)
        errors = g.validate_playability()
        self.assertTrue(any('island' in e for e in errors))

    def test_no_start_node(self):
        g = LevelGraph()
        g.add_node('room', NodeSize.ROOM)
        errors = g.validate_playability()
        self.assertTrue(any('start' in e.lower() for e in errors))

    def test_stairs_are_passable(self):
        g = LevelGraph()
        g.add_node('floor1', NodeSize.CORRIDOR, is_start=True)
        g.add_node('floor2', NodeSize.ROOM)
        g.add_edge('floor1', 'floor2', EdgeType.STAIRS)
        g.nodes['floor2'].treasures.append((1,))
        self.assertEqual(g.validate_playability(), [])


# ── Graph generation tests ────────────────────────────────────────────────────

class TestGeneration(unittest.TestCase):

    def _make_features(self, **overrides):
        defaults = {
            'room_count': (3, 5),
            'edge_types': [EdgeType.OPEN, EdgeType.BREAKABLE],
            'node_sizes': [NodeSize.ROOM, NodeSize.HALL],
            'treasure_count': (4, 8),
            'material_types': [MAT_ROCKS, MAT_PLANKS],
            'material_count': (3, 6),
            'enemy_count': (1, 2),
        }
        defaults.update(overrides)
        return defaults

    def test_generation_produces_valid_graph(self):
        for seed in range(20):
            rng = random.Random(seed)
            g = LevelGraph.generate(self._make_features(), rng=rng)
            errors = g.validate_playability()
            self.assertEqual(errors, [],
                             f"Seed {seed} produced invalid graph: {errors}")

    def test_generation_with_locked_edges(self):
        features = self._make_features(
            edge_types=[EdgeType.OPEN, EdgeType.LOCKED])
        for seed in range(20):
            rng = random.Random(seed)
            g = LevelGraph.generate(features, rng=rng)
            errors = g.validate_playability()
            self.assertEqual(errors, [],
                             f"Seed {seed} (locked): {errors}")

    def test_generation_with_gated_edges(self):
        features = self._make_features(
            edge_types=[EdgeType.OPEN, EdgeType.GATED])
        for seed in range(20):
            rng = random.Random(seed)
            g = LevelGraph.generate(features, rng=rng)
            errors = g.validate_playability()
            self.assertEqual(errors, [],
                             f"Seed {seed} (gated): {errors}")

    def test_generation_with_all_edge_types(self):
        features = self._make_features(
            edge_types=[EdgeType.OPEN, EdgeType.BREAKABLE,
                        EdgeType.LOCKED, EdgeType.GATED])
        for seed in range(20):
            rng = random.Random(seed)
            g = LevelGraph.generate(features, rng=rng)
            errors = g.validate_playability()
            self.assertEqual(errors, [],
                             f"Seed {seed} (all types): {errors}")

    def test_always_has_corridor(self):
        g = LevelGraph.generate(self._make_features())
        corridors = [n for n in g.nodes.values()
                     if n.size == NodeSize.CORRIDOR]
        self.assertEqual(len(corridors), 1)

    def test_corridor_is_start(self):
        g = LevelGraph.generate(self._make_features())
        starts = [n for n in g.nodes.values() if n.is_start]
        self.assertEqual(len(starts), 1)
        self.assertEqual(starts[0].size, NodeSize.CORRIDOR)

    def test_enemy_rooms_have_treasure(self):
        """Every room with enemies must have at least one treasure."""
        features = self._make_features(enemy_count=(3, 4))
        for seed in range(20):
            rng = random.Random(seed)
            g = LevelGraph.generate(features, rng=rng)
            for name, node in g.nodes.items():
                if node.enemies:
                    self.assertTrue(
                        node.treasures,
                        f"Seed {seed}: {name} has enemies but no treasure")

    def test_gate_block_and_plate_same_room(self):
        """Block and plate for a gate must be in the same room."""
        features = self._make_features(
            edge_types=[EdgeType.OPEN, EdgeType.GATED])
        for seed in range(20):
            rng = random.Random(seed)
            g = LevelGraph.generate(features, rng=rng)
            for edge in g.edges:
                if edge.edge_type != EdgeType.GATED:
                    continue
                gate_id = edge.params['gate_id']
                plate_rooms = [n for n, node in g.nodes.items()
                               if any(gid == gate_id for gid, in node.plates)]
                block_rooms = [n for n, node in g.nodes.items()
                               if node.blocks]
                self.assertTrue(plate_rooms, f"Seed {seed}: no plate for {gate_id}")
                self.assertTrue(block_rooms, f"Seed {seed}: no block for {gate_id}")
                self.assertTrue(
                    set(plate_rooms) & set(block_rooms),
                    f"Seed {seed}: plate in {plate_rooms}, block in {block_rooms} — not same room")

    def test_all_feature_types_present(self):
        """Every edge type in the feature set appears at least once."""
        features = self._make_features(
            edge_types=[EdgeType.OPEN, EdgeType.BREAKABLE,
                        EdgeType.LOCKED, EdgeType.GATED])
        for seed in range(20):
            rng = random.Random(seed)
            g = LevelGraph.generate(features, rng=rng)
            present = {e.edge_type for e in g.edges}
            for et in [EdgeType.OPEN, EdgeType.BREAKABLE,
                       EdgeType.LOCKED, EdgeType.GATED]:
                self.assertIn(et, present,
                              f"Seed {seed}: {et.name} missing from graph")

    def test_respects_room_count(self):
        features = self._make_features(room_count=(3, 3))
        g = LevelGraph.generate(features)
        non_corridor = [n for n in g.nodes.values()
                        if n.size != NodeSize.CORRIDOR]
        self.assertEqual(len(non_corridor), 3)


# ── Layout tests ──────────────────────────────────────────────────────────────

class TestLayout(unittest.TestCase):

    def _simple_graph(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('room_a', NodeSize.ROOM)
        g.add_node('room_b', NodeSize.ROOM)
        g.add_edge('corridor', 'room_a', EdgeType.OPEN)
        g.add_edge('corridor', 'room_b', EdgeType.OPEN)
        return g

    def test_all_nodes_placed(self):
        g = self._simple_graph()
        placed = layout_graph(g, rng=random.Random(0))
        self.assertEqual(set(placed.keys()), set(g.nodes.keys()))

    def test_no_overlap(self):
        g = self._simple_graph()
        placed = layout_graph(g, rng=random.Random(0))
        all_tiles = set()
        for pn in placed.values():
            overlap = all_tiles & pn.floor_tiles
            self.assertEqual(overlap, set(),
                             f"Node {pn.name} overlaps at {overlap}")
            all_tiles.update(pn.floor_tiles)

    def test_within_bounds(self):
        g = self._simple_graph()
        placed = layout_graph(g, rng=random.Random(0))
        for pn in placed.values():
            for c, r in pn.floor_tiles:
                self.assertGreaterEqual(c, 1, f"{pn.name} out of bounds")
                self.assertLessEqual(c, COLS - 2)
                self.assertGreaterEqual(r, 1)
                self.assertLessEqual(r, ROWS - 2)

    def test_walls_cover_non_floor(self):
        """Every interior tile is either floor, wall, or a doorway."""
        g = self._simple_graph()
        placed = layout_graph(g, rng=random.Random(0))
        walls, _water = derive_walls(g, placed)
        floor = set()
        for pn in placed.values():
            floor.update(pn.floor_tiles)
        # Doorways are non-floor tiles removed from walls by derive_walls
        doorways = set()
        for c in range(1, COLS - 1):
            for r in range(1, ROWS - 1):
                if (c, r) not in floor and (c, r) not in walls:
                    doorways.add((c, r))
        # Every doorway must be adjacent to at least two different rooms
        for dc, dr in doorways:
            adjacent_rooms = set()
            for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nc, nr = dc + ddx, dr + ddy
                for pn in placed.values():
                    if (nc, nr) in pn.floor_tiles:
                        adjacent_rooms.add(pn.name)
            self.assertGreaterEqual(
                len(adjacent_rooms), 2,
                f"Doorway ({dc},{dr}) adjacent to {adjacent_rooms}, expected ≥2 rooms")
        # Floor tiles must not be walls
        for c, r in floor:
            self.assertNotIn((c, r), walls, f"Floor tile ({c},{r}) is a wall")


class TestLayoutInvariant(unittest.TestCase):
    """Edges must be the only passages between rooms."""

    def test_no_adjacent_floor_tiles(self):
        """No two rooms share adjacent floor tiles without a wall."""
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('a', NodeSize.ROOM)
        g.add_node('b', NodeSize.ROOM)
        g.add_edge('corridor', 'a', EdgeType.OPEN)
        g.add_edge('corridor', 'b', EdgeType.OPEN)
        placed = layout_graph(g, rng=random.Random(0))
        walls, _water = derive_walls(g, placed)
        errors = validate_layout(g, placed, walls)
        self.assertEqual(errors, [], f"Invariant errors: {errors}")

    def test_single_passage_per_edge(self):
        """Each edge produces exactly one passage in the wall."""
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('room', NodeSize.ROOM)
        g.add_edge('corridor', 'room', EdgeType.OPEN)
        placed = layout_graph(g, rng=random.Random(0))
        walls, _water = derive_walls(g, placed)
        errors = validate_layout(g, placed, walls)
        self.assertEqual(errors, [])

    def test_invariant_holds_across_seeds(self):
        """Layout invariant holds for many random graphs."""
        features = {
            'room_count': (4, 5),
            'edge_types': [EdgeType.OPEN, EdgeType.BREAKABLE, EdgeType.LOCKED],
            'node_sizes': [NodeSize.ROOM, NodeSize.HALL],
            'treasure_count': (4, 6),
            'material_types': [MAT_ROCKS],
            'material_count': (2, 4),
            'enemy_count': (1, 2),
        }
        for seed in range(15):
            rng = random.Random(seed)
            g = LevelGraph.generate(features, rng=rng)
            if g.validate_playability():
                continue  # skip invalid graphs
            placed = layout_graph(g, rng=rng)
            walls, _water = derive_walls(g, placed)
            errors = validate_layout(g, placed, walls)
            self.assertEqual(errors, [],
                             f"Seed {seed}: {errors}")


class TestTileOwnership(unittest.TestCase):

    def test_room_floor_has_owner(self):
        """Every room's floor tile has an owner. Doorway tiles (wall
        removed for edges) are not owned — they're transitions."""
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('room', NodeSize.ROOM)
        g.add_edge('corridor', 'room', EdgeType.OPEN)
        placed = layout_graph(g, rng=random.Random(0))
        owner = build_tile_owner(placed)
        for name, pn in placed.items():
            for tile in pn.floor_tiles:
                self.assertIn(tile, owner,
                              f"Room {name} floor tile {tile} has no owner")
                self.assertEqual(owner[tile], name)

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
                self.assertNotIn(tile, seen,
                    f"Tile {tile} owned by both {seen.get(tile)} and {name}")
                seen[tile] = name


class TestPushPuzzleSolvability(unittest.TestCase):

    def test_simple_push_solvable(self):
        """Block can be pushed straight to the plate."""
        from levellayout import validate_push_puzzles
        room = {
            'walls': {(c, r): WALL_REINFORCED
                      for c in range(1, 29) for r in range(1, 15)
                      if not (5 <= c <= 20 and 5 <= r <= 10)},
            'pushable_blocks': [(10, 7)],
            'pressure_plates': [(15, 7, 'g1')],
            'gates': [(20, 7, 'g1')],
        }
        owner = {(c, r): 'room' for c in range(5, 21) for r in range(5, 11)}
        errors = validate_push_puzzles(room, owner)
        self.assertEqual(errors, [])

    def test_narrow_corridor_different_row_unsolvable(self):
        """Block in row 5 of a 2-tile-wide corridor, plate in row 6.
        Player can only push horizontally — can't reach row 6."""
        from levellayout import validate_push_puzzles
        # 2-tile-wide corridor: rows 5-6, cols 5-20
        floor = {(c, r) for c in range(5, 21) for r in range(5, 7)}
        walls = {(c, r): WALL_REINFORCED
                 for c in range(1, 29) for r in range(1, 15)
                 if (c, r) not in floor}
        room = {
            'walls': walls,
            'pushable_blocks': [(10, 5)],   # block in top row
            'pressure_plates': [(10, 6, 'g1')],  # plate in bottom row
            'gates': [(20, 5, 'g1')],
        }
        owner = {pos: 'room' for pos in floor}
        errors = validate_push_puzzles(room, owner)
        self.assertTrue(len(errors) > 0,
                         "Should be unsolvable: can't push block to adjacent row "
                         "in a 2-tile corridor")

    def test_wide_room_push_solvable(self):
        """Block and plate in same row of a wide room — trivially solvable."""
        from levellayout import validate_push_puzzles
        floor = {(c, r) for c in range(5, 21) for r in range(5, 11)}
        walls = {(c, r): WALL_REINFORCED
                 for c in range(1, 29) for r in range(1, 15)
                 if (c, r) not in floor}
        room = {
            'walls': walls,
            'pushable_blocks': [(8, 7)],
            'pressure_plates': [(15, 7, 'g1')],
            'gates': [(20, 7, 'g1')],
        }
        owner = {pos: 'room' for pos in floor}
        errors = validate_push_puzzles(room, owner)
        self.assertEqual(errors, [])

    def test_generated_puzzles_solvable(self):
        """All generated levels with gates must have solvable puzzles."""
        features = {
            'room_count': (4, 5),
            'edge_types': [EdgeType.OPEN, EdgeType.GATED],
            'node_sizes': [NodeSize.ROOM, NodeSize.HALL],
            'treasure_count': (4, 6),
            'material_types': [MAT_ROCKS],
            'material_count': (2, 3),
            'enemy_count': (1, 2),
        }
        successes = 0
        for seed in range(30):
            rng = random.Random(seed)
            graph = LevelGraph.generate(features, rng=rng)
            if graph.validate_playability():
                continue
            try:
                level = build_level_dict(graph, rng=rng)
                successes += 1
            except ValueError:
                pass  # unsolvable puzzle — generator should retry
        self.assertGreater(successes, 0,
                           "No seed produced a solvable gated level")


class TestBuildLevelDict(unittest.TestCase):

    def test_output_format(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('room', NodeSize.ROOM)
        g.add_edge('corridor', 'room', EdgeType.OPEN)
        g.nodes['room'].treasures.append((5,))
        level = build_level_dict(g)
        self.assertIn('start_room', level)
        self.assertIn('player_start', level)
        self.assertIn('rooms', level)
        room = level['rooms'][level['start_room']]
        self.assertIn('walls', room)
        self.assertIsInstance(room['walls'], dict)

    def test_treasures_on_floor(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('room', NodeSize.ROOM)
        g.add_edge('corridor', 'room', EdgeType.OPEN)
        g.nodes['room'].treasures.append((5,))
        g.nodes['room'].treasures.append((3,))
        level = build_level_dict(g)
        room = level['rooms'][level['start_room']]
        walls = room['walls']
        for tc, tr, item in room.get('treasures', []):
            self.assertNotIn((tc, tr), walls,
                             f"Treasure {item} at ({tc},{tr}) is on a wall")

    def test_player_start_on_floor(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('room', NodeSize.ROOM)
        g.add_edge('corridor', 'room', EdgeType.OPEN)
        level = build_level_dict(g)
        pc, pr = level['player_start']
        room = level['rooms'][level['start_room']]
        self.assertNotIn((pc, pr), room['walls'],
                         "Player start is on a wall")

    def test_entrance_key_exists(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('room', NodeSize.ROOM)
        g.add_edge('corridor', 'room', EdgeType.OPEN)
        level = build_level_dict(g)
        room = level['rooms'][level['start_room']]
        self.assertIn('entrance', room)

    def test_entrance_is_on_outer_border(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('room', NodeSize.ROOM)
        g.add_edge('corridor', 'room', EdgeType.OPEN)
        level = build_level_dict(g)
        room = level['rooms'][level['start_room']]
        ec, er = room['entrance']
        on_border = (ec == 0 or ec == COLS - 1 or er == 0 or er == ROWS - 1)
        self.assertTrue(on_border, f"entrance {(ec, er)} not on outer border")

    def test_player_start_adjacent_to_entrance(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('room', NodeSize.ROOM)
        g.add_edge('corridor', 'room', EdgeType.OPEN)
        level = build_level_dict(g)
        room = level['rooms'][level['start_room']]
        ec, er = room['entrance']
        pc, pr = level['player_start']
        dist = abs(pc - ec) + abs(pr - er)
        self.assertEqual(dist, 1,
                         f"player_start {(pc, pr)} not adjacent to entrance {(ec, er)}")
        self.assertNotIn((pc, pr), room['walls'])

    def test_entrance_in_start_grid_only(self):
        from tests.conftest import FS_ALL
        fs = dict(FS_ALL)
        fs['grid_count'] = 3
        fs['branch_prob'] = 0.0
        for seed in range(5):
            rng = random.Random(seed)
            graph = LevelGraph.generate(fs, rng=rng)
            level = build_level_dict(graph, rng=random.Random(seed))
            start_room = level['start_room']
            for gname, room in level['rooms'].items():
                if gname == start_room:
                    self.assertIn('entrance', room,
                                  f"Start grid {gname!r} missing entrance (seed={seed})")
                else:
                    self.assertNotIn('entrance', room,
                                     f"Non-start grid {gname!r} should not have entrance (seed={seed})")

    def test_tile_owner_in_output(self):
        g = LevelGraph()
        g.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        g.add_node('room', NodeSize.ROOM)
        g.add_edge('corridor', 'room', EdgeType.OPEN)
        level = build_level_dict(g)
        room = level['rooms'][level['start_room']]
        self.assertIn('tile_owner', room)
        self.assertIsInstance(room['tile_owner'], dict)

    def test_enemies_far_from_player(self):
        """Enemies must be placed far from the player start."""
        from collections import deque
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
            passable = set()
            for c in range(1, COLS - 1):
                for r in range(1, ROWS - 1):
                    if (c, r) not in walls:
                        passable.add((c, r))
            dist = {(pc, pr): 0}
            q = deque([(pc, pr)])
            while q:
                cx, cy = q.popleft()
                for dc, dr in ((1,0),(-1,0),(0,1),(0,-1)):
                    nc, nr = cx+dc, cy+dr
                    if (nc, nr) in passable and (nc, nr) not in dist:
                        dist[(nc, nr)] = dist[(cx, cy)] + 1
                        q.append((nc, nr))
            for edata in room.get('enemy_starts', []):
                ec, er = edata[0], edata[1]
                d = dist.get((ec, er), 0)
                self.assertGreaterEqual(
                    d, MIN_ENEMY_DIST // 2,
                    f"Seed {seed}: enemy at ({ec},{er}) only {d} tiles from player")

    def test_multiple_seeds_produce_different_layouts(self):
        """Different seeds should produce at least some variation."""
        features = {
            'room_count': (5, 6),
            'edge_types': [EdgeType.OPEN, EdgeType.BREAKABLE],
            'node_sizes': [NodeSize.ROOM, NodeSize.HALL],
            'treasure_count': (4, 6),
            'material_types': [MAT_ROCKS],
            'material_count': (2, 3),
            'enemy_count': (1, 2),
        }
        layouts = set()
        for seed in range(10):
            rng = random.Random(seed * 999)
            g = LevelGraph.generate(features, rng=rng)
            if g.validate_playability():
                continue
            try:
                level = build_level_dict(g, rng=rng)
                w = frozenset(level['rooms']['main']['walls'].items())
                layouts.add(w)
            except ValueError:
                pass
        self.assertGreater(len(layouts), 1,
                           "10 seeds should produce at least 2 different layouts")


if __name__ == '__main__':
    unittest.main()
