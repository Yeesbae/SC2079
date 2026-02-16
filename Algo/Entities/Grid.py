from .Cell import CellState
from typing import List
from constants import Direction, ROBOT_HALF_CELLS, OBSTACLE_SIZE_CELLS
from .Obstacle import Obstacle
from Util.helper import overlap

class Grid:
    """
    Grid object that contains the size of the grid and a list of obstacles
    """
    def __init__(self, size_x: int, size_y: int):
        """
        Args:
            size_x (int): Size of the grid in the x direction
            size_y (int): Size of the grid in the y direction
        """
        self.size_x = size_x
        self.size_y = size_y
        self.obstacles: List[Obstacle] = []

    def add_obstacle(self, obstacle: Obstacle):
        """Add a new obstacle to the Grid object, ignores if duplicate obstacle

        Args:
            obstacle (Obstacle): Obstacle to be added
        """
        # Loop through the existing obstacles to check for duplicates
        to_add = True
        for ob in self.obstacles:
            if ob == obstacle:
                to_add = False
                break

        if to_add:
            self.obstacles.append(obstacle)

    def remove_obstacle(self, obstacle_id: int):
        """Add a new obstacle to the Grid object, ignores if duplicate obstacle

        Args:
            obstacle (Obstacle): Obstacle to be added
        """
        # Loop through the existing obstacles to check for duplicates
        for ob in self.obstacles:
            if ob.obstacle_id == obstacle_id:
                self.obstacles.remove(ob)
                break

    def reset_obstacles(self):
        """
        Resets the obstacles in the grid
        """
        self.obstacles = []

    def get_obstacles(self):
        """
        Returns the list of obstacles in the grid
        """
        return self.obstacles

    # def reachable(self, x: int, y: int, turn=False, preTurn=False) -> bool:
    #     """Checks whether the given x,y coordinate is reachable/safe. Criterion is as such:
    #     - Must be at least 4 units away in total (x+y) from the obstacle
    #     - Greater distance (x or y distance) must be at least 3 units away from obstacle

    #     Args:
    #         x (int): _description_
    #         y (int): _description_

    #     Returns:
    #         bool: _description_
    #     """
        
    #     if not self.is_valid_coord(x, y):
    #         return False

    #     for ob in self.obstacles:
    #         # print(f"Looking at position x:{x} y:{y} against ob: {ob.x} {ob.y}")
    #         if ob.x == 8 and ob.y <= 8 and x < 8 and y < 8:
    #             # print(f"ob.x: {ob.x} ob.y: {ob.y} x: {x} y:{y} Triggered four bypass")
    #             continue

    #         # if x <= 3 and y <= 4:
    #         #     continue

    #         # Must be at least 4 units away in total (x+y)

    #         if abs(ob.x - x) + abs(ob.y - y) >= 8:
    #             # print(f"ob.x: {ob.x} ob.y: {ob.y} x: {x} y:{y} Triggered more than 3 units bypass")
    #             continue

    #         # If max(x,y) is less than 3 units away, consider not reachable
    #         # if max(abs(ob.x - x), abs(ob.y - y)) < EXPANDED_CELL * 2 + 1:

    #         if turn:
    #             if max(abs(ob.x - x), abs(ob.y - y)) < ROBOT_HALF_CELLS * 2 + 1:
    #                 # if ob.x == 0 and ob.y == 10 and x == 1 and y == 12:
    #                 #     print(f"ob.x: {ob.x} ob.y: {ob.y} x: {x} y:{y} Triggered less than 3 max units trap")
    #                 return False
                
    #         if preTurn:
    #             if max(abs(ob.x - x), abs(ob.y - y)) < ROBOT_HALF_CELLS * 2 + 1:
    #                 # if ob.x == 0 and ob.y == 10 and x == 1 and y == 12:
    #                 #     print(f"ob.x: {ob.x} ob.y: {ob.y} x: {x} y:{y} Triggered less than 3 max units trap")
    #                 return False
                
    #         else:
    #             if max(abs(ob.x - x), abs(ob.y - y)) < 4:
    #                 # print(f"ob.x: {ob.x} ob.y: {ob.y} x: {x} y:{y} Triggered less than 3 max units trap")
    #                 return False

    #     return True

    def reachable(self, x: int, y: int) -> bool:
        """Checks whether the given x, y coordinate is reachable/safe. Criterion is as such:
        - Given a target coordinate of robot, iterate through the available obstacles, 
          get the 4 coordinates of all 4 corners of the car & obstacles, are there
          no overlap between them?
          - If no overlap return Yes (reachable)
          - Otherwise, return No (Not reachable)

        Args:
            x (int): x coordinate of the target square
            y (int): y coordinate of the target square

        Returns:
            bool: is the square safely reachable?
        """
        
        if not self.is_valid_coord(x, y):
            return False
        
        # Always in format of [
        #   TOP_LEFT, 
        #   TOP_RIGHT, 
        #   BOTTOM_LEFT, 
        #   BOTTOM_RIGHT,
        # ]
        target_robot_coor = (
            (x - ROBOT_HALF_CELLS, y + ROBOT_HALF_CELLS),
            (x + ROBOT_HALF_CELLS, y + ROBOT_HALF_CELLS),
            (x - ROBOT_HALF_CELLS, y - ROBOT_HALF_CELLS),
            (x + ROBOT_HALF_CELLS, y - ROBOT_HALF_CELLS),
        )
        
        for ob in self.obstacles:
            ob_coor = (
                (ob.x,                       ob.y + OBSTACLE_SIZE_CELLS),
                (ob.x + OBSTACLE_SIZE_CELLS, ob.y + OBSTACLE_SIZE_CELLS),
                (ob.x,                       ob.y                      ),
                (ob.x + OBSTACLE_SIZE_CELLS, ob.y                      ),
            )

            if (overlap(target_robot_coor, ob_coor)):
                return False

        return True

    def is_valid_coord(self, x: int, y: int) -> bool:
        """Checks if given position is within bounds

        Args:
            x (int): x-coordinate
            y (int): y-coordinate

        Returns:
            bool: True if valid, False otherwise
        """
        if x < ROBOT_HALF_CELLS or x >= self.size_x - ROBOT_HALF_CELLS or y < ROBOT_HALF_CELLS or y >= self.size_y - ROBOT_HALF_CELLS:
            return False

        return True

    def is_valid_cell_state(self, state: CellState) -> bool:
        """Checks if given state is within bounds

        Args:
            state (CellState)

        Returns:
            bool: True if valid, False otherwise
        """
        return self.is_valid_coord(state.x, state.y)

    def get_view_obstacle_positions(self, retrying) -> List[List[CellState]]:
        """
        This function return a list of desired states for the robot to achieve based on the obstacle position and direction.
        The state is the position that the robot can see the image of the obstacle and is safe to reach without collision
        :return: [[CellState]]
        """
        # print(f"Inside get_view_obstacle_positions: retrying = {retrying}")
        optimal_positions = []
        for obstacle in self.obstacles:
            if obstacle.direction == Direction.SKIP:
                continue
            else:
                view_states = [view_state for view_state in obstacle.get_view_state(
                    retrying) if self.reachable(view_state.x, view_state.y)]
            optimal_positions.append(view_states)

        return optimal_positions