"""Core game logic and rendering."""
import os
import sys
import random
from collections import deque
import pygame
from constants import *
from sprites import create_sprites, draw_flame_at
from levels import LEVELS
from entities import Player, Enemy, PatrolEnemy, ForgeOgre
from hiscore import load_scores, save_score, qualifies
from sounds import SoundManager
from rooms import RoomState, parse_level_walls, find_exit
from crafting import (Inventory, RECIPES, CRAFT_NAMES, CRAFT_ICONS,
                      CRAFT_STONE_WALL, CRAFT_BRIDGE,
                      MATERIAL_NAMES, MATERIAL_ICONS,
                      TOOL_NAMES, TOOL_ICONS, MAT_ROCKS,
                      KEY_NAMES, KEY_COLORS)

# ── States ────────────────────────────────────────────────────────────────────
TITLE       = 'title'
QUIT_GAME   = 'quit'
DIFFICULTY  = 'difficulty'
STORY       = 'story'
LEVEL_INTRO = 'level_intro'
PLAYING     = 'playing'
PAUSED      = 'paused'
GAME_OVER   = 'game_over'
WIN         = 'win'
ENTER_SCORE = 'enter_score'
SHOW_SCORES = 'show_scores'
PLAY_AGAIN  = 'play_again'
INVENTORY   = 'inventory'

NUM_LEVELS  = len(LEVELS)
ACT1_BOSS_LEVEL = 10


def _flame_tile_intensity(jet, tile_idx, timer_ms):
    """Compute flame intensity (0.0-1.0) for a tile in a jet.

    The flame sweeps from tile 0 to the last tile during the on phase,
    then fades from the last tile back during the off phase.
    Each tile's ignition is staggered by a delay proportional to its
    position in the jet.
    """
    n = len(jet['tiles'])
    on_ms = jet['on_ms']
    off_ms = jet['off_ms']
    cycle = on_ms + off_ms
    phase = timer_ms % cycle

    # Time each tile takes to ignite/fade (stagger across the on/off period)
    sweep_ms = on_ms * 0.6       # 60% of on-time used for sweep
    sustain_ms = on_ms - sweep_ms  # remaining time at full intensity
    tile_delay = (sweep_ms / max(1, n)) * tile_idx

    if phase < on_ms:
        # On phase: tiles ignite with staggered delay
        tile_phase = phase - tile_delay
        if tile_phase < 0:
            return 0.0
        if tile_phase < sweep_ms / max(1, n):
            return min(1.0, tile_phase / (sweep_ms / max(1, n) * 0.5))
        return 1.0
    else:
        # Off phase: tiles fade from last to first (reverse sweep)
        fade_phase = phase - on_ms
        reverse_idx = n - 1 - tile_idx
        tile_delay_fade = (off_ms * 0.6 / max(1, n)) * reverse_idx
        tile_phase = fade_phase - tile_delay_fade
        if tile_phase < 0:
            return 1.0
        fade_dur = off_ms * 0.4 / max(1, n)
        if fade_dur <= 0:
            return 0.0
        return max(0.0, 1.0 - tile_phase / fade_dur)


