"""BL-56 HUD: diag-dr-2 stack with held/ghost states.

Stack of `total` keys of one colour (total = #doors of that colour in the
level). `held` of them are lit (currently in inventory); the rest are ghosted
(~15% alpha, like the spec-0071 collect tracker). Lit keys are drawn in FRONT
(bottom-right, most visible); ghosts recede behind (top-left).

Outputs to scratchpad/keymock/:
  sheet_ghost.png        grid: total 1..4 (rows) x held 0..total (cols)
  hud_ghost_context.png  a realistic HUD strip, 7 colours, mixed total/held
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
RIM = (12, 10, 8)
GHOST_ALPHA = 48    # a touch above the live 38 so the rim stays visible
DX, DY = 2, 2       # diag-dr-2

OUT = os.path.join(os.path.dirname(__file__), "keymock")
os.makedirs(OUT, exist_ok=True)


def key_icon(colour, size=ICON, ghost=False):
    base = sprites.draw_key_pickup(colour, size=TILE)
    key = pygame.transform.smoothscale(base, (size, size))
    mask = pygame.mask.from_surface(key)
    sil = mask.to_surface(setcolor=(*RIM, 255), unsetcolor=(0, 0, 0, 0))
    out = pygame.Surface((size + 2, size + 2), pygame.SRCALPHA)
    for ox in (-1, 0, 1):
        for oy in (-1, 0, 1):
            out.blit(sil, (1 + ox, 1 + oy))
    out.blit(key, (1, 1))
    if ghost:
        out.fill((255, 255, 255, GHOST_ALPHA), None, pygame.BLEND_RGBA_MULT)
    return out


def compose(colour, total, held, dx=DX, dy=DY, footprint=SLOT, height=ROW_H):
    """total keys; the front `held` are lit, the back `total-held` ghosted."""
    lit = key_icon(colour, ICON, ghost=False)
    dim = key_icon(colour, ICON, ghost=True)
    iw, ih = lit.get_size()
    span_x, span_y = abs(dx) * (total - 1), abs(dy) * (total - 1)
    total_w, total_h = iw + span_x, ih + span_y
    canvas = pygame.Surface((max(footprint, total_w), max(height, total_h)),
                            pygame.SRCALPHA)
    cw, ch = canvas.get_size()
    x0, y0 = (cw - total_w) // 2, (ch - total_h) // 2
    n_ghost = total - held
    for i in range(total):      # i=0 back (top-left), i=total-1 front (btm-right)
        px = x0 + (i * dx if dx >= 0 else span_x + i * dx)
        py = y0 + (i * dy if dy >= 0 else span_y + i * dy)
        canvas.blit(dim if i < n_ghost else lit, (px, py))
    return canvas


SCALE = 14
BLUE = KEY_COLORS['blue']
PAD = 10


def big(surf, scale=SCALE):
    w, h = surf.get_size()
    return pygame.transform.scale(surf, (w * scale, h * scale))


def build_sheet():
    font = pygame.font.SysFont("dejavusansmono", 18)
    totals = [1, 2, 3, 4]
    max_cols = 5   # held 0..4
    cell_w = SLOT * SCALE + PAD
    cell_h = ROW_H * SCALE + PAD
    LABEL_W = 150
    W = LABEL_W + max_cols * cell_w + PAD
    H = 34 + len(totals) * cell_h
    sheet = pygame.Surface((W, H))
    sheet.fill(HUD_BG)
    for j in range(max_cols):
        t = font.render(f"held {j}", True, (255, 200, 100))
        sheet.blit(t, (LABEL_W + j * cell_w + cell_w // 2 - 24, 8))
    for i, total in enumerate(totals):
        y = 34 + i * cell_h
        t = font.render(f"total {total}", True, (230, 230, 230))
        sheet.blit(t, (6, y + cell_h // 2 - 10))
        for held in range(total + 1):
            comp = compose(BLUE, total, held)
            b = big(comp)
            slot_px = SLOT * SCALE
            ox = LABEL_W + held * cell_w + (cell_w - slot_px) // 2
            pygame.draw.rect(sheet, (40, 40, 55),
                             (ox, y, slot_px, ROW_H * SCALE), 1)
            x = LABEL_W + held * cell_w + (cell_w - b.get_width()) // 2
            sheet.blit(b, (x, y + (ROW_H * SCALE - b.get_height()) // 2))
    pygame.image.save(sheet, os.path.join(OUT, "sheet_ghost.png"))
    print("wrote sheet_ghost.png", sheet.get_size())


def build_context():
    colours = list(KEY_COLORS.items())
    # (total, held) per colour: a mid-game snapshot
    states = [(1, 0), (2, 1), (3, 1), (4, 2), (2, 2), (1, 1), (3, 0)]
    strip = pygame.Surface((len(colours) * SLOT + 8, ROW_H), pygame.SRCALPHA)
    strip.fill(HUD_BG)
    for k, ((cname, rgb), (tot, held)) in enumerate(zip(colours, states)):
        comp = compose(rgb, tot, held)
        x = 4 + k * SLOT + (SLOT - comp.get_width()) // 2
        y = (ROW_H - comp.get_height()) // 2
        strip.blit(comp, (x, y))
    pygame.image.save(big(strip, 8), os.path.join(OUT, "hud_ghost_context.png"))
    print("wrote hud_ghost_context.png  states:", states)


if __name__ == "__main__":
    build_sheet()
    build_context()
    print("done ->", OUT)
