"""
Task 1 RPi Implementation
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


class Task1RPI:
    def __init__(self, config: Config):
        self.config = config
        self.pc = PC()
        
        # Thread related
        self.pc_receive_thread = None
        self.stream_thread = None
        
        # Store last received image ID (can be extended as needed)
        self.last_image = None

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
                    # ========== Handle NONE message here ==========
                    # Example: notify other modules that no image detected
                    # ==============================================
                    
                elif "," in message_rcv:
                    # Recognition result format: "obstacle_id,confidence,image_id"
                    msg_split = message_rcv.split(",")
                    if len(msg_split) == 3:
                        obstacle_id, conf_str, object_id = msg_split
                        confidence_level = None
                        
                        try:
                            confidence_level = float(conf_str)
                        except ValueError:
                            confidence_level = None
                        
                        print(f"OBJECT ID: {object_id}, Confidence: {confidence_level}")
                        self.last_image = object_id
                        
                        # ========== Handle recognition result here ==========
                        # Example: send to Android or other modules
                        # self.android.send(f"TARGET,{obstacle_id},{object_id}")
                        # ================================================
                
                elif "DETECT" in message_rcv:
                    # Command format: "DETECT,obstacle_id"
                    obstacle_id = message_rcv.split(",")[1]
                    print(f"Received DETECT command for obstacle {obstacle_id}")
                    # ========== Handle DETECT command here ==========
                    # Example: record timestamp, prepare to match image
                    # ===============================================
                
                elif "PERFORM STITCHING" in message_rcv:
                    # Command format: "PERFORM STITCHING,num"
                    num = int(message_rcv.split(",")[1])
                    print(f"Received STITCHING command for {num} images")
                    # ========== Handle stitching command here ==========
                    # Example: notify PC to start stitching
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

