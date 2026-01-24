import pygame
from constants import Direction

class MazeVisualizer:
    def __init__(self, grid_size=(20, 20), cell_pixel_size=40):
        pygame.init()
        self.cell_size = cell_pixel_size
        self.width = grid_size[0] * self.cell_size
        self.height = grid_size[1] * self.cell_size
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("MazeSolver: A* & TSP Path")
        
        # Colors
        self.COLOR_BG = (20, 20, 20)
        self.COLOR_GRID = (40, 40, 40)
        self.COLOR_ROBOT = (0, 255, 100)
        self.COLOR_OBS = (255, 50, 50)
        self.COLOR_PATH = (0, 150, 255)
        self.COLOR_ARROW = (255, 255, 255)

    def _to_px(self, x, y):
        return x * self.cell_size, self.height - (y * self.cell_size)

    def draw_frame(self, current_robot_state, obstacles, path_history):
        self.screen.fill(self.COLOR_BG)
        self._draw_grid()

        # 1. Draw all obstacles
        for obs in obstacles:
            # Grid objects are typically 1x1, draw rect
            px, py = self._to_px(obs.x, obs.y + 1) 
            pygame.draw.rect(self.screen, self.COLOR_OBS, (px, py, self.cell_size, self.cell_size))
            
            # Draw Arrow INSIDE obstacle
            # We pass is_robot=False so it centers the arrow in the 1x1 cell
            self._draw_arrow(obs.x, obs.y, obs.direction, self.COLOR_ARROW, is_robot=False)

        # 2. Draw planned path line
        if len(path_history) > 1:
            points = [self._to_px(p.x, p.y) for p in path_history]
            pygame.draw.lines(self.screen, self.COLOR_PATH, False, points, 2)

        # 3. Draw Robot
        rx, ry = self._to_px(current_robot_state.x, current_robot_state.y)
        robot_rect = pygame.Rect(0, 0, self.cell_size * 2, self.cell_size * 2)
        robot_rect.center = (rx, ry)
        pygame.draw.rect(self.screen, self.COLOR_ROBOT, robot_rect, 2)
        
        # Draw Arrow for Robot (slightly larger)
        self._draw_arrow(current_robot_state.x, current_robot_state.y, current_robot_state.direction, self.COLOR_ROBOT, is_robot=True)

        pygame.display.flip()

    def _draw_grid(self):
        for x in range(0, self.width, self.cell_size):
            pygame.draw.line(self.screen, self.COLOR_GRID, (x, 0), (x, self.height))
        for y in range(0, self.height, self.cell_size):
            pygame.draw.line(self.screen, self.COLOR_GRID, (0, y), (self.width, y))

    def _draw_arrow(self, x, y, direction, color, is_robot=False):
        """Draws a directional arrow. If is_robot=False, centers it inside a 1x1 obstacle cell."""
        
        # Calculate center point in pixels
        # If it's an obstacle, the (x,y) represents bottom-left, so center is +0.5
        cx, cy = self._to_px(x + 0.5, y + 0.5) if not is_robot else self._to_px(x, y)
        
        size = self.cell_size * 0.4 if not is_robot else self.cell_size * 0.7
        head_size = size * 0.4
        
        # Define vectors for N, E, S, W
        # format: (tip_dx, tip_dy, side1_dx, side1_dy, side2_dx, side2_dy)
        vectors = {
            Direction.NORTH: (0, -size, -head_size, -size+head_size, head_size, -size+head_size),
            Direction.EAST:  (size, 0,  size-head_size, -head_size, size-head_size, head_size),
            Direction.SOUTH: (0, size,  -head_size, size-head_size, head_size, size-head_size),
            Direction.WEST:  (-size, 0, -size+head_size, -head_size, -size+head_size, head_size)
        }
        
        tip_dx, tip_dy, s1x, s1y, s2x, s2y = vectors.get(direction, (0,0,0,0,0,0))
        
        tip = (cx + tip_dx, cy + tip_dy)
        base = (cx - tip_dx, cy - tip_dy)
        side1 = (cx + s1x, cy + s1y)
        side2 = (cx + s2x, cy + s2y)
        
        # Draw the arrow shaft
        pygame.draw.line(self.screen, color, base, tip, 3)
        # Draw the arrow head (triangle)
        pygame.draw.polygon(self.screen, color, [tip, side1, side2])