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


def draw_reinforced_wall(size=TILE):
    """Indestructible interior wall — dark stone with rivets, heavier than brick."""
    s = _surf(size, alpha=False)
    s.fill((35, 35, 48))
    mid = size // 2
    for row_y, offset in ((1, 0), (mid + 1, mid // 3)):
        bh = mid - 2
        for bx, bw in ((1 + offset, mid - 2), (mid + offset, size - mid - 2)):
            bx = bx % (size - 2) + 1
            pygame.draw.rect(s, (58, 58, 78), (bx, row_y, min(bw, size - bx - 1), bh))
            pygame.draw.line(s, (78, 78, 100), (bx, row_y), (bx + min(bw, 8), row_y))
            pygame.draw.line(s, (78, 78, 100), (bx, row_y), (bx, row_y + 2))
            pygame.draw.line(s, (25, 25, 35),
                             (bx, row_y + bh - 1), (bx + min(bw, size - bx - 1), row_y + bh - 1))
    for rx, ry in ((4, 4), (size - 6, 4), (4, size - 6), (size - 6, size - 6)):
        pygame.draw.circle(s, (90, 90, 110), (rx, ry), 2)
        pygame.draw.circle(s, (45, 45, 60), (rx, ry), 2, 1)
    return s


def draw_wooden_wall(size=TILE):
    """Breakable wooden wall — brown planks, easier to break than stone."""
    s = _surf(size, alpha=False)
    s.fill((80, 45, 15))
    plank_h = size // 4
    for i in range(4):
        y = i * plank_h
        shade = 10 if i % 2 == 0 else -10
        color = (90 + shade, 50 + shade, 18 + shade // 2)
        pygame.draw.rect(s, color, (1, y + 1, size - 2, plank_h - 2))
        pygame.draw.line(s, (110, 65, 25), (1, y + 1), (size - 2, y + 1), 1)
        pygame.draw.line(s, (55, 30, 8), (1, y + plank_h - 1), (size - 2, y + plank_h - 1), 1)
    for nx, ny in ((6, size // 4), (size - 8, size * 3 // 4)):
        pygame.draw.circle(s, (55, 30, 10), (nx, ny), 3)
        pygame.draw.circle(s, (70, 40, 15), (nx, ny), 2)
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


def draw_ogre_1(size=TILE):
    """Normal enemy type 1 (levels 1–3): simple green ogre, no horns."""
    s = _surf(size)

    skin = (72, 152, 48)
    dark = (44, 96, 26)

    # Ears (drawn before head so head overlaps cleanly)
    for ex in (5, 27):
        pygame.draw.circle(s, skin, (ex, 14), 4)
        pygame.draw.circle(s, dark, (ex, 14), 2)

    # Head
    pygame.draw.rect(s, skin, (6, 4, 20, 22), border_radius=5)
    pygame.draw.rect(s, dark, (6, 4, 20, 22), 1, border_radius=5)

    # Brow ridge
    pygame.draw.rect(s, dark, (6, 9, 20, 3))

    # Eyes — white with black pupils and a shine dot
    for ex in (12, 20):
        pygame.draw.circle(s, WHITE, (ex, 12), 3)
        pygame.draw.circle(s, (20, 20, 20), (ex, 12), 2)
        pygame.draw.circle(s, WHITE, (ex - 1, 11), 1)

    # Flat nose with two nostrils
    pygame.draw.rect(s, dark, (13, 16, 6, 3), border_radius=1)
    pygame.draw.circle(s, (30, 70, 15), (14, 17), 1)
    pygame.draw.circle(s, (30, 70, 15), (18, 17), 1)

    # Mouth with two teeth
    pygame.draw.rect(s, (15, 10, 5), (8, 21, 16, 5), border_radius=2)
    pygame.draw.line(s, WHITE, (11, 21), (11, 24), 2)
    pygame.draw.line(s, WHITE, (20, 21), (20, 24), 2)
    pygame.draw.line(s, dark,  (9,  23), (23, 23), 1)

    return s


def draw_ogre_2(size=TILE):
    """Normal enemy type 2 (levels 4–6): orange ogre with small horns and wide grin."""
    s = _surf(size)

    skin = (200, 95, 28)
    dark = (130, 55, 10)
    horn = (90, 55, 20)

    # Horns
    pygame.draw.polygon(s, horn, [(10, 5), (8,  1), (14, 5)])
    pygame.draw.polygon(s, horn, [(22, 5), (18, 1), (24, 5)])
    pygame.draw.line(s, (130, 80, 30), (9, 4), (11, 5), 1)
    pygame.draw.line(s, (130, 80, 30), (21, 5), (23, 4), 1)

    # Pointed ears
    pygame.draw.polygon(s, skin, [(3, 10), (2, 17), (7, 13)])
    pygame.draw.polygon(s, skin, [(29, 10), (30, 17), (25, 13)])

    # Head
    pygame.draw.rect(s, skin, (5, 4, 22, 22), border_radius=4)
    pygame.draw.rect(s, dark, (5, 4, 22, 22), 1, border_radius=4)

    # Angled brow (angry V-shape)
    pygame.draw.polygon(s, dark, [(5, 9), (14, 12), (27, 9), (27, 11), (14, 14), (5, 11)])

    # Eyes — yellow irises, small dark pupils
    for ex in (12, 20):
        pygame.draw.ellipse(s, (235, 195, 20), (ex - 3, 13, 6, 4))
        pygame.draw.circle(s, (15, 8, 3), (ex, 15), 1)

    # Flat nose
    pygame.draw.rect(s, dark, (12, 17, 8, 4), border_radius=1)
    pygame.draw.circle(s, (100, 45, 8), (14, 19), 1)
    pygame.draw.circle(s, (100, 45, 8), (18, 19), 1)

    # Wide grin with row of teeth and side tusks
    pygame.draw.rect(s, (15, 8, 3), (5, 22, 22, 6), border_radius=2)
    for tx in (8, 11, 14, 17, 20, 23):
        pygame.draw.rect(s, WHITE, (tx, 22, 2, 3))
    pygame.draw.polygon(s, (230, 220, 195), [(5, 22), (8, 22), (6, 27)])
    pygame.draw.polygon(s, (230, 220, 195), [(24, 22), (27, 22), (25, 27)])

    return s


def draw_ogre_3(size=TILE):
    """Normal enemy type 3 (levels 7–9): purple ogre, war paint, large horns, red eyes."""
    s = _surf(size)

    skin = (118, 44, 158)
    dark = (68, 18, 98)
    horn = (65, 42, 18)

    # Large horns
    pygame.draw.polygon(s, horn, [(9, 5), (5,  1), (13, 5)])
    pygame.draw.polygon(s, horn, [(23, 5), (19, 1), (27, 5)])
    pygame.draw.line(s, (100, 68, 28), (6, 3), (10, 5), 1)
    pygame.draw.line(s, (100, 68, 28), (22, 5), (26, 3), 1)

    # Ears with inner colour
    for ex in (4, 28):
        pygame.draw.circle(s, skin, (ex, 15), 5)
        pygame.draw.circle(s, (180, 110, 205), (ex, 15), 2)

    # Head (wider)
    pygame.draw.rect(s, skin, (4, 4, 24, 22), border_radius=4)
    pygame.draw.rect(s, dark, (4, 4, 24, 22), 1, border_radius=4)

    # Heavy brow
    pygame.draw.rect(s, dark, (4, 8, 24, 5))

    # War-paint diagonal slashes on cheeks
    pygame.draw.line(s, (210, 35, 35), (6,  15), (9,  20), 2)
    pygame.draw.line(s, (210, 35, 35), (22, 15), (25, 20), 2)

    # Glowing red eyes
    for ex in (12, 20):
        pygame.draw.circle(s, (255, 55, 25), (ex, 14), 3)
        pygame.draw.circle(s, (255, 175, 50), (ex, 14), 1)

    # Flat nose
    pygame.draw.rect(s, dark, (11, 18, 10, 4), border_radius=1)
    pygame.draw.circle(s, (58, 15, 80), (13, 20), 1)
    pygame.draw.circle(s, (58, 15, 80), (19, 20), 1)

    # Snarling mouth with teeth and large tusks
    pygame.draw.rect(s, (10, 4, 15), (4, 23, 24, 5), border_radius=2)
    for tx in (7, 10, 13, 17, 20, 23):
        pygame.draw.rect(s, WHITE, (tx, 23, 2, 2))
    pygame.draw.polygon(s, (230, 220, 195), [(4, 23), (8, 23), (5, 29)])
    pygame.draw.polygon(s, (230, 220, 195), [(24, 23), (28, 23), (27, 29)])

    return s


def draw_boss_ogre(phase=0, size=TILE):
    """Boss enemy (level 10): armoured dark-red ogre, animated glowing eyes and mouth."""
    s = _surf(size)
    cx = size // 2

    skin  = (155, 18, 18)
    dark  = (85,   6,  6)
    armor = (78,  78, 92)
    crown = GOLD

    # Gold triple-pronged crown
    pygame.draw.polygon(s, crown, [(cx - 8, 4), (cx - 6, 0), (cx - 4, 4)])
    pygame.draw.polygon(s, crown, [(cx - 2, 4), (cx,     0), (cx + 2, 4)])
    pygame.draw.polygon(s, crown, [(cx + 4, 4), (cx + 6, 0), (cx + 8, 4)])
    pygame.draw.rect(s, crown, (cx - 8, 3, 16, 3))
    pygame.draw.line(s, LTYELLOW, (cx - 8, 3), (cx + 8, 3), 1)

    # Shoulder armour plates (drawn before head)
    pygame.draw.ellipse(s, armor, ( 0, 20, 10, 10))
    pygame.draw.ellipse(s, armor, (22, 20,  9, 10))
    pygame.draw.ellipse(s, (115, 115, 135), ( 0, 20, 10, 10), 1)
    pygame.draw.ellipse(s, (115, 115, 135), (22, 20,  9, 10), 1)

    # Ears
    for ex in (4, 28):
        pygame.draw.circle(s, skin, (ex, 15), 4)

    # Head
    pygame.draw.rect(s, skin, (4, 4, 24, 22), border_radius=3)
    pygame.draw.rect(s, dark, (4, 4, 24, 22), 1, border_radius=3)

    # Armoured brow plate
    pygame.draw.rect(s, armor, (4, 8, 24, 5))
    pygame.draw.rect(s, (115, 115, 135), (4, 8, 24, 5), 1)

    # Facial scar
    pygame.draw.line(s, (80, 5, 5), (10, 10), (18, 20), 1)

    # Animated eyes — size and colour cycle across phases
    eye_radii  = (3, 4, 3, 4)
    eye_colors = [(255, 70, 20), (255, 160, 30), (220, 40, 10), (255, 230, 60)]
    er = eye_radii[phase]
    ec = eye_colors[phase]
    glow = pygame.Surface((size, size), pygame.SRCALPHA)
    for ex in (12, 20):
        pygame.draw.circle(glow, (*ec, 90), (ex, 14), er + 3)
    s.blit(glow, (0, 0))
    for ex in (12, 20):
        pygame.draw.circle(s, ec, (ex, 14), er)
        pygame.draw.circle(s, WHITE, (ex - 1, 13), max(1, er - 2))

    # Nose
    pygame.draw.rect(s, dark, (12, 18, 8, 4), border_radius=1)
    pygame.draw.circle(s, (70, 4, 4), (14, 20), 1)
    pygame.draw.circle(s, (70, 4, 4), (18, 20), 1)

    # Animated mouth: open on phases 1 and 3
    mouth_open = phase in (1, 3)
    pygame.draw.rect(s, (8, 2, 2), (4, 22, 24, 7 if mouth_open else 5), border_radius=2)
    if mouth_open:
        for tx in (7, 10, 13, 17, 20, 23):
            pygame.draw.rect(s, WHITE, (tx, 22, 2, 3))
        for tx in (8, 12, 16, 20):
            pygame.draw.rect(s, (210, 200, 180), (tx, 26, 2, 3))
    else:
        for tx in (8, 12, 16, 20):
            pygame.draw.rect(s, WHITE, (tx, 22, 2, 3))
    pygame.draw.polygon(s, (235, 225, 200), [(4, 22), (8, 22), (5, 28)])
    pygame.draw.polygon(s, (235, 225, 200), [(24, 22), (28, 22), (27, 28)])

    return s


# ── Treasure sprites ──────────────────────────────────────────────────────────

def draw_coin(size=TILE):
    """item_no=1: flat gold coin with small engraved profile and rim legend marks"""
    s = _surf(size)
    cx, cy = size // 2, size // 2
    r = 10   # coin radius

    # Shiny outer rim — drawn first so the coin face sits on top
    outer_r = r + 2
    pygame.draw.circle(s, (242, 205, 60), (cx, cy), outer_r)    # bright gold fill
    pygame.draw.circle(s, (148, 108, 14), (cx, cy), outer_r, 1) # dark outer boundary

    # Flat disc
    pygame.draw.circle(s, GOLD, (cx, cy), r - 1)               # face
    pygame.draw.circle(s, (250, 215, 75), (cx, cy), r - 1, 1)  # bright rim line

    engrave = (128, 92, 12)

    # Engraved "1" centred on the coin face
    pygame.draw.line(s, engrave, (16, 10), (16, 22), 2)  # vertical stroke
    pygame.draw.line(s, engrave, (13, 13), (16, 10), 2)  # top-left serif diagonal
    pygame.draw.line(s, engrave, (13, 22), (19, 22), 2)  # base serif

    # Unreadable legend text: clusters of 1-px marks at radius r-2 (just inside rim)
    rim_r = r - 2
    for a in (
         5, 11, 17, 23,           # word 1
        42, 47, 52, 57, 63,       # word 2
        82, 87, 93,               # word 3
       115, 121, 126, 132, 138,   # word 4
       158, 163, 169,             # word 5
       195, 201, 207, 213,        # word 6
       232, 238, 243, 249,        # word 7
       270, 275, 281,             # word 8
       300, 305, 311, 317, 323,   # word 9
       342, 348, 353,             # word 10
    ):
        rad = math.radians(a)
        pygame.draw.circle(s, engrave,
                           (cx + round(rim_r * math.cos(rad)),
                            cy + round(rim_r * math.sin(rad))), 1)

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
    # Chain: 9 beads along a downward-dipping quadratic bezier arc.
    # Note: the bezier midpoint is at half the control-point offset, so with
    # ym=17 the centre bead actually lands at ~y=11. Bead positions are
    # collected first so we can attach the pendant to the real centre bead.
    n  = 9
    x0, y0 = 4,        6   # left end
    xm, ym = cx,      17   # bezier control point
    x1, y1 = size - 4, 6   # right end
    beads = []
    for i in range(n):
        t  = i / (n - 1)
        bx = int((1 - t) ** 2 * x0 + 2 * (1 - t) * t * xm + t ** 2 * x1)
        by = int((1 - t) ** 2 * y0 + 2 * (1 - t) * t * ym + t ** 2 * y1)
        beads.append((bx, by))
    # Drop string: draw BEFORE beads so the centre bead covers the line's top
    cx_bead, cy_bead = beads[n // 2]
    pendant_top = cy_bead + 4
    pygame.draw.line(s, GOLD, (cx_bead, cy_bead), (cx_bead, pendant_top), 1)
    # Beads on top — centre bead overlaps and hides the string's upper end
    for bx, by in beads:
        pygame.draw.circle(s, GOLD, (bx, by), 2)
        pygame.draw.circle(s, LTYELLOW, (bx - 1, by - 1), 1)
    # Pendant gem: top vertex sits exactly at pendant_top (line's lower end)
    pr = 5
    py = pendant_top + pr
    pts = [(cx_bead, pendant_top), (cx_bead + pr, py),
           (cx_bead, py + pr + 1),  (cx_bead - pr, py)]
    pygame.draw.polygon(s, (200, 60, 220), pts)
    pygame.draw.polygon(s, (240, 150, 255), pts, 1)
    pygame.draw.circle(s, WHITE, (cx_bead - 1, py - 2), 1)
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
    """item_no=9: emerald (large green octagonal gem)"""
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


def draw_patrol_guard(size=TILE):
    """Patrol enemy: ogre with lantern — walks a fixed path, doesn't chase."""
    s = _surf(size)
    skin = (72, 152, 48)
    dark = (44, 96, 26)

    pygame.draw.circle(s, skin, (5, 14), 4)
    pygame.draw.circle(s, dark, (5, 14), 2)
    pygame.draw.circle(s, skin, (27, 14), 4)
    pygame.draw.circle(s, dark, (27, 14), 2)

    pygame.draw.rect(s, skin, (6, 4, 20, 22), border_radius=5)
    pygame.draw.rect(s, dark, (6, 4, 20, 22), 1, border_radius=5)
    pygame.draw.rect(s, dark, (6, 9, 20, 3))

    for ex in (12, 20):
        pygame.draw.circle(s, WHITE, (ex, 12), 3)
        pygame.draw.circle(s, (20, 20, 20), (ex, 12), 2)
        pygame.draw.circle(s, WHITE, (ex - 1, 11), 1)

    pygame.draw.rect(s, dark, (13, 16, 6, 3), border_radius=1)
    pygame.draw.rect(s, (15, 10, 5), (8, 21, 16, 5), border_radius=2)
    pygame.draw.line(s, WHITE, (11, 21), (11, 24), 2)
    pygame.draw.line(s, WHITE, (20, 21), (20, 24), 2)

    # Lantern in hand (right side)
    pygame.draw.rect(s, (40, 40, 15), (25, 18, 5, 8))
    pygame.draw.rect(s, (255, 225, 60), (26, 19, 3, 5))
    pygame.draw.circle(s, (255, 245, 200), (27, 21), 2)

    return s


def draw_rocks_pickup(size=TILE):
    """Material pickup: pile of grey rocks."""
    s = _surf(size)
    for rx, ry, rr in [(10, 20, 5), (18, 18, 6), (14, 24, 4),
                        (22, 22, 4), (8, 16, 3)]:
        pygame.draw.circle(s, (120, 120, 130), (rx, ry), rr)
        pygame.draw.circle(s, (80, 80, 90), (rx, ry), rr, 1)
        pygame.draw.circle(s, (160, 160, 170), (rx - 1, ry - 1), max(1, rr // 2))
    return s


def draw_planks_pickup(size=TILE):
    """Material pickup: stack of brown planks."""
    s = _surf(size)
    for i, y in enumerate([14, 18, 22]):
        shade = 15 * (i % 2)
        color = (140 + shade, 80 + shade, 25)
        pygame.draw.rect(s, color, (6, y, 20, 3))
        pygame.draw.rect(s, (100, 55, 15), (6, y, 20, 3), 1)
    return s


def draw_metal_pickup(size=TILE):
    """Material pickup: silver metal scraps."""
    s = _surf(size)
    for mx, my, mw, mh in [(8, 14, 6, 3), (15, 18, 8, 2),
                             (10, 22, 5, 3), (20, 15, 4, 5)]:
        pygame.draw.rect(s, (170, 170, 185), (mx, my, mw, mh))
        pygame.draw.rect(s, (130, 130, 145), (mx, my, mw, mh), 1)
    return s


def draw_crystal_pickup(size=TILE):
    """Material pickup: glowing blue forge crystal."""
    s = _surf(size)
    cx, cy = size // 2, size // 2 + 2
    pts = [(cx, cy - 8), (cx + 5, cy), (cx, cy + 8), (cx - 5, cy)]
    glow = _surf(size)
    pygame.draw.circle(glow, (60, 120, 255, 60), (cx, cy), 10)
    s.blit(glow, (0, 0))
    pygame.draw.polygon(s, (80, 160, 255), pts)
    pygame.draw.polygon(s, (150, 210, 255), pts, 1)
    pygame.draw.circle(s, WHITE, (cx - 1, cy - 3), 2)
    return s


def draw_key_pickup(color, size=TILE):
    """Floor pickup: coloured key."""
    s = _surf(size)
    cx, cy = size // 2, size // 2
    # Key head (circle)
    pygame.draw.circle(s, color, (cx, cy - 4), 7)
    pygame.draw.circle(s, (0, 0, 0, 0), (cx, cy - 4), 3)
    pygame.draw.circle(s, color, (cx, cy - 4), 7, 2)
    # Key shaft
    pygame.draw.rect(s, color, (cx - 1, cy + 2, 3, 12))
    # Key teeth
    pygame.draw.rect(s, color, (cx + 2, cy + 8, 4, 2))
    pygame.draw.rect(s, color, (cx + 2, cy + 12, 3, 2))
    # Shine
    bright = tuple(min(255, c + 80) for c in color)
    pygame.draw.circle(s, bright, (cx - 2, cy - 6), 2)
    return s


def draw_locked_door(color, size=TILE):
    """Wall tile: locked door with coloured indicator."""
    s = _surf(size, alpha=False)
    s.fill((50, 40, 30))
    # Door panels
    pygame.draw.rect(s, (90, 70, 45), (3, 2, size // 2 - 4, size - 4), border_radius=2)
    pygame.draw.rect(s, (90, 70, 45), (size // 2 + 1, 2, size // 2 - 4, size - 4), border_radius=2)
    # Frame
    pygame.draw.rect(s, (120, 95, 55), (1, 0, size - 2, size), 2)
    pygame.draw.line(s, (120, 95, 55), (size // 2, 0), (size // 2, size), 1)
    # Coloured lock plate
    lx, ly = size // 2 - 5, size // 2 - 4
    pygame.draw.rect(s, color, (lx, ly, 10, 8), border_radius=2)
    # Keyhole
    pygame.draw.circle(s, (20, 15, 10), (size // 2, ly + 3), 2)
    pygame.draw.rect(s, (20, 15, 10), (size // 2 - 1, ly + 4, 2, 3))
    return s


def draw_pressure_plate(size=TILE):
    """Floor tile with a pressure plate."""
    s = _surf(size, alpha=False)
    s.fill((8, 8, 12))  # floor base
    m = 6
    pygame.draw.rect(s, (60, 55, 45), (m, m, size - 2 * m, size - 2 * m), border_radius=2)
    pygame.draw.rect(s, (80, 75, 60), (m, m, size - 2 * m, size - 2 * m), 1, border_radius=2)
    pygame.draw.rect(s, (50, 45, 35), (m + 2, m + 2, size - 2 * m - 4, size - 2 * m - 4))
    return s


def draw_gate_closed(size=TILE):
    """Gate (portcullis) — closed state, acts as wall."""
    s = _surf(size, alpha=False)
    s.fill((20, 20, 28))
    bar_color = (100, 90, 70)
    # Vertical bars
    for bx in range(4, size - 2, 6):
        pygame.draw.line(s, bar_color, (bx, 0), (bx, size), 2)
    # Horizontal bars
    for by in range(4, size - 2, 8):
        pygame.draw.line(s, bar_color, (0, by), (size, by), 1)
    # Rivets at intersections
    for bx in range(4, size - 2, 6):
        for by in range(4, size - 2, 8):
            pygame.draw.circle(s, (130, 120, 95), (bx, by), 1)
    return s


def draw_gate_open(size=TILE):
    """Gate (portcullis) — open state, passable floor with gate remnant at top."""
    s = _surf(size, alpha=False)
    s.fill((8, 8, 12))  # floor
    bar_color = (80, 72, 55)
    # Gate retracted to top 6 pixels
    for bx in range(4, size - 2, 6):
        pygame.draw.line(s, bar_color, (bx, 0), (bx, 5), 2)
    pygame.draw.line(s, bar_color, (0, 4), (size, 4), 1)
    return s


def draw_pushable_block(size=TILE):
    """Pushable block — grey stone, indestructible, player can push."""
    s = _surf(size, alpha=False)
    s.fill((70, 70, 80))
    pygame.draw.rect(s, (95, 95, 108), (2, 2, size - 4, size - 4))
    pygame.draw.rect(s, (120, 120, 135), (2, 2, size - 4, size - 4), 2)
    # Chiselled cross pattern
    mid = size // 2
    pygame.draw.line(s, (75, 75, 88), (4, mid), (size - 4, mid), 1)
    pygame.draw.line(s, (75, 75, 88), (mid, 4), (mid, size - 4), 1)
    # Corner bevels
    pygame.draw.line(s, (140, 140, 155), (3, 3), (10, 3), 1)
    pygame.draw.line(s, (140, 140, 155), (3, 3), (3, 10), 1)
    pygame.draw.line(s, (55, 55, 65), (size - 4, size - 4), (size - 11, size - 4), 1)
    pygame.draw.line(s, (55, 55, 65), (size - 4, size - 4), (size - 4, size - 11), 1)
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


def _icon(surf, icon_size=20):
    """Scale a TILE-sized surface down to icon_size for inventory display."""
    return pygame.transform.smoothscale(surf, (icon_size, icon_size))


def draw_craft_bridge_icon(size=TILE):
    """Craftable item icon: wooden bridge plank."""
    s = _surf(size)
    for i, y in enumerate([10, 15, 20]):
        shade = 12 * (i % 2)
        pygame.draw.rect(s, (130 + shade, 75 + shade, 22), (4, y, 24, 4))
        pygame.draw.rect(s, (90, 50, 12), (4, y, 24, 4), 1)
    pygame.draw.line(s, (100, 55, 15), (8, 8), (8, 24), 2)
    pygame.draw.line(s, (100, 55, 15), (24, 8), (24, 24), 2)
    return s


def draw_craft_bell_icon(size=TILE):
    """Craftable item icon: metal bell / noise lure."""
    s = _surf(size)
    cx = size // 2
    pygame.draw.polygon(s, SILVER, [(cx - 8, 6), (cx + 8, 6),
                                     (cx + 10, 22), (cx - 10, 22)])
    pygame.draw.rect(s, DKSILVER, (cx - 10, 22, 20, 3))
    pygame.draw.circle(s, DKSILVER, (cx, 27), 2)
    pygame.draw.rect(s, (220, 220, 235), (cx - 2, 3, 4, 4), border_radius=1)
    pygame.draw.line(s, (230, 230, 245), (cx - 5, 9), (cx - 3, 18), 1)
    return s


def draw_craft_barricade_icon(size=TILE):
    """Craftable item icon: reinforced barricade (stone + wood frame)."""
    s = _surf(size, alpha=False)
    s.fill((55, 55, 70))
    pygame.draw.rect(s, (100, 55, 18), (2, 2, size - 4, 4))
    pygame.draw.rect(s, (100, 55, 18), (2, size - 6, size - 4, 4))
    pygame.draw.rect(s, (100, 55, 18), (2, 2, 4, size - 4))
    pygame.draw.rect(s, (100, 55, 18), (size - 6, 2, 4, size - 4))
    pygame.draw.rect(s, (80, 80, 100), (6, 6, size - 12, size - 12))
    pygame.draw.line(s, (110, 110, 130), (7, 7), (11, 7), 1)
    return s


def draw_craft_portal_icon(size=TILE):
    """Craftable item icon: portal pair (two linked swirls)."""
    s = _surf(size)
    for cx, cy in ((size // 3, size // 2), (size * 2 // 3, size // 2)):
        pygame.draw.circle(s, (80, 60, 200, 80), (cx, cy), 8)
        pygame.draw.circle(s, (120, 100, 255), (cx, cy), 6, 2)
        pygame.draw.circle(s, (200, 180, 255), (cx, cy), 2)
    pygame.draw.line(s, (120, 100, 255, 140), (size // 3 + 6, size // 2),
                     (size * 2 // 3 - 6, size // 2), 1)
    return s


def draw_craft_compass_icon(size=TILE):
    """Craftable item icon: compass."""
    s = _surf(size)
    cx, cy = size // 2, size // 2
    pygame.draw.circle(s, (50, 50, 60), (cx, cy), 10)
    pygame.draw.circle(s, SILVER, (cx, cy), 10, 2)
    pygame.draw.polygon(s, RED, [(cx, cy - 8), (cx + 3, cy), (cx, cy + 2), (cx - 3, cy)])
    pygame.draw.polygon(s, WHITE, [(cx, cy + 8), (cx + 3, cy), (cx, cy - 2), (cx - 3, cy)])
    pygame.draw.circle(s, GOLD, (cx, cy), 2)
    return s


def draw_tool_hammer_icon(size=TILE):
    """Tool icon: hammer."""
    s = _surf(size)
    pygame.draw.rect(s, (100, 60, 18), (13, 14, 4, 16))
    pygame.draw.rect(s, (140, 140, 155), (8, 6, 16, 10), border_radius=2)
    pygame.draw.rect(s, (170, 170, 185), (8, 6, 16, 10), 1, border_radius=2)
    pygame.draw.line(s, (200, 200, 215), (10, 8), (22, 8), 1)
    return s


def draw_tool_chisel_icon(size=TILE):
    """Tool icon: chisel."""
    s = _surf(size)
    pygame.draw.rect(s, (100, 60, 18), (14, 8, 3, 18))
    pygame.draw.polygon(s, (160, 160, 175), [(12, 6), (19, 6), (17, 8), (14, 8)])
    pygame.draw.polygon(s, (160, 160, 175), [(13, 26), (18, 26), (16, 30), (15, 30)])
    return s


def draw_tool_runestone_icon(size=TILE):
    """Tool icon: runestone."""
    s = _surf(size)
    cx, cy = size // 2, size // 2
    pts = [(cx, 4), (cx + 10, cy + 4), (cx, size - 2), (cx - 10, cy + 4)]
    pygame.draw.polygon(s, (60, 60, 80), pts)
    pygame.draw.polygon(s, (100, 100, 130), pts, 2)
    pygame.draw.line(s, (120, 140, 255), (cx, 10), (cx, 24), 2)
    pygame.draw.line(s, (120, 140, 255), (cx - 5, 16), (cx + 5, 18), 1)
    pygame.draw.line(s, (120, 140, 255), (cx - 4, 22), (cx + 4, 20), 1)
    return s


def create_sprites():
    return {
        'border_wall':   draw_border_wall(),
        'wall':          draw_wall(),
        'wall_reinforced': draw_reinforced_wall(),
        'wall_wooden':   draw_wooden_wall(),
        'placed_wall':   draw_placed_wall(),
        'crack1':        draw_damage_cracks(1),
        'crack2':        draw_damage_cracks(2),
        'floor':         draw_floor(),
        'player':        draw_player(),
        'enemy_1':       draw_ogre_1(),
        'enemy_2':       draw_ogre_2(),
        'enemy_3':       draw_ogre_3(),
        'boss_0':        draw_boss_ogre(0),
        'boss_1':        draw_boss_ogre(1),
        'boss_2':        draw_boss_ogre(2),
        'boss_3':        draw_boss_ogre(3),
        'shield':        draw_shield_overlay(),
        'patrol_guard':  draw_patrol_guard(),
        'mat_rocks':     draw_rocks_pickup(),
        'mat_planks':    draw_planks_pickup(),
        'mat_metal':     draw_metal_pickup(),
        'mat_crystal':   draw_crystal_pickup(),
        # Inventory icons (20×20)
        'icon_rocks':    _icon(draw_rocks_pickup()),
        'icon_planks':   _icon(draw_planks_pickup()),
        'icon_metal':    _icon(draw_metal_pickup()),
        'icon_crystal':  _icon(draw_crystal_pickup()),
        'icon_stone_wall':  _icon(draw_placed_wall()),
        'icon_bridge':      _icon(draw_craft_bridge_icon()),
        'icon_bell':        _icon(draw_craft_bell_icon()),
        'icon_barricade':   _icon(draw_craft_barricade_icon()),
        'icon_portal_pair': _icon(draw_craft_portal_icon()),
        'icon_compass':     _icon(draw_craft_compass_icon()),
        'key_red':       draw_key_pickup((220, 50, 50)),
        'key_blue':      draw_key_pickup((80, 140, 255)),
        'key_green':     draw_key_pickup((60, 200, 80)),
        'door_red':      draw_locked_door((220, 50, 50)),
        'door_blue':     draw_locked_door((80, 140, 255)),
        'door_green':    draw_locked_door((60, 200, 80)),
        'pushable_block': draw_pushable_block(),
        'pressure_plate': draw_pressure_plate(),
        'gate_closed':    draw_gate_closed(),
        'gate_open':      draw_gate_open(),
        'icon_key_red':  _icon(draw_key_pickup((220, 50, 50))),
        'icon_key_blue': _icon(draw_key_pickup((80, 140, 255))),
        'icon_key_green':_icon(draw_key_pickup((60, 200, 80))),
        'icon_hammer':      _icon(draw_tool_hammer_icon()),
        'icon_chisel':      _icon(draw_tool_chisel_icon()),
        'icon_runestone':   _icon(draw_tool_runestone_icon()),
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
