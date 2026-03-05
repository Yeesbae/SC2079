#!/usr/bin/env python3
"""
Test Algo Client Output
Tests if the algo client produces correct path for given arena data
"""

import sys
import json
import time
from pathlib import Path

# Add project path
sys.path.insert(0, str(Path(__file__).parent / "Algo"))

from Algo.pathAlgo import MazeSolver
from Algo.constants import Direction, ARENA_WIDTH, ARENA_HEIGHT
from Algo.visualizer import MazeVisualizer
import pygame


def test_arena_data():
    """Test arena data - 8 obstacles (from Algo/main.py test case 1)"""
    return {
        "cmd": "START_EXPLORE",
        "grid_size": {"x": 40, "y": 40},
        "robot": {"x": 3, "y": 3, "d": 0},
        "obstacles": [
            {"id": 1, "x": 2,  "y": 15, "width": 2, "length": 2, "d": 4},
            {"id": 2, "x": 16, "y": 4,  "width": 2, "length": 2, "d": 2},
            {"id": 3, "x": 34, "y": 4,  "width": 2, "length": 2, "d": 0},
            {"id": 4, "x": 29, "y": 16, "width": 2, "length": 2, "d": 0},
            {"id": 5, "x": 13, "y": 24, "width": 2, "length": 2, "d": 2},
            {"id": 6, "x": 4,  "y": 35, "width": 2, "length": 2, "d": 4},
            {"id": 7, "x": 18, "y": 35, "width": 2, "length": 2, "d": 2},
            {"id": 8, "x": 34, "y": 35, "width": 2, "length": 2, "d": 6}
        ]
    }


def calculate_path(arena_data):
    """Calculate path using the same logic as algo_client"""
    # Extract grid info
    grid_x = arena_data.get('grid_size', {}).get('x', 40)
    grid_y = arena_data.get('grid_size', {}).get('y', 40)

    # Extract robot info
    robot_data = arena_data.get('robot', {})
    robot_x = robot_data.get('x', 20)
    robot_y = robot_data.get('y', 20)
    robot_d = Direction(robot_data.get('d', 0))

    # Create solver
    solver = MazeSolver(grid_x, grid_y, robot_x, robot_y, robot_d)

    # Add obstacles
    obstacles = arena_data.get('obstacles', [])
    for obs in obstacles:
        obs_x = obs.get('x')
        obs_y = obs.get('y')
        obs_d = Direction(obs.get('d', Direction.SKIP))
        obs_id = obs.get('id')
        obs_width = obs.get('width', 2)
        obs_length = obs.get('length', 2)

        if obs_width == 2 and obs_length == 2:
            solver.add_obstacle(obs_x, obs_y, obs_d, obs_id)
        else:
            solver.add_composite_obstacle(obs_x, obs_y, obs_length, obs_width, obs_d, obs_id)

    # Debug: Check view positions for each obstacle
    dir_name = {0: "NORTH", 2: "EAST", 4: "SOUTH", 6: "WEST", 8: "SKIP"}
    print(f"\n[DEBUG] Checking view positions for each obstacle:")
    all_views = solver.grid.get_view_obstacle_positions(retrying=False)
    non_skip_obs = [o for o in solver.grid.obstacles if o.direction != Direction.SKIP]
    for i, (obs, views) in enumerate(zip(non_skip_obs, all_views)):
        print(f"\n  Obstacle {obs.obstacle_id} at ({obs.x}, {obs.y}) facing {dir_name.get(int(obs.direction), obs.direction)}:")
        if views:
            for v in views:
                print(f"    ✓ View: ({v.x}, {v.y}) facing {dir_name.get(int(v.direction), v.direction)} (penalty={v.penalty})")
        else:
            print(f"    ✗ NO REACHABLE VIEW POSITIONS!")
            # Show raw (unfiltered) view states for debugging
            raw_views = obs.get_view_state(retrying=False)
            print(f"    Raw views (before reachability check): {len(raw_views)}")
            for rv in raw_views:
                reachable = solver.grid.reachable(rv.x, rv.y)
                valid = solver.grid.is_valid_coord(rv.x, rv.y)
                print(f"      ({rv.x}, {rv.y}) facing {dir_name.get(int(rv.direction), rv.direction)} "
                      f"valid_coord={valid} reachable={reachable}")

    # Get optimal path
    print(f"\n[TEST] Calculating path for {len(obstacles)} obstacles...")
    start_time = time.perf_counter()
    try:
        optimal_path, total_cost = solver.get_optimal_order_dp(retrying=False)
    except RuntimeError as e:
        print(f"[TEST] ✗ {e}")
        print("[TEST] Retrying with retrying=True...")
        try:
            optimal_path, total_cost = solver.get_optimal_order_dp(retrying=True)
        except RuntimeError as e2:
            print(f"[TEST] ✗ Retry also failed: {e2}")
            return [], solver
    duration = time.perf_counter() - start_time
    
    print(f"[TEST] ✓ Path calculated in {duration:.2f}s")
    print(f"[TEST] Total cost: {total_cost}")
    print(f"[TEST] Total waypoints: {len(optimal_path)}")

    return optimal_path, solver


