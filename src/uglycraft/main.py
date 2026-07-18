#!/usr/bin/env python3
"""
UGLYCRAFT — entry point.

Logical resolution: 960×540 (16:9).
Scaling:
  • 1920×1080  → 2× integer scale, fills screen exactly.
  • 1024×768   → 1× (960×540 centred, ~32 px pillarbox / 114 px letterbox).
  • Any other  → largest integer scale that fits, then centred with black bars.

Debug flags (skip menus and highscore):
  --level N        start at level N (1–9)
  --easy / --hard  set difficulty   (default: easy)
  --dump-level N   print an ASCII export of level N as loaded and exit
                   (spec 0064); --seed S pins all randomness
"""
import sys
import argparse
import pygame
from uglycraft.constants import LOGICAL_W, LOGICAL_H, FPS, MAX_DT_MS, TITLE, EASY, HARD
from uglycraft.levels import TOTAL_LEVELS
from uglycraft.game import Game, PLAYING, QUIT_GAME


def best_scale(display_w, display_h):
    sx = display_w  // LOGICAL_W
    sy = display_h  // LOGICAL_H
    return max(1, min(sx, sy))


def present(logical):
    """Scale the logical surface to the current window and flip.

    Used both by the main loop and by Game's loading screen (which draws frames
    during the blocking Act 2 generation inside _start_level)."""
    screen = pygame.display.get_surface()
    sw, sh   = screen.get_size()
    sc       = best_scale(sw, sh)
    scaled_w = sc * LOGICAL_W
    scaled_h = sc * LOGICAL_H
    ox       = (sw - scaled_w) // 2
    oy       = (sh - scaled_h) // 2

    screen.fill((0, 0, 0))
    if sc == 1:
        screen.blit(logical, (ox, oy))
    else:
        screen.blit(pygame.transform.scale(logical, (scaled_w, scaled_h)), (ox, oy))
    pygame.display.flip()


def parse_args():
    p = argparse.ArgumentParser(description=TITLE)
    p.add_argument('--level', '-l', type=int, metavar='N',
                   help='Debug: start directly at level N (1–9)')
    p.add_argument('--dump-level', type=int, metavar='N',
                   help='Print an ASCII export of level N as loaded and exit')
    p.add_argument('--seed', type=int, metavar='S',
                   help='Pin all randomness (only meaningful with --dump-level)')
    g = p.add_mutually_exclusive_group()
    g.add_argument('--easy', action='store_true', help='Debug: use Easy difficulty')
    g.add_argument('--hard', action='store_true', help='Debug: use Hard difficulty')
    return p.parse_args()


def main():
    args = parse_args()

    # ── Headless ASCII export (spec 0064): no window, print and exit ──────────
    if args.dump_level is not None:
        from uglycraft.leveldump import dump_level
        level = max(1, min(args.dump_level, TOTAL_LEVELS))
        print(dump_level(level, difficulty=HARD if args.hard else EASY,
                         seed=args.seed), end='')
        return

    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()

    info  = pygame.display.Info()
    dw, dh = info.current_w, info.current_h

    if dw <= 0 or dh <= 0:
        dw, dh = 1280, 720

    scale = best_scale(dw, dh)

    if scale * LOGICAL_W == dw and scale * LOGICAL_H == dh:
        flags  = pygame.FULLSCREEN | pygame.NOFRAME
        screen = pygame.display.set_mode((dw, dh), flags)
    else:
        win_w  = min(scale * LOGICAL_W, dw)
        win_h  = min(scale * LOGICAL_H, dh)
        screen = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)

    pygame.display.set_caption(TITLE)
    pygame.mouse.set_visible(False)

    logical = pygame.Surface((LOGICAL_W, LOGICAL_H))
    clock   = pygame.time.Clock()
    game    = Game(logical)
    game.present = present   # lets the loading screen draw during generation

    # ── Debug start ───────────────────────────────────────────────────────────
    if args.level is not None:
        level = max(1, min(args.level, TOTAL_LEVELS))
        game.difficulty = HARD if args.hard else EASY
        game._debug = True          # suppresses highscore entry on game-end
        game._full_reset()
        game._start_level(level)
        game.state = PLAYING
        pygame.display.set_caption(f"{TITLE}  [debug  level {level}"
                                   f"  {'hard' if args.hard else 'easy'}]")

    # ── Main loop ─────────────────────────────────────────────────────────────
    while True:
        # Clamp dt so a long hitch (startup, or a heavy Act 2 level generated
        # mid-game) cannot dump a huge accumulated time into the update step and
        # cause an enemy-movement burst (spec 0028 / BL-11).
        dt = min(clock.tick(FPS), MAX_DT_MS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
            game.handle_event(event)
            if game.state == QUIT_GAME:
                pygame.quit()
                sys.exit()

        game.update(dt)
        game.render()
        present(logical)


if __name__ == '__main__':
    main()
