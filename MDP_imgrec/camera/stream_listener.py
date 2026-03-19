import base64
import socket

import cv2
import numpy as np
from ultralytics import YOLO


class StreamListener:
    """
    UDP video stream client + YOLO image recognition
    Receives video stream from RPi and performs real-time recognition
    """
    def define_constants(self):
        self.BUFF_SIZE = 65536
        # ========== Modify as needed: set your RPi IP address ==========
        self.HOST_ADDR = ("192.168.8.1", 5005)
        # ================================================
        self.REQ_STREAM = b"stream_request"

    def __init__(self, weights):
        """
        Initialize StreamListener
        
        Args:
            weights: YOLO model weights file path
        """
        # define constants.
        self.define_constants()

        # initialise model.
        # ========== Modify as needed: ensure weights path is correct ==========
        self.model = YOLO(weights)
        # ================================================

        # intialise socket.
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.BUFF_SIZE)

        # timeout of 3 seconds to signal disconnect.
        self.sock.settimeout(3)

    def req_stream(self):
        """Send stream request to RPi"""
        print("Sending request to HOST.")
        self.sock.sendto(self.REQ_STREAM, self.HOST_ADDR)

    def start_stream_read(
        self, on_result, on_disconnect, conf_threshold=0.7, show_video=True
    ):
        """
        Start receiving video stream and perform recognition
        
        Args:
            on_result: Callback function, called when result is detected: on_result(result, frame)
            on_disconnect: Callback function, called when connection is lost
            conf_threshold: Confidence threshold
            show_video: Whether to display video window
        """
        # request for stream to be sent to this client.
        self.req_stream()
        
        # Track if GUI is available (may fail on macOS)
        gui_available = show_video

        while True:
            packet = None
            try:
                packet, _ = self.sock.recvfrom(self.BUFF_SIZE)
            except:
                print("Timeout, ending stream")
                break

            # decode received packet and run prediction model.
            frame = base64.b64decode(packet)
            npdata = np.frombuffer(frame, dtype=np.uint8)
            frame = cv2.imdecode(npdata, cv2.IMREAD_COLOR)
            if frame is None:
                continue
            # RPi typically outputs RGB, OpenCV uses BGR; convert if red/blue are swapped (e.g. brown appears blue)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # ========== Image brightness enhancement (enable if image is dim) ==========
            # Uncomment ONE of these methods if camera image is too dark:
            
            # Method 1: Simple brightness adjustment (fast)
            brightness = 30  # Increase value for brighter image (0-100)
            frame = cv2.convertScaleAbs(frame, alpha=1.0, beta=brightness)
            
            # Method 2: Histogram equalization (better contrast)
            # lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            # lab[:,:,0] = cv2.equalizeHist(lab[:,:,0])
            # frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            
            # Method 3: CLAHE - Adaptive histogram equalization (best quality)
            # lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            # clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            # lab[:,:,0] = clahe.apply(lab[:,:,0])
            # frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            # ============================================================================

            # ========== YOLO inference ==========
            res = self.model.predict(
                frame,
                save=False,
                imgsz=frame.shape[1],
                conf=conf_threshold,
                verbose=False,
            )[0]
            # ==============================

            # perform actions based on results.
            annotated_frame = frame
            if len(res.boxes) > 0:
                annotated_frame = res.plot()
                on_result(res, annotated_frame)
            else:
                on_result(None, frame)

            if gui_available:
                try:
                    cv2.imshow("Stream", annotated_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("q"):
                        break
                except (cv2.error, Exception) as e:
                    # GUI may fail on macOS; continue running without video display
                    print(f"Warning: Cannot display video window ({type(e).__name__}: {e}).")
                    print("Continuing without video display. Recognition will still work normally.")
                    gui_available = False

        # call final disconnect handler.
        on_disconnect()

    def close(self):
        """Release resources and close"""
        self.sock.close()
