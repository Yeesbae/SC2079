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
ROBOT_SIZE_CELLS = (ROBOT_SIZE_CM // CELL_SIZE_CM) # 5
ROBOT_HALF_CELLS = ROBOT_SIZE_CELLS // 2 # 2.5 


# =====================
# Obstacle dimensions
# =====================

OBSTACLE_SIZE_CM = 10
OBSTACLE_SIZE_CELLS = (OBSTACLE_SIZE_CM // CELL_SIZE_CM) # 2
OBSTACLE_HALF_CELLS = OBSTACLE_SIZE_CELLS // 2  # 1

# =====================
# Obstacle-Robot guard dimensions
# =====================

OBSTACLE_ROBOT_MIN_DIM = 2 
OBSTACLE_ROBOT_GUARD_DIM = OBSTACLE_ROBOT_MIN_DIM + OBSTACLE_HALF_CELLS + ROBOT_HALF_CELLS

# =====================
# Obstacle dimensions
# =====================

ACTUAL_OPTIMAL_VIEWING_DISTANCE_CM = 20
OPTIMAL_VIEWING_DISTANCE_BETWEEN_CAR_OB_COORDINATES_CM = ACTUAL_OPTIMAL_VIEWING_DISTANCE_CM
OPTIMAL_IMAGE_VIEWING_DISTANCE = OPTIMAL_VIEWING_DISTANCE_BETWEEN_CAR_OB_COORDINATES_CM // CELL_SIZE_CM + ROBOT_HALF_CELLS


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


# =====================
# Planning / costs
# =====================

ITERATIONS = 2000
SAFE_COST = 1200


# =====================
# Screenshot Costs
# =====================

FAR_PENALTY = 5
OFFSIDED_PENALTY = 10

BEST_SCREENSHOT_COST = 0
FAR_SCREENSHOT_COST = BEST_SCREENSHOT_COST + FAR_PENALTY
OFFSIDED_SCREENSHOT_COST = BEST_SCREENSHOT_COST + OFFSIDED_PENALTY
FAR_OFFSIDED_SCREENSHOT_COST = BEST_SCREENSHOT_COST + FAR_PENALTY + OFFSIDED_PENALTY
