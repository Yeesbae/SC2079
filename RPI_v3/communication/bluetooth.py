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
        self.server_initialized = False
    
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
    
    def _try_bind(self, bluetooth_module) -> bool:
        """
        Bind to any available RFCOMM port using PORT_ANY
        
        Returns:
            True if bind successful
        """
        try:
            self.server_socket = bluetooth_module.BluetoothSocket(bluetooth_module.RFCOMM)
            self.server_socket.bind(("", bluetooth_module.PORT_ANY))
            self.server_socket.listen(1)
            self.port = self.server_socket.getsockname()[1]
            return True
        except OSError as e:
            if self.server_socket:
                try:
                    self.server_socket.close()
                except:
                    pass
                self.server_socket = None
            return False
        
    def wait_for_client(self) -> bool:
        """
        Wait for a new client connection on existing server socket
        Used for reconnections without recreating the server
        
        Returns:
            True if client connected successfully
        """
        if not self.server_socket:
            return False
            
        try:
            import bluetooth
            
            # Close old client socket if exists
            if self.client_socket:
                try:
                    self.client_socket.close()
                except:
                    pass
                self.client_socket = None
            
            print(f"[Bluetooth] Waiting for client reconnection on channel {self.port}...")
            self.server_socket.settimeout(300)  # 5 minute timeout
            self.client_socket, self.client_address = self.server_socket.accept()
            self.server_socket.settimeout(None)
            self.connected = True
            print(f"[Bluetooth] ✓ Client reconnected: {self.client_address}")
            return True
            
        except socket.timeout:
            print("[Bluetooth] ✗ Reconnection timeout")
            self.connected = False
            return False
        except Exception as e:
            print(f"[Bluetooth] ✗ Reconnection error: {e}")
            self.connected = False
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
            
            # If server already initialized, just wait for new client
            if self.server_initialized and self.server_socket:
                return self.wait_for_client()
            
            # Clean up any existing sockets first
            self.disconnect(keep_server=False)
            
            # Try to release any stuck RFCOMM ports first
            self._release_rfcomm_ports()
            
            # Use PORT_ANY — let the system assign a free channel
            if not self._try_bind(bluetooth):
                print("[Bluetooth] ✗ Failed to bind to any RFCOMM channel!")
                print("[Bluetooth] Try running: sudo rfcomm release all && sudo systemctl restart bluetooth")
                return False
            print(f"[Bluetooth] ✓ Bound to RFCOMM channel {self.port}")
            
            # Get local Bluetooth address (best-effort — fails on some kernels)
            try:
                local_bt_addr = bluetooth.read_local_bdaddr()[0]
                print(f"[Bluetooth] RPi Bluetooth Address: {local_bt_addr}")
            except Exception:
                pass
            
            # Advertise the service (best-effort — fails if /var/run/sdp is not accessible)
            try:
                print(f"[Bluetooth] Advertising service 'MDP-Group8-RPi' with UUID {self.UUID}...")
                bluetooth.advertise_service(
                    self.server_socket,
                    "MDP-Group8-RPi",
                    service_id=self.UUID,
                    service_classes=[self.UUID, bluetooth.SERIAL_PORT_CLASS],
                    profiles=[bluetooth.SERIAL_PORT_PROFILE]
                )
                print("[Bluetooth] Service advertised via SDP.")
            except Exception as adv_err:
                print(f"[Bluetooth] ⚠ SDP advertise skipped ({adv_err})")
                print(f"[Bluetooth]   Connect manually to MAC + channel {self.port}")
                print(f"[Bluetooth]   Fix: sudo chmod 777 /var/run/sdp")

            print(f"[Bluetooth] Waiting for RFCOMM connection on channel {self.port}...")
            print(f"[Bluetooth] Android/PC should connect to UUID: {self.UUID}")
            
            # Set a timeout for debugging
            self.server_socket.settimeout(300)  # 5 minute timeout
            
            self.client_socket, self.client_address = self.server_socket.accept()
            self.server_socket.settimeout(None)  # Remove timeout after connection
            self.connected = True
            self.server_initialized = True
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
    
    def disconnect(self, keep_server: bool = True):
        """Close Bluetooth connection and optionally clean up server
        
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
                    import bluetooth
                    bluetooth.stop_advertising(self.server_socket)
                except:
                    pass
                try:
                    self.server_socket.close()
                except:
                    pass
                self.server_socket = None
                self.server_initialized = False
            
            self.client_address = None
            if keep_server:
                print("[Bluetooth] Client disconnected (server still listening)")
            else:
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
            # Add newline if not present (Android apps typically expect this)
            if not message.endswith('\n'):
                message = message + '\n'
            self.client_socket.send(message.encode("utf-8"))
            print(f"[Bluetooth] Sent: {message.strip()}")
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
        except (socket.timeout, TimeoutError):
            return None
        except OSError as e:
            if e.errno in (11, 110) or "timed out" in str(e):
                return None
            print(f"[Bluetooth] Receive error: {e}")
            self.connected = False
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
            else:
                # Empty data means client disconnected
                print("[Bluetooth] Client disconnected (recv returned empty)")
                self.connected = False
                return None
        except (socket.timeout, TimeoutError):
            self.client_socket.settimeout(None)
            return None
        except OSError as e:
            self.client_socket.settimeout(None)
            # EAGAIN (11) / ETIMEDOUT (110) / "timed out" are normal timeout signals on RFCOMM
            if e.errno in (11, 110) or "timed out" in str(e):
                return None
            print(f"[Bluetooth] Receive error: {e}")
            self.connected = False
            return None
        except Exception as e:
            print(f"[Bluetooth] Receive error: {e}")
            self.connected = False
            try:
                self.client_socket.settimeout(None)
            except:
                pass
            return None
    
    def is_connected(self) -> bool:
        """Check if Bluetooth is connected"""
        return self.connected
