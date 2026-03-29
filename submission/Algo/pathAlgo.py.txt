import heapq
import math
import time
from typing import List
import numpy as np
from Entities.Bot import Robot
from Entities.Cell import CellState
from Entities.Obstacle import Obstacle
from Entities.Grid import Grid
from constants import Direction, MOVE_DIRECTION, TURN_FACTOR, NORTH_LEFT_MASK, NORTH_BACKWARD_LEFT_MASK, TURN_RADIUS, SMALL_TURN
from python_tsp.exact import solve_tsp_dynamic_programming

turn_wrt_big_turns = [[0 * TURN_RADIUS, 0 * TURN_RADIUS], SMALL_TURN]

# 'FW60', 'BL00', 'FW30', 'BR00', 'FW30', 'BR00', 'SNAP1_C', 'FIN'
class MazeSolver:
    def __init__(
            self,
            size_x: int,
            size_y: int,
            robot_x: int,
            robot_y: int,
            robot_direction: Direction,
            enabled_turn: int = 1,
    ):
        # Initialize a Grid object for the arena representation
        self.grid = Grid(size_x, size_y)
        # Initialize a Robot object for robot representation
        self.robot = Robot(robot_x, robot_y, robot_direction)
        # Create tables for paths and costs
        self.path_table = dict()
        self.cost_table = dict()
        self.enabled_turn = int(enabled_turn)

    def add_obstacle(self, x: int, y: int, direction: Direction, obstacle_id: int):
        """Add obstacle to MazeSolver object

        Args:
            x (int): x coordinate of obstacle
            y (int): y coordinate of obstacle
            direction (Direction): Direction of obstacle
            obstacle_id (int): ID of obstacle
        """
        # Create an obstacle object
        obstacle = Obstacle(x, y, direction, obstacle_id)
        # Add created obstacle to grid object
        self.grid.add_obstacle(obstacle)

    def add_composite_obstacle(
        self,
        x: int,
        y: int,
        length: int,
        width: int,
        direction: Direction,
        obstacle_id: int
    ):
        """
        Add a rectangular obstacle of dimension length × width (in grid cells),
        constructed by stacking multiple 2×2 Obstacle objects.

        (x, y) is the bottom-left corner.

        If direction != Direction.SKIP:
            - The geometrically centered 2×2 block gets the given direction.
            - All other blocks are Direction.SKIP.
            - Overlap is allowed.
        """

        blocks_x = math.ceil(length / 2)
        blocks_y = math.ceil(width / 2)

        base_id = obstacle_id * 1000
        counter = 0

        center_block_coord = None

        if direction != Direction.SKIP:
            center_x = x + length / 2
            center_y = y + width / 2

            center_block_x = int(round(center_x - 1))
            center_block_y = int(round(center_y - 1))

            center_block_coord = (center_block_x, center_block_y)

            obstacle = Obstacle(
                center_block_x,
                center_block_y,
                direction,
                base_id + counter
            )
            self.grid.add_obstacle(obstacle)
            counter += 1

        for i in range(blocks_x):
            for j in range(blocks_y):

                new_x = x + 2 * i
                new_y = y + 2 * j

                if center_block_coord and (new_x, new_y) == center_block_coord:
                    continue

                obstacle = Obstacle(
                    new_x,
                    new_y,
                    Direction.SKIP,
                    base_id + counter
                )

                self.grid.add_obstacle(obstacle)
                counter += 1


    @staticmethod
    def compute_coord_distance(x1: int, y1: int, x2: int, y2: int, level=1):
        """Compute the L-n distance between two coordinates

        Args:
            x1 (int)
            y1 (int)
            x2 (int)
            y2 (int)
            level (int, optional): L-n distance to compute. Defaults to 1.

        Returns:
            float: L-n distance between the two given points
        """
        horizontal_distance = x1 - x2
        vertical_distance = y1 - y2

        # Euclidean distance
        if level == 2:
            return math.sqrt(horizontal_distance ** 2 + vertical_distance ** 2)

        return abs(horizontal_distance) + abs(vertical_distance)

    @staticmethod
    def compute_state_distance(start_state: CellState, end_state: CellState, level=1):
        """Compute the L-n distance between two cell states

        Args:
            start_state (CellState): Start cell state
            end_state (CellState): End cell state
            level (int, optional): L-n distance to compute. Defaults to 1.

        Returns:
            float: L-n distance between the two given cell states
        """
        return MazeSolver.compute_coord_distance(start_state.x, start_state.y, end_state.x, end_state.y, level)


    def get_optimal_order_dp(self, retrying):
        # timings = {}
        # start_total = time.perf_counter()

        start_state = self.robot.get_start_state()

        # 1️⃣ Get all view positions (6 per obstacle)
        # t0 = time.perf_counter()
        all_view_positions = self.grid.get_view_obstacle_positions(retrying)
        # timings["get_view_positions"] = time.perf_counter() - t0
        num_obstacles = len(all_view_positions)

        # 2️⃣ Flatten all states for one-time A* precomputation
        # t0 = time.perf_counter()
        all_states = [start_state]
        for views in all_view_positions:
            all_states.extend(views)

        # Precompute all A* paths once
        self.path_cost_generator(all_states)
        # timings["a_star_precomputation"] = time.perf_counter() - t0

        # 3️⃣ Build obstacle-level distance matrix
        # t0 = time.perf_counter()
        obstacle_cost = np.zeros((num_obstacles + 1, num_obstacles + 1))

        # index 0 = start
        for i in range(num_obstacles):
            # start → obstacle i
            min_cost = float('inf')
            for v in all_view_positions[i]:
                if (start_state, v) in self.cost_table:
                    min_cost = min(min_cost, self.cost_table[(start_state, v)])
            obstacle_cost[0][i + 1] = min_cost
            obstacle_cost[i + 1][0] = min_cost

        # obstacle → obstacle
        for i in range(num_obstacles):
            for j in range(i + 1, num_obstacles):
                min_cost = float('inf')
                for v1 in all_view_positions[i]:
                    for v2 in all_view_positions[j]:
                        if (v1, v2) in self.cost_table:
                            min_cost = min(min_cost, self.cost_table[(v1, v2)])

                obstacle_cost[i + 1][j + 1] = min_cost
                obstacle_cost[j + 1][i + 1] = min_cost
        # timings["build_obstacle_cost_matrix"] = time.perf_counter() - t0

        # 4️⃣ Solve TSP on obstacles only
        # t0 = time.perf_counter()
        obstacle_cost[:, 0] = 0  # allow free return to start
        permutation, _ = solve_tsp_dynamic_programming(obstacle_cost)
        # timings["solve_tsp"] = time.perf_counter() - t0

        # Remove start index (0)
        # t0 = time.perf_counter()
        visit_order = [idx - 1 for idx in permutation if idx != 0]

        # 5️⃣ Greedy view selection along obstacle order
        optimal_path = [start_state]
        total_cost = 0

        current_state = start_state

        for obs_idx in visit_order:

            best_view = None
            best_cost = float('inf')

            for view in all_view_positions[obs_idx]:
                if (current_state, view) in self.cost_table:
                    cost = self.cost_table[(current_state, view)] + view.penalty
                    if cost < best_cost:
                        best_cost = cost
                        best_view = view

            if best_view is None:
                raise RuntimeError("No reachable view state found.")

            # Append path
            path_segment = self.path_table[(current_state, best_view)]
            for j in range(1, len(path_segment)):
                optimal_path.append(
                    CellState(path_segment[j][0],
                            path_segment[j][1],
                            path_segment[j][2])
                )

            optimal_path[-1].set_screenshot(best_view.screenshot_id)

            total_cost += best_cost
            current_state = best_view
        # timings["greedy_view_selection"] = time.perf_counter() - t0

        # timings["total"] = time.perf_counter() - start_total

        # print("Timing breakdown (seconds):")
        # for k, v in timings.items():
        #     print(f"  {k}: {v:.4f}")

        return optimal_path, total_cost


    def get_safe_cost(self, x, y):
        """Get the safe cost of a particular x,y coordinate wrt obstacles that are exactly 2 units away from it in both x and y directions

        Args:
            x (int): x-coordinate
            y (int): y-coordinate

        Returns:
            int: safe cost
        """
        return 0
    
    
    def is_turn_sweep_safe(self, x, y, direction, turn_type, move_type):
        """
        Returns False if any obstacle blocks the turn.
        Uses NORTH_LEFT_MASK as the base reference frame.
        """

        for ob in self.grid.obstacles:
            dx = ob.x + 1 - x
            dy = ob.y + 1 - y

            # --- Rotate obstacle into NORTH reference frame ---
            if direction == Direction.NORTH:
                rdx, rdy = dx, dy
            elif direction == Direction.EAST:
                rdx, rdy = -dy, dx
            elif direction == Direction.SOUTH:
                rdx, rdy = -dx, -dy
            elif direction == Direction.WEST:
                rdx, rdy = dy, -dx

            # --- Mirror if RIGHT turn ---
            if turn_type == "RIGHT":
                rdx = -rdx

            # --- Check against mask intervals ---
            if move_type == "BACKWARD":
                for dx_min, dx_max, dy_min, dy_max in NORTH_BACKWARD_LEFT_MASK:
                    if dx_min <= rdx <= dx_max and dy_min <= rdy <= dy_max:
                        return False
            else:
                for dx_min, dx_max, dy_min, dy_max in NORTH_LEFT_MASK:
                    if dx_min <= rdx <= dx_max and dy_min <= rdy <= dy_max:
                        return False

        return True


    def get_neighbors(self, x, y, direction):
        neighbors = []

        # --- Straight moves ---
        for dx, dy, md in MOVE_DIRECTION:
            if md == direction:
                # Forward
                if self.grid.reachable(x + dx, y + dy):
                    safe_cost = self.get_safe_cost(x + dx, y + dy)
                    neighbors.append((x + dx, y + dy, md, safe_cost))
                # Backward
                if self.grid.reachable(x - dx, y - dy):
                    safe_cost = self.get_safe_cost(x - dx, y - dy)
                    neighbors.append((x - dx, y - dy, md, safe_cost))

        # --- Hardcoded 90° forward and reverse turns ---
        x_change = turn_wrt_big_turns[self.enabled_turn][0]
        y_change = turn_wrt_big_turns[self.enabled_turn][1]

        # Map of valid turns (dx, dy) → resulting end direction
        turn_values_map = {
            "RF": (8, 5),
            "LF": (8, 5),
            "RB": (5, 8),
            "LB": (5, 8)
        }
        turn_map = {
            Direction.NORTH: [
                ((turn_values_map["RF"][0], turn_values_map["RF"][1]), Direction.EAST, "RIGHT", "FORWARD"),
                ((-turn_values_map["LF"][0], turn_values_map["LF"][1]), Direction.WEST, "LEFT", "FORWARD"),
                ((turn_values_map["RB"][0], -turn_values_map["RB"][1]), Direction.WEST, "RIGHT", "BACKWARD"),
                ((-turn_values_map["LB"][0], -turn_values_map["LB"][1]), Direction.EAST, "LEFT", "BACKWARD"),
            ],
            Direction.SOUTH: [
                ((-turn_values_map["RF"][0], -turn_values_map["RF"][1]), Direction.WEST, "RIGHT", "FORWARD"),
                ((turn_values_map["LF"][0], -turn_values_map["LF"][1]), Direction.EAST, "LEFT", "FORWARD"),
                ((-turn_values_map["RB"][0], turn_values_map["RB"][1]), Direction.EAST, "RIGHT", "BACKWARD"),
                ((turn_values_map["LB"][0], turn_values_map["LB"][1]), Direction.WEST, "LEFT", "BACKWARD"),
            ],
            Direction.EAST: [
                ((turn_values_map["RF"][1], -turn_values_map["RF"][0]), Direction.SOUTH, "RIGHT", "FORWARD"),
                ((turn_values_map["LF"][1], turn_values_map["LF"][0]), Direction.NORTH, "LEFT", "FORWARD"),
                ((-turn_values_map["RB"][1], -turn_values_map["RB"][0]), Direction.NORTH, "RIGHT", "BACKWARD"),
                ((-turn_values_map["LB"][1], turn_values_map["LB"][0]), Direction.SOUTH, "LEFT", "BACKWARD"),
            ],
            Direction.WEST: [
                ((-turn_values_map["RF"][1], turn_values_map["RF"][0]), Direction.NORTH, "RIGHT", "FORWARD"),
                ((-turn_values_map["LF"][1], -turn_values_map["LF"][0]), Direction.SOUTH, "LEFT", "FORWARD"),
                ((turn_values_map["RB"][1], turn_values_map["RB"][0]), Direction.SOUTH, "RIGHT", "BACKWARD"),
                ((turn_values_map["LB"][1], -turn_values_map["LB"][0]), Direction.NORTH, "LEFT", "BACKWARD"), 
            ]
        }

        for (dx, dy), end_dir, turn_type, move_type in turn_map[direction]:
            new_x = x + dx
            new_y = y + dy

            if not self.grid.reachable(new_x, new_y):
                continue

            if self.is_turn_sweep_safe(x, y, direction, turn_type, move_type):
                safe_cost = self.get_safe_cost(new_x, new_y) + 10
                neighbors.append((new_x, new_y, end_dir, safe_cost))
                    
        return neighbors
    

    def path_cost_generator(self, states: List[CellState]):
        """Generate the path cost between the input states and update the tables accordingly

        Args:
            states (List[CellState]): cell states to visit
        """
        def record_path(start, end, parent: dict, cost: int):

            # Update cost table for the (start,end) and (end,start) edges
            self.cost_table[(start, end)] = cost
            self.cost_table[(end, start)] = cost

            path = []
            cursor = (end.x, end.y, end.direction)

            while cursor in parent:
                path.append(cursor)
                cursor = parent[cursor]

            path.append(cursor)

            # Update path table for the (start,end) and (end,start) edges, with the (start,end) edge being the reversed path
            self.path_table[(start, end)] = path[::-1]
            self.path_table[(end, start)] = path

        def astar_search(start: CellState, end: CellState):
            # astar search algo with three states: x, y, direction

            # If it is already done before, return
            if (start, end) in self.path_table:
                return

            # Heuristic to guide the search: 'distance' is calculated by f = g + h
            # g is the actual distance moved so far from the start node to current node
            # h is the heuristic distance from current node to end node
            g_distance = {(start.x, start.y, start.direction): 0}

            # format of each item in heap: (f_distance of node, x coord of node, y coord of node)
            # heap in Python is a min-heap
            heap = [(self.compute_state_distance(start, end), start.x, start.y, start.direction)]
            parent = dict()
            visited = set()

            while heap:
                # Pop the node with the smallest distance
                _, cur_x, cur_y, cur_direction = heapq.heappop(heap)
                
                if (cur_x, cur_y, cur_direction) in visited:
                    continue

                if end.is_eq(cur_x, cur_y, cur_direction):
                    record_path(start, end, parent, g_distance[(cur_x, cur_y, cur_direction)])
                    return

                visited.add((cur_x, cur_y, cur_direction))
                cur_distance = g_distance[(cur_x, cur_y, cur_direction)]

                for next_x, next_y, new_direction, safe_cost in self.get_neighbors(cur_x, cur_y, cur_direction):
                    if (next_x, next_y, new_direction) in visited:
                        continue

                    move_cost = Direction.rotation_cost(new_direction, cur_direction) * TURN_FACTOR + 1 + safe_cost

                    # the cost to check if any obstacles that considered too near the robot; if it
                    # safe_cost =

                    # new cost is calculated by the cost to reach current state + cost to move from
                    # current state to new state + heuristic cost from new state to end state
                    next_cost = cur_distance + move_cost + \
                                self.compute_coord_distance(next_x, next_y, end.x, end.y)

                    if (next_x, next_y, new_direction) not in g_distance or \
                            g_distance[(next_x, next_y, new_direction)] > cur_distance + move_cost:
                        g_distance[(next_x, next_y, new_direction)] = cur_distance + move_cost
                        parent[(next_x, next_y, new_direction)] = (cur_x, cur_y, cur_direction)

                        heapq.heappush(heap, (next_cost, next_x, next_y, new_direction))

        # Nested loop through all the state pairings
        for i in range(len(states) - 1):
            for j in range(i + 1, len(states)):
                astar_search(states[i], states[j])


if __name__ == "__main__":
    pass
