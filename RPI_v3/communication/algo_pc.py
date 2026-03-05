import socket
import json
import sys
from typing import Optional, Dict, List


class AlgoPC:
    """
    TCP Server for Algorithm PC communication
    RPi acts as TCP server, Algorithm PC connects as client
    """
    def __init__(self, port: int = 6000):
        # ========== Configuration ==========
        self.port = port  # Port to listen on
        # ===================================
        self.server_socket = None
        self.client_socket = None
        self.client_address = None
        self.connected = False
        self.server_initialized = False

    def start_server(self) -> bool:
        """
        Start TCP server and bind to port
        Must be called before wait_for_connection()
        """
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(("0.0.0.0", self.port))
            self.server_socket.listen(1)
            
            # Get local IP address
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            print(f"[AlgoPC] Server started on {local_ip}:{self.port}")
            print(f"[AlgoPC] Waiting for Algorithm PC to connect...")
            self.server_initialized = True
            return True
            
        except socket.error as e:
            print(f"[AlgoPC] Failed to start server: {e}")
            print(f"[AlgoPC] Port {self.port} may already be in use")
            if self.server_socket:
                self.server_socket.close()
            return False

    def wait_for_connection(self, timeout: float = 300.0) -> bool:
        """
        Wait for Algorithm PC to connect
        
        Args:
            timeout: Connection timeout in seconds (default 5 minutes)
            
        Returns:
            True if connected successfully
        """
        if not self.server_initialized:
            print("[AlgoPC] Server not initialized. Call start_server() first.")
            return False
        
        try:
            # Close old client socket if exists
            if self.client_socket:
                try:
                    self.client_socket.close()
                except:
                    pass
                self.client_socket = None
            
            self.server_socket.settimeout(timeout)
            self.client_socket, self.client_address = self.server_socket.accept()
            self.server_socket.settimeout(None)
            self.connected = True
            print(f"[AlgoPC] ✓ Algorithm PC connected from {self.client_address}")
            return True
            
        except socket.timeout:
            print(f"[AlgoPC] ✗ Connection timeout - no client connected within {timeout}s")
            self.connected = False
            return False
        except Exception as e:
            print(f"[AlgoPC] ✗ Connection error: {e}")
            self.connected = False
            return False

    def connect(self) -> bool:
        """
        Start server and wait for Algorithm PC connection
        (Convenience method that combines start_server + wait_for_connection)
        
        Returns:
            True if connected successfully
        """
        # If server already initialized, just wait for new client
        if self.server_initialized and self.server_socket:
            return self.wait_for_connection()
        
        # Start server first
        if not self.start_server():
            return False
        
        # Wait for client
        return self.wait_for_connection()

    def disconnect(self, keep_server: bool = True):
        """
        Disconnect Algorithm PC client
        
        Args:
            keep_server: If True, keep server socket alive for reconnections
        """
        try:
            self.connected = False
            if self.client_socket:
                try:
                    self.client_socket.close()
                except:
                    pass
                self.client_socket = None
            
            # Only close server if explicitly requested
            if not keep_server and self.server_socket:
                try:
                    self.server_socket.close()
                except:
                    pass
                self.server_socket = None
                self.server_initialized = False
            
            self.client_address = None
            if keep_server:
                print("[AlgoPC] Client disconnected (server still listening)")
            else:
                print("[AlgoPC] Server shut down")
        except Exception as e:
            print(f"[AlgoPC] Disconnect error: {e}")

    def send(self, message: str) -> bool:
        """Send string message to Algorithm PC (newline-delimited)"""
        if not self.connected or not self.client_socket:
            print("[AlgoPC] Not connected")
            return False
        
        try:
            if not message.endswith('\n'):
                message = message + '\n'
            self.client_socket.sendall(message.encode("utf-8"))
            print(f"[AlgoPC] Sent: {message.strip()}")
            return True
        except Exception as e:
            print(f"[AlgoPC] Failed to send: {e}")
            self.connected = False
            return False

    def send_json(self, data: Dict) -> bool:
        """Send JSON data to Algorithm PC (newline-delimited)"""
        if not self.connected or not self.client_socket:
            print("[AlgoPC] Not connected")
            return False
        
        try:
            message = json.dumps(data) + '\n'
            self.client_socket.sendall(message.encode("utf-8"))
            print(f"[AlgoPC] Sent JSON: {message.strip()}")
            return True
        except Exception as e:
            print(f"[AlgoPC] Failed to send JSON: {e}")
            self.connected = False
            return False

    def receive(self, timeout: float = 5.0) -> Optional[str]:
        """
        Receive a complete newline-delimited message from Algorithm PC
        Buffers until a full message (ending with newline) is received.
        
        Args:
            timeout: Socket timeout in seconds (default 5.0)
            
        Returns:
            Message string or None on timeout/error
        """
        if not self.connected or not self.client_socket:
            return None
        
        try:
            self.client_socket.settimeout(timeout)
            buffer = b''
            while True:
                chunk = self.client_socket.recv(4096)
                if not chunk:
                    # Empty data means client disconnected
                    print("[AlgoPC] Client disconnected (recv returned empty)")
                    self.connected = False
                    return None
                buffer += chunk
                if b'\n' in buffer:
                    message = buffer[:buffer.index(b'\n')].decode("utf-8")
                    print(f"[AlgoPC] Received: {message}")
                    return message
        except socket.timeout:
            # Return whatever we have if timeout
            if buffer:
                message = buffer.decode("utf-8").strip()
                if message:
                    print(f"[AlgoPC] Received (partial): {message}")
                    return message
            return None
        except OSError as e:
            print(f"[AlgoPC] Failed to receive: {e}")
            self.connected = False
            return None

    def receive_json(self, timeout: float = 5.0) -> Optional[Dict]:
        """
        Receive JSON data from Algorithm PC (for path commands)
        
        Args:
            timeout: Socket timeout in seconds
        """
        if not self.connected or not self.client_socket:
            return None
        
        try:
            self.client_socket.settimeout(timeout)
            data = self.client_socket.recv(4096)
            self.client_socket.settimeout(None)
            if data:
                message = data.decode("utf-8")
                json_data = json.loads(message)
                print(f"[AlgoPC] Received JSON: {message}")
                return json_data
            else:
                # Empty data means client disconnected
                print("[AlgoPC] Client disconnected (recv returned empty)")
                self.connected = False
                return None
        except socket.timeout:
            return None
        except json.JSONDecodeError as e:
            print(f"[AlgoPC] Invalid JSON received: {e}")
            return None
        except OSError as e:
            print(f"[AlgoPC] Failed to receive: {e}")
            self.connected = False
            return None
    
    def is_connected(self) -> bool:
        """Check if Algorithm PC is connected"""
        return self.connected