def analyze_path(path):
    """Analyze path for correctness"""
    print("\n" + "="*80)
    print("PATH ANALYSIS")
    print("="*80)
    
    # Basic stats
    print(f"\nTotal waypoints: {len(path)}")
    
    # Screenshot points
    screenshots = [wp for wp in path if wp.screenshot_id >= 0]
    print(f"Screenshot waypoints: {len(screenshots)}")
    
    if screenshots:
        print("\nObstacles to photograph:")
        for wp in screenshots:
            dir_name = {0: "NORTH", 2: "EAST", 4: "SOUTH", 6: "WEST", 8: "SKIP"}
            print(f"  - Obstacle {wp.screenshot_id} at ({wp.x:2d}, {wp.y:2d}) facing {dir_name.get(wp.direction, wp.direction)}")
    
    # First and last waypoints
    print(f"\nStart: ({path[0].x}, {path[0].y}) facing {path[0].direction}")
    print(f"End:   ({path[-1].x}, {path[-1].y}) facing {path[-1].direction}")
    
    # Sample waypoints
    print("\nFirst 10 waypoints:")
    for i, wp in enumerate(path[:10]):
        dir_name = {0: "N", 2: "E", 4: "S", 6: "W", 8: "-"}
        s = f"PHOTO({wp.screenshot_id})" if wp.screenshot_id >= 0 else ""
        print(f"  {i+1:3d}. ({wp.x:2d}, {wp.y:2d}) dir={dir_name.get(wp.direction, wp.direction)} {s}")
    
    if len(path) > 20:
        print(f"  ... ({len(path) - 20} waypoints omitted) ...")
        print("\nLast 10 waypoints:")
        for i, wp in enumerate(path[-10:], start=len(path)-9):
            dir_name = {0: "N", 2: "E", 4: "S", 6: "W", 8: "-"}
            s = f"PHOTO({wp.screenshot_id})" if wp.screenshot_id >= 0 else ""
            print(f"  {i:3d}. ({wp.x:2d}, {wp.y:2d}) dir={dir_name.get(wp.direction, wp.direction)} {s}")
    
    # JSON output (what gets sent to RPI)
    print("\n" + "="*80)
    print("JSON OUTPUT (sent to RPI)")
    print("="*80)
    path_json = [cell.get_dict() for cell in path]
    print(json.dumps(path_json[:5], indent=2))
    print(f"... ({len(path_json) - 5} more waypoints)")
    
    return path_json


def visualize_path(solver, path):
    """Visualize the path using pygame"""
    print("\n" + "="*80)
    print("VISUALIZATION")
    print("="*80)
    print("\nControls:")
    print("  SPACE    - Pause/Resume auto-play")
    print("  →        - Next waypoint")
    print("  ←        - Previous waypoint")
    print("  A        - Toggle auto-play")
    print("  Q/ESC    - Quit")
    print("="*80)
    
    viz = MazeVisualizer(grid_size=(ARENA_WIDTH, ARENA_HEIGHT), cell_pixel_size=17)
    clock = pygame.time.Clock()
    
    path_index = 0
    running = True
    auto_play = True
    paused = False
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_RIGHT and not auto_play:
                    path_index = min(path_index + 1, len(path) - 1)
                elif event.key == pygame.K_LEFT and not auto_play:
                    path_index = max(path_index - 1, 0)
                elif event.key == pygame.K_a:
                    auto_play = not auto_play
                    paused = False
                elif event.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False
        
        if auto_play and not paused:
            path_index = (path_index + 1) % len(path)
            time.sleep(0.05)  # Animation speed
        
        # Draw
        viz.draw_frame(
            robot_state=path[path_index],
            obstacles=solver.grid.obstacles,
            path=path,
            upto_idx=path_index,
            override_angle=None
        )
        
        # Show progress
        caption = f"Path Visualization - Waypoint {path_index+1}/{len(path)}"
        if path[path_index].screenshot_id >= 0:
            caption += f" [PHOTO: Obstacle {path[path_index].screenshot_id}]"
        pygame.display.set_caption(caption)
        
        clock.tick(60)
    
    pygame.quit()


def main():
    print("\n" + "="*80)
    print("ALGO CLIENT OUTPUT TEST")
    print("="*80)
    
    # Get test data
    arena_data = test_arena_data()
    
    print("\nTest Arena:")
    print(f"  Grid: {arena_data['grid_size']['x']}x{arena_data['grid_size']['y']}")
    print(f"  Robot: ({arena_data['robot']['x']}, {arena_data['robot']['y']}) facing {arena_data['robot']['d']}")
    print(f"  Obstacles: {len(arena_data['obstacles'])}")
    
    # Calculate path
    path, solver = calculate_path(arena_data)
    
    if not path:
        print("[TEST] ✗ No path found!")
        return False
    
    # Analyze
    path_json = analyze_path(path)
    
    # Ask if user wants visualization
    print("\n" + "="*80)
    response = input("Show visualization? (y/n) >> ").strip().lower()
    
    if response == 'y':
        visualize_path(solver, path)
    
    print("\n[TEST] ✓ Test complete!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
