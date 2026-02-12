import pygame
from pathAlgo import MazeSolver
from constants import Direction
from visualizer import MazeVisualizer
from Util.helper import capture_image

def task_1():
    # Start robot at (2, 2) facing NORTH
    solver = MazeSolver(size_x=40, size_y=40, robot_x=2, robot_y=2, robot_direction=Direction.NORTH)
    
    solver.add_obstacle(x=6,  y=6,  direction=Direction.NORTH, obstacle_id=1)
    solver.add_obstacle(x=30, y=6,  direction=Direction.WEST,  obstacle_id=2)
    solver.add_obstacle(x=6,  y=30, direction=Direction.EAST,  obstacle_id=3)
    solver.add_obstacle(x=30, y=30, direction=Direction.SOUTH, obstacle_id=4)
    solver.add_obstacle(x=18, y=18, direction=Direction.WEST,  obstacle_id=5)

    # 3. Solve for optimal order and paths
    print("Calculating optimal Hamiltonian path...")
    optimal_path, total_distance = solver.get_optimal_order_dp(retrying=False)
    
    if not optimal_path:
        print("No valid path found!")
        return

    viz = MazeVisualizer(grid_size=(40, 40), cell_pixel_size=17)
    clock = pygame.time.Clock()
    
    path_index = 0
    running = True
    paused = False
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    path_index = 0
                if event.key == pygame.K_SPACE:
                    paused = not paused

        if not paused and path_index < len(optimal_path) - 1:
            print(optimal_path[path_index])
            path_index += 1

        viz.draw_frame(
            optimal_path[path_index],
            solver.grid.obstacles,
            optimal_path,
            path_index
        )

        clock.tick(10)

    pygame.quit()


