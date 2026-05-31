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
SHOP        = 'shop'
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

    # ── Wall helpers ──────────────────────────────────────────────────────────

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
        self._break_pool += 1
        if self._break_pool >= BREAKS_PER_CREDIT:
            self._break_pool -= BREAKS_PER_CREDIT
            self._place_credits += 1

    # ── Game initialisation ───────────────────────────────────────────────────

    def _full_reset(self):
        self.score        = 0
        self.lives        = STARTING_LIVES
        self.level        = 0
        self.zahl         = 0
        self.shield       = False
        self.move_ms      = BASE_MOVE_MS
        self.enemy_ms     = BASE_ENEMY_MS
        self._placed_walls  = set()
        self._wall_hits     = {}   # (col, row) → hit count (inner walls only)
        self._break_pool    = 0    # leftover breaks toward next credit
        self._place_credits = 0   # available wall placements
        self._bump_consumed = set()  # direction keys that must be released before next bump
        self._start_level(1)

    def _start_level(self, level_num):
        self.level = level_num
        self.zahl  = 0
        data = LEVELS[level_num - 1]
        self._level_walls = set(data['walls'])
        # Refund one credit per placed wall being cleared (they were earned legitimately)
        self._place_credits += len(self._placed_walls)
        self._placed_walls.clear()
        self._wall_hits.clear()
        self._bump_consumed.clear()
        self._build_walls()
        pc, pr = data['player_start']
        ec, er = data['enemy_start']
        self.player = Player(pc, pr)
        self.enemy  = Enemy(ec, er)
        self.shield = False
        self._spawn_treasure()
        self._move_timer   = 0
        self._enemy_timer  = 0
        self._key_repeat   = {}
        self._flash_timer  = 0
        self._intro_timer  = 0

    def _spawn_treasure(self):
        self.zahl += 1
        if self.zahl > 9:
            self.zahl = 1   # safety; level advance happens before this normally
        # Crown only on level 9
        self.treasure_zahl = 10 if (self.zahl == 9 and self.level == NUM_LEVELS) \
                             else self.zahl
        # Random open tile (not player, not enemy, not a wall)
        open_tiles = [
            (c, r) for c in range(1, COLS - 1) for r in range(1, ROWS - 1)
            if not self.walls[c][r]
            and (c, r) != (self.player.col, self.player.row)
            and (c, r) != (self.enemy.col, self.enemy.row)
        ]
        self.treasure_pos = random.choice(open_tiles) if open_tiles else (1, 1)

    def _relocate_treasure(self):
        """Enemy walked over the treasure — move it to a new random open tile."""
        open_tiles = [
            (c, r) for c in range(1, COLS - 1) for r in range(1, ROWS - 1)
            if not self.walls[c][r]
            and (c, r) != (self.player.col, self.player.row)
            and (c, r) != (self.enemy.col, self.enemy.row)
        ]
        if open_tiles:
            self.treasure_pos = random.choice(open_tiles)

    # ── Title screen ─────────────────────────────────────────────────────────

    def _title_init(self):
        self.state = TITLE
        self._title_t = 0

    # ── Input handling ────────────────────────────────────────────────────────

    def handle_event(self, event):
        if self.state == TITLE:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.state = DIFFICULTY
                elif event.key == pygame.K_h:
                    self.state = SHOW_SCORES
                    self._scores_from = TITLE
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

        elif self.state == SHOP:
            self._shop_event(event)

        elif self.state in (GAME_OVER, WIN):
            if event.type == pygame.KEYDOWN:
                self.state = PLAY_AGAIN

        elif self.state == PLAY_AGAIN:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_j or event.key == pygame.K_y:
                    self.state = DIFFICULTY
                elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                    self._title_init()

        elif self.state == ENTER_SCORE:
            self._enter_score_event(event)

        elif self.state == SHOW_SCORES:
            if event.type == pygame.KEYDOWN:
                self.state = getattr(self, '_scores_from', TITLE)

    def _playing_event(self, event):
        if event.type == pygame.KEYDOWN:
            k = event.key
            if k == pygame.K_ESCAPE:
                self.state = PLAY_AGAIN
            elif k == pygame.K_p:
                self.state = PAUSED
            elif k == pygame.K_SPACE:
                self.state = SHOP
            elif k == pygame.K_s:
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

    def _shop_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                if self.score >= SHIELD_COST_PTS and not self.shield:
                    self.shield = True
                    self.score -= SHIELD_COST_PTS
            elif event.key == pygame.K_2:
                if self.score >= LIFE_COST_PTS:
                    self.lives += 1
                    self.score -= LIFE_COST_PTS
            self.state = PLAYING

    def _enter_score_event(self, event):
        if event.type == pygame.KEYDOWN:
            k = event.key
            if k == pygame.K_RETURN and self._name_buf.strip():
                save_score(self._name_buf.strip(), self._final_score)
                self._scores_from = PLAY_AGAIN
                self.state = SHOW_SCORES
            elif k == pygame.K_BACKSPACE:
                self._name_buf = self._name_buf[:-1]
            elif len(self._name_buf) < 20 and event.unicode.isprintable():
                self._name_buf += event.unicode

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

    def _lose_life(self):
        if self.shield:
            self.shield = False
            return
        self.score = max(0, self.score - self.zahl * 1000)
        self.lives -= 1
        self._flash_timer = 600
        if self.lives <= 0:
            self._end_game(won=False)
        else:
            # Reset positions but keep level walls
            data = LEVELS[self.level - 1]
            pc, pr = data['player_start']
            ec, er = data['enemy_start']
            self.player.col, self.player.row = pc, pr
            self.enemy.col,  self.enemy.row  = ec, er

    def _end_game(self, won):
        self._final_score = self.score * max(1, self.lives)
        self.state = WIN if won else GAME_OVER

    # ── Update ───────────────────────────────────────────────────────────────

    def update(self, dt):
        self._title_t = getattr(self, '_title_t', 0) + dt

        if self.state == LEVEL_INTRO:
            self._intro_timer -= dt
            if self._intro_timer <= 0:
                self.state = PLAYING

        elif self.state == PLAYING:
            self._update_playing(dt)

    def _update_playing(self, dt):
        if self._flash_timer > 0:
            self._flash_timer -= dt

        # Key repeat
        now = pygame.time.get_ticks()
        for key, (first, last) in list(self._key_repeat.items()):
            elapsed_first = now - first
            elapsed_last  = now - last
            if elapsed_first >= FIRST_REPEAT_MS and elapsed_last >= REPEAT_MS:
                self._try_move_key(key)
                self._key_repeat[key] = (first, now)

        # Enemy movement
        self._enemy_timer += dt
        if self._enemy_timer >= self.enemy_ms:
            self._enemy_timer -= self.enemy_ms
            if self.difficulty == HARD:
                dist = self._bfs_from(self.player.col, self.player.row)
                self.enemy.move_bfs(dist)
            else:
                self.enemy.move_toward(self.player.col, self.player.row, self.walls)
            if (self.enemy.col, self.enemy.row) == self.treasure_pos:
                self._relocate_treasure()

        # Collision: enemy catches player
        if self.enemy.col == self.player.col and self.enemy.row == self.player.row:
            self._lose_life()
            return

        # Treasure collection
        if (self.player.col, self.player.row) == self.treasure_pos:
            self.score += TREASURE_POINTS.get(self.zahl, 0)
            if self.zahl == 9:
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
        elif self.state == SHOP:
            self._render_field()
            self._render_hud()
            self._render_shop()
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
        tz = self.treasure_zahl
        if tz in sp:
            self.surf.blit(sp[tz], (tc * TILE, tr * TILE))

        # Enemy
        self.surf.blit(sp['enemy'],
                       (self.enemy.col * TILE, self.enemy.row * TILE))

        # Player
        self.surf.blit(sp['player'],
                       (self.player.col * TILE, self.player.row * TILE))
        if self.shield:
            self.surf.blit(sp['shield'],
                           (self.player.col * TILE, self.player.row * TILE))

    def _render_hud(self):
        hud_y = ROWS * TILE
        hud_rect = pygame.Rect(0, hud_y, LOGICAL_W, STATUS_H)
        pygame.draw.rect(self.surf, HUD_BG, hud_rect)

        def htext(txt, x, color=HUD_TEXT):
            img = self.font_hud.render(txt, True, color)
            self.surf.blit(img, (x, hud_y + (STATUS_H - img.get_height()) // 2))

        htext(f"SCORE {self.score:>7}", 4)
        htext(f"LEVEL {self.level}", 200)
        htext(f"LIVES {self.lives}", 310, HUD_LIFE)
        item = TREASURE_NAMES.get(self.treasure_zahl, "")
        htext(f"SEEK: {item}", 430)
        # Wall placement credits — colour signals state, no extra symbols needed:
        #   green  = credits ready to spend
        #   yellow = no credits yet but progress made toward next one
        #   gray   = no credits, no progress
        if self._place_credits > 0:
            wall_color = LTGREEN
        elif self._break_pool > 0:
            wall_color = YELLOW
        else:
            wall_color = GRAY
        htext(f"WALLS  {self._place_credits}", 700, wall_color)
        if self.difficulty == HARD:
            htext("HARD", 840, RED)
        if self.shield:
            htext("★SHIELD", 895, LTBLUE)

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
        t = self._title_t / 1000.0

        # Animated coloured title letters
        title = "UGLYCRAFT"
        colors = [RED, ORANGE, YELLOW, LTGREEN, CYAN, LTBLUE, MAGENTA, WHITE, GOLD]
        char_w = 54
        total_w = char_w * len(title)
        start_x = (LOGICAL_W - total_w) // 2
        base_y   = 120

        for i, ch in enumerate(title):
            wave_y = int(12 * abs(((t * 2 + i * 0.4) % 2) - 1))
            color  = colors[i % len(colors)]
            img = pygame.font.SysFont('monospace', 64, bold=True).render(ch, True, color)
            self.surf.blit(img, (start_x + i * char_w, base_y - wave_y))

        # Subtitle
        sub = self.font_med.render("Inspired by UGLI (1996)", True, GRAY)
        self.surf.blit(sub, (LOGICAL_W // 2 - sub.get_width() // 2, 210))

        # Instructions
        lines = [
            ("Arrow keys", "move"),
            ("S",          "place wall  (costs 1 credit)"),
            ("SPACE",      "shop (shield / extra life)"),
            ("P",          "pause"),
        ]
        lx = LOGICAL_W // 2 - 180
        for i, (key, desc) in enumerate(lines):
            ky = 280 + i * 26
            ki = self.font_small.render(f"[{key}]", True, HUD_KEY)
            di = self.font_small.render(desc, True, WHITE)
            self.surf.blit(ki, (lx, ky))
            self.surf.blit(di, (lx + 180, ky))

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

    # ── Shop overlay ─────────────────────────────────────────────────────────

    def _render_shop(self):
        overlay = pygame.Surface((LOGICAL_W, ROWS * TILE), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.surf.blit(overlay, (0, 0))

        bw, bh = 480, 160
        bx = (LOGICAL_W - bw) // 2
        by = (ROWS * TILE - bh) // 2
        pygame.draw.rect(self.surf, (20, 20, 50), (bx, by, bw, bh), border_radius=8)
        pygame.draw.rect(self.surf, GOLD, (bx, by, bw, bh), 2, border_radius=8)

        title = self.font_big.render("SHOP", True, GOLD)
        self.surf.blit(title, (LOGICAL_W // 2 - title.get_width() // 2, by + 10))

        shield_col = GRAY if self.shield else WHITE
        items = [
            (f"[1] Shield — absorbs one hit          {SHIELD_COST_PTS} pts", shield_col),
            (f"[2] Extra life                        {LIFE_COST_PTS} pts", WHITE),
        ]
        for i, (txt, col) in enumerate(items):
            img = self.font_small.render(txt, True, col)
            self.surf.blit(img, (bx + 16, by + 60 + i * 30))

        note = self.font_small.render(f"Your score: {self.score}  (any other key: close)", True, GRAY)
        self.surf.blit(note, (bx + 16, by + 130))

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
        name_img = self.font_med.render(self._name_buf + cursor, True, WHITE)
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
            for i, (name, sc) in enumerate(scores):
                color = GOLD if i == 0 else WHITE
                line  = f"{i+1:>2}.  {name:<20}  {sc:>9}"
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
            self._name_buf = ""
            self.state = ENTER_SCORE
        else:
            self._scores_from = PLAY_AGAIN
            self.state = SHOW_SCORES
