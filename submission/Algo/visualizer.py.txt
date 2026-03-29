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
        if d == Direction.SKIP:
            return None
    
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
    def draw_frame(self, robot_state, obstacles, path, upto_idx, override_angle=None):
        self.screen.fill(self.COLOR_BG)
        self._draw_grid()

        # Draw obstacles
        for obs in obstacles:
            ox, oy = self._to_px(obs.x, obs.y + OBSTACLE_SIZE_CELLS)
            pygame.draw.rect(
                self.screen,
                self.COLOR_OBS,
                (ox, oy,
                self.cell_size * OBSTACLE_SIZE_CELLS,
                self.cell_size * OBSTACLE_SIZE_CELLS)
            )

            angle = self._dir_to_angle(obs.direction)
            if angle is not None:
                self._draw_arrow(
                    obs.x + OBSTACLE_HALF_CELLS,
                    obs.y + OBSTACLE_HALF_CELLS,
                    angle,
                    self.COLOR_ARROW,
                    0.4
                )

        # Draw path
        self._draw_path(path[:upto_idx + 1])

        # Decide robot angle
        if override_angle is not None:
            angle = override_angle
        else:
            angle = self._dir_to_angle(robot_state.direction)

        # Draw robot body (rotated)
        self._draw_robot(robot_state.x, robot_state.y, angle)

        # Draw arrow aligned with same angle
        self._draw_arrow(
            robot_state.x,
            robot_state.y,
            angle,
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

    def _draw_robot(self, x, y, angle):
        size = self.cell_size * ROBOT_SIZE_CELLS

        # Create surface for robot
        surf = pygame.Surface((size, size), pygame.SRCALPHA)

        # Draw rectangle centered in surface
        pygame.draw.rect(
            surf,
            self.COLOR_ROBOT,
            (0, 0, size, size),
            2
        )

        # Rotate surface
        rotated = pygame.transform.rotate(surf, math.degrees(angle))

        # Get new rect centered at (x,y)
        rect = rotated.get_rect(center=self._to_px(x, y))

        self.screen.blit(rotated, rect)

    # -------------------------------------------------
    # Path drawing (Bezier curves)
    # -------------------------------------------------
    def _draw_path(self, path):
        if len(path) < 2:
            return

        for i in range(1, len(path)):
            p0 = path[i - 1]
            p1 = path[i]

            if p0.direction == p1.direction:
                # Straight segment
                pygame.draw.line(
                    self.screen,
                    self.COLOR_PATH,
                    self._to_px(p0.x, p0.y),
                    self._to_px(p1.x, p1.y),
                    2
                )
            else:
                # Turning segment
                self._draw_bezier_turn(p0, p1)

    def _draw_bezier_turn(self, p0, p1, steps=30):
        x0, y0 = p0.x, p0.y
        x3, y3 = p1.x, p1.y

        a0 = self._dir_to_angle(p0.direction)
        a1 = self._dir_to_angle(p1.direction)

        dx = x3 - x0
        dy = y3 - y0
        dist = math.hypot(dx, dy)
        control_len = 0.5 * dist

        hx0, hy0 = self._heading_vec(a0)
        hx1, hy1 = self._heading_vec(a1)

        # Determine reversing automatically
        dot = dx * hx0 + dy * hy0
        reversing = dot < 0

        if reversing:
            hx0, hy0 = -hx0, -hy0
            hx1, hy1 = -hx1, -hy1

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
        """
        Draw a triangle pointing in the given angle.
        The triangle is scaled relative to cell size (approx 2x2 cells if scale=1.0).
        """
        cx, cy = self._to_px(x, y)
        size = self.cell_size * 2 * scale  # triangle roughly 2x2 cells
        half_size = size / 2

        # Tip of the triangle
        tip_x = cx + half_size * math.cos(angle)
        tip_y = cy - half_size * math.sin(angle)

        # Base points (triangle base perpendicular to facing direction)
        left_x = cx + half_size * math.cos(angle + 2.5 * math.pi / 3)
        left_y = cy - half_size * math.sin(angle + 2.5 * math.pi / 3)

        right_x = cx + half_size * math.cos(angle - 2.5 * math.pi / 3)
        right_y = cy - half_size * math.sin(angle - 2.5 * math.pi / 3)

        pygame.draw.polygon(self.screen, color, [(tip_x, tip_y), (left_x, left_y), (right_x, right_y)])


    def _bezier_position(self, p0, p1, t):
        x0, y0 = p0.x, p0.y
        x3, y3 = p1.x, p1.y

        a0 = self._dir_to_angle(p0.direction)
        a1 = self._dir_to_angle(p1.direction)

        dx = x3 - x0
        dy = y3 - y0
        dist = math.hypot(dx, dy)
        control_len = 0.5 * dist

        hx0, hy0 = self._heading_vec(a0)
        hx1, hy1 = self._heading_vec(a1)

        dot = dx * hx0 + dy * hy0
        reversing = dot < 0

        if reversing:
            hx0, hy0 = -hx0, -hy0
            hx1, hy1 = -hx1, -hy1

        x1 = x0 + control_len * hx0
        y1 = y0 + control_len * hy0
        x2 = x3 - control_len * hx1
        y2 = y3 - control_len * hy1

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

        return xt, yt

    def animate_transition(self, p0, p1, obstacles, path, upto_idx, frames=10):
        clock = pygame.time.Clock()

        # -------------------------
        # Straight Move
        # -------------------------
        if p0.direction == p1.direction:
            for i in range(1, frames + 1):
                t = i / frames
                x = p0.x + t * (p1.x - p0.x)
                y = p0.y + t * (p1.y - p0.y)

                temp_state = type(p0)(x, y, p0.direction)

                self.draw_frame(
                    temp_state,
                    obstacles,
                    path,
                    upto_idx
                )

                clock.tick(60)

        # -------------------------
        # Turning Move
        # -------------------------
        else:
            a0 = self._dir_to_angle(p0.direction)
            a1 = self._dir_to_angle(p1.direction)

            # Shortest rotation normalization
            delta = a1 - a0
            if delta > math.pi:
                delta -= 2 * math.pi
            elif delta < -math.pi:
                delta += 2 * math.pi

            for i in range(1, frames + 1):
                t = i / frames

                # Position along Bezier
                x, y = self._bezier_position(p0, p1, t)

                # Smooth interpolated angle
                angle = a0 + t * delta

                temp_state = type(p0)(x, y, p0.direction)

                self.draw_frame(
                    temp_state,
                    obstacles,
                    path,
                    upto_idx,
                    override_angle=angle
                )

                clock.tick(60)