def task_2():
    TASK_2_ARENA_WIDTH = 50
    TASK_2_ARENA_HEIGHT = 40

    FINAL_PATH = []

    # Visit first obstacle
    solver = MazeSolver(size_x=TASK_2_ARENA_WIDTH, size_y=TASK_2_ARENA_HEIGHT, robot_x=7, robot_y=20, robot_direction=Direction.EAST)
    
    solver.add_composite_obstacle(x=0, y=12, length=12, width=2, direction=Direction.SKIP, obstacle_id=1)
    solver.add_composite_obstacle(x=0, y=14, length=2, width=12, direction=Direction.SKIP, obstacle_id=2)
    solver.add_composite_obstacle(x=0, y=26, length=12, width=2, direction=Direction.SKIP, obstacle_id=3)

    solver.add_composite_obstacle(x=38, y=15, length=2, width=10, direction=Direction.SKIP, obstacle_id=4)
    solver.add_composite_obstacle(x=24, y=17, length=2, width=6, direction=Direction.WEST, obstacle_id=5)

    # 3. Solve for optimal order and paths
    print("Calculating optimal path to visit 1st obstacle...")
    optimal_path, total_distance = solver.get_optimal_order_dp(retrying=False)
    print(optimal_path)
    
    if not optimal_path:
        print("No valid path found!")
        return
    
    FINAL_PATH.extend(optimal_path.copy())

    ## Follow first image's instruction 
    finalState = optimal_path[-1]
    solver = MazeSolver(size_x=TASK_2_ARENA_WIDTH, size_y=TASK_2_ARENA_HEIGHT, robot_x=finalState.x, robot_y=finalState.y, robot_direction=finalState.direction)
    solver.add_composite_obstacle(x=0, y=12, length=12, width=2, direction=Direction.SKIP, obstacle_id=1)
    solver.add_composite_obstacle(x=0, y=14, length=2, width=12, direction=Direction.SKIP, obstacle_id=2)
    solver.add_composite_obstacle(x=0, y=26, length=12, width=2, direction=Direction.SKIP, obstacle_id=3)

    solver.add_composite_obstacle(x=38, y=15, length=2, width=10, direction=Direction.SKIP, obstacle_id=4)
    solver.add_composite_obstacle(x=24, y=17, length=2, width=6, direction=Direction.SKIP, obstacle_id=5)
    capture = capture_image()
    optimal_path = solver.perform_turn(capture)
    print(optimal_path)

    if not optimal_path:
        print("No valid turn found!")
        return

    FINAL_PATH.extend(optimal_path.copy())

    ## Visit second obstacle
    finalState = optimal_path[-1]
    solver = MazeSolver(size_x=TASK_2_ARENA_WIDTH, size_y=TASK_2_ARENA_HEIGHT, robot_x=finalState.x, robot_y=finalState.y, robot_direction=finalState.direction)
    
    solver.add_composite_obstacle(x=0, y=12, length=12, width=2, direction=Direction.SKIP, obstacle_id=1)
    solver.add_composite_obstacle(x=0, y=14, length=2, width=12, direction=Direction.SKIP, obstacle_id=2)
    solver.add_composite_obstacle(x=0, y=26, length=12, width=2, direction=Direction.SKIP, obstacle_id=3)

    solver.add_composite_obstacle(x=38, y=15, length=2, width=10, direction=Direction.WEST, obstacle_id=4)
    solver.add_composite_obstacle(x=24, y=17, length=2, width=6, direction=Direction.SKIP, obstacle_id=5)

    # 3. Solve for optimal order and paths
    print("Calculating optimal path to visit 2nd obstacle...")
    optimal_path, total_distance = solver.get_optimal_order_dp(retrying=False)

    print(optimal_path)
    
    if not optimal_path:
        print("No valid path found!")
        return
    
    FINAL_PATH.extend(optimal_path.copy())

    ## Follow 2nd image's instruction 
    finalState = optimal_path[-1]
    solver = MazeSolver(size_x=TASK_2_ARENA_WIDTH, size_y=TASK_2_ARENA_HEIGHT, robot_x=finalState.x, robot_y=finalState.y, robot_direction=finalState.direction)
    solver.add_composite_obstacle(x=0, y=12, length=12, width=2, direction=Direction.SKIP, obstacle_id=1)
    solver.add_composite_obstacle(x=0, y=14, length=2, width=12, direction=Direction.SKIP, obstacle_id=2)
    solver.add_composite_obstacle(x=0, y=26, length=12, width=2, direction=Direction.SKIP, obstacle_id=3)

    solver.add_composite_obstacle(x=38, y=15, length=2, width=10, direction=Direction.SKIP, obstacle_id=4)
    solver.add_composite_obstacle(x=24, y=17, length=2, width=6, direction=Direction.SKIP, obstacle_id=5)
    capture = capture_image()
    optimal_path = solver.perform_turn(capture)
    print(optimal_path)

    if not optimal_path:
        print("No valid turn found!")
        return

    FINAL_PATH.extend(optimal_path.copy())

    ## Go back to parking lot
    finalState = optimal_path[-1]
    solver = MazeSolver(size_x=TASK_2_ARENA_WIDTH, size_y=TASK_2_ARENA_HEIGHT, robot_x=finalState.x, robot_y=finalState.y, robot_direction=finalState.direction)
    
    solver.add_composite_obstacle(x=0, y=12, length=12, width=2, direction=Direction.SKIP, obstacle_id=1)
    solver.add_composite_obstacle(x=0, y=14, length=2, width=12, direction=Direction.SKIP, obstacle_id=2)
    solver.add_composite_obstacle(x=0, y=26, length=12, width=2, direction=Direction.SKIP, obstacle_id=3)

    solver.add_composite_obstacle(x=38, y=15, length=2, width=10, direction=Direction.SKIP, obstacle_id=4)
    solver.add_composite_obstacle(x=24, y=17, length=2, width=6, direction=Direction.SKIP, obstacle_id=5)

    print("Calculating optimal path to park the car...")
    optimal_path = solver.get_path_to_parking(parking_x=7, parking_y=20)

    print(optimal_path)
    
    if not optimal_path:
        print("No valid parking path found!")
        return
    
    FINAL_PATH.extend(optimal_path.copy())

    ## VISUALIZE EVERYTHING
    solver = MazeSolver(size_x=TASK_2_ARENA_WIDTH, size_y=TASK_2_ARENA_HEIGHT, robot_x=7, robot_y=20, robot_direction=Direction.EAST)
    
    solver.add_composite_obstacle(x=0, y=12, length=12, width=2, direction=Direction.SKIP, obstacle_id=1)
    solver.add_composite_obstacle(x=0, y=14, length=2, width=12, direction=Direction.SKIP, obstacle_id=2)
    solver.add_composite_obstacle(x=0, y=26, length=12, width=2, direction=Direction.SKIP, obstacle_id=3)

    solver.add_composite_obstacle(x=38, y=15, length=2, width=10, direction=Direction.WEST, obstacle_id=4)
    solver.add_composite_obstacle(x=24, y=17, length=2, width=6, direction=Direction.WEST, obstacle_id=5)

    viz = MazeVisualizer(grid_size=(TASK_2_ARENA_WIDTH, TASK_2_ARENA_HEIGHT), cell_pixel_size=17)
    clock = pygame.time.Clock()
    
    path_index = 0
    running = True
    paused = False
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    path_index = 0
                if event.key == pygame.K_SPACE:
                    paused = not paused

        if not paused and path_index < len(FINAL_PATH) - 1:
            print(FINAL_PATH[path_index])
            path_index += 1

        viz.draw_frame(
            FINAL_PATH[path_index],
            solver.grid.obstacles,
            FINAL_PATH,
            path_index
        )

        clock.tick(10)
        
    pygame.quit()


if __name__ == "__main__":
    print("Starting Task 1: Visit all Obstacles & Capture all images")
    task_1()
    print("\n============================================================================\n")
    print("Starting Task 2: Visit all images & Follow Direction & Go Back to Start")
    task_2()