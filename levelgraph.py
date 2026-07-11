"""Graph-based level model: nodes are rooms, edges are connections.

The graph is the source of truth for a level. The 30×16 tile grid is
derived from the graph by the layout algorithm in levellayout.py.
"""
import math
import random
from enum import Enum, auto
from crafting import KEY_COLORS


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
    BORDER    = auto()   # connects corridors across 30×16 grid boundaries


# ── Graph elements ────────────────────────────────────────────────────────────

class Node:
    """A room in the level graph."""

    def __init__(self, name, size=NodeSize.ROOM, is_start=False):
        self.name = name
        self.size = size
        self.is_start = is_start
        self.super_pos = (0, 0)   # (col, row) on the super-grid (corridor nodes only)
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


# ── Super-grid helpers ────────────────────────────────────────────────────────

_OPPOSITE = {'right': 'left', 'left': 'right', 'top': 'bottom', 'bottom': 'top'}


def _spanning_tree(n, rng, root=(0, 0), blocked=frozenset()):
    """Return a spanning-tree description for n grids on the super-grid.

    Uses randomized Prim's algorithm: at each step pick a random edge from the
    frontier of all tree nodes and add the neighbour. Terminates in exactly n-1
    successful steps; never wanders on the infinite grid.

    root:    super-grid cell of the tree root (index 0).
    blocked: cells no grid may ever occupy, checked on every Prim step (the
             frontier can approach them from any direction) — reserves grid
             zero, the outside of the dungeon (spec 0053).

    Returns a list of length exactly n where entry i is
        (parent_idx, exit_side, (super_col, super_row))
    with parent_idx=None and exit_side=None for the root (index 0).

    Parents always appear before their children in the list.
    All super-grid positions are unique.
    """
    if n <= 1:
        return [(None, None, root)]

    _DIRS = [('right', 1, 0), ('left', -1, 0), ('bottom', 0, 1), ('top', 0, -1)]
    _DELTA_TO_SIDE = {(1, 0): 'right', (-1, 0): 'left', (0, 1): 'bottom', (0, -1): 'top'}

    result  = [(None, None, root)]
    in_tree = {root: 0}

    # frontier: list of (parent_idx, child_pos) — edges from tree to unvisited
    frontier = [(0, (root[0] + dx, root[1] + dy)) for _, dx, dy in _DIRS]

    while len(in_tree) < n:
        i = rng.randrange(len(frontier))
        parent_idx, child_pos = frontier[i]
        frontier[i] = frontier[-1]
        frontier.pop()

        if child_pos in in_tree or child_pos in blocked:
            continue

        parent_pos = result[parent_idx][2]
        exit_side  = _DELTA_TO_SIDE[(child_pos[0] - parent_pos[0],
                                     child_pos[1] - parent_pos[1])]
        new_idx = len(result)
        result.append((parent_idx, exit_side, child_pos))
        in_tree[child_pos] = new_idx

        cx, cy = child_pos
        for _, dx, dy in _DIRS:
            nb = (cx + dx, cy + dy)
            if nb not in in_tree:
                frontier.append((new_idx, nb))

    return result


def _border_direction(pos_a, pos_b):
    """Return (exit_side, entry_side) for a BORDER edge from pos_a to pos_b."""
    dc = pos_b[0] - pos_a[0]
    dr = pos_b[1] - pos_a[1]
    if dc == 1:   return 'right',  'left'
    if dc == -1:  return 'left',   'right'
    if dr == 1:   return 'bottom', 'top'
    if dr == -1:  return 'top',    'bottom'
    return 'right', 'left'  # fallback for non-adjacent (shouldn't happen)


# ── Level graph ───────────────────────────────────────────────────────────────

