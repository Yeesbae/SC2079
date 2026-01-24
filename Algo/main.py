import pygame
from pathAlgo import MazeSolver
from constants import Direction
from visualizer import MazeVisualizer

def main():
    # Start robot at (1, 1) facing North
    solver = MazeSolver(size_x=20, size_y=20, robot_x=1, robot_y=1, robot_direction=Direction.NORTH)
    
    # 2. Add 5 Obstacles (x, y, image_direction, id)
    solver.add_obstacle(x=5, y=10, direction=Direction.SOUTH, obstacle_id=1)
    solver.add_obstacle(x=15, y=5, direction=Direction.WEST, obstacle_id=2)
    solver.add_obstacle(x=10, y=18, direction=Direction.SOUTH, obstacle_id=3)
    solver.add_obstacle(x=2, y=15, direction=Direction.EAST, obstacle_id=4)
    solver.add_obstacle(x=18, y=12, direction=Direction.WEST, obstacle_id=5)

    # 3. Solve for optimal order and paths
    print("Calculating optimal Hamiltonian path...")
    optimal_path, total_distance = solver.get_optimal_order_dp(retrying=False)
    
    if not optimal_path:
        print("No valid path found!")
        return

    # 4. Setup Visualizer
    viz = MazeVisualizer(grid_size=(20, 20), cell_pixel_size=35)
    clock = pygame.time.Clock()
    
    path_index = 0
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # If we have path steps left, update the robot
        if path_index < len(optimal_path):
            current_state = optimal_path[path_index]
            # Draw frame: Current robot pos, list of obstacles, and full path line
            viz.draw_frame(current_state, solver.grid.obstacles, optimal_path)
            path_index += 1
        else:
            # Path finished, just keep drawing the last frame
            viz.draw_frame(optimal_path[-1], solver.grid.obstacles, optimal_path)

        clock.tick(10)

    pygame.quit()

if __name__ == "__main__":
    main()