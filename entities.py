"""Player and Enemy entities (tile-grid based)."""
import pygame
from constants import TILE, ROWS, COLS


class Entity:
    def __init__(self, col, row):
        self.col = col
        self.row = row

    @property
    def px(self):
        return self.col * TILE

    @property
    def py(self):
        return self.row * TILE

    def rect(self):
        return pygame.Rect(self.col * TILE, self.row * TILE, TILE, TILE)


class Player(Entity):
    def __init__(self, col, row):
        super().__init__(col, row)
        self.last_dir = (1, 0)    # (dcol, drow) of last attempted move

    def try_move(self, dcol, drow, walls):
        """Move if destination is open. Returns True if moved."""
        nc, nr = self.col + dcol, self.row + drow
        if 0 <= nc < COLS and 0 <= nr < ROWS and not walls[nc][nr]:
            self.col, self.row = nc, nr
            self.last_dir = (dcol, drow)
            return True
        return False


class Enemy(Entity):
    """Greedy chase AI: prefers the axis with the larger delta."""

    def move_toward(self, px, py, walls):
        dx = px - self.col
        dy = py - self.row
        if dx == 0 and dy == 0:
            return

        def can(dc, dr):
            nc, nr = self.col + dc, self.row + dr
            return 0 <= nc < COLS and 0 <= nr < ROWS and not walls[nc][nr]

        def step(dc, dr):
            self.col += dc
            self.row += dr

        if abs(dx) >= abs(dy):
            # Try horizontal first
            if dx > 0 and can(1, 0):
                step(1, 0)
            elif dx < 0 and can(-1, 0):
                step(-1, 0)
            elif dy > 0 and can(0, 1):
                step(0, 1)
            elif dy < 0 and can(0, -1):
                step(0, -1)
        else:
            # Try vertical first
            if dy > 0 and can(0, 1):
                step(0, 1)
            elif dy < 0 and can(0, -1):
                step(0, -1)
            elif dx > 0 and can(1, 0):
                step(1, 0)
            elif dx < 0 and can(-1, 0):
                step(-1, 0)
