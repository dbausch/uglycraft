"""Graph-based level model: nodes are rooms, edges are connections.

The graph is the source of truth for a level. The 30×16 tile grid is
derived from the graph by the layout algorithm in levellayout.py.
"""
import random
from enum import Enum, auto


# ── Node sizes ────────────────────────────────────────────────────────────────

class NodeSize(Enum):
    CLOSET   = auto()   # 3-4 × 3-4
    ROOM     = auto()   # 5-8 × 4-6
    HALL     = auto()   # 8-12 × 5-8
    CORRIDOR = auto()   # 8-20 × 2-3

SIZE_RANGES = {
    NodeSize.CLOSET:   ((3, 4), (3, 4)),
    NodeSize.ROOM:     ((5, 8), (4, 6)),
    NodeSize.HALL:     ((8, 12), (5, 8)),
    NodeSize.CORRIDOR: ((8, 20), (2, 3)),
}


# ── Edge types ────────────────────────────────────────────────────────────────

class EdgeType(Enum):
    OPEN      = auto()   # always passable doorway
    BREAKABLE = auto()   # stone or wooden wall, player can break through
    LOCKED    = auto()   # needs a key of a specific colour
    GATED     = auto()   # needs a pressure plate + pushable block
    WATER     = auto()   # blocked by water, crossable with bridge (2 planks)
    STAIRS    = auto()   # connects nodes on different grids (floors)


# ── Graph elements ────────────────────────────────────────────────────────────

class Node:
    """A room in the level graph."""

    def __init__(self, name, size=NodeSize.ROOM, is_start=False):
        self.name = name
        self.size = size
        self.is_start = is_start
        self.treasures = []       # [(item_no,)]
        self.materials = []       # [(mat_type,)]
        self.keys = []            # [(key_colour,)]
        self.blocks = []          # pushable block count
        self.plates = []          # [(gate_id,)]
        self.enemies = []         # [(enemy_type, ...)]
        self.has_flames = False   # room contains flame jets
        self.patrol_waypoints = None

    def __repr__(self):
        return f"Node({self.name!r}, {self.size.name})"


class Edge:
    """A connection between two rooms."""

    def __init__(self, node_a, node_b, edge_type=EdgeType.OPEN, **params):
        self.node_a = node_a    # node name
        self.node_b = node_b    # node name
        self.edge_type = edge_type
        self.params = params    # key_colour, gate_id, wall_type, etc.

    def __repr__(self):
        return f"Edge({self.node_a!r} <-> {self.node_b!r}, {self.edge_type.name})"


# ── Level graph ───────────────────────────────────────────────────────────────

