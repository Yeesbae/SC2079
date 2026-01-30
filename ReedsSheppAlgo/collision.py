"""
collision.py

Collision checking module.
- Works for polygons, oriented rectangles, and robot footprints
- Uses geometry primitives
- Supports safety margins / inflated obstacles
"""

from geometry import OrientedRectangle, Polygon, RobotFootprint
from typing import List, Tuple
import math


# =========================
# Polygon collision helpers
# =========================

def aabb_overlap(aabb1: Tuple[float, float, float, float],
                 aabb2: Tuple[float, float, float, float]) -> bool:
    """
    Fast axis-aligned bounding box check.
    """
    min_x1, min_y1, max_x1, max_y1 = aabb1
    min_x2, min_y2, max_x2, max_y2 = aabb2

    overlap_x = (min_x1 <= max_x2) and (max_x1 >= min_x2)
    overlap_y = (min_y1 <= max_y2) and (max_y1 >= min_y2)

    return overlap_x and overlap_y


def sat_collision(poly1: Polygon, poly2: Polygon) -> bool:
    """
    Separating Axis Theorem (SAT) for convex polygons.
    Returns True if collision exists.
    """

    def get_axes(vertices):
        """
        Returns the axes (normals) to project onto
        Each edge normal is a potential separating axis
        """
        axes = []
        n = len(vertices)
        for i in range(n):
            p1 = vertices[i]
            p2 = vertices[(i + 1) % n]
            edge = (p2[0] - p1[0], p2[1] - p1[1])
            normal = (-edge[1], edge[0])  # perpendicular
            # normalize
            length = math.hypot(normal[0], normal[1])
            axes.append((normal[0] / length, normal[1] / length))
        return axes

    def project(vertices, axis):
        min_proj = float('inf')
        max_proj = float('-inf')
        for x, y in vertices:
            proj = x * axis[0] + y * axis[1]
            min_proj = min(min_proj, proj)
            max_proj = max(max_proj, proj)
        return min_proj, max_proj

    vertices1 = poly1.get_vertices()
    vertices2 = poly2.get_vertices()

    axes = get_axes(vertices1) + get_axes(vertices2)

    for axis in axes:
        min1, max1 = project(vertices1, axis)
        min2, max2 = project(vertices2, axis)

        if max1 < min2 or max2 < min1:
            return False  # Separating axis found

    return True  # Collision exists


# =========================
# Main collision checking
# =========================

def check_collision_robot_obstacles(
    robot_footprint: RobotFootprint,
    obstacles: List[OrientedRectangle]
) -> bool:
    """
    Checks if the robot footprint collides with any obstacles.
    """
    # First AABB quick check
    robot_aabb = robot_footprint.get_aabb()
    for obs in obstacles:
        obs_aabb = obs.get_aabb()
        if not aabb_overlap(robot_aabb, obs_aabb):
            continue  # definitely no collision

        # Use SAT for precise check
        robot_poly = Polygon(list(robot_footprint.get_vertices()))
        obs_poly = Polygon(list(obs.get_vertices()))
        if sat_collision(robot_poly, obs_poly):
            return True  # collision detected

    return False  # no collisions


def check_collision_swept_volume(
    swept_volume: List[RobotFootprint],
    obstacles: List[OrientedRectangle]
) -> bool:
    """
    Checks if any footprint in a swept volume collides with obstacles.
    Useful for RS path checking.
    """
    for fp in swept_volume:
        if check_collision_robot_obstacles(fp, obstacles):
            return True
    return False


# =========================
# Obstacle inflation helpers
# =========================

def inflate_obstacles(
    obstacles: List[OrientedRectangle],
    margin: float
) -> List[OrientedRectangle]:
    """
    Returns a new list of inflated obstacles for collision safety.
    """
    inflated = []
    for obs in obstacles:
        inflated.append(obs.inflate(margin))
    return inflated
