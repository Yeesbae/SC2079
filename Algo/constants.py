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

MOVE_DIRECTION = [
    (1, 0, Direction.EAST),
    (-1, 0, Direction.WEST),
    (0, 1, Direction.NORTH),
    (0, -1, Direction.SOUTH),
]

TURN_FACTOR = 1

EXPANDED_CELL = 1

WIDTH = 20
HEIGHT = 20

ITERATIONS = 2000
TURN_RADIUS = 1


SAFE_COST = 1200
SCREENSHOT_COST = 50 
