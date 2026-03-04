"""
Task 2 RPi Implementation
Contains only image recognition related communication parts
"""
import sys
import threading
import time
from pathlib import Path

# Add project path
sys.path.insert(0, str(Path(__file__).parent.parent))

from camera.stream_server import StreamServer
from communication.pc import PC
from config.config import Config


class Task2RPI:
    def __init__(self, config: Config):
        self.config = config
        self.pc = PC()
        
        # Thread related
        self.pc_receive_thread = None
        self.stream_thread = None
        
        # Task2 specific variables
        self.last_image = None
        self.prev_image = None
        self.obstacle_id = 1
        
        # Left and right arrow IDs (adjust according to your model)
        self.LEFT_ARROW_ID = "39"
        self.RIGHT_ARROW_ID = "38"

    def initialize(self):
        """
        Initialize connections and start threads
        """
        try:
            # Start video stream server first
            print("Starting stream server...")
            self.stream_thread = threading.Thread(target=self.stream_start)
            self.stream_thread.start()
            time.sleep(0.1)
            
            # Connect to PC (TCP server)
            self.pc.connect()
            
            # Start thread to receive messages from PC
            self.pc_receive_thread = threading.Thread(target=self.pc_receive)
            self.pc_receive_thread.start()
            
            print("Task2 RPi initialized successfully")
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
        1. Recognition result: "confidence,image_id"
        2. Commands: "SEEN" or "STITCH"
        """
        print("PC receive thread started")
        while True:
            try:
                message_rcv = self.pc.receive()
                print(f"Received from PC: {message_rcv}")
                
                if "NONE" in message_rcv:
                    self.last_image = "NONE"
                    # ========== Handle NONE message here ==========
                    # ==============================================
                    
                elif "," in message_rcv:
                    # Recognition result format: "confidence,image_id"
                    msg_split = message_rcv.split(",")
                    if len(msg_split) == 2:
                        conf_str, object_id = msg_split
                        confidence_level = None
                        
                        try:
                            confidence_level = float(conf_str)
                        except ValueError:
                            confidence_level = None
                        
                        print(f"OBJECT ID: {object_id}, Confidence: {confidence_level}")
                        
                        # ========== Handle recognition result here ==========
                        # Example: determine if it's left or right arrow
                        if object_id == self.LEFT_ARROW_ID:
                            print("Detected LEFT arrow")
                        elif object_id == self.RIGHT_ARROW_ID:
                            print("Detected RIGHT arrow")
                        # ================================================
                        
                        if self.prev_image is None:
                            self.prev_image = object_id
                            self.last_image = object_id
                        elif self.prev_image != object_id:
                            self.prev_image = object_id
                            self.last_image = object_id
                
                elif "SEEN" in message_rcv:
                    # Command: "SEEN" - indicates arrow has been seen
                    print("Received SEEN command")
                    self.obstacle_id += 1
                    self.prev_image = None
                    # ========== Handle SEEN command here ==========
                    # ============================================
                
                elif "STITCH" in message_rcv:
                    # Command: "STITCH" - start stitching
                    print("Received STITCH command")
                    # ========== Handle stitching command here ==========
                    # ================================================

            except OSError as e:
                print(f"Error in receiving data: {e}")
                break

    def get_last_image(self) -> str:
        """Get last received image ID"""
        return self.last_image

    def stop(self):
        """Stop all threads and connections"""
        try:
            self.pc.disconnect()
            print("Task2 RPi stopped")
        except Exception as e:
            print(f"Error stopping Task2 RPi: {e}")


def main(config: Config):
    """
    Task2 main function
    """
    print("# ------------- Running Task 2, RPi ---------------- #")
    print(f"You are {'out' if config.is_outdoors else 'in'}doors.")
    task2 = Task2RPI(config)
    task2.initialize()
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        task2.stop()
