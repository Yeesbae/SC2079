import heapq
import math
import time
from typing import List
import numpy as np
from Entities.Bot import Robot
from Entities.Cell import CellState
from Entities.Obstacle import Obstacle
from Entities.Grid import Grid
from constants import Direction, MOVE_DIRECTION, TURN_FACTOR, ITERATIONS, TURN_RADIUS, SAFE_COST, SMALL_TURN, OBSTACLE_ROBOT_GUARD_DIM
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
        self.safe_cost_map = self.build_safe_cost_map()

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


    # def perform_turn(self, turn_instruction: str, max_reverse_steps=10):
    #     """
    #     Compute a safe 90° turn (LEFT or RIGHT) as a full path.
    #     If turn is blocked, reverse step by step until a turn is possible.
    #     Returns: List[CellState] representing the maneuver
    #     """
    #     start_state = self.robot.get_start_state()
    #     target_dir = self.get_target_direction(start_state.direction, turn_instruction)

    #     path = []
    #     states_to_try = [(start_state, 0)]  # tuple of (state, reverse_steps_done)
    #     visited = set()

    #     while states_to_try:
    #         state, reverse_steps = states_to_try.pop(0)
    #         if (state.x, state.y, state.direction) in visited:
    #             continue
    #         visited.add((state.x, state.y, state.direction))

    #         # 1️⃣ Try turning in place
    #         neighbors = self.get_neighbors(state.x, state.y, state.direction)
    #         for nx, ny, new_dir, _ in neighbors:
    #             if new_dir == target_dir:
    #                 # Turn possible, return full path
    #                 turn_path = path + [CellState(nx, ny, new_dir)]
    #                 return turn_path

    #         # 2️⃣ If turn blocked, reverse one step if allowed
    #         if reverse_steps < max_reverse_steps:
    #             reversed_state = self.try_reverse_one_step(state)
    #             if reversed_state:
    #                 path.append(reversed_state)
    #                 states_to_try.append((reversed_state, reverse_steps + 1))

    #     raise RuntimeError("Could not find safe turn path after reversing.")


    def get_target_direction(self, current_dir, instruction):
        if instruction == "LEFT":
            return {
                Direction.NORTH: Direction.WEST,
                Direction.WEST: Direction.SOUTH,
                Direction.SOUTH: Direction.EAST,
                Direction.EAST: Direction.NORTH
            }[current_dir]

        elif instruction == "RIGHT":
            return {
                Direction.NORTH: Direction.EAST,
                Direction.EAST: Direction.SOUTH,
                Direction.SOUTH: Direction.WEST,
                Direction.WEST: Direction.NORTH
            }[current_dir]


    # def try_reverse_one_step(self, state: CellState):
    #     """
    #     Reverse 1 grid step safely.
    #     Returns new CellState or None if blocked.
    #     """

    #     for dx, dy, md in MOVE_DIRECTION:
    #         if md == state.direction:
    #             back_x = state.x - dx
    #             back_y = state.y - dy

    #             if self.grid.reachable(back_x, back_y):
    #                 return CellState(back_x, back_y, state.direction)

    #     return None


    def reset_obstacles(self):
        self.grid.reset_obstacles()

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

    @staticmethod
    def get_visit_options(n):
        """Generate all possible n-digit binary strings

        Args:
            n (int): number of digits in binary string to generate

        Returns:
            List: list of all possible n-digit binary strings
        """
        s = []
        l = bin(2 ** n - 1).count('1')

        for i in range(2 ** n):
            s.append(bin(i)[2:].zfill(l))

        s.sort(key=lambda x: x.count('1'), reverse=True)
        return s

    def get_optimal_order_dp(self, retrying):
        timings = {}
        start_total = time.perf_counter()

        start_state = self.robot.get_start_state()

        # 1️⃣ Get all view positions (6 per obstacle)
        t0 = time.perf_counter()
        all_view_positions = self.grid.get_view_obstacle_positions(retrying)
        timings["get_view_positions"] = time.perf_counter() - t0
        num_obstacles = len(all_view_positions)

        # 2️⃣ Flatten all states for one-time A* precomputation
        t0 = time.perf_counter()
        all_states = [start_state]
        for views in all_view_positions:
            all_states.extend(views)

        # Precompute all A* paths once
        self.path_cost_generator(all_states)
        timings["a_star_precomputation"] = time.perf_counter() - t0

        # 3️⃣ Build obstacle-level distance matrix
        t0 = time.perf_counter()
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
        timings["build_obstacle_cost_matrix"] = time.perf_counter() - t0

        # 4️⃣ Solve TSP on obstacles only
        t0 = time.perf_counter()
        obstacle_cost[:, 0] = 0  # allow free return to start
        permutation, _ = solve_tsp_dynamic_programming(obstacle_cost)
        timings["solve_tsp"] = time.perf_counter() - t0

        # Remove start index (0)
        t0 = time.perf_counter()
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
        timings["greedy_view_selection"] = time.perf_counter() - t0

        timings["total"] = time.perf_counter() - start_total

        print("Timing breakdown (seconds):")
        for k, v in timings.items():
            print(f"  {k}: {v:.4f}")

        return optimal_path, total_cost


    @staticmethod
    def generate_combination(view_positions, index, current, result, iteration_left):
        if index == len(view_positions):
            result.append(current[:])
            return

        if iteration_left[0] == 0:
            return

        iteration_left[0] -= 1
        for j in range(len(view_positions[index])):
            current.append(j)
            MazeSolver.generate_combination(view_positions, index + 1, current, result, iteration_left)
            current.pop()

    def get_safe_cost(self, x, y):
        """Get the safe cost of a particular x,y coordinate wrt obstacles that are exactly 2 units away from it in both x and y directions

        Args:
            x (int): x-coordinate
            y (int): y-coordinate

        Returns:
            int: safe cost
        """
        for ob in self.grid.obstacles:
            if abs(ob.x-x) == 4 and abs(ob.y-y) == 4:
                return SAFE_COST
            
            if abs(ob.x-x) == 2 and abs(ob.y-y) == 4:
                return SAFE_COST
            
            if abs(ob.x-x) == 4 and abs(ob.y-y) == 2:
                return SAFE_COST

        return 0


    def build_safe_cost_map(self):
        safe_cost_map = [[0 for _ in range(self.grid.size_x)] for _ in range(self.grid.size_y)]
        for ob in self.grid.obstacles:
            for (x, y) in [
                (OBSTACLE_ROBOT_GUARD_DIM, OBSTACLE_ROBOT_GUARD_DIM),
                (-OBSTACLE_ROBOT_GUARD_DIM, -OBSTACLE_ROBOT_GUARD_DIM),
                (-OBSTACLE_ROBOT_GUARD_DIM, OBSTACLE_ROBOT_GUARD_DIM),
                (OBSTACLE_ROBOT_GUARD_DIM, -OBSTACLE_ROBOT_GUARD_DIM),
            ]:
                if self.grid.is_valid_coord(ob.x + x, ob.y + y):
                    safe_cost_map[ob.x + x][ob.y + y] = SAFE_COST
        
        return safe_cost_map

    
    def get_arc_points_from_endpoints(
        self,
        start_x, start_y,
        end_x, end_y,
        start_dir,
        radius=TURN_RADIUS,
        steps=20
    ):
        """
        Generate an arc of a quadrant of a circle given:
        - start position
        - end position
        - start direction
        - radius

        Assumes axis-aligned grid and exact quarter-circle motion.
        """

        dx = end_x - start_x
        dy = end_y - start_y

        # Sanity check: must be a quarter circle
        if abs(dx) != radius or abs(dy) != radius:
            raise ValueError("End point does not form a 90° arc with given radius")

        # Determine arc center candidates
        if start_dir == Direction.NORTH:
            candidates = [
                (start_x + radius, start_y),  # right turn
                (start_x - radius, start_y),  # left turn
            ]
        elif start_dir == Direction.SOUTH:
            candidates = [
                (start_x - radius, start_y),
                (start_x + radius, start_y),
            ]
        elif start_dir == Direction.EAST:
            candidates = [
                (start_x, start_y - radius),
                (start_x, start_y + radius),
            ]
        elif start_dir == Direction.WEST:
            candidates = [
                (start_x, start_y + radius),
                (start_x, start_y - radius),
            ]
        else:
            raise ValueError("Invalid start direction")

        # Pick the center that places both start and end on the circle
        cx = cy = None
        for cxx, cyy in candidates:
            if (
                abs((start_x - cxx)**2 + (start_y - cyy)**2 - radius**2) < 1e-6 and
                abs((end_x - cxx)**2 + (end_y - cyy)**2 - radius**2) < 1e-6
            ):
                cx, cy = cxx, cyy
                break

        if cx is None:
            raise RuntimeError("No valid arc center found")

        # Compute angles
        start_angle = math.atan2(start_y - cy, start_x - cx)
        end_angle   = math.atan2(end_y - cy, end_x - cx)

        # Ensure 90° sweep (choose shortest direction)
        delta = end_angle - start_angle
        if delta > math.pi:
            delta -= 2 * math.pi
        elif delta < -math.pi:
            delta += 2 * math.pi

        # Generate arc points
        points = []
        for i in range(steps + 1):
            t = i / steps
            angle = start_angle + delta * t
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            points.append((x, y))

        return points


    def is_arc_safe(self, arc_points):
        for x, y in arc_points:
            # floor is safer than round for collision detection
            if not self.grid.reachable(math.floor(x), math.floor(y)):
                return False
        return True

    def get_neighbors(self, x, y, direction):
        neighbors = []

        # --- Straight moves ---
        for dx, dy, md in MOVE_DIRECTION:
            if md == direction:
                # Forward
                if self.grid.reachable(x + dx, y + dy):
                    # safe_cost = self.get_safe_cost(x + dx, y + dy)
                    safe_cost = self.safe_cost_map[x + dx][y + dy]
                    neighbors.append((x + dx, y + dy, md, safe_cost))
                # Backward
                if self.grid.reachable(x - dx, y - dy):
                    # safe_cost = self.get_safe_cost(x - dx, y - dy)
                    safe_cost = self.safe_cost_map[x - dx][y - dy]
                    neighbors.append((x - dx, y - dy, md, safe_cost))

        # --- Hardcoded 90° forward and reverse turns ---
        x_change = turn_wrt_big_turns[self.enabled_turn][0]
        y_change = turn_wrt_big_turns[self.enabled_turn][1]

        # Map of valid turns (dx, dy) → resulting end direction
        turn_map = {
            Direction.NORTH: [
                ((x_change, y_change), Direction.EAST),
                ((-x_change, y_change), Direction.WEST),
                ((x_change, -y_change), Direction.WEST),
                ((-x_change, -y_change), Direction.EAST),
            ],
            Direction.SOUTH: [
                ((x_change, -y_change), Direction.EAST),
                ((-x_change, -y_change), Direction.WEST),
                ((x_change, y_change), Direction.WEST),
                ((-x_change, y_change), Direction.EAST),
            ],
            Direction.EAST: [
                ((x_change, y_change), Direction.NORTH),
                ((-x_change, y_change), Direction.SOUTH),
                ((-x_change, -y_change), Direction.NORTH),
                ((x_change, -y_change), Direction.SOUTH),
            ],
            Direction.WEST: [
                ((-x_change, y_change), Direction.NORTH),
                ((-x_change, -y_change), Direction.SOUTH),
                ((x_change, y_change), Direction.SOUTH),
                ((x_change, -y_change), Direction.NORTH), 
            ]
        }

        for (dx, dy), end_dir in turn_map[direction]:
            arc_points = self.get_arc_points_from_endpoints(x, y, x + dx, y + dy, direction, radius=x_change, steps=10)

            if self.is_arc_safe(arc_points):
                safe_cost = self.get_safe_cost(x + dx, y + dy) + 10
                neighbors.append((x + dx, y + dy, end_dir, safe_cost))
                
        return neighbors
    

    # def get_path_to_parking(
    #     self,
    #     parking_x: int,
    #     parking_y: int,
    #     parking_direction: Direction = None
    # ) -> list[CellState]:
    #     """
    #     Compute the optimal path from current robot position to the parking lot.

    #     Args:
    #         parking_x (int): target x-coordinate of parking spot
    #         parking_y (int): target y-coordinate of parking spot
    #         parking_direction (Direction, optional): desired facing at parking. 
    #                                                 Defaults to None (any direction).

    #     Returns:
    #         List[CellState]: full path from current robot state to parking
    #     """
    #     start_state = self.robot.get_start_state()
        
    #     # Create parking CellState
    #     if parking_direction is None:
    #         # If direction not specified, allow any direction (try all 4)
    #         candidate_directions = [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]
    #     else:
    #         candidate_directions = [parking_direction]

    #     best_path = None
    #     best_cost = float('inf')

    #     for dir_candidate in candidate_directions:
    #         parking_state = CellState(parking_x, parking_y, dir_candidate)
            
    #         # Generate path cost table for this start→goal
    #         self.path_cost_generator([start_state, parking_state])

    #         if (start_state, parking_state) not in self.cost_table:
    #             continue

    #         cost = self.cost_table[(start_state, parking_state)]
    #         path = self.path_table[(start_state, parking_state)]

    #         if cost < best_cost:
    #             best_cost = cost
    #             best_path = [CellState(x, y, d) for x, y, d in path]

    #     if best_path is None:
    #         raise RuntimeError("No valid path to parking found!")

    #     return best_path


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
                # print(f"while heap: ", time.perf_counter())
                _, cur_x, cur_y, cur_direction = heapq.heappop(heap)
                
                if (cur_x, cur_y, cur_direction) in visited:
                    continue

                if end.is_eq(cur_x, cur_y, cur_direction):
                    record_path(start, end, parent, g_distance[(cur_x, cur_y, cur_direction)])
                    return

                visited.add((cur_x, cur_y, cur_direction))
                cur_distance = g_distance[(cur_x, cur_y, cur_direction)]
                
                for next_x, next_y, new_direction, safe_cost in self.get_neighbors(cur_x, cur_y, cur_direction):
                    # print(f"self.get_neighbors: ", time.perf_counter())
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
        nested_loop_count = 0
        for i in range(len(states) - 1):
            for j in range(i + 1, len(states)):
                nested_loop_count += 1
                print(f"nested loop count: ", nested_loop_count)
                astar_search(states[i], states[j])


if __name__ == "__main__":
    pass
