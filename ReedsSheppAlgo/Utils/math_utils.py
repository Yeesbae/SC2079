"""
math_utils.py

Pure mathematical helper functions used throughout the project.
This file must NOT depend on any project-specific classes (Robot, Obstacle, etc).

All functions here should be:
- Deterministic
- Stateless
- Reusable
"""

import math
from typing import Tuple

# =========================
# Angle utilities
# =========================

def normalize_angle(theta: float) -> float:
    """
    Normalize angle to range [-pi, pi)
    """
    while theta >= math.pi:
        theta -= 2 * math.pi
    while theta < -math.pi:
        theta += 2 * math.pi
    return theta


def angle_difference(a: float, b: float) -> float:
    """
    Smallest signed angle difference a - b
    Result in range [-pi, pi)
    """
    return normalize_angle(a - b)


def deg2rad(deg: float) -> float:
    return deg * math.pi / 180.0


def rad2deg(rad: float) -> float:
    return rad * 180.0 / math.pi


# =========================
# Distance & geometry
# =========================

def euclidean_distance(p1: Tuple[float, float],
                       p2: Tuple[float, float]) -> float:
    """
    Euclidean distance between two 2D points
    """
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    return math.hypot(dx, dy)


def squared_distance(p1: Tuple[float, float],
                     p2: Tuple[float, float]) -> float:
    """
    Squared distance (avoids sqrt for performance)
    """
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    return dx * dx + dy * dy


# =========================
# Pose utilities
# =========================

def pose_distance(pose1: Tuple[float, float, float],
                  pose2: Tuple[float, float, float],
                  angle_weight: float = 1.0) -> float:
    """
    Distance metric between two poses.
    Used for graph weights and heuristics.

    pose = (x, y, theta)
    """
    pos_dist = euclidean_distance(pose1[:2], pose2[:2])
    ang_dist = abs(angle_difference(pose1[2], pose2[2]))
    return pos_dist + angle_weight * ang_dist


def move_point(x: float, y: float,
               theta: float,
               distance: float) -> Tuple[float, float]:
    """
    Move a point forward by 'distance' along heading theta
    """
    nx = x + distance * math.cos(theta)
    ny = y + distance * math.sin(theta)
    return nx, ny


def transform_local_to_world(local_point: Tuple[float, float],
                             origin_pose: Tuple[float, float, float]) -> Tuple[float, float]:
    """
    Transform a point from local frame to world frame

    local_point = (lx, ly)
    origin_pose = (x, y, theta)
    """
    lx, ly = local_point
    ox, oy, theta = origin_pose

    wx = ox + lx * math.cos(theta) - ly * math.sin(theta)
    wy = oy + lx * math.sin(theta) + ly * math.cos(theta)
    return wx, wy


def transform_world_to_local(world_point: Tuple[float, float],
                             origin_pose: Tuple[float, float, float]) -> Tuple[float, float]:
    """
    Transform a point from world frame to local frame
    """
    wx, wy = world_point
    ox, oy, theta = origin_pose

    dx = wx - ox
    dy = wy - oy

    lx = dx * math.cos(theta) + dy * math.sin(theta)
    ly = -dx * math.sin(theta) + dy * math.cos(theta)
    return lx, ly


# =========================
# Rectangle & bounding box helpers
# =========================

def rectangle_corners(bottom_left: Tuple[float, float],
                      width: float,
                      height: float,
                      theta: float = 0.0) -> Tuple[Tuple[float, float], ...]:
    """
    Compute the 4 corners of a rectangle given:
    - bottom-left corner
    - width
    - height
    - orientation (theta)

    Returned in world coordinates, counter-clockwise.
    """
    x, y = bottom_left

    local_corners = [
        (0.0, 0.0),
        (width, 0.0),
        (width, height),
        (0.0, height),
    ]

    world_corners = []
    for lx, ly in local_corners:
        wx = x + lx * math.cos(theta) - ly * math.sin(theta)
        wy = y + lx * math.sin(theta) + ly * math.cos(theta)
        world_corners.append((wx, wy))

    return tuple(world_corners)


def axis_aligned_bounding_box(points: Tuple[Tuple[float, float], ...]) -> Tuple[float, float, float, float]:
    """
    Compute AABB for a set of points
    Returns (min_x, min_y, max_x, max_y)
    """
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


# =========================
# Camera / facing logic
# =========================

def is_facing_target(robot_pose: Tuple[float, float, float],
                     target_point: Tuple[float, float],
                     angle_tolerance: float) -> bool:
    """
    Check if robot is facing a target point within angular tolerance
    """
    rx, ry, rtheta = robot_pose
    dx = target_point[0] - rx
    dy = target_point[1] - ry

    target_angle = math.atan2(dy, dx)
    diff = abs(angle_difference(target_angle, rtheta))
    return diff <= angle_tolerance


def front_point(robot_pose: Tuple[float, float, float],
                front_offset: float) -> Tuple[float, float]:
    """
    Compute the point at the front of the robot (camera position)
    """
    x, y, theta = robot_pose
    return move_point(x, y, theta, front_offset)
