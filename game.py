"""Presentation layer: state machine, input translation, rendering, sound.

All gameplay state and rules live in world.World (spec 0045); Game
constructs it, forwards input to its methods, and maps its drained event
stream back onto sounds, music, the damage flash, and menu-state changes.
"""
import os
import sys
import random
import pygame
from constants import *
from hud import LabelValue, IconStrip, HBox
from sprites import create_sprites, draw_flame_at
from entities import PatrolEnemy, ForgeOgre
from hiscore import load_scores, save_score, qualifies
from sounds import SoundManager
from world import World, ACT1_BOSS_LEVEL, is_border, _flame_tile_intensity
from crafting import (RECIPES, CRAFT_NAMES, CRAFT_ICONS,
                      MATERIAL_NAMES, MATERIAL_ICONS,
                      TOOL_NAMES, TOOL_ICONS,
                      KEY_NAMES, KEY_COLORS,
                      CRAFT_BRIDGE, MAT_PLANKS)

# Block-blast animation: 4 frames, one every _EXPLOSION_FRAME_MS (spec 0068).
_EXPLOSION_FRAME_MS = 80

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

# Item sprite dispatch (spec 0052 G4): kind + payload -> sprite key.
# The sprite dict is keyed by ints for treasures and by str keys
# otherwise; a None/missing key renders nothing, as before.
_MAT_SPRITE = {'rocks': 'mat_rocks', 'planks': 'mat_planks',
               'metal': 'mat_metal', 'crystal': 'mat_crystal'}
_ITEM_SPRITE = {
    'treasure': lambda payload: payload,
    'key':      lambda payload: f'key_{payload}',
    'material': _MAT_SPRITE.get,
}


_OVERLAY_PAD = 24          # px between overlay text edge and box border


def overlay_box_width(title_w, sub_w):
    """Overlay box width for rendered text widths (spec 0059).

    Any box auto-adapts to longer text; the 420 px minimum keeps every
    existing short-title overlay pixel-identical, and the clamp leaves a
    20 px margin to each edge of the logical surface.
    """
    want = max(420, title_w + 2 * _OVERLAY_PAD, sub_w + 2 * _OVERLAY_PAD)
    return min(want, LOGICAL_W - 40)


def border_exit_sprite(record, orient, open_channels, opened_doors):
    """Sprite key for a grid-border exit tile, or None to draw nothing.

    record is the room's border_barriers entry (kind, param, home) written
    at stitch time (spec 0056), mirroring the source barrier's appearance —
    including live state — onto both sides of the border.  Open borders get
    no sprite: the gap in the border wall is the marker, and the staircase
    sprite is reserved for floor-to-floor travel.
    """
    if record is None:
        return None
    kind, param, home = record
    if kind == 'locked':
        home_room, (hc, hr) = home
        if (home_room, hc, hr, param) in opened_doors:
            return f'door_open_{orient}'
        return f'door_{param}_{orient}'
    if kind == 'gated':
        state = 'open' if param in open_channels else 'closed'
        return f'gate_{state}_{orient}'
    return None