class LevelGraph:
    """A complete level as a graph of rooms and connections."""

    def __init__(self, rng=None):
        self.nodes = {}    # {name: Node}
        self.edges = []    # [Edge]
        self.rng = rng or random.Random()

    def add_node(self, name, size=NodeSize.ROOM, is_start=False):
        node = Node(name, size, is_start)
        self.nodes[name] = node
        return node

    def add_edge(self, node_a, node_b, edge_type=EdgeType.OPEN, **params):
        edge = Edge(node_a, node_b, edge_type, **params)
        self.edges.append(edge)
        return edge

    def neighbors(self, node_name):
        """Return list of (neighbor_name, edge) for a node."""
        result = []
        for e in self.edges:
            if e.node_a == node_name:
                result.append((e.node_b, e))
            elif e.node_b == node_name:
                result.append((e.node_a, e))
        return result

    # ── Playability validation ────────────────────────────────────────────

    def validate_playability(self):
        """Check that all nodes are reachable from the start node.

        Returns a list of error strings (empty = valid).

        The algorithm progressively opens edges:
        1. Start with all OPEN and BREAKABLE edges passable.
        2. For each LOCKED edge on the frontier: if a matching key is in
           the reachable set, open the edge and expand.
        3. For each GATED edge on the frontier: if a matching plate AND
           a block are in the reachable set, open the edge and expand.
        4. Repeat until no more edges can be opened.
        5. Any unreachable node with items is an error.
        """
        errors = []

        start = None
        for node in self.nodes.values():
            if node.is_start:
                start = node.name
                break
        if start is None:
            return ["No start node defined"]

        reachable = set()
        opened_edges = set()

        def _expand(seed_nodes):
            frontier = list(seed_nodes - reachable)
            reachable.update(seed_nodes)
            while frontier:
                current = frontier.pop()
                for neighbor, edge in self.neighbors(current):
                    if neighbor in reachable:
                        continue
                    if id(edge) in opened_edges:
                        continue
                    if edge.edge_type in (EdgeType.OPEN, EdgeType.BREAKABLE,
                                          EdgeType.STAIRS):
                        reachable.add(neighbor)
                        opened_edges.add(id(edge))
                        frontier.append(neighbor)

        _expand({start})

        changed = True
        while changed:
            changed = False
            for edge in self.edges:
                if id(edge) in opened_edges:
                    continue

                a_reachable = edge.node_a in reachable
                b_reachable = edge.node_b in reachable
                if not a_reachable and not b_reachable:
                    continue

                if edge.edge_type == EdgeType.LOCKED:
                    colour = edge.params.get('key_colour')
                    has_key = any(
                        colour in [k for k, in node.keys]
                        for name, node in self.nodes.items()
                        if name in reachable
                    )
                    if has_key:
                        opened_edges.add(id(edge))
                        new_node = edge.node_b if a_reachable else edge.node_a
                        _expand({new_node})
                        changed = True

                elif edge.edge_type == EdgeType.GATED:
                    gate_id = edge.params.get('gate_id')
                    has_plate = any(
                        gate_id in [g for g, in node.plates]
                        for name, node in self.nodes.items()
                        if name in reachable
                    )
                    has_block = any(
                        node.blocks
                        for name, node in self.nodes.items()
                        if name in reachable
                    )
                    if has_plate and has_block:
                        opened_edges.add(id(edge))
                        new_node = edge.node_b if a_reachable else edge.node_a
                        _expand({new_node})
                        changed = True

                elif edge.edge_type == EdgeType.WATER:
                    has_planks = any(
                        'planks' in [m for m, in node.materials]
                        for name, node in self.nodes.items()
                        if name in reachable
                    )
                    has_block = any(
                        node.blocks
                        for name, node in self.nodes.items()
                        if name in reachable
                    )
                    if has_planks or has_block:
                        opened_edges.add(id(edge))
                        new_node = edge.node_b if a_reachable else edge.node_a
                        _expand({new_node})
                        changed = True

        for name, node in self.nodes.items():
            if name not in reachable:
                if node.treasures or node.materials or node.keys:
                    errors.append(
                        f"Node {name!r} has items but is unreachable")
                else:
                    errors.append(f"Node {name!r} is unreachable (no items)")

        return errors

    # ── Graph generation ──────────────────────────────────────────────────

    @classmethod
    def generate(cls, feature_set, rng=None):
        """Generate a random level graph from a feature set.

        feature_set: dict with keys:
            'room_count': (min, max)
            'edge_types': [EdgeType, ...]  — allowed edge types
            'node_sizes': [NodeSize, ...]  — allowed node sizes
            'treasure_count': (min, max)
            'material_types': [mat_type, ...]
            'material_count': (min, max)
            'enemy_count': (min, max)
        """
        rng = rng or random.Random()
        graph = cls(rng=rng)

        edge_types = feature_set.get('edge_types', [EdgeType.OPEN])
        node_sizes = feature_set.get('node_sizes',
                                      [NodeSize.ROOM, NodeSize.HALL])
        # Every distinct edge type in the feature set must appear at least once
        required_types = list(dict.fromkeys(edge_types))

        room_min, room_max = feature_set.get('room_count', (4, 6))
        room_count = max(rng.randint(room_min, room_max), len(required_types))

        # Always create a corridor as the backbone
        corridor = graph.add_node('corridor', NodeSize.CORRIDOR, is_start=True)

        # Attach rooms to the corridor
        room_names = []
        for i in range(room_count):
            name = f'room_{i}'
            size = rng.choice(node_sizes)
            graph.add_node(name, size)
            room_names.append(name)

            # First rooms satisfy required types, rest are random
            if i < len(required_types):
                et = required_types[i]
            else:
                et = rng.choice(edge_types)
            params = {}
            if et == EdgeType.LOCKED:
                params['key_colour'] = rng.choice(['red', 'blue', 'green'])
            elif et == EdgeType.GATED:
                params['gate_id'] = f'gate_{i}'
            elif et == EdgeType.WATER:
                params['water_id'] = f'water_{i}'
            elif et == EdgeType.BREAKABLE:
                params['wall_type'] = rng.choice(['stone', 'wooden'])
            graph.add_edge('corridor', name, et, **params)

        # Place items to satisfy playability
        _assign_items(graph, feature_set, rng)

        return graph


