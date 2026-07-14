"""World: all gameplay state and rules, pygame-free (spec 0045, Stage 1).

The presentation layer (game.Game) constructs a World, translates input
into its methods, ticks it once per frame with update(dt), and drains the
typed event stream.  Events map 1:1 onto the sound/music/flash/state
triggers that used to be inline calls inside the game logic — Game
dispatches them in emission order, so the observable sequence is
byte-identical to the pre-split code (proven by the spec-0044 goldens).

Event kinds (args in parentheses):

  moved, bumped, wall_broken, door_opened, bridge_built, credit_earned,
  block_placed, collected, shield_bought, shield_expired, caught,
  caught_shielded, item_relocated, boss_appeared,
  action_denied                                       — sound triggers
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
from rooms import Room, find_exit
from crafting import Inventory, KEY_NAMES, MAT_ROCKS, MAT_PLANKS
from cells import BARRIER_BUMP, Barrier, _exit_tiles

NUM_LEVELS  = TOTAL_LEVELS
ACT1_BOSS_LEVEL = 10

# Every non-border tile (spec 0066): the Act 1 single room owns all of these,
# so its enemies are confined here and can never step on a border tile —
# the open entrance included.
INTERIOR_TILES = frozenset((c, r) for c in range(1, COLS - 1)
                                  for r in range(1, ROWS - 1))


def is_border(col, row):
    return col == 0 or col == COLS - 1 or row == 0 or row == ROWS - 1


def _as_multiroom(data):
    """Normalise a level dict to the multiroom shape (spec 0046).

    Act 1 dicts (no 'rooms') become one-room multiroom levels.  The single
    room is keyed None — the 0044 golden traces record _current_room every
    tick, and Act 1 has always reported None.  Only 'walls',
    'enemy_starts', and 'entrance' (spec 0064) go into the room dict;
    every other room key is read with .get(..., default) downstream, so
    the empty defaults apply.
    The wrapper is runtime-only: levels.py's authoring format, and the
    direct get_level() reads of 'player_start'/'crown_pos', are untouched.
    """
    if 'rooms' in data:
        return data
    return {
        'rooms': {None: {'walls': data['walls'],
                         'enemy_starts': data['enemy_starts'],
                         'entrance': data['entrance']}},
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
        self.room = Room.placeholder()   # until the first room is entered
        # Credit economy (spec 0073 D2): halves bank toward whole credits
        # (HALVES_PER_CREDIT == 2). Blocks: mining a wall or collecting rubble.
        # Bridges: collecting a pack of planks.
        self._block_halves   = 0
        self._block_credits  = 0    # placeable blocks
        self._bridge_halves  = 0
        self._bridge_credits = 0    # buildable bridges
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
        if self.room.block_at(c, r) is not None:
            return True
        return False

    def channel(self, name):
        """Signal-channel query (spec 0050 Q1, kb review R2): receivers
        (gate barriers — later levers, lasers, pistons) ask only this.
        The table is latched once per tick at the plate pass, so state
        changes become visible exactly when the old _gate_open did."""
        return name in self._channels

    # ── Current-room views (spec 0051): read-only over self.room ────────────

    @property
    def cells(self):
        return self.room.cells

    @property
    def enemies(self):
        return self.room.enemies

    @property
    def _current_room(self):
        return self.room.key

    @property
    def _current_room_data(self):
        return self.room.data

    @property
    def _tile_owner(self):
        return self.room.tile_owner

    @property
    def entrance_open(self):
        """True once the level entrance has been unlocked (spec 0066): the
        reserved channel is latched high, so the entrance gate is passable."""
        return ENTRANCE_CHANNEL in self._channels

    @property
    def _safe_tiles(self):
        """The current room's safe area (spec 0068): union of the plates'
        `safe_tiles`.  A block pushed off this set is doomed."""
        return self.room.safe_tile_set

    def _room_floor(self, c, r):
        """Floor tiles of the room that owns (c, r) — a block is confined to
        these (spec 0068).  Act 1 has no `tile_owner`, so the whole interior
        is one room."""
        owner_map = self._tile_owner
        if not owner_map:
            return INTERIOR_TILES
        o = owner_map.get((c, r))
        return frozenset(t for t, oo in owner_map.items() if oo == o)

    @property
    def _flame_jets(self):
        return self.room.flame_jets

    def _register_bump(self, key, col, row):
        """Called when the player walks into wall (col, row) via direction key."""
        if key in self._bump_consumed:
            return  # key not released since last hit — ignore
        barrier = self.cells.barrier(col, row)
        if barrier is None:
            # No fixture: unbridged water (a deliberate bridge attempt) or a
            # pushable block (inert; the push already failed before we got
            # here — normal navigation, no denial).  A refused bridge attempt
            # is a denied deliberate action (spec 0074); the key is consumed so
            # a held direction fires the denial only once per press, like walls.
            if self.cells.is_water(col, row):
                self._bump_consumed.add(key)
                if not self._try_auto_bridge(col, row):
                    self._emit('action_denied')
            return
        action = BARRIER_BUMP[barrier.kind]
        if action == 'key':                         # a locked door
            self._bump_consumed.add(key)
            if not self._try_auto_open_door(col, row):
                self._emit('action_denied')
            return
        if action is None:
            return  # border / reinforced / gate: inert navigation, no denial
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
        self._earn_block_half()   # a mined wall is half a block

    def _earn_block_half(self):
        """Bank half a block credit (spec 0073 D2): a mined wall or a rubble."""
        self._block_halves += 1
        if self._block_halves >= HALVES_PER_CREDIT:
            self._block_halves -= HALVES_PER_CREDIT
            self._block_credits += 1
            self._emit('credit_earned')

    def _earn_bridge_half(self):
        """Bank half a bridge credit (spec 0073 D2): a pack of planks."""
        self._bridge_halves += 1
        if self._bridge_halves >= HALVES_PER_CREDIT:
            self._bridge_halves -= HALVES_PER_CREDIT
            self._bridge_credits += 1
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
        # since the pre-0047 per-room _placed_blocks had the same scope)
        self._block_credits += sum(1 for _ in self.cells.barriers('placed'))
        self._bump_consumed.clear()

        self._rooms = {}         # visited rooms, by key (spec 0051)
        self._level_data = data
        self._transition_timer = 0

        pc, pr = data['player_start']
        self.player = Player(pc, pr)
        self._loot_total = sum(len(rdata.get('treasures', []))
                               for rdata in data['rooms'].values())
        self._loot_collected = 0
        # Key colours actually present in this level (spec 0071 D3): the HUD
        # key strip shows one ghosted slot per colour that appears as a key
        # somewhere in the level, lit when held. Ordered by KEY_NAMES for a
        # stable display; empty when the level has no keys (strip hidden and
        # its HUD space redistributed).
        self._level_key_colours = [
            c for c in KEY_NAMES
            if any(k[2] == c
                   for rdata in data['rooms'].values()
                   for k in rdata.get('keys', []))
        ]
        # How many keys of each colour the level contains (spec 0075): a colour
        # may have 1-4 keys/doors, so the HUD draws a stack of that many icons,
        # lit up to the number held.  Fixed per level -> the strip never reflows.
        self._level_key_counts = {c: 0 for c in self._level_key_colours}
        for rdata in data['rooms'].values():
            for k in rdata.get('keys', []):
                if k[2] in self._level_key_counts:
                    self._level_key_counts[k[2]] += 1
        # Whether this level contains planks anywhere (spec 0072 D2): the HUD
        # BRIDGE counter is shown only on plank-bearing levels. Fixed per level,
        # so the counter's presence and width are constant during play.
        self._level_has_planks = any(
            m[2] == MAT_PLANKS
            for rdata in data['rooms'].values()
            for m in rdata.get('materials', [])
        )
        self._channels = set()   # latched high channel names (spec 0050)
        self.treasure_pos = None
        self._opened_doors = set()
        # Water rooms already made accessible by a bridge.  One bridge per
        # water room (spec 0029 W2): once a room is reachable, no further
        # bridge to it can be built.  Replaces the old per-grid bridge cap.
        self._bridged_water_rooms = set()
        self._enter_room(data['start_room'])

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
        """Swap to a room, creating it on first entry (spec 0051):
        rooms persist by identity, nothing is copied in or out."""
        room = self._rooms.get(room_key)
        fresh = room is None
        if fresh:
            room = Room.from_data(room_key,
                                  self._level_data['rooms'][room_key],
                                  self.difficulty)
            self._rooms[room_key] = room
        self.room = room
        self._flame_timer = 0
        self._bump_consumed.clear()
        # The entrance-exit trigger (spec 0066) needs this room's entrance
        # tile, if any; only the start grid of an Act 2 level carries one.
        self._entrance_pos = self._current_room_data.get('entrance')
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
        for bc, br in self.room.block_positions():
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
        """Assign each enemy to its room based on tile_owner map.

        Act 1 has no tile_owner: its single room owns every interior tile, so
        confine each enemy to INTERIOR_TILES (spec 0066) — leaving room_name
        None keeps them always-chasing while barring them from the border,
        the open entrance included."""
        if not self._tile_owner:
            for enemy in self.enemies:
                enemy.room_tiles = INTERIOR_TILES
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

    def _try_room_transition(self):
        """Check if the player is on an exit tile and transition if so."""
        result = find_exit(self.player.col, self.player.row,
                           self._current_room_data)
        if result is None:
            return False
        target_room, entry_col, entry_row = result
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
                self._open_entrance()      # spec 0066: leave via the entrance

    def _collect_materials(self):
        """Material pickup at the player's tile (Act 2).

        Rubble and planks are credit-only (spec 0073 D2): a rubble banks half
        a block, a pack of planks banks half a bridge — neither enters the
        inventory. Other materials (metal/crystal, when re-enabled) still do.
        """
        item = self._collect_item('material')
        if item is not None:
            if item.payload == MAT_ROCKS:
                self._earn_block_half()
            elif item.payload == MAT_PLANKS:
                self._earn_bridge_half()
            else:
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
        plates = self.room.plates
        if not plates:
            return

        occupied = {(self.player.col, self.player.row)}
        occupied.update((e.col, e.row) for e in self.enemies)
        block_set = set(self.room.block_positions())

        # Relatch ONLY the channels emitted by this room's plates: a
        # channel held high by a block parked in another grid must
        # survive (cross-grid gates) — the old _gate_open code only ever
        # add/discarded the current room's gate-ids.
        local = {gate_id for _pc, _pr, gate_id in plates}
        pressed = {
            gate_id for pc, pr, gate_id in plates
            if (pc, pr) in occupied or (pc, pr) in block_set}
        self._channels = (self._channels - local) | pressed

    def _try_push_block(self, bc, br, dcol, drow):
        """Try to push a block at (bc, br) in direction (dcol, drow)."""
        block = self.room.block_at(bc, br)
        if block is None:
            return False
        nc, nr = bc + dcol, br + drow
        # Confined to the block's own room floor (spec 0068): a block may be
        # pushed anywhere in its room — including out of the safe area, which
        # ignites it — but never off the room's floor.
        if not self.blocked(nc, nr) and (nc, nr) in self._room_floor(bc, br):
            block.col, block.row = nc, nr
            self._emit('bumped')
            self._light_doomed_fuses()
            return True
        return False

    def _light_doomed_fuses(self):
        """Ignite any block that has been pushed out of the safe area (spec
        0068).  A block on a plate is always in the safe set, so it is never
        lit; an already-fused block is left alone (the fuse never re-lights)."""
        safe = self._safe_tiles
        if not safe:
            return          # no plate in this room → no puzzle → nothing to doom
        for b in self.room.blocks:
            if b.fuse is None and (b.col, b.row) not in safe:
                b.fuse = BLOCK_FUSE_MS
                self._emit('block_fuse_lit', b.col, b.row)

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
        never be wasted.  Builds only if the player has a bridge credit, the
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
        for pc, pr, _gid in self.room.plates:
            if abs(pc - col) + abs(pr - row) == 1:
                return False
        # A bridge is buildable when the player has at least one bridge credit
        # (2 planks collected = 1 credit, spec 0073 D2).
        if self._bridge_credits <= 0:
            return False
        # Check that the opposite side has open floor (not wall/water)
        pc, pr = self.player.col, self.player.row
        dc, dr = col - pc, row - pr
        far_c, far_r = col + dc, row + dr
        if (0 < far_c < COLS - 1 and 0 < far_r < ROWS - 1
                and not self.blocked(far_c, far_r)):
            self._bridge_credits -= 1
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
        # Off-screen press: leave the level through the open entrance (spec
        # 0066), else a grid transition if standing on a border exit.  The
        # entrance exit mirrors the grid-change flow — walk onto the open
        # door, then this outward press ends the level.
        if not (0 <= tc < COLS and 0 <= tr < ROWS):
            if self.entrance_open and \
                    (self.player.col, self.player.row) == self._entrance_pos:
                self.advance_level()
                return False
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
        """SPACE: place a block from a block credit (spec 0073 D2)."""
        self._place_block()

    def _is_respawn_tile(self, c, r):
        """The start room's player_start — where the player respawns on death
        (spec 0067).  A crafted wall/block here would trap the player, so
        placement on it is refused."""
        return (self._current_room == self._level_data['start_room']
                and (c, r) == tuple(self._level_data['player_start']))

    def _place_block(self):
        c, r = self.player.col, self.player.row
        if (self._block_credits > 0 and not self.blocked(c, r)
                and not self._is_respawn_tile(c, r)):
            self._block_credits -= 1
            self.cells.set_barrier((c, r), Barrier('placed'))
            self._emit('block_placed')
        else:
            self._emit('action_denied')   # no credit / blocked / respawn tile

    def buy_shield(self):
        if not self.shield and self.score >= SHIELD_COST_PTS:
            self.shield = True
            self._shield_timer = SHIELD_DURATION_MS
            self.score -= SHIELD_COST_PTS
            self._emit('shield_bought')
        else:
            self._emit('action_denied')   # already shielded / too few points

    # ── Level transitions ─────────────────────────────────────────────────────

    def _open_entrance(self):
        """Award completion (spec 0066): unlock the level entrance by
        latching its reserved channel high.  The gate barrier at the entrance
        then stops blocking, so the tile becomes a walkable exit gap; leaving
        through it (a further off-screen press) is what ends the level."""
        if ENTRANCE_CHANNEL in self._channels:
            return
        self._channels.add(ENTRANCE_CHANNEL)
        self._emit('entrance_opened')

    def advance_level(self):
        if self.level >= NUM_LEVELS:
            self._end_game(won=True)
            return
        self.lives += 1
        self._emit('level_advanced', self.level + 1)
        self.start_level(self.level + 1)
        self._emit('level_intro')

    def _on_caught(self, enemy):
        """Player-enemy collision.  Shielded: shove the catcher away and spend
        the shield (no life lost).  Otherwise lose a life — the full
        death-respawn reset (spec 0067) handles every enemy, so no pre-relocate
        here."""
        if self.shield:
            self._respawn_enemy(enemy)
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
            # Respawn at the start (spec 0067): return to the start room
            # (Decision 1), reposition the player, and reset blocks + every
            # enemy to their starts.
            data = get_level(self.level)
            self._enter_room(self._level_data['start_room'])
            self.player.col, self.player.row = data['player_start']
            # Blocks are NOT reset on death (spec 0068): wedged blocks
            # self-heal by exploding, so dying preserves solved puzzle
            # progress.  `_channels` is left untouched so plate-gates recompute
            # from live occupancy at the next latch and the open entrance
            # persists.
            self._reset_enemies()

    def _tick_block_fuses(self, dt):
        """Count down every burning block and detonate at zero (spec 0068).
        Runs before the plate latch so a detonation that moves a block off a
        plate closes its gate the same tick."""
        for b in self.room.blocks:
            if b.fuse is None:
                continue
            b.fuse -= dt
            if b.fuse <= 0:
                b.fuse = None
                self._detonate_block(b)

    def _detonate_block(self, b):
        """Explode a doomed block (spec 0068): deduct the penalty, emit the
        blast, and respawn it on a random free tile inside the safe area
        (spec 0076)."""
        self.score = max(0, self.score - BLOCK_EXPLOSION_PENALTY)
        self._emit('block_exploded', b.col, b.row)
        b.col, b.row = self._block_respawn_tile(b)
        b.fuse = None

    def _block_respawn_tile(self, b):
        """A random free tile inside the room's safe area, avoiding plate tiles
        unless nothing else is free (spec 0076 / BL-55).  Free = not blocked
        (walls / water / another block) and not the player's tile; enemies never
        share a push-puzzle room (R-P9).  The detonating block sits on an unsafe
        tile, so it excludes itself.  Falls back to its current tile only if the
        safe area has no free tile at all (degenerate; never with one block)."""
        player = (self.player.col, self.player.row)
        plates = {pos for pos, _ in self.room.cells.fixtures_of_kind('plate')}
        free = [t for t in self._safe_tiles
                if not self.blocked(*t) and t != player]
        non_plate = sorted(t for t in free if t not in plates)
        if non_plate:
            return random.choice(non_plate)            # normal path
        if free:
            return random.choice(sorted(free))         # tiny room: plate last resort
        return (b.col, b.row)                           # doomed-but-inert fallback

    def _forge_ogre_attack(self, enemy):
        """Forge ogre damages an adjacent player-placed wall (2 hits to break)."""
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            tc, tr = enemy.col + dc, enemy.row + dr
            b = self.cells.barrier(tc, tr)
            if b is not None and b.kind == 'placed':
                hits = b.hits + 1
                if hits >= enemy.block_bump_power:
                    self._break_wall(tc, tr)
                else:
                    b.hits = hits
                    self._emit('bumped')
                return

    def _room_blocked(self, room, c, r):
        """`blocked` for an arbitrary room (not necessarily the current one)."""
        if not (0 <= c < COLS and 0 <= r < ROWS):
            return True
        if room.cells.blocked(c, r, self._channels):
            return True
        return room.block_at(c, r) is not None

    def _bfs_seeds(self, room, seeds):
        """BFS distance map over `room`'s unblocked tiles from many seeds."""
        dist = {s: 0 for s in seeds}
        q = deque(dist)
        while q:
            c, r = q.popleft()
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nc, nr = c + dc, r + dr
                if (nc, nr) not in dist and not self._room_blocked(room, nc, nr):
                    dist[(nc, nr)] = dist[(c, r)] + 1
                    q.append((nc, nr))
        return dist

    def _player_reach(self, room):
        """Tiles the player can reach in `room` (spec 0067): from the player's
        own tile in the current room, else from the room's entry tiles (the
        border gaps the player crosses to get in).  A tile absent from this
        map is unblocked-unreachable — a sealed pocket."""
        if room is self.room:
            return self._bfs_from(self.player.col, self.player.row)
        return self._bfs_seeds(room, list(_exit_tiles(room.data.get('exits', {}))))

    def _reset_enemies(self):
        """Respawn every visited room's enemies to their starts (spec 0067),
        but only where that is SAFE: unblocked, clear of the player, and in the
        component the player reaches in that room.  Otherwise relocate into
        that component (never inside a wall, on/beside the player, or sealed in
        a pocket the player can't reach)."""
        for room in self._rooms.values():
            reach = self._player_reach(room)
            for enemy, home in zip(room.enemies, room.enemies_initial):
                if self._safe_home(home, room, reach):
                    enemy.col, enemy.row = home
                else:
                    self._respawn_enemy(enemy, reach, room)
                enemy.reset_patrol()

    def _safe_home(self, home, room, reach):
        """Is an enemy's start tile a safe respawn given `reach`?"""
        if room is self.room:
            return reach.get(home, 0) >= 2   # reachable, and not on/next to player
        return home in reach                 # reachable from the room's entries

    def _respawn_enemy(self, enemy, reach=None, room=None):
        """Place `enemy` on a tile the player can reach, far from the player
        when possible, confined to the enemy's `room_tiles` (spec 0067).

        `reach` is a player-reachable distance map (defaults to a fresh BFS
        from the player, the shielded-catch case); `room` is the enemy's room
        (defaults to the current room)."""
        room = room or self.room
        if reach is None:
            reach = self._bfs_from(self.player.col, self.player.row)
        others = {(e.col, e.row) for e in room.enemies if e is not enemy}
        excl = {self.treasure_pos} if self.treasure_pos else set()
        confine = enemy.room_tiles

        def _valid(pos, min_dist):
            if reach.get(pos, 0) < min_dist:
                return False
            if pos in excl or pos in others:
                return False
            if confine is not None and pos not in confine:
                return False
            return True

        for min_dist in (8, 4, 1):           # prefer far; min 1 keeps off the player
            candidates = [p for p in reach if _valid(p, min_dist)]
            if candidates:
                enemy.col, enemy.row = random.choice(candidates)
                return

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
        the world frozen.

        SYSTEM ORDER CONTRACT (spec 0052 G5): transition gate → shield
        timer → input phase → enemy movement (incl. forge attacks and
        boss relocation) → treasure/loot collection → player-enemy
        collision → flame damage → block-fuse detonation (spec 0068) →
        channel latch (plate pass) → material pickup → key pickup.  The
        goldens pin this sequence; any future registry entry that ticks or
        collects must slot into it explicitly, never reorder it."""
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
                    self.treasure_pos = None   # final award gone: clear its sprite
                    self._open_entrance()      # spec 0066: leave via the entrance
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

        # Doomed-block fuses (spec 0068): count down and detonate BEFORE the
        # latch, so a block that explodes off a plate closes its gate this tick.
        self._tick_block_fuses(dt)

        # Pressure plates (Act 2): the channel latch pass
        self._latch_channels()

        # Pickups (Act 2)
        self._collect_materials()
        self._collect_keys()
