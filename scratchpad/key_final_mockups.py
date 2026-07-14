"""BL-56 HUD key stack — EXACT spec from Daniel.

for index in range(total_keys):
    pos = (index*2, index*2)
    if total_keys - held_keys > index:
        draw GHOST key   # blended 15% against background colour, FULL ALPHA (opaque)
    else:
        draw NORMAL key
(no rim; opaque keys occlude cleanly; higher index drawn later = on top)
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from constants import TILE, HUD_BG
from crafting import KEY_COLORS
import sprites

ICON = 20
SLOT = 23
ROW_H = 28
GHOST_MIX = 0.15          # 15% of the way from bg toward the key colour
RIM = (12, 10, 8)         # 1px dark rim, as in diag-dr-2
OUT = os.path.join(os.path.dirname(__file__), "keymock")
os.makedirs(OUT, exist_ok=True)


def _outline(body, size):
    """Add a 1px dark rim around `body` (a size x size key surface)."""
    mask = pygame.mask.from_surface(body)
    sil = mask.to_surface(setcolor=(*RIM, 255), unsetcolor=(0, 0, 0, 0))
    out = pygame.Surface((size + 2, size + 2), pygame.SRCALPHA)
    for ox in (-1, 0, 1):
        for oy in (-1, 0, 1):
            out.blit(sil, (1 + ox, 1 + oy))
    out.blit(body, (1, 1))
    return out


def normal_key(colour, size=ICON):
    key = pygame.transform.smoothscale(
        sprites.draw_key_pickup(colour, size=TILE), (size, size))
    return _outline(key, size)


def ghost_key(colour, size=ICON):
    """Opaque key in a colour blended 15% (key) / 85% (HUD_BG), full alpha,
    with the same 1px dark rim as the normal key.

    Build an opaque bg-coloured silhouette of the key shape, then blit the
    key over it at 15% alpha -> per-pixel = 0.85*bg + 0.15*key, alpha = shape.
    """
    key = pygame.transform.smoothscale(
        sprites.draw_key_pickup(colour, size=TILE), (size, size))
    mask = pygame.mask.from_surface(key)
    sil = mask.to_surface(setcolor=(*HUD_BG, 255), unsetcolor=(0, 0, 0, 0))
    faint = key.copy()
    faint.fill((255, 255, 255, int(255 * GHOST_MIX)), None, pygame.BLEND_RGBA_MULT)
    sil.blit(faint, (0, 0))
    return _outline(sil, size)


def compose(colour, total, held, footprint=SLOT, height=ROW_H):
    lit = normal_key(colour)
    dim = ghost_key(colour)
    iw, ih = lit.get_size()
    span = 2 * (total - 1)
    tw, th = iw + span, ih + span
    canvas = pygame.Surface((max(footprint, tw), max(height, th)), pygame.SRCALPHA)
    x0 = (canvas.get_width() - tw) // 2
    y0 = (canvas.get_height() - th) // 2
    for index in range(total):
        is_ghost = (total - held) > index
        canvas.blit(dim if is_ghost else lit, (x0 + index * 2, y0 + index * 2))
    return canvas


SCALE = 14
BLUE = KEY_COLORS['blue']
PAD = 10


def big(s, sc=SCALE):
    return pygame.transform.scale(s, (s.get_width() * sc, s.get_height() * sc))


def build_sheet():
    font = pygame.font.SysFont("dejavusansmono", 18)
    totals = [1, 2, 3, 4]
    max_cols = 5
    cell_w = SLOT * SCALE + PAD
    cell_h = ROW_H * SCALE + PAD
    LABEL = 150
    W = LABEL + max_cols * cell_w + PAD
    H = 34 + len(totals) * cell_h
    sheet = pygame.Surface((W, H))
    sheet.fill(HUD_BG)
    for j in range(max_cols):
        sheet.blit(font.render(f"held {j}", True, (255, 200, 100)),
                   (LABEL + j * cell_w + cell_w // 2 - 24, 8))
    for i, total in enumerate(totals):
        y = 34 + i * cell_h
        sheet.blit(font.render(f"total {total}", True, (230, 230, 230)),
                   (6, y + cell_h // 2 - 10))
        for held in range(total + 1):
            b = big(compose(BLUE, total, held))
            slot_px = SLOT * SCALE
            ox = LABEL + held * cell_w + (cell_w - slot_px) // 2
            pygame.draw.rect(sheet, (40, 40, 55), (ox, y, slot_px, ROW_H * SCALE), 1)
            x = LABEL + held * cell_w + (cell_w - b.get_width()) // 2
            sheet.blit(b, (x, y + (ROW_H * SCALE - b.get_height()) // 2))
    pygame.image.save(sheet, os.path.join(OUT, "sheet_final.png"))
    print("wrote sheet_final.png", sheet.get_size())


def build_context():
    colours = list(KEY_COLORS.items())
    states = [(1, 0), (2, 1), (3, 1), (4, 2), (2, 2), (1, 1), (3, 0)]
    strip = pygame.Surface((len(colours) * SLOT + 8, ROW_H), pygame.SRCALPHA)
    strip.fill(HUD_BG)
    for k, ((cname, rgb), (tot, held)) in enumerate(zip(colours, states)):
        comp = compose(rgb, tot, held)
        x = 4 + k * SLOT + (SLOT - comp.get_width()) // 2
        y = (ROW_H - comp.get_height()) // 2
        strip.blit(comp, (x, y))
    pygame.image.save(big(strip, 8), os.path.join(OUT, "hud_final_context.png"))
    print("wrote hud_final_context.png  states:", states)


if __name__ == "__main__":
    build_sheet()
    build_context()
    print("done ->", OUT)