def _assign_items(graph, feature_set, rng):
    """Distribute treasures, materials, keys, blocks, plates across nodes."""

    all_nodes = list(graph.nodes.keys())
    corridor_name = 'corridor'

    # Collect which keys, gates, and water crossings are needed
    needed_keys = {}   # {colour: edge}
    needed_gates = {}  # {gate_id: edge}
    needed_water = {}  # {water_id: edge}
    for edge in graph.edges:
        if edge.edge_type == EdgeType.LOCKED:
            colour = edge.params['key_colour']
            needed_keys[colour] = edge
        elif edge.edge_type == EdgeType.GATED:
            gate_id = edge.params['gate_id']
            needed_gates[gate_id] = edge
        elif edge.edge_type == EdgeType.WATER:
            water_id = edge.params.get('water_id', f'water_{id(edge)}')
            needed_water[water_id] = edge

    # For each locked edge, place a key on the start side
    for colour, edge in needed_keys.items():
        # The key must be in a room reachable without crossing this edge.
        # Since all rooms connect to the corridor, and the corridor is the
        # start, place the key in the corridor or another freely-accessible room.
        candidates = [corridor_name]
        for name, _ in graph.neighbors(corridor_name):
            if name == edge.node_b:
                continue
            other_edge = [e for n, e in graph.neighbors(corridor_name)
                          if n == name][0]
            if other_edge.edge_type in (EdgeType.OPEN, EdgeType.BREAKABLE):
                candidates.append(name)
        target = rng.choice(candidates)
        graph.nodes[target].keys.append((colour,))

    # For each gated edge, place plate AND block in the SAME room.
    # Never in the corridor — it's too narrow for pushing.
    for gate_id, edge in needed_gates.items():
        candidates = []
        for name, _ in graph.neighbors(corridor_name):
            if name == edge.node_b:
                continue
            other_edge = [e for n, e in graph.neighbors(corridor_name)
                          if n == name][0]
            if other_edge.edge_type in (EdgeType.OPEN, EdgeType.BREAKABLE):
                candidates.append(name)
        if not candidates:
            candidates = [corridor_name]  # last resort
        target = rng.choice(candidates)
        graph.nodes[target].plates.append((gate_id,))
        graph.nodes[target].blocks.append(1)

    # For each water edge, ensure planks are reachable on the start side
    for water_id, edge in needed_water.items():
        candidates = [corridor_name]
        for name, _ in graph.neighbors(corridor_name):
            if name == edge.node_b:
                continue
            other_edge = [e for n, e in graph.neighbors(corridor_name)
                          if n == name][0]
            if other_edge.edge_type in (EdgeType.OPEN, EdgeType.BREAKABLE):
                candidates.append(name)
        target = rng.choice(candidates)
        graph.nodes[target].materials.append(('planks',))
        graph.nodes[target].materials.append(('planks',))

    # Distribute treasures
    t_min, t_max = feature_set.get('treasure_count', (6, 10))
    t_count = rng.randint(t_min, t_max)
    item_nos = list(range(1, 10))
    for _ in range(t_count):
        target = rng.choice(all_nodes)
        item_no = rng.choice(item_nos)
        graph.nodes[target].treasures.append((item_no,))

    # Distribute materials (exclude planks if water edges exist — planks
    # are placed precisely for bridge crafting)
    mat_types = list(feature_set.get('material_types', []))
    if needed_water and 'planks' in mat_types:
        mat_types = [m for m in mat_types if m != 'planks']
    m_min, m_max = feature_set.get('material_count', (4, 8))
    m_count = rng.randint(m_min, m_max)
    for _ in range(m_count):
        if mat_types:
            target = rng.choice(all_nodes)
            mat = rng.choice(mat_types)
            graph.nodes[target].materials.append((mat,))

    # Distribute enemies (never in corridor, puzzle rooms, or flame rooms)
    e_min, e_max = feature_set.get('enemy_count', (1, 3))
    e_count = max(1, rng.randint(e_min, e_max))
    hazard_rooms = {n for n, node in graph.nodes.items()
                    if node.blocks or node.plates or node.has_flames}
    enemy_candidates = [n for n in all_nodes
                        if n != corridor_name and n not in hazard_rooms]
    if not enemy_candidates:
        enemy_candidates = [n for n in all_nodes if n != corridor_name]
    has_forge = feature_set.get('has_forge_ogre', False)
    forge_placed = False
    for _ in range(e_count):
        target = rng.choice(enemy_candidates)
        if has_forge and not forge_placed:
            graph.nodes[target].enemies.append(('forge_ogre',))
            forge_placed = True
        else:
            graph.nodes[target].enemies.append(('chaser',))

    # Ensure every room with enemies has at least one treasure (reward for risk)
    item_nos = list(range(1, 10))
    for name, node in graph.nodes.items():
        if node.enemies and not node.treasures:
            node.treasures.append((rng.choice(item_nos),))

    # Add flame jets to some rooms (if feature set allows)
    if feature_set.get('has_flames'):
        flame_candidates = [n for n in all_nodes
                            if n != corridor_name
                            and not graph.nodes[n].blocks
                            and not graph.nodes[n].plates]
        if flame_candidates:
            target = rng.choice(flame_candidates)
            graph.nodes[target].has_flames = True
            if not graph.nodes[target].treasures:
                graph.nodes[target].treasures.append((rng.choice(item_nos),))
