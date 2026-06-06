"""Procedural pixel-art sprite generation — no external image files."""
import math
import pygame
from constants import *


def _surf(size=TILE, alpha=True):
    flags = pygame.SRCALPHA if alpha else 0
    return pygame.Surface((size, size), flags)


# ── Tiles ─────────────────────────────────────────────────────────────────────

def draw_border_wall(size=TILE):
    """Indestructible outer frame — dark granite, visually heavier than brick."""
    s = _surf(size, alpha=False)
    s.fill((28, 28, 38))
    # Large stone blocks with tight mortar
    mid = size // 2
    for row_y, offset in ((1, 0), (mid + 1, mid // 3)):
        bh = mid - 2
        for bx, bw in ((1 + offset, mid - 2), (mid + offset, size - mid - 2)):
            bx = bx % (size - 2) + 1
            pygame.draw.rect(s, (52, 54, 72), (bx, row_y, min(bw, size - bx - 1), bh))
            # Bevelled top-left edge (highlight)
            pygame.draw.line(s, (72, 74, 96), (bx, row_y), (bx + min(bw, 8), row_y))
            pygame.draw.line(s, (72, 74, 96), (bx, row_y), (bx, row_y + 2))
            # Bevelled bottom-right edge (shadow)
            pygame.draw.line(s, (22, 22, 32),
                             (bx, row_y + bh - 1), (bx + min(bw, size - bx - 1), row_y + bh - 1))
    return s


def draw_damage_cracks(level, size=TILE):
    """Transparent overlay drawn on top of any wall sprite to show hit damage."""
    s = _surf(size)   # fully transparent base
    dark = (10, 10, 10, 220)
    light = (180, 180, 180, 120)
    if level >= 1:
        # Single diagonal crack, upper-left quadrant
        pts = [(size // 4, size // 5),
               (size // 3, size * 2 // 5),
               (size * 2 // 5, size // 2)]
        pygame.draw.lines(s, dark, False, pts, 2)
        pygame.draw.lines(s, light, False, [(p[0]+1, p[1]+1) for p in pts], 1)
        # Small branch
        pygame.draw.line(s, dark,
                         (size // 3, size * 2 // 5),
                         (size // 2, size * 2 // 5 + 3), 1)
    if level >= 2:
        # Second crack, lower-right area, crossing the first
        pts2 = [(size * 3 // 5, size // 3),
                (size // 2, size * 3 // 5),
                (size * 2 // 5, size * 4 // 5)]
        pygame.draw.lines(s, dark, False, pts2, 2)
        pygame.draw.lines(s, light, False, [(p[0]+1, p[1]+1) for p in pts2], 1)
        # Debris dots
        for dx, dy in ((size*2//5, size//3+2), (size*3//5-2, size*3//5+1),
                       (size//3+1, size*3//5-1)):
            pygame.draw.circle(s, dark, (dx, dy), 1)
    return s


def draw_wall(size=TILE):
    s = _surf(size, alpha=False)
    s.fill((90, 22, 22))
    mid = size // 2
    # Two rows of bricks
    for row_y, offset in ((1, 0), (mid + 1, mid // 2)):
        brick_h = mid - 2
        pygame.draw.rect(s, (165, 45, 45), (1, row_y, mid - 2, brick_h))
        pygame.draw.rect(s, (165, 45, 45), (mid + 1, row_y, size - mid - 2, brick_h))
        pygame.draw.rect(s, (165, 45, 45), (1 + offset, mid + 1, size // 2 - 2, brick_h))
        pygame.draw.rect(s, (165, 45, 45), (1 + offset + mid // 2, mid + 1, mid // 2 - 1, brick_h))
    # Highlight
    pygame.draw.line(s, (210, 75, 75), (1, 1), (mid - 2, 1))
    pygame.draw.line(s, (210, 75, 75), (mid + 1, mid + 1), (size - 2, mid + 1))
    return s


def draw_floor(size=TILE):
    s = _surf(size, alpha=False)
    s.fill((8, 8, 12))
    return s


# ── Characters ────────────────────────────────────────────────────────────────

def draw_player(size=TILE):
    s = _surf(size)
    cx, cy = size // 2, size // 2
    r = size // 2 - 3

    # Face
    pygame.draw.circle(s, (255, 215, 0), (cx, cy), r)
    pygame.draw.circle(s, (180, 150, 0), (cx, cy), r, 2)

    # Eyes — positioned in the upper third of the face
    ey = cy - r // 3
    er = max(2, r // 5)
    for ex in (cx - r // 3, cx + r // 3):
        pygame.draw.circle(s, (20, 20, 20), (ex, ey), er)
        pygame.draw.circle(s, WHITE, (ex - 1, ey - 1), max(1, er // 2))

    # Smile — smooth curve computed point-by-point, avoiding pygame.draw.arc artifacts
    smile_rx = r * 5 // 12   # horizontal half-width
    smile_ry = r // 4        # vertical depth
    smile_cy = cy + r // 5   # baseline sits just below centre
    pts = [
        (cx + int(smile_rx * math.cos(math.radians(a))),
         smile_cy + int(smile_ry * math.sin(math.radians(a))))
        for a in range(0, 181, 6)
    ]
    pygame.draw.lines(s, (20, 20, 20), False, pts, 2)

    return s


def _ghost_pts(cx, dome_cy, r, n_bumps=3):
    """Polygon outline of a ghost: dome top + straight sides + scalloped bottom."""
    pts = []
    # Dome: left equator → apex → right equator (angles 180°→360°)
    for a in range(180, 361, 12):
        pts.append((cx + int(r * math.cos(math.radians(a))),
                    dome_cy + int(r * math.sin(math.radians(a)))))
    body_bot = dome_cy + r
    pts.append((cx + r, body_bot))
    # Scalloped bottom: n_bumps downward semicircles, traced right→left
    bw  = (2 * r) // n_bumps
    br  = bw // 2
    for i in range(n_bumps - 1, -1, -1):
        bx = cx - r + int((i + 0.5) * bw)
        for a in range(0, 181, 30):
            pts.append((bx + int(br * math.cos(math.radians(a))),
                        body_bot + int(br * math.sin(math.radians(a)))))
    pts.append((cx - r, dome_cy))
    return pts, body_bot, br


def draw_enemy(size=TILE):
    """Ghost sprite — pale blue-white with dark oval eyes."""
    s   = _surf(size)
    cx  = size // 2
    r   = size // 2 - 4
    dome_cy = r + 1

    pts, body_bot, _ = _ghost_pts(cx, dome_cy, r)

    pygame.draw.polygon(s, (195, 210, 240), pts)
    pygame.draw.polygon(s, (120, 140, 195), pts, 1)

    # Eyes
    ey = dome_cy - r // 5
    er = max(2, r // 4)
    for ex in (cx - r // 3, cx + r // 3):
        pygame.draw.ellipse(s, (30, 40, 80),
                            (ex - er, ey - er, er * 2, int(er * 1.3)))
        pygame.draw.circle(s, WHITE, (ex - 1, ey - 1), max(1, er // 3))

    return s


def draw_boss(phase=0, size=TILE):
    """Electric ghost boss — dark purple with crackling sparks (4-frame animation)."""
    s   = _surf(size)
    cx  = size // 2
    r   = size // 2 - 4
    dome_cy = r + 1

    pts, body_bot, br = _ghost_pts(cx, dome_cy, r)

    # ── Electric glow (semi-transparent halo) ──────────────────────────────
    glow_alpha = (80, 100, 70, 90)[phase]
    glow_col   = (160, 80, 255, glow_alpha)
    glow = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(glow, glow_col, (cx, dome_cy), r + 5)
    pygame.draw.rect(glow,  glow_col, (cx - r - 3, dome_cy, (r + 3) * 2, r + 3))
    s.blit(glow, (0, 0))

    # ── Ghost body ─────────────────────────────────────────────────────────
    pygame.draw.polygon(s, (55, 15, 100), pts)
    ec = ((150, 70, 255), (200, 130, 255), (120, 50, 230), (180, 100, 255))[phase]
    pygame.draw.polygon(s, ec, pts, 2)

    # ── Electric sparks (three per frame, positions cycle with phase) ──────
    # Each entry: (origin_x, origin_y, end_dx, end_dy, zigzag_dx, zigzag_dy)
    spark_sets = [
        [(cx,     dome_cy - r - 1,  0,  -6,  3,  -3),
         (cx + r, dome_cy - r // 2,  5,  -3, -2,   2),
         (cx - r, dome_cy + r // 2, -5,   2,  2,  -3)],
        [(cx,     dome_cy - r - 1,  0,  -6, -3,  -3),
         (cx + r, dome_cy,           6,   0,  2,   3),
         (cx - r, dome_cy - r // 2, -5,  -3, -2,   2)],
        [(cx + r // 2, dome_cy - r,  3,  -5, -3,  -2),
         (cx - r // 2, dome_cy - r, -3,  -5,  3,  -2),
         (cx + r,      dome_cy,      6,   1, -2,   3)],
        [(cx,     dome_cy - r - 1,  0,  -5,  2,  -4),
         (cx + r, dome_cy - r // 3,  5,  -2,  2,   3),
         (cx - r, dome_cy - r // 3, -5,  -2, -2,   3)],
    ]
    sc = ((255, 240, 60), (220, 200, 255), (255, 250, 80), (200, 180, 255))[phase]
    for ox, oy, ex, ey, zx, zy in spark_sets[phase]:
        mid = (ox + ex // 2 + zx, oy + ey // 2 + zy)
        pygame.draw.lines(s, sc, False, [(ox, oy), mid, (ox + ex, oy + ey)], 2)

    # ── Glowing eyes ───────────────────────────────────────────────────────
    ey_y = dome_cy - r // 5
    er   = max(2, r // 4)
    eye_col = ((255, 230, 50), (255, 255, 160), (255, 220, 40), (255, 240, 130))[phase]
    for ex_pos in (cx - r // 3, cx + r // 3):
        pygame.draw.circle(s, eye_col, (ex_pos, ey_y), er)
        pygame.draw.circle(s, WHITE,   (ex_pos - 1, ey_y - 1), max(1, er // 3))

    return s


# ── Treasure sprites ──────────────────────────────────────────────────────────

def draw_coin(size=TILE):
    """item_no=1: gold coin"""
    s = _surf(size)
    cx, cy = size // 2, size // 2
    r = size // 2 - 3
    # Outer rim (slightly darker)
    pygame.draw.circle(s, (160, 120, 20), (cx, cy), r)
    # Main face
    pygame.draw.circle(s, GOLD, (cx, cy), r - 2)
    # Raised rim highlight
    pygame.draw.circle(s, (255, 225, 70), (cx, cy), r - 2, 2)
    # Inner circle for relief detail
    pygame.draw.circle(s, (190, 150, 30), (cx, cy), r - 6)
    # Shine spot
    pygame.draw.circle(s, CREAM, (cx - r // 3, cy - r // 3), max(2, r // 5))
    # Bottom shadow arc
    pygame.draw.arc(s, (130, 100, 10),
                    pygame.Rect(cx - r + 2, cy - r + 2, (r - 2) * 2, (r - 2) * 2),
                    math.radians(250), math.radians(350), 2)
    return s


def draw_big_diamond(size=TILE):
    """item_no=2: large cyan diamond"""
    s = _surf(size)
    cx, cy = size // 2, size // 2
    pts = [(cx, 2), (size - 3, cy), (cx, size - 3), (3, cy)]
    pygame.draw.polygon(s, (80, 150, 240), pts)
    pygame.draw.polygon(s, (160, 220, 255), pts, 2)
    pygame.draw.line(s, (200, 240, 255), (cx, 4), (cx, size - 5), 1)
    pygame.draw.line(s, (200, 240, 255), (5, cy), (size - 5, cy), 1)
    pygame.draw.circle(s, WHITE, (cx - 3, cy - 4), 2)
    return s


def draw_small_gems(size=TILE):
    """item_no=3: scattered colorful gems of varying size"""
    s = _surf(size)
    # (x, y, radius, color) — fixed layout, different colors and sizes
    gems = [
        ( 8,  7, 4, (220,  50,  80)),   # red
        (23,  6, 3, ( 50, 160, 255)),   # blue
        (16, 15, 5, ( 50, 210,  70)),   # green, largest
        ( 6, 21, 3, (255, 200,  40)),   # yellow
        (25, 19, 4, (190,  70, 255)),   # purple
        (14, 25, 3, ( 60, 220, 210)),   # cyan
    ]
    for gx, gy, gr, color in gems:
        pts = [(gx, gy - gr), (gx + gr, gy), (gx, gy + gr), (gx - gr, gy)]
        pygame.draw.polygon(s, color, pts)
        edge = tuple(min(255, c + 70) for c in color)
        pygame.draw.polygon(s, edge, pts, 1)
        pygame.draw.circle(s, WHITE, (gx - 1, gy - 1), max(1, gr // 3))
    return s


def draw_trophy(size=TILE):
    """item_no=4: gold trophy cup"""
    s = _surf(size)
    cx = size // 2
    # Cup body (trapezoid, wider at top)
    cup = [(7, 5), (size - 7, 5), (size - 10, 18), (10, 18)]
    pygame.draw.polygon(s, GOLD, cup)
    pygame.draw.polygon(s, LTYELLOW, cup, 1)
    # Rim
    pygame.draw.rect(s, (255, 225, 60), (6, 4, size - 12, 4), border_radius=2)
    # Handles (small rounded rects on each side)
    for hx in (3, size - 8):
        pygame.draw.rect(s, (185, 145, 30), (hx, 9, 5, 6), border_radius=2)
        pygame.draw.rect(s, LTYELLOW,       (hx, 9, 5, 6), 1, border_radius=2)
    # Stem
    pygame.draw.rect(s, (190, 148, 35), (cx - 3, 18, 6, 5))
    pygame.draw.rect(s, LTYELLOW,       (cx - 3, 18, 6, 5), 1)
    # Base
    pygame.draw.rect(s, GOLD,    (6, 23, size - 12, 5), border_radius=2)
    pygame.draw.rect(s, LTYELLOW,(6, 23, size - 12, 5), 1, border_radius=2)
    # Shine on cup body
    pygame.draw.line(s, CREAM, (10, 7), (10, 16), 1)
    return s


def draw_gold_bar(size=TILE):
    """item_no=5: gold ingot"""
    s = _surf(size)
    m = 4
    h = size // 2 - 2
    rect = pygame.Rect(m, size // 4, size - 2 * m, h)
    pygame.draw.rect(s, GOLD, rect, border_radius=3)
    pygame.draw.rect(s, (255, 230, 100), rect, 2, border_radius=3)
    for i in range(1, 3):
        ly = rect.top + i * h // 3
        pygame.draw.line(s, (170, 135, 40), (m + 3, ly), (size - m - 3, ly), 1)
    pygame.draw.line(s, CREAM, (m + 3, rect.top + 2), (m + 9, rect.top + 2), 2)
    return s


def draw_silver_bar(size=TILE):
    """item_no=6: platinum ingot"""
    s = _surf(size)
    m = 4
    h = size // 2 - 2
    rect = pygame.Rect(m, size // 4, size - 2 * m, h)
    pygame.draw.rect(s, SILVER, rect, border_radius=3)
    pygame.draw.rect(s, (230, 230, 245), rect, 2, border_radius=3)
    for i in range(1, 3):
        ly = rect.top + i * h // 3
        pygame.draw.line(s, DKSILVER, (m + 3, ly), (size - m - 3, ly), 1)
    pygame.draw.line(s, WHITE, (m + 3, rect.top + 2), (m + 9, rect.top + 2), 2)
    return s


def draw_necklace(size=TILE):
    """item_no=7: gold chain necklace with gem pendant"""
    s = _surf(size)
    cx = size // 2
    # Chain: 9 beads along a downward-dipping quadratic bezier arc
    n  = 9
    x0, y0 = 4,        6   # left end
    xm, ym = cx,      17   # midpoint (lowest)
    x1, y1 = size - 4, 6   # right end
    for i in range(n):
        t  = i / (n - 1)
        bx = int((1 - t) ** 2 * x0 + 2 * (1 - t) * t * xm + t ** 2 * x1)
        by = int((1 - t) ** 2 * y0 + 2 * (1 - t) * t * ym + t ** 2 * y1)
        pygame.draw.circle(s, GOLD, (bx, by), 2)
        pygame.draw.circle(s, LTYELLOW, (bx - 1, by - 1), 1)
    # Short drop from lowest bead to pendant
    drop_top = ym + 2
    pygame.draw.line(s, GOLD, (cx, ym), (cx, drop_top), 1)
    # Pendant: teardrop diamond gem
    pr = 5
    py = drop_top + pr
    pts = [(cx, drop_top), (cx + pr, py), (cx, py + pr + 1), (cx - pr, py)]
    pygame.draw.polygon(s, (200, 60, 220), pts)    # purple
    pygame.draw.polygon(s, (240, 150, 255), pts, 1)
    pygame.draw.circle(s, WHITE, (cx - 1, py - 2), 1)
    return s


def draw_lamp(size=TILE):
    """item_no=8: lantern"""
    s = _surf(size)
    cx = size // 2
    # Body hexagon
    body = [(cx, 4), (cx + 8, 8), (cx + 8, size - 10),
            (cx, size - 6), (cx - 8, size - 10), (cx - 8, 8)]
    pygame.draw.polygon(s, (40, 40, 15), body)
    # Glowing glass panels
    inner = [(cx, 7), (cx + 5, 10), (cx + 5, size - 12),
             (cx, size - 8), (cx - 5, size - 12), (cx - 5, 10)]
    pygame.draw.polygon(s, (255, 225, 60), inner)
    pygame.draw.polygon(s, (165, 125, 10), body, 2)
    # Base
    pygame.draw.rect(s, (165, 125, 10),
                     pygame.Rect(cx - 6, size - 8, 12, 5), border_radius=2)
    # Glow center
    pygame.draw.circle(s, CREAM, (cx, size // 2), 3)
    # Hanging hook
    pygame.draw.line(s, (120, 100, 10), (cx - 3, 4), (cx + 3, 4), 2)
    pygame.draw.line(s, (120, 100, 10), (cx, 4), (cx, 1), 2)
    return s


def draw_big_gem(size=TILE):
    """item_no=9: large green octagonal gem"""
    s = _surf(size)
    cx, cy = size // 2, size // 2
    r = size // 2 - 3
    pts = [(cx + int(r * math.cos(math.radians(i * 45 - 22.5))),
            cy + int(r * math.sin(math.radians(i * 45 - 22.5)))) for i in range(8)]
    pygame.draw.polygon(s, (35, 185, 55), pts)
    r2 = r * 2 // 3
    inner = [(cx + int(r2 * math.cos(math.radians(i * 45 - 22.5))),
              cy + int(r2 * math.sin(math.radians(i * 45 - 22.5)))) for i in range(8)]
    pygame.draw.polygon(s, (90, 240, 110), inner)
    pygame.draw.polygon(s, (160, 255, 160), pts, 2)
    pygame.draw.circle(s, WHITE, (cx - 3, cy - 4), 2)
    return s


def draw_crown(size=TILE):
    """item_no=10 (level 9 final treasure): golden crown"""
    s = _surf(size)
    cx = size // 2
    yb = size - 5
    # Three prongs
    prong_pts = [
        (2, yb), (2, 12),
        (cx - 6, 16), (cx - 4, 6),
        (cx, 3),
        (cx + 4, 6), (cx + 6, 16),
        (size - 2, 12), (size - 2, yb),
    ]
    pygame.draw.polygon(s, GOLD, prong_pts)
    pygame.draw.polygon(s, LTYELLOW, prong_pts, 2)
    # Base band
    pygame.draw.rect(s, (185, 150, 40), (2, yb - 7, size - 4, 7))
    pygame.draw.rect(s, LTYELLOW, (2, yb - 7, size - 4, 7), 1)
    # Three gems on band
    for gx in (cx - 7, cx, cx + 7):
        pygame.draw.circle(s, (220, 50, 50), (gx, yb - 3), 2)
    return s


def draw_placed_wall(size=TILE):
    """Player-placed block — distinct from level walls"""
    s = _surf(size, alpha=False)
    s.fill((30, 30, 80))
    pygame.draw.rect(s, (60, 60, 150), (2, 2, size - 4, size - 4))
    pygame.draw.rect(s, (100, 100, 200), (2, 2, size - 4, size - 4), 2)
    pygame.draw.line(s, (140, 140, 220), (4, 4), (8, 4), 1)
    return s


def draw_shield_overlay(size=TILE):
    """Semi-transparent blue glow drawn over the player when shielded."""
    s = _surf(size)
    cx, cy = size // 2, size // 2
    r = size // 2 - 1
    pygame.draw.circle(s, (80, 150, 255, 90), (cx, cy), r)
    pygame.draw.circle(s, (150, 200, 255, 180), (cx, cy), r, 2)
    return s


def create_sprites():
    return {
        'border_wall':   draw_border_wall(),
        'wall':          draw_wall(),
        'placed_wall':   draw_placed_wall(),
        'crack1':        draw_damage_cracks(1),
        'crack2':        draw_damage_cracks(2),
        'floor':         draw_floor(),
        'player':        draw_player(),
        'enemy':         draw_enemy(),
        'boss_0':        draw_boss(0),
        'boss_1':        draw_boss(1),
        'boss_2':        draw_boss(2),
        'boss_3':        draw_boss(3),
        'shield':        draw_shield_overlay(),
        1:               draw_coin(),
        2:               draw_big_diamond(),
        3:               draw_small_gems(),
        4:               draw_trophy(),
        5:               draw_gold_bar(),
        6:               draw_silver_bar(),
        7:               draw_necklace(),
        8:               draw_lamp(),
        9:               draw_big_gem(),
        10:              draw_crown(),
    }
