from Entities.robot import Robot
from Entities.obstacle import Obstacle
from geometry import OrientedRectangle
from reeds_shepp_wrapper import RSWrapper
from Planning.maze_solver import MazeSolver
from Utils.visualizer import Visualizer
import constants


def main():
    # -------------------------------
    # 1. Initialize Robot
    # -------------------------------
    robot = Robot(x=50, y=50, theta=0)

    # -------------------------------
    # 2. Initialize Obstacles
    # -------------------------------
    obstacle_data = [
        #(150, 150, 0),
        (60, 140, 0),
        (100, 120, 0)
    ]

    obstacles = []
    for x, y, theta in obstacle_data:
        rect = OrientedRectangle(
            bottom_left=(x, y),
            width=constants.DEFAULT_OBSTACLE_WIDTH,
            height=constants.DEFAULT_OBSTACLE_HEIGHT,
            theta=theta
        )
        obstacles.append(rect)

    # -------------------------------
    # 3. Initialize RSWrapper
    # -------------------------------
    rs_wrapper = RSWrapper(turning_radius=constants.MIN_TURNING_RADIUS)

    # -------------------------------
    # 4. Solve maze / generate final path
    # -------------------------------
    solver = MazeSolver(robot, obstacles, rs_wrapper, step_size=1.0)

    print("Before MazeSolver.solve()")
    visiting_order, paths = solver.solve()
    print("After MazeSolver.solve()")

    # -------------------------------
    # 5. Output / debug
    # -------------------------------
    print("=== Visiting Order ===")
    for i, (x, y, theta) in enumerate(visiting_order):
        print(f"{i+1}: ({x:.2f}, {y:.2f}, {theta:.2f} rad)")

    # -------------------------------
    # 6. Visualize
    # -------------------------------
    viz = Visualizer(
        arena_width=constants.ARENA_WIDTH,
        arena_height=constants.ARENA_HEIGHT
    )

    full_path = []
    for segment in paths:
        full_path.extend(segment)

    print(f"\nVisualizing {len(full_path)} poses...")
    viz.animate_path(full_path, obstacles)


if __name__ == "__main__":
    main()
