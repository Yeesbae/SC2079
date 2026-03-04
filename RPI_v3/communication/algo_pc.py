import socket
import json
import sys
from typing import Optional, Dict, List


class AlgoPC:
    """
    TCP connection for Algorithm PC communication
    RPi acts as TCP client, connects to Algorithm PC server
    """
    def __init__(self):
        # ========== MODIFY: Change to your Algorithm PC IP address ==========
        self.host = "192.168.8.100"  # Algorithm PC IP address
        # =====================================================================
        self.port = 6000  # Algorithm server port (from algo_server.py)
        self.connected = False
        self.socket = None

    def connect(self):
        """
        Connect to Algorithm PC as TCP client
        Algorithm PC must be running algo_server.py first
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print(f"[AlgoPC] Connecting to Algorithm PC at {self.host}:{self.port}...")
            
            self.socket.connect((self.host, self.port))
            print("[AlgoPC] Connected to Algorithm PC successfully")
            
            self.connected = True
            return True
            
        except socket.error as e:
            print(f"[AlgoPC] Connection failed: {e}")
            print("[AlgoPC] Make sure:")
            print("[AlgoPC]   1. Algorithm PC is running algo_server.py")
            print(f"[AlgoPC]   2. IP address {self.host} is correct")
            print("[AlgoPC]   3. Both devices are on the same network")
            print(f"[AlgoPC]   4. Firewall allows port {self.port}")
            if self.socket:
                self.socket.close()
            return False

    def disconnect(self):
        """Disconnect from Algorithm PC"""
        try:
            if self.socket:
                self.socket.shutdown(socket.SHUT_RDWR)
                self.socket.close()
            self.socket = None
            self.connected = False
            print("[AlgoPC] Disconnected successfully")
        except Exception as e:
            print(f"[AlgoPC] Error disconnecting: {e}")

    def send(self, message: str) -> bool:
        """Send string message to Algorithm PC"""
        try:
            self.socket.send(message.encode("utf-8"))
            print(f"[AlgoPC] Sent: {message}")
            return True
        except Exception as e:
            print(f"[AlgoPC] Failed to send: {e}")
            return False

    def send_json(self, data: Dict) -> bool:
        """Send JSON data to Algorithm PC (for obstacle coordinates)"""
        try:
            message = json.dumps(data)
            self.socket.send(message.encode("utf-8"))
            print(f"[AlgoPC] Sent JSON: {message}")
            return True
        except Exception as e:
            print(f"[AlgoPC] Failed to send JSON: {e}")
            return False

    def receive(self, timeout: float = 5.0) -> Optional[str]:
        """
        Receive string message from Algorithm PC
        
        Args:
            timeout: Socket timeout in seconds (default 5.0)
            
        Returns:
            Message string or None on timeout/error
        """
        try:
            self.socket.settimeout(timeout)
            data = self.socket.recv(4096)
            self.socket.settimeout(None)
            if data:
                message = data.decode("utf-8")
                return message
            return None
        except socket.timeout:
            return None
        except OSError as e:
            print(f"[AlgoPC] Failed to receive: {e}")
            raise e

    def receive_json(self, timeout: float = 5.0) -> Optional[Dict]:
        """
        Receive JSON data from Algorithm PC (for path commands)
        
        Args:
            timeout: Socket timeout in seconds
        """
        try:
            self.socket.settimeout(timeout)
            data = self.socket.recv(4096)
            self.socket.settimeout(None)
            if data:
                message = data.decode("utf-8")
                return json.loads(message)
            return None
        except socket.timeout:
            return None
        except json.JSONDecodeError as e:
            print(f"[AlgoPC] Invalid JSON received: {e}")
            return None
        except OSError as e:
            print(f"[AlgoPC] Failed to receive: {e}")
            raise e
