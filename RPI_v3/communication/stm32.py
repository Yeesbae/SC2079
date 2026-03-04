"""
STM32 UART Communication Handler
Communicates with STM32 via USB serial for motor control
"""
import serial
import time
from typing import Optional


class STM32:
    """
    Serial communication with STM32 microcontroller
    RPi connects to STM32 via USB serial (/dev/ttyUSB0 or /dev/ttyACM0)
    """
    
    def __init__(self, port: str = "/dev/ttyUSB0", baudrate: int = 115200):
        """
        Initialize STM32 connection
        
        Args:
            port: Serial port (try /dev/ttyUSB0 or /dev/ttyACM0)
            baudrate: Baud rate (must match STM32 config)
        """
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.connected = False
    
    def connect(self) -> bool:
        """
        Open serial connection to STM32
        
        Returns:
            True if connected successfully
        """
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            time.sleep(2)  # Wait for STM32 to reset after connection
            
            # Clear any boot messages
            if self.serial.in_waiting > 0:
                boot_msg = self.serial.read(self.serial.in_waiting)
                print(f"[STM32] Boot message: {boot_msg.decode('utf-8', errors='ignore').strip()}")
            
            self.connected = True
            print(f"[STM32] Connected on {self.port} at {self.baudrate} baud")
            return True
        except serial.SerialException as e:
            print(f"[STM32] Connection failed: {e}")
            print(f"[STM32] Try: ls /dev/tty* to find correct port")
            self.connected = False
            return False
    
    def disconnect(self):
        """Close serial connection"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            self.connected = False
            print("[STM32] Disconnected")
    
    def send(self, command: str) -> bool:
        """
        Send command to STM32
        
        Args:
            command: Command string (e.g., "SF050", "RF090", "LF045")
            
        Returns:
            True if sent successfully
        """
        if not self.connected or not self.serial:
            print("[STM32] Not connected")
            return False
        
        try:
            # Commands should be exactly 5 bytes, no newline
            command = command.strip().upper()
            
            # Send raw bytes without newline
            self.serial.write(command.encode('utf-8'))
            self.serial.flush()
            print(f"[STM32] Sent: {command}")
            return True
        except Exception as e:
            print(f"[STM32] Send error: {e}")
            return False
    
    def receive(self, timeout: float = 1.0) -> Optional[str]:
        """
        Receive response from STM32
        
        Args:
            timeout: Read timeout in seconds
            
        Returns:
            Response string or None
        """
        if not self.connected or not self.serial:
            return None
        
        try:
            # Clear input buffer first
            self.serial.reset_input_buffer()
            
            # Wait for acknowledgment (single 'A' byte)
            start_time = time.time()
            response = ""
            
            while time.time() - start_time < timeout:
                if self.serial.in_waiting > 0:
                    data = self.serial.read(self.serial.in_waiting)
                    response += data.decode('utf-8', errors='ignore')
                    
                    # Check if we received the acknowledgment
                    if 'A' in response:
                        print(f"[STM32] Received: {response.strip()}")
                        return response.strip()
                
                time.sleep(0.01)
            
            # Timeout - return whatever we got
            if response:
                print(f"[STM32] Received (timeout): {response.strip()}")
                return response.strip()
            return None
        except Exception as e:
            print(f"[STM32] Receive error: {e}")
            return None
    
    def send_and_wait(self, command: str, timeout: float = 5.0) -> Optional[str]:
        """
        Send command and wait for acknowledgment
        
        Args:
            command: Command to send
            timeout: How long to wait for response
            
        Returns:
            Response from STM32
        """
        if self.send(command):
            return self.receive(timeout)
        return None
    
    # ========== Movement Commands ==========
    # Adjust these based on your STM32 command protocol
    
    def forward(self, distance_cm: int = 10) -> bool:
        """Move forward"""
        return self.send(f"FW{distance_cm:03d}")
    
    def backward(self, distance_cm: int = 10) -> bool:
        """Move backward"""
        return self.send(f"BW{distance_cm:03d}")
    
    def turn_left(self, angle: int = 90) -> bool:
        """Turn left"""
        return self.send(f"TL{angle:03d}")
    
    def turn_right(self, angle: int = 90) -> bool:
        """Turn right"""
        return self.send(f"TR{angle:03d}")
    
    def stop(self) -> bool:
        """Emergency stop"""
        return self.send("STOP")
    
    # ========== Image Recognition Commands ==========
    
    def execute_for_image(self, image_id: str) -> bool:
        """
        Execute movement based on recognized image
        
        Args:
            image_id: Recognized image ID from YOLO model
            
        Returns:
            True if command sent successfully
        """
        # ========== MODIFY: Map image IDs to STM32 commands ==========
        # These mappings depend on your model's class names
        IMAGE_TO_COMMAND = {
            # Arrow signs
            "38": "TR090",   # Right arrow → turn right 90°
            "39": "TL090",   # Left arrow → turn left 90°
            
            # Number signs (example: stop at numbers)
            "0": "STOP"
            
            # Add more mappings as needed for your model's classes
            # "bullseye": "STOP"
        }
        # =============================================================
        
        command = IMAGE_TO_COMMAND.get(image_id)
        if command:
            print(f"[STM32] Image {image_id} → Command {command}")
            return self.send(command)
        else:
            print(f"[STM32] No command mapped for image: {image_id}")
            return False


# Test the STM32 connection
if __name__ == "__main__":
    print("Testing STM32 connection...")
    print("Make sure STM32 is connected via USB")
    
    # Try common serial ports
    ports_to_try = ["/dev/ttyUSB0", "/dev/ttyACM0", "/dev/ttyAMA0"]
    
    stm = STM32()
    
    for port in ports_to_try:
        stm.port = port
        print(f"\nTrying {port}...")
        if stm.connect():
            break
    
    if not stm.connected:
        print("\nCould not connect. Run 'ls /dev/tty*' to find the correct port.")
        exit(1)
    
    # Test commands
    print("\n--- Testing Commands ---")
    stm.forward(10)
    time.sleep(1)
    stm.stop()
    
    stm.disconnect()
