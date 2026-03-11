from enum import Enum

class Direction(int, Enum):
    NORTH = 0
    EAST = 2
    SOUTH = 4
    WEST = 6
    SKIP = 8

    def __int__(self):
        return self.value

    @staticmethod
    def rotation_cost(d1, d2):
        diff = abs(d1 - d2)
        return min(diff, 8 - diff)


# =====================
# Physical dimensions
# =====================

CELL_SIZE_CM = 5
ARENA_SIZE_CM = 200


# =====================
# Grid size
# =====================

ARENA_WIDTH = ARENA_SIZE_CM // CELL_SIZE_CM
ARENA_HEIGHT = ARENA_SIZE_CM // CELL_SIZE_CM


# =====================
# Robot dimensions
# =====================

ROBOT_SIZE_CM = 25
ROBOT_SIZE_CELLS = (ROBOT_SIZE_CM // CELL_SIZE_CM)  # = 5
ROBOT_HALF_CELLS = ROBOT_SIZE_CELLS / 2   # = 2


# =====================
# Obstacle dimensions
# =====================

OBSTACLE_SIZE_CM = 10
OBSTACLE_SIZE_CELLS = (OBSTACLE_SIZE_CM // CELL_SIZE_CM)
OBSTACLE_HALF_CELLS = OBSTACLE_SIZE_CELLS / 2  # = 1
OBSTACLE_INFLATION_CELLS = 0     # Inflate an edge of a obstacle by how many cells


# =====================
# Obstacle dimensions
# =====================

ACTUAL_OPTIMAL_VIEWING_DISTANCE_CM = 20
OPTIMAL_VIEWING_DISTANCE_BETWEEN_CAR_OB_COORDINATES_CM = ACTUAL_OPTIMAL_VIEWING_DISTANCE_CM
OPTIMAL_IMAGE_VIEWING_DISTANCE = OPTIMAL_VIEWING_DISTANCE_BETWEEN_CAR_OB_COORDINATES_CM // CELL_SIZE_CM + int(ROBOT_HALF_CELLS)


# =====================
# Motion / Dubins
# =====================

TURN_RADIUS_CM = 25
TURN_RADIUS = TURN_RADIUS_CM // CELL_SIZE_CM

SMALL_TURN = [1 * TURN_RADIUS, 1 * TURN_RADIUS]
BIG_TURN = [2 * TURN_RADIUS, 2 * TURN_RADIUS]

TURN_FACTOR = 1


# =====================
# Movement
# =====================

MOVE_DIRECTION = [
    (1, 0, Direction.EAST),
    (-1, 0, Direction.WEST),
    (0, 1, Direction.NORTH),
    (0, -1, Direction.SOUTH),
]

# Calculated when assuming coors for both car and obstacle are the center
# The mask is calculated by calculating inner & outer sweep circle using GeogeBra Tool.
# """
# Robot: 25cm x 25cm (5 cells x 5 cells)
# Obstacle: 10cm x 10cm (2 cells x 2 cells)
# Obstacle Inflation: 0 cells
# Turning Radius: 25cm (5 cells)
# """
# NORTH_LEFT_MASK = [
#     (-8, -4, 2, 8),
#     (-3, -1, 4, 8),
#     (0, 1, 4, 7),
#     (2, 2, 4, 6),
#     (3, 3, 4, 4),
# ]

"""
Robot: 25cm x 25cm (5 cells x 5 cells)
Obstacle: 10cm x 10cm (2 cells x 2 cells)
Obstacle Inflation: 0.5 cells
Turning Radius: 25cm (5 cells)
"""
NORTH_LEFT_MASK = [
    (-9, -5, 1, 9),
    (-4, -1, 5, 9),
    (0, 1, 5, 8),
    (2, 2, 5, 7),
    (3, 3, 5, 6),
]


# =====================
# Planning / costs
# =====================

ITERATIONS = 2000
TOO_CLOSE_PENALTY = 100
MINIMUM_ALLOWED_DISTANCE_BETWEEN_CAR_AND_OBSTACLE_CM = 5
MINIMUM_ALLOWED_DISTANCE_BETWEEN_CAR_AND_OBSTACLE_CELLS = MINIMUM_ALLOWED_DISTANCE_BETWEEN_CAR_AND_OBSTACLE_CM // CELL_SIZE_CM

# =====================
# Screenshot Costs
# =====================

FAR_PENALTY = 5
OFFSIDED_PENALTY = 10

BEST_SCREENSHOT_COST = 0
FAR_SCREENSHOT_COST = BEST_SCREENSHOT_COST + FAR_PENALTY
OFFSIDED_SCREENSHOT_COST = BEST_SCREENSHOT_COST + OFFSIDED_PENALTY
FAR_OFFSIDED_SCREENSHOT_COST = BEST_SCREENSHOT_COST + FAR_PENALTY + OFFSIDED_PENALTY
