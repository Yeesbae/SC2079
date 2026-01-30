"""
planning/maze_solver.py

High-level orchestrator that generates the final path for the robot
to visit all obstacles safely using RS paths and TSP.
"""

from typing import List, Tuple
from geometry import OrientedRectangle
from reeds_shepp_wrapper import RSWrapper
from .viewpoint_generator import ViewpointGenerator
from .graph_builder import GraphBuilder
from .tsp_solver import TSPSolver

class MazeSolver:
    """
    Orchestrates path planning:
    - Generates viewpoints
    - Builds RS graph
    - Solves TSP
    """

    def __init__(self, robot, obstacles: List[OrientedRectangle], rs_wrapper: RSWrapper, step_size: float = 1.0):
        self.robot = robot
        self.obstacles = obstacles
        self.rs_wrapper = rs_wrapper
        self.step_size = step_size

    def solve(self) -> Tuple[List[Tuple[float, float, float]], List[List]]:
        """
        Returns:
            visiting_order: list of robot poses in order
            paths: list of RS paths (list of RobotFootprint) connecting nodes
        """
        # 1. Generate candidate viewpoints
        vp_generator = ViewpointGenerator(self.obstacles)
        viewpoints = vp_generator.generate_all_viewpoints()

        # 2. Build graph
        graph_builder = GraphBuilder(viewpoints, self.obstacles, self.rs_wrapper, step_size=self.step_size)
        graph = graph_builder.build_graph()

        # Flatten all poses for TSP
        all_nodes = []
        for poses in viewpoints.values():
            all_nodes.extend(poses)

        # 3. Solve TSP
        tsp_solver = TSPSolver(graph)
        visiting_order, paths = tsp_solver.solve(all_nodes)

        return visiting_order, paths
