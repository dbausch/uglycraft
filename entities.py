"""Player and Enemy entities (tile-grid based)."""
import random
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
    """Enemy with two movement modes: greedy (EASY) and BFS (HARD)."""

    def __init__(self, col, row):
        super().__init__(col, row)
        self.room_name = None       # graph node this enemy belongs to
        self.room_tiles = None      # set of (col, row) tiles in this room

    def wander(self, walls, occupied=frozenset()):
        """Move to a random adjacent tile within this enemy's room."""
        options = []
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nc, nr = self.col + dc, self.row + dr
            if (0 <= nc < COLS and 0 <= nr < ROWS
                    and not walls[nc][nr]
                    and (nc, nr) not in occupied
                    and (self.room_tiles is None
                         or (nc, nr) in self.room_tiles)):
                options.append((nc, nr))
        if options:
            self.col, self.row = random.choice(options)

    def move_toward(self, px, py, walls, occupied=frozenset()):
        dx = px - self.col
        dy = py - self.row
        if dx == 0 and dy == 0:
            return

        def can(dc, dr):
            nc, nr = self.col + dc, self.row + dr
            return (0 <= nc < COLS and 0 <= nr < ROWS
                    and not walls[nc][nr]
                    and (nc, nr) not in occupied
                    and (self.room_tiles is None
                         or (nc, nr) in self.room_tiles))

        def step(dc, dr):
            self.col += dc
            self.row += dr

        if abs(dx) >= abs(dy):
            if dx > 0 and can(1, 0):
                step(1, 0)
            elif dx < 0 and can(-1, 0):
                step(-1, 0)
            elif dy > 0 and can(0, 1):
                step(0, 1)
            elif dy < 0 and can(0, -1):
                step(0, -1)
        else:
            if dy > 0 and can(0, 1):
                step(0, 1)
            elif dy < 0 and can(0, -1):
                step(0, -1)
            elif dx > 0 and can(1, 0):
                step(1, 0)
            elif dx < 0 and can(-1, 0):
                step(-1, 0)

    def move_bfs(self, dist, occupied=frozenset()):
        """Step toward the player using a pre-computed BFS distance map.

        Among all passable, unoccupied neighbours that share the minimum
        distance to the player, one is chosen uniformly at random.
        """
        best = float('inf')
        candidates = []
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nc, nr = self.col + dc, self.row + dr
            if (nc, nr) in occupied:
                continue
            if self.room_tiles is not None and (nc, nr) not in self.room_tiles:
                continue
            d = dist.get((nc, nr), float('inf'))
            if d < best:
                best = d
                candidates = [(nc, nr)]
            elif d == best:
                candidates.append((nc, nr))
        if candidates and best < float('inf'):
            self.col, self.row = random.choice(candidates)


class ForgeOgre(Enemy):
    """Enemy that breaks player-placed walls in 2 bumps instead of 3."""

    def __init__(self, col, row):
        super().__init__(col, row)
        self.wall_bump_power = 2  # breaks walls in 2 hits


class PatrolEnemy(Enemy):
    """Enemy that walks a fixed back-and-forth path between waypoints."""

    def __init__(self, col, row, waypoints):
        super().__init__(col, row)
        self.waypoints = waypoints
        self._wp_idx = 0
        self._forward = True

    def move_patrol(self, walls, occupied=frozenset()):
        if not self.waypoints:
            return
        target_col, target_row = self.waypoints[self._wp_idx]
        if self.col == target_col and self.row == target_row:
            if self._forward:
                if self._wp_idx < len(self.waypoints) - 1:
                    self._wp_idx += 1
                else:
                    self._forward = False
                    if self._wp_idx > 0:
                        self._wp_idx -= 1
            else:
                if self._wp_idx > 0:
                    self._wp_idx -= 1
                else:
                    self._forward = True
                    if self._wp_idx < len(self.waypoints) - 1:
                        self._wp_idx += 1
            target_col, target_row = self.waypoints[self._wp_idx]

        dx = target_col - self.col
        dy = target_row - self.row
        dc = (1 if dx > 0 else -1) if dx != 0 else 0
        dr = (1 if dy > 0 else -1) if dy != 0 else 0

        if dc != 0:
            nc = self.col + dc
            if 0 <= nc < COLS and not walls[nc][self.row] and (nc, self.row) not in occupied:
                self.col = nc
                return
        if dr != 0:
            nr = self.row + dr
            if 0 <= nr < ROWS and not walls[self.col][nr] and (self.col, nr) not in occupied:
                self.row = nr
