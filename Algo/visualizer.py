# import pygame
# from constants import Direction, ARENA_HEIGHT, ARENA_WIDTH, OBSTACLE_SIZE_CELLS, OBSTACLE_HALF_CELLS, ROBOT_SIZE_CELLS

# class MazeVisualizer:
#     def __init__(self, grid_size=(ARENA_HEIGHT, ARENA_WIDTH), cell_pixel_size=20):
#         pygame.init()
#         self.cell_size = cell_pixel_size
#         self.width = grid_size[0] * self.cell_size
#         self.height = grid_size[1] * self.cell_size
#         self.screen = pygame.display.set_mode((self.width, self.height))
#         pygame.display.set_caption("MazeSolver: A* & TSP Path")
        
#         # Colors
#         self.COLOR_BG = (20, 20, 20)
#         self.COLOR_GRID = (40, 40, 40)
#         self.COLOR_ROBOT = (0, 255, 100)
#         self.COLOR_OBS = (255, 50, 50)
#         self.COLOR_PATH = (0, 150, 255)
#         self.COLOR_ARROW = (255, 255, 255)

#     def _to_px(self, x, y):
#         return x * self.cell_size, self.height - (y * self.cell_size)

#     def draw_frame(self, current_robot_state, obstacles, path_history):
#         self.screen.fill(self.COLOR_BG)
#         self._draw_grid()

#         # 1. Draw all obstacles
#         for obs in obstacles:
#             # Grid objects are typically 1x1, draw rect
#             obs_px, obs_py = self._to_px(obs.x, obs.y + OBSTACLE_SIZE_CELLS)

#             pygame.draw.rect(
#                 self.screen,
#                 self.COLOR_OBS,
#                 (
#                     obs_px,
#                     obs_py,
#                     self.cell_size * OBSTACLE_SIZE_CELLS,
#                     self.cell_size * OBSTACLE_SIZE_CELLS
#                 )
#             )
                        
#             # Draw Arrow INSIDE obstacle
#             # We pass is_robot=False so it centers the arrow in the 1x1 cell
#             self._draw_arrow(obs.x, obs.y, obs.direction, self.COLOR_ARROW, is_robot=False)

#         # 2. Draw planned path line
#         if len(path_history) > 1:
#             points = [self._to_px(p.x, p.y) for p in path_history]
#             pygame.draw.lines(self.screen, self.COLOR_PATH, False, points, 2)

#         # 3. Draw Robot
#         rx, ry = self._to_px(current_robot_state.x, current_robot_state.y)
#         robot_rect = pygame.Rect(
#             0,
#             0,
#             self.cell_size * ROBOT_SIZE_CELLS,
#             self.cell_size * ROBOT_SIZE_CELLS
#         )
#         robot_rect.center = (rx, ry)
#         pygame.draw.rect(self.screen, self.COLOR_ROBOT, robot_rect, 2)
        
#         # Draw Arrow for Robot (slightly larger)
#         self._draw_arrow(current_robot_state.x, current_robot_state.y, current_robot_state.direction, self.COLOR_ROBOT, is_robot=True)

#         pygame.display.flip()

#     def _draw_grid(self):
#         for x in range(0, self.width, self.cell_size):
#             pygame.draw.line(self.screen, self.COLOR_GRID, (x, 0), (x, self.height))
#         for y in range(0, self.height, self.cell_size):
#             pygame.draw.line(self.screen, self.COLOR_GRID, (0, y), (self.width, y))

#     def _draw_arrow(self, x, y, direction, color, is_robot=False):
#         """Draws a directional arrow. If is_robot=False, centers it inside a 1x1 obstacle cell."""
        
#         # Calculate center point in pixels
#         # If it's an obstacle, the (x,y) represents bottom-left, so center is +0.5
#         cx, cy = self._to_px(
#             x + OBSTACLE_HALF_CELLS,
#             y + OBSTACLE_HALF_CELLS
#         ) if not is_robot else self._to_px(x, y)
        
#         size = self.cell_size * 0.4 if not is_robot else self.cell_size * 0.7
#         head_size = size * 0.4
        
#         # Define vectors for N, E, S, W
#         # format: (tip_dx, tip_dy, side1_dx, side1_dy, side2_dx, side2_dy)
#         vectors = {
#             Direction.NORTH: (0, -size, -head_size, -size+head_size, head_size, -size+head_size),
#             Direction.EAST:  (size, 0,  size-head_size, -head_size, size-head_size, head_size),
#             Direction.SOUTH: (0, size,  -head_size, size-head_size, head_size, size-head_size),
#             Direction.WEST:  (-size, 0, -size+head_size, -head_size, -size+head_size, head_size)
#         }
        
#         tip_dx, tip_dy, s1x, s1y, s2x, s2y = vectors.get(direction, (0,0,0,0,0,0))
        
#         tip = (cx + tip_dx, cy + tip_dy)
#         base = (cx - tip_dx, cy - tip_dy)
#         side1 = (cx + s1x, cy + s1y)
#         side2 = (cx + s2x, cy + s2y)
        
#         # Draw the arrow shaft
#         pygame.draw.line(self.screen, color, base, tip, 3)
#         # Draw the arrow head (triangle)
#         pygame.draw.polygon(self.screen, color, [tip, side1, side2])

import pygame
import math
from constants import (
    Direction,
    ARENA_HEIGHT,
    ARENA_WIDTH,
    OBSTACLE_SIZE_CELLS,
    OBSTACLE_HALF_CELLS,
    ROBOT_SIZE_CELLS
)

