"""
planning/graph_builder.py

Builds a weighted graph of candidate viewpoints for RS path planning.
Edges represent feasible RS paths between viewpoints, filtered by collisions.
"""

from typing import Dict, List, Tuple
from geometry import RobotFootprint, OrientedRectangle
from reeds_shepp_wrapper import RSWrapper
import collision


class GraphBuilder:
    """
    Builds a graph from viewpoints with collision-safe RS paths
    """

    def __init__(
        self,
        viewpoints: Dict[OrientedRectangle, List[Tuple[float, float, float]]],
        obstacles: List[OrientedRectangle],
        rs_wrapper: RSWrapper,
        step_size: float = 1.0
    ):
        """
        viewpoints: dict of obstacle -> list of poses (x,y,theta)
        obstacles: list of inflated obstacles
        rs_wrapper: instance of RSWrapper
        step_size: distance between sampled poses for collision checking
        """
        self.viewpoints = viewpoints
        self.obstacles = obstacles
        self.rs_wrapper = rs_wrapper
        self.step_size = step_size
        self.graph = {}  # (start_pose, goal_pose) -> {"length": float, "footprints": list}

    def build_graph(self) -> Dict[Tuple, Dict]:
        """
        Build a graph connecting all viewpoints
        """
        all_poses = []
        for pose_list in self.viewpoints.values():
            all_poses.extend(pose_list)

        # Generate edges between every pair of poses
        for i, start_pose in enumerate(all_poses):
            for j, goal_pose in enumerate(all_poses):
                if i == j:
                    continue  # no self-loops

                edge_data = self._compute_edge(start_pose, goal_pose)
                if edge_data is not None:
                    self.graph[(start_pose, goal_pose)] = edge_data

        return self.graph

    def _compute_edge(self, start_pose: Tuple[float, float, float],
                      goal_pose: Tuple[float, float, float]) -> Dict:
        """
        Compute RS path between two poses and check collisions.
        Returns dict with path info or None if path is invalid
        """
        # 1. Generate RS path
        path = self.rs_wrapper.generate_path(start_pose, goal_pose, step_size=self.step_size)

        # 2. Convert to RobotFootprints
        footprints = self.rs_wrapper.discretize_to_footprints(path)

        # 3. Check collision along the path
        if collision.check_collision_swept_volume(footprints, self.obstacles):
            return None  # path is invalid

        # 4. Compute path length
        length = self.rs_wrapper.path_length(path)

        return {"length": length, "footprints": footprints}
