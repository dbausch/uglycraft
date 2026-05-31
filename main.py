#!/usr/bin/env python3
"""
UGLYCRAFT — entry point.

Logical resolution: 960×540 (16:9).
Scaling:
  • 1920×1080  → 2× integer scale, fills screen exactly.
  • 1024×768   → 1× (960×540 centred, ~32 px pillarbox / 114 px letterbox).
  • Any other  → largest integer scale that fits, then centred with black bars.
"""
import sys
import pygame
from constants import LOGICAL_W, LOGICAL_H, FPS, TITLE
from game import Game, WIN, GAME_OVER, PLAY_AGAIN, QUIT_GAME


def best_scale(display_w, display_h):
    sx = display_w  // LOGICAL_W
    sy = display_h  // LOGICAL_H
    return max(1, min(sx, sy))


def main():
    pygame.init()

    info  = pygame.display.Info()
    dw, dh = info.current_w, info.current_h

    # Default to a comfortable windowed size if the monitor query looks wrong
    if dw <= 0 or dh <= 0:
        dw, dh = 1280, 720

    scale = best_scale(dw, dh)

    # Try full-screen if the scaled game area exactly matches the display
    if scale * LOGICAL_W == dw and scale * LOGICAL_H == dh:
        flags  = pygame.FULLSCREEN | pygame.NOFRAME
        screen = pygame.display.set_mode((dw, dh), flags)
    else:
        # Windowed — size the window to the scaled game area
        win_w  = min(scale * LOGICAL_W, dw)
        win_h  = min(scale * LOGICAL_H, dh)
        screen = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)

    pygame.display.set_caption(TITLE)

    # Logical surface that the game always renders at 960×540
    logical = pygame.Surface((LOGICAL_W, LOGICAL_H))

    clock = pygame.time.Clock()
    game  = Game(logical)

    while True:
        dt = clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(
                    event.size, pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
            # Route events to game (after handling global ones)
            game.handle_event(event)
            if game.state == QUIT_GAME:
                pygame.quit()
                sys.exit()

            # Transition from WIN/GAME_OVER → score entry
            from game import WIN, GAME_OVER, PLAY_AGAIN, SHOW_SCORES, ENTER_SCORE
            if event.type == pygame.KEYDOWN:
                if game.state == PLAY_AGAIN:
                    pass  # handled inside game
                # if game just showed WIN/GAME_OVER and player pressed key,
                # check whether we should offer score entry
                # (game.py transitions state to PLAY_AGAIN on key; we catch it here)

        game.update(dt)

        # Render onto logical surface
        game.render()

        # Blit logical surface onto screen with scaling + centring
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
