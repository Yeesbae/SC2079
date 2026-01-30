"""
planning/tsp_solver.py

Solve the Traveling Salesman Problem (TSP) for given viewpoints.
Takes a weighted graph (RS paths between viewpoints) and returns
the optimal visiting sequence and paths.
"""

from itertools import permutations
from typing import List, Tuple, Dict

class TSPSolver:
    """
    Simple TSP solver using brute-force or heuristic approach.
    """

    def __init__(self, graph: Dict[Tuple[Tuple, Tuple], Dict]):
        """
        graph: dict mapping (start_pose, goal_pose) -> {"length": float, "footprints": list}
        """
        self.graph = graph

    def solve(self, nodes_to_visit: List[Tuple[float, float, float]]) -> Tuple[List[Tuple], List[List[Tuple[float, float, float]]]]:
        """
        Solve TSP for the given nodes.
        Returns:
            visiting_order: list of nodes in visiting order
            paths: list of RS paths (list of poses) connecting nodes in order
        """
        n = len(nodes_to_visit)
        if n <= 1:
            return nodes_to_visit, []

        best_order = None
        best_length = float('inf')
        best_paths = None

        # Brute-force all permutations
        for perm in permutations(nodes_to_visit):
            valid = True
            total_length = 0.0
            perm_paths = []

            for i in range(n - 1):
                start = perm[i]
                goal = perm[i + 1]
                edge = self.graph.get((start, goal))
                if edge is None:
                    valid = False  # no valid RS path
                    break
                total_length += edge["length"]
                perm_paths.append(edge["footprints"])

            if valid and total_length < best_length:
                best_length = total_length
                best_order = perm
                best_paths = perm_paths

        if best_order is None:
            raise ValueError("No valid TSP path found")

        return list(best_order), best_paths
