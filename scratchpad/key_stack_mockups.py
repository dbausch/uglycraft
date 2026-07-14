"""BL-56 HUD: mock-ups for stacked multi-key icons (1-4 keys, one colour).

Composes N real key sprites (sprites.draw_key_pickup) into the current HUD
icon footprint using several offset / overlay strategies, so we can pick a
look before touching game code.

Constraints from the live HUD:
  * icon size 20 px, slot 23 px wide, HUD row 28 px tall  (game.py, constants)
  * must stay in ~the same HORIZONTAL space as a single icon.

Each candidate key is given a 1 px dark rim (mask silhouette) so overlapping
same-colour keys stay visually separable.

Outputs to scratchpad/keymock/:
  sheet_strategies.png   strategies (rows) x counts 1..4 (cols), scaled up
  hud_context_<s>.png    a realistic HUD strip per strategy (7 colours, mixed
                         counts), at true size and scaled up
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

ICON = 20          # live HUD icon size
SLOT = 23          # live HUD slot width
ROW_H = 28         # live HUD row height (STATUS_H)
RIM = (12, 10, 8)  # dark rim colour for separation

OUT = os.path.join(os.path.dirname(__file__), "keymock")
os.makedirs(OUT, exist_ok=True)


def key_icon(colour, size=ICON):
    """A single key sprite scaled to `size`, with a 1 px dark rim."""
    base = sprites.draw_key_pickup(colour, size=TILE)
    key = pygame.transform.smoothscale(base, (size, size))
    # dark silhouette from the alpha mask, blitted at 8 neighbours = 1px rim
    mask = pygame.mask.from_surface(key)
    sil = mask.to_surface(setcolor=(*RIM, 255), unsetcolor=(0, 0, 0, 0))
    out = pygame.Surface((size + 2, size + 2), pygame.SRCALPHA)
    for ox in (-1, 0, 1):
        for oy in (-1, 0, 1):
            out.blit(sil, (1 + ox, 1 + oy))
    out.blit(key, (1, 1))
    return out


def compose(colour, n, dx, dy, footprint=SLOT, height=ROW_H, shrink=True):
    """Stack n keys with per-step offset (dx, dy) inside a fixed footprint.

    shrink=True: scale each key down so the whole fan fits `footprint` wide
    (and `height` tall) -> horizontal space stays constant as n grows.
    shrink=False: keep full ICON size, let the fan overflow (tiny offsets).
    """
    span_x = abs(dx) * (n - 1)
    span_y = abs(dy) * (n - 1)
    if shrink:
        size = min(ICON,
                   footprint - 2 - span_x,   # -2 for the rim
                   height - 2 - span_y)
        size = max(8, size)
    else:
        size = ICON
    ic = key_icon(colour, size)
    iw, ih = ic.get_size()
    total_w = iw + span_x
    total_h = ih + span_y
    canvas = pygame.Surface((max(footprint, total_w), max(height, total_h)),
                            pygame.SRCALPHA)
    cw, ch = canvas.get_size()
    # centre the whole fan
    x0 = (cw - total_w) // 2
    y0 = (ch - total_h) // 2
    # draw back-to-front so the front (last) key is fully visible
    for i in range(n):
        px = x0 + (i * dx if dx >= 0 else span_x + i * dx)
        py = y0 + (i * dy if dy >= 0 else span_y + i * dy)
        canvas.blit(ic, (px, py))
    return canvas


# (name, dx, dy, shrink)
STRATEGIES = [
    ("diag-dr-3 shrink",  3,  3, True),
    ("diag-ur-3 shrink",  3, -3, True),
    ("fan-x-3 shrink",    3,  1, True),
    ("steep-ur shrink",   2, -3, True),
    ("diag-dr-2 free",    2,  2, False),
    ("diag-ur-2 free",    2, -2, False),
]

SCALE = 14
BLUE = KEY_COLORS['blue']
PAD = 10
LABEL_W = 200


def big(surf, scale=SCALE):
    w, h = surf.get_size()
    return pygame.transform.scale(surf, (w * scale, h * scale))


def build_sheet():
    font = pygame.font.SysFont("dejavusansmono", 18)
    counts = [1, 2, 3, 4]
    cell_w = SLOT * SCALE + PAD
    cell_h = ROW_H * SCALE + PAD
    W = LABEL_W + len(counts) * cell_w + PAD
    H = PAD + 30 + len(STRATEGIES) * cell_h
    sheet = pygame.Surface((W, H))
    sheet.fill(HUD_BG)
    # column headers
    for j, c in enumerate(counts):
        t = font.render(f"{c} key", True, (255, 200, 100))
        sheet.blit(t, (LABEL_W + j * cell_w + cell_w // 2 - 20, 6))
    for i, (name, dx, dy, shrink) in enumerate(STRATEGIES):
        y = 30 + PAD + i * cell_h
        t = font.render(name, True, (230, 230, 230))
        sheet.blit(t, (6, y + cell_h // 2 - 20))
        t2 = font.render(f"({dx:+d},{dy:+d})", True, (150, 150, 150))
        sheet.blit(t2, (6, y + cell_h // 2 + 2))
        for j, c in enumerate(counts):
            comp = compose(BLUE, c, dx, dy, shrink=shrink)
            b = big(comp)
            x = LABEL_W + j * cell_w + (cell_w - b.get_width()) // 2
            # slot outline at true footprint (23px) for reference
            slot_px = SLOT * SCALE
            ox = LABEL_W + j * cell_w + (cell_w - slot_px) // 2
            pygame.draw.rect(sheet, (40, 40, 55),
                             (ox, y, slot_px, ROW_H * SCALE), 1)
            sheet.blit(b, (x, y + (ROW_H * SCALE - b.get_height()) // 2))
    pygame.image.save(sheet, os.path.join(OUT, "sheet_strategies.png"))
    print("wrote sheet_strategies.png", sheet.get_size())


def build_hud_context():
    """A realistic HUD strip: 7 colour slots with mixed counts, per strategy."""
    colours = list(KEY_COLORS.items())
    # a plausible level: mixed counts across colours
    counts = [1, 2, 3, 4, 2, 1, 3]
    for name, dx, dy, shrink in STRATEGIES:
        n_slots = len(colours)
        strip = pygame.Surface((n_slots * SLOT + 8, ROW_H), pygame.SRCALPHA)
        strip.fill(HUD_BG)
        for k, ((cname, rgb), cnt) in enumerate(zip(colours, counts)):
            comp = compose(rgb, cnt, dx, dy, shrink=shrink)
            x = 4 + k * SLOT + (SLOT - comp.get_width()) // 2
            y = (ROW_H - comp.get_height()) // 2
            strip.blit(comp, (x, y))
        b = big(strip, 8)
        safe = name.split()[0]
        pygame.image.save(b, os.path.join(OUT, f"hud_context_{safe}.png"))
    print("wrote hud_context_*.png")


if __name__ == "__main__":
    build_sheet()
    build_hud_context()
    print("done ->", OUT)
