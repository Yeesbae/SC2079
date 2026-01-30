import math
from typing import List, Tuple
from .entity import Entity
import constants


class Obstacle(Entity):
    """
    Obstacle model.

    Coordinate convention:
    - (x, y) is the bottom-left corner
    - theta is obstacle orientation (radians)

    Obstacles may be square or rectangular.
    """

    def __init__(
        self,
        x: float,
        y: float,
        theta: float,
        width: float = constants.DEFAULT_OBSTACLE_WIDTH,
        height: float = constants.DEFAULT_OBSTACLE_HEIGHT,
        has_image: bool = True
    ):
        super().__init__(x, y, theta)
        self.width = width
        self.height = height
        self.has_image = has_image

    # -----------------------
    # Geometry helpers
    # -----------------------

    def center_position(self) -> Tuple[float, float]:
        cx = self.x + self.width / 2.0
        cy = self.y + self.height / 2.0
        return cx, cy

    def inflated_dimensions(self) -> Tuple[float, float]:
        """
        Dimensions after inflation for collision checking.
        """
        inflation = constants.TOTAL_OBSTACLE_INFLATION
        return (
            self.width + 2 * inflation,
            self.height + 2 * inflation
        )

    # -----------------------
    # Image face handling
    # -----------------------

    def image_faces(self) -> List[Tuple[Tuple[float, float], float]]:
        """
        Returns a list of image faces.

        Each face is represented as:
        - (face_center_x, face_center_y)
        - face_normal_theta (direction camera must face)

        Faces are returned in world coordinates.
        """
        cx, cy = self.center_position()
        faces = []

        # Local face normals (before rotation)
        local_faces = [
            ((0, self.height / 2.0), math.pi),              # left
            ((self.width, self.height / 2.0), 0.0),        # right
            ((self.width / 2.0, self.height), math.pi/2),  # top
            ((self.width / 2.0, 0), -math.pi/2),            # bottom
        ]

        for (lx, ly), normal in local_faces:
            # Rotate local point
            rx = (
                lx * math.cos(self.theta)
                - ly * math.sin(self.theta)
            )
            ry = (
                lx * math.sin(self.theta)
                + ly * math.cos(self.theta)
            )

            face_x = self.x + rx
            face_y = self.y + ry
            face_theta = self.theta + normal

            faces.append(((face_x, face_y), face_theta))

        return faces
