import heapq
import math
from itertools import permutations
from sre_parse import State

from Algo.constants import DIR_VECTORS, GRID_SIZE, PHOTO_DISTANCE, Direction

def get_view_positions(obstacle):
    ox, oy = obstacle
    d = PHOTO_DISTANCE // GRID_SIZE

    return [
        State(ox, oy - d, Direction.NORTH),
        State(ox + d, oy, Direction.WEST),
        State(ox, oy + d, Direction.SOUTH),
        State(ox - d, oy, Direction.EAST),
    ]

def astar(grid, start, goal):
    pq = []
    heapq.heappush(pq, (0, start))
    cost = {start: 0}
    parent = {start: None}

    while pq:
        _, cur = heapq.heappop(pq)

        if cur == goal:
            break

        for nxt, step_cost in neighbors(grid, cur):
            new_cost = cost[cur] + step_cost
            if nxt not in cost or new_cost < cost[nxt]:
                cost[nxt] = new_cost
                priority = new_cost + heuristic(nxt, goal)
                heapq.heappush(pq, (priority, nxt))
                parent[nxt] = cur

    return cost.get(goal, math.inf)

def neighbors(grid, state):
    results = []

    # forward
    dx, dy = DIR_VECTORS[state.direction]
    nx, ny = state.x + dx, state.y + dy
    if grid.is_free(nx, ny):
        results.append((State(nx, ny, state.direction), 1))

    # turn left / right (in-place rotation)
    left = Direction((state.direction.value - 1) % 4)
    right = Direction((state.direction.value + 1) % 4)

    results.append((State(state.x, state.y, left), 2))
    results.append((State(state.x, state.y, right), 2))

    return results

def heuristic(a, b):
    return abs(a.x - b.x) + abs(a.y - b.y)

def solve_tsp(start, obstacle_views, grid):
    best_cost = math.inf
    best_order = None

    for perm in permutations(range(len(obstacle_views))):
        cost = 0
        cur = start

        for i in perm:
            goal = obstacle_views[i][0]  # pick first view pose
            c = astar(grid, cur, goal)
            if c == math.inf:
                cost = math.inf
                break
            cost += c
            cur = goal

        if cost < best_cost:
            best_cost = cost
            best_order = perm

    return best_order
