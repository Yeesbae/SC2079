"""
geometry.py

Geometric primitives and helpers.
This file defines shapes (rectangles, polygons) and how they exist in space.

"""

from typing import List, Tuple
import math
from Utils.math_utils import (
    rectangle_corners,
    axis_aligned_bounding_box,
)


# =========================
# Base geometry class
# =========================

class Geometry:
    """
    Abstract geometric object.
    """

    def get_vertices(self) -> Tuple[Tuple[float, float], ...]:
        raise NotImplementedError

    def get_aabb(self) -> Tuple[float, float, float, float]:
        """
        Axis-aligned bounding box
        """
        return axis_aligned_bounding_box(self.get_vertices())


# =========================
# Polygon
# =========================

class Polygon(Geometry):
    """
    Generic polygon defined by world-space vertices
    """

    def __init__(self, vertices: List[Tuple[float, float]]):
        self.vertices = tuple(vertices)

    def get_vertices(self) -> Tuple[Tuple[float, float], ...]:
        return self.vertices


# =========================
# Oriented Rectangle
# =========================

class OrientedRectangle(Geometry):
    """
    Rectangle defined by:
    - bottom-left corner
    - width
    - height
    - orientation (theta)
    """

    def __init__(
        self,
        bottom_left: Tuple[float, float],
        width: float,
        height: float,
        theta: float = 0.0,
    ):
        self.bottom_left = bottom_left
        self.width = width
        self.height = height
        self.theta = theta

    def get_vertices(self) -> Tuple[Tuple[float, float], ...]:
        return rectangle_corners(
            self.bottom_left,
            self.width,
            self.height,
            self.theta,
        )

    def inflate(self, margin: float) -> "OrientedRectangle":
        """
        Inflate rectangle by margin in all directions.
        Used for safety clearance.
        """
        new_bl = (
            self.bottom_left[0] - margin,
            self.bottom_left[1] - margin,
        )
        return OrientedRectangle(
            bottom_left=new_bl,
            width=self.width + 2 * margin,
            height=self.height + 2 * margin,
            theta=self.theta,
        )


# =========================
# Robot footprint
# =========================

class RobotFootprint(OrientedRectangle):
    """
    Robot footprint at a specific pose.
    Pose refers to robot reference point (usually center or rear axle).

    This class converts pose -> bottom-left internally.
    """

    def __init__(
        self,
        pose: Tuple[float, float, float],
        length: float,
        width: float,
        reference_offset: float,
    ):
        """
        pose = (x, y, theta)
        reference_offset = distance from reference point to rectangle center
        """
        x, y, theta = pose

        # Compute center of robot rectangle
        cx = x + reference_offset * math.cos(theta)
        cy = y + reference_offset * math.sin(theta)

        # Convert center to bottom-left
        bl_x = cx - (length / 2) * math.cos(theta) + (width / 2) * math.sin(theta)
        bl_y = cy - (length / 2) * math.sin(theta) - (width / 2) * math.cos(theta)

        super().__init__(
            bottom_left=(bl_x, bl_y),
            width=length,
            height=width,
            theta=theta,
        )


# =========================
# Path geometry
# =========================

class SweptVolume(Geometry):
    """
    Represents the swept area of a robot along a path.
    This is a conservative approximation using union of footprints.
    """

    def __init__(self, footprints: List[RobotFootprint]):
        self.footprints = footprints

    def get_vertices(self) -> Tuple[Tuple[float, float], ...]:
        """
        Union of all footprint vertices
        """
        vertices = []
        for fp in self.footprints:
            vertices.extend(fp.get_vertices())
        return tuple(vertices)
