import heapq
import math
from typing import List
import numpy as np
from Entities.Bot import Robot
from Entities.Cell import CellState
from Entities.Obstacle import Obstacle
from Entities.Grid import Grid
from Entities.DubinsPath import DubinsPath
from constants import Direction, MOVE_DIRECTION, TURN_FACTOR, ITERATIONS, TURN_RADIUS, SAFE_COST
from python_tsp.exact import solve_tsp_dynamic_programming

# Turning displacements for big/small turns
turn_wrt_big_turns = [[0 * TURN_RADIUS, 0 * TURN_RADIUS], [4 * TURN_RADIUS, 2 * TURN_RADIUS]]

class MazeSolver:
    def __init__(
        self,
        size_x: int,
        size_y: int,
        robot_x: int,
        robot_y: int,
        robot_direction: Direction,
        big_turn=None
    ):
        # Initialize grid and robot
        self.grid = Grid(size_x, size_y)
        self.robot = Robot(robot_x, robot_y, robot_direction)

        # Tables to store paths and costs between CellStates
        self.path_table = dict()
        self.cost_table = dict()
        self.big_turn = int(big_turn) if big_turn is not None else 0

    def add_obstacle(self, x: int, y: int, direction: Direction, obstacle_id: int):
        """Add obstacle to MazeSolver"""
        obstacle = Obstacle(x, y, direction, obstacle_id)
        self.grid.add_obstacle(obstacle)

    def reset_obstacles(self):
        self.grid.reset_obstacles()

    @staticmethod
    def compute_coord_distance(x1, y1, x2, y2, level=1):
        dx, dy = x1 - x2, y1 - y2
        if level == 2:
            return math.sqrt(dx ** 2 + dy ** 2)
        return abs(dx) + abs(dy)

    @staticmethod
    def compute_state_distance(start_state: CellState, end_state: CellState, level=1):
        return MazeSolver.compute_coord_distance(start_state.x, start_state.y, end_state.x, end_state.y, level)

    @staticmethod
    def get_visit_options(n):
        """Generate all n-digit binary strings for obstacle visit options"""
        options = []
        length = bin(2 ** n - 1).count('1')
        for i in range(2 ** n):
            options.append(bin(i)[2:].zfill(length))
        options.sort(key=lambda x: x.count('1'), reverse=True)
        return options

    def get_optimal_order_dp(self, retrying) -> List[CellState]:
        """Compute optimal obstacle visiting order using TSP + Dubins path smoothing"""
        distance = 1e9
        optimal_path = []

        all_view_positions = self.grid.get_view_obstacle_positions(retrying)

        for op in self.get_visit_options(len(all_view_positions)):
            items = [self.robot.get_start_state()]
            cur_view_positions = []

            for idx in range(len(all_view_positions)):
                if op[idx] == '1':
                    items += all_view_positions[idx]
                    cur_view_positions.append(all_view_positions[idx])

            # Generate path costs using Dubins paths
            self.path_cost_generator(items)

            # Generate all combinations of positions to take obstacle pictures
            combination = []
            self.generate_combination(cur_view_positions, 0, [], combination, [ITERATIONS])

            for c in combination:
                visited_candidates = [0]  # robot start
                cur_index = 1
                fixed_cost = 0
                for index, view_position in enumerate(cur_view_positions):
                    visited_candidates.append(cur_index + c[index])
                    fixed_cost += view_position[c[index]].penalty
                    cur_index += len(view_position)

                # Build cost matrix
                n = len(visited_candidates)
                cost_np = np.zeros((n, n))
                for s in range(n - 1):
                    for e in range(s + 1, n):
                        u = items[visited_candidates[s]]
                        v = items[visited_candidates[e]]
                        cost_np[s][e] = self.cost_table.get((u, v), 1e9)
                        cost_np[e][s] = cost_np[s][e]
                cost_np[:, 0] = 0

                permutation, tsp_distance = solve_tsp_dynamic_programming(cost_np)
                if tsp_distance + fixed_cost >= distance:
                    continue

                # Build the final path
                optimal_path = [items[0]]
                distance = tsp_distance + fixed_cost
                for i in range(len(permutation) - 1):
                    from_item = items[visited_candidates[permutation[i]]]
                    to_item = items[visited_candidates[permutation[i + 1]]]
                    cur_path = self.path_table[(from_item, to_item)]
                    for j in range(1, len(cur_path)):
                        optimal_path.append(CellState(cur_path[j][0], cur_path[j][1], cur_path[j][2]))
                    optimal_path[-1].set_screenshot(to_item.screenshot_id)

            if optimal_path:
                break

        return optimal_path, distance

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
        for ob in self.grid.obstacles:
            if (abs(ob.x - x), abs(ob.y - y)) in [(2, 2), (1, 2), (2, 1)]:
                return SAFE_COST
        return 0

    def get_neighbors(self, x, y, direction):
        """Return neighbors with possible turns and safe cost"""
        forward_dx, forward_dy = 0, 0
        if direction == Direction.NORTH:
            forward_dy = 1
        elif direction == Direction.SOUTH:
            forward_dy = -1
        elif direction == Direction.EAST:
            forward_dx = 1
        elif direction == Direction.WEST:
            forward_dx = -1

        neighbors = []
        intermediate_x = x + forward_dx
        intermediate_y = y + forward_dy

        for dx, dy, md in MOVE_DIRECTION:
            if md == direction:
                # straight move
                for nx, ny in [(x + dx, y + dy), (x - dx, y - dy)]:
                    if self.grid.reachable(nx, ny):
                        neighbors.append((nx, ny, md, self.get_safe_cost(nx, ny)))
            else:
                # turning moves (4-2 or 3-1 displacement)
                bigger_change = turn_wrt_big_turns[self.big_turn][0]
                smaller_change = turn_wrt_big_turns[self.big_turn][1]

                # All 8 turn cases
                new_positions = self.compute_turn_positions(x, y, direction, md, intermediate_x, intermediate_y, bigger_change, smaller_change)
                neighbors.extend(new_positions)

        return neighbors

    def compute_turn_positions(self, x, y, direction, md, intermediate_x, intermediate_y, big, small):
        """Helper to compute turn neighbors"""
        positions = []
        # Map all direction combinations with their (+/-) displacement
        delta_map = {
            (Direction.NORTH, Direction.EAST): [(big, small), (-small, -big)],
            (Direction.EAST, Direction.NORTH): [(small, big), (-big, -small)],
            (Direction.EAST, Direction.SOUTH): [(small, -big), (-big, small)],
            (Direction.SOUTH, Direction.EAST): [(big, -small), (-small, big)],
            (Direction.SOUTH, Direction.WEST): [(-big, -small), (small, big)],
            (Direction.WEST, Direction.SOUTH): [(-small, -big), (big, small)],
            (Direction.WEST, Direction.NORTH): [(-big, small), (small, -small)],
            (Direction.NORTH, Direction.WEST): [(-small, -big), (big, -small)]
        }

        for dx, dy in delta_map.get((direction, md), []):
            if self.grid.reachable(intermediate_x, intermediate_y) and self.grid.reachable(x + dx, y + dy, turn=True) and self.grid.reachable(x, y, preTurn=True):
                positions.append((x + dx, y + dy, md, self.get_safe_cost(x + dx, y + dy) + 10))
        return positions

    def path_cost_generator(self, states: List[CellState]):
        """Generate paths and costs using DubinsPath between all state pairs"""
        for i in range(len(states) - 1):
            for j in range(i + 1, len(states)):
                start = states[i]
                end = states[j]
                # Skip if already computed
                if (start, end) in self.path_table:
                    continue
                # Compute Dubins path
                dp = DubinsPath(
                    (start.x, start.y, start.direction.to_radians()),
                    (end.x, end.y, end.direction.to_radians()),
                    TURN_RADIUS
                )
                path_points = dp.refine_path(step_size=0.5)

                # Compute real distance along Dubins path
                cost = 0.0
                for k in range(len(path_points) - 1):
                    dx = path_points[k + 1].x - path_points[k].x
                    dy = path_points[k + 1].y - path_points[k].y
                    cost += math.hypot(dx, dy)

                # Store in tables
                self.cost_table[(start, end)] = cost
                self.cost_table[(end, start)] = cost
                self.path_table[(start, end)] = [(c.x, c.y, c.direction) for c in path_points]
                self.path_table[(end, start)] = [(c.x, c.y, c.direction) for c in reversed(path_points)]


if __name__ == "__main__":
    # Example usage
    solver = MazeSolver(10, 10, 0, 0, Direction.NORTH)
    solver.add_obstacle(5, 5, Direction.EAST, 1)
    optimal_path, dist = solver.get_optimal_order_dp(retrying=True)
    print("Optimal path length:", dist)
    print("Path:", optimal_path)
