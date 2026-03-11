"""
Algo Client - TCP client that connects to RPi server
Receives arena data from RPi, calculates path, sends it back
"""

import pygame
import socket
import json
import time
from pathAlgo import MazeSolver
from constants import Direction
from visualizer import MazeVisualizer
from Util.helper import compress_path, command_generator


class AlgoClient:
    """
    TCP client that connects to RPi and runs the MazeSolver algorithm
    RPi is the server, this Algo PC connects as client
    """

    def __init__(self, rpi_host='192.168.8.1', rpi_port=6000):
        """
        Initialize Algo client

        Args:
            rpi_host (str): RPi IP address (default: 192.168.8.1)
            rpi_port (int): RPi port (default: 6000)
        """
        self.rpi_host = rpi_host
        self.rpi_port = rpi_port
        self.socket = None
        self.connected = False

    def connect(self) -> bool:
        """Connect to RPi server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print(f"[AlgoClient] Connecting to RPi at {self.rpi_host}:{self.rpi_port}...")
            self.socket.connect((self.rpi_host, self.rpi_port))
            self.connected = True
            print(f"[AlgoClient] ✓ Connected to RPi successfully!")
            return True
        except Exception as e:
            print(f"[AlgoClient] ✗ Failed to connect: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from RPi"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.connected = False
        print("[AlgoClient] Disconnected from RPi")

    def send(self, message: str) -> bool:
        """Send string message to RPi (newline-delimited)"""
        if not self.connected or not self.socket:
            print("[AlgoClient] Not connected to RPi")
            return False
        
        try:
            # Use newline delimiter for message framing
            if not message.endswith('\n'):
                message = message + '\n'
            self.socket.sendall(message.encode('utf-8'))
            print(f"[AlgoClient] Sent: {message.strip()}")
            return True
        except Exception as e:
            print(f"[AlgoClient] Send error: {e}")
            self.connected = False
            return False

    def send_json(self, data: dict) -> bool:
        """Send JSON data to RPi (newline-delimited)"""
        if not self.connected or not self.socket:
            print("[AlgoClient] Not connected to RPi")
            return False
        
        try:
            message = json.dumps(data) + '\n'
            self.socket.sendall(message.encode('utf-8'))
            print(f"[AlgoClient] Sent JSON: {message.strip()}")
            return True
        except Exception as e:
            print(f"[AlgoClient] Send error: {e}")
            self.connected = False
            return False

    def receive(self, timeout: float = 5.0) -> str:
        """Receive a complete newline-delimited message from RPi"""
        if not self.connected or not self.socket:
            return None
        
        try:
            self.socket.settimeout(timeout)
            buffer = b''
            while True:
                chunk = self.socket.recv(4096)
                if not chunk:
                    print("[AlgoClient] RPi disconnected")
                    self.connected = False
                    return None
                buffer += chunk
                if b'\n' in buffer:
                    message = buffer[:buffer.index(b'\n')].decode('utf-8')
                    print(f"[AlgoClient] Received: {message}")
                    return message
        except socket.timeout:
            # Return whatever we have if timeout
            if buffer:
                message = buffer.decode('utf-8').strip()
                if message:
                    print(f"[AlgoClient] Received (partial): {message}")
                    return message
            return None
        except Exception as e:
            print(f"[AlgoClient] Receive error: {e}")
            self.connected = False
            return None

    def run(self):
        """Main loop - connect and process requests from RPi"""
        print("\n" + "=" * 60)
        print("ALGO CLIENT - Connecting to RPi")
        print("=" * 60)
        
        # Connect to RPi
        if not self.connect():
            print("[AlgoClient] Failed to connect. Exiting.")
            return
        
        print("\n[AlgoClient] Waiting for arena data from RPi...")
        print("Commands:")
        print("  Press Ctrl+C to disconnect and exit")
        print("=" * 60 + "\n")
        
        try:
            while self.connected:
                # Receive arena data from RPi
                data = self.receive(timeout=30.0)
                
                if not data:
                    continue
                
                try:
                    # Parse arena data
                    arena_data = json.loads(data)
                    print(f"\n[AlgoClient] Received arena data with {len(arena_data.get('obstacles', []))} obstacles")
                    
                    # Calculate path
                    path = self._calculate_path(arena_data)
                    
                    # Send path back to RPi
                    path_json = json.dumps(path)
                    self.send(path_json)
                    print(f"[AlgoClient] Path sent to RPi\n")

                    print("Visualizing Paths:\n")
                    optimal_path = path["full_path"]
                    obstacles_list = path["obstacles"]
                    viz = MazeVisualizer(grid_size=path["grid_size"], cell_pixel_size=17)
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
                                obstacles_list,
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
                                obstacles_list,
                                optimal_path,
                                path_index
                            )

                        clock.tick(60)

                    pygame.quit()
                    
                except json.JSONDecodeError:
                    print(f"[AlgoClient] Invalid JSON received from RPi")
                    self.send(json.dumps({"error": "Invalid JSON"}))
                except Exception as e:
                    print(f"[AlgoClient] Error processing request: {str(e)}")
                    self.send(json.dumps({"error": str(e)}))
        
        except KeyboardInterrupt:
            print("\n\n[AlgoClient] Interrupted by user")
        finally:
            self.disconnect()

    def _calculate_path(self, arena_data):
        """
        Calculate path using MazeSolver and convert to STM32 commands.

        Args:
            arena_data (dict): {
                "cmd": "START_EXPLORE",
                "grid_size": {"x":40, "y":40},
                "robot": {"x":0,"y":0,"d":0},
                "obstacles": [
                    {"id":1,"x":21,"y":14,"width":2,"length":2,"d":0}, 
                    {"id":2,"x":30,"y":27,"width":2,"length":2,"d":2}
                ]
            }

        Returns:
            dict: {
                "commands": ["FW10", "BL00", "FW20", "SNAP3_C", "FW10", ..., "FIN"],
                "path": [{'x': int, 'y': int, 'd': int, 's': int}, ...]
            }
        """

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

            # If width/length are both 2, use single obstacle; otherwise composite
            if obs_width == 2 and obs_length == 2:
                solver.add_obstacle(obs_x, obs_y, obs_d, obs_id)
            else:
                solver.add_composite_obstacle(obs_x, obs_y, obs_length, obs_width, obs_d, obs_id)

        # Get optimal path
        print(f"[AlgoClient] Calculating path for {len(obstacles)} obstacles...")
        optimal_path, total_cost = solver.get_optimal_order_dp(retrying=False)
        compressed_path = compress_path(optimal_path)

        print(f"[AlgoClient] Path calculated. Total cost: {total_cost}")

        # Build obstacle dicts for command_generator (needs 'id', 'x', 'y', 'd' as int)
        obstacle_dicts = []
        for obs in obstacles:
            obstacle_dicts.append({
                'id': obs.get('id'),
                'x': obs.get('x'),
                'y': obs.get('y'),
                'd': obs.get('d', 8)  # Direction int value
            })

        # Generate compressed STM32 commands from the CellState path
        stm32_commands = command_generator(compressed_path, obstacle_dicts)

        print(f"[AlgoClient] Generated {len(stm32_commands)} STM32 commands: {stm32_commands}")

        # Also include raw path for debugging
        path_list = [cell.get_dict() for cell in compressed_path]

        return {
            "commands": stm32_commands,
            "path": path_list,
            "full_path": optimal_path,
            "obstacles": solver.grid.obstacles,
            "grid_size": (grid_x, grid_y)
        }


if __name__ == "__main__":
    """Run the algo client"""
    import sys
    
    # Allow custom RPi IP from command line
    rpi_host = sys.argv[1] if len(sys.argv) > 1 else '192.168.8.1'
    
    client = AlgoClient(rpi_host=rpi_host, rpi_port=6000)
    client.run()
