import pygame
from pathAlgo import MazeSolver
from constants import Direction
from visualizer import MazeVisualizer

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


if __name__ == "__main__":
    print("Starting Task 1: Visit all Obstacles & Capture all images")
    task_1()
    print("\n============================================================================\n")
    print("Starting Task 2: Visit all images & Follow Direction & Go Back to Start")
    task_2()