"""Core game logic and rendering."""
import random
from collections import deque
import pygame
from constants import *
from sprites import create_sprites
from levels import LEVELS
from entities import Player, Enemy
from hiscore import load_scores, save_score, qualifies

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

NUM_LEVELS  = len(LEVELS)


class Game:
    def __init__(self, surface: pygame.Surface):
        self.surf = surface
        self.sprites = create_sprites()
        self._init_fonts()
        self.difficulty = EASY   # persists across games; player changes it on difficulty screen
        self._debug    = False   # set by main.py when launched with --level; skips menus/hiscore
        self.state = TITLE
        self._title_init()

    # ── Font setup ────────────────────────────────────────────────────────────

    def _init_fonts(self):
        self.font_big   = pygame.font.SysFont('monospace', 36, bold=True)
        self.font_med   = pygame.font.SysFont('monospace', 22, bold=True)
        self.font_small = pygame.font.SysFont('monospace', 16)
        self.font_hud   = pygame.font.SysFont('monospace', 16, bold=True)
        self.font_title = pygame.font.SysFont('monospace', 64, bold=True)

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
        # Level walls
        for (c, r) in self._level_walls:
            w[c][r] = True
        # Placed walls
        for (c, r) in self._placed_walls:
            w[c][r] = True
        self.walls = w

    def _is_border(self, col, row):
        return col == 0 or col == COLS - 1 or row == 0 or row == ROWS - 1

    def _register_bump(self, key, col, row):
        """Called when the player walks into wall (col, row) via direction key."""
        if key in self._bump_consumed:
            return  # key not released since last hit — ignore
        if self._is_border(col, row):
            return  # indestructible
        self._bump_consumed.add(key)
        hits = self._wall_hits.get((col, row), 0) + 1
        if hits >= WALL_HITS_TO_BREAK:
            self._break_wall(col, row)
        else:
            self._wall_hits[(col, row)] = hits

    def _break_wall(self, col, row):
        self._wall_hits.pop((col, row), None)
        self._level_walls.discard((col, row))
        self._placed_walls.discard((col, row))
        self._build_walls()
        self._breaks_toward_credit += 1
        if self._breaks_toward_credit >= BREAKS_PER_CREDIT:
            self._breaks_toward_credit -= BREAKS_PER_CREDIT
            self._place_credits += 1

    # ── Game initialisation ───────────────────────────────────────────────────

    def _full_reset(self):
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
        self._start_level(1)

    def _start_level(self, level_num):
        self.level = level_num
        self.item_no  = 0
        data = LEVELS[level_num - 1]
        self._level_walls = set(data['walls'])
        # Refund one credit per placed wall being cleared (they were earned legitimately)
        self._place_credits += len(self._placed_walls)
        self._placed_walls.clear()
        self._wall_hits.clear()
        self._bump_consumed.clear()
        self._build_walls()
        pc, pr = data['player_start']
        self.player  = Player(pc, pr)
        starts = data['enemy_starts']
        # Level 10 always has exactly 1 enemy (the boss) on both difficulties.
        # Levels 1-9: HARD uses all starts, EASY only the first.
        active = starts if (self.difficulty == HARD and level_num < NUM_LEVELS) \
                 else starts[:1]
        self.enemies = [Enemy(ec, er) for ec, er in active]
        # Speed: level 10 runs at full BASE_ENEMY_MS / BOSS_MOVE_MS.
        # Each earlier level is 5% slower per step: factor = 1.05^(10 − level).
        # At level 1 both enemy and player are ~55% slower than at level 10.
        # self.move_ms replaces REPEAT_MS in the key-repeat check so player speed scales too.
        if level_num == NUM_LEVELS:
            self.enemy_ms = BOSS_MOVE_MS
            self.move_ms  = BASE_MOVE_MS
        else:
            factor = 1.05 ** (NUM_LEVELS - level_num)
            self.enemy_ms = round(BASE_ENEMY_MS * factor)
            self.move_ms  = round(BASE_MOVE_MS  * factor)
        self.shield = False
        self._shield_timer = 0
        self._spawn_treasure()
        self._move_timer   = 0
        self._enemy_timer  = 0
        self._key_repeat   = {}
        self._flash_timer  = 0
        self._intro_timer  = 0

    def _spawn_treasure(self):
        self.item_no += 1
        if self.item_no > 9:
            self.item_no = 1
        self.treasure_item_no = 10 if (self.item_no == 9 and self.level == NUM_LEVELS) \
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

    # ── Title screen ─────────────────────────────────────────────────────────

    def _title_init(self):
        self.state = TITLE
        self._title_ms = 0
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
                self._full_reset()
                self._intro_timer = 2000
                self.state = LEVEL_INTRO

        elif self.state == LEVEL_INTRO:
            if event.type == pygame.KEYDOWN:
                self._intro_timer = 0   # skip wait

        elif self.state == PLAYING:
            self._playing_event(event)

        elif self.state == PAUSED:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                self.state = PLAYING

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
            elif k == pygame.K_RETURN:
                self._buy_shield()
            elif k == pygame.K_SPACE:
                self._place_wall()
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
            # Successful step clears the bump-consumed flag so the player can
            # bump the next wall they reach without having to re-press the key.
            self._bump_consumed.discard(key)
        else:
            tc = self.player.col + dcol
            tr = self.player.row + drow
            if 0 <= tc < COLS and 0 <= tr < ROWS and self.walls[tc][tr]:
                self._register_bump(key, tc, tr)

    def _place_wall(self):
        c, r = self.player.col, self.player.row
        if self._place_credits > 0 and not self.walls[c][r]:
            self._place_credits -= 1
            self._placed_walls.add((c, r))
            self._build_walls()

    # ── Level transitions ─────────────────────────────────────────────────────

    def _advance_level(self):
        if self.level >= NUM_LEVELS:
            self._end_game(won=True)
            return
        self.lives += 1
        self._start_level(self.level + 1)
        self._intro_timer = 2000
        self.state = LEVEL_INTRO

    def _on_caught(self, enemy):
        """Handle player-enemy collision: respawn the enemy far away, then apply hit."""
        self._respawn_enemy(enemy)
        if self.shield:
            self.shield = False
            self._shield_timer = 0
        else:
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

    def _respawn_enemy(self, enemy):
        """Teleport enemy to a tile at significant BFS distance from the player."""
        dist = self._bfs_from(self.player.col, self.player.row)
        others = {(e.col, e.row) for e in self.enemies if e is not enemy}
        candidates = [
            pos for pos, d in dist.items()
            if d >= 8
            and pos != self.treasure_pos
            and pos not in others
        ]
        if not candidates:
            candidates = [
                pos for pos, d in dist.items()
                if d >= 4
                and pos != self.treasure_pos
                and pos not in others
            ]
        if candidates:
            enemy.col, enemy.row = random.choice(candidates)

    def _end_game(self, won):
        self._final_score = self.score * max(1, self.lives)
        self._final_level = self.level
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
        if self._flash_timer > 0:
            self._flash_timer -= dt

        if self._shield_timer > 0:
            self._shield_timer -= dt
            if self._shield_timer <= 0:
                self._shield_timer = 0
                self.shield = False

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
            # reserved tracks tiles claimed by enemies that have already moved
            # this tick; each enemy vacates its old tile before moving.
            reserved = {(e.col, e.row) for e in self.enemies}
            if self.difficulty == HARD:
                dist = self._bfs_from(self.player.col, self.player.row)
                for enemy in self.enemies:
                    reserved.discard((enemy.col, enemy.row))
                    enemy.move_bfs(dist, occupied=reserved)
                    reserved.add((enemy.col, enemy.row))
            else:
                for enemy in self.enemies:
                    reserved.discard((enemy.col, enemy.row))
                    enemy.move_toward(self.player.col, self.player.row,
                                      self.walls, occupied=reserved)
                    reserved.add((enemy.col, enemy.row))
            for enemy in self.enemies:
                if (enemy.col, enemy.row) == self.treasure_pos:
                    self._relocate_treasure()
                    break

        # Collision: any enemy catches player
        for enemy in self.enemies:
            if enemy.col == self.player.col and enemy.row == self.player.row:
                self._on_caught(enemy)
                return

        # Treasure collection
        if (self.player.col, self.player.row) == self.treasure_pos:
            self.score += TREASURE_POINTS.get(self.treasure_item_no, 0)
            if self.item_no == 9:
                self._advance_level()
            else:
                self._spawn_treasure()

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
            if self._flash_timer > 0:
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
            self._render_overlay_text("YOU  WON!", sub=f"Final score: {self._final_score}", color=YELLOW)
        elif self.state == PLAY_AGAIN:
            self._render_field()
            self._render_hud()
            self._render_overlay_text("PLAY AGAIN?", sub="[Y] yes   [N] no")
        elif self.state == ENTER_SCORE:
            self._render_enter_score()
        elif self.state == SHOW_SCORES:
            self._render_scores()

    # ── Field rendering ───────────────────────────────────────────────────────

    def _render_field(self):
        sp = self.sprites

        for c in range(COLS):
            for r in range(ROWS):
                x, y = c * TILE, r * TILE
                if self.walls[c][r]:
                    if self._is_border(c, r):
                        self.surf.blit(sp['border_wall'], (x, y))
                    else:
                        base = 'placed_wall' if (c, r) in self._placed_walls else 'wall'
                        self.surf.blit(sp[base], (x, y))
                        hits = self._wall_hits.get((c, r), 0)
                        if hits:
                            self.surf.blit(sp[f'crack{hits}'], (x, y))
                else:
                    self.surf.blit(sp['floor'], (x, y))

        # Treasure
        tc, tr = self.treasure_pos
        tz = self.treasure_item_no
        if tz in sp:
            self.surf.blit(sp[tz], (tc * TILE, tr * TILE))

        # Enemies / boss
        if self.level == NUM_LEVELS:
            phase = (pygame.time.get_ticks() // 120) % 4
            for enemy in self.enemies:
                self.surf.blit(sp[f'boss_{phase}'], (enemy.col * TILE, enemy.row * TILE))
        else:
            ekey = f'enemy_{(self.level - 1) // 3 + 1}'
            for enemy in self.enemies:
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
            (f"SEEK: {item_name:<{max_name}}",       HUD_TEXT),
        ]
        if self.level == NUM_LEVELS:
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

    def _render_red_flash(self):
        alpha = min(180, int(self._flash_timer * 0.3))
        flash = pygame.Surface((LOGICAL_W, ROWS * TILE), pygame.SRCALPHA)
        flash.fill((220, 20, 20, alpha))
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

        footer = self.font_small.render("[H] High scores          [Q] Quit", True, GRAY)
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

    def _render_story(self):
        self.surf.fill((10, 5, 20))
        lines = [
            "THE  STORY",
            "",
            "A king has locked you in his castle.",
            '"I will only free you once you have',
            ' found all my treasures," he said,',
            "slamming the door.",
            "",
            "You dash off to collect them — but",
            "something lurks in the shadows...",
            "",
            "Press any key to begin.",
        ]
        for i, line in enumerate(lines):
            color = YELLOW if i == 0 else WHITE
            font  = self.font_big if i == 0 else self.font_med
            img   = font.render(line, True, color)
            self.surf.blit(img, (LOGICAL_W // 2 - img.get_width() // 2, 60 + i * 40))

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
