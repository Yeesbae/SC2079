import pygame
import time
import socket
import json
import sys
from pathAlgo import MazeSolver
from constants import Direction, ARENA_WIDTH, ARENA_HEIGHT
from visualizer import MazeVisualizer
from Util.helper import compress_path

# ── RPI server settings ──────────────────────────────────────────────────────
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 6000


def receive_from_rpi():
    """
    Start a TCP server, wait for RPI to connect, and receive arena data.

    RPI sends JSON in this format:
        {
            "cmd": "START_EXPLORE",
            "grid_size": {"x": 40, "y": 40},
            "robot": {"x": 3, "y": 3, "d": 0},
            "obstacles": [
                {"id": 1, "x": 7, "y": 7, "d": 0, "width": 2, "length": 2},
                ...
            ]
        }

    Returns:
        (arena_data dict, conn socket) — caller must close conn after use.
    """
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((SERVER_HOST, SERVER_PORT))
    server_sock.listen(1)
    print(f"[Server] Waiting for RPI connection on {SERVER_HOST}:{SERVER_PORT} ...")

    conn, addr = server_sock.accept()
    print(f"[Server] RPI connected from {addr}")
    server_sock.close()  # stop accepting new connections

    raw = b""
    while True:
        chunk = conn.recv(8192)
        if not chunk:
            break
        raw += chunk
        try:
            arena_data = json.loads(raw.decode("utf-8"))
            print(f"[Server] Arena data received: {len(arena_data.get('obstacles', []))} obstacles")
            return arena_data, conn
        except json.JSONDecodeError:
            continue  # keep reading until we have a complete JSON object


def build_solver_from_rpi(arena_data):
    """
    Build a MazeSolver from the JSON arena data sent by RPI.

    Args:
        arena_data (dict): parsed JSON from RPI

    Returns:
        MazeSolver instance with obstacles already added
    """
    grid_x = arena_data.get("grid_size", {}).get("x", ARENA_WIDTH)
    grid_y = arena_data.get("grid_size", {}).get("y", ARENA_HEIGHT)

    robot = arena_data.get("robot", {})
    robot_x = robot.get("x", 3)
    robot_y = robot.get("y", 3)
    robot_d = Direction(robot.get("d", Direction.NORTH))

    solver = MazeSolver(size_x=grid_x, size_y=grid_y,
                        robot_x=robot_x, robot_y=robot_y,
                        robot_direction=robot_d)

    for obs in arena_data.get("obstacles", []):
        obs_x      = obs.get("x")
        obs_y      = obs.get("y")
        obs_d      = Direction(obs.get("d", Direction.SKIP))
        obs_id     = obs.get("id")
        obs_width  = obs.get("width", 2)
        obs_length = obs.get("length", 2)

        if obs_width == 2 and obs_length == 2:
            solver.add_obstacle(obs_x, obs_y, obs_d, obs_id)
        else:
            solver.add_composite_obstacle(obs_x, obs_y, obs_length, obs_width, obs_d, obs_id)

    return solver


