"""
Bluetooth RFCOMM handler for Android communication
Uses PyBluez for Bluetooth serial communication
"""
import socket
from typing import Optional


class BluetoothHandler:
    """
    Bluetooth RFCOMM server for Android communication
    RPi acts as server, Android connects as client
    """
    
    # Standard UUID for Serial Port Profile (SPP)
    UUID = "00001101-0000-1000-8000-00805F9B34FB"
    
    def __init__(self, port: int = 1):
        """
        Initialize Bluetooth handler
        
        Args:
            port: RFCOMM channel (default 1)
        """
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.client_address = None
        self.connected = False
        
    def connect(self) -> bool:
        """
        Start Bluetooth server and wait for Android connection
        
        Returns:
            True if connected successfully
        """
        try:
            # Import bluetooth here to avoid issues if not on RPi
            import bluetooth
            
            self.server_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            self.server_socket.bind(("", self.port))
            self.server_socket.listen(1)
            
            # Advertise the service
            bluetooth.advertise_service(
                self.server_socket,
                "MDP-Group8-RPi",
                service_id=self.UUID,
                service_classes=[self.UUID, bluetooth.SERIAL_PORT_CLASS],
                profiles=[bluetooth.SERIAL_PORT_PROFILE]
            )
            
            print(f"[Bluetooth] Waiting for connection on RFCOMM channel {self.port}...")
            
            self.client_socket, self.client_address = self.server_socket.accept()
            self.connected = True
            print(f"[Bluetooth] Connected to {self.client_address}")
            return True
            
        except ImportError:
            print("[Bluetooth] PyBluez not installed. Install with: sudo apt-get install python3-bluez")
            return False
        except Exception as e:
            print(f"[Bluetooth] Connection error: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Close Bluetooth connection"""
        try:
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
            self.connected = False
            self.client_address = None
            print("[Bluetooth] Disconnected")
        except Exception as e:
            print(f"[Bluetooth] Disconnect error: {e}")
    
    def send(self, message: str) -> bool:
        """
        Send message to Android
        
        Args:
            message: String message to send
            
        Returns:
            True if sent successfully
        """
        if not self.connected or not self.client_socket:
            print("[Bluetooth] Not connected")
            return False
            
        try:
            self.client_socket.send(message.encode("utf-8"))
            print(f"[Bluetooth] Sent: {message}")
            return True
        except Exception as e:
            print(f"[Bluetooth] Send error: {e}")
            self.connected = False
            return False
    
    def receive(self, buffer_size: int = 1024) -> Optional[str]:
        """
        Receive message from Android (blocking)
        
        Args:
            buffer_size: Max bytes to receive
            
        Returns:
            Received message string, or None on error
        """
        if not self.connected or not self.client_socket:
            return None
            
        try:
            data = self.client_socket.recv(buffer_size)
            if data:
                message = data.decode("utf-8").strip()
                print(f"[Bluetooth] Received: {message}")
                return message
            return None
        except Exception as e:
            print(f"[Bluetooth] Receive error: {e}")
            self.connected = False
            return None
    
    def receive_nonblocking(self, timeout: float = 0.1) -> Optional[str]:
        """
        Non-blocking receive with timeout
        
        Args:
            timeout: Socket timeout in seconds
            
        Returns:
            Received message or None if no data
        """
        if not self.connected or not self.client_socket:
            return None
            
        try:
            self.client_socket.settimeout(timeout)
            data = self.client_socket.recv(1024)
            self.client_socket.settimeout(None)
            if data:
                message = data.decode("utf-8").strip()
                print(f"[Bluetooth] Received: {message}")
                return message
            return None
        except socket.timeout:
            return None
        except Exception as e:
            print(f"[Bluetooth] Receive error: {e}")
            self.connected = False
            return None
    
    def is_connected(self) -> bool:
        """Check if Bluetooth is connected"""
        return self.connected
