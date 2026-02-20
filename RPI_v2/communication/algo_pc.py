import socket
import json
import sys
from typing import Optional, Dict, List


class AlgoPC:
    """
    TCP connection for Algorithm PC communication
    RPi acts as server, Algorithm PC connects as client
    """
    def __init__(self):
        # ========== MODIFY: Change to your RPi IP address ==========
        self.host = "192.168.8.1"
        # =============================================================
        self.port = 5001  # Different port from Image Rec PC (5000)
        self.connected = False
        self.server_socket = None
        self.client_socket = None

    def connect(self):
        """
        Act as TCP server, wait for Algorithm PC to connect
        """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print("[AlgoPC] Socket established successfully")

        try:
            self.server_socket.bind((self.host, self.port))
            print(f"[AlgoPC] Socket bound to {self.host}:{self.port}")
        except socket.error as e:
            print("[AlgoPC] Socket binding failed:", e)
            self.server_socket.close()
            sys.exit()

        print("[AlgoPC] Waiting for Algorithm PC connection...")
        try:
            self.server_socket.listen(1)
            self.client_socket, client_address = self.server_socket.accept()
            print(f"[AlgoPC] Algorithm PC connected from {client_address}")
        except socket.error as e:
            print("[AlgoPC] Error accepting connection:", e)
            return False

        self.connected = True
        return True

    def disconnect(self):
        """Disconnect from Algorithm PC"""
        try:
            if self.client_socket:
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
            if self.server_socket:
                self.server_socket.shutdown(socket.SHUT_RDWR)
                self.server_socket.close()
            self.server_socket = None
            self.client_socket = None
            self.connected = False
            print("[AlgoPC] Disconnected successfully")
        except Exception as e:
            print(f"[AlgoPC] Error disconnecting: {e}")

    def send(self, message: str) -> bool:
        """Send string message to Algorithm PC"""
        try:
            self.client_socket.send(message.encode("utf-8"))
            print(f"[AlgoPC] Sent: {message}")
            return True
        except Exception as e:
            print(f"[AlgoPC] Failed to send: {e}")
            return False

    def send_json(self, data: Dict) -> bool:
        """Send JSON data to Algorithm PC (for obstacle coordinates)"""
        try:
            message = json.dumps(data)
            self.client_socket.send(message.encode("utf-8"))
            print(f"[AlgoPC] Sent JSON: {message}")
            return True
        except Exception as e:
            print(f"[AlgoPC] Failed to send JSON: {e}")
            return False

    def receive(self) -> Optional[str]:
        """Receive string message from Algorithm PC"""
        try:
            data = self.client_socket.recv(4096)
            message = data.decode("utf-8")
            return message
        except OSError as e:
            print(f"[AlgoPC] Failed to receive: {e}")
            raise e

    def receive_json(self) -> Optional[Dict]:
        """Receive JSON data from Algorithm PC (for path commands)"""
        try:
            data = self.client_socket.recv(4096)
            message = data.decode("utf-8")
            return json.loads(message)
        except json.JSONDecodeError as e:
            print(f"[AlgoPC] Invalid JSON received: {e}")
            return None
        except OSError as e:
            print(f"[AlgoPC] Failed to receive: {e}")
            raise e
