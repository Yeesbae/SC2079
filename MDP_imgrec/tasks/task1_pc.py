"""
Task 1 PC-side code - AUTO-SEND MODE
Receives video stream, performs YOLO recognition, and automatically sends results to RPi
When a new image is detected, it immediately sends: "obstacle_id,confidence,image_id"
Then sends the annotated frame as base64 JPEG: "IMG_DATA:obstacle_id:image_id:b64jpeg"
"""
import base64
import socket
import sys
import threading
from pathlib import Path
from time import time_ns, sleep

# Add project path
sys.path.insert(0, str(Path(__file__).parent.parent))

from camera.stream_listener import StreamListener
from communication.pc_client import PCClient
from stitching.stitching import stitch_images, add_to_stitching_dict
from config.config import Config


class Task1PC:
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

        print(f"! -- initialising weights file: {config.task1_weights}....")
        self.stream_listener = StreamListener(config.task1_weights)
        
        # Task1-specific variables
        self.IMG_BLACKLIST = ["marker"]  # ========== Modify blacklist as needed ==========
        self.prev_image = None
        self.img_time_dict = {}  # Store timestamps for image IDs
        self.time_advance_ns = 0.75e9  # ========== Time matching parameters, adjust as needed ==========
        self.time_threshold_ns = 1.5e9
        self.img_pending_arr = []  # List of obstacle IDs pending match
        self.stitching_img_dict = {}  # Store images for stitching
        self.stitching_arr = []  # Array of image IDs to stitch
        self.should_stitch = False
        self.stitch_len = 0  # Number of images to stitch

        self.filename = "task1"  # ========== Stitching output file prefix ==========
        self.start_time = time_ns()
        
        # Auto-send variables
        self.obstacle_id = 1  # Fallback obstacle ID counter
        self.current_snap_obstacle_id = None  # Obstacle ID from latest SNAP command
        self.sent_images = set()  # Track which images have been sent

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
            conf_threshold=self.config.conf_threshold, 
            show_video=True  # ========== Display video window and recognition results ==========
        )
        
    def on_result(self, result, frame):
        """
        Recognition result callback - AUTO-SEND MODE
        
        Args:
            result: YOLO recognition result
            frame: Image frame
        """
        if result is not None:
            names = result.names
            
            for box in result.boxes:
                detected_img_id = names[int(box.cls[0].item())]
                detected_conf_level = box.conf.item()
                
                # Skip blacklisted images
                if detected_img_id in self.IMG_BLACKLIST:
                    continue
                
                self.prev_image = detected_img_id
                # Add to stitching dict
                add_to_stitching_dict(
                    self.stitching_img_dict, 
                    detected_img_id, 
                    detected_conf_level, 
                    frame
                )
                
                # Only send detection if a SNAP command has been received.
                # This prevents spurious detections from firing before the
                # RPi asks for one, which would use wrong obstacle IDs.
                if self.current_snap_obstacle_id is not None and detected_img_id not in self.sent_images:
                    use_obstacle_id = self.current_snap_obstacle_id
                    self.current_snap_obstacle_id = None  # consume it — one detection per SNAP

                    message_content = f"{use_obstacle_id},{detected_conf_level},{detected_img_id}"
                    print(f"[AUTO-SEND] Detected new image: {detected_img_id}, obstacle_id={use_obstacle_id}, sending to RPi...")
                    print(f"Sending: {message_content}")
                    self.pc_client.send(message_content)

                    # Also send the best-confidence frame as a base64 JPEG
                    try:
                        import cv2
                        frame_resized = cv2.resize(frame, (320, 320))
                        _, jpeg_buffer = cv2.imencode(
                            '.jpg', frame_resized,
                            [cv2.IMWRITE_JPEG_QUALITY, 50]
                        )
                        b64_data = base64.b64encode(jpeg_buffer.tobytes()).decode('utf-8')
                        img_data_msg = f"IMG_DATA:{use_obstacle_id}:{detected_img_id}:{b64_data}"
                        self.pc_client.send(img_data_msg)
                        print(f"[AUTO-SEND] Sent image binary for {detected_img_id} "
                              f"({len(b64_data)} b64 chars)")
                    except Exception as img_err:
                        print(f"[AUTO-SEND] Failed to send image binary: {img_err}")

                    self.sent_images.add(detected_img_id)
                    self.stitching_arr.append(detected_img_id)
                
                # Save timestamp (for legacy compatibility)
                cur_time = time_ns()
                old_time = cur_time
                if detected_img_id in self.img_time_dict:
                    old_time = self.img_time_dict[detected_img_id][0]
                
                self.img_time_dict[detected_img_id] = (old_time, cur_time)

        elif self.prev_image != "NONE":
            # No object detected
            self.prev_image = "NONE"

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

    def interval_overlap(self, int1, int2):
        """Compute overlap of two time intervals"""
        min1, max1 = int1
        min2, max2 = int2
        return min(max1, max2) - max(min1, min2)

    def check_timestamp(self, img_id, timestamp, old_time, cur_time):
        """
        Check if image ID timestamp matches obstacle timestamp
        
        Args:
            img_id: Image ID
            timestamp: Obstacle detection timestamp
            old_time: Image first detection time
            cur_time: Image current detection time
        """
        if img_id in self.stitching_arr:
            return 0
        
        timestamp_int = (
            timestamp - self.time_advance_ns, 
            timestamp + self.time_threshold_ns
        )
        comp_int = (old_time, cur_time)
        overlap = self.interval_overlap(comp_int, timestamp_int)
        return overlap
    
    def match_image(self, obstacle_id, img_id):
        """
        Match obstacle ID to image ID, send result to RPi
        
        Args:
            obstacle_id: Obstacle ID
            img_id: Image ID
        """
        print(f"Matched obstacle ID {obstacle_id} as image ID {img_id}.")
        self.stitching_arr.append(img_id)
        print(f"Images found for stitching: {len(self.stitching_arr)}")
        
        # Send format: "obstacle_id,confidence,image_id"
        message_content = f"{obstacle_id},{self.stitching_img_dict[img_id][0]},{img_id}"
        print("Sending:", message_content)
        self.pc_client.send(message_content)

    def pc_receive(self) -> None:
        """
        Receive commands from RPi
        
        Command formats:
        1. "DETECT,obstacle_id" - Request image for specified obstacle (LEGACY - not used in auto-send mode)
        2. "PERFORM STITCHING,num" - Request stitching of num images
        3. "SEEN" - Reset detection (allow re-detection of same images)
        """
        print("PC Socket connection started successfully")
        while not self.exit:
            try:
                message_rcv = self.pc_client.receive()
                print("Message received from RPi:", message_rcv)

                if "SEEN" in message_rcv:
                    # Reset sent images to allow re-detection
                    print("Received SEEN command - resetting detection state")
                    self.sent_images.clear()

                if message_rcv.startswith("SNAP"):
                    # SNAP command format: "SNAP{obstacle_id}_{position}"
                    # e.g., "SNAP2_L" → obstacle_id = "2"
                    snap_body = message_rcv[4:]  # Remove "SNAP" prefix
                    parts = snap_body.split("_")
                    snap_obstacle_id = parts[0]
                    self.current_snap_obstacle_id = snap_obstacle_id
                    # Reset sent_images so the next detection is sent even if
                    # the same image_id was seen before for a different obstacle
                    self.sent_images.clear()
                    print(f"[SNAP] Received SNAP command for obstacle {snap_obstacle_id}, "
                          f"will use this ID for next detection")

                elif "DETECT" in message_rcv:
                    # Command format: "DETECT,obstacle_id"
                    obstacle_id = message_rcv.split(",")[1]
                    timestamp = time_ns()
                    
                    # Find matching image in timestamp dict
                    max_overlap = 0
                    max_img_id = None
                    for img_id, (old_time, cur_time) in self.img_time_dict.items():
                        overlap = self.check_timestamp(img_id, timestamp, old_time, cur_time)
                        print(f"overlap: {overlap}, max overlap: {max_overlap}")
                        if overlap > 0 and overlap >= max_overlap:
                            print(f"replacing max overlap with {overlap}")
                            max_overlap = overlap
                            max_img_id = img_id
                    
                    if max_img_id is not None:
                        # Found match, send immediately
                        self.match_image(obstacle_id, max_img_id)
                        del self.img_time_dict[max_img_id]
                    else:
                        # No match, add to pending list
                        self.img_pending_arr.append((obstacle_id, timestamp))

                elif "PERFORM STITCHING" in message_rcv:
                    # Command format: "PERFORM STITCHING,num"
                    self.stitch_len = int(message_rcv.split(",")[1])
                    
                    if len(self.stitching_arr) < self.stitch_len:
                        # Not all images found yet, wait
                        print("Stitch request received, wait for completion...")
                        self.should_stitch = True
                        sleep(self.time_threshold_ns * 2e-9)
                        if self.should_stitch:
                            # Timeout, stitch whatever we have
                            stitch_images(
                                self.stitching_arr, 
                                self.stitching_img_dict, 
                                filename=self.filename
                            )
                    else:
                        # All images found, stitch immediately
                        print("All images present, stitching now...")
                        self.stream_listener.close()
                        stitch_images(
                            self.stitching_arr, 
                            self.stitching_img_dict, 
                            filename=self.filename
                        )

                if not message_rcv:
                    print("RPi connection dropped")
                    break
            except OSError as e:
                print("Error in receiving data:", e)
                break


def main(config: Config):
    """
    Task1 main function
    """
    print("# ------------- Running Task 1, PC ---------------- #")
    print(f"You are {'out' if config.is_outdoors else 'in'}doors.")
    pcMain = Task1PC(config)
    pcMain.start()
    
    # Keep running
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        pcMain.disconnect()
