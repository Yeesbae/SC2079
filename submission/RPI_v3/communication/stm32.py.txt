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
        
        NOTE: Opening the serial port may toggle DTR, causing STM32 to reset.
        After connection, there may be a delay before STM32 is ready.
        If other blocking operations follow (e.g., waiting for PC connection),
        use flush_input() and sync() to re-establish clean communication.
        
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
    
    def flush_input(self) -> int:
        """
        Clear any accumulated data in the serial receive buffer.
        
        Call this after any blocking operation (e.g., waiting for network connections)
        to clear stale heartbeats or other accumulated data from STM32.
        
        Returns:
            Number of bytes cleared
        """
        if not self.connected or not self.serial:
            return 0
        
        try:
            bytes_waiting = self.serial.in_waiting
            if bytes_waiting > 0:
                self.serial.read(bytes_waiting)
                print(f"[STM32] Flushed {bytes_waiting} bytes from input buffer")
            return bytes_waiting
        except Exception as e:
            print(f"[STM32] Flush error: {e}")
            return 0
    
    def sync(self, timeout: float = 3.0) -> bool:
        """
        Verify STM32 is responsive by sending a no-op command.
        
        Use this after long blocking operations to ensure STM32 hasn't
        hung due to TX buffer overflow (from accumulated heartbeats).
        
        Returns:
            True if STM32 responded with ACK
        """
        if not self.connected:
            return False
        
        # Clear buffer first
        self.flush_input()
        time.sleep(0.1)
        self.flush_input()
        
        # Send no-op command (forward 0cm)
        if self.send("SF000"):
            response = self.receive(timeout=timeout)
            if response and 'A' in response:
                print(f"[STM32] Sync OK")
                return True
        
        print(f"[STM32] Sync failed - no ACK (may need manual reset)")
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
        
        All commands are padded/truncated to exactly 5 bytes with null (\0).
        e.g. "STRT" → b'STRT\x00', "SF050" → b'SF050'
        
        Args:
            command: Command string (e.g., "SF050", "STRT", "LEFT", "RGHT")
            
        Returns:
            True if sent successfully
        """
        if not self.connected or not self.serial:
            print("[STM32] Not connected")
            return False
        
        try:
            command = command.strip().upper()
            raw = command.encode('utf-8')
            
            # Pad or truncate to exactly 5 bytes
            if len(raw) < 5:
                raw = raw + b'\x00' * (5 - len(raw))
            elif len(raw) > 5:
                raw = raw[:5]
            
            self.serial.write(raw)
            self.serial.flush()
            print(f"[STM32] Sent: {command} ({raw!r})")
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
            Response string containing 'A' if ACK received, or None on timeout/error.
            Heartbeat ("HB") messages from STM32 are filtered out.
        """
        if not self.connected or not self.serial:
            return None
        
        try:
            # Wait for acknowledgment (single 'A' byte)
            # NOTE: Do NOT call reset_input_buffer() here - STM32 may have already
            # sent the ACK before we enter receive(), clearing it would lose the ACK.
            start_time = time.time()
            response = ""
            
            while time.time() - start_time < timeout:
                if self.serial.in_waiting > 0:
                    data = self.serial.read(self.serial.in_waiting)
                    response += data.decode('utf-8', errors='ignore')
                    
                    # Check if we received the actual acknowledgment ('A')
                    # Ignore heartbeat ("HB") messages from STM32
                    if 'A' in response:
                        # Strip out HB tokens for a clean response
                        clean = response.replace("HB", "").strip()
                        print(f"[STM32] Received ACK: {clean}")
                        return clean if clean else "A"
                
                time.sleep(0.01)
            
            # Timeout - only return if we got a real ACK, ignore heartbeats
            if response:
                stripped = response.replace("HB", "").strip()
                if 'A' in stripped:
                    print(f"[STM32] Received ACK (late): {stripped}")
                    return stripped
                else:
                    print(f"[STM32] Timeout - only heartbeats received, no ACK")
                    return None
            print(f"[STM32] Timeout - no response")
            return None
        except Exception as e:
            print(f"[STM32] Receive error: {e}")
            return None

    def receive_task2_message(self, timeout: float = 30.0) -> Optional[str]:
        """
        Receive a Task 2 message from STM32.

        Recognized single-character messages from STM32:
            I  → returns "IMG"   (image request)
            B  → returns "BULL"  (bull's-eye request)
            F  → returns "FIN"   (task complete)

        Heartbeat ("HB") messages are filtered out.

        Args:
            timeout: Read timeout in seconds

        Returns:
            Message keyword ("IMG", "BULL", "FIN") or None on timeout.
        """
        if not self.connected or not self.serial:
            return None

        try:
            start_time = time.time()
            buffer = ""

            while time.time() - start_time < timeout:
                if self.serial.in_waiting > 0:
                    data = self.serial.read(self.serial.in_waiting)
                    buffer += data.decode('utf-8', errors='ignore')

                    # Strip heartbeats FIRST so "HB" doesn't false-match "B"/"F"
                    buffer = buffer.replace("HB", "")
                    # Keep buffer from growing indefinitely
                    if len(buffer) > 200:
                        buffer = buffer[-50:]

                    # Check for Task 2 single-character messages
                    if "I" in buffer:
                        print(f"[STM32] Received: I (take photo)")
                        return "IMG"
                    if "B" in buffer:
                        print(f"[STM32] Received: B (confirm bull's-eye)")
                        return "BULL"
                    if "F" in buffer:
                        print(f"[STM32] Received: F (task complete)")
                        return "FIN"

                time.sleep(0.01)

            if buffer.replace("HB", "").strip():
                print(f"[STM32] Timeout - unrecognized data in buffer: {buffer[:80]}")
            else:
                print(f"[STM32] Timeout - no Task 2 message")
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
        return self.send(f"SF{distance_cm:03d}")
    
    def backward(self, distance_cm: int = 10) -> bool:
        """Move backward"""
        return self.send(f"SB{distance_cm:03d}")
    
    def turn_left(self, angle: int = 90) -> bool:
        """Turn left forward"""
        return self.send(f"LF{angle:03d}")
    
    def turn_right(self, angle: int = 90) -> bool:
        """Turn right forward"""
        return self.send(f"RF{angle:03d}")
    
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
            "38": "RF090",   # Right arrow → turn right 90°
            "39": "LF090",   # Left arrow → turn left 90°
            
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
