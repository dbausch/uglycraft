"""Diagnostic: render held vs ghost in DISTINCT hues to see actual positions.

held  = bright GREEN
ghost = dim RED
Two orderings, so we can see which the current code produces and which we want.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from constants import TILE, HUD_BG
import sprites

ICON = 20
RIM = (12, 10, 8)
GHOST_ALPHA = 70
DX, DY = 2, 2
GREEN = (60, 220, 90)
RED = (230, 70, 70)
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


def compose_current(total, held):
    """EXACT logic from key_ghost_mockups.compose (held = high indices)."""
    lit = key_icon(GREEN, ghost=False)
    dim = key_icon(RED, ghost=True)
    iw, ih = lit.get_size()
    span = 2 * (total - 1)
    tw, th = iw + span, ih + span
    canvas = pygame.Surface((tw + 8, th + 8), pygame.SRCALPHA)
    x0 = y0 = 4
    n_ghost = total - held
    for i in range(total):
        canvas.blit(dim if i < n_ghost else lit, (x0 + i * DX, y0 + i * DY))
    return canvas


def compose_wanted(total, held):
    """Held on TOP at the up-left/front; ghosts fan behind toward bottom-right.
    Paint back(bottom-right)->front(top-left): ghosts first, held last on top."""
    lit = key_icon(GREEN, ghost=False)
    dim = key_icon(RED, ghost=True)
    iw, ih = lit.get_size()
    span = 2 * (total - 1)
    tw, th = iw + span, ih + span
    canvas = pygame.Surface((tw + 8, th + 8), pygame.SRCALPHA)
    x0 = y0 = 4
    n_ghost = total - held
    # positions: i=0 top-left ... i=total-1 bottom-right
    # held occupy top-left positions [0, held); ghosts occupy [held, total)
    # paint bottom-right first (ghosts), then top-left (held) -> held on top
    for i in reversed(range(total)):
        is_held = i < held
        canvas.blit(lit if is_held else dim, (x0 + i * DX, y0 + i * DY))
    return canvas


SCALE = 18


def big(s, sc=SCALE):
    return pygame.transform.scale(s, (s.get_width() * sc, s.get_height() * sc))


def main():
    font = pygame.font.SysFont("dejavusansmono", 20)
    states = [(2, 1), (3, 1), (4, 2)]
    cols = [("CURRENT code", compose_current),
            ("WANTED? held up-left/front", compose_wanted)]
    cell = 34 * SCALE
    LABEL = 90
    W = LABEL + len(cols) * (cell + 20)
    H = 50 + len(states) * (cell + 10)
    sheet = pygame.Surface((W, H))
    sheet.fill(HUD_BG)
    hint = font.render("held=GREEN  ghost=dim RED", True, (200, 200, 200))
    sheet.blit(hint, (LABEL, 6))
    for j, (name, _) in enumerate(cols):
        t = font.render(name, True, (255, 200, 100))
        sheet.blit(t, (LABEL + j * (cell + 20), 28))
    for r, (tot, held) in enumerate(states):
        y = 52 + r * (cell + 10)
        sheet.blit(font.render(f"{held}/{tot}", True, (230, 230, 230)), (6, y + cell // 2))
        for j, (_, fn) in enumerate(cols):
            b = big(fn(tot, held))
            x = LABEL + j * (cell + 20)
            sheet.blit(b, (x, y))
    pygame.image.save(sheet, os.path.join(OUT, "order_diag.png"))
    print("wrote order_diag.png", sheet.get_size())


if __name__ == "__main__":
    main()
