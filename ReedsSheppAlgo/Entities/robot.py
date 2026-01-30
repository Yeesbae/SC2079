import math
from typing import Tuple
from .entity import Entity
import constants


class Robot(Entity):
    """
    Robot model.

    Pose convention:
    - (x, y) is the bottom-left corner of the robot bounding box
    - theta is the robot forward direction (camera faces forward)
    """

    def __init__(self, x: float, y: float, theta: float):
        super().__init__(x, y, theta)

    # -----------------------
    # Geometry helpers
    # -----------------------

    def center_position(self) -> Tuple[float, float]:
        """
        Returns the center of the robot body.
        """
        cx = self.x + constants.ROBOT_CENTER_OFFSET_X
        cy = self.y + constants.ROBOT_CENTER_OFFSET_Y
        return cx, cy

    def front_center_position(self) -> Tuple[float, float]:
        """
        Returns the center point of the robot's front face.
        """
        cx, cy = self.center_position()
        fx = cx + (constants.ROBOT_LENGTH / 2.0) * math.cos(self.theta)
        fy = cy + (constants.ROBOT_LENGTH / 2.0) * math.sin(self.theta)
        return fx, fy

    def camera_position(self) -> Tuple[float, float]:
        """
        Returns the camera position in world coordinates.
        """
        fx, fy = self.front_center_position()
        offset = constants.CAMERA_OFFSET_FROM_FRONT
        cam_x = fx + offset * math.cos(self.theta)
        cam_y = fy + offset * math.sin(self.theta)
        return cam_x, cam_y

    # -----------------------
    # Pose construction
    # -----------------------

    @staticmethod
    def pose_from_camera(
        camera_x: float,
        camera_y: float,
        theta: float
    ) -> Tuple[float, float, float]:
        """
        Given a desired camera pose, compute the corresponding robot pose
        (bottom-left corner).

        This is used when generating capture viewpoints.
        """
        # Step back from camera to robot front
        fx = camera_x - constants.CAMERA_OFFSET_FROM_FRONT * math.cos(theta)
        fy = camera_y - constants.CAMERA_OFFSET_FROM_FRONT * math.sin(theta)

        # Step back from front face to robot center
        cx = fx - (constants.ROBOT_LENGTH / 2.0) * math.cos(theta)
        cy = fy - (constants.ROBOT_LENGTH / 2.0) * math.sin(theta)

        # Convert center to bottom-left
        x = cx - constants.ROBOT_CENTER_OFFSET_X
        y = cy - constants.ROBOT_CENTER_OFFSET_Y

        return x, y, theta

    # -----------------------
    # Collision abstraction
    # -----------------------

    def footprint_radius(self) -> float:
        """
        Returns approximate footprint radius for collision inflation.
        """
        return constants.ROBOT_FOOTPRINT_RADIUS
