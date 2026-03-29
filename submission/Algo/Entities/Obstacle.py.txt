from .Cell import CellState
from typing import List
from constants import Direction, OFFSIDED_SCREENSHOT_COST, FAR_OFFSIDED_SCREENSHOT_COST, FAR_SCREENSHOT_COST, BEST_SCREENSHOT_COST, OPTIMAL_IMAGE_VIEWING_DISTANCE
from Util.helper import is_valid

class Obstacle(CellState):
    """Obstacle class, inherited from CellState"""

    def __init__(self, x: int, y: int, direction: Direction, obstacle_id: int):
        super().__init__(x, y, direction)
        self.obstacle_id = obstacle_id


    def __eq__(self, other):
        """Checks if this obstacle is the same as input in terms of x, y, and direction

        Args:
            other (Obstacle): input obstacle to compare to

        Returns:
            bool: True if same, False otherwise
        """
        return self.x == other.x and self.y == other.y and self.direction == other.direction


    def get_view_state(self, retrying) -> List[CellState]:
        """Constructs the list of CellStates from which the robot can view the symbol on the obstacle

        Returns:
            List[CellState]: Valid cell states where robot can be positioned to view the symbol on the obstacle
        """
        cells = []

        # If the obstacle is facing north, then robot's cell state must be facing south
        if self.direction == Direction.NORTH:
            y_offset = 2
            x_offset = 1

            if retrying == False:
                # Or (x, y + 5)
                if is_valid(self.x + x_offset, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE):
                    cells.append(CellState(self.x + x_offset, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE, 
                                 Direction.SOUTH, self.obstacle_id, BEST_SCREENSHOT_COST))
                # Or (x, y + 6)
                if is_valid(self.x + x_offset, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 1):
                    cells.append(CellState(self.x + x_offset, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 1, 
                                 Direction.SOUTH, self.obstacle_id, BEST_SCREENSHOT_COST))
                # Or (x, y + 7)
                if is_valid(self.x + x_offset, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2):
                    cells.append(CellState(self.x + x_offset, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2, 
                                 Direction.SOUTH, self.obstacle_id, BEST_SCREENSHOT_COST))
                # Or (x + 1, y + 7)
                if is_valid(self.x + x_offset + 1, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2):
                    cells.append(CellState(self.x + x_offset + 1, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2, 
                                 Direction.SOUTH, self.obstacle_id, FAR_SCREENSHOT_COST))
                # Or (x - 1, y + 7)
                if is_valid(self.x + x_offset - 1, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2):
                    cells.append(CellState(self.x + x_offset - 1, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2, 
                                 Direction.SOUTH, self.obstacle_id, FAR_SCREENSHOT_COST))
                # Or (x + 2, y + 8)
                if is_valid(self.x + x_offset + 2, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 3):
                    cells.append(CellState(self.x + x_offset + 2, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 3, 
                                 Direction.SOUTH, self.obstacle_id, OFFSIDED_SCREENSHOT_COST))
                # Or (x - 2, y + 8)
                if is_valid(self.x + x_offset - 2, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 3):
                    cells.append(CellState(self.x + x_offset - 2, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 3, 
                                 Direction.SOUTH, self.obstacle_id, OFFSIDED_SCREENSHOT_COST))

            elif retrying == True:
                # Or (x, y + 4)
                if is_valid(self.x + x_offset, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 1):
                    cells.append(CellState(self.x + x_offset, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 1, 
                                 Direction.SOUTH, self.obstacle_id, BEST_SCREENSHOT_COST))
                # Or (x + 1, y + 4)
                if is_valid(self.x + x_offset + 1, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 1):
                    cells.append(CellState(self.x + x_offset + 1, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 1, 
                                 Direction.SOUTH, self.obstacle_id, OFFSIDED_SCREENSHOT_COST))
                # Or (x - 1, y + 4)
                if is_valid(self.x + x_offset - 1, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 1):
                    cells.append(CellState(self.x + x_offset - 1, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 1, 
                                 Direction.SOUTH, self.obstacle_id, OFFSIDED_SCREENSHOT_COST))
                # Or (x, y + 5)
                if is_valid(self.x + x_offset, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2):
                    cells.append(CellState(self.x + x_offset, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2, 
                                 Direction.SOUTH, self.obstacle_id, FAR_SCREENSHOT_COST))
                # Or (x + 1, y + 8)
                if is_valid(self.x + x_offset + 1, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2):
                    cells.append(CellState(self.x + x_offset + 1, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2, 
                                 Direction.SOUTH, self.obstacle_id, FAR_OFFSIDED_SCREENSHOT_COST))
                # Or (x - 1, y + 8)
                if is_valid(self.x + x_offset - 1, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2):
                    cells.append(CellState(self.x + x_offset - 1, self.y + y_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2, 
                                 Direction.SOUTH, self.obstacle_id, FAR_OFFSIDED_SCREENSHOT_COST))

        # If obstacle is facing south, then robot's cell state must be facing north
        elif self.direction == Direction.SOUTH:
            y_offset = 0
            x_offset = 1

            if retrying == False:
                # Or (x, y - 5)
                if is_valid(self.x + x_offset, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE):
                    cells.append(CellState(self.x + x_offset, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE, 
                                 Direction.NORTH, self.obstacle_id, BEST_SCREENSHOT_COST))
                # Or (x, y - 6)
                if is_valid(self.x + x_offset, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 1):
                    cells.append(CellState(self.x + x_offset, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 1, 
                                 Direction.NORTH, self.obstacle_id, BEST_SCREENSHOT_COST))
                # Or (x, y - 7)
                if is_valid(self.x + x_offset, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2):
                    cells.append(CellState(self.x + x_offset, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2, 
                                 Direction.NORTH, self.obstacle_id, BEST_SCREENSHOT_COST))
                # Or (x + 1, y - 7)
                if is_valid(self.x + x_offset + 1, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2):
                    cells.append(CellState(self.x + x_offset + 1, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2, 
                                 Direction.NORTH, self.obstacle_id, FAR_SCREENSHOT_COST))
                # Or (x - 1, y - 7)
                if is_valid(self.x + x_offset - 1, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2):
                    cells.append(CellState(self.x + x_offset - 1, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2, 
                                 Direction.NORTH, self.obstacle_id, FAR_SCREENSHOT_COST))
                # Or (x + 2, y - 8)
                if is_valid(self.x + x_offset + 2, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 3):
                    cells.append(CellState(self.x + x_offset + 2, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 3, 
                                 Direction.NORTH, self.obstacle_id, OFFSIDED_SCREENSHOT_COST))
                # Or (x - 2, y - 8)
                if is_valid(self.x + x_offset - 2, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 3):
                    cells.append(CellState(self.x + x_offset - 2, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 3, 
                                 Direction.NORTH, self.obstacle_id, OFFSIDED_SCREENSHOT_COST))
            
            elif retrying == True:
                # Or (x, y - 4)
                if is_valid(self.x + x_offset, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 1):
                    cells.append(CellState(self.x + x_offset, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 1, 
                                 Direction.NORTH, self.obstacle_id, BEST_SCREENSHOT_COST))
                # Or (x + 1, y - 4)
                if is_valid(self.x + x_offset + 1, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 1):
                    cells.append(CellState(self.x + x_offset + 1, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 1, 
                                 Direction.NORTH, self.obstacle_id, OFFSIDED_SCREENSHOT_COST))
                # Or (x - 1, y - 4)
                if is_valid(self.x + x_offset - 1, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 1):
                    cells.append(CellState(self.x + x_offset - 1, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 1, 
                                 Direction.NORTH, self.obstacle_id, OFFSIDED_SCREENSHOT_COST))
                # Or (x, y - 5)
                if is_valid(self.x + x_offset, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2):
                    cells.append(CellState(self.x + x_offset, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2, 
                                 Direction.NORTH, self.obstacle_id, FAR_SCREENSHOT_COST))
                # Or (x + 1, y - 5)
                if is_valid(self.x + x_offset + 1, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2):
                    cells.append(CellState(self.x + x_offset + 1, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2, 
                                 Direction.NORTH, self.obstacle_id, FAR_OFFSIDED_SCREENSHOT_COST))
                # Or (x - 1, y - 5)
                if is_valid(self.x + x_offset - 1, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2):
                    cells.append(CellState(self.x + x_offset - 1, self.y + y_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2, 
                                 Direction.NORTH, self.obstacle_id, FAR_OFFSIDED_SCREENSHOT_COST))

        # If obstacle is facing east, then robot's cell state must be facing west
        elif self.direction == Direction.EAST:
            y_offset = 1
            x_offset = 2

            if retrying == False:
                # Or (x + 5, y)
                if is_valid(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE, self.y + y_offset):
                    cells.append(CellState(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE,
                                 self.y + y_offset, Direction.WEST, self.obstacle_id, BEST_SCREENSHOT_COST))
                # Or (x + 6, y)
                if is_valid(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 1, self.y + y_offset):
                    cells.append(CellState(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 1,
                                 self.y + y_offset, Direction.WEST, self.obstacle_id, BEST_SCREENSHOT_COST))
                # Or (x + 7, y)
                if is_valid(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2, self.y + y_offset):
                    cells.append(CellState(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2,
                                 self.y + y_offset, Direction.WEST, self.obstacle_id, BEST_SCREENSHOT_COST))
                # Or (x + 7, y + 1)
                if is_valid(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2, self.y + y_offset + 1):
                    cells.append(CellState(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2,
                                 self.y + y_offset + 1, Direction.WEST, self.obstacle_id, FAR_SCREENSHOT_COST))
                # Or (x + 7, y - 1)
                if is_valid(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2, self.y + y_offset - 1):
                    cells.append(CellState(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2,
                                 self.y + y_offset - 1, Direction.WEST, self.obstacle_id, FAR_SCREENSHOT_COST))
                # Or (x + 8, y + 2)
                if is_valid(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 3, self.y + y_offset + 2):
                    cells.append(CellState(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 3,
                                 self.y + y_offset + 2, Direction.WEST, self.obstacle_id, OFFSIDED_SCREENSHOT_COST))
                # Or (x + 8, y - 2)
                if is_valid(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 3, self.y + y_offset - 2):
                    cells.append(CellState(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 3,
                                 self.y + y_offset - 2, Direction.WEST, self.obstacle_id, OFFSIDED_SCREENSHOT_COST))

            elif retrying == True:
                # Or (x + 4, y)
                if is_valid(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 1, self.y + y_offset):
                    cells.append(CellState(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 1,
                                 self.y + y_offset, Direction.WEST, self.obstacle_id, BEST_SCREENSHOT_COST))
                # Or (x + 4, y - 1)
                if is_valid(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 1, self.y + y_offset - 1):
                    cells.append(CellState(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 1,
                                 self.y + y_offset - 1, Direction.WEST, self.obstacle_id, OFFSIDED_SCREENSHOT_COST))
                # Or (x + 4, y + 1)
                if is_valid(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 1, self.y + y_offset + 1):
                    cells.append(CellState(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 1,
                                 self.y + y_offset + 1, Direction.WEST, self.obstacle_id, OFFSIDED_SCREENSHOT_COST))
                # Or (x + 5, y)
                if is_valid(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2, self.y + y_offset):
                    cells.append(CellState(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2,
                                 self.y + y_offset, Direction.WEST, self.obstacle_id, FAR_SCREENSHOT_COST))
                # Or (x + 5, y + 1)
                if is_valid(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2, self.y + y_offset + 1):
                    cells.append(CellState(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2,
                                 self.y + y_offset + 1, Direction.WEST, self.obstacle_id, FAR_OFFSIDED_SCREENSHOT_COST))
                # Or (x + 5, y - 1)
                if is_valid(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2, self.y + y_offset - 1):
                    cells.append(CellState(self.x + x_offset + OPTIMAL_IMAGE_VIEWING_DISTANCE + 2,
                                 self.y + y_offset - 1, Direction.WEST, self.obstacle_id, FAR_OFFSIDED_SCREENSHOT_COST))


        # If obstacle is facing west, then robot's cell state must be facing east
        elif self.direction == Direction.WEST:
            y_offset = 1
            x_offset = 0

            if retrying == False:
                # Or (x - 5, y)
                if is_valid(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE, self.y + y_offset):
                    cells.append(CellState(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE,
                                 self.y + y_offset, Direction.EAST, self.obstacle_id, BEST_SCREENSHOT_COST))
                # Or (x - 6, y)
                if is_valid(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 1, self.y + y_offset):
                    cells.append(CellState(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 1,
                                 self.y + y_offset, Direction.EAST, self.obstacle_id, BEST_SCREENSHOT_COST))
                # Or (x - 7, y)
                if is_valid(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2, self.y + y_offset):
                    cells.append(CellState(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2,
                                 self.y + y_offset, Direction.EAST, self.obstacle_id, BEST_SCREENSHOT_COST))
                # Or (x - 7, y + 1)
                if is_valid(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2, self.y + y_offset + 1):
                    cells.append(CellState(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2,
                                 self.y + y_offset + 1, Direction.EAST, self.obstacle_id, OFFSIDED_SCREENSHOT_COST))
                # # Or (x - 7, y - 1)
                if is_valid(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2, self.y + y_offset - 1):
                    cells.append(CellState(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2,
                                 self.y + y_offset - 1, Direction.EAST, self.obstacle_id, OFFSIDED_SCREENSHOT_COST))
                # Or (x - 8, y + 2)
                if is_valid(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 3, self.y + y_offset + 2):
                    cells.append(CellState(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 3, 
                                 self.y + y_offset + 2, Direction.EAST, self.obstacle_id, FAR_OFFSIDED_SCREENSHOT_COST))
                # Or (x - 8, y - 2)
                if is_valid(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 3, self.y + y_offset - 2):
                    cells.append(CellState(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 3,
                                 self.y + y_offset - 2, Direction.EAST, self.obstacle_id, FAR_OFFSIDED_SCREENSHOT_COST))

            elif retrying == True:
                # Or (x - 4, y)
                if is_valid(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 1, self.y + y_offset):
                    cells.append(CellState(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 1,
                                 self.y + y_offset, Direction.EAST, self.obstacle_id, BEST_SCREENSHOT_COST))
                # Or (x - 4, y + 1)
                if is_valid(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 1, self.y + y_offset + 1):
                    cells.append(CellState(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 1,
                                 self.y + y_offset + 1, Direction.EAST, self.obstacle_id, OFFSIDED_SCREENSHOT_COST))
                # Or (x - 4, y - 1)
                if is_valid(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 1, self.y + y_offset - 1):
                    cells.append(CellState(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 1,
                                 self.y + y_offset - 1, Direction.EAST, self.obstacle_id, OFFSIDED_SCREENSHOT_COST))
                # Or (x - 5, y)
                if is_valid(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2, self.y + y_offset):
                    cells.append(CellState(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2,
                                 self.y + y_offset, Direction.EAST, self.obstacle_id, FAR_SCREENSHOT_COST))
                # Or (x - 5, y - 1)
                if is_valid(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2, self.y + y_offset - 1):
                    cells.append(CellState(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2,
                                 self.y + y_offset - 1, Direction.EAST, self.obstacle_id, FAR_OFFSIDED_SCREENSHOT_COST))
                # Or (x - 5, y + 1)
                if is_valid(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2, self.y + y_offset + 1):
                    cells.append(CellState(self.x + x_offset - OPTIMAL_IMAGE_VIEWING_DISTANCE - 2,
                                 self.y + y_offset + 1, Direction.EAST, self.obstacle_id, FAR_OFFSIDED_SCREENSHOT_COST))
                    

        return cells
