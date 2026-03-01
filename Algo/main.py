import pygame
import time
from pathAlgo import MazeSolver
from constants import Direction, ARENA_WIDTH, ARENA_HEIGHT
from visualizer import MazeVisualizer
from Util.helper import path_to_stm_commands

def task_1():
    # Start robot at (3, 3) facing NORTH
    solver = MazeSolver(size_x=ARENA_WIDTH, size_y=ARENA_HEIGHT, robot_x=3, robot_y=3, robot_direction=Direction.NORTH)
    
    # """5 Obstacles: Test Case 1"""
    # solver.add_obstacle(x=6,  y=6,  direction=Direction.NORTH, obstacle_id=1)
    # solver.add_obstacle(x=30, y=6,  direction=Direction.WEST,  obstacle_id=2)
    # solver.add_obstacle(x=6,  y=30, direction=Direction.EAST,  obstacle_id=3)
    # solver.add_obstacle(x=30, y=30, direction=Direction.SOUTH, obstacle_id=4)
    # solver.add_obstacle(x=18, y=18, direction=Direction.WEST,  obstacle_id=5)

    # """8 Obstacles: Test Case 1"""
    # solver.add_obstacle(x=2,  y=15,  direction=Direction.SOUTH, obstacle_id=1)
    # solver.add_obstacle(x=16, y=4,  direction=Direction.EAST,  obstacle_id=2)
    # solver.add_obstacle(x=34, y=4,  direction=Direction.NORTH, obstacle_id=3)
    # solver.add_obstacle(x=29, y=16, direction=Direction.NORTH,  obstacle_id=4)
    # solver.add_obstacle(x=13, y=24, direction=Direction.EAST, obstacle_id=5)
    # solver.add_obstacle(x=4, y=35, direction=Direction.SOUTH,  obstacle_id=6)
    # solver.add_obstacle(x=18, y=35, direction=Direction.EAST, obstacle_id=7)
    # solver.add_obstacle(x=34, y=35, direction=Direction.WEST,  obstacle_id=8)

    """8 Obstacles: Test Case 2"""
    solver.add_obstacle(x=3,  y=15,  direction=Direction.SOUTH, obstacle_id=1)
    solver.add_obstacle(x=35, y=3,  direction=Direction.NORTH,  obstacle_id=2)
    solver.add_obstacle(x=19, y=18,  direction=Direction.EAST, obstacle_id=3)
    solver.add_obstacle(x=19, y=23, direction=Direction.EAST,  obstacle_id=4)
    solver.add_obstacle(x=8, y=30, direction=Direction.EAST, obstacle_id=5)
    solver.add_obstacle(x=3, y=35, direction=Direction.SOUTH,  obstacle_id=6)
    solver.add_obstacle(x=31, y=31, direction=Direction.SOUTH, obstacle_id=7)
    solver.add_obstacle(x=36, y=36, direction=Direction.SOUTH,  obstacle_id=8)

    # 5 Obs around 10.51 ~ 11.63 seconds
    # 8 Obs around 40.41 ~ 51.46 seconds

    print("Calculating optimal Hamiltonian path...")

    # Start the timer
    start_time = time.perf_counter()
    # Execute the line
    optimal_path, total_distance = solver.get_optimal_order_dp(retrying=False)
    print(optimal_path)
    print()
    commands = path_to_stm_commands(optimal_path)
    print(commands)
    # End the timer
    end_time = time.perf_counter()
    # Calculate duration
    duration = end_time - start_time
    print(f"The DP solver took {duration:.6f} seconds.")
    
    print("Total Distance: ", total_distance)

    if not optimal_path:
        print("No valid path found!")
        return

    viz = MazeVisualizer(grid_size=(ARENA_WIDTH, ARENA_HEIGHT), cell_pixel_size=17)
    clock = pygame.time.Clock()
    
    path_index = 0
    running = True

    animating = False
    anim_start = None
    anim_end = None

    auto_play = False
    paused = False
    anim_frames = 20  # default speed: frames per move

    while running:
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:

                # Reset
                if event.key == pygame.K_r:
                    path_index = 0
                    animating = False
                    auto_play = False
                    paused = False
                    print(f"[RESET] Index {path_index}: {optimal_path[path_index]}")

                # Manual Forward
                elif event.key == pygame.K_RIGHT:
                    if not animating and path_index < len(optimal_path) - 1:
                        anim_start = optimal_path[path_index]
                        anim_end = optimal_path[path_index + 1]
                        animating = True
                        auto_play = False
                        paused = False
                        print(f"[MOVE] Index {path_index} -> {path_index + 1}: {anim_end}")

                # Manual Backward
                elif event.key == pygame.K_LEFT:
                    if not animating and path_index > 0:
                        anim_start = optimal_path[path_index]
                        anim_end = optimal_path[path_index - 1]
                        animating = True
                        auto_play = False
                        paused = False
                        print(f"[MOVE] Index {path_index} -> {path_index - 1}: {anim_end}")

                # Autoplay
                elif event.key == pygame.K_g:
                    auto_play = True
                    paused = False
                    if path_index < len(optimal_path) - 1 and not animating:
                        anim_start = optimal_path[path_index]
                        anim_end = optimal_path[path_index + 1]
                        animating = True
                        print(f"[AUTOPLAY START] Index {path_index} -> {path_index + 1}: {anim_end}")

                # Pause autoplay
                elif event.key == pygame.K_SPACE:
                    paused = True
                    auto_play = False
                    print("[PAUSE]")

                # Speed control
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_KP_PLUS:  # '+' key
                    anim_frames = max(2, anim_frames - 5)  # faster (fewer frames)
                    print(f"[SPEED UP] frames per move: {anim_frames}")

                elif event.key == pygame.K_MINUS or event.key == pygame.K_KP_MINUS:  # '-' key
                    anim_frames += 5  # slower (more frames)
                    print(f"[SLOW DOWN] frames per move: {anim_frames}")

        # -----------------------
        # Animate current move
        # -----------------------
        if animating:
            viz.animate_transition(
                anim_start,
                anim_end,
                solver.grid.obstacles,
                optimal_path,
                path_index,
                anim_frames
            )

            # Finish move
            if anim_end == optimal_path[min(path_index + 1, len(optimal_path)-1)]:
                path_index += 1
            else:
                path_index -= 1

            animating = False

        # -----------------------
        # Autoplay logic
        # -----------------------
        elif auto_play and not paused:
            if path_index < len(optimal_path) - 1:
                anim_start = optimal_path[path_index]
                anim_end = optimal_path[path_index + 1]
                animating = True
                print(f"[AUTOPLAY MOVE] Index {path_index} -> {path_index + 1}: {anim_end}")
            else:
                auto_play = False

        # -----------------------
        # Draw current state
        # -----------------------
        else:
            viz.draw_frame(
                optimal_path[path_index],
                solver.grid.obstacles,
                optimal_path,
                path_index
            )

        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    print("Starting Task 1: Visit all Obstacles & Capture all images")
    task_1()
