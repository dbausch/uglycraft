"""World: all gameplay state and rules, pygame-free (spec 0045, Stage 1).

The presentation layer (game.Game) constructs a World, translates input
into its methods, ticks it once per frame with update(dt), and drains the
typed event stream.  Events map 1:1 onto the sound/music/flash/state
triggers that used to be inline calls inside the game logic — Game
dispatches them in emission order, so the observable sequence is
byte-identical to the pre-split code (proven by the spec-0044 goldens).

Event kinds (args in parentheses):

  moved, bumped, wall_broken, door_opened, bridge_built, credit_earned,
  wall_placed, collected, shield_bought, shield_expired, caught,
  caught_shielded, item_relocated, boss_appeared      — sound triggers
  flash(ms)                                           — red damage flash
  level_advanced(n)                                   — level-up fanfare
  level_started(n)                                    — input/timer reset + music
  level_intro                                         — enter LEVEL_INTRO state
  game_over(won)                                      — enter WIN / GAME_OVER

This module (and everything it imports) must never import pygame — the
key ids passed to try_move()/key_released() are opaque ints.
"""
import random
from collections import deque
from constants import *
from levels import (TOTAL_LEVELS, get_level, new_game_levels,
                    regenerate_level)
from entities import Player, Enemy, PatrolEnemy, ForgeOgre
from rooms import RoomState, find_exit
from crafting import Inventory, CRAFT_STONE_WALL, CRAFT_BRIDGE
from cells import BARRIER_BUMP, Barrier, RoomCells, build_room_cells

NUM_LEVELS  = TOTAL_LEVELS
ACT1_BOSS_LEVEL = 10


def is_border(col, row):
    return col == 0 or col == COLS - 1 or row == 0 or row == ROWS - 1


def _as_multiroom(data):
    """Normalise a level dict to the multiroom shape (spec 0046).

    Act 1 dicts (no 'rooms') become one-room multiroom levels.  The single
    room is keyed None — the 0044 golden traces record _current_room every
    tick, and Act 1 has always reported None.  Only 'walls' and
    'enemy_starts' go into the room dict; every other room key is read
    with .get(..., default) downstream, so the empty defaults apply.
    The wrapper is runtime-only: levels.py's authoring format, and the
    direct get_level() reads of 'player_start'/'crown_pos', are untouched.
    """
    if 'rooms' in data:
        return data
    return {
        'rooms': {None: {'walls': data['walls'],
                         'enemy_starts': data['enemy_starts']}},
        'start_room': None,
        'player_start': data['player_start'],
        'spawn_mode': 'sequential',
        'crafting': False,
    }


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


