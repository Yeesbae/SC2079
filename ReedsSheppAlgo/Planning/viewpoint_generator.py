"""
planning/viewpoint_generator.py

Generate candidate viewpoints (robot poses) in front of obstacle images.
Each viewpoint satisfies:
1. Robot front faces the image
2. Camera/front is CAMERA_DISTANCE away from the image
3. Outside inflated obstacles for safety
"""

from typing import List, Tuple, Dict
import math
from geometry import OrientedRectangle
import constants


class ViewpointGenerator:
    """
    Generates viewpoints for obstacles
    """

    def __init__(self, obstacles: List[OrientedRectangle], camera_distance: float = constants.CAMERA_CAPTURE_DISTANCE):
        """
        obstacles: list of OrientedRectangle objects (already inflated if needed)
        camera_distance: distance robot front/camera should maintain from obstacle image
        """
        self.obstacles = obstacles
        self.camera_distance = camera_distance

    @staticmethod
    def _compute_face_center_and_normal(obstacle: OrientedRectangle, face_idx: int) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Compute the center and outward normal of one face of the rectangle
        face_idx: 0=bottom, 1=right, 2=top, 3=left (counter-clockwise)
        Returns:
            center: (x, y)
            normal: (nx, ny) unit vector pointing away from face
        """
        vertices = obstacle.get_vertices()
        # vertex order: bottom-left, bottom-right, top-right, top-left
        if face_idx == 0:  # bottom
            p1, p2 = vertices[0], vertices[1]
            normal = (0, -1)
        elif face_idx == 1:  # right
            p1, p2 = vertices[1], vertices[2]
            normal = (1, 0)
        elif face_idx == 2:  # top
            p1, p2 = vertices[2], vertices[3]
            normal = (0, 1)
        elif face_idx == 3:  # left
            p1, p2 = vertices[3], vertices[0]
            normal = (-1, 0)
        else:
            raise ValueError("face_idx must be 0,1,2,3")

        # Center of face
        center = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)

        return center, normal

    def generate_viewpoints_for_obstacle(self, obstacle: OrientedRectangle) -> List[Tuple[float, float, float]]:
        """
        Generate candidate robot poses in front of each of the obstacle's 4 faces
        Returns list of poses: (x, y, theta)
        """
        viewpoints = []

        for face_idx in range(4):
            face_center, normal = self._compute_face_center_and_normal(obstacle, face_idx)

            # Position the robot at CAMERA_DISTANCE along the normal
            rx = face_center[0] + normal[0] * self.camera_distance
            ry = face_center[1] + normal[1] * self.camera_distance

            # Theta is robot orientation facing the obstacle (opposite normal)
            theta = math.atan2(-normal[1], -normal[0])

            viewpoints.append((rx, ry, theta))

        return viewpoints

    def generate_all_viewpoints(self) -> Dict[OrientedRectangle, List[Tuple[float, float, float]]]:
        """
        Generate all candidate viewpoints for all obstacles
        Returns:
            Dict mapping obstacle -> list of candidate poses
        """
        all_viewpoints = {}
        for obs in self.obstacles:
            all_viewpoints[obs] = self.generate_viewpoints_for_obstacle(obs)
        return all_viewpoints