def task_1(rpi_conn=None, solver=None):
    """
    Run the path-finding task and display the visualizer.

    Args:
        rpi_conn: open socket to RPI (optional). If provided, the computed path
                  is sent back as JSON before the visualizer starts.
        solver:   pre-built MazeSolver from RPI data (optional).
                  If None, hardcoded test obstacles are used.
    """
    # ── Build solver ──────────────────────────────────────────────────────────
    if solver is None:
        # ── Hardcoded test obstacles (local mode only) ────────────────────────
        # Start robot at (3, 3) facing NORTH
        solver = MazeSolver(size_x=ARENA_WIDTH, size_y=ARENA_HEIGHT, robot_x=3, robot_y=3, robot_direction=Direction.NORTH)

        # """5 Obstacles: Test Case 1"""
        # solver.add_obstacle(x=7,  y=7,  direction=Direction.NORTH, obstacle_id=1)
        # solver.add_obstacle(x=30, y=7,  direction=Direction.WEST,  obstacle_id=2)
        # solver.add_obstacle(x=7,  y=30, direction=Direction.EAST,  obstacle_id=3)
        # solver.add_obstacle(x=30, y=30, direction=Direction.SOUTH, obstacle_id=4)
        # solver.add_obstacle(x=18, y=18, direction=Direction.WEST,  obstacle_id=5)

        """5 Obstacles: Test Case 2"""
        solver.add_obstacle(x=0,  y=18,  direction=Direction.SOUTH, obstacle_id=1)
        solver.add_obstacle(x=25, y=5,  direction=Direction.WEST,  obstacle_id=2)
        solver.add_obstacle(x=35,  y=13, direction=Direction.WEST,  obstacle_id=3)
        solver.add_obstacle(x=25, y=23, direction=Direction.NORTH, obstacle_id=4)
        solver.add_obstacle(x=5, y=33, direction=Direction.EAST,  obstacle_id=5)

        # """8 Obstacles: Test Case 1"""
        # solver.add_obstacle(x=2,  y=15,  direction=Direction.SOUTH, obstacle_id=1)
        # solver.add_obstacle(x=16, y=4,  direction=Direction.EAST,  obstacle_id=2)
        # solver.add_obstacle(x=34, y=4,  direction=Direction.NORTH, obstacle_id=3)
        # solver.add_obstacle(x=29, y=16, direction=Direction.NORTH,  obstacle_id=4)
        # solver.add_obstacle(x=13, y=24, direction=Direction.EAST, obstacle_id=5)
        # solver.add_obstacle(x=4, y=35, direction=Direction.SOUTH,  obstacle_id=6)
        # solver.add_obstacle(x=18, y=35, direction=Direction.EAST, obstacle_id=7)
        # solver.add_obstacle(x=34, y=35, direction=Direction.WEST,  obstacle_id=8)

        # """8 Obstacles: Test Case 2"""
        # solver.add_obstacle(x=3,  y=15,  direction=Direction.SOUTH, obstacle_id=1)
        # solver.add_obstacle(x=35, y=3,  direction=Direction.NORTH,  obstacle_id=2)
        # solver.add_obstacle(x=19, y=18,  direction=Direction.EAST, obstacle_id=3)
        # solver.add_obstacle(x=19, y=23, direction=Direction.EAST,  obstacle_id=4)
        # solver.add_obstacle(x=8, y=30, direction=Direction.EAST, obstacle_id=5)
        # solver.add_obstacle(x=3, y=35, direction=Direction.SOUTH,  obstacle_id=6)
        # solver.add_obstacle(x=31, y=31, direction=Direction.SOUTH, obstacle_id=7)
        # solver.add_obstacle(x=36, y=36, direction=Direction.SOUTH,  obstacle_id=8)

        # """8 Obstacles: Test Case 3"""
        # solver.add_obstacle(x=5,  y=18,  direction=Direction.NORTH, obstacle_id=1)
        # solver.add_obstacle(x=9, y=18,  direction=Direction.SOUTH,  obstacle_id=2)
        # solver.add_obstacle(x=18, y=3,  direction=Direction.WEST, obstacle_id=3)
        # solver.add_obstacle(x=36, y=3, direction=Direction.WEST,  obstacle_id=4)
        # solver.add_obstacle(x=34, y=11, direction=Direction.NORTH, obstacle_id=5)
        # solver.add_obstacle(x=5, y=33, direction=Direction.SOUTH,  obstacle_id=6)
        # solver.add_obstacle(x=15, y=33, direction=Direction.EAST, obstacle_id=7)
        # solver.add_obstacle(x=36, y=33, direction=Direction.WEST,  obstacle_id=8)

        # 5 Obs around 10.51 ~ 11.63 seconds
        # 8 Obs around 40.41 ~ 51.46 seconds

    # ── Path calculation ──────────────────────────────────────────────────────
    print("Calculating optimal Hamiltonian path...")

    # Start the timer
    start_time = time.perf_counter()
    # Execute the line
    optimal_path, total_distance = solver.get_optimal_order_dp(retrying=False)
    print(optimal_path)
    print()
    compressed_path = compress_path(optimal_path)
    print(compressed_path)
    # End the timer
    end_time = time.perf_counter()
    # Calculate duration
    duration = end_time - start_time
    print(f"The DP solver took {duration:.6f} seconds.")
    
    print("Total Distance: ", total_distance)

    if not optimal_path:
        print("No valid path found!")
        if rpi_conn:
            rpi_conn.send(json.dumps({"error": "No valid path found"}).encode("utf-8"))
            rpi_conn.close()
        return

    # ── Send path back to RPI ─────────────────────────────────────────────────
    if rpi_conn:
        path_list = [cell.get_dict() for cell in optimal_path]
        compressed = compress_path(optimal_path)
        response = {"path": path_list, "commands": compressed, "total_distance": total_distance}
        rpi_conn.send(json.dumps(response).encode("utf-8"))
        print(f"[Server] Path sent to RPI ({len(path_list)} waypoints, {len(compressed)} commands)")
        rpi_conn.close()

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

    if "--rpi" in sys.argv or "-r" in sys.argv:
        # ── RPI mode: wait for RPI to send arena data, then solve & visualize ──
        print("[Mode] RPI input mode — waiting for RPI connection...")
        arena_data, rpi_conn = receive_from_rpi()
        solver = build_solver_from_rpi(arena_data)
        task_1(rpi_conn=rpi_conn, solver=solver)
    else:
        # ── Local mode: use hardcoded test obstacles ───────────────────────────
        print("[Mode] Local test mode — using hardcoded obstacles")
        print("       Run with --rpi flag to receive obstacles from RPI")
        task_1()