class World:
    """All gameplay state and rules for one game (was Game._full_reset…)."""

    def __init__(self, difficulty, progress=None):
        self.difficulty = difficulty
        self._progress = progress   # loading callback for get_level (opaque)
        self._events = []
        new_game_levels()
        self.score        = 0
        self.lives        = STARTING_LIVES
        self.level        = 0
        self.item_no         = 0
        self.shield       = False
        self._shield_timer = 0
        self.move_ms      = BASE_MOVE_MS
        self.enemy_ms     = BASE_ENEMY_MS  # overridden to BOSS_MOVE_MS on level 10
        self.cells = RoomCells()   # empty until the first room is entered
        self._breaks_toward_credit    = 0    # leftover breaks toward next credit
        self._place_credits = 0   # available wall placements
        self._bump_consumed = set()  # direction keys that must be released before next bump
        self.inventory = Inventory()
        self.start_level(1)

    # ── Event stream ──────────────────────────────────────────────────────────

    def _emit(self, kind, *args):
        self._events.append((kind,) + args)

    def drain_events(self):
        """Return and clear the events emitted since the last call."""
        events = self._events
        self._events = []
        return events

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
                        and not self.blocked(nc, nr)):
                    dist[(nc, nr)] = dist[(c, r)] + 1
                    q.append((nc, nr))
        return dist

    # ── Passability (spec 0047) ───────────────────────────────────────────────

    def blocked(self, c, r):
        """True iff (c, r) cannot be walked on: out of bounds, a blocking
        barrier, unbridged water, or a pushable block.  The query replaces
        the cached walls grid — nothing to rebuild, nothing to forget."""
        if not (0 <= c < COLS and 0 <= r < ROWS):
            return True
        if self.cells.blocked(c, r, self._channels):
            return True
        if (c, r) in self._room_blocks.get(self._current_room, []):
            return True
        return False

    def channel(self, name):
        """Signal-channel query (spec 0050 Q1, kb review R2): receivers
        (gate barriers — later levers, lasers, pistons) ask only this.
        The table is latched once per tick at the plate pass, so state
        changes become visible exactly when the old _gate_open did."""
        return name in self._channels

    def _register_bump(self, key, col, row):
        """Called when the player walks into wall (col, row) via direction key."""
        if key in self._bump_consumed:
            return  # key not released since last hit — ignore
        barrier = self.cells.barrier(col, row)
        if barrier is None:
            # No fixture: unbridged water (a bridge attempt) or a pushable
            # block (inert; the push already failed before we got here).
            self._try_auto_bridge(col, row)
            return
        action = BARRIER_BUMP[barrier.kind]
        if action == 'key':
            self._try_auto_open_door(col, row)
            return
        if action is None:
            return  # border / reinforced / gate: inert
        # breakable: `action` is the hits threshold
        self._bump_consumed.add(key)
        hits = barrier.hits + 1
        if hits >= action:
            self._break_wall(col, row)
        else:
            barrier.hits = hits
            self._emit('bumped')

    def _break_wall(self, col, row):
        self.cells.remove_barrier((col, row))
        self._emit('wall_broken')
        self._breaks_toward_credit += 1
        if self._breaks_toward_credit >= BREAKS_PER_CREDIT:
            self._breaks_toward_credit -= BREAKS_PER_CREDIT
            self._place_credits += 1
            self._emit('credit_earned')

    # ── Level setup ───────────────────────────────────────────────────────────

    def start_level(self, level_num):
        self.level = level_num
        self.item_no  = 0
        data = _as_multiroom(get_level(level_num, progress=self._progress))
        # Per-level rules (spec 0046): generated dicts carry neither key
        # and get the Act 2 defaults; the Act 1 wrapper sets both.
        self.spawn_mode = data.get('spawn_mode', 'preplaced')
        self.crafting   = data.get('crafting', True)

        # Refund one credit per placed wall being cleared (placed walls in
        # rooms other than the current one are not refunded — unchanged
        # since the pre-0047 per-room _placed_walls had the same scope)
        self._place_credits += sum(1 for _ in self.cells.barriers('placed'))
        self._bump_consumed.clear()

        self._room_states = {}
        self._level_data = data
        self._transition_timer = 0

        self._current_room = data['start_room']
        pc, pr = data['player_start']
        self.player = Player(pc, pr)
        # Pre-placed treasures and materials: gather from all rooms
        self._loot_total = 0
        self._loot_collected = 0
        self._room_blocks = {}
        self._room_plates = {}
        self._channels = set()   # latched high channel names (spec 0050)
        for rkey, rdata in data['rooms'].items():
            self._loot_total += len(rdata.get('treasures', []))
            self._room_blocks[rkey] = list(rdata.get('pushable_blocks', []))
            self._room_plates[rkey] = list(rdata.get('pressure_plates', []))
        self.treasure_pos = None
        self._opened_doors = set()
        # Water rooms already made accessible by a bridge.  One bridge per
        # water room (spec 0029 W2): once a room is reachable, no further
        # bridge to it can be built.  Replaces the old per-grid bridge cap.
        self._bridged_water_rooms = set()
        self._tile_owner = {}
        self._room_blocks_initial = {
            rk: list(self._room_blocks[rk])
            for rk in self._room_blocks}
        self._enter_room(self._current_room)

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
        if self.spawn_mode == 'sequential':
            self._spawn_treasure()
        self._move_timer   = 0
        self._enemy_timer  = 0
        self._emit('level_started', level_num)
        if level_num == ACT1_BOSS_LEVEL:
            self._emit('boss_appeared')

    # ── Multi-room support ────────────────────────────────────────────────────

    def _enter_room(self, room_key):
        """Load a room, restoring saved state if the player has visited before."""
        room_data = self._level_data['rooms'][room_key]
        self._current_room = room_key
        self._current_room_data = room_data

        fresh = room_key not in self._room_states
        if not fresh:
            st = self._room_states[room_key]
            self.cells = st.cells
            self.enemies = st.enemies
            self._room_blocks[room_key] = st.blocks
        else:
            self.cells = build_room_cells(room_data)
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
        self._dead_squares = set(tuple(t) for t in room_data.get('dead_squares', []))
        self._flame_jets = room_data.get('flame_jets', [])
        for jet in self._flame_jets:
            jet['_tile_set'] = frozenset(tuple(t) for t in jet['tiles'])
        self._flame_timer = 0
        self._bump_consumed.clear()
        self._tag_enemies_with_rooms()
        # The stuck-block net runs only on first entry of a freshly
        # generated room (spec 0048 U5 / BL-36): restored rooms are the
        # only place player-wedged blocks exist, and a wedged block is a
        # solved-or-failed puzzle, not a broken level — death already
        # resets blocks.  With the water-aware solver (0048 U2/U3) this
        # is a should-never-fire last resort against generator bugs.
        if fresh:
            self._verify_blocks()

    def _verify_blocks(self):
        """Check blocks are pushable. Regenerate level if any are stuck."""
        rk = self._current_room
        for bc, br in self._room_blocks.get(rk, []):
            push_dirs = 0
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                pf_c, pf_r = bc - dc, br - dr
                pt_c, pt_r = bc + dc, br + dr
                pf_ok = (0 < pf_c < COLS - 1 and 0 < pf_r < ROWS - 1
                         and not self.blocked(pf_c, pf_r))
                pt_ok = (0 < pt_c < COLS - 1 and 0 < pt_r < ROWS - 1
                         and not self.blocked(pt_c, pt_r))
                if pf_ok and pt_ok:
                    push_dirs += 1
            if push_dirs == 0:
                regenerate_level(self.level)
                self.start_level(self.level)
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
            cells=self.cells,
            enemies=list(self.enemies),
            blocks=list(self._room_blocks.get(rk, [])),
        )


    def _try_room_transition(self):
        """Check if the player is on an exit tile and transition if so."""
        result = find_exit(self.player.col, self.player.row,
                           self._current_room_data)
        if result is None:
            return False
        target_room, entry_col, entry_row = result
        self._save_room_state()
        level_data = self._level_data
        self._enter_room(target_room)
        if self._level_data is not level_data:
            # Entering triggered the stuck-block regeneration: the whole
            # level was rebuilt and the player already stands at its
            # start.  Do not teleport onto the stale entry tile of a
            # level that no longer exists (spec 0048 U5 / BL-36).
            return True
        self.player.col, self.player.row = entry_col, entry_row
        self._transition_timer = 300
        self._emit('moved')
        return True

    # ── Pickups ───────────────────────────────────────────────────────────────

    def _collect_item(self, kind):
        """Collect at most ONE item of `kind` at the player's tile —
        the per-category one-per-tick semantics the goldens pin."""
        pos = (self.player.col, self.player.row)
        for item in self.cells.items(*pos):
            if item.kind != kind:
                continue
            self.cells.remove_item(pos, item)
            return item
        return None

    def _collect_loot(self):
        """Pre-placed treasure at the player's tile (Act 2)."""
        item = self._collect_item('treasure')
        if item is not None:
            self.score += TREASURE_POINTS.get(item.payload, 0)
            self._emit('collected')
            self._loot_collected += 1
            if self._loot_collected >= self._loot_total:
                self.advance_level()

    def _collect_materials(self):
        """Material pickup at the player's tile (Act 2)."""
        item = self._collect_item('material')
        if item is not None:
            self.inventory.add_material(item.payload)
            self._emit('collected')

    def _collect_keys(self):
        """Key pickup at the player's tile (Act 2)."""
        item = self._collect_item('key')
        if item is not None:
            self.inventory.add_key(item.payload)
            self._emit('collected')

    # ── Act 2 mechanics ───────────────────────────────────────────────────────

    def _latch_channels(self):
        """THE plate pass (spec 0050 Q1): recompute the channel table
        wholesale from plate occupancy.  Runs once per tick at exactly the
        position the old _update_pressure_plates mutated _gate_open, so
        gate-opening timing is unchanged.  Future emitters (levers,
        buttons) fold into this same latch."""
        room_key = self._current_room
        plates = self._room_plates.get(room_key, [])
        if not plates and not self._channels:
            return

        occupied = {(self.player.col, self.player.row)}
        occupied.update((e.col, e.row) for e in self.enemies)
        block_set = set(self._room_blocks.get(room_key, []))

        self._channels = {
            gate_id for pc, pr, gate_id in plates
            if (pc, pr) in occupied or (pc, pr) in block_set}

    def _try_push_block(self, bc, br, dcol, drow):
        """Try to push a block at (bc, br) in direction (dcol, drow)."""
        room_key = self._current_room
        blocks = self._room_blocks.get(room_key, [])
        for i, (bx, by) in enumerate(blocks):
            if bx == bc and by == br:
                nc, nr = bc + dcol, br + drow
                if (0 < nc < COLS - 1 and 0 < nr < ROWS - 1
                        and not self.blocked(nc, nr)
                        and (nc, nr) not in self._dead_squares):
                    blocks[i] = (nc, nr)
                    self._emit('bumped')
                    return True
                return False
        return False

    def _try_auto_open_door(self, col, row):
        """Open a locked door at (col, row) if the player has the key."""
        barrier = self.cells.barrier(col, row)
        if barrier is None or barrier.kind != 'door':
            return False
        if not self.inventory.has_key(barrier.colour):
            return False
        self.inventory.use_key(barrier.colour)
        self.cells.remove_barrier((col, row))
        self._opened_doors.add(
            (self._current_room, col, row, barrier.colour))
        self._emit('door_opened')
        return True

    def _try_auto_bridge(self, col, row):
        """Build a bridge on a water tile when the player bumps it.

        One bridge per water ROOM (spec 0029 W2): once a water room has been
        made accessible, no further bridge to it can be built — so a bridge can
        never be wasted.  Builds only if the player has a bridge item, the
        target room is not yet accessible, and the tile connects to open floor
        on the opposite side.
        """
        if not self.cells.is_water(col, row):
            return False
        # The water room this tile grants access to; fall back to the tile
        # itself if the mapping is missing (older level data).
        water_room = self.cells.water_room(col, row) or (col, row)
        if water_room in self._bridged_water_rooms:
            return False
        # A bridged water tile is a doorway; its flanking floor tiles are
        # landing tiles.  Never create a passage whose landing tile carries
        # a plate — the solved puzzle (block parked on it) would seal the
        # passage (spec 0049).
        for pc, pr, _gid in self._room_plates.get(self._current_room, []):
            if abs(pc - col) + abs(pr - row) == 1:
                return False
        if not self.inventory.has_item(CRAFT_BRIDGE):
            return False
        # Check that the opposite side has open floor (not wall/water)
        pc, pr = self.player.col, self.player.row
        dc, dr = col - pc, row - pr
        far_c, far_r = col + dc, row + dr
        if (0 < far_c < COLS - 1 and 0 < far_r < ROWS - 1
                and not self.blocked(far_c, far_r)):
            self.inventory.use_item(CRAFT_BRIDGE)
            self.cells.add_bridge((col, row))
            self._bridged_water_rooms.add(water_room)
            self._emit('bridge_built')
            return True
        return False

    # ── Treasure (Act 1) ──────────────────────────────────────────────────────

    def _spawn_treasure(self):
        self.item_no += 1
        if self.item_no > 9:
            self.item_no = 1
        self.treasure_item_no = 10 if (self.item_no == 9 and self.level == ACT1_BOSS_LEVEL) \
                             else self.item_no
        # Crown on the boss level spawns at a fixed position inside the vault
        if self.treasure_item_no == 10:
            data = get_level(self.level)
            if 'crown_pos' in data:
                self.treasure_pos = data['crown_pos']
                return
        open_tiles = [
            (c, r) for c in range(1, COLS - 1) for r in range(1, ROWS - 1)
            if not self.blocked(c, r)
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
            if not self.blocked(c, r)
            and (c, r) != (self.player.col, self.player.row)
            and (c, r) not in {(e.col, e.row) for e in self.enemies}
        ]
        if open_tiles:
            self.treasure_pos = random.choice(open_tiles)
            self._emit('item_relocated')

    # ── Input API (called by Game's event handlers) ───────────────────────────

    def try_move(self, dcol, drow, key):
        """Move/push/bump one step in direction (dcol, drow).

        key is an opaque id used for bump-consumption tracking (a bump
        requires releasing the key before it counts again).  Returns True
        if the player stepped onto a new tile."""
        moved = self.player.try_move(dcol, drow, self.blocked)
        if moved:
            self._bump_consumed.discard(key)
            self._emit('moved')
            return True
        tc = self.player.col + dcol
        tr = self.player.row + drow
        # Off-screen: grid transition if at an exit
        if not (0 <= tc < COLS and 0 <= tr < ROWS):
            self._try_room_transition()
            return False
        if self.blocked(tc, tr):
            if self._try_push_block(tc, tr, dcol, drow):
                self.player.col, self.player.row = tc, tr
                self._bump_consumed.discard(key)
                self._emit('moved')
                return True
            self._register_bump(key, tc, tr)
        return False

    def key_released(self, key):
        """Direction key released → its next press can bump again."""
        self._bump_consumed.discard(key)

    def place(self):
        """SPACE: place the active item (credit wall / crafted item)."""
        if self.crafting:
            self._act2_place()
        else:
            self._place_wall()

    def _place_wall(self):
        c, r = self.player.col, self.player.row
        if self._place_credits > 0 and not self.blocked(c, r):
            self._place_credits -= 1
            self.cells.set_barrier((c, r), Barrier('placed'))
            self._emit('wall_placed')

    def _act2_place(self):
        """SPACE in Act 2: place the active item."""
        c, r = self.player.col, self.player.row
        active = self.inventory.active_item
        if active == CRAFT_STONE_WALL:
            if not self.blocked(c, r):
                if self.inventory.has_item(CRAFT_STONE_WALL):
                    self.inventory.use_item(CRAFT_STONE_WALL)
                elif self.inventory.can_quick_place_wall():
                    self.inventory.quick_place_wall()
                else:
                    return
                self.cells.set_barrier((c, r), Barrier('placed'))
                self._emit('wall_placed')

    def buy_shield(self):
        if not self.shield and self.score >= SHIELD_COST_PTS:
            self.shield = True
            self._shield_timer = SHIELD_DURATION_MS
            self.score -= SHIELD_COST_PTS
            self._emit('shield_bought')

    # ── Level transitions ─────────────────────────────────────────────────────

    def advance_level(self):
        if self.level >= NUM_LEVELS:
            self._end_game(won=True)
            return
        self.lives += 1
        self._emit('level_advanced', self.level + 1)
        self.start_level(self.level + 1)
        self._emit('level_intro')

    def _on_caught(self, enemy):
        """Handle player-enemy collision: respawn the enemy far away, then apply hit."""
        self._respawn_enemy(enemy)
        if self.shield:
            self.shield = False
            self._shield_timer = 0
            self._emit('caught_shielded')
        else:
            self._emit('caught')
            self._lose_life()

    def _lose_life(self):
        self.score = max(0, self.score - LIFE_PENALTY)
        self.lives -= 1
        self._emit('flash', 600)
        if self.lives <= 0:
            self._end_game(won=False)
        else:
            data = get_level(self.level)
            self.player.col, self.player.row = data['player_start']
            self._reset_blocks()

    def _reset_blocks(self):
        """Reset all pushable blocks to their starting positions and close
        any gates that were held open by blocks on plates."""
        for rk, initial in self._room_blocks_initial.items():
            self._room_blocks[rk] = list(initial)
        # Close everything synchronously (the old _gate_open.clear()):
        # the next plate pass re-latches from the reset occupancy.
        self._channels = set()

    def _forge_ogre_attack(self, enemy):
        """Forge ogre damages an adjacent player-placed wall (2 hits to break)."""
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            tc, tr = enemy.col + dc, enemy.row + dr
            b = self.cells.barrier(tc, tr)
            if b is not None and b.kind == 'placed':
                hits = b.hits + 1
                if hits >= enemy.wall_bump_power:
                    self._break_wall(tc, tr)
                else:
                    b.hits = hits
                    self._emit('bumped')
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
                          if not self.blocked(p[0], p[1]) and p not in others]
        if candidates:
            enemy.col, enemy.row = random.choice(candidates)

    def _end_game(self, won):
        self._final_score = self.score * max(1, self.lives)
        self._final_level = self.level
        self._emit('game_over', won)

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt, input_phase=None):
        """One world tick: timers, input phase, enemies, collisions, pickups.

        input_phase is Game's key-repeat pass (input hardware scheduling
        stays in the presentation layer); it runs exactly where the old
        inline key-repeat block sat — after the shield timer, before enemy
        movement — and is skipped entirely while a room transition holds
        the world frozen."""
        if self._transition_timer > 0:
            self._transition_timer -= dt
            return

        if self._shield_timer > 0:
            self._shield_timer -= dt
            if self._shield_timer <= 0:
                self._shield_timer = 0
                self.shield = False
                self._emit('shield_expired')

        if input_phase is not None:
            input_phase()

        # Enemy movement
        self._enemy_timer += dt
        if self._enemy_timer >= self.enemy_ms:
            self._enemy_timer -= self.enemy_ms
            reserved = {(e.col, e.row) for e in self.enemies}
            player_room = self._player_room()

            if self.difficulty == HARD:
                dist = self._bfs_from(self.player.col, self.player.row)
            else:
                dist = None
            for enemy in self.enemies:
                reserved.discard((enemy.col, enemy.row))
                if isinstance(enemy, PatrolEnemy):
                    enemy.move_patrol(self.blocked, occupied=reserved)
                elif (enemy.room_name is None
                      or player_room == enemy.room_name):
                    # Unconfined enemies (Act 1: no room) always chase;
                    # room-confined enemies chase only while the player is
                    # inside their room and wander otherwise (BL-34, keeps
                    # the 9b9ed4a doorway behaviour for Act 2).
                    if dist is not None:
                        enemy.move_bfs(dist, occupied=reserved)
                    else:
                        enemy.move_toward(self.player.col, self.player.row,
                                          self.blocked, occupied=reserved)
                else:
                    enemy.wander(self.blocked, occupied=reserved)
                reserved.add((enemy.col, enemy.row))
            # Forge ogres damage adjacent player-placed walls
            for enemy in self.enemies:
                if isinstance(enemy, ForgeOgre):
                    self._forge_ogre_attack(enemy)

            if self.spawn_mode == 'sequential':
                for enemy in self.enemies:
                    if (enemy.col, enemy.row) == self.treasure_pos:
                        self._relocate_treasure()
                        break

        # Treasure collection (checked before enemy collision so the player
        # can grab a treasure even if an enemy is on the same tile)
        if self.spawn_mode == 'preplaced':
            self._collect_loot()
        else:
            if (self.player.col, self.player.row) == self.treasure_pos:
                self.score += TREASURE_POINTS.get(self.treasure_item_no, 0)
                self._emit('collected')
                if self.item_no == 9:
                    self.advance_level()
                else:
                    self._spawn_treasure()

        # Collision: any enemy catches player
        for enemy in self.enemies:
            if enemy.col == self.player.col and enemy.row == self.player.row:
                self._on_caught(enemy)
                return

        # Flame jets (Act 2)
        if self._flame_jets:
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
                                self._emit('caught')
                                self._lose_life()
                                return

        # Pressure plates (Act 2): the channel latch pass
        self._latch_channels()

        # Pickups (Act 2)
        self._collect_materials()
        self._collect_keys()
