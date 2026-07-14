"""Compare stacking order for held vs ghost keys (diag-dr-2).

Four orderings, so we can pick the right one:
  A lit-front  : held keys drawn in FRONT (bottom-right), ghosts behind  [current]
  B lit-back   : held keys drawn in BACK (top-left), ghosts in front
  C fill-front : same as A but ghost/lit assignment reversed end
  D lit-front-revdraw : held front but draw front-to-back (ghost on top)

We really just need the two axes: which END is lit, and which is drawn on top.
So render 2 columns x a few states.
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
GHOST_ALPHA = 48
DX, DY = 2, 2
OUT = os.path.join(os.path.dirname(__file__), "keymock")


def key_icon(colour, ghost=False, size=ICON):
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


def compose(colour, total, held, lit_at_front):
    """lit_at_front=True: held keys occupy the FRONT (last-drawn) positions.
    lit_at_front=False: held keys occupy the BACK (first-drawn) positions,
    so ghosts are drawn on top (in front)."""
    lit = key_icon(colour, ghost=False)
    dim = key_icon(colour, ghost=True)
    iw, ih = lit.get_size()
    span = 2 * (total - 1)
    tw, th = iw + span, ih + span
    canvas = pygame.Surface((max(SLOT, tw), max(ROW_H, th)), pygame.SRCALPHA)
    cw, ch = canvas.get_size()
    x0, y0 = (cw - tw) // 2, (ch - th) // 2
    n_ghost = total - held
    for i in range(total):          # i=0 back(top-left) -> i=total-1 front
        if lit_at_front:
            is_ghost = i < n_ghost
        else:
            is_ghost = i >= held
        canvas.blit(dim if is_ghost else lit, (x0 + i * DX, y0 + i * DY))
    return canvas


SCALE = 16
BLUE = KEY_COLORS['blue']
PAD = 12


def big(s, sc=SCALE):
    return pygame.transform.scale(s, (s.get_width() * sc, s.get_height() * sc))


def main():
    font = pygame.font.SysFont("dejavusansmono", 18)
    states = [(2, 1), (3, 1), (4, 2), (4, 1), (3, 2)]
    cols = [("A: held in FRONT (current)", True),
            ("B: held in BACK, ghost in front", False)]
    cell_w = SLOT * SCALE + PAD
    cell_h = ROW_H * SCALE + PAD
    LABEL = 90
    W = LABEL + len(cols) * cell_w + PAD
    H = 40 + len(states) * cell_h
    sheet = pygame.Surface((W, H))
    sheet.fill(HUD_BG)
    for j, (name, _) in enumerate(cols):
        t = font.render(name, True, (255, 200, 100))
        sheet.blit(t, (LABEL + j * cell_w + 10, 10))
    for i, (tot, held) in enumerate(states):
        y = 40 + i * cell_h
        t = font.render(f"{held}/{tot}", True, (230, 230, 230))
        sheet.blit(t, (8, y + cell_h // 2 - 10))
        for j, (_, lf) in enumerate(cols):
            comp = compose(BLUE, tot, held, lf)
            b = big(comp)
            x = LABEL + j * cell_w + (cell_w - b.get_width()) // 2
            sheet.blit(b, (x, y + (cell_h - PAD - b.get_height()) // 2))
    pygame.image.save(sheet, os.path.join(OUT, "order_compare.png"))
    print("wrote order_compare.png", sheet.get_size())


if __name__ == "__main__":
    main()
