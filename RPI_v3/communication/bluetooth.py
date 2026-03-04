"""
Bluetooth RFCOMM handler for Android communication
Uses PyBluez for Bluetooth serial communication
"""
import socket
import subprocess
import time
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
            port: RFCOMM channel (default 1, some devices use 2)
        """
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.client_address = None
        self.connected = False
    
    def _release_rfcomm_ports(self):
        """Release any stuck RFCOMM ports"""
        try:
            print("[Bluetooth] Releasing stuck RFCOMM ports...")
            subprocess.run(['sudo', 'rfcomm', 'release', 'all'], 
                         capture_output=True, timeout=5)
            subprocess.run(['sudo', 'killall', 'rfcomm'], 
                         capture_output=True, timeout=5)
            time.sleep(0.5)
        except Exception as e:
            print(f"[Bluetooth] Note: Could not release ports: {e}")
    
    def _try_bind(self, bluetooth_module, port: int) -> bool:
        """
        Try to bind to a specific RFCOMM port
        
        Returns:
            True if bind successful
        """
        try:
            self.server_socket = bluetooth_module.BluetoothSocket(bluetooth_module.RFCOMM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(("", port))
            self.server_socket.listen(1)
            self.port = port
            return True
        except OSError as e:
            if self.server_socket:
                try:
                    self.server_socket.close()
                except:
                    pass
                self.server_socket = None
            return False
        
    def connect(self) -> bool:
        """
        Start Bluetooth server and wait for Android connection
        
        Returns:
            True if connected successfully
        """
        try:
            # Import bluetooth here to avoid issues if not on RPi
            import bluetooth
            
            # Clean up any existing sockets first
            self.disconnect()
            
            # Try to release any stuck RFCOMM ports first
            self._release_rfcomm_ports()
            
            # Try multiple RFCOMM channels (1, 2, 3, 4, 5)
            ports_to_try = [self.port] + [p for p in [1, 2, 3, 4, 5] if p != self.port]
            bound = False
            
            for port in ports_to_try:
                print(f"[Bluetooth] Trying RFCOMM channel {port}...")
                if self._try_bind(bluetooth, port):
                    print(f"[Bluetooth] ✓ Bound to RFCOMM channel {port}")
                    bound = True
                    break
                else:
                    print(f"[Bluetooth] ✗ Channel {port} unavailable")
            
            if not bound:
                print("[Bluetooth] ✗ All RFCOMM channels failed!")
                print("[Bluetooth] Try running: sudo rfcomm release all && sudo systemctl restart bluetooth")
                return False
            
            # Get local Bluetooth address
            local_bt_addr = bluetooth.read_local_bdaddr()[0]
            print(f"[Bluetooth] RPi Bluetooth Address: {local_bt_addr}")
            
            # Advertise the service
            print(f"[Bluetooth] Advertising service 'MDP-Group8-RPi' with UUID {self.UUID}...")
            bluetooth.advertise_service(
                self.server_socket,
                "MDP-Group8-RPi",
                service_id=self.UUID,
                service_classes=[self.UUID, bluetooth.SERIAL_PORT_CLASS],
                profiles=[bluetooth.SERIAL_PORT_PROFILE]
            )
            
            print(f"[Bluetooth] Service advertised. Waiting for RFCOMM connection on channel {self.port}...")
            print(f"[Bluetooth] Android app should now connect to UUID: {self.UUID}")
            
            # Set a timeout for debugging
            self.server_socket.settimeout(300)  # 5 minute timeout
            
            self.client_socket, self.client_address = self.server_socket.accept()
            self.server_socket.settimeout(None)  # Remove timeout after connection
            self.connected = True
            print(f"[Bluetooth] ✓ Connected to {self.client_address}")
            return True
            
        except ImportError:
            print("[Bluetooth] ✗ PyBluez not installed. Install with: sudo apt-get install python3-bluez")
            return False
        except socket.timeout:
            print("[Bluetooth] ✗ Connection timeout - no Android client connected within 5 minutes")
            print("[Bluetooth] Troubleshooting steps:")
            print("  1. Ensure Android app is running and trying to connect")
            print(f"  2. Verify Android is connecting to UUID: {self.UUID}")
            print("  3. Check 'bluetoothctl' and run: trust <ANDROID_MAC>")
            print("  4. Run: sudo rfcomm release all")
            self.disconnect()
            return False
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"[Bluetooth] ✗ Port {self.port} already in use")
                print("  Fix: sudo rfcomm release all")
                print("  Or try: sudo killall rfcomm")
            else:
                print(f"[Bluetooth] ✗ OSError: {e}")
            self.disconnect()
            return False
        except Exception as e:
            print(f"[Bluetooth] ✗ Connection error: {e}")
            import traceback
            traceback.print_exc()
            self.connected = False
            self.disconnect()
            return False
    
    def disconnect(self):
        """Close Bluetooth connection and clean up for reconnection"""
        try:
            self.connected = False
            if self.client_socket:
                try:
                    self.client_socket.close()
                except:
                    pass
                self.client_socket = None
            if self.server_socket:
                try:
                    self.server_socket.close()
                except:
                    pass
                self.server_socket = None
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