class MazeVisualizer:
    def __init__(self, grid_size=(ARENA_HEIGHT, ARENA_WIDTH), cell_pixel_size=20):
        pygame.init()
        self.cell_size = cell_pixel_size
        self.width = grid_size[0] * self.cell_size
        self.height = grid_size[1] * self.cell_size
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("MazeSolver Path Replay")

        self.COLOR_BG = (20, 20, 20)
        self.COLOR_GRID = (40, 40, 40)
        self.COLOR_ROBOT = (0, 255, 100)
        self.COLOR_OBS = (255, 50, 50)
        self.COLOR_PATH = (0, 150, 255)
        self.COLOR_ARROW = (255, 255, 255)

    # -------------------------------------------------
    # Geometry helpers
    # -------------------------------------------------
    def _to_px(self, x, y):
        return x * self.cell_size, self.height - y * self.cell_size

    def _dir_to_angle(self, d):
        return {
            Direction.EAST: 0.0,
            Direction.NORTH: math.pi / 2,
            Direction.WEST: math.pi,
            Direction.SOUTH: -math.pi / 2
        }[d]

    def _heading_vec(self, angle):
        return math.cos(angle), math.sin(angle)

    # -------------------------------------------------
    # Frame
    # -------------------------------------------------
    def draw_frame(self, robot_state, obstacles, path, upto_idx):
        self.screen.fill(self.COLOR_BG)
        self._draw_grid()

        for obs in obstacles:
            ox, oy = self._to_px(obs.x, obs.y + OBSTACLE_SIZE_CELLS)
            pygame.draw.rect(
                self.screen,
                self.COLOR_OBS,
                (ox, oy,
                 self.cell_size * OBSTACLE_SIZE_CELLS,
                 self.cell_size * OBSTACLE_SIZE_CELLS)
            )
            self._draw_arrow(
                obs.x + OBSTACLE_HALF_CELLS,
                obs.y + OBSTACLE_HALF_CELLS,
                self._dir_to_angle(obs.direction),
                self.COLOR_ARROW,
                0.4
            )

        self._draw_path(path[:upto_idx + 1])

        rx, ry = self._to_px(robot_state.x, robot_state.y)
        rect = pygame.Rect(
            0, 0,
            self.cell_size * ROBOT_SIZE_CELLS,
            self.cell_size * ROBOT_SIZE_CELLS
        )
        rect.center = (rx, ry)
        pygame.draw.rect(self.screen, self.COLOR_ROBOT, rect, 2)

        self._draw_arrow(
            robot_state.x,
            robot_state.y,
            self._dir_to_angle(robot_state.direction),
            self.COLOR_ROBOT,
            0.7
        )

        pygame.display.flip()

    # -------------------------------------------------
    # Grid
    # -------------------------------------------------
    def _draw_grid(self):
        for x in range(0, self.width, self.cell_size):
            pygame.draw.line(self.screen, self.COLOR_GRID, (x, 0), (x, self.height))
        for y in range(0, self.height, self.cell_size):
            pygame.draw.line(self.screen, self.COLOR_GRID, (0, y), (self.width, y))

    # -------------------------------------------------
    # Path drawing (Bezier, NOT fake circles)
    # -------------------------------------------------
    def _draw_path(self, path):
        if len(path) < 2:
            return

        for i in range(1, len(path)):
            p0 = path[i - 1]
            p1 = path[i]

            if p0.direction == p1.direction:
                pygame.draw.line(
                    self.screen,
                    self.COLOR_PATH,
                    self._to_px(p0.x, p0.y),
                    self._to_px(p1.x, p1.y),
                    2
                )
            else:
                self._draw_bezier_turn(p0, p1)

    def _draw_bezier_turn(self, p0, p1, steps=30):
        x0, y0 = p0.x, p0.y
        x3, y3 = p1.x, p1.y

        a0 = self._dir_to_angle(p0.direction)
        a1 = self._dir_to_angle(p1.direction)

        dx = x3 - x0
        dy = y3 - y0
        dist = math.hypot(dx, dy)

        # Control length scales with distance
        control_len = 0.5 * dist

        hx0, hy0 = self._heading_vec(a0)
        hx1, hy1 = self._heading_vec(a1)

        x1 = x0 + control_len * hx0
        y1 = y0 + control_len * hy0

        x2 = x3 - control_len * hx1
        y2 = y3 - control_len * hy1

        points = []
        for i in range(steps + 1):
            t = i / steps
            xt = (
                (1 - t) ** 3 * x0 +
                3 * (1 - t) ** 2 * t * x1 +
                3 * (1 - t) * t ** 2 * x2 +
                t ** 3 * x3
            )
            yt = (
                (1 - t) ** 3 * y0 +
                3 * (1 - t) ** 2 * t * y1 +
                3 * (1 - t) * t ** 2 * y2 +
                t ** 3 * y3
            )
            points.append(self._to_px(xt, yt))

        pygame.draw.lines(self.screen, self.COLOR_PATH, False, points, 2)

    # -------------------------------------------------
    # Arrow
    # -------------------------------------------------
    def _draw_arrow(self, x, y, angle, color, scale):
        cx, cy = self._to_px(x, y)
        size = self.cell_size * scale
        head = size * 0.4

        tip = (cx + size * math.cos(angle), cy - size * math.sin(angle))
        base = (cx - size * math.cos(angle), cy + size * math.sin(angle))

        left = (
            tip[0] - head * math.cos(angle - math.pi / 6),
            tip[1] + head * math.sin(angle - math.pi / 6)
        )
        right = (
            tip[0] - head * math.cos(angle + math.pi / 6),
            tip[1] + head * math.sin(angle + math.pi / 6)
        )

        pygame.draw.line(self.screen, color, base, tip, 3)
        pygame.draw.polygon(self.screen, color, [tip, left, right])