class Game:
    def __init__(self, surface: pygame.Surface):
        self.surf = surface
        self.world = None        # created by _full_reset when a game starts
        # Set by main.py: present(logical_surface) scales + blits + flips the
        # frame to the window.  Lets the loading screen draw during the blocking
        # Act 2 generation that happens inside _start_level (spec 0028).
        self.present = None
        self.sprites = create_sprites()
        self.sounds = SoundManager()
        self._init_fonts()
        self.difficulty = EASY   # persists across games; player changes it on difficulty screen
        self._debug    = False   # set by main.py when launched with --level; skips menus/hiscore
        self._explosions = []    # active block blasts: [col, row, elapsed_ms] (spec 0068)
        self.state = TITLE
        self._title_init()

    # ── Clock seam ────────────────────────────────────────────────────────────

    def now(self):
        """Current time in ms. Tests override this (game.now = lambda: fake_ms)
        to make key repeat and animation frames deterministic (spec 0044 H1)."""
        return pygame.time.get_ticks()

    # ── Font setup ────────────────────────────────────────────────────────────

    def _init_fonts(self):
        base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        ttf  = os.path.join(base, 'fonts', 'ShareTechMono-Regular.ttf')
        self.font_big   = pygame.font.Font(ttf, 36)
        self.font_med   = pygame.font.Font(ttf, 22)
        self.font_small = pygame.font.Font(ttf, 16)
        self.font_hud   = pygame.font.Font(ttf, 16)
        self.font_title = pygame.font.Font(ttf, 64)

    # ── Loading screen ────────────────────────────────────────────────────────

    def draw_loading(self, done, total):
        """Render "Loading . . ." with a 10-dot progress field (white on black).

        Left-aligned in the lower-left corner.  The font is monospace, so
        swapping filled dots for spaces keeps the line width constant.
        """
        filled = round(10 * done / max(1, total))
        dots = ' '.join(['.'] * filled + [' '] * (10 - filled))
        surf = self.font_big.render(f'Loading {dots}', True, (255, 255, 255))
        self.surf.fill((0, 0, 0))
        margin = 8
        self.surf.blit(surf, (margin,
                              LOGICAL_H - surf.get_height() - margin))

    def _loading_progress(self, done, total):
        """Progress callback for get_level(): paint and present a loading frame.

        Does nothing until main.py has wired up self.present (e.g. in tests).
        """
        if self.present is None:
            return
        self.draw_loading(done, total)
        self.present(self.surf)
        pygame.event.pump()   # keep the window responsive during long builds

    # ── Render helpers ────────────────────────────────────────────────────────

    def _door_orient(self, col, row):
        """Detect orientation from adjacent reinforced walls only.
        'v' = vertical passage (reinforced wall left or right),
        'h' = horizontal (reinforced wall above or below)."""
        def _is_reinforced(c, r):
            if c == 0 or c == COLS - 1 or r == 0 or r == ROWS - 1:
                return True  # border is always reinforced
            b = self.cells.barrier(c, r)
            return b is not None and b.kind == WALL_REINFORCED
        left  = col > 0 and _is_reinforced(col - 1, row)
        right = col < COLS - 1 and _is_reinforced(col + 1, row)
        if left or right:
            return 'v'
        return 'h'

    # ── Game initialisation ───────────────────────────────────────────────────

    def _full_reset(self):
        self.world = World(self.difficulty, progress=self._loading_progress)
        self._inv_cursor = 0  # cursor position in inventory screen
        self._pump_world()

    def _start_level(self, level_num):
        self.world.start_level(level_num)
        self._pump_world()

    # ── World event dispatch ──────────────────────────────────────────────────

    # Events that are pure sound triggers (kind → SFX key).
    _EVENT_SOUNDS = {
        'moved':           'move',
        'bumped':          'bump',
        'wall_broken':     'break',
        'door_opened':     'break',
        'bridge_built':    'place_wall',
        'credit_earned':   'credit',
        'wall_placed':     'place_wall',
        'collected':       'collect',
        'shield_bought':   'shield_buy',
        'shield_expired':  'shield_expire',
        'caught':          'caught',
        'caught_shielded': 'caught_shield',
        'item_relocated':  'item_hit',
        'level_advanced':  'level_up',
        'boss_appeared':   'boss_appear',
        'entrance_opened': 'entrance_open',
        'block_fuse_lit':  'block_fuse',
        'block_exploded':  'block_explode',
    }

    def _pump_world(self):
        """Drain the world's event stream and apply each event, in order.

        Called synchronously after every world entry point (input handlers,
        level start, per-frame update) so sounds, music, and state changes
        happen at exactly the moment the old inline calls did."""
        for event in self.world.drain_events():
            kind = event[0]
            sound = self._EVENT_SOUNDS.get(kind)
            if sound is not None:
                self.sounds.play(sound)
            if kind == 'block_exploded':
                self._explosions.append([event[1], event[2], 0])   # spec 0068
            if kind == 'level_started':
                self._key_repeat   = {}
                self._flash_timer  = 0
                self._intro_timer  = 0
                self._explosions   = []
                self.sounds.start_music(event[1])
            elif kind == 'level_intro':
                self._intro_timer = 2000
                self.state = LEVEL_INTRO
            elif kind == 'flash':
                self._flash_timer = event[1]
            elif kind == 'game_over':
                won = event[1]
                self.sounds.stop_music()
                self.sounds.play('level_up' if won else 'game_over')
                if won:
                    self.sounds.start_music('win')
                self.state = WIN if won else GAME_OVER

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
                self.world.buy_shield()
            elif k == pygame.K_SPACE:
                self.world.place()
            elif k == pygame.K_TAB and self.crafting:
                self.state = INVENTORY
                self._inv_cursor = 0
                self.sounds.pause_music()
            elif k == pygame.K_F10:
                self.world.advance_level()  # cheat: skip to next level
            # Register key-down for movement
            if k in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                now = self.now()
                self._key_repeat[k] = (now, now)
                self._try_move_key(k)
            self._pump_world()

        elif event.type == pygame.KEYUP:
            self._key_repeat.pop(event.key, None)
            self.world.key_released(event.key)  # key released → next press can bump

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
        self.world.try_move(dcol, drow, key)

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
        # The flash timer is presentation state, but it freezes with the
        # world during a room transition (as it always did), so gate its
        # decrement on the transition timer as seen at frame start.
        if self.world._transition_timer <= 0 and self._flash_timer > 0:
            self._flash_timer -= dt
        # Advance block-blast animations and drop finished ones (spec 0068).
        for e in self._explosions:
            e[2] += dt
        self._explosions = [e for e in self._explosions
                            if e[2] < 4 * _EXPLOSION_FRAME_MS]
        self.world.update(dt, input_phase=self._key_repeat_phase)
        self._pump_world()

    def _key_repeat_phase(self):
        """Key repeat: input hardware scheduling, run by World.update at the
        point where the old inline key-repeat block sat."""
        now = self.now()
        for key, (first, last) in list(self._key_repeat.items()):
            elapsed_first = now - first
            elapsed_last  = now - last
            if elapsed_first >= FIRST_REPEAT_MS and elapsed_last >= self.move_ms:
                self._try_move_key(key)
                self._key_repeat[key] = (first, now)

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
            self._render_overlay_text("YOU  WON!",
                                      sub=f"Final score: {self._final_score}",
                                      color=YELLOW)
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
                if self.blocked(c, r):
                    b = self.cells.barrier(c, r)
                    if is_border(c, r):
                        self.surf.blit(sp['border_wall'], (x, y))
                    elif b is not None and b.kind == 'placed':
                        self.surf.blit(sp['placed_wall'], (x, y))
                        if b.hits:
                            self.surf.blit(sp[f'crack{b.hits}'], (x, y))
                    else:
                        # Barrier kinds equal the WALL_* constants; door,
                        # gate, block, and water cells fall back to the
                        # stone base tile their overlay is drawn over,
                        # exactly as the grid renderer did.
                        wt = b.kind if b is not None else None
                        self.surf.blit(sp[_WALL_SPRITE.get(wt, 'wall')], (x, y))
                        if wt != WALL_REINFORCED:
                            hits = b.hits if b is not None else 0
                            if hits:
                                self.surf.blit(sp[f'crack{hits}'], (x, y))
                else:
                    if (c, r) in getattr(self, '_safe_tiles', frozenset()):
                        self.surf.blit(sp['safe_floor'], (x, y))
                    else:
                        self.surf.blit(sp['floor'], (x, y))

        # Every level is a one-or-more-room multiroom level (spec 0046):
        # the room collections below always exist and are simply empty on
        # Act 1, so none of these blocks needs an act gate any more.
        rk = self._current_room

        # Level entrance sprite at the start-grid entry border tile — open
        # once all awards are collected (spec 0066), else the closed door.
        if 'entrance' in self._current_room_data:
            ec, er = self._current_room_data['entrance']
            key = 'level_entrance_open' if self.world.entrance_open \
                else 'level_entrance'
            self.surf.blit(sp[key], (ec * TILE, er * TILE))

        # Grid border exits mirror the source barrier's appearance (spec
        # 0056); an open border is just the gap in the border wall.
        border_recs = self._current_room_data.get('border_barriers', {})
        for exit_key in self._current_room_data.get('exits', {}):
            side, pos_str = exit_key.rsplit('_', 1)
            pos = int(pos_str)
            if side == 'right':    sc, sr = COLS - 1, pos
            elif side == 'left':   sc, sr = 0,        pos
            elif side == 'bottom': sc, sr = pos, ROWS - 1
            else:                  sc, sr = pos, 0
            skey = border_exit_sprite(border_recs.get(exit_key),
                                      self._door_orient(sc, sr),
                                      self.world._channels,
                                      self._opened_doors)
            if skey is not None:
                self.surf.blit(sp[skey], (sc * TILE, sr * TILE))

        # Treasure: pre-placed loot (Act 2) and the sequential item (Act 1)
        # are mutually exclusive by data — the item layer is empty on Act 1,
        # treasure_pos is None on Act 2.
        self._blit_items('treasure', sp)
        if self.treasure_pos:
            tc, tr = self.treasure_pos
            tz = self.treasure_item_no
            if tz in sp:
                self.surf.blit(sp[tz], (tc * TILE, tr * TILE))

        # Act 2 overlays: plates, gates, blocks, doors, keys, materials
        for pc, pr, _gid in self.room.plates:
            self.surf.blit(sp['pressure_plate'], (pc * TILE, pr * TILE))
        for (gc, gr), gate in self.cells.barriers('gate'):
            if gate.channel == ENTRANCE_CHANNEL:
                continue     # the entrance gate is drawn as a door, above
            o = self._door_orient(gc, gr)
            base = 'gate_open' if self.channel(gate.channel) else 'gate_closed'
            self.surf.blit(sp[f'{base}_{o}'], (gc * TILE, gr * TILE))
        for b in self.room.blocks:
            self.surf.blit(sp['pushable_block'], (b.col * TILE, b.row * TILE))
            if b.fuse is not None:                     # doomed: red-glow blend (spec 0068)
                glow = 1.0 - max(0, b.fuse) / BLOCK_FUSE_MS
                g = sp['block_glow']
                g.set_alpha(int(30 + 170 * min(1.0, max(0.0, glow))))
                self.surf.blit(g, (b.col * TILE, b.row * TILE))
        for col, row, elapsed in self._explosions:     # 4-frame blast (spec 0068)
            frame = min(3, int(elapsed // _EXPLOSION_FRAME_MS))
            self.surf.blit(sp[f'explosion_{frame}'], (col * TILE, row * TILE))
        # Detect water orientation: if any neighbor up/down is also
        # water, the stream is vertical; otherwise horizontal.
        for wc, wr in self.cells.water_tiles():
            vert = (self.cells.is_water(wc, wr - 1) or
                    self.cells.is_water(wc, wr + 1))
            o = 'v' if vert else 'h'
            if self.cells.bridge(wc, wr):
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
        for (dc, dr), door in self.cells.barriers('door'):
            o = self._door_orient(dc, dr)
            dkey = f'door_{door.colour}_{o}'
            if dkey in sp:
                self.surf.blit(sp[dkey], (dc * TILE, dr * TILE))
        for ok, dc, dr, _color in self._opened_doors:
            if ok != rk:
                continue
            o = self._door_orient(dc, dr)
            self.surf.blit(sp[f'door_open_{o}'], (dc * TILE, dr * TILE))
        self._blit_items('key', sp)
        self._blit_items('material', sp)

        # Enemies / boss
        if self.level == ACT1_BOSS_LEVEL:
            phase = (self.now() // 120) % 4
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

    def _blit_items(self, kind, sp):
        """Draw all items of one kind via the _ITEM_SPRITE table (spec
        0052 G4).  Call sites keep the pinned category blit order."""
        sprite_key = _ITEM_SPRITE[kind]
        for (c, r), item in self.cells.items_of_kind(kind):
            skey = sprite_key(item.payload)
            if skey is not None and skey in sp:
                self.surf.blit(sp[skey], (c * TILE, r * TILE))

    # Geometry for the HUD key strip (spec 0071 D3).
    _KEY_ICON = 20
    _KEY_SLOT = 23   # icon + 3px pad
    _KEY_GHOST_ALPHA = 38   # ~15% opacity for a colour not currently held

    def _key_strip_element(self):
        """The HUD key tracker as an IconStrip element, or None when the level
        has no keys (spec 0071 D3, spec 0072 D3).

        One fixed-width slot per key colour present in the level (ordered by
        KEY_NAMES), lit when the key is held and ghosted (~15%) when not — a
        collect-tracker. The colour set is constant for the level, so the strip
        never reflows during play; it only differs between levels. Returns None
        for a keyless level, so the element is simply omitted from the HBox and
        its space redistributed.
        """
        colours = self._level_key_colours
        if not colours:
            return None
        sp = self.sprites
        icons = []
        for key_color in colours:
            skey = f'icon_key_{key_color}'
            if skey not in sp:
                continue
            icons.append((sp[skey], self.inventory.keys.get(key_color, 0) > 0))
        return IconStrip(icons, self._KEY_SLOT, self._KEY_ICON,
                         self._KEY_GHOST_ALPHA)

    def _render_hud(self):
        hud_y = ROWS * TILE
        pygame.draw.rect(self.surf, HUD_BG, (0, hud_y, LOGICAL_W, STATUS_H))
        f = self.font_hud

        # One HUD text colour throughout (spec 0072): everything is HUD_TEXT;
        # inactive/empty counters are dimmed to HUD_DIM (a darker shade of the
        # same hue) rather than given a distinct colour.
        # WALLS: fixed width with optional "." when half a credit has been mined.
        wall_color = HUD_TEXT if self._place_credits > 0 else HUD_DIM
        walls_dot = '.' if self._breaks_toward_credit > 0 else ' '

        # Pad SEEK name to the longest treasure name so the slot never shifts.
        max_name = max(len(v) for v in TREASURE_NAMES.values())
        item_name = TREASURE_NAMES.get(self.treasure_item_no, "")

        # SHIELD: always present at fixed width "SHIELD XX" so layout never
        # shifts. Active shows the remaining seconds; inactive shows a dim
        # "SHIELD --" placeholder (spec 0072 D4 follow-up — the gap separators
        # made a blank reserved slot look like an empty element).
        if self.shield:
            shield_val = f"{max(1, (self._shield_timer + 999) // 1000):>2}"
            shield_col = HUD_TEXT
        else:
            shield_val = "--"          # same width, dim placeholder
            shield_col = HUD_DIM

        # HUD elements in display order; conditional ones are simply not added.
        elements = [
            LabelValue(f, "SCORE", f"{self.score:>7}", HUD_TEXT),
            LabelValue(f, "LEVEL", f"{self.level:>2}", HUD_TEXT),
            LabelValue(f, "LIVES", f"{self.lives:>2}", HUD_TEXT),
        ]
        if self.spawn_mode == 'preplaced':
            elements.append(LabelValue(f, "LOOT",
                                       f"{self._loot_collected:>2}/{self._loot_total}", HUD_TEXT))
        else:
            elements.append(LabelValue(f, "SEEK:", f"{item_name:<{max_name}}", HUD_TEXT))

        strip = self._key_strip_element()       # keys, after SEEK/LOOT (0071)
        if strip is not None:
            elements.append(strip)

        if self.level == ACT1_BOSS_LEVEL:
            elements.append(LabelValue(f, "BOSS", "", HUD_TEXT))
        elif self.difficulty == HARD:
            elements.append(LabelValue(f, "HARD", "", HUD_TEXT))

        elements.append(LabelValue(f, "SHIELD", shield_val, shield_col))

        # BRIDGE: buildable bridges from carried planks (2 planks = 1 bridge),
        # plus any pre-crafted bridge; a trailing "." marks one odd plank (half
        # a bridge banked), mirroring WALLS. Shown only on plank-bearing levels
        # (spec 0072 D2); omitted elsewhere and the HBox redistributes the space.
        if self._level_has_planks:
            planks = self.inventory.materials.get(MAT_PLANKS, 0)
            buildable = self.inventory.crafted.get(CRAFT_BRIDGE, 0) + planks // 2
            bridge_dot = '.' if planks % 2 else ' '
            bridge_col = HUD_TEXT if buildable > 0 else HUD_DIM
            elements.append(LabelValue(f, "BRIDGE",
                                       f"{buildable:>2}{bridge_dot}", bridge_col))

        elements.append(LabelValue(f, "WALLS",
                                   f"{self._place_credits:>2}{walls_dot}", wall_color))

        HBox(LOGICAL_W, margin=10, gap_color=HUD_GAP).blit(
            self.surf, elements, hud_y, STATUS_H)

    # ── Overlays ─────────────────────────────────────────────────────────────

    def _render_overlay_text(self, text, sub="", color=WHITE):
        overlay = pygame.Surface((LOGICAL_W, ROWS * TILE), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.surf.blit(overlay, (0, 0))

        img = self.font_big.render(text, True, color)
        simg = self.font_small.render(sub, True, GRAY) if sub else None

        # Box adapts to the text (spec 0059); box and texts are all
        # centred on LOGICAL_W // 2, so widening stays symmetric.
        box_w = overlay_box_width(img.get_width(),
                                  simg.get_width() if simg else 0)
        box_h = 90 if sub else 60
        bx = (LOGICAL_W - box_w) // 2
        by = (ROWS * TILE - box_h) // 2
        pygame.draw.rect(self.surf, (30, 30, 50), (bx, by, box_w, box_h), border_radius=8)
        pygame.draw.rect(self.surf, color, (bx, by, box_w, box_h), 2, border_radius=8)

        self.surf.blit(img, (LOGICAL_W // 2 - img.get_width() // 2, by + 10))
        if simg:
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
                # Keys are unique per colour (levelgraph distinct-colour pool),
                # so no count is shown — [icon] Name only, aligned with Tools
                # (spec 0071 D1).
                col = KEY_COLORS.get(key_color, WHITE)
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
        phase = (self.now() // 120) % 4
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
        cursor = "|" if int(self.now() / 500) % 2 == 0 else ""
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


# ── World facade ──────────────────────────────────────────────────────────────
# Read-only delegating properties for every world attribute the renderer, the
# HUD, and the spec-0044 harness read off the Game instance (spec 0045).
# Deliberately no setters: writes must go through game.world, so state can
# never silently fork between the two objects.

_WORLD_ATTRS = (
    'level', 'score', 'lives', 'shield', '_shield_timer',
    'player', 'enemies', 'inventory',
    'treasure_pos', 'treasure_item_no', 'item_no',
    'move_ms', 'enemy_ms',
    'cells', 'blocked', 'channel', 'room',
    'spawn_mode', 'crafting', '_current_room', '_current_room_data',
    '_place_credits', '_breaks_toward_credit',
    '_opened_doors', '_safe_tiles', '_level_key_colours', '_level_has_planks',
    '_flame_jets', '_flame_timer', '_loot_total', '_loot_collected',
    '_transition_timer', '_final_score', '_final_level',
)


def _world_property(name):
    def _get(self):
        return getattr(self.world, name)
    _get.__name__ = name
    return property(_get, doc=f'Read-only view of world.{name}')


for _name in _WORLD_ATTRS:
    setattr(Game, _name, _world_property(_name))
del _name