class LevelGraph:
    """A complete level as a graph of rooms and connections."""

    def __init__(self, rng=None):
        self.nodes = {}    # {name: Node}
        self.edges = []    # [Edge]
        self.rng = rng or random.Random()
        # Side of the start grid reserved for the level entrance — the face
        # toward grid zero at super-grid origin (0,0), the outside of the
        # dungeon (spec 0053).  None for single-grid graphs.
        self.entrance_side = None

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
                    elif (edge.edge_type == EdgeType.BORDER
                          and edge.params.get('barrier', 'open') == 'open'):
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
                    # A bridge costs two planks; a pushable block cannot cross
                    # water.  Require >= 2 reachable planks (BL-04 / spec 0029 W5).
                    reachable_planks = sum(
                        sum(1 for m in node.materials if m == ('planks',))
                        for name, node in self.nodes.items()
                        if name in reachable
                    )
                    if reachable_planks >= 2:
                        opened_edges.add(id(edge))
                        new_node = edge.node_b if a_reachable else edge.node_a
                        _expand({new_node})
                        changed = True

                elif edge.edge_type == EdgeType.BORDER:
                    barrier = edge.params.get('barrier', 'open')
                    if barrier == 'locked':
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
                    elif barrier == 'gated':
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
        """Generate a level graph from a feature set using LevelGraphBuilder.

        Each challenge addition (locked room, gated room, water room) atomically
        places its prerequisite item in the already-reachable set, so
        validate_playability() is guaranteed to pass without retries.

        feature_set keys:
            'room_count': (min, max)
            'edge_types': [EdgeType, ...]  — allowed edge types
            'node_sizes': [NodeSize, ...]  — allowed node sizes
            'treasure_count': (min, max)
            'material_types': [mat_type, ...]
            'material_count': (min, max)
            'enemy_count': (min, max)
            'grid_count': N  — number of 30×16 grids (default 1)
            'has_flames': bool
            'has_forge_ogre': bool
        """
        rng = rng or random.Random()
        b = LevelGraphBuilder(rng)

        edge_types  = feature_set.get('edge_types',  [EdgeType.OPEN])
        node_sizes  = feature_set.get('node_sizes',  [NodeSize.ROOM, NodeSize.HALL])
        grid_count  = feature_set.get('grid_count',  1)
        required    = list(dict.fromkeys(edge_types))  # ordered, deduplicated

        room_min, room_max = feature_set.get('room_count', (4, 6))
        room_count  = max(rng.randint(room_min, room_max), len(required))

        # Shuffled color pool — ensures every locked door uses a distinct color.
        all_colors = list(KEY_COLORS.keys())
        rng.shuffle(all_colors)
        color_pool = list(all_colors)  # cycling: refilled when exhausted

        def _next_color():
            if not color_pool:
                color_pool.extend(all_colors)
                rng.shuffle(color_pool)
            return color_pool.pop()

        gate_counter  = [0]
        border_counter = [0]

        def _add_room(et):
            size = rng.choice(node_sizes)
            if et == EdgeType.OPEN:
                b.add_open_room(size=size)
            elif et == EdgeType.BREAKABLE:
                b.add_breakable_room(rng.choice(['stone', 'wooden']), size=size)
            elif et == EdgeType.LOCKED:
                b.add_locked_room(_next_color(), size=size)
            elif et == EdgeType.GATED:
                b.add_gated_room(f'gate_{gate_counter[0]}', size=size)
                gate_counter[0] += 1
            elif et == EdgeType.WATER:
                b.add_water_room(size=size)

        def _barrier_kw():
            """Pick barrier type for the next BORDER edge."""
            barrier_options = ['open']
            if EdgeType.LOCKED in edge_types:
                barrier_options.append('locked')
            if EdgeType.GATED in edge_types:
                barrier_options.append('gated')
            barrier = rng.choice(barrier_options)
            if barrier == 'locked':
                return {'barrier': 'locked', 'key_colour': _next_color()}
            elif barrier == 'gated':
                gid = f'border_gate_{border_counter[0]}'
                border_counter[0] += 1
                return {'barrier': 'gated', 'gate_id': gid}
            return {}

        # Grid zero (spec 0053): the outside of the dungeon occupies the
        # super-grid origin (0,0).  Its pseudo exit points at the start grid,
        # which therefore sits in the adjacent cell; the start grid's face
        # back toward the origin is reserved for the level entrance — no
        # BORDER edge can ever use it because no grid may occupy (0,0).
        entrance_side = None
        root = (0, 0)
        if grid_count >= 2:
            _DELTA = {'right': (1, 0), 'left': (-1, 0),
                      'bottom': (0, 1), 'top': (0, -1)}
            _OPPOSITE = {'right': 'left', 'left': 'right',
                         'bottom': 'top', 'top': 'bottom'}
            pseudo_exit = rng.choice(['right', 'left', 'bottom', 'top'])
            root = _DELTA[pseudo_exit]
            entrance_side = _OPPOSITE[pseudo_exit]

        tree = _spanning_tree(grid_count, rng, root=root, blocked={(0, 0)})
        # tree[i] = (parent_idx, exit_side, (sc, sr)); root has parent_idx=None

        def _idx_to_name(i):
            return 'corridor' if i == 0 else f'corridor_{i}'

        rooms_per_grid = [room_count // grid_count] * grid_count
        for i in range(room_count % grid_count):
            rooms_per_grid[i] += 1

        room_idx = 0
        for i, (parent_idx, exit_side, (sc, sr)) in enumerate(tree):
            if parent_idx is not None:
                b.start_next_grid(sc, sr, exit_side,
                                  source=_idx_to_name(parent_idx),
                                  **_barrier_kw())
            else:
                b._graph.nodes[_idx_to_name(0)].super_pos = (sc, sr)

            for _ in range(rooms_per_grid[i]):
                et = required[room_idx] if room_idx < len(required) else rng.choice(edge_types)
                _add_room(et)
                room_idx += 1

        # Each room independently gets at most ONE closet (spec 0032 C1).
        closet_prob = feature_set.get('closet_prob', 0.10)
        room_names = [n for n, nd in b._graph.nodes.items()
                      if nd.size in (NodeSize.ROOM, NodeSize.HALL)]
        for rn in room_names:
            if rng.random() < closet_prob:
                b.add_closet_room(parent=rn)

        if feature_set.get('has_flames'):
            b.add_flames()

        t_min, t_max = feature_set.get('treasure_count', (6, 10))
        b.add_treasures(rng.randint(t_min, t_max))

        mat_types = list(feature_set.get('material_types', []))
        m_min, m_max = feature_set.get('material_count', (4, 8))
        b.add_materials(mat_types, rng.randint(m_min, m_max))

        e_min, e_max = feature_set.get('enemy_count', (1, 3))
        b._has_forge = feature_set.get('has_forge_ogre', False)
        b.add_enemies(max(1, rng.randint(e_min, e_max)))

        graph = b.build()
        graph.entrance_side = entrance_side
        return graph


# ── Level graph builder ───────────────────────────────────────────────────────

class LevelGraphBuilder:
    """Construct a LevelGraph by adding challenges one at a time.

    Each add_*_room() method maintains the invariant:
        self._graph.validate_playability() == []

    This is guaranteed because each method atomically places the prerequisite
    item (key, plate+block, planks) in a node that is already in _reachable
    BEFORE the new node joins _reachable.
    """

    def __init__(self, rng):
        self._graph = LevelGraph(rng)
        self._rng   = rng
        self._idx   = 0
        self._current_corridor = 'corridor'
        self._has_water  = False
        self._has_forge  = False
        self._graph.add_node('corridor', NodeSize.CORRIDOR, is_start=True)
        self._reachable  = {'corridor'}
        self._water_rooms: set = set()

    # ── Internal helpers ──────────────────────────────────────────────────

    def _new_name(self):
        name = f'room_{self._idx}'
        self._idx += 1
        return name

    def _room_candidates(self):
        """Reachable non-corridor rooms."""
        return [n for n in self._reachable
                if self._graph.nodes[n].size != NodeSize.CORRIDOR]

    def _current_grid_rooms(self):
        """Rooms directly attached to the current corridor (same subgraph)."""
        return {name for name, edge in self._graph.neighbors(self._current_corridor)
                if edge.edge_type != EdgeType.BORDER}

    def _puzzle_candidates(self):
        """Reachable rooms on the current grid suitable for a Sokoban puzzle.

        Only returns rooms directly attached to the current corridor so that
        plates always land in the same subgraph as their gate.  Returning []
        signals add_gated_room() to auto-add an open room first.
        """
        def eligible(n):
            node = self._graph.nodes[n]
            return (node.size not in (NodeSize.CORRIDOR, NodeSize.CLOSET)
                    and not node.blocks
                    and not node.plates)

        return [n for n in self._current_grid_rooms()
                if n in self._reachable and eligible(n)]

    def _pick(self, candidates, fallback=None):
        """Choose a random candidate, falling back to _reachable if empty."""
        pool = candidates or fallback or list(self._reachable)
        return self._rng.choice(pool)

    def _add_node_and_edge(self, size, et, parent, **params):
        name = self._new_name()
        self._graph.add_node(name, size)
        self._graph.add_edge(parent or self._current_corridor, name, et, **params)
        self._reachable.add(name)
        return name

    # ── Challenge additions ───────────────────────────────────────────────

    def add_open_room(self, size=None, parent=None) -> str:
        size = size or self._rng.choice([NodeSize.ROOM, NodeSize.HALL])
        return self._add_node_and_edge(size, EdgeType.OPEN, parent)

    def add_closet_room(self, edge_type=EdgeType.OPEN, parent=None) -> str:
        """Add a small CLOSET node attached to an existing room (not the corridor)."""
        candidates = self._room_candidates()
        chosen = parent or (self._pick(candidates) if candidates else self._current_corridor)
        return self._add_node_and_edge(NodeSize.CLOSET, edge_type, chosen)

    def add_breakable_room(self, wall_type='stone', size=None, parent=None) -> str:
        size = size or self._rng.choice([NodeSize.ROOM, NodeSize.HALL])
        return self._add_node_and_edge(size, EdgeType.BREAKABLE, parent,
                                       wall_type=wall_type)

    def add_locked_room(self, colour, size=None, parent=None) -> str:
        """Add room behind LOCKED edge. Places key in an already-reachable room."""
        size = size or self._rng.choice([NodeSize.ROOM, NodeSize.HALL])
        name = self._new_name()
        self._graph.add_node(name, size)
        self._graph.add_edge(parent or self._current_corridor, name,
                             EdgeType.LOCKED, key_colour=colour)
        # Key goes in a non-corridor reachable room, or corridor as last resort
        key_room = self._pick(self._room_candidates())
        self._graph.nodes[key_room].keys.append((colour,))
        self._reachable.add(name)
        return name

    def add_gated_room(self, gate_id, size=None, parent=None) -> str:
        """Add room behind GATED edge. Places plate+block in a suitable
        already-reachable room on the same grid.

        If no eligible room exists on the current grid yet, an open room is
        added automatically to serve as the puzzle room — this keeps the
        plate within the same subgraph as the gate (required for multi-grid
        levels where each grid is laid out independently).
        """
        size = size or NodeSize.ROOM
        name = self._new_name()
        self._graph.add_node(name, size)
        self._graph.add_edge(parent or self._current_corridor, name,
                             EdgeType.GATED, gate_id=gate_id)

        candidates = self._puzzle_candidates()
        if not candidates:
            # No eligible room on this grid yet; add one so the puzzle stays
            # within the subgraph.
            self.add_open_room()
            candidates = self._puzzle_candidates()

        puzzle_room = self._pick(candidates, fallback=self._room_candidates())
        self._graph.nodes[puzzle_room].plates.append((gate_id,))
        self._graph.nodes[puzzle_room].blocks.append(1)
        self._reachable.add(name)
        return name

    def add_water_room(self, size=None, parent=None) -> str:
        """Add room behind WATER edge. Places 2 planks in an already-reachable room."""
        size = size or self._rng.choice([NodeSize.ROOM, NodeSize.HALL])
        name = self._new_name()
        self._graph.add_node(name, size)
        self._graph.add_edge(parent or self._current_corridor, name, EdgeType.WATER)
        dry = [r for r in self._reachable if r not in self._water_rooms]
        for _ in range(2):
            planks_room = self._pick(dry)
            self._graph.nodes[planks_room].materials.append(('planks',))
        self._has_water = True
        self._reachable.add(name)
        self._water_rooms.add(name)
        return name

    # ── Multi-grid ────────────────────────────────────────────────────────

    def start_next_grid(self, super_col, super_row, exit_side='right',
                        source=None, barrier=None, key_colour=None, gate_id=None):
        """Add the next corridor node and a BORDER edge.

        super_col, super_row: position on the super-grid for the new corridor.
        exit_side: which face of the source corridor the exit is on.
        source: name of the corridor from which the BORDER edge originates.
                Defaults to _current_corridor when None.
        barrier / key_colour / gate_id: optional lock on the border passage.

        Places barrier prerequisites in the currently-reachable set before
        switching the default parent to the new corridor.
        """
        prev_corridor = source if source is not None else self._current_corridor
        n = sum(1 for name in self._graph.nodes if name.startswith('corridor'))
        new_name = f'corridor_{n}'
        self._graph.add_node(new_name, NodeSize.CORRIDOR)
        self._graph.nodes[new_name].super_pos = (super_col, super_row)

        entry_side = _OPPOSITE[exit_side]
        params = {'exit_side': exit_side, 'entry_side': entry_side}
        if barrier == 'locked' and key_colour:
            params.update(barrier='locked', key_colour=key_colour)
            key_room = self._pick(list(self._reachable))
            self._graph.nodes[key_room].keys.append((key_colour,))
        elif barrier == 'gated' and gate_id:
            params.update(barrier='gated', gate_id=gate_id)
            puzzle_room = self._pick(self._puzzle_candidates(),
                                     fallback=self._room_candidates())
            self._graph.nodes[puzzle_room].plates.append((gate_id,))
            self._graph.nodes[puzzle_room].blocks.append(1)

        self._graph.add_edge(prev_corridor, new_name, EdgeType.BORDER, **params)
        self._reachable.add(new_name)
        self._current_corridor = new_name

    # ── Content distribution ──────────────────────────────────────────────

    def add_treasures(self, count) -> None:
        all_nodes = list(self._graph.nodes.keys())
        item_nos  = list(range(1, 10))
        for _ in range(count):
            t = self._rng.choice(all_nodes)
            self._graph.nodes[t].treasures.append((self._rng.choice(item_nos),))

    def add_materials(self, mat_types, count) -> None:
        if not mat_types:
            return
        mats = [m for m in mat_types if m != 'planks']  # planks only via add_water_room
        if not mats:
            return
        all_nodes = list(self._graph.nodes.keys())
        for _ in range(count):
            t = self._rng.choice(all_nodes)
            self._graph.nodes[t].materials.append((self._rng.choice(mats),))

    def add_enemies(self, count) -> None:
        item_nos   = list(range(1, 10))
        candidates = [
            n for n, node in self._graph.nodes.items()
            if node.size in (NodeSize.ROOM, NodeSize.HALL)
            and not node.blocks
            and not node.plates
            and not node.has_flames
        ]
        if not candidates:
            return
        forge_placed = False
        for _ in range(count):
            t = self._rng.choice(candidates)
            if self._has_forge and not forge_placed:
                self._graph.nodes[t].enemies.append(('forge_ogre',))
                forge_placed = True
            else:
                self._graph.nodes[t].enemies.append(('chaser',))
            if not self._graph.nodes[t].treasures:
                self._graph.nodes[t].treasures.append(
                    (self._rng.choice(item_nos),))

    def add_flames(self) -> None:
        candidates = [
            n for n, node in self._graph.nodes.items()
            if n != 'corridor'
            and not node.blocks
            and not node.plates
            and not node.enemies
            and not any(e.edge_type == EdgeType.WATER
                        for _, e in self._graph.neighbors(n))
        ]
        if not candidates:
            return
        t = self._rng.choice(candidates)
        self._graph.nodes[t].has_flames = True

    # ── Finalise ──────────────────────────────────────────────────────────

    def build(self) -> 'LevelGraph':
        return self._graph


# (formerly _assign_items — replaced by LevelGraphBuilder)
def _assign_items(graph, feature_set, rng):
    """Distribute treasures, materials, keys, blocks, plates across nodes."""

    all_nodes = list(graph.nodes.keys())
    corridor_name = 'corridor'

    # Find all freely reachable rooms (via OPEN, BREAKABLE, BORDER edges)
    # from the start corridor — these are valid for placing keys/plates
    _free_types = (EdgeType.OPEN, EdgeType.BREAKABLE)
    def _is_free_edge(edge):
        if edge.edge_type in _free_types:
            return True
        if (edge.edge_type == EdgeType.BORDER
                and edge.params.get('barrier', 'open') == 'open'):
            return True
        return False

    def _freely_reachable(exclude_edge=None):
        """Rooms reachable without crossing locked/gated/water edges."""
        reached = {corridor_name}
        frontier = [corridor_name]
        while frontier:
            current = frontier.pop()
            for name, edge in graph.neighbors(current):
                if name in reached:
                    continue
                if exclude_edge is not None and id(edge) == id(exclude_edge):
                    continue
                if _is_free_edge(edge):
                    reached.add(name)
                    frontier.append(name)
        return list(reached)

    # Collect which keys, gates, and water crossings are needed
    needed_keys = []     # [(colour, edge), ...]  one per locked edge
    needed_gates = {}    # {gate_id: edge}
    needed_water = {}    # {water_id: edge}
    for edge in graph.edges:
        if edge.edge_type == EdgeType.LOCKED:
            colour = edge.params['key_colour']
            needed_keys.append((colour, edge))
        elif edge.edge_type == EdgeType.GATED:
            gate_id = edge.params['gate_id']
            needed_gates[gate_id] = edge
        elif edge.edge_type == EdgeType.WATER:
            water_id = edge.params.get('water_id', f'water_{id(edge)}')
            needed_water[water_id] = edge
        elif edge.edge_type == EdgeType.BORDER:
            barrier = edge.params.get('barrier', 'open')
            if barrier == 'locked':
                colour = edge.params['key_colour']
                needed_keys.append((colour, edge))
            elif barrier == 'gated':
                gate_id = edge.params['gate_id']
                needed_gates[gate_id] = edge

    # For each locked edge, place a key on the reachable side
    for colour, edge in needed_keys:
        candidates = _freely_reachable(exclude_edge=edge)
        if edge.node_b in candidates:
            candidates.remove(edge.node_b)
        if not candidates:
            candidates = [corridor_name]
        target = rng.choice(candidates)
        graph.nodes[target].keys.append((colour,))

    # For each gated edge, place plate AND block in the SAME room.
    # Never in a corridor — too narrow for pushing.
    for gate_id, edge in needed_gates.items():
        candidates = [n for n in _freely_reachable(exclude_edge=edge)
                      if n != edge.node_b
                      and graph.nodes[n].size != NodeSize.CORRIDOR]
        if not candidates:
            candidates = _freely_reachable(exclude_edge=edge)
            if edge.node_b in candidates:
                candidates.remove(edge.node_b)
        if not candidates:
            candidates = [corridor_name]
        target = rng.choice(candidates)
        graph.nodes[target].plates.append((gate_id,))
        graph.nodes[target].blocks.append(1)

    # For each water edge, ensure planks are reachable on the start side
    for water_id, edge in needed_water.items():
        candidates = _freely_reachable(exclude_edge=edge)
        if edge.node_b in candidates:
            candidates.remove(edge.node_b)
        if not candidates:
            candidates = [corridor_name]
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

    # Distribute enemies. Excluded from:
    # - corridors (grid-connecting rooms)
    # - nodes connected by a BORDER edge (transition zones)
    # - puzzle rooms (blocks/plates)
    # - flame rooms
    e_min, e_max = feature_set.get('enemy_count', (1, 3))
    e_count = max(1, rng.randint(e_min, e_max))
    hazard_rooms = {n for n, node in graph.nodes.items()
                    if node.blocks or node.plates or node.has_flames}
    corridors = {n for n, node in graph.nodes.items()
                 if node.size == NodeSize.CORRIDOR}
    excluded = corridors | hazard_rooms
    enemy_candidates = [n for n in all_nodes if n not in excluded]
    if not enemy_candidates:
        enemy_candidates = [n for n in all_nodes
                            if n not in corridors]
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
