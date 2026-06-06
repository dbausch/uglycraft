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
"""
import sys
import argparse
import pygame
from constants import LOGICAL_W, LOGICAL_H, FPS, TITLE, EASY, HARD
from levels import LEVELS
from game import Game, PLAYING, QUIT_GAME


def best_scale(display_w, display_h):
    sx = display_w  // LOGICAL_W
    sy = display_h  // LOGICAL_H
    return max(1, min(sx, sy))


def parse_args():
    p = argparse.ArgumentParser(description=TITLE)
    p.add_argument('--level', '-l', type=int, metavar='N',
                   help='Debug: start directly at level N (1–9)')
    g = p.add_mutually_exclusive_group()
    g.add_argument('--easy', action='store_true', help='Debug: use Easy difficulty')
    g.add_argument('--hard', action='store_true', help='Debug: use Hard difficulty')
    return p.parse_args()


def main():
    args = parse_args()

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

    # ── Debug start ───────────────────────────────────────────────────────────
    if args.level is not None:
        level = max(1, min(args.level, len(LEVELS)))
        game.difficulty = HARD if args.hard else EASY
        game._debug = True          # suppresses highscore entry on game-end
        game._full_reset()
        game._start_level(level)
        game.state = PLAYING
        pygame.display.set_caption(f"{TITLE}  [debug  level {level}"
                                   f"  {'hard' if args.hard else 'easy'}]")

    # ── Main loop ─────────────────────────────────────────────────────────────
    while True:
        dt = clock.tick(FPS)

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
            scaled = pygame.transform.scale(logical, (scaled_w, scaled_h))
            screen.blit(scaled, (ox, oy))

        pygame.display.flip()


if __name__ == '__main__':
    main()
