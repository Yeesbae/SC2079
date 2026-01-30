"""
reeds_shepp_wrapper.py

Wrapper for Reeds-Shepp path planning using Nathan's reeds_shepp repo.
Generates feasible paths between two poses for a car-like robot
that can move forward and backward with a minimum turning radius.

Outputs a discretized list of robot poses (RobotFootprint ready)
for collision checking or graph building.
"""

from typing import List, Tuple
from ReedsShepp import reeds_shepp
from geometry import RobotFootprint
import constants
import math

class RSWrapper:
    """
    Reeds-Shepp path wrapper
    """

    def __init__(self, turning_radius: float):
        self.turning_radius = turning_radius

    # def generate_path(
    #     self,
    #     start_pose: Tuple[float, float, float],
    #     goal_pose: Tuple[float, float, float],
    #     step_size: float = 1.0
    # ) -> List[Tuple[float, float, float]]:
    #     """
    #     Generate a Reeds-Shepp path between start and goal.
    #     Returns a list of poses (x, y, theta) along the path.
    #     step_size: distance between sampled poses (cm)
    #     """
    #     x0, y0, theta0 = start_pose
    #     x1, y1, theta1 = goal_pose

    #     # Get shortest path as list of PathElement
    #     path_elements = reeds_shepp.get_optimal_path((x0, y0, theta0), (x1, y1, theta1))

    #     poses = [(x0, y0, theta0)]
    #     x, y, theta = x0, y0, theta0

    #     for elem in path_elements:
    #         length = elem.param * self.turning_radius  # scale by turning radius
    #         n_steps = max(int(abs(length) / step_size), 1)
    #         step = step_size if elem.gear.value > 0 else -step_size

    #         for i in range(n_steps):
    #             if elem.steering == reeds_shepp.Steering.STRAIGHT:
    #                 # Move straight
    #                 x += step * math.cos(theta)
    #                 y += step * math.sin(theta)
    #             else:
    #                 # Turning
    #                 radius = self.turning_radius
    #                 omega = step / radius
    #                 if elem.steering == reeds_shepp.Steering.LEFT:
    #                     theta += omega * (1 if elem.gear.value > 0 else -1)
    #                     x += radius * (math.sin(theta) - math.sin(theta - omega * (1 if elem.gear.value > 0 else -1)))
    #                     y -= radius * (math.cos(theta) - math.cos(theta - omega * (1 if elem.gear.value > 0 else -1)))
    #                 else:  # RIGHT
    #                     theta -= omega * (1 if elem.gear.value > 0 else -1)
    #                     x += radius * (math.sin(theta + omega * (1 if elem.gear.value > 0 else -1)) - math.sin(theta))
    #                     y += radius * (math.cos(theta + omega * (1 if elem.gear.value > 0 else -1)) - math.cos(theta))

    #             poses.append((x, y, theta))

    #     # Ensure last pose is exactly the goal
    #     poses.append((x1, y1, theta1))

    #     return poses

    def generate_path(
        self,
        start_pose: Tuple[float, float, float],
        goal_pose: Tuple[float, float, float],
        step_size: float = 5.0  # IMPORTANT: bigger default
    ) -> List[Tuple[float, float, float]]:

        x, y, theta = start_pose
        poses = [(x, y, theta)]

        path_elements = reeds_shepp.get_optimal_path(start_pose, goal_pose)

        MAX_STEPS_PER_ELEMENT = 1000  # safety fuse

        for elem in path_elements:
            # true arc length in world units
            segment_length = abs(elem.param) * self.turning_radius

            n_steps = min(
                max(int(segment_length / step_size), 1),
                MAX_STEPS_PER_ELEMENT
            )

            ds = segment_length / n_steps
            direction = 1 if elem.gear == reeds_shepp.Gear.FORWARD else -1

            for _ in range(n_steps):
                if elem.steering == reeds_shepp.Steering.STRAIGHT:
                    x += direction * ds * math.cos(theta)
                    y += direction * ds * math.sin(theta)

                else:
                    radius = self.turning_radius
                    dtheta = direction * ds / radius
                    if elem.steering == reeds_shepp.Steering.RIGHT:
                        dtheta *= -1

                    cx = x - radius * math.sin(theta)
                    cy = y + radius * math.cos(theta)

                    theta += dtheta
                    x = cx + radius * math.sin(theta)
                    y = cy - radius * math.cos(theta)

                poses.append((x, y, theta))

        poses.append(goal_pose)
        return poses

    def discretize_to_footprints(
        self,
        path: List[Tuple[float, float, float]],
        front_offset: float = constants.CAMERA_OFFSET_FROM_FRONT
    ) -> List[RobotFootprint]:
        """
        Convert a list of poses into RobotFootprints for collision checking.
        front_offset: distance from robot reference point to camera/front
        """

        footprints = []
        for pose in path:
            fp = RobotFootprint(
                pose=pose,
                length=constants.ROBOT_LENGTH,
                width=constants.ROBOT_WIDTH,
                reference_offset=front_offset
            )
            footprints.append(fp)

        return footprints

    def path_length(self, path: List[Tuple[float, float, float]]) -> float:
        """
        Compute total Euclidean path length along a discretized path
        """
        total_length = 0.0
        for i in range(1, len(path)):
            x1, y1, _ = path[i - 1]
            x2, y2, _ = path[i]
            total_length += ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        return total_length
