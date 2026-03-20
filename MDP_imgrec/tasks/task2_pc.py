"""
Task 2 PC-side code
Receives video stream, performs YOLO recognition, sends results back to RPi
"""
import os
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

# Directory for saving detected images
IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'images', 'task_2')
os.makedirs(IMAGES_DIR, exist_ok=True)


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
        self.BULLSEYE_ID = "41"
        # =====================================================

        # Gate recognition results behind CAPTURE command from RPi
        self.capture_requested = False
        self.capture_mode = "arrow"  # "arrow" or "bull" — controls which classes to accept

        # Lock protects capture_requested and detections (written by both
        # the stream thread via on_result and the receive thread via pc_receive)
        self._lock = threading.Lock()

        # ========== Voting window settings ==========
        # Collect detections over VOTE_WINDOW frames, then pick majority vote
        self.VOTE_WINDOW = 15            # Number of frames to collect before deciding
        self.VOTE_TIMEOUT = 10.0         # Max seconds to wait for detections before giving up
        self.detections = []              # List of (img_id, conf_level, frame, result) tuples
        self.capture_start_time = None   # Timestamp when CAPTURE was requested
        # ============================================

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
        Recognition result callback.
        Collects detections over a voting window, then picks the majority
        vote to avoid sending a wrong result from a single bad frame.
        If the vote timeout expires, sends the best result so far or NONE.

        Filtering by capture_mode:
          - "arrow": only accept LEFT_ARROW_ID / RIGHT_ARROW_ID
          - "bull":  only accept BULLSEYE_ID
        """
        import time as _time

        with self._lock:
            if not self.capture_requested:
                return

            if result is not None:
                conf_level = result.boxes[0].conf.item()
                img_id = result.names[int(result.boxes[0].cls[0].item())]

                # Filter based on capture mode
                if self.capture_mode == "arrow":
                    accept = img_id in [self.LEFT_ARROW_ID, self.RIGHT_ARROW_ID]
                elif self.capture_mode == "bull":
                    accept = (img_id == self.BULLSEYE_ID)
                else:
                    accept = False

                if accept:
                    self.detections.append((img_id, conf_level, frame, result))
                    print(f"[Vote] Collected {len(self.detections)}/{self.VOTE_WINDOW}: "
                          f"{img_id} ({conf_level:.2f})")

            # Once we have enough detections, pick the winner
            if len(self.detections) >= self.VOTE_WINDOW:
                self._resolve_vote()
                return

            # Timeout: send best result so far, or NONE if nothing detected
            if self.capture_start_time and (_time.time() - self.capture_start_time) >= self.VOTE_TIMEOUT:
                if len(self.detections) > 0:
                    print(f"[Vote] Timeout reached with {len(self.detections)}/{self.VOTE_WINDOW} detections — resolving")
                    self._resolve_vote()
                else:
                    print("[Vote] Timeout reached with 0 detections — sending NONE")
                    self.capture_requested = False
                    self.capture_start_time = None
                    self.pc_client.send("NONE")

    def _resolve_vote(self):
        """Pick the majority-voted image ID and send it."""
        import cv2
        from collections import Counter

        self.capture_requested = False  # consume the capture request
        self.capture_start_time = None  # reset timeout

        # Count votes per image ID
        votes = Counter(d[0] for d in self.detections)
        winner_id, vote_count = votes.most_common(1)[0]
        total = len(self.detections)
        print(f"[Vote] Result: {winner_id} with {vote_count}/{total} votes "
              f"(votes: {dict(votes)})")

        # Among detections of the winner, pick the one with highest confidence
        best_conf = 0.0
        best_frame = None
        best_result = None
        for img_id, conf, frm, res in self.detections:
            if img_id == winner_id and conf > best_conf:
                best_conf = conf
                best_frame = frm
                best_result = res

        self.obstacle_img_id = winner_id

        # Draw bounding boxes on the frame using YOLO's plot()
        annotated_frame = best_result.plot() if best_result is not None else best_frame

        # Save annotated frame (with bounding boxes) to images/task_2/
        save_path = os.path.join(
            IMAGES_DIR,
            f"obstacle_{self.obstacle_id}_{winner_id}_{best_conf:.2f}.jpg",
        )
        cv2.imwrite(save_path, annotated_frame)
        print(f"Saved detected image to {save_path}")

        # Add annotated frame to stitching dict (skip bullseye — not an obstacle)
        if self.capture_mode != "bull":
            add_to_stitching_dict(
                self.stitching_dict,
                self.obstacle_id,
                best_conf,
                annotated_frame,
            )
            self.stitching_arr.append(self.obstacle_id)

        # Send result to RPi
        message_content = f"{best_conf},{winner_id}"
        print("Sending:", message_content)
        self.pc_client.send(message_content)

        # Stitch images progressively after each detection
        if self.capture_mode != "bull" and self.stitching_arr:
            print(f"[Stitch] Updating collage with {len(self.stitching_arr)} images so far")
            stitch_images(
                self.stitching_arr,
                self.stitching_dict,
                filename=self.filename,
                blocking=False,
            )

        # Clear detections for next capture
        self.detections = []

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
        1. "CAPTURE" - RPi wants a recognition result (triggered by STM32 snap)
        2. "SEEN"    - Arrow seen, ready for next obstacle
        3. "STITCH"  - Request image stitching
        """
        print("PC Socket connection started successfully")
        while not self.exit:
            try:
                message_rcv = self.pc_client.receive()
                if not message_rcv:
                    print("RPi connection dropped")
                    break
                print("Message received from RPi:", message_rcv)

                if "CAPTURE_BULL" in message_rcv:
                    # RPi requests bull's-eye recognition
                    import time as _time
                    print("CAPTURE_BULL requested — enabling bullseye-only recognition")
                    with self._lock:
                        self.detections = []
                        self.capture_requested = True
                        self.capture_mode = "bull"
                        self.capture_start_time = _time.time()
                        self.obstacle_img_id = None

                elif "CAPTURE" in message_rcv:
                    # RPi requests arrow recognition
                    import time as _time
                    print("CAPTURE requested — enabling arrow-only recognition")
                    with self._lock:
                        self.detections = []
                        self.capture_requested = True
                        self.capture_mode = "arrow"
                        self.capture_start_time = _time.time()
                        self.obstacle_img_id = None

                elif "SEEN" in message_rcv:
                    self.obstacle_id += 1
                    self.obstacle_img_id = None
                    print(f"Obstacle ID incremented to {self.obstacle_id}")

                elif "STITCH" in message_rcv or "FIN" in message_rcv:
                    if self.stitching_arr:
                        print(f"Generating final collage for obstacles: {self.stitching_arr}")
                        stitch_images(
                            self.stitching_arr,
                            self.stitching_dict,
                            filename=self.filename,
                            blocking=True,
                        )
                    else:
                        print("No images to stitch")
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
