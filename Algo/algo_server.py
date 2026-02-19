"""
Algo Server - TCP server for receiving arena data and sending calculated paths
Runs on PC, RPi connects as client to request path calculation
"""

import socket
import json
import threading
from pathAlgo import MazeSolver
from Entities.Cell import CellState
from constants import Direction


class AlgoServer:
    """
    TCP server that runs the MazeSolver algorithm
    RPi sends arena data (obstacles, robot position), server responds with path
    """

    def __init__(self, host='0.0.0.0', port=6000):
        """
        Initialize Algo server

        Args:
            host (str): Server host (0.0.0.0 to listen on all interfaces)
            port (int): Server port (6000 is unique from image rec port 5000)
        """
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = False

    def start(self):
        """Start the TCP server and listen for connections"""
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        self.running = True
        print(f"[AlgoServer] Listening on {self.host}:{self.port}")

        try:
            while self.running:
                print(f"[AlgoServer] Waiting for connection...")
                conn, addr = self.socket.accept()
                print(f"[AlgoServer] RPi connected from {addr}")

                # Handle this connection in a separate thread
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(conn, addr),
                    daemon=True
                )
                client_thread.start()

        except KeyboardInterrupt:
            print(f"\n[AlgoServer] Shutting down...")
            self.stop()

    def stop(self):
        """Stop the server"""
        self.running = False
        self.socket.close()

    def _handle_client(self, conn, addr):
        """
        Handle a single client connection
        Receives arena data, calculates path, sends it back
        """
        try:
            while self.running:
                # Receive arena data from RPi
                data = conn.recv(8192).decode('utf-8')

                if not data:
                    print(f"[AlgoServer] Client {addr} disconnected")
                    break

                print(f"[AlgoServer] Received data from {addr}")

                try:
                    # Parse arena data
                    arena_data = json.loads(data)

                    # Calculate path
                    path = self._calculate_path(arena_data)

                    # Send path back
                    path_json = json.dumps(path)
                    conn.send(path_json.encode('utf-8'))
                    print(f"[AlgoServer] Sent path to {addr}")

                except json.JSONDecodeError:
                    print(f"[AlgoServer] Invalid JSON received from {addr}")
                    conn.send(json.dumps({"error": "Invalid JSON"}).encode('utf-8'))
                except Exception as e:
                    print(f"[AlgoServer] Error processing request: {str(e)}")
                    conn.send(json.dumps({"error": str(e)}).encode('utf-8'))

        except Exception as e:
            print(f"[AlgoServer] Connection error with {addr}: {str(e)}")
        finally:
            conn.close()

    def _calculate_path(self, arena_data):
        """
        Calculate path using MazeSolver

        Args:
            arena_data (dict): {
                'grid_size': {'x': int, 'y': int},
                'robot': {'x': int, 'y': int, 'd': int},
                'obstacles': [{'id': int, 'x': int, 'y': int, 'width': int, 'length': int, 'd': int}, ...],
                'parking': {'x': int, 'y': int, 'd': int} (optional)
            }

        Returns:
            list: [
                {'x': int, 'y': int, 'd': int, 's': int},
                ...
            ]
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
        print(f"[AlgoServer] Calculating path for {len(obstacles)} obstacles...")
        optimal_path, total_cost = solver.get_optimal_order_dp(retrying=False)
        print(f"[AlgoServer] Path calculated. Total cost: {total_cost}")

        # Check for parking location
        parking = arena_data.get('parking')
        if parking:
            parking_x = parking.get('x')
            parking_y = parking.get('y')
            parking_d = Direction(parking.get('d', Direction.NORTH))
            path_to_parking = solver.get_path_to_parking(parking_x, parking_y, parking_d)
            optimal_path.extend(path_to_parking)

        # Convert CellState objects to dictionaries
        path_list = [cell.get_dict() for cell in optimal_path]

        return path_list


if __name__ == "__main__":
    """Run the algo server"""
    server = AlgoServer(host='0.0.0.0', port=6000)
    server.start()
