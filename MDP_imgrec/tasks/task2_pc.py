"""
Task 2 PC-side code
Receives video stream, performs YOLO recognition, sends results back to RPi
"""
import socket
import sys
import threading
from pathlib import Path

# Add project path
sys.path.insert(0, str(Path(__file__).parent.parent))

from camera.stream_listener import StreamListener
from communication.pc_client import PCClient
from stitching.stitching import stitch_images, add_to_stitching_dict
from config.config import Config


class Task2PC:
    def __init__(self, config: Config):
        self.config = config
        
        self.exit = False
        self.pc_receive_thread = None
        self.stream_thread = None

        # ========== Modify as needed: set your RPi IP address ==========
        self.host = "192.168.8.1"
        # ================================================
        self.port = 5000
        self.pc_client = None
        
        print(f"! -- initialising weights file: {config.task2_weights}....")
        self.stream_listener = StreamListener(config.task2_weights)

        # Task2-specific variables
        self.stitching_arr = []
        self.stitching_dict = {}
        self.filename = "task2"  # ========== Stitching output file prefix ==========

        self.obstacle_id = 1
        self.obstacle_img_id = None

        # ========== Modify as needed: adjust left/right arrow IDs for your model ==========
        self.LEFT_ARROW_ID = "39"
        self.RIGHT_ARROW_ID = "38"
        # =====================================================

    def start(self):
        """Start all threads"""
        self.pc_client = PCClient(self.host, self.port)
        self.pc_client.connect()
        
        self.pc_receive_thread = threading.Thread(target=self.pc_receive)
        self.stream_thread = threading.Thread(target=self.stream_start)
        self.pc_receive_thread.start()  # Receive commands from RPi
        self.stream_thread.start()  # Start video stream recognition

    def stream_start(self):
        """Start video stream recognition"""
        self.stream_listener.start_stream_read(
            self.on_result, 
            self.on_disconnect, 
            conf_threshold=0.65,  # ========== Adjust confidence threshold as needed ==========
            show_video=True  # ========== Display video window and recognition results ==========
        )

    def on_result(self, result, frame):
        """
        Recognition result callback
        
        Args:
            result: YOLO recognition result
            frame: Image frame
        """
        message_content = None

        if result is not None:
            conf_level = result.boxes[0].conf.item()
            img_id = result.names[int(result.boxes[0].cls[0].item())]

            # Only process left/right arrows
            if img_id not in [self.LEFT_ARROW_ID, self.RIGHT_ARROW_ID]:
                print(f"Detected invalid image {img_id}, skipping...")
                return
            
            if self.obstacle_img_id is None:
                # First arrow detected, send result
                message_content = f"{conf_level},{img_id}"
                self.obstacle_img_id = img_id
            
            # Add to stitching dict
            if img_id == self.obstacle_img_id:
                add_to_stitching_dict(
                    self.stitching_dict, 
                    self.obstacle_id, 
                    conf_level, 
                    frame
                )

        if message_content is not None:
            print("Sending:", message_content)
            self.pc_client.send(message_content)

    def on_disconnect(self):
        """Video stream disconnect callback"""
        print("Stream disconnected, disconnect.")
        self.disconnect()

    def disconnect(self):
        """Disconnect"""
        try:
            self.exit = True
            if self.pc_client:
                self.pc_client.disconnect()
            print("Disconnected from RPi successfully")
        except Exception as e:
            print(f"Failed to disconnect from RPi: {e}")

    def pc_receive(self) -> None:
        """
        Receive commands from RPi
        
        Command formats:
        1. "SEEN" - Arrow seen, ready for next
        2. "STITCH" - Request image stitching
        """
        print("PC Socket connection started successfully")
        while not self.exit:
            try:
                message_rcv = self.pc_client.receive()
                if not message_rcv:
                    print("RPi connection dropped")
                    break
                print("Message received from RPi:", message_rcv)

                if "SEEN" in message_rcv:
                    # Command: "SEEN" - Arrow seen, ready for next
                    self.obstacle_id += 1
                    self.obstacle_img_id = None
                    print(f"Obstacle ID incremented to {self.obstacle_id}")

                elif "STITCH" in message_rcv:
                    # Command: "STITCH" - Start stitching
                    # ========== Note: Assumes stitching obstacle_id 1 and 2 ==========
                    stitch_images(
                        [1, 2], 
                        self.stitching_dict, 
                        filename=self.filename
                    )
                    # =====================================================
            except OSError as e:
                print("Error in receiving data:", e)
                break


def main(config: Config):
    """
    Task2 main function
    """
    print("# ------------- Running Task 2, PC ---------------- #")
    print(f"You are {'out' if config.is_outdoors else 'in'}doors.")
    pcMain = Task2PC(config)
    pcMain.start()
    
    # Keep running
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        pcMain.disconnect()
