"""
Algo Client - Connects to Algo server on PC for path calculation
RPi sends arena data, receives calculated path back
"""

import socket
import json


class AlgoClient:
    """
    TCP client that connects to Algo server on PC
    Sends arena data, receives calculated path
    """

    def __init__(self, host='192.168.88.3', port=6000):
        """
        Initialize Algo client

        Args:
            host (str): Algo server host (PC IP address)
            port (int): Algo server port (default 6000)
        """
        self.host = host
        self.port = port
        self.socket = None

    def connect(self):
        """
        Connect to Algo server
        Blocks until connection successful

        Raises:
            Exception: If connection fails
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"[AlgoClient] Connected to Algo server at {self.host}:{self.port}")
        except Exception as e:
            print(f"[AlgoClient] Connection error: {str(e)}")
            raise

    def send_arena_data(self, arena_data):
        """
        Send arena data to Algo server

        Args:
            arena_data (dict): {
                'grid_size': {'x': int, 'y': int},
                'robot': {'x': int, 'y': int, 'd': int},
                'obstacles': [{'id': int, 'x': int, 'y': int, 'width': int, 'length': int, 'd': int}, ...],
                'parking': {'x': int, 'y': int, 'd': int} (optional)
            }

        Returns:
            list: Calculated path as [{'x': int, 'y': int, 'd': int, 's': int}, ...]
        """
        try:
            # Send arena data
            message = json.dumps(arena_data)
            self.socket.send(message.encode('utf-8'))
            print(f"[AlgoClient] Sent arena data to server")

            # Receive path back
            data = self.socket.recv(81920).decode('utf-8')

            if not data:
                raise ConnectionError("Algo server disconnected")

            path = json.loads(data)

            # Check for errors
            if isinstance(path, dict) and 'error' in path:
                raise Exception(f"Algo server error: {path['error']}")

            print(f"[AlgoClient] Received path with {len(path)} waypoints")
            return path

        except json.JSONDecodeError as e:
            print(f"[AlgoClient] Invalid JSON from server: {str(e)}")
            raise
        except Exception as e:
            print(f"[AlgoClient] Error: {str(e)}")
            raise

    def disconnect(self):
        """Close connection to Algo server"""
        if self.socket:
            self.socket.close()
            print(f"[AlgoClient] Disconnected from Algo server")

    def __enter__(self):
        """Context manager support"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support"""
        self.disconnect()