class Game:
    def __init__(self, surface: pygame.Surface):
        self.surf = surface
        self.sprites = create_sprites()
        self.sounds = SoundManager()
        self._init_fonts()
        self.difficulty = EASY   # persists across games; player changes it on difficulty screen
        self._debug    = False   # set by main.py when launched with --level; skips menus/hiscore
        self.state = TITLE
        self._title_init()

    # ── Font setup ────────────────────────────────────────────────────────────

    def _init_fonts(self):
        base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        ttf  = os.path.join(base, 'fonts', 'ShareTechMono-Regular.ttf')
        self.font_big   = pygame.font.Font(ttf, 36)
        self.font_med   = pygame.font.Font(ttf, 22)
        self.font_small = pygame.font.Font(ttf, 16)
        self.font_hud   = pygame.font.Font(ttf, 16)
        self.font_title = pygame.font.Font(ttf, 64)

    # ── Pathfinding ───────────────────────────────────────────────────────────

    def _bfs_from(self, col, row):
        """BFS distance map from (col, row) to every reachable open tile."""
        dist = {(col, row): 0}
        q = deque([(col, row)])
        while q:
            c, r = q.popleft()
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nc, nr = c + dc, r + dr
                if ((nc, nr) not in dist
                        and 0 <= nc < COLS and 0 <= nr < ROWS
                        and not self.walls[nc][nr]):
                    dist[(nc, nr)] = dist[(c, r)] + 1
                    q.append((nc, nr))
        return dist

    # ── Wall helpers ──────────────────────────────────────────────────────────

    def _build_walls(self):
        """Rebuild the full collision map from border + level + placed walls."""
        w = [[False] * ROWS for _ in range(COLS)]
        # Border
        for c in range(COLS):
            w[c][0] = w[c][ROWS - 1] = True
        for r in range(ROWS):
            w[0][r] = w[COLS - 1][r] = True
        # Level walls (dict: (col, row) → wall_type)
        for (c, r) in self._level_walls:
            w[c][r] = True
        # Placed walls
        for (c, r) in self._placed_walls:
            w[c][r] = True
        self.walls = w

    def _is_border(self, col, row):
        return col == 0 or col == COLS - 1 or row == 0 or row == ROWS - 1

    def _door_orient(self, col, row):
        """Detect orientation from adjacent reinforced walls only.
        'v' = vertical passage (reinforced wall left or right),
        'h' = horizontal (reinforced wall above or below)."""
        def _is_reinforced(c, r):
            if c == 0 or c == COLS - 1 or r == 0 or r == ROWS - 1:
                return True  # border is always reinforced
            return self._level_walls.get((c, r)) == WALL_REINFORCED
        left  = col > 0 and _is_reinforced(col - 1, row)
        right = col < COLS - 1 and _is_reinforced(col + 1, row)
        if left or right:
            return 'v'
        return 'h'

    def _is_unbumpable(self, col, row):
        """Check if (col, row) is a door, gate, or pushable block."""
        if not self._is_multiroom:
            return False
        rk = self._current_room
        for dc, dr, _ in self._room_doors.get(rk, []):
            if dc == col and dr == row:
                return True
        for gc, gr in self._room_gates.get(rk, {}).values():
            if gc == col and gr == row:
                return True
        if (col, row) in self._room_blocks.get(rk, []):
            return True
        if (col, row) in getattr(self, '_water_tiles', set()):
            return True
        return False

    def _register_bump(self, key, col, row):
        """Called when the player walks into wall (col, row) via direction key."""
        if key in self._bump_consumed:
            return  # key not released since last hit — ignore
        # Doors and bridges can be on border tiles (grid transitions)
        if self._try_auto_open_door(col, row):
            return
        if self._try_auto_bridge(col, row):
            return
        if self._is_border(col, row):
            return  # indestructible border (no door/bridge here)
        wall_type = self._level_walls.get((col, row))
        if wall_type == WALL_REINFORCED:
            return  # indestructible — bumping has no effect
        if self._is_unbumpable(col, row):
            return  # gates and blocks are not breakable by bumping
        self._bump_consumed.add(key)
        hits_needed = WALL_BUMPS.get(wall_type, WALL_HITS_TO_BREAK)
        hits = self._wall_hits.get((col, row), 0) + 1
        if hits >= hits_needed:
            self._break_wall(col, row)
        else:
            self._wall_hits[(col, row)] = hits
            self.sounds.play('bump')

    def _break_wall(self, col, row):
        self._wall_hits.pop((col, row), None)
        self._level_walls.pop((col, row), None)
        self._placed_walls.discard((col, row))
        if self._is_multiroom:
            self._build_walls_multiroom()
        else:
            self._build_walls()
        self.sounds.play('break')
        self._breaks_toward_credit += 1
        if self._breaks_toward_credit >= BREAKS_PER_CREDIT:
            self._breaks_toward_credit -= BREAKS_PER_CREDIT
            self._place_credits += 1
            self.sounds.play('credit')

    # ── Game initialisation ───────────────────────────────────────────────────

    def _full_reset(self):
        from levels import regenerate_act2
        regenerate_act2()
        self.score        = 0
        self.lives        = STARTING_LIVES
        self.level        = 0
        self.item_no         = 0
        self.shield       = False
        self._shield_timer = 0
        self.move_ms      = BASE_MOVE_MS
        self.enemy_ms     = BASE_ENEMY_MS  # overridden to BOSS_MOVE_MS on level 10
        self._placed_walls  = set()
        self._wall_hits     = {}   # (col, row) → hit count (inner walls only)
        self._breaks_toward_credit    = 0    # leftover breaks toward next credit
        self._place_credits = 0   # available wall placements
        self._bump_consumed = set()  # direction keys that must be released before next bump
        self.inventory = Inventory()
        self._inv_cursor = 0  # cursor position in inventory screen
        self._start_level(1)

    def _start_level(self, level_num):
        self.level = level_num
        self.item_no  = 0
        data = LEVELS[level_num - 1]

        # Refund one credit per placed wall being cleared
        self._place_credits += len(self._placed_walls)
        self._placed_walls.clear()
        self._wall_hits.clear()
        self._bump_consumed.clear()

        # Multi-room setup
        self._is_multiroom = 'rooms' in data
        self._room_states = {}
        self._current_room = None
        self._level_data = data
        self._transition_timer = 0

        if self._is_multiroom:
            self._current_room = data['start_room']
            pc, pr = data['player_start']
            self.player = Player(pc, pr)
            # Pre-placed treasures and materials: gather from all rooms
            self._loot_total = 0
            self._loot_collected = 0
            self._room_treasures = {}
            self._room_materials = {}
            self._room_keys = {}
            self._room_doors = {}
            self._room_blocks = {}
            self._room_plates = {}
            self._room_gates = {}
            self._bridged_tiles = set()
            self._gate_open = set()  # set of currently open gate_ids
            for rkey, rdata in data['rooms'].items():
                treasures = list(rdata.get('treasures', []))
                self._room_treasures[rkey] = treasures
                self._loot_total += len(treasures)
                self._room_materials[rkey] = list(rdata.get('materials', []))
                self._room_keys[rkey] = list(rdata.get('keys', []))
                self._room_doors[rkey] = list(rdata.get('locked_doors', []))
                self._room_blocks[rkey] = list(rdata.get('pushable_blocks', []))
                self._room_plates[rkey] = list(rdata.get('pressure_plates', []))
                self._room_gates[rkey] = {gid: (gc, gr)
                                           for gc, gr, gid in rdata.get('gates', [])}
            self.treasure_pos = None
            self._opened_doors = set()
            # Count water edges for bridge limit (one bridge per edge)
            self._bridges_remaining = sum(
                1 for rdata in data['rooms'].values()
                if rdata.get('water_tiles'))
            self._tile_owner = {}
            self._room_blocks_initial = {
                rk: list(self._room_blocks[rk])
                for rk in self._room_blocks}
            self._enter_room(self._current_room)
        else:
            self._level_walls = parse_level_walls(data['walls'])
            self._build_walls()
            pc, pr = data['player_start']
            self.player = Player(pc, pr)
            starts = data['enemy_starts']
            active = starts if (self.difficulty == HARD and level_num != ACT1_BOSS_LEVEL) \
                     else starts[:1]
            self.enemies = [Enemy(ec, er) for ec, er in active]

        # Speed scaling
        if level_num >= ACT2_START_LEVEL:
            act2_last = 20
            factor = 1.05 ** (act2_last - level_num)   # 1.0 at level 20
            self.enemy_ms = round(ACT2_BASE_ENEMY_MS * factor)
            self.move_ms  = round(ACT2_BASE_MOVE_MS  * factor)
        elif level_num == ACT1_BOSS_LEVEL:
            self.enemy_ms = BOSS_MOVE_MS
            self.move_ms  = BASE_MOVE_MS
        else:
            factor = 1.07 ** (ACT1_BOSS_LEVEL - level_num)
            self.enemy_ms = round(BASE_ENEMY_MS * factor)
            self.move_ms  = round(BASE_MOVE_MS  * factor)

        self.shield = False
        self._shield_timer = 0
        if not self._is_multiroom:
            self._spawn_treasure()
        self._move_timer   = 0
        self._enemy_timer  = 0
        self._key_repeat   = {}
        self._flash_timer  = 0
        self._intro_timer  = 0
        self.sounds.start_music(level_num)
        if level_num == ACT1_BOSS_LEVEL:
            self.sounds.play('boss_appear')

    # ── Multi-room support ────────────────────────────────────────────────────

    def _enter_room(self, room_key):
        """Load a room, restoring saved state if the player has visited before."""
        room_data = self._level_data['rooms'][room_key]
        self._current_room = room_key
        self._current_room_data = room_data

        if room_key in self._room_states:
            st = self._room_states[room_key]
            self._level_walls = st.level_walls
            self._placed_walls = st.placed_walls
            self._wall_hits = st.wall_hits
            self.enemies = st.enemies
            self._room_treasures[room_key] = st.treasures
            self._room_materials[room_key] = st.materials
            self._room_keys[room_key] = st.keys
            self._room_doors[room_key] = st.doors
            self._room_blocks[room_key] = st.blocks
        else:
            self._level_walls = parse_level_walls(room_data['walls'])
            self._placed_walls = set()
            self._wall_hits = {}
            starts = room_data.get('enemy_starts', [])
            patrols = room_data.get('patrol_enemies', [])
            if self.difficulty == HARD:
                active = starts
                active_patrols = patrols
            else:
                # EASY: keep all special enemies + up to 1 regular chaser
                special = [s for s in starts if len(s) >= 3 and s[2] != 'chaser']
                regular = [s for s in starts if len(s) < 3 or s[2] == 'chaser']
                active = special + regular[:1]
                active_patrols = patrols[:1] if patrols else []
            self.enemies = []
            for edata in active:
                if len(edata) >= 3:
                    ec, er, etype = edata[0], edata[1], edata[2]
                else:
                    ec, er, etype = edata[0], edata[1], 'chaser'
                if etype == 'forge_ogre':
                    self.enemies.append(ForgeOgre(ec, er))
                else:
                    self.enemies.append(Enemy(ec, er))
            for pdata in active_patrols:
                pe = PatrolEnemy(pdata['start'][0], pdata['start'][1],
                                 pdata['waypoints'])
                self.enemies.append(pe)

        self._tile_owner = room_data.get('tile_owner', {})
        self._water_tiles = set(tuple(t) for t in room_data.get('water_tiles', []))
        self._dead_squares = set(tuple(t) for t in room_data.get('dead_squares', []))
        self._flame_jets = room_data.get('flame_jets', [])
        for jet in self._flame_jets:
            jet['_tile_set'] = frozenset(tuple(t) for t in jet['tiles'])
        self._flame_timer = 0
        self._build_walls_multiroom()
        self._bump_consumed.clear()
        self._tag_enemies_with_rooms()
        self._verify_blocks()

    def _verify_blocks(self):
        """Check blocks are pushable. Regenerate level if any are stuck."""
        if not self._is_multiroom:
            return
        rk = self._current_room
        for bc, br in self._room_blocks.get(rk, []):
            push_dirs = 0
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                pf_c, pf_r = bc - dc, br - dr
                pt_c, pt_r = bc + dc, br + dr
                pf_ok = (0 < pf_c < COLS - 1 and 0 < pf_r < ROWS - 1
                         and not self.walls[pf_c][pf_r])
                pt_ok = (0 < pt_c < COLS - 1 and 0 < pt_r < ROWS - 1
                         and not self.walls[pt_c][pt_r])
                if pf_ok and pt_ok:
                    push_dirs += 1
            if push_dirs == 0:
                from levels import regenerate_act2
                regenerate_act2()
                self._start_level(self.level)
                return

    def _tag_enemies_with_rooms(self):
        """Assign each enemy to its room based on tile_owner map."""
        if not self._tile_owner:
            return
        room_tiles_cache = {}
        for enemy in self.enemies:
            room = self._tile_owner.get((enemy.col, enemy.row))
            if room:
                enemy.room_name = room
                if room not in room_tiles_cache:
                    room_tiles_cache[room] = frozenset(
                        pos for pos, name in self._tile_owner.items()
                        if name == room)
                enemy.room_tiles = room_tiles_cache[room]

    def _player_room(self):
        """Return the graph node name the player is currently in, or None."""
        return self._tile_owner.get(
            (self.player.col, self.player.row))

    def _save_room_state(self):
        """Snapshot the current room's mutable state before leaving."""
        rk = self._current_room
        self._room_states[rk] = RoomState(
            level_walls=dict(self._level_walls),
            placed_walls=set(self._placed_walls),
            wall_hits=dict(self._wall_hits),
            enemies=list(self.enemies),
            treasures=list(self._room_treasures.get(rk, [])),
            materials=list(self._room_materials.get(rk, [])),
            keys=list(self._room_keys.get(rk, [])),
            doors=list(self._room_doors.get(rk, [])),
            blocks=list(self._room_blocks.get(rk, [])),
        )

    def _build_walls_multiroom(self):
        """Build collision map for a multi-room level."""
        self._build_walls()
        room_key = self._current_room
        # Open exit tiles in the border FIRST
        room_data = self._current_room_data
        for exit_key in room_data.get('exits', {}):
            side, pos_str = exit_key.rsplit('_', 1)
            pos = int(pos_str)
            if side == 'left':
                self.walls[0][pos] = False
            elif side == 'right':
                self.walls[COLS - 1][pos] = False
            elif side == 'top':
                self.walls[pos][0] = False
            elif side == 'bottom':
                self.walls[pos][ROWS - 1] = False
        # Then apply obstacles on top (doors/gates can block exits)
        for dc, dr, _color in self._room_doors.get(room_key, []):
            self.walls[dc][dr] = True
        for bc, br in self._room_blocks.get(room_key, []):
            self.walls[bc][br] = True
        for wc, wr in getattr(self, '_water_tiles', set()):
            if (wc, wr) not in getattr(self, '_bridged_tiles', set()):
                self.walls[wc][wr] = True
        for gate_id, (gc, gr) in self._room_gates.get(room_key, {}).items():
            if gate_id not in self._gate_open:
                self.walls[gc][gr] = True

    def _try_room_transition(self):
        """Check if the player is on an exit tile and transition if so."""
        if not self._is_multiroom:
            return False
        result = find_exit(self.player.col, self.player.row,
                           self._current_room_data)
        if result is None:
            return False
        target_room, entry_col, entry_row = result
        self._save_room_state()
        self._enter_room(target_room)
        self.player.col, self.player.row = entry_col, entry_row
        self._transition_timer = 300
        self.sounds.play('move')
        return True

    def _collect_loot(self):
        """Check if the player is standing on a pre-placed treasure (Act 2)."""
        pc, pr = self.player.col, self.player.row
        room_key = self._current_room
        treasures = self._room_treasures.get(room_key, [])
        for i, (tc, tr, item_no) in enumerate(treasures):
            if pc == tc and pr == tr:
                self.score += TREASURE_POINTS.get(item_no, 0)
                self.sounds.play('collect')
                treasures.pop(i)
                self._loot_collected += 1
                if self._loot_collected >= self._loot_total:
                    self._advance_level()
                return

    def _collect_materials(self):
        """Check if the player is standing on a material pickup (Act 2)."""
        if not self._is_multiroom:
            return
        pc, pr = self.player.col, self.player.row
        room_key = self._current_room
        materials = self._room_materials.get(room_key, [])
        for i, (mc, mr, mat_type) in enumerate(materials):
            if pc == mc and pr == mr:
                self.inventory.add_material(mat_type)
                self.sounds.play('collect')
                materials.pop(i)
                return

    def _collect_keys(self):
        """Check if the player is standing on a key pickup (Act 2)."""
        if not self._is_multiroom:
            return
        pc, pr = self.player.col, self.player.row
        room_key = self._current_room
        keys = self._room_keys.get(room_key, [])
        for i, (kc, kr, key_color) in enumerate(keys):
            if pc == kc and pr == kr:
                self.inventory.add_key(key_color)
                self.sounds.play('collect')
                keys.pop(i)
                return

    def _update_pressure_plates(self):
        """Check pressure plates and open/close linked gates."""
        if not self._is_multiroom:
            return
        room_key = self._current_room
        plates = self._room_plates.get(room_key, [])
        if not plates:
            return

        occupied = {(self.player.col, self.player.row)}
        occupied.update((e.col, e.row) for e in self.enemies)
        block_set = set(self._room_blocks.get(room_key, []))

        changed = False
        for pc, pr, gate_id in plates:
            pressed = (pc, pr) in occupied or (pc, pr) in block_set
            was_open = gate_id in self._gate_open
            if pressed and not was_open:
                self._gate_open.add(gate_id)
                changed = True
            elif not pressed and was_open:
                self._gate_open.discard(gate_id)
                changed = True
        if changed:
            self._build_walls_multiroom()

    def _try_push_block(self, bc, br, dcol, drow):
        """Try to push a block at (bc, br) in direction (dcol, drow)."""
        if not self._is_multiroom:
            return False
        room_key = self._current_room
        blocks = self._room_blocks.get(room_key, [])
        for i, (bx, by) in enumerate(blocks):
            if bx == bc and by == br:
                nc, nr = bc + dcol, br + drow
                if (0 < nc < COLS - 1 and 0 < nr < ROWS - 1
                        and not self.walls[nc][nr]
                        and (nc, nr) not in self._dead_squares):
                    blocks[i] = (nc, nr)
                    self._build_walls_multiroom()
                    self.sounds.play('bump')
                    return True
                return False
        return False

    def _try_auto_open_door(self, col, row):
        """Open a locked door at (col, row) if the player has the key."""
        if not self._is_multiroom:
            return False
        room_key = self._current_room
        doors = self._room_doors.get(room_key, [])
        for i, (door_c, door_r, door_color) in enumerate(doors):
            if door_c == col and door_r == row:
                if self.inventory.has_key(door_color):
                    self.inventory.use_key(door_color)
                    doors.pop(i)
                    self._opened_doors.add((room_key, col, row, door_color))
                    self._build_walls_multiroom()
                    self.sounds.play('break')
                    return True
                return False
        return False

    def _spawn_treasure(self):
        self.item_no += 1
        if self.item_no > 9:
            self.item_no = 1
        self.treasure_item_no = 10 if (self.item_no == 9 and self.level == ACT1_BOSS_LEVEL) \
                             else self.item_no
        # Crown on the boss level spawns at a fixed position inside the vault
        if self.treasure_item_no == 10:
            data = LEVELS[self.level - 1]
            if 'crown_pos' in data:
                self.treasure_pos = data['crown_pos']
                return
        open_tiles = [
            (c, r) for c in range(1, COLS - 1) for r in range(1, ROWS - 1)
            if not self.walls[c][r]
            and (c, r) != (self.player.col, self.player.row)
            and (c, r) not in {(e.col, e.row) for e in self.enemies}
        ]
        self.treasure_pos = random.choice(open_tiles) if open_tiles else (1, 1)

    def _relocate_treasure(self):
        """Boss walked over a treasure — move it to a new random open tile.
        The crown (fixed in the vault) is never relocated."""
        if self.treasure_item_no == 10:
            return
        open_tiles = [
            (c, r) for c in range(1, COLS - 1) for r in range(1, ROWS - 1)
            if not self.walls[c][r]
            and (c, r) != (self.player.col, self.player.row)
            and (c, r) not in {(e.col, e.row) for e in self.enemies}
        ]
        if open_tiles:
            self.treasure_pos = random.choice(open_tiles)
            self.sounds.play('item_hit')

    # ── Title screen ─────────────────────────────────────────────────────────

    def _title_init(self):
        self.state = TITLE
        self._title_ms = 0
        self.sounds.start_music('title')
        # One ogre per corner: [x, y, vx, vy] (floats; px and px/s).
        # Bounds are sprite top-left ranges keeping the 32×32 sprite inside its corner.
        # TL=ogre1, TR=ogre2, BL=ogre3, BR=boss
        self._title_ogre_bounds = [
            ( 10, 140,   0, 100),   # top-left
            (800, 928,   0, 100),   # top-right
            ( 10, 140, 420, 508),   # bottom-left
            (800, 928, 420, 508),   # bottom-right
        ]
        self._title_ogres = [
            [float((b[0] + b[1]) // 2), float((b[2] + b[3]) // 2),
             random.choice([-1, 1]) * random.uniform(45, 75),
             random.choice([-1, 1]) * random.uniform(35, 60)]
            for b in self._title_ogre_bounds
        ]

    def _update_title_ogres(self, dt):
        for i, ogre in enumerate(self._title_ogres):
            xmin, xmax, ymin, ymax = self._title_ogre_bounds[i]
            ogre[0] += ogre[2] * dt / 1000
            ogre[1] += ogre[3] * dt / 1000
            if ogre[0] < xmin:
                ogre[0] = xmin; ogre[2] = abs(ogre[2])
            elif ogre[0] > xmax:
                ogre[0] = xmax; ogre[2] = -abs(ogre[2])
            if ogre[1] < ymin:
                ogre[1] = ymin; ogre[3] = abs(ogre[3])
            elif ogre[1] > ymax:
                ogre[1] = ymax; ogre[3] = -abs(ogre[3])

    # ── Input handling ────────────────────────────────────────────────────────

    def handle_event(self, event):
        if self.state == TITLE:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.state = DIFFICULTY
                elif event.key == pygame.K_h:
                    self.state = SHOW_SCORES
                    self._scores_return_to = TITLE
                elif event.key == pygame.K_s:
                    self.state = STORY
                elif event.key == pygame.K_q:
                    self.state = QUIT_GAME

        elif self.state == DIFFICULTY:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_e, pygame.K_1):
                    self.difficulty = EASY
                    self._full_reset()
                    self._intro_timer = 2000
                    self.state = LEVEL_INTRO
                elif event.key in (pygame.K_h, pygame.K_2):
                    self.difficulty = HARD
                    self._full_reset()
                    self._intro_timer = 2000
                    self.state = LEVEL_INTRO
                elif event.key == pygame.K_ESCAPE:
                    self._title_init()

        elif self.state == STORY:
            if event.type == pygame.KEYDOWN:
                self._title_init()

        elif self.state == LEVEL_INTRO:
            if event.type == pygame.KEYDOWN:
                self._intro_timer = 0   # skip wait

        elif self.state == PLAYING:
            self._playing_event(event)

        elif self.state == PAUSED:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                self.state = PLAYING
                self.sounds.unpause_music()

        elif self.state in (GAME_OVER, WIN):
            if event.type == pygame.KEYDOWN:
                self.try_enter_score()

        elif self.state == PLAY_AGAIN:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_j or event.key == pygame.K_y:
                    if self._debug:
                        level = self.level
                        self._full_reset()
                        self._start_level(level)
                        self.state = PLAYING
                    else:
                        self.state = DIFFICULTY
                elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                    if self._debug:
                        self.state = QUIT_GAME
                    else:
                        self._title_init()

        elif self.state == INVENTORY:
            self._inventory_event(event)

        elif self.state == ENTER_SCORE:
            self._enter_score_event(event)

        elif self.state == SHOW_SCORES:
            if event.type == pygame.KEYDOWN:
                self.state = getattr(self, '_scores_return_to', TITLE)

    def _playing_event(self, event):
        if event.type == pygame.KEYDOWN:
            k = event.key
            if k == pygame.K_ESCAPE:
                self.state = PLAY_AGAIN
            elif k == pygame.K_p:
                self.state = PAUSED
                self.sounds.pause_music()
            elif k == pygame.K_RETURN:
                self._buy_shield()
            elif k == pygame.K_SPACE:
                if self._is_multiroom:
                    self._act2_place()
                else:
                    self._place_wall()
            elif k == pygame.K_TAB and self._is_multiroom:
                self.state = INVENTORY
                self._inv_cursor = 0
                self.sounds.pause_music()
            elif k == pygame.K_F10:
                self._advance_level()  # cheat: skip to next level
            # Register key-down for movement
            if k in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                now = pygame.time.get_ticks()
                self._key_repeat[k] = (now, now)
                self._try_move_key(k)

        elif event.type == pygame.KEYUP:
            self._key_repeat.pop(event.key, None)
            self._bump_consumed.discard(event.key)  # key released → next press can bump

    def _buy_shield(self):
        if not self.shield and self.score >= SHIELD_COST_PTS:
            self.shield = True
            self._shield_timer = SHIELD_DURATION_MS
            self.score -= SHIELD_COST_PTS
            self.sounds.play('shield_buy')

    def _enter_score_event(self, event):
        if event.type == pygame.KEYDOWN:
            k = event.key
            if k == pygame.K_RETURN and self._name_input.strip():
                save_score(self._name_input.strip(), self._final_score, self._final_level)
                self._scores_return_to = PLAY_AGAIN
                self.state = SHOW_SCORES
            elif k == pygame.K_BACKSPACE:
                self._name_input = self._name_input[:-1]
            elif len(self._name_input) < 20 and event.unicode.isprintable():
                self._name_input += event.unicode

    # ── Movement helpers ──────────────────────────────────────────────────────

    _DIR_MAP = {
        pygame.K_LEFT:  (-1,  0),
        pygame.K_RIGHT: ( 1,  0),
        pygame.K_UP:    ( 0, -1),
        pygame.K_DOWN:  ( 0,  1),
    }

    def _try_move_key(self, key):
        dcol, drow = self._DIR_MAP[key]
        moved = self.player.try_move(dcol, drow, self.walls)
        if moved:
            self._bump_consumed.discard(key)
            self.sounds.play('move')
        else:
            tc = self.player.col + dcol
            tr = self.player.row + drow
            # Off-screen: grid transition if at an exit
            if not (0 <= tc < COLS and 0 <= tr < ROWS):
                if self._is_multiroom:
                    self._try_room_transition()
                return
            if self.walls[tc][tr]:
                if self._try_push_block(tc, tr, dcol, drow):
                    self.player.col, self.player.row = tc, tr
                    self._bump_consumed.discard(key)
                    self.sounds.play('move')
                else:
                    self._register_bump(key, tc, tr)

    def _place_wall(self):
        c, r = self.player.col, self.player.row
        if self._place_credits > 0 and not self.walls[c][r]:
            self._place_credits -= 1
            self._placed_walls.add((c, r))
            self._build_walls()
            self.sounds.play('place_wall')

    def _act2_place(self):
        """SPACE in Act 2: place the active item."""
        c, r = self.player.col, self.player.row
        active = self.inventory.active_item
        if active == CRAFT_STONE_WALL:
            if not self.walls[c][r]:
                if self.inventory.has_item(CRAFT_STONE_WALL):
                    self.inventory.use_item(CRAFT_STONE_WALL)
                elif self.inventory.can_quick_place_wall():
                    self.inventory.quick_place_wall()
                else:
                    return
                self._placed_walls.add((c, r))
                if self._is_multiroom:
                    self._build_walls_multiroom()
                else:
                    self._build_walls()
                self.sounds.play('place_wall')


    def _inventory_event(self, event):
        """Handle input in the inventory/crafting screen."""
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k in (pygame.K_ESCAPE, pygame.K_TAB):
            self.state = PLAYING
            self.sounds.unpause_music()
        elif k == pygame.K_UP:
            self._inv_cursor = max(0, self._inv_cursor - 1)
        elif k == pygame.K_DOWN:
            self._inv_cursor = min(len(RECIPES) - 1, self._inv_cursor + 1)
        elif k == pygame.K_RETURN:
            if self.inventory.can_craft(self._inv_cursor):
                self.inventory.craft(self._inv_cursor)
                self.sounds.play('credit')
        elif k == pygame.K_SPACE:
            result = RECIPES[self._inv_cursor][0]
            self.inventory.active_item = result

    # ── Level transitions ─────────────────────────────────────────────────────

    def _advance_level(self):
        if self.level >= NUM_LEVELS:
            self._end_game(won=True)
            return
        self.lives += 1
        self.sounds.play('level_up')
        self._start_level(self.level + 1)
        self._intro_timer = 2000
        self.state = LEVEL_INTRO

    def _on_caught(self, enemy):
        """Handle player-enemy collision: respawn the enemy far away, then apply hit."""
        self._respawn_enemy(enemy)
        if self.shield:
            self.shield = False
            self._shield_timer = 0
            self.sounds.play('caught_shield')
        else:
            self.sounds.play('caught')
            self._lose_life()

    def _lose_life(self):
        self.score = max(0, self.score - LIFE_PENALTY)
        self.lives -= 1
        self._flash_timer = 600
        if self.lives <= 0:
            self._end_game(won=False)
        else:
            data = LEVELS[self.level - 1]
            self.player.col, self.player.row = data['player_start']
            if self._is_multiroom:
                self._reset_blocks()

    def _reset_blocks(self):
        """Reset all pushable blocks to their starting positions and close
        any gates that were held open by blocks on plates."""
        for rk, initial in self._room_blocks_initial.items():
            self._room_blocks[rk] = list(initial)
        self._gate_open.clear()
        if self._is_multiroom:
            self._build_walls_multiroom()

    def _try_auto_bridge(self, col, row):
        """Build a bridge on a water tile when the player bumps it.

        Only builds if: player has a bridge item, this stream hasn't
        been bridged yet (one bridge per water edge), and the tile
        connects to open floor on the opposite side.
        """
        if not self._is_multiroom:
            return False
        water = getattr(self, '_water_tiles', set())
        bridged = getattr(self, '_bridged_tiles', set())
        if (col, row) not in water or (col, row) in bridged:
            return False
        if not self.inventory.has_item(CRAFT_BRIDGE):
            return False
        if self._bridges_remaining <= 0:
            return False
        # Check that the opposite side has open floor (not wall/water)
        pc, pr = self.player.col, self.player.row
        dc, dr = col - pc, row - pr
        far_c, far_r = col + dc, row + dr
        if (0 < far_c < COLS - 1 and 0 < far_r < ROWS - 1
                and not self.walls[far_c][far_r]):
            self.inventory.use_item(CRAFT_BRIDGE)
            self._bridged_tiles.add((col, row))
            self._bridges_remaining -= 1
            self._build_walls_multiroom()
            self.sounds.play('place_wall')
            return True
        return False

    def _forge_ogre_attack(self, enemy):
        """Forge ogre damages an adjacent player-placed wall (2 hits to break)."""
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            tc, tr = enemy.col + dc, enemy.row + dr
            if (tc, tr) in self._placed_walls:
                hits = self._wall_hits.get((tc, tr), 0) + 1
                if hits >= enemy.wall_bump_power:
                    self._break_wall(tc, tr)
                else:
                    self._wall_hits[(tc, tr)] = hits
                    self.sounds.play('bump')
                return

    def _respawn_enemy(self, enemy):
        """Teleport enemy to a tile at significant BFS distance from the player.
        In Act 2, the enemy stays within its own room."""
        dist = self._bfs_from(self.player.col, self.player.row)
        others = {(e.col, e.row) for e in self.enemies if e is not enemy}
        excl = {self.treasure_pos} if self.treasure_pos else set()
        room = enemy.room_tiles

        def _valid(pos, min_dist):
            if dist.get(pos, 0) < min_dist:
                return False
            if pos in excl or pos in others:
                return False
            if room is not None and pos not in room:
                return False
            return True

        candidates = [p for p in dist if _valid(p, 8)]
        if not candidates:
            candidates = [p for p in dist if _valid(p, 4)]
        if not candidates and room is not None:
            candidates = [p for p in room
                          if not self.walls[p[0]][p[1]] and p not in others]
        if candidates:
            enemy.col, enemy.row = random.choice(candidates)

    def _end_game(self, won):
        self._final_score = self.score * max(1, self.lives)
        self._final_level = self.level
        self.sounds.stop_music()
        self.sounds.play('level_up' if won else 'game_over')
        if won:
            self.sounds.start_music('win')
        self.state = WIN if won else GAME_OVER

    # ── Update ───────────────────────────────────────────────────────────────

    def update(self, dt):
        self._title_ms = getattr(self, '_title_ms', 0) + dt

        if self.state == TITLE:
            self._update_title_ogres(dt)

        elif self.state == LEVEL_INTRO:
            self._intro_timer -= dt
            if self._intro_timer <= 0:
                self.state = PLAYING

        elif self.state == PLAYING:
            self._update_playing(dt)

    def _update_playing(self, dt):
        if self._transition_timer > 0:
            self._transition_timer -= dt
            return

        if self._flash_timer > 0:
            self._flash_timer -= dt

        if self._shield_timer > 0:
            self._shield_timer -= dt
            if self._shield_timer <= 0:
                self._shield_timer = 0
                self.shield = False
                self.sounds.play('shield_expire')

        # Key repeat
        now = pygame.time.get_ticks()
        for key, (first, last) in list(self._key_repeat.items()):
            elapsed_first = now - first
            elapsed_last  = now - last
            if elapsed_first >= FIRST_REPEAT_MS and elapsed_last >= self.move_ms:
                self._try_move_key(key)
                self._key_repeat[key] = (first, now)

        # Enemy movement
        self._enemy_timer += dt
        if self._enemy_timer >= self.enemy_ms:
            self._enemy_timer -= self.enemy_ms
            reserved = {(e.col, e.row) for e in self.enemies}
            player_room = self._player_room() if self._is_multiroom else None

            if self.difficulty == HARD:
                dist = self._bfs_from(self.player.col, self.player.row)
            else:
                dist = None
            for enemy in self.enemies:
                reserved.discard((enemy.col, enemy.row))
                if isinstance(enemy, PatrolEnemy):
                    enemy.move_patrol(self.walls, occupied=reserved)
                elif (enemy.room_name and
                      player_room == enemy.room_name):
                    if dist is not None:
                        enemy.move_bfs(dist, occupied=reserved)
                    else:
                        enemy.move_toward(self.player.col, self.player.row,
                                          self.walls, occupied=reserved)
                else:
                    enemy.wander(self.walls, occupied=reserved)
                reserved.add((enemy.col, enemy.row))
            # Forge ogres damage adjacent player-placed walls
            for enemy in self.enemies:
                if isinstance(enemy, ForgeOgre):
                    self._forge_ogre_attack(enemy)

            if not self._is_multiroom:
                for enemy in self.enemies:
                    if (enemy.col, enemy.row) == self.treasure_pos:
                        self._relocate_treasure()
                        break

        # Treasure collection (checked before enemy collision so the player
        # can grab a treasure even if an enemy is on the same tile)
        if self._is_multiroom:
            self._collect_loot()
        else:
            if (self.player.col, self.player.row) == self.treasure_pos:
                self.score += TREASURE_POINTS.get(self.treasure_item_no, 0)
                self.sounds.play('collect')
                if self.item_no == 9:
                    self._advance_level()
                else:
                    self._spawn_treasure()

        # Collision: any enemy catches player
        for enemy in self.enemies:
            if enemy.col == self.player.col and enemy.row == self.player.row:
                self._on_caught(enemy)
                return

        # Flame jets (Act 2)
        if self._is_multiroom and self._flame_jets:
            self._flame_timer += dt
            if not self.shield:
                pc, pr = self.player.col, self.player.row
                for jet in self._flame_jets:
                    tiles = jet['tiles']
                    for idx, (fc, fr) in enumerate(tiles):
                        if fc == pc and fr == pr:
                            intensity = _flame_tile_intensity(
                                jet, idx, self._flame_timer)
                            if intensity > 0.3:
                                self.sounds.play('caught')
                                self._lose_life()
                                return

        # Pressure plates (Act 2)
        self._update_pressure_plates()

        # Pickups (Act 2)
        self._collect_materials()
        self._collect_keys()

    # ── Rendering ────────────────────────────────────────────────────────────

    def render(self):
        s = self.surf

        if self.state == TITLE:
            self._render_title()
        elif self.state == DIFFICULTY:
            self._render_difficulty()
        elif self.state == STORY:
            self._render_story()
        elif self.state == LEVEL_INTRO:
            self._render_field()
            self._render_hud()
            self._render_overlay_text(f"LEVEL  {self.level}", sub="press any key")
        elif self.state == PLAYING:
            self._render_field()
            self._render_hud()
            if self._transition_timer > 0:
                self._render_transition_flash()
            elif self._flash_timer > 0:
                self._render_red_flash()
        elif self.state == PAUSED:
            self._render_field()
            self._render_hud()
            self._render_overlay_text("PAUSED", sub="[P] to resume")
        elif self.state == GAME_OVER:
            self._render_field()
            self._render_hud()
            self._render_overlay_text("GAME  OVER", sub="press any key")
        elif self.state == WIN:
            self._render_field()
            self._render_hud()
            win_msg = "THE  FORGE  IS  DEFEATED!" if self._final_level >= 20 else "YOU  WON!"
            self._render_overlay_text(win_msg, sub=f"Final score: {self._final_score}", color=YELLOW)
        elif self.state == PLAY_AGAIN:
            self._render_field()
            self._render_hud()
            self._render_overlay_text("PLAY AGAIN?", sub="[Y] yes   [N] no")
        elif self.state == INVENTORY:
            self._render_field()
            self._render_hud()
            self._render_inventory()
        elif self.state == ENTER_SCORE:
            self._render_enter_score()
        elif self.state == SHOW_SCORES:
            self._render_scores()

    # ── Field rendering ───────────────────────────────────────────────────────

    def _render_field(self):
        sp = self.sprites

        _WALL_SPRITE = {WALL_STONE: 'wall', WALL_WOODEN: 'wall_wooden',
                        WALL_REINFORCED: 'wall_reinforced'}

        for c in range(COLS):
            for r in range(ROWS):
                x, y = c * TILE, r * TILE
                if self.walls[c][r]:
                    if self._is_border(c, r):
                        self.surf.blit(sp['border_wall'], (x, y))
                    elif (c, r) in self._placed_walls:
                        self.surf.blit(sp['placed_wall'], (x, y))
                        hits = self._wall_hits.get((c, r), 0)
                        if hits:
                            self.surf.blit(sp[f'crack{hits}'], (x, y))
                    else:
                        wt = self._level_walls.get((c, r), WALL_STONE)
                        self.surf.blit(sp[_WALL_SPRITE.get(wt, 'wall')], (x, y))
                        if wt != WALL_REINFORCED:
                            hits = self._wall_hits.get((c, r), 0)
                            if hits:
                                self.surf.blit(sp[f'crack{hits}'], (x, y))
                else:
                    if (c, r) in getattr(self, '_dead_squares', set()):
                        self.surf.blit(sp['dead_floor'], (x, y))
                    else:
                        self.surf.blit(sp['floor'], (x, y))

        # Level entrance sprite at the start-grid entry border tile
        if 'entrance' in self._current_room_data:
            ec, er = self._current_room_data['entrance']
            self.surf.blit(sp['level_entrance'], (ec * TILE, er * TILE))

        # Staircase sprite at grid border exits
        if self._is_multiroom:
            for exit_key in self._current_room_data.get('exits', {}):
                side, pos_str = exit_key.rsplit('_', 1)
                pos = int(pos_str)
                if side == 'right':    sc, sr = COLS - 1, pos
                elif side == 'left':   sc, sr = 0,        pos
                elif side == 'bottom': sc, sr = pos, ROWS - 1
                else:                  sc, sr = pos, 0
                self.surf.blit(sp['staircase'], (sc * TILE, sr * TILE))

        # Treasure
        if self._is_multiroom:
            rk = self._current_room
            for tc, tr, item_no in self._room_treasures.get(rk, []):
                if item_no in sp:
                    self.surf.blit(sp[item_no], (tc * TILE, tr * TILE))
        elif self.treasure_pos:
            tc, tr = self.treasure_pos
            tz = self.treasure_item_no
            if tz in sp:
                self.surf.blit(sp[tz], (tc * TILE, tr * TILE))

        # Act 2 overlays: plates, gates, blocks, doors, keys, materials
        if self._is_multiroom:
            _MAT_SPRITE = {'rocks': 'mat_rocks', 'planks': 'mat_planks',
                           'metal': 'mat_metal', 'crystal': 'mat_crystal'}
            for pc, pr, _gid in self._room_plates.get(rk, []):
                self.surf.blit(sp['pressure_plate'], (pc * TILE, pr * TILE))
            for gate_id, (gc, gr) in self._room_gates.get(rk, {}).items():
                o = self._door_orient(gc, gr)
                base = 'gate_open' if gate_id in self._gate_open else 'gate_closed'
                self.surf.blit(sp[f'{base}_{o}'], (gc * TILE, gr * TILE))
            for bc, br in self._room_blocks.get(rk, []):
                self.surf.blit(sp['pushable_block'], (bc * TILE, br * TILE))
            # Detect water orientation: if any neighbor up/down is also
            # water, the stream is vertical; otherwise horizontal.
            for wc, wr in self._water_tiles:
                vert = ((wc, wr - 1) in self._water_tiles or
                        (wc, wr + 1) in self._water_tiles)
                o = 'v' if vert else 'h'
                if (wc, wr) in self._bridged_tiles:
                    self.surf.blit(sp[f'bridge_{o}'], (wc * TILE, wr * TILE))
                else:
                    self.surf.blit(sp[f'water_{o}'], (wc * TILE, wr * TILE))
            _DIR_SUFFIX = {(1,0): 'r', (-1,0): 'l', (0,1): 'd', (0,-1): 'u'}
            for jet in self._flame_jets:
                dc, dr = jet.get('dir', (1, 0))
                d = _DIR_SUFFIX.get((dc, dr), 'r')
                sc, sr = jet.get('source', jet['tiles'][0])
                src_key = f'flame_source_{d}'
                if src_key in sp:
                    self.surf.blit(sp[src_key], (sc * TILE, sr * TILE))
                tile_set = jet['_tile_set']
                source = jet.get('source')
                for idx, (fc, fr) in enumerate(jet['tiles']):
                    intensity = _flame_tile_intensity(
                        jet, idx, self._flame_timer)
                    connected = set()
                    nozzle = set()
                    for side, (dc, dr) in (('l', (-1, 0)), ('r', (1, 0)),
                                            ('u', (0, -1)), ('d', (0, 1))):
                        adj = (fc + dc, fr + dr)
                        if adj in tile_set:
                            connected.add(side)
                        elif adj == source:
                            connected.add(side)
                            nozzle.add(side)
                    draw_flame_at(self.surf, fc * TILE, fr * TILE,
                                  intensity, connected, nozzle_sides=nozzle)
            for dc, dr, door_color in self._room_doors.get(rk, []):
                o = self._door_orient(dc, dr)
                dkey = f'door_{door_color}_{o}'
                if dkey in sp:
                    self.surf.blit(sp[dkey], (dc * TILE, dr * TILE))
            for ok, dc, dr, _color in self._opened_doors:
                if ok != rk:
                    continue
                o = self._door_orient(dc, dr)
                self.surf.blit(sp[f'door_open_{o}'], (dc * TILE, dr * TILE))
            for kc, kr, key_color in self._room_keys.get(rk, []):
                kkey = f'key_{key_color}'
                if kkey in sp:
                    self.surf.blit(sp[kkey], (kc * TILE, kr * TILE))
            for mc, mr, mat_type in self._room_materials.get(rk, []):
                skey = _MAT_SPRITE.get(mat_type)
                if skey and skey in sp:
                    self.surf.blit(sp[skey], (mc * TILE, mr * TILE))

        # Enemies / boss
        if self.level == ACT1_BOSS_LEVEL:
            phase = (pygame.time.get_ticks() // 120) % 4
            for enemy in self.enemies:
                self.surf.blit(sp[f'boss_{phase}'], (enemy.col * TILE, enemy.row * TILE))
        else:
            ekey = f'enemy_{min((self.level - 1) // 3 + 1, 3)}'
            for enemy in self.enemies:
                if isinstance(enemy, PatrolEnemy):
                    self.surf.blit(sp['patrol_guard'], (enemy.col * TILE, enemy.row * TILE))
                elif isinstance(enemy, ForgeOgre):
                    self.surf.blit(sp['forge_ogre'], (enemy.col * TILE, enemy.row * TILE))
                else:
                    self.surf.blit(sp[ekey], (enemy.col * TILE, enemy.row * TILE))

        # Player
        self.surf.blit(sp['player'],
                       (self.player.col * TILE, self.player.row * TILE))
        if self.shield:
            self.surf.blit(sp['shield'],
                           (self.player.col * TILE, self.player.row * TILE))

    def _render_hud(self):
        hud_y = ROWS * TILE
        pygame.draw.rect(self.surf, HUD_BG, (0, hud_y, LOGICAL_W, STATUS_H))

        if self._place_credits > 0:
            wall_color = LTGREEN
        elif self._breaks_toward_credit > 0:
            wall_color = YELLOW
        else:
            wall_color = GRAY

        # Pad SEEK name to the longest treasure name so the slot never shifts.
        max_name = max(len(v) for v in TREASURE_NAMES.values())
        item_name = TREASURE_NAMES.get(self.treasure_item_no, "")

        # SHIELD: always present; invisible (HUD_BG) when inactive so layout never shifts.
        # Fixed width "SHIELD XX" — right-aligned 2-digit number, no unit suffix.
        if self.shield:
            shield_txt = f"SHIELD {max(1, (self._shield_timer + 999) // 1000):>2}"
            shield_col = LTBLUE
        else:
            shield_txt = "SHIELD   "   # same 9-char width, rendered invisible
            shield_col = HUD_BG

        # WALLS: fixed width with optional "." when half a credit has been mined.
        walls_dot = '.' if self._breaks_toward_credit > 0 else ' '

        elems = [
            (f"SCORE {self.score:>7}",              HUD_TEXT),
            (f"LEVEL {self.level:>2}",               HUD_TEXT),
            (f"LIVES {self.lives:>2}",               HUD_LIFE),
        ]
        if self._is_multiroom:
            elems.append((f"LOOT {self._loot_collected:>2}/{self._loot_total}", GOLD))
        else:
            elems.append((f"SEEK: {item_name:<{max_name}}", HUD_TEXT))
        if self.level == ACT1_BOSS_LEVEL:
            elems.append(("BOSS", MAGENTA))
        elif self.difficulty == HARD:
            elems.append(("HARD", RED))
        elems.append((shield_txt, shield_col))
        elems.append((f"WALLS {self._place_credits:>2}{walls_dot}", wall_color))

        imgs = [self.font_hud.render(txt, True, col) for txt, col in elems]
        total_w = sum(img.get_width() for img in imgs)
        margin = 10
        gap = (LOGICAL_W - 2 * margin - total_w) / max(len(imgs) - 1, 1)
        cy = hud_y + (STATUS_H - imgs[0].get_height()) // 2
        x = float(margin)
        for img in imgs:
            self.surf.blit(img, (round(x), cy))
            x += img.get_width() + gap

    # ── Overlays ─────────────────────────────────────────────────────────────

    def _render_overlay_text(self, text, sub="", color=WHITE):
        overlay = pygame.Surface((LOGICAL_W, ROWS * TILE), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.surf.blit(overlay, (0, 0))

        box_w, box_h = 420, 90 if sub else 60
        bx = (LOGICAL_W - box_w) // 2
        by = (ROWS * TILE - box_h) // 2
        pygame.draw.rect(self.surf, (30, 30, 50), (bx, by, box_w, box_h), border_radius=8)
        pygame.draw.rect(self.surf, color, (bx, by, box_w, box_h), 2, border_radius=8)

        img = self.font_big.render(text, True, color)
        self.surf.blit(img, (LOGICAL_W // 2 - img.get_width() // 2, by + 10))
        if sub:
            simg = self.font_small.render(sub, True, GRAY)
            self.surf.blit(simg, (LOGICAL_W // 2 - simg.get_width() // 2, by + 58))

    def _render_inventory(self):
        """Draw the inventory/crafting overlay — icon-driven for kids."""
        overlay = pygame.Surface((LOGICAL_W, ROWS * TILE), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.surf.blit(overlay, (0, 0))

        sp = self.sprites
        inv = self.inventory
        ICO = 20  # icon size

        # ── Title ─────────────────────────────────────────────────────────
        title = self.font_big.render("INVENTORY", True, GOLD)
        self.surf.blit(title, (LOGICAL_W // 2 - title.get_width() // 2, 14))

        # ── Materials (left panel, vertical list) ─────────────────────────
        ROW = 26  # row height for vertical lists
        panel_x, panel_y = 30, 60
        count_x = panel_x + ICO + 6       # "×N" column
        name_x  = panel_x + ICO + 40      # name column

        header = self.font_small.render("Materials", True, GRAY)
        self.surf.blit(header, (panel_x, panel_y))
        panel_y += 22

        for mat_type, name in MATERIAL_NAMES.items():
            count = inv.materials.get(mat_type, 0)
            col = WHITE if count > 0 else DKGRAY

            icon_key = MATERIAL_ICONS.get(mat_type)
            if icon_key and icon_key in sp:
                self.surf.blit(sp[icon_key], (panel_x, panel_y))

            txt = self.font_small.render(f"×{count}", True, col)
            self.surf.blit(txt, (count_x, panel_y + 2))
            nm = self.font_small.render(name, True, col)
            self.surf.blit(nm, (name_x, panel_y + 2))
            panel_y += ROW

        # ── Tools (below materials, vertical list) ────────────────────────
        panel_y += 8
        header = self.font_small.render("Tools", True, GRAY)
        self.surf.blit(header, (panel_x, panel_y))
        panel_y += 22

        for tool_type, name in TOOL_NAMES.items():
            has = tool_type in inv.tools
            icon_key = TOOL_ICONS.get(tool_type)
            if icon_key and icon_key in sp:
                icon = sp[icon_key]
                if not has:
                    dark = icon.copy()
                    dark.fill((60, 60, 60, 180), special_flags=pygame.BLEND_RGBA_MULT)
                    self.surf.blit(dark, (panel_x, panel_y))
                else:
                    self.surf.blit(icon, (panel_x, panel_y))
            col = LTGREEN if has else DKGRAY
            txt = self.font_small.render(name, True, col)
            self.surf.blit(txt, (name_x, panel_y + 2))
            panel_y += ROW

        # ── Keys (below tools) ───────────────────────────────────────────
        any_keys = any(v > 0 for v in inv.keys.values())
        if any_keys:
            panel_y += 8
            header = self.font_small.render("Keys", True, GRAY)
            self.surf.blit(header, (panel_x, panel_y))
            panel_y += 22
            for key_color, name in KEY_NAMES.items():
                count = inv.keys.get(key_color, 0)
                if count <= 0:
                    continue
                icon_key = f'icon_key_{key_color}'
                if icon_key in sp:
                    self.surf.blit(sp[icon_key], (panel_x, panel_y))
                col = KEY_COLORS.get(key_color, WHITE)
                txt = self.font_small.render(f"×{count}", True, col)
                self.surf.blit(txt, (count_x, panel_y + 2))
                nm = self.font_small.render(name, True, col)
                self.surf.blit(nm, (name_x, panel_y + 2))
                panel_y += ROW

        # ── Recipes (right panel) ─────────────────────────────────────────
        # Each recipe: [result icon] name  =  [ingredient icons] × count + ...
        rx = 360
        ry = 60
        header = self.font_small.render("Recipes", True, GRAY)
        self.surf.blit(header, (rx, ry))
        ry += 24

        ROW_H = 36
        for i, (result, ingredients, tool) in enumerate(RECIPES):
            is_selected = (i == self._inv_cursor)
            can = inv.can_craft(i)
            locked = tool and tool not in inv.tools
            y = ry + i * ROW_H

            # Selection highlight
            if is_selected:
                pygame.draw.rect(self.surf, (40, 40, 70),
                                 (rx - 4, y - 2, LOGICAL_W - rx - 10, ROW_H - 2),
                                 border_radius=4)
                pygame.draw.rect(self.surf, GOLD if can else GRAY,
                                 (rx - 4, y - 2, LOGICAL_W - rx - 10, ROW_H - 2),
                                 1, border_radius=4)

            # Active item marker
            if inv.active_item == result:
                pygame.draw.polygon(self.surf, GOLD,
                                    [(rx - 14, y + 4), (rx - 6, y + 10),
                                     (rx - 14, y + 16)])

            # Result icon
            res_icon = CRAFT_ICONS.get(result)
            if res_icon and res_icon in sp:
                icon = sp[res_icon]
                if locked:
                    icon = icon.copy()
                    icon.fill((60, 60, 60, 180), special_flags=pygame.BLEND_RGBA_MULT)
                self.surf.blit(icon, (rx, y))

            # Result name + count
            name = CRAFT_NAMES.get(result, result)
            crafted_n = inv.crafted.get(result, 0)
            if crafted_n > 0:
                name += f" ×{crafted_n}"
            col = LTGREEN if can else (DKGRAY if locked else GRAY)
            txt = self.font_small.render(name, True, col)
            self.surf.blit(txt, (rx + ICO + 4, y + 2))

            # "=" separator
            eq = self.font_small.render("=", True, DKGRAY)
            eq_x = rx + ICO + 4 + txt.get_width() + 8
            self.surf.blit(eq, (eq_x, y + 2))

            # Ingredient icons with multipliers
            ix = eq_x + eq.get_width() + 8
            first = True
            for mat, count in ingredients.items():
                if not first:
                    plus = self.font_small.render("+", True, DKGRAY)
                    self.surf.blit(plus, (ix, y + 2))
                    ix += plus.get_width() + 4
                first = False

                mat_icon = MATERIAL_ICONS.get(mat)
                if mat_icon and mat_icon in sp:
                    self.surf.blit(sp[mat_icon], (ix, y))
                ix += ICO + 2

                have = inv.materials.get(mat, 0)
                enough = have >= count
                cnt_col = LTGREEN if enough else RED
                cnt = self.font_small.render(f"×{count}", True, cnt_col)
                self.surf.blit(cnt, (ix, y + 2))
                ix += cnt.get_width() + 6

            # Lock icon for missing tool
            if locked:
                tool_icon = TOOL_ICONS.get(tool)
                if tool_icon and tool_icon in sp:
                    dark_tool = sp[tool_icon].copy()
                    dark_tool.fill((80, 80, 80, 180), special_flags=pygame.BLEND_RGBA_MULT)
                    self.surf.blit(dark_tool, (ix, y))
                    ix += ICO + 4
                need_txt = self.font_small.render(f"need {TOOL_NAMES.get(tool, '?')}",
                                                   True, DKGRAY)
                self.surf.blit(need_txt, (ix, y + 2))

        # ── Footer ────────────────────────────────────────────────────────
        fy = ROWS * TILE - 34
        hints = [
            ("[Tab]", "close"),
            ("[Up/Dn]", "navigate"),
            ("[Enter]", "craft"),
            ("[Space]", "select"),
        ]
        fx = 200
        for key, desc in hints:
            ki = self.font_small.render(key, True, HUD_KEY)
            di = self.font_small.render(f" {desc}", True, DKGRAY)
            self.surf.blit(ki, (fx, fy))
            self.surf.blit(di, (fx + ki.get_width(), fy))
            fx += ki.get_width() + di.get_width() + 16

    def _render_red_flash(self):
        alpha = min(180, int(self._flash_timer * 0.3))
        flash = pygame.Surface((LOGICAL_W, ROWS * TILE), pygame.SRCALPHA)
        flash.fill((220, 20, 20, alpha))
        self.surf.blit(flash, (0, 0))

    def _render_transition_flash(self):
        alpha = min(220, int(self._transition_timer * 0.7))
        flash = pygame.Surface((LOGICAL_W, ROWS * TILE), pygame.SRCALPHA)
        flash.fill((255, 255, 255, alpha))
        self.surf.blit(flash, (0, 0))

    # ── Title screen ─────────────────────────────────────────────────────────

    def _render_title(self):
        self.surf.fill(BLACK)
        t = self._title_ms / 1000.0
        sp = self.sprites

        # Corner ogres (drawn first, behind all text)
        phase = (pygame.time.get_ticks() // 120) % 4
        ogre_keys = ['enemy_1', 'enemy_2', 'enemy_3', f'boss_{phase}']
        for i, ogre in enumerate(self._title_ogres):
            self.surf.blit(sp[ogre_keys[i]], (int(ogre[0]), int(ogre[1])))

        # Animated coloured title letters
        title = "UGLYCRAFT"
        colors = [RED, ORANGE, YELLOW, LTGREEN, CYAN, LTBLUE, MAGENTA, WHITE, GOLD]
        base_y = 120

        # Measure actual glyph dimensions from the font
        gw     = self.font_title.size(title[0])[0]   # rendered width of one char
        font_h = self.font_title.get_height()

        # Distribute glyph centres evenly: step between consecutive centres,
        # whole arrangement centred on screen.
        n    = len(title)
        step = 54   # centre-to-centre spacing (px)
        first_cx = LOGICAL_W // 2 - (n - 1) * step // 2

        wave_ys = [int(12 * abs(((t * 2 + i * 0.4) % 2) - 1)) for i in range(n)]

        for i, ch in enumerate(title):
            color = colors[i % len(colors)]
            img   = self.font_title.render(ch, True, color)
            self.surf.blit(img, (first_cx + i * step - gw // 2, base_y - wave_ys[i]))

        # Items 1–9 centred on their letter's glyph centre, waving with it
        for i in range(9):
            self.surf.blit(sp[i + 1],
                           (first_cx + i * step - TILE // 2,
                            base_y - wave_ys[i] + font_h + 4))

        # Crown centred on the "C" glyph, above it, riding its wave
        c_idx = title.index('C')
        self.surf.blit(sp[10],
                       (first_cx + c_idx * step - TILE // 2,
                        base_y - wave_ys[c_idx] - TILE - 4))

        # Subtitle and instructions sit below the item row (wave_y=0 is the lowest point)
        item_row_bottom = base_y + font_h + 4 + TILE
        sub_y   = item_row_bottom + 20
        instr_y = sub_y + 50

        sub = self.font_med.render("Inspired by UGLI (1996)", True, GRAY)
        self.surf.blit(sub, (LOGICAL_W // 2 - sub.get_width() // 2, sub_y))

        # Instructions — measure first, then centre the two-column block
        lines = [
            ("Arrow keys", "move  (bump a wall 3× to mine it)"),
            ("Space",      "place wall  (costs 1 credit)"),
            ("Enter",      "buy shield  (250 pts, lasts 10 s)"),
            ("P",          "pause"),
        ]
        gap = 14
        rendered = [(self.font_small.render(f"[{k}]", True, HUD_KEY),
                     self.font_small.render(d, True, WHITE)) for k, d in lines]
        max_key_w  = max(ki.get_width() for ki, _ in rendered)
        max_desc_w = max(di.get_width() for _, di in rendered)
        block_x = (LOGICAL_W - max_key_w - gap - max_desc_w) // 2
        for i, (ki, di) in enumerate(rendered):
            ky = instr_y + i * 26
            self.surf.blit(ki, (block_x + max_key_w - ki.get_width(), ky))
            self.surf.blit(di, (block_x + max_key_w + gap, ky))

        # Blink prompt
        if int(t * 2) % 2 == 0:
            prompt = self.font_med.render("PRESS ENTER TO PLAY", True, YELLOW)
            self.surf.blit(prompt, (LOGICAL_W // 2 - prompt.get_width() // 2, 460))

        footer = self.font_small.render("[H] High scores   [S] History   [Q] Quit", True, GRAY)
        self.surf.blit(footer, (LOGICAL_W // 2 - footer.get_width() // 2, 510))

    # ── Difficulty selection screen ───────────────────────────────────────────

    def _render_difficulty(self):
        self.surf.fill(BLACK)

        title = self.font_big.render("SELECT  DIFFICULTY", True, WHITE)
        self.surf.blit(title, (LOGICAL_W // 2 - title.get_width() // 2, 140))

        cx = LOGICAL_W // 2
        for key, label, desc, color, y in (
            ("E", "EASY", "For a relaxed game",   LTGREEN, 250),
            ("H", "HARD", "For a real challenge",  RED,     340),
        ):
            # Box
            bw, bh = 520, 70
            bx = cx - bw // 2
            pygame.draw.rect(self.surf, (20, 20, 30), (bx, y, bw, bh), border_radius=6)
            pygame.draw.rect(self.surf, color,         (bx, y, bw, bh), 2,  border_radius=6)

            key_img  = self.font_big.render(f"[{key}]", True, color)
            name_img = self.font_big.render(label, True, WHITE)
            desc_img = self.font_small.render(desc, True, GRAY)

            self.surf.blit(key_img,  (bx + 16, y + 10))
            self.surf.blit(name_img, (bx + 80, y + 10))
            self.surf.blit(desc_img, (bx + 80, y + 46))

        hint = self.font_small.render("[Esc] back", True, DKGRAY)
        self.surf.blit(hint, (cx - hint.get_width() // 2, 450))

    # ── Story screen ─────────────────────────────────────────────────────────

    def _load_history_text(self):
        base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, 'translations', 'history_en.txt')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except OSError:
            return 'File not found.'

    def _wrap_text(self, text, font, max_width):
        lines = []
        for paragraph in text.split('\n\n'):
            words = paragraph.split()
            if not words:
                lines.append('')
                continue
            current = words[0]
            for word in words[1:]:
                test = current + ' ' + word
                if font.size(test)[0] <= max_width:
                    current = test
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
            lines.append('')
        if lines and lines[-1] == '':
            lines.pop()
        return lines

    def _render_story(self):
        self.surf.fill((10, 5, 20))
        title = self.font_big.render("THE  HISTORY  OF  UGLI", True, YELLOW)
        self.surf.blit(title, (LOGICAL_W // 2 - title.get_width() // 2, 40))
        text = self._load_history_text()
        lines = self._wrap_text(text, self.font_med, LOGICAL_W - 80)
        y = 110
        for line in lines:
            if line:
                img = self.font_med.render(line, True, WHITE)
                self.surf.blit(img, (40, y))
            y += 28
        prompt = self.font_small.render("Press any key", True, GRAY)
        self.surf.blit(prompt, (LOGICAL_W // 2 - prompt.get_width() // 2, 500))

    # ── Score entry ───────────────────────────────────────────────────────────

    def _render_enter_score(self):
        self.surf.fill(BLACK)
        lines = [
            ("HIGH SCORE!", YELLOW),
            (f"Final score: {self._final_score}", WHITE),
            ("Enter your name:", GRAY),
        ]
        for i, (txt, col) in enumerate(lines):
            img = self.font_big.render(txt, True, col)
            self.surf.blit(img, (LOGICAL_W // 2 - img.get_width() // 2, 160 + i * 60))

        # Text input box
        bw, bh = 400, 40
        bx = (LOGICAL_W - bw) // 2
        by = 360
        pygame.draw.rect(self.surf, DKGRAY, (bx, by, bw, bh), border_radius=4)
        pygame.draw.rect(self.surf, WHITE,  (bx, by, bw, bh), 2, border_radius=4)
        cursor = "|" if int(pygame.time.get_ticks() / 500) % 2 == 0 else ""
        name_img = self.font_med.render(self._name_input + cursor, True, WHITE)
        self.surf.blit(name_img, (bx + 10, by + 8))

        hint = self.font_small.render("[Enter] to confirm", True, GRAY)
        self.surf.blit(hint, (LOGICAL_W // 2 - hint.get_width() // 2, 420))

    # ── High score table ──────────────────────────────────────────────────────

    def _render_scores(self):
        self.surf.fill(BLACK)
        title = self.font_big.render("HIGH  SCORES", True, YELLOW)
        self.surf.blit(title, (LOGICAL_W // 2 - title.get_width() // 2, 50))

        scores = load_scores()
        if not scores:
            msg = self.font_med.render("No scores yet.", True, GRAY)
            self.surf.blit(msg, (LOGICAL_W // 2 - msg.get_width() // 2, 200))
        else:
            for i, (name, sc, lvl) in enumerate(scores):
                color = GOLD if i == 0 else WHITE
                line  = f"{i+1:>2}.  {name:<16}  {sc:>8}  Lv{lvl:>2}"
                img   = self.font_med.render(line, True, color)
                self.surf.blit(img, (LOGICAL_W // 2 - img.get_width() // 2, 120 + i * 34))

        hint = self.font_small.render("Press any key to continue", True, GRAY)
        self.surf.blit(hint, (LOGICAL_W // 2 - hint.get_width() // 2, 500))

    # ── Transition into score entry if applicable ─────────────────────────────

    def try_enter_score(self):
        """Call after WIN or GAME_OVER state is acknowledged."""
        if self._debug:
            self.state = PLAY_AGAIN
            return
        fs = getattr(self, '_final_score', 0)
        if qualifies(fs):
            self._name_input = ""
            self.state = ENTER_SCORE
        else:
            self._scores_return_to = PLAY_AGAIN
            self.state = SHOW_SCORES
