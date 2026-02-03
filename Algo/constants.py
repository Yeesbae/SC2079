from enum import Enum


EXPANDED_CELL = 2

WIDTH = 20
HEIGHT = 20


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

ROBOT_SIZE_CM = 20
ROBOT_SIZE_CELLS = (ROBOT_SIZE_CM // CELL_SIZE_CM)  # = 4
ROBOT_HALF_CELLS = ROBOT_SIZE_CELLS // 2   # = 2


# =====================
# Obstacle dimensions
# =====================

OBSTACLE_SIZE_CM = 10
OBSTACLE_SIZE_CELLS = (OBSTACLE_SIZE_CM // CELL_SIZE_CM)
OBSTACLE_HALF_CELLS = OBSTACLE_SIZE_CELLS // 2  # = 1


# =====================
# Obstacle dimensions
# =====================

ACTUAL_OPTIMAL_VIEWING_DISTANCE_CM = 20
OPTIMAL_VIEWING_DISTANCE_BETWEEN_CAR_OB_COORDINATES_CM = ACTUAL_OPTIMAL_VIEWING_DISTANCE_CM + 2 * OBSTACLE_SIZE_CM
OPTIMAL_IMAGE_VIEWING_DISTANCE = OPTIMAL_VIEWING_DISTANCE_BETWEEN_CAR_OB_COORDINATES_CM // CELL_SIZE_CM


# =====================
# Motion / Dubins
# =====================

TURN_RADIUS_CM = 25
TURN_RADIUS = TURN_RADIUS_CM // CELL_SIZE_CM

SMALL_TURN = [1 * TURN_RADIUS, 1 * TURN_RADIUS]
BIG_TURN = [4 * TURN_RADIUS, 2 * TURN_RADIUS]


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


# =====================
# Planning / costs
# =====================

ITERATIONS = 2000
SAFE_COST = 1200
SCREENSHOT_COST = 50
