"""
Task 1 RPi Implementation
Contains image recognition + STM32 movement control
"""
import sys
import threading
import time
from pathlib import Path
from queue import Queue, Empty

# Add project path
sys.path.insert(0, str(Path(__file__).parent.parent))

from camera.stream_server import StreamServer
from communication.pc import PC
from communication.stm32 import STM32
from config.config import Config


class Task1RPI:
    # ========== Movement Mode ==========
    # "hardcoded" - Use IMAGE_COMMANDS mapping (for simple tasks)
    # "algorithm" - Use path from Algorithm (for path planning tasks)
    # ===================================
    
    # ========== Image ID to STM32 Command Mapping ==========
    # Only used when mode = "hardcoded"
    # Modify these based on your model's class names
    IMAGE_COMMANDS = {
        "38": "TR090",   # Right arrow → turn right 90°
        "39": "TL090",   # Left arrow → turn left 90°
        "bullseye": "STOP",  # Bullseye → stop
        # Add more mappings as needed
        # "bullseye": None,  # No movement for bullseye
        # "1": None,         # No movement for number 1
    }
    # =======================================================
    
    def __init__(self, config: Config, mode: str = "hardcoded"):
        """
        Initialize Task1 RPi
        
        Args:
            config: Configuration object
            mode: "hardcoded" or "algorithm"
                  - hardcoded: Use IMAGE_COMMANDS dict for movements
                  - algorithm: Wait for path commands from Algorithm
        """
        self.config = config
        self.mode = mode  # "hardcoded" or "algorithm"
        self.pc = PC()
        self.stm32 = STM32()
        
        # Thread related
        self.pc_receive_thread = None
        self.stream_thread = None
        self.path_thread = None
        
        # Store last received image ID
        self.last_image = None
        
        # Path execution
        self.path_queue = Queue()  # Queue of waypoints from Algorithm
        self.executing_path = False
        self.current_obstacle_id = None
        
        # Callbacks for external communication (e.g., Bluetooth to Android)
        self.on_image_detected = None  # Callback: on_image_detected(obstacle_id, image_id, confidence)

    def initialize(self):
        """
        Initialize connections and start threads
        """
        try:
            # Connect to STM32
            print("Connecting to STM32...")
            if not self.stm32.connect():
                print("[WARNING] STM32 not connected - movements disabled")
            
            # Start video stream server first
            print("Starting stream server...")
            self.stream_thread = threading.Thread(target=self.stream_start, daemon=True)
            self.stream_thread.start()
            time.sleep(0.1)
            
            # Connect to PC (TCP server)
            self.pc.connect()
            
            # Start thread to receive messages from PC
            self.pc_receive_thread = threading.Thread(target=self.pc_receive, daemon=True)
            self.pc_receive_thread.start()
            
            print("Task1 RPi initialized successfully")
        except Exception as e:
            print(f"Initialization failed: {e}")

    def stream_start(self):
        """
        Start UDP video stream server
        """
        StreamServer().start(
            framerate=15, 
            quality=45, 
            is_outdoors=self.config.is_outdoors
        )

    def pc_receive(self) -> None:
        """
        Receive recognition results and commands from PC
        
        Message formats:
        1. Recognition result: "obstacle_id,confidence,image_id"
        2. Commands: "DETECT,obstacle_id" or "PERFORM STITCHING,num"
        """
        print("PC receive thread started")
        while True:
            try:
                message_rcv = self.pc.receive()
                print(f"Received from PC: {message_rcv}")
                
                if "NONE" in message_rcv:
                    self.last_image = "NONE"
                    
                elif "," in message_rcv:
                    # Recognition result format: "obstacle_id,confidence,image_id"
                    msg_split = message_rcv.split(",")
                    if len(msg_split) == 3:
                        obstacle_id, conf_str, image_id = msg_split
                        confidence_level = None
                        
                        try:
                            confidence_level = float(conf_str)
                        except ValueError:
                            confidence_level = None
                        
                        print(f"DETECTED: Image {image_id} for obstacle {obstacle_id} (conf: {confidence_level})")
                        self.last_image = image_id
                        
                        # ========== Handle Image Detection ==========
                        self.handle_image_detected(obstacle_id, image_id, confidence_level)
                        # ============================================
                
                elif "DETECT" in message_rcv:
                    obstacle_id = message_rcv.split(",")[1]
                    print(f"Received DETECT command for obstacle {obstacle_id}")
                    self.current_obstacle_id = obstacle_id
                
                elif "PERFORM STITCHING" in message_rcv:
                    num = int(message_rcv.split(",")[1])
                    print(f"Received STITCHING command for {num} images")

            except OSError as e:
                print(f"Error in receiving data: {e}")
                break
    
    def handle_image_detected(self, obstacle_id: str, image_id: str, confidence: float):
        """
        Handle detected image - execute movement if needed
        
        Args:
            obstacle_id: The obstacle being observed
            image_id: Detected image class
            confidence: Detection confidence
        """
        # Notify external listeners (e.g., send to Android via Bluetooth)
        if self.on_image_detected:
            self.on_image_detected(obstacle_id, image_id, confidence)
        
        # ========== Mode-based behavior ==========
        if self.mode == "hardcoded":
            # Hardcoded mode: Check IMAGE_COMMANDS dict
            if image_id in self.IMAGE_COMMANDS:
                command = self.IMAGE_COMMANDS[image_id]
                if command:
                    print(f"[STM32] Image {image_id} triggers command: {command}")
                    self.stm32.send(command)
                    response = self.stm32.receive(timeout=5.0)
                    if response:
                        print(f"[STM32] Response: {response}")
            else:
                print(f"[INFO] Image {image_id} has no hardcoded command")
                
        elif self.mode == "algorithm":
            # Algorithm mode: Just report detection, path executor handles movement
            print(f"[Algorithm Mode] Detected {image_id} - waiting for path command")
            # The path executor will handle the next movement
        # =========================================
    
    def execute_path(self, path: list):
        """
        Execute a path from the Algorithm
        
        Args:
            path: List of waypoints from Algorithm
                  [{'x': 10, 'y': 20, 'd': 0, 's': 1}, ...]
                  s >= 0 means take screenshot for obstacle s
        """
        self.executing_path = True
        print(f"[Path] Starting path execution with {len(path)} waypoints")
        
        for i, waypoint in enumerate(path):
            if not self.executing_path:
                print("[Path] Execution stopped")
                break
            
            x, y = waypoint['x'], waypoint['y']
            direction = waypoint['d']
            screenshot_obstacle = waypoint.get('s', -1)
            
            print(f"[Path] Waypoint {i+1}/{len(path)}: ({x}, {y}) dir={direction}")
            
            # ========== Convert waypoint to STM32 commands ==========
            # This is simplified - you'll need path-to-command conversion
            # based on current position and target position
            # Example: self.move_to(x, y, direction)
            # ========================================================
            
            # If this waypoint requires a screenshot (obstacle detection)
            if screenshot_obstacle >= 0:
                print(f"[Path] Detecting obstacle {screenshot_obstacle}...")
                self.current_obstacle_id = screenshot_obstacle
                
                # Request image detection from PC
                self.pc.send(f"DETECT,{screenshot_obstacle}")
                
                # Wait for detection result (handled in pc_receive)
                time.sleep(2)  # Allow time for detection
        
        self.executing_path = False
        print("[Path] Path execution complete")
    
    def add_path(self, path: list):
        """Add path to execution queue"""
        for waypoint in path:
            self.path_queue.put(waypoint)
    
    def move_forward(self, distance_cm: int = 10):
        """Move robot forward"""
        self.stm32.forward(distance_cm)
    
    def move_backward(self, distance_cm: int = 10):
        """Move robot backward"""
        self.stm32.backward(distance_cm)
    
    def turn_left(self, angle: int = 90):
        """Turn robot left"""
        self.stm32.turn_left(angle)
    
    def turn_right(self, angle: int = 90):
        """Turn robot right"""
        self.stm32.turn_right(angle)

    def get_last_image(self) -> str:
        """Get last received image ID"""
        return self.last_image

    def stop(self):
        """Stop all threads and connections"""
        self.executing_path = False
        try:
            self.stm32.stop()  # Emergency stop
            self.stm32.disconnect()
            self.pc.disconnect()
            print("Task1 RPi stopped")
        except Exception as e:
            print(f"Error stopping Task1 RPi: {e}")


def main(config: Config):
    """
    Task1 main function
    """
    print("# ------------- Running Task 1, RPi ---------------- #")
    print(f"You are {'out' if config.is_outdoors else 'in'}doors.")
    task1 = Task1RPI(config)
    task1.initialize()
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        task1.stop()
