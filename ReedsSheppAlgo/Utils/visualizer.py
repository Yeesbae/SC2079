"""
visualizer.py

Matplotlib-based visualizer for:
- Robot motion along Reeds–Shepp paths
- Robot heading direction
- Oriented obstacles with facing direction
"""

import math
import numpy as np
from matplotlib.patches import Polygon
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
from matplotlib import transforms

import constants


class Visualizer:
    def __init__(self, arena_width=constants.ARENA_WIDTH, arena_height=constants.ARENA_HEIGHT):
        self.arena_width = arena_width
        self.arena_height = arena_height

        self.fig, self.ax = plt.subplots()
        self.ax.set_aspect("equal")
        self.ax.set_xlim(0, arena_width)
        self.ax.set_ylim(0, arena_height)
        self.ax.set_xlabel("X (cm)")
        self.ax.set_ylabel("Y (cm)")
        self.ax.set_title("Reeds–Shepp Robot Visualization")

    # -------------------------------------------------
    # Robot drawing
    # -------------------------------------------------
    # def draw_robot(self, pose, color="blue"):
    #     x, y, theta = pose

    #     length = constants.ROBOT_LENGTH
    #     width = constants.ROBOT_WIDTH

    #     # Rectangle at bottom-left
    #     rect = Rectangle(
    #         (x, y),
    #         length,
    #         width,
    #         linewidth=2,
    #         edgecolor=color,
    #         facecolor="none",
    #         zorder=3
    #     )

    #     # Rotate about robot center
    #     cx = x + length / 2
    #     cy = y + width / 2

    #     transform = (
    #         transforms.Affine2D()
    #         .rotate_around(cx, cy, theta)
    #         + self.ax.transData
    #     )
    #     rect.set_transform(transform)
    #     self.ax.add_patch(rect)

    #     # Heading arrow
    #     arrow_len = length * 0.6
    #     dx = math.cos(theta) * arrow_len
    #     dy = math.sin(theta) * arrow_len

    #     self.ax.arrow(
    #         cx,
    #         cy,
    #         dx,
    #         dy,
    #         head_width=2.5,
    #         head_length=3.5,
    #         fc=color,
    #         ec=color,
    #         zorder=4
    #     )

    def draw_robot(self, pose):
        """
        Draw robot at a given pose.
        Pose can be:
        - (x, y, theta)
        - RobotFootprint
        """

        # --- Extract pose correctly ---
        if hasattr(pose, "x") and hasattr(pose, "theta"):
            # RobotFootprint
            x = pose.x
            y = pose.y
            theta = pose.theta
            length = pose.length
            width = pose.width
        else:
            # Tuple pose
            x, y, theta = pose
            length = constants.ROBOT_LENGTH
            width = constants.ROBOT_WIDTH

        # --- Robot rectangle (center-based) ---
        corners = [
            (-length / 2, -width / 2),
            ( length / 2, -width / 2),
            ( length / 2,  width / 2),
            (-length / 2,  width / 2)
        ]

        rotated = []
        for cx, cy in corners:
            rx = cx * np.cos(theta) - cy * np.sin(theta)
            ry = cx * np.sin(theta) + cy * np.cos(theta)
            rotated.append((x + rx, y + ry))

        self.ax.add_patch(
            Polygon(
                rotated,
                closed=True,
                fill=False,
                edgecolor="blue",
                linewidth=2,
                zorder=3
            )
        )

        # --- Heading arrow ---
        arrow_len = length * 0.6
        self.ax.arrow(
            x,
            y,
            arrow_len * np.cos(theta),
            arrow_len * np.sin(theta),
            head_width=4,
            head_length=6,
            fc="red",
            ec="red",
            zorder=4
        )



    # -------------------------------------------------
    # Obstacle drawing
    # -------------------------------------------------
    def draw_obstacle(self, obstacle, color="red"):
        x, y = obstacle.bottom_left
        w = obstacle.width
        h = obstacle.height
        theta = obstacle.theta

        rect = Rectangle(
            (x, y),
            w,
            h,
            linewidth=2,
            edgecolor=color,
            facecolor="none",
            zorder=2
        )

        cx = x + w / 2
        cy = y + h / 2

        transform = (
            transforms.Affine2D()
            .rotate_around(cx, cy, theta)
            + self.ax.transData
        )
        rect.set_transform(transform)
        self.ax.add_patch(rect)

        # Facing direction arrow (image side)
        face_len = max(w, h) * 0.5
        fx = math.cos(theta) * face_len
        fy = math.sin(theta) * face_len

        self.ax.arrow(
            cx,
            cy,
            fx,
            fy,
            head_width=2.0,
            head_length=3.0,
            fc=color,
            ec=color,
            zorder=3
        )

    # -------------------------------------------------
    # Full scene rendering
    # -------------------------------------------------
    def animate_path(self, path, obstacles, pause=0.05):
        """
        path: List[(x,y,theta)]
        obstacles: List[OrientedRectangle]
        """

        for pose in path:
            self.ax.clear()
            self.ax.set_xlim(0, self.arena_width)
            self.ax.set_ylim(0, self.arena_height)
            self.ax.set_aspect("equal")
            self.ax.set_title("Reeds–Shepp Robot Visualization")

            # Draw obstacles
            for obs in obstacles:
                self.draw_obstacle(obs)

            # Draw robot
            self.draw_robot(pose)

            plt.pause(pause)

        plt.show()
